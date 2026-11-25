import random

import pytest
from materials import PROPS, Material, can_displace, is_mobile, palette
from world import MAX_SPEED, World

SAND, WATER, STONE, EMPTY = Material.SAND, Material.WATER, Material.STONE, Material.EMPTY


def make(width: int = 12, height: int = 12, seed: int = 0) -> World:
    return World(width, height, random.Random(seed))


def settle(world: World, max_ticks: int = 2000, quiet: int = 30) -> None:
    '''Step until nothing moved for `quiet` consecutive ticks.'''
    still = 0
    for _ in range(max_ticks):
        still = still + 1 if world.step() == 0 else 0
        if still >= quiet:
            return
    raise AssertionError('world did not settle')


def ys(world: World, material: Material) -> list[int]:
    return [y for _, y, m in world.particles() if m == material]


# -- materials -------------------------------------------------------------


def test_material_rules() -> None:
    assert is_mobile(SAND) and is_mobile(WATER)
    assert not is_mobile(STONE) and not is_mobile(EMPTY)
    assert can_displace(SAND, EMPTY) and can_displace(SAND, WATER)
    assert not can_displace(WATER, SAND) and not can_displace(WATER, WATER)
    assert not can_displace(SAND, STONE)
    assert PROPS[SAND].density > PROPS[WATER].density
    assert all(len(shades) > 1 for shades in palette().values())


# -- gravity ---------------------------------------------------------------


def test_free_fall_accelerates() -> None:
    world = make(3, 60)
    world.set(1, 0, SAND)
    positions = []
    for _ in range(8):
        world.step()
        positions.append(ys(world, SAND)[0])
    deltas = [b - a for a, b in zip([0, *positions], positions, strict=False)]
    assert deltas[0] == 1
    assert deltas[-1] > deltas[0]
    assert deltas == sorted(deltas)


def test_fall_speed_is_capped() -> None:
    world = make(3, 200)
    world.set(1, 0, SAND)
    previous = 0
    for _ in range(40):
        world.step()
        y = ys(world, SAND)[0]
        assert y - previous <= MAX_SPEED
        previous = y


def test_fast_grain_stops_on_floor_and_stone() -> None:
    world = make(3, 40)
    world.set(1, 0, SAND)
    settle(world)
    assert ys(world, SAND) == [39]

    world = make(3, 40)
    for x in range(3):
        world.set(x, 30, STONE)
    world.set(1, 0, SAND)
    settle(world)
    assert world.get(1, 29) == SAND


def test_stone_never_moves() -> None:
    world = make(5, 5)
    world.set(2, 0, STONE)
    for _ in range(10):
        world.step()
    assert world.get(2, 0) == STONE


def test_outside_is_solid() -> None:
    assert make().get(-1, 0) == STONE
    assert make().get(0, 99) == STONE


# -- powder ----------------------------------------------------------------


def test_grain_slides_off_another_grain() -> None:
    world = make(5, 3)
    world.set(2, 2, SAND)
    world.set(2, 1, SAND)
    world.velocity[1 * 5 + 2] = 1.0  # just landed: no static friction
    world.step()
    assert world.get(2, 2) == SAND
    assert sorted(x for x, y, _ in world.particles() if y == 2) in ([1, 2], [2, 3])


def test_no_squeezing_through_diagonal_gap() -> None:
    world = make(4, 4)
    world.set(1, 3, STONE)  # below
    world.set(2, 2, STONE)  # right
    world.set(0, 2, STONE)  # left
    world.set(1, 2, SAND)
    settle(world)
    assert world.get(1, 2) == SAND


def test_sand_pile_has_slopes_not_a_tower() -> None:
    width, height = 41, 30
    world = make(width, height)
    for _ in range(150):
        world.paint(20, 0, 0, SAND)
        world.step()
    settle(world)
    heights = [world.column_height(x, SAND) for x in range(width)]
    assert sum(heights) == 150
    peak = heights.index(max(heights))
    assert abs(peak - 20) <= 3
    # Neighbouring columns differ by at most one cell (diagonal slide rule).
    assert all(abs(a - b) <= 1 for a, b in zip(heights, heights[1:], strict=False))
    assert sum(1 for h in heights if h) > 15


# -- liquid ----------------------------------------------------------------


def test_water_spreads_into_a_flat_layer() -> None:
    width = 20
    world = make(width, 10)
    for y in range(8):
        world.set(10, y, WATER)
    # A thin film keeps wandering sideways (it never fully settles), but it
    # must end up as a single layer on the floor.
    for _ in range(200):
        world.step()
    assert ys(world, WATER) == [9] * 8


def test_water_levels_out_across_the_floor() -> None:
    width = 10
    world = make(width, 12)
    for y in range(10):
        for x in range(3):
            world.set(x, y, WATER)
    for _ in range(600):
        world.step()
    heights = [world.column_height(x, WATER) for x in range(width)]
    assert sum(heights) == 30
    assert max(heights) - min(heights) <= 1


def test_sand_sinks_through_water() -> None:
    world = make(1, 10)
    for y in range(5, 10):
        world.set(0, y, WATER)
    for y in range(0, 3):
        world.set(0, y, SAND)
    settle(world)
    column = [world.get(0, y) for y in range(10)]
    assert column[-3:] == [SAND] * 3
    assert column[2:7] == [WATER] * 5


def test_sand_falls_slower_in_water() -> None:
    def distance_after(ticks: int, medium: Material) -> int:
        world = make(1, 80)
        for y in range(20, 80):
            world.set(0, y, medium)
        world.set(0, 0, SAND)
        world.velocity[0] = MAX_SPEED
        for _ in range(ticks):
            world.step()
        return ys(world, SAND)[0]

    assert distance_after(12, WATER) < distance_after(12, EMPTY)


# -- conservation ----------------------------------------------------------


@pytest.mark.parametrize('seed', range(5))
def test_particles_are_conserved(seed: int) -> None:
    rng = random.Random(seed)
    world = make(16, 16, seed)
    for _ in range(80):
        world.set(rng.randrange(16), rng.randrange(16), rng.choice([SAND, WATER, STONE]))
    counts = {m: world.count(m) for m in (SAND, WATER, STONE)}
    for _ in range(200):
        world.step()
        assert {m: world.count(m) for m in counts} == counts


# -- painting --------------------------------------------------------------


def test_paint_disc_clipped_and_only_into_empty() -> None:
    world = make(10, 10)
    world.set(0, 0, STONE)
    painted = world.paint(0, 0, 2, SAND)
    assert world.get(0, 0) == STONE
    assert painted == world.count(SAND) == 5  # 6-cell quarter disc minus the stone
    assert world.paint(0, 0, 2, WATER) == 0


def test_paint_fill_probability_and_eraser() -> None:
    world = make(30, 30)
    sparse = world.paint(15, 15, 10, SAND, fill=0.3)
    assert 0 < sparse < 317 * 0.6
    assert world.paint(15, 15, 30, EMPTY) == sparse
    assert world.count(SAND) == 0


def test_clear() -> None:
    world = make()
    world.paint(5, 5, 3, WATER)
    world.clear()
    assert list(world.particles()) == []
