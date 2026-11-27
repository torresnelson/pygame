//! Shared bevy setup for the sandbox games.
//!
//! Phase 1 only builds the window; later phases add the pixel camera, text,
//! buttons, layouts, pointers and storage (see `plans/claude/rust-rewrite.md`).

use bevy::prelude::*;
use bevy::window::WindowResolution;

/// The `<canvas>` the web page renders into.
pub const CANVAS_SELECTOR: &str = "#bevy";

/// Window settings shared by every game.
///
/// In the browser the canvas fills its parent and keeps touch gestures for
/// the game instead of scrolling or zooming the page.
pub fn game_window(title: &str, width: u32, height: u32) -> Window {
    Window {
        title: title.to_owned(),
        resolution: WindowResolution::new(width, height),
        canvas: Some(CANVAS_SELECTOR.to_owned()),
        fit_canvas_to_parent: true,
        prevent_default_event_handling: true,
        ..default()
    }
}

/// A bevy app with the default plugins, the shared window and a black background.
pub fn game_app(title: &str, width: u32, height: u32) -> App {
    let mut app = App::new();
    app.add_plugins(DefaultPlugins.set(WindowPlugin {
        primary_window: Some(game_window(title, width, height)),
        ..default()
    }))
    .insert_resource(ClearColor(Color::BLACK));
    app
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn game_window_fills_the_page_canvas_and_keeps_touches() {
        let window = game_window("Tetris", 800, 700);
        assert_eq!(window.title, "Tetris");
        assert_eq!(window.canvas.as_deref(), Some("#bevy"));
        assert!(window.fit_canvas_to_parent);
        assert!(window.prevent_default_event_handling);
        assert_eq!(window.resolution.physical_width(), 800);
        assert_eq!(window.resolution.physical_height(), 700);
    }
}
