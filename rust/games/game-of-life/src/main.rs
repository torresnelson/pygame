//! Game of Life: Rust/bevy port of `src/game_of_life/game_of_life.py`.
//!
//! Start screen: up/down (or click) to pick a pattern, enter or START to load
//! it; on a touch screen a tap previews and START loads. Board: space
//! run/pause, n step, click toggles cells while paused, +/- speed, r reload,
//! c clear, esc back. The buttons under the board do the same. A window (or
//! phone) taller than wide gets the portrait layout; `--portrait` opens one.

mod game;

use bevy::prelude::*;
use game::{Event, Game, Key, Layout, Outcome};
use sandbox_ui::{Orientation, PixelCanvas, PointerId, Pointers, SandboxPlugin};

#[derive(Resource)]
struct Life {
    game: Game,
    landscape: Layout,
    portrait: Layout,
}

const KEYS: [(KeyCode, Key); 14] = [
    (KeyCode::ArrowUp, Key::Up),
    (KeyCode::KeyK, Key::Up),
    (KeyCode::ArrowDown, Key::Down),
    (KeyCode::KeyJ, Key::Down),
    (KeyCode::Enter, Key::Enter),
    (KeyCode::NumpadEnter, Key::Enter),
    (KeyCode::Space, Key::Space),
    (KeyCode::Escape, Key::Escape),
    (KeyCode::KeyN, Key::Step),
    (KeyCode::Equal, Key::Faster),
    (KeyCode::NumpadAdd, Key::Faster),
    (KeyCode::Minus, Key::Slower),
    (KeyCode::NumpadSubtract, Key::Slower),
    (KeyCode::KeyR, Key::Reset),
];

fn main() {
    let web = cfg!(target_arch = "wasm32");
    let portrait = !web && std::env::args().any(|arg| arg == "--portrait");
    let life = Life {
        game: Game::new(web, sandbox_ui::clock::seed()),
        landscape: game::landscape(),
        portrait: game::portrait(),
    };
    let (width, height) = if portrait {
        life.portrait.size
    } else {
        life.landscape.size
    };
    sandbox_ui::game_app("Game of Life", width as u32, height as u32)
        .add_plugins(SandboxPlugin {
            canvas_size: (width, height),
            scanlines: false,
        })
        .insert_resource(life)
        .add_systems(Update, play)
        .run();
}

fn play(
    mut life: ResMut<Life>,
    mut pixel: ResMut<PixelCanvas>,
    mut exit: MessageWriter<AppExit>,
    keys: Res<ButtonInput<KeyCode>>,
    pointers: Res<Pointers>,
    orientation: Res<Orientation>,
) {
    let Life {
        game,
        landscape,
        portrait,
    } = &mut *life;
    let layout = match *orientation {
        Orientation::Landscape => &*landscape,
        Orientation::Portrait => &*portrait,
    };

    let mut events: Vec<Event> = KEYS
        .iter()
        .filter(|(code, _)| keys.just_pressed(*code))
        .map(|&(_, key)| Event::Key(key))
        .collect();
    if keys.just_pressed(KeyCode::KeyC) {
        events.push(Event::Key(Key::Clear));
    }
    if pointers.is_changed()
        && let Some(pos) = pointers.hover
    {
        events.push(Event::Hover(pos));
    }
    events.extend(
        pointers
            .pressed
            .iter()
            .filter(|p| p.id != PointerId::MouseRight)
            .map(|p| Event::Press {
                pos: p.pos,
                touch: p.id.is_touch(),
            }),
    );
    for event in events {
        if game.handle(event, layout) == Outcome::Quit {
            exit.write(AppExit::Success);
        }
    }
    game.update(pointers.now_ms);

    if pixel.canvas.size() != layout.size {
        pixel.canvas.resize(layout.size.0, layout.size.1);
    }
    game.draw(&mut pixel.canvas, layout);
}
