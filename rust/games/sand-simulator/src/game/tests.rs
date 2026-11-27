//! Ports of `tests/test_sand_ui.py`, plus behaviour tests.

use super::*;
use std::collections::HashSet;

const KEY_ACTIONS: [&str; 9] = [
    "sand", "water", "stone", "erase", "smaller", "bigger", "pause", "clear", "menu",
];

#[test]
fn status_text_matches_python() {
    assert_eq!(
        status_text(Material::Sand, 3, 59.6, false),
        "SAND  BRUSH 3  60 FPS"
    );
    assert!(status_text(Material::Water, 0, 30.0, true).ends_with("PAUSED"));
    assert!(status_text(Material::Empty, 2, 60.0, false).starts_with("ERASER"));
}

#[test]
fn hud_text_only_uses_characters_the_pixel_font_can_draw() {
    let charset: HashSet<char> = pixelfont::charset().collect();
    let mut texts = vec![
        HELP.to_owned(),
        status_text(Material::Stone, 12, 60.0, true),
        "TAP TO START".into(),
        "PLAY".into(),
    ];
    texts.extend(landscape().toolbar.iter().map(|b| b.label.to_owned()));
    for text in texts {
        assert!(
            text.to_uppercase().chars().all(|c| charset.contains(&c)),
            "{text}"
        );
    }
}

