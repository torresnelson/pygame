//! Falling-sand physics engine (port of `src/sand_simulator/world.py`).
//!
//! The world is a fixed grid of particles in flat, row-major vectors. Each
//! tick rows are scanned bottom-up, alternating the horizontal scan direction
//! per row and per tick so no side is favoured. A per-cell tick stamp
//! guarantees a particle moves at most once per tick.
//!
//! - Gravity: mobile particles accelerate by `GRAVITY` cells/tick^2 up to
//!   `MAX_SPEED`, moving several cells per tick when fast.
//! - Density: a particle may move into empty space or sink through a lighter
//!   liquid (swapping places); sinking is capped at the liquid's drag speed.
//! - Powders slide diagonally when blocked, never squeezing between two
//!   diagonal neighbours; resting grains resist sliding with `friction`, and
//!   fast impacts scatter grains further down the slope.
//! - Liquids fall like powders, then flow sideways up to `dispersion` cells
//!   per tick, keeping a flow direction until they hit something.
//! - Solids never move. Outside the grid counts as solid.

pub mod materials;

pub use materials::{Color, Material, PROPS, SHADES, State, can_displace, is_mobile, palette};

pub const GRAVITY: f32 = 0.5;
pub const MAX_SPEED: f32 = 6.0;
pub const SCATTER_SPEED: f32 = 3.0;

const EMPTY: u8 = Material::Empty as u8;

pub struct World {
    pub width: i32,
    pub height: i32,
    pub rng: fastrand::Rng,
    pub tick: u32,
    pub material: Vec<u8>,
    pub velocity: Vec<f32>,
    pub shade: Vec<u8>,
    pub flow: Vec<i8>,
    pub stamp: Vec<u32>,
}

impl World {
    pub fn new(width: i32, height: i32, rng: fastrand::Rng) -> Self {
        let size = (width * height) as usize;
        Self {
            width,
            height,
            rng,
            tick: 0,
            material: vec![EMPTY; size],
            velocity: vec![0.0; size],
            shade: vec![0; size],
            flow: vec![1; size],
            stamp: vec![0; size],
        }
    }

    // -- queries ----------------------------------------------------------

    pub fn in_bounds(&self, x: i32, y: i32) -> bool {
        (0..self.width).contains(&x) && (0..self.height).contains(&y)
    }

    fn index(&self, x: i32, y: i32) -> usize {
        (y * self.width + x) as usize
    }

    pub fn get(&self, x: i32, y: i32) -> Material {
        if !self.in_bounds(x, y) {
            return Material::Stone;
        }
        Material::from_index(self.material[self.index(x, y)])
    }

    pub fn count(&self, material: Material) -> usize {
        self.material
            .iter()
            .filter(|&&m| m == material as u8)
            .count()
    }

