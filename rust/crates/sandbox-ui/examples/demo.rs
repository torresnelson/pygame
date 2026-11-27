//! Demo of the shared layer: pixel text, boxes, buttons that light up under
//! any pointer (several fingers light several), pointer markers, and a canvas
//! that switches between landscape (400x350) and portrait (400x760).
//!
//!     cargo run -p sandbox-ui --example demo [-- --portrait]

use bevy::prelude::*;
use sandbox_ui::{BLACK, Orientation, PixelCanvas, Pointers, Rect, Rgb, SandboxPlugin};

const LANDSCAPE: (i32, i32) = (400, 350);
const PORTRAIT: (i32, i32) = (400, 760);
const WHITE: Rgb = (252, 252, 252);
const GOLD: Rgb = (248, 184, 0);
const BLUE: Rgb = (0, 88, 248);
const DIM: Rgb = (120, 120, 150);

fn main() {
    let portrait = std::env::args().any(|arg| arg == "--portrait");
    let (width, height) = if portrait { PORTRAIT } else { LANDSCAPE };
    sandbox_ui::game_app("Sandbox UI demo", width as u32 * 2, height as u32 * 2)
        .add_plugins(SandboxPlugin {
            canvas_size: (width, height),
            scanlines: true,
        })
        .add_systems(Update, draw)
        .run();
}

fn nes_box(canvas: &mut sandbox_ui::Canvas, rect: Rect) {
    canvas.fill_rect(rect, BLACK);
    canvas.outline(rect, WHITE, 1);
    canvas.outline(
        Rect::new(rect.x + 2, rect.y + 2, rect.w - 4, rect.h - 4),
        BLUE,
        1,
    );
}

fn draw(
    mut pixel: ResMut<PixelCanvas>,
    orientation: Res<Orientation>,
    pointers: Res<Pointers>,
    window: Single<&Window>,
    mut taps: Local<usize>,
) {
    let (width, height) = match *orientation {
        Orientation::Landscape => LANDSCAPE,
        Orientation::Portrait => PORTRAIT,
    };
    if pixel.canvas.size() != (width, height) {
        info!(
            "{orientation:?}: canvas {width}x{height}, window {} at scale {}",
            window.size(),
            window.scale_factor()
        );
        pixel.canvas.resize(width, height);
    }
    *taps += pointers.released.len();
    for pointer in &pointers.pressed {
        info!("pressed {:?} at canvas {:?}", pointer.id, pointer.pos);
    }

    let canvas = &mut pixel.canvas;
    canvas.fill(BLACK);
    canvas.text(
        "SANDBOX UI",
        (width / 2, 30),
        GOLD,
        4,
        Some((90, 60, 0)),
        true,
    );
    let label = match *orientation {
        Orientation::Landscape => "LANDSCAPE",
        Orientation::Portrait => "PORTRAIT",
    };
    canvas.text(
        &format!("{label} {width}X{height}"),
        (width / 2, 62),
        DIM,
        1,
        None,
        true,
    );

    let panel = Rect::new(20, 90, width - 40, 90);
    nes_box(canvas, panel);
    canvas.text(
        &format!("POINTERS {}", pointers.down.len()),
        (panel.x + 14, panel.y + 18),
        WHITE,
        2,
        None,
        false,
    );
    canvas.text(
        &format!("TAPS {}", *taps),
        (panel.x + 14, panel.y + 50),
        WHITE,
        2,
        None,
        false,
    );

    let buttons = touch::button_row(
        &[("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")],
        20,
        height - 100,
        width - 40,
        80,
        8,
    );
    for button in &buttons {
        let held = pointers.down.iter().any(|p| button.contains(p.pos));
        nes_box(canvas, button.rect);
        let center = (
            button.rect.x + button.rect.w / 2,
            button.rect.y + button.rect.h / 2,
        );
        canvas.text(
            button.label,
            center,
            if held { GOLD } else { WHITE },
            3,
            None,
            true,
        );
        if held {
            canvas.outline(button.rect, GOLD, 3);
        }
    }

    for pointer in &pointers.down {
        let (x, y) = pointer.pos;
        canvas.fill_rect(Rect::new(x - 6, y, 13, 1), GOLD);
        canvas.fill_rect(Rect::new(x, y - 6, 1, 13), GOLD);
    }
}
