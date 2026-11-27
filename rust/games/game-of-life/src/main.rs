//! Game of Life: Rust/bevy port of `src/game_of_life/game_of_life.py` (work in progress).
//!
//! Phase 1 placeholder: opens the game window and draws an accent square,
//! proving the window and renderer work natively and in the browser.

use bevy::prelude::*;

fn main() {
    sandbox_ui::game_app("Game of Life", 649, 741)
        .add_systems(Startup, setup)
        .run();
}

fn setup(mut commands: Commands) {
    commands.spawn(Camera2d);
    commands.spawn(Sprite::from_color(
        Color::srgb_u8(120, 200, 255),
        Vec2::splat(120.0),
    ));
}
