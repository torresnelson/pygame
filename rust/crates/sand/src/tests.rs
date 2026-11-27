//! Ports of `tests/test_world.py`.

use super::*;
use Material::{Empty as EMPTY_M, Sand as SAND, Stone as STONE, Water as WATER};

fn make(width: i32, height: i32, seed: u64) -> World {
    World::new(width, height, fastrand::Rng::with_seed(seed))
}

/// Step until nothing moved for `quiet` consecutive ticks.
fn settle(world: &mut World) {
    let mut still = 0;
    for _ in 0..2000 {
        still = if world.step() == 0 { still + 1 } else { 0 };
        if still >= 30 {
            return;
        }
    }
    panic!("world did not settle");
}

fn ys(world: &World, material: Material) -> Vec<i32> {
    world
        .particles()
        .filter(|&(_, _, m)| m == material)
        .map(|(_, y, _)| y)
        .collect()
}

// -- materials ----------------------------------------------------------------

#[test]
fn material_rules() {
    assert!(is_mobile(SAND) && is_mobile(WATER));
    assert!(!is_mobile(STONE) && !is_mobile(EMPTY_M));
    assert!(can_displace(SAND, EMPTY_M) && can_displace(SAND, WATER));
    assert!(!can_displace(WATER, SAND) && !can_displace(WATER, WATER));
    assert!(!can_displace(SAND, STONE));
    assert!(SAND.props().density > WATER.props().density);
    assert!(
        palette()
            .iter()
            .all(|shades| shades.iter().any(|&c| c != shades[0]) || shades[0] == (0, 0, 0))
    );
}

#[test]
fn shades_match_python() {
    // int(channel * factor), capped at 255, for factor 0.85 .. 1.15.
    assert_eq!(materials::shade((220, 190, 110), 0), (187, 161, 93));
    assert_eq!(
        materials::shade((220, 190, 110), SHADES - 1),
        (253, 218, 126)
    );
    assert_eq!(
        materials::shade((250, 250, 250), SHADES - 1),
        (255, 255, 255)
    );
}

// -- gravity --------------------------------------------------------------------

#[test]
fn free_fall_accelerates() {
    let mut world = make(3, 60, 0);
    world.set(1, 0, SAND);
    let mut positions = vec![0];
    for _ in 0..8 {
        world.step();
        positions.push(ys(&world, SAND)[0]);
    }
    let deltas: Vec<i32> = positions.windows(2).map(|w| w[1] - w[0]).collect();
    assert_eq!(deltas[0], 1);
    assert!(deltas.last() > deltas.first());
    assert!(deltas.windows(2).all(|w| w[0] <= w[1]), "{deltas:?}");
}

#[test]
fn fall_speed_is_capped() {
    let mut world = make(3, 200, 0);
    world.set(1, 0, SAND);
    let mut previous = 0;
    for _ in 0..40 {
        world.step();
        let y = ys(&world, SAND)[0];
        assert!((y - previous) as f32 <= MAX_SPEED);
        previous = y;
    }
}

#[test]
fn fast_grain_stops_on_floor_and_stone() {
    let mut world = make(3, 40, 0);
    world.set(1, 0, SAND);
    settle(&mut world);
    assert_eq!(ys(&world, SAND), vec![39]);

    let mut world = make(3, 40, 0);
    for x in 0..3 {
        world.set(x, 30, STONE);
    }
    world.set(1, 0, SAND);
    settle(&mut world);
    assert_eq!(world.get(1, 29), SAND);
}

#[test]
fn stone_never_moves() {
    let mut world = make(5, 5, 0);
    world.set(2, 0, STONE);
    for _ in 0..10 {
        world.step();
    }
    assert_eq!(world.get(2, 0), STONE);
}

#[test]
fn outside_is_solid() {
    assert_eq!(make(12, 12, 0).get(-1, 0), STONE);
    assert_eq!(make(12, 12, 0).get(0, 99), STONE);
}

// -- powder ---------------------------------------------------------------------

#[test]
fn grain_slides_off_another_grain() {
    for seed in 0..10 {
        let mut world = make(5, 3, seed);
        world.set(2, 2, SAND);
        world.set(2, 1, SAND);
        world.velocity[5 + 2] = 1.0; // just landed: no static friction
        world.step();
        assert_eq!(world.get(2, 2), SAND);
        let mut bottom: Vec<i32> = world
            .particles()
            .filter(|&(_, y, _)| y == 2)
            .map(|(x, _, _)| x)
            .collect();
        bottom.sort();
        assert!(
            bottom == vec![1, 2] || bottom == vec![2, 3],
            "seed {seed}: {bottom:?}"
        );
    }
}

#[test]
fn no_squeezing_through_diagonal_gap() {
    let mut world = make(4, 4, 0);
    world.set(1, 3, STONE); // below
    world.set(2, 2, STONE); // right
    world.set(0, 2, STONE); // left
    world.set(1, 2, SAND);
    settle(&mut world);
    assert_eq!(world.get(1, 2), SAND);
}

