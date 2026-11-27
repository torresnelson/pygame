//! Tetris: Rust/bevy port of `src/tetris/tetris.py` (work in progress).
//!
//! Phase 1 placeholder: opens the game window and draws an accent square,
//! proving the window and renderer work natively and in the browser.

use bevy::prelude::*;

fn main() {
    sandbox_ui::game_app("Tetris", 800, 700)
        .add_systems(Startup, setup)
        .run();
}

fn setup(mut commands: Commands) {
    commands.spawn(Camera2d);
    commands.spawn(Sprite::from_color(
        Color::srgb_u8(248, 184, 0),
        Vec2::splat(120.0),
    ));
}