    /// Every non-empty cell as (x, y, material), row by row.
    pub fn particles(&self) -> impl Iterator<Item = (i32, i32, Material)> + '_ {
        let width = self.width;
        self.material
            .iter()
            .enumerate()
            .filter(|&(_, &m)| m != EMPTY)
            .map(move |(i, &m)| (i as i32 % width, i as i32 / width, Material::from_index(m)))
    }

    /// Number of `material` cells in column `x`.
    pub fn column_height(&self, x: i32, material: Material) -> usize {
        (0..self.height)
            .filter(|&y| self.material[self.index(x, y)] == material as u8)
            .count()
    }

    // -- editing ----------------------------------------------------------

    pub fn set(&mut self, x: i32, y: i32, material: Material) {
        if !self.in_bounds(x, y) {
            return;
        }
        let i = self.index(x, y);
        self.material[i] = material as u8;
        self.velocity[i] = 0.0;
        self.shade[i] = self.rng.u8(..SHADES as u8);
        self.flow[i] = if self.rng.bool() { -1 } else { 1 };
    }

    /// Paint a disc of `material`; returns how many cells changed.
    ///
    /// `Material::Empty` erases anything. Other materials only fill empty
    /// cells, each with probability `fill` so poured sand looks granular.
    pub fn paint(&mut self, cx: i32, cy: i32, radius: i32, material: Material, fill: f32) -> usize {
        let mut changed = 0;
        for y in cy - radius..=cy + radius {
            for x in cx - radius..=cx + radius {
                if (x - cx).pow(2) + (y - cy).pow(2) > radius * radius || !self.in_bounds(x, y) {
                    continue;
                }
                let current = self.material[self.index(x, y)];
                if material == Material::Empty {
                    if current != EMPTY {
                        self.set(x, y, material);
                        changed += 1;
                    }
                } else if current == EMPTY && self.rng.f32() < fill {
                    self.set(x, y, material);
                    changed += 1;
                }
            }
        }
        changed
    }

    pub fn clear(&mut self) {
        self.material.fill(EMPTY);
        self.velocity.fill(0.0);
    }

    /// A `width` x `height` copy, aligned to the bottom-left corner.
    ///
    /// Bottom-aligned so piles stay on the floor; whatever does not fit is
    /// dropped. Particles start at rest.
    pub fn resized(&self, width: i32, height: i32) -> World {
        let mut world = World::new(width, height, self.rng.clone());
        world.tick = self.tick;
        for row in 0..height.min(self.height) {
            let src = ((self.height - 1 - row) * self.width) as usize;
            let dst = ((height - 1 - row) * width) as usize;
            for x in 0..width.min(self.width) as usize {
                world.material[dst + x] = self.material[src + x];
                world.shade[dst + x] = self.shade[src + x];
                world.flow[dst + x] = self.flow[src + x];
            }
        }
        world
    }

    // -- simulation -------------------------------------------------------

    /// Advance one tick; return how many particles moved.
    pub fn step(&mut self) -> usize {
        self.tick += 1;
        let tick = self.tick;
        let mut moved = 0;
        for y in (0..self.height).rev() {
            let left_to_right = (tick as i32 + y) % 2 == 1;
            for k in 0..self.width {
                let x = if left_to_right { k } else { self.width - 1 - k };
                let i = self.index(x, y);
                let m = self.material[i];
                if m == EMPTY || self.stamp[i] == tick {
                    continue;
                }
                moved += match Material::from_index(m).props().state {
                    State::Powder => self.update_powder(x, y, i, m),
                    State::Liquid => self.update_liquid(x, y, i, m),
                    _ => 0,
                };
            }
        }
        moved
    }

    /// Index of (x, y) if `mover` can move there.
    fn target(&self, x: i32, y: i32, mover: u8) -> Option<usize> {
        if !self.in_bounds(x, y) {
            return None;
        }
        let j = self.index(x, y);
        can_displace(
            Material::from_index(mover),
            Material::from_index(self.material[j]),
        )
        .then_some(j)
    }

    fn swap(&mut self, i: usize, j: usize) {
        self.material.swap(i, j);
        self.velocity.swap(i, j);
        self.shade.swap(i, j);
        self.flow.swap(i, j);
        self.stamp[i] = self.tick;
        self.stamp[j] = self.tick;
    }

    /// Accelerate and fall; return (new y, new index, impact speed or 0 if airborne).
    fn fall(&mut self, x: i32, mut y: i32, mut i: usize, m: u8) -> (i32, usize, f32) {
        let mut speed = (self.velocity[i] + GRAVITY).min(MAX_SPEED);
        let mut budget = (speed as i32).max(1);
        let mut fallen = 0;
        while fallen < budget {
            let Some(j) = self.target(x, y + 1, m) else {
                break;
            };
            if self.material[j] != EMPTY {
                // Sinking through a liquid: drag caps the speed.
                let drag = Material::from_index(self.material[j]).props().drag_speed;
                speed = speed.min(drag);
                budget = budget.min((drag as i32).max(1));
            }
            self.swap(i, j);
            i = j;
            y += 1;
            fallen += 1;
        }
        if fallen == budget {
            self.velocity[i] = speed;
            return (y, i, 0.0);
        }
        self.velocity[i] = 0.0;
        (y, i, if fallen > 0 { speed.max(1.0) } else { 0.0 })
    }

    /// Move one cell diagonally down towards `dx` if not squeezing; the new index.
    fn slide(&mut self, x: i32, y: i32, i: usize, m: u8, dx: i32) -> Option<usize> {
        let j = self.target(x + dx, y + 1, m)?;
        self.target(x + dx, y, m)?;
        self.swap(i, j);
        Some(j)
    }

    /// -1 and 1 in random order.
    fn directions(&mut self) -> [i32; 2] {
        if self.rng.bool() { [-1, 1] } else { [1, -1] }
    }

    fn update_powder(&mut self, mut x: i32, y: i32, i: usize, m: u8) -> usize {
        let was_resting = self.velocity[i] == 0.0;
        let (new_y, mut i, impact) = self.fall(x, y, i, m);
        if new_y != y && impact == 0.0 {
            return 1; // still in free fall
        }
        let friction = Material::from_index(m).props().friction;
        if new_y == y && was_resting && self.rng.f32() < friction {
            return 0; // static friction holds the grain this tick
        }

        let fell = new_y != y;
        let mut y = new_y;
        for dx in self.directions() {
            let Some(j) = self.slide(x, y, i, m, dx) else {
                continue;
            };
            // Fast impacts keep tumbling down the slope.
            let extra = if impact >= SCATTER_SPEED {
                (impact / 2.0) as i32
            } else {
                0
            };
            (x, y, i) = (x + dx, y + 1, j);
            for _ in 0..extra {
                let Some(j) = self.slide(x, y, i, m, dx) else {
                    break;
                };
                (x, y, i) = (x + dx, y + 1, j);
            }
            return 1;
        }
        usize::from(fell)
    }

    fn update_liquid(&mut self, mut x: i32, y: i32, i: usize, m: u8) -> usize {
        let (new_y, mut i, impact) = self.fall(x, y, i, m);
        if new_y != y && impact == 0.0 {
            return 1;
        }
        let mut moved = new_y != y;
        let y = new_y;

        for dx in self.directions() {
            if self.slide(x, y, i, m, dx).is_some() {
                return 1;
            }
        }

        let direction = self.flow[i] as i32;
        let dispersion = Material::from_index(m).props().dispersion;
        for step in 0..dispersion {
            let Some(j) = self.target(x + direction, y, m) else {
                if step == 0 {
                    self.flow[i] = -direction as i8;
                }
                break;
            };
            self.swap(i, j);
            i = j;
            x += direction;
            moved = true;
            if self.target(x, y + 1, m).is_some() {
                break; // found a drop: fall next tick
            }
        }
        usize::from(moved)
    }
}

#[cfg(test)]
mod tests;