#[test]
fn sand_pile_has_slopes_not_a_tower() {
    for seed in 0..5 {
        let (width, height) = (41, 30);
        let mut world = make(width, height, seed);
        for _ in 0..150 {
            world.paint(20, 0, 0, SAND, 1.0);
            world.step();
        }
        settle(&mut world);
        let heights: Vec<usize> = (0..width).map(|x| world.column_height(x, SAND)).collect();
        assert_eq!(heights.iter().sum::<usize>(), 150);
        let peak = heights
            .iter()
            .position(|h| h == heights.iter().max().unwrap())
            .unwrap();
        assert!((peak as i32 - 20).abs() <= 3, "seed {seed}: peak {peak}");
        // Neighbouring columns differ by at most one cell (diagonal slide rule).
        assert!(
            heights.windows(2).all(|w| w[0].abs_diff(w[1]) <= 1),
            "seed {seed}: {heights:?}"
        );
        assert!(heights.iter().filter(|&&h| h > 0).count() > 15);
    }
}

// -- liquid ---------------------------------------------------------------------

#[test]
fn water_spreads_into_a_flat_layer() {
    let mut world = make(20, 10, 0);
    for y in 0..8 {
        world.set(10, y, WATER);
    }
    // A thin film keeps wandering sideways (it never fully settles), but it
    // must end up as a single layer on the floor.
    for _ in 0..200 {
        world.step();
    }
    assert_eq!(ys(&world, WATER), vec![9; 8]);
}

#[test]
fn water_levels_out_across_the_floor() {
    let width = 10;
    let mut world = make(width, 12, 0);
    for y in 0..10 {
        for x in 0..3 {
            world.set(x, y, WATER);
        }
    }
    for _ in 0..600 {
        world.step();
    }
    let heights: Vec<usize> = (0..width).map(|x| world.column_height(x, WATER)).collect();
    assert_eq!(heights.iter().sum::<usize>(), 30);
    assert!(
        heights.iter().max().unwrap() - heights.iter().min().unwrap() <= 1,
        "{heights:?}"
    );
}

#[test]
fn sand_sinks_through_water() {
    let mut world = make(1, 10, 0);
    for y in 5..10 {
        world.set(0, y, WATER);
    }
    for y in 0..3 {
        world.set(0, y, SAND);
    }
    settle(&mut world);
    let column: Vec<Material> = (0..10).map(|y| world.get(0, y)).collect();
    assert_eq!(column[7..], [SAND; 3]);
    assert_eq!(column[2..7], [WATER; 5]);
}

#[test]
fn sand_falls_slower_in_water() {
    let distance_after = |ticks: usize, medium: Material| {
        let mut world = make(1, 80, 0);
        for y in 20..80 {
            world.set(0, y, medium);
        }
        world.set(0, 0, SAND);
        world.velocity[0] = MAX_SPEED;
        for _ in 0..ticks {
            world.step();
        }
        ys(&world, SAND)[0]
    };
    assert!(distance_after(12, WATER) < distance_after(12, EMPTY_M));
}

// -- conservation ---------------------------------------------------------------

#[test]
fn particles_are_conserved() {
    for seed in 0..5 {
        let mut rng = fastrand::Rng::with_seed(seed);
        let mut world = make(16, 16, seed);
        for _ in 0..80 {
            let material = [SAND, WATER, STONE][rng.usize(..3)];
            world.set(rng.i32(..16), rng.i32(..16), material);
        }
        let counts: Vec<usize> = [SAND, WATER, STONE].map(|m| world.count(m)).to_vec();
        for _ in 0..200 {
            world.step();
            assert_eq!(
                [SAND, WATER, STONE].map(|m| world.count(m)).to_vec(),
                counts
            );
        }
    }
}

// -- painting -------------------------------------------------------------------

#[test]
fn paint_disc_clipped_and_only_into_empty() {
    let mut world = make(10, 10, 0);
    world.set(0, 0, STONE);
    let painted = world.paint(0, 0, 2, SAND, 1.0);
    assert_eq!(world.get(0, 0), STONE);
    assert_eq!(painted, 5); // 6-cell quarter disc minus the stone
    assert_eq!(world.count(SAND), 5);
    assert_eq!(world.paint(0, 0, 2, WATER, 1.0), 0);
}

#[test]
fn paint_fill_probability_and_eraser() {
    let mut world = make(30, 30, 0);
    let sparse = world.paint(15, 15, 10, SAND, 0.3);
    assert!(sparse > 0 && (sparse as f32) < 317.0 * 0.6, "{sparse}");
    assert_eq!(world.paint(15, 15, 30, EMPTY_M, 1.0), sparse);
    assert_eq!(world.count(SAND), 0);
}

#[test]
fn clear_empties_the_world() {
    let mut world = make(12, 12, 0);
    world.paint(5, 5, 3, WATER, 1.0);
    world.clear();
    assert_eq!(world.particles().count(), 0);
}

#[test]
fn resized_keeps_particles_on_the_floor_and_drops_what_does_not_fit() {
    let mut world = make(6, 4, 1);
    world.set(0, 3, SAND); // bottom-left
    world.set(5, 3, WATER); // bottom-right: outside a 4-wide copy
    world.set(1, 0, STONE); // top row: outside a 2-tall copy

    let narrow = world.resized(4, 6);
    assert_eq!(narrow.get(0, 5), SAND);
    assert_eq!(narrow.get(1, 2), STONE);
    assert_eq!(narrow.count(WATER), 0);

    let short = world.resized(6, 2);
    assert_eq!(short.get(0, 1), SAND);
    assert_eq!(short.get(5, 1), WATER);
    assert_eq!(short.count(STONE), 0);
    assert_eq!((short.width, short.height), (6, 2));
}

#[test]
fn resized_copy_is_independent() {
    let mut world = make(3, 3, 0);
    world.set(1, 2, SAND);
    let copy = world.resized(3, 3);
    world.clear();
    assert_eq!(copy.get(1, 2), SAND);
}
