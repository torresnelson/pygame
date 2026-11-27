//! Shared bevy layer for the sandbox games.
//!
//! Games draw each frame on a CPU [`Canvas`] (like the pygame versions), which
//! [`SandboxPlugin`] shows scaled with hard pixel edges and letterboxed to the
//! window. It also provides [`Pointers`] (mouse and multi-touch in canvas
//! pixels), the window [`Orientation`], small text saves ([`storage`]) and
//! removes the web page's loading screen on the first frame.

pub mod canvas;
pub mod clock;
pub mod display;
pub mod orientation;
pub mod pointer;
pub mod storage;
pub mod web;

pub use canvas::{BLACK, Canvas, Rgb};
pub use display::PixelCanvas;
pub use orientation::Orientation;
pub use pixelfont::Rect;
pub use pointer::{Pointer, PointerId, Pointers};

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

/// Canvas display, pointers, orientation and the loading-screen hook.
pub struct SandboxPlugin {
    pub canvas_size: (i32, i32),
    pub scanlines: bool,
}

impl Plugin for SandboxPlugin {
    fn build(&self, app: &mut App) {
        let (width, height) = self.canvas_size;
        app.insert_resource(PixelCanvas {
            canvas: Canvas::new(width, height),
            scanlines: self.scanlines,
        })
        .add_plugins((display::plugin, pointer::plugin, orientation::plugin))
        .add_systems(Last, hide_loading_once);
    }
}

fn hide_loading_once(mut done: Local<bool>) {
    if !*done {
        web::hide_loading();
        *done = true;
    }
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