fn overlaps(a: Rect, b: Rect) -> bool {
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

#[test]
fn toolbars_fit_below_the_world_without_overlapping() {
    for layout in [landscape(), portrait()] {
        let (width, height) = layout.size;
        for button in &layout.toolbar {
            let r = button.rect;
            assert!(
                r.y >= layout.world_size.1,
                "{} {}",
                layout.name,
                button.action
            );
            assert!(r.x >= 0 && r.x + r.w <= width && r.y + r.h <= height);
            assert!(!layout.in_world((r.x + 1, r.y + 1)));
        }
        for (i, a) in layout.toolbar.iter().enumerate() {
            for b in &layout.toolbar[i + 1..] {
                assert!(!overlaps(a.rect, b.rect), "{} {}", a.action, b.action);
            }
        }
        let actions: HashSet<&str> = layout.toolbar.iter().map(|b| b.action).collect();
        assert_eq!(actions, KEY_ACTIONS.into_iter().collect());
    }
}

#[test]
fn layouts_match_python() {
    assert_eq!(landscape().size, (800, 664));
    assert_eq!(portrait().size, (600, 1044));
    let (lc, lr) = landscape().cells();
    let (pc, pr) = portrait().cells();
    assert_eq!(lc * lr, pc * pr); // same cell count: same speed
    let tallest = portrait().toolbar.iter().map(|b| b.rect.h).min().unwrap();
    assert!(tallest > 2 * landscape().toolbar.iter().map(|b| b.rect.h).max().unwrap());
}

#[test]
fn in_world_depends_on_the_layout() {
    assert!(landscape().in_world((700, 100)));
    assert!(!portrait().in_world((700, 100)));
    assert!(portrait().in_world((100, 700)));
    assert!(!landscape().in_world((100, 700)));
}

#[test]
fn resize_brush_is_clamped() {
    assert_eq!(resize_brush(3, "bigger"), 4);
    assert_eq!(resize_brush(3, "smaller"), 2);
    assert_eq!(resize_brush(MAX_BRUSH, "bigger"), MAX_BRUSH);
    assert_eq!(resize_brush(MIN_BRUSH, "smaller"), MIN_BRUSH);
}

#[test]
fn every_tool_can_paint() {
    for (action, tool) in TOOLS {
        assert_eq!(tool_for(action), Some(tool));
        assert!(fill(tool) > 0.0);
    }
    assert_eq!(tool_name(Material::Empty), "eraser");
}

fn sandbox(game: &Game) -> &Sandbox {
    match &game.screen {
        Screen::Sandbox(sandbox) => sandbox,
        Screen::Title => panic!("still on the title"),
    }
}

fn button(layout: &Layout, action: &str) -> (i32, i32) {
    let r = layout
        .toolbar
        .iter()
        .find(|b| b.action == action)
        .unwrap()
        .rect;
    (r.x + r.w / 2, r.y + r.h / 2)
}

#[test]
fn a_press_starts_then_toolbar_and_keys_change_the_tool() {
    let layout = landscape();
    let mut game = Game::new(true, 1);
    game.handle(Event::Press((10, 10)), &layout);
    assert_eq!(sandbox(&game).tool, Material::Sand);
    game.handle(Event::Press(button(&layout, "water")), &layout);
    assert_eq!(sandbox(&game).tool, Material::Water);
    game.handle(Event::Key(Some("erase")), &layout);
    assert_eq!(sandbox(&game).tool, Material::Empty);
    // A press inside the world never triggers a button.
    game.handle(Event::Press((10, 10)), &layout);
    assert_eq!(sandbox(&game).tool, Material::Empty);
    game.handle(Event::Wheel(20), &layout);
    assert_eq!(sandbox(&game).brush, MAX_BRUSH);
    game.handle(Event::Key(Some("menu")), &layout);
    assert!(matches!(game.screen, Screen::Title));
}

#[test]
fn painting_pours_sand_and_the_right_button_erases() {
    let layout = landscape();
    let mut game = Game::new(false, 1);
    game.handle(Event::Key(None), &layout); // any key starts
    game.handle(Event::Key(Some("pause")), &layout);
    for _ in 0..10 {
        game.update(&[Paint {
            pos: (400, 300),
            erase: false,
            start_ms: 1,
        }]);
    }
    let poured = sandbox(&game).world.count(Material::Sand);
    assert!(poured > 10, "{poured}");
    game.update(&[Paint {
        pos: (400, 300),
        erase: true,
        start_ms: 1,
    }]);
    assert!(sandbox(&game).world.count(Material::Sand) < poured);
}

#[test]
fn pause_stops_the_physics() {
    let layout = landscape();
    let mut game = Game::new(false, 1);
    game.handle(Event::Key(None), &layout);
    game.update(&[Paint {
        pos: (400, 5),
        erase: false,
        start_ms: 1,
    }]);
    game.handle(Event::Key(Some("pause")), &layout);
    let before = sandbox(&game).world.material.clone();
    game.update(&[]);
    assert_eq!(sandbox(&game).world.material, before);
}

#[test]
fn turning_the_phone_keeps_the_sand() {
    let mut game = Game::new(true, 1);
    game.handle(Event::Press((10, 10)), &landscape());
    for _ in 0..200 {
        game.update(&[Paint {
            pos: (100, 300),
            erase: false,
            start_ms: 1,
        }]);
    }
    let grains = sandbox(&game).world.count(Material::Sand);
    game.relayout(&portrait());
    let world = &sandbox(&game).world;
    assert_eq!((world.width, world.height), portrait().cells());
    // Bottom-left aligned: the pile near x = 20 cells fits the narrower world.
    assert_eq!(world.count(Material::Sand), grains);
}

#[test]
fn draws_the_world_toolbar_and_title() {
    let layout = landscape();
    let mut canvas = Canvas::new(layout.size.0, layout.size.1);
    let mut game = Game::new(false, 1);
    game.draw(&mut canvas, &layout, 0, 60.0);
    assert_eq!(canvas.get(0, layout.size.1 - 1), Some(BLACK));

    game.handle(Event::Key(None), &layout);
    if let Screen::Sandbox(sandbox) = &mut game.screen {
        sandbox.world.set(10, 100, Material::Stone);
    }
    game.draw(&mut canvas, &layout, 0, 60.0);
    let stone = canvas.get(10 * CELL_SIZE + 2, 100 * CELL_SIZE + 2).unwrap();
    assert_ne!(stone, BACKGROUND);
    assert_eq!(canvas.get(0, 0), Some(BACKGROUND));
    // The selected tool's button is highlighted.
    let (x, y) = button(&layout, "sand");
    assert_eq!(canvas.get(x - 20, y + 10), Some(BUTTON_ACTIVE));
}

#[test]
fn the_tap_that_opens_the_sandbox_does_not_paint() {
    let layout = landscape();
    let mut game = Game::new(true, 1);
    game.now_ms = 500;
    game.handle(Event::Press((400, 300)), &layout);
    game.handle(Event::Key(Some("pause")), &layout);
    // Still held: same press, started at 500.
    game.update(&[Paint {
        pos: (400, 300),
        erase: false,
        start_ms: 500,
    }]);
    assert_eq!(sandbox(&game).world.count(Material::Sand), 0);
    // A new press paints.
    game.update(&[Paint {
        pos: (400, 300),
        erase: false,
        start_ms: 900,
    }]);
    assert!(sandbox(&game).world.count(Material::Sand) > 0);
}
