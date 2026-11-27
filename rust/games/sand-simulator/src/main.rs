//! Sand Simulator: Rust/bevy port of `src/sand_simulator/sand_simulator.py`.
//!
//! Left mouse (or a finger) paints the selected tool, right mouse erases;
//! 1 sand, 2 water, 3 stone, 4 eraser, wheel or [ ] brush size, space pause,
//! c clear, esc menu. The toolbar under the world does the same. Every finger
//! that goes down in the world paints, so one can paint while another taps
//! the toolbar. A window (or phone) taller than wide gets the portrait
//! layout and keeps the sand when turned; `--portrait` opens one.

mod game;

use bevy::input::mouse::{MouseScrollUnit, MouseWheel};
use bevy::prelude::*;
use game::{Event, Game, Layout, Paint};
use sandbox_ui::{Orientation, PixelCanvas, PointerId, Pointers, SandboxPlugin};

#[derive(Resource)]
struct Sand {
    game: Game,
    landscape: Layout,
    portrait: Layout,
    current: Orientation,
    fps: f32,
}

const KEYS: [(KeyCode, &str); 9] = [
    (KeyCode::Digit1, "sand"),
    (KeyCode::Digit2, "water"),
    (KeyCode::Digit3, "stone"),
    (KeyCode::Digit4, "erase"),
    (KeyCode::BracketLeft, "smaller"),
    (KeyCode::BracketRight, "bigger"),
    (KeyCode::Space, "pause"),
    (KeyCode::KeyC, "clear"),
    (KeyCode::Escape, "menu"),
];

fn main() {
    let web = cfg!(target_arch = "wasm32");
    let portrait = !web && std::env::args().any(|arg| arg == "--portrait");
    let sand = Sand {
        game: Game::new(web, sandbox_ui::clock::seed()),
        landscape: game::landscape(),
        portrait: game::portrait(),
        current: if portrait {
            Orientation::Portrait
        } else {
            Orientation::Landscape
        },
        fps: 60.0,
    };
    let (width, height) = if portrait {
        sand.portrait.size
    } else {
        sand.landscape.size
    };
    sandbox_ui::game_app("Sand Simulator", width as u32, height as u32)
        .add_plugins(SandboxPlugin {
            canvas_size: (width, height),
            scanlines: false,
        })
        .insert_resource(sand)
        .add_systems(Update, play)
        .run();
}

fn play(
    mut sand: ResMut<Sand>,
    mut pixel: ResMut<PixelCanvas>,
    mut wheel: MessageReader<MouseWheel>,
    keys: Res<ButtonInput<KeyCode>>,
    pointers: Res<Pointers>,
    orientation: Res<Orientation>,
    time: Res<Time>,
) {
    let Sand {
        game,
        landscape,
        portrait,
        current,
        fps,
    } = &mut *sand;
    let layout = match *orientation {
        Orientation::Landscape => &*landscape,
        Orientation::Portrait => &*portrait,
    };
    if *current != *orientation {
        *current = *orientation;
        game.relayout(layout);
    }

    let mut events: Vec<Event> = keys
        .get_just_pressed()
        .map(|code| {
            Event::Key(
                KEYS.iter()
                    .find(|(key, _)| key == code)
                    .map(|&(_, action)| action),
            )
        })
        .collect();
    for scroll in wheel.read() {
        let steps = match scroll.unit {
            MouseScrollUnit::Line => scroll.y.signum() as i32,
            MouseScrollUnit::Pixel => (scroll.y / 40.0) as i32,
        };
        if steps != 0 {
            events.push(Event::Wheel(steps));
        }
    }
    events.extend(
        pointers
            .pressed
            .iter()
            .filter(|p| p.id != PointerId::MouseRight)
            .map(|p| Event::Press(p.pos)),
    );
    game.now_ms = pointers.now_ms;
    for event in events {
        game.handle(event, layout);
    }

    let paints: Vec<Paint> = pointers
        .down
        .iter()
        .filter(|p| layout.in_world(p.start))
        .map(|p| Paint {
            pos: p.pos,
            erase: p.id == PointerId::MouseRight,
            start_ms: p.start_ms,
        })
        .collect();
    game.update(&paints);

    let delta = time.delta_secs();
    if delta > 0.0 {
        *fps += (1.0 / delta - *fps) * 0.1;
    }
    if pixel.canvas.size() != layout.size {
        pixel.canvas.resize(layout.size.0, layout.size.1);
    }
    game.draw(&mut pixel.canvas, layout, pointers.now_ms, *fps);
}
