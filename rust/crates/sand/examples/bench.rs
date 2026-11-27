//! Time `World::step` on the game's 160x120 grid with sand and water.
//!
//!     cargo run --release -p sand --example bench
//!
//! Same scenario as the Python measurement (about 6 ms per step).

use sand::{Material, World};
use std::time::Instant;

fn main() {
    let mut world = World::new(160, 120, fastrand::Rng::with_seed(0));
    for x in (0..160).step_by(8) {
        world.paint(x, 20, 6, Material::Sand, 0.5);
        world.paint(x, 60, 6, Material::Water, 0.6);
    }
    let (sand, water) = (world.count(Material::Sand), world.count(Material::Water));
    let steps = 100;
    let start = Instant::now();
    for _ in 0..steps {
        world.step();
    }
    let per_step = start.elapsed().as_secs_f64() * 1000.0 / steps as f64;
    println!("{per_step:.3} ms/step ({sand} sand, {water} water)");
}
