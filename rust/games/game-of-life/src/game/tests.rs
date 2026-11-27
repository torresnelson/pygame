//! Ports of `tests/test_game_of_life_ui.py`, plus behaviour tests.

use super::*;
use std::collections::HashSet;

#[test]
fn wrap_greedily() {
    assert!(wrap("", 10).is_empty());
    assert_eq!(wrap("one", 10), ["one"]);
    assert_eq!(
        wrap("fires a new glider every 30", 10),
        ["fires a", "new glider", "every 30"]
    );
    assert_eq!(
        wrap("supercalifragilistic word", 5),
        ["supercalifragilistic", "word"]
    );
}

#[test]
fn every_description_fits_the_preview_column() {
    for pattern in CATALOGUE {
        assert!(
            wrap(pattern.description, 17)
                .iter()
                .all(|l| l.len() <= DESCRIPTION_CHARS)
        );
    }
}

#[test]
fn status_text_matches_python() {
    assert_eq!(status_text(127, 58, 60, true), "GEN 127  POP 58  60/S  RUN");
    assert!(status_text(0, 0, 10, false).ends_with("PAUSE"));
}

#[test]
fn menu_index_at_maps_rows() {
    for i in 0..CATALOGUE.len() {
        assert_eq!(
            menu_index_at((40, MENU_TOP + i as i32 * MENU_ROW + 4)),
            Some(i)
        );
    }
    assert_eq!(menu_index_at((PREVIEW.x + 5, MENU_TOP)), None);
    assert_eq!(
        menu_index_at((40, MENU_TOP + CATALOGUE.len() as i32 * MENU_ROW + 10)),
        None
    );
}

#[test]
fn pick_tap_mouse_starts_touch_only_selects() {
    assert_eq!(pick_tap(3, false), (3, true));
    assert_eq!(pick_tap(3, true), (3, false));
}

fn inside(rect: Rect, size: (i32, i32)) -> bool {
    rect.x >= 0 && rect.y >= 0 && rect.x + rect.w <= size.0 && rect.y + rect.h <= size.1
}

fn overlaps(a: Rect, b: Rect) -> bool {
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

#[test]
fn layout_buttons_fit_below_the_board_without_overlapping() {
    for layout in [landscape(), portrait()] {
        for button in &layout.buttons {
            assert!(
                inside(button.rect, layout.size),
                "{} {}",
                layout.name,
                button.action
            );
            assert!(button.rect.y >= BOARD_SIZE + STATUS_HEIGHT);
        }
        for (i, a) in layout.buttons.iter().enumerate() {
            for b in &layout.buttons[i + 1..] {
                assert!(!overlaps(a.rect, b.rect), "{} {}", a.action, b.action);
            }
        }
        let actions: HashSet<&str> = layout.buttons.iter().map(|b| b.action).collect();
        assert_eq!(actions, BOARD_ACTIONS.iter().map(|&(a, _)| a).collect());
    }
}

#[test]
fn start_button_is_clear_of_the_menu_and_descriptions() {
    let longest = CATALOGUE
        .iter()
        .map(|p| wrap(p.description, DESCRIPTION_CHARS).len())
        .max()
        .unwrap();
    let description_bottom = PREVIEW.y + PREVIEW.h + 16 + longest as i32 * DESCRIPTION_ROW;
    let menu_bottom = MENU_TOP + CATALOGUE.len() as i32 * MENU_ROW;
    for layout in [landscape(), portrait()] {
        let start = layout.start.rect;
        assert!(inside(start, layout.size));
        assert!(start.y >= description_bottom);
        assert!(start.y >= menu_bottom || start.x >= PREVIEW.x - 8);
        assert_eq!(menu_index_at((start.x + 2, start.y + 2)), None);
    }
}

#[test]
fn layouts_match_python_sizes() {
    assert_eq!(landscape().size, (649, 741));
    assert_eq!(portrait().size, (649, 1009));
    let tallest = portrait().buttons.iter().map(|b| b.rect.h).min().unwrap();
    assert!(tallest > 2 * landscape().buttons.iter().map(|b| b.rect.h).max().unwrap());
}

fn press(game: &mut Game, pos: (i32, i32), touch: bool, layout: &Layout) {
    game.handle(Event::Press { pos, touch }, layout);
}

fn board(game: &Game) -> &Board {
    match &game.screen {
        Screen::Board(board) => board,
        Screen::Picker { .. } => panic!("still on the picker"),
    }
}

fn row(index: usize) -> (i32, i32) {
    (40, MENU_TOP + index as i32 * MENU_ROW + 4)
}

#[test]
fn touch_selects_then_start_loads_mouse_click_starts() {
    let layout = landscape();
    let mut game = Game::new(true, 1);
    press(&mut game, row(2), true, &layout);
    press(&mut game, row(2), true, &layout); // a second tap still only selects
    assert!(matches!(game.screen, Screen::Picker { selected: 2 }));
    let start = layout.start.rect;
    press(&mut game, (start.x + 5, start.y + 5), true, &layout);
    assert_eq!(board(&game).pattern, 2);

    let mut game = Game::new(false, 1);
    game.handle(Event::Hover(row(5)), &layout);
    assert!(matches!(game.screen, Screen::Picker { selected: 5 }));
    press(&mut game, row(5), false, &layout);
    assert_eq!(board(&game).pattern, 5);
}

#[test]
fn keys_move_the_selection_and_escape_quits_only_on_desktop() {
    let layout = landscape();
    let mut game = Game::new(false, 1);
    assert_eq!(game.handle(Event::Key(Key::Up), &layout), Outcome::Continue);
    assert!(matches!(game.screen, Screen::Picker { selected: 12 }));
    assert_eq!(game.handle(Event::Key(Key::Escape), &layout), Outcome::Quit);
    let mut web = Game::new(true, 1);
    assert_eq!(
        web.handle(Event::Key(Key::Escape), &layout),
        Outcome::Continue
    );
}

#[test]
fn board_runs_steps_and_stops_when_everything_dies() {
    let layout = landscape();
    let mut game = Game::new(false, 1);
    game.handle(Event::Key(Key::Down), &layout);
    game.handle(Event::Key(Key::Down), &layout); // blinker
    game.handle(Event::Key(Key::Enter), &layout);
    assert_eq!(board(&game).cells.len(), 3);

    game.handle(Event::Key(Key::Step), &layout);
    game.update(0);
    assert_eq!(board(&game).generation, 1);

    game.handle(Event::Key(Key::Space), &layout);
    assert!(board(&game).running);
    game.update(1000); // 10/s: due
    game.update(1050); // not yet
    assert_eq!(board(&game).generation, 2);
    game.handle(Event::Key(Key::Faster), &layout);
    assert_eq!(board(&game).speed, DEFAULT_SPEED + 1);

    // Clearing stops it; running an empty board does nothing.
    game.handle(Event::Key(Key::Clear), &layout);
    assert!(board(&game).cells.is_empty() && !board(&game).running);
    game.handle(Event::Key(Key::Space), &layout);
    assert!(!board(&game).running);
}

#[test]
fn tapping_cells_toggles_them_only_while_paused() {
    let layout = landscape();
    let mut game = Game::new(false, 1);
    for _ in 0..12 {
        game.handle(Event::Key(Key::Down), &layout); // empty board
    }
    game.handle(Event::Key(Key::Enter), &layout);
    press(&mut game, (SIZE + GAP + 1, 1), true, &layout);
    assert!(board(&game).cells.contains(&(0, 1)));
    game.handle(Event::Key(Key::Space), &layout);
    press(&mut game, (1, 1), true, &layout);
    assert!(!board(&game).cells.contains(&(0, 0)));
}

#[test]
fn back_returns_to_the_picker_on_the_same_pattern() {
    let layout = portrait();
    let mut game = Game::new(true, 1);
    game.handle(Event::Key(Key::Down), &layout);
    game.handle(Event::Key(Key::Enter), &layout);
    let back = layout
        .buttons
        .iter()
        .find(|b| b.action == "back")
        .unwrap()
        .rect;
    press(&mut game, (back.x + 5, back.y + 5), true, &layout);
    assert!(matches!(game.screen, Screen::Picker { selected: 1 }));
}

#[test]
fn draws_the_picker_and_the_board() {
    let layout = landscape();
    let mut canvas = Canvas::new(layout.size.0, layout.size.1);
    let mut game = Game::new(false, 1);
    game.draw(&mut canvas, &layout);
    // Selected row highlight and the preview frame.
    assert_eq!(canvas.get(14, MENU_TOP - 8), Some(HIGHLIGHT));
    assert_eq!(canvas.get(PREVIEW.x, PREVIEW.y), Some(MUTED));

    game.handle(Event::Key(Key::Enter), &layout); // glider
    game.draw(&mut canvas, &layout);
    let (row, column) = *board(&game).cells.iter().next().unwrap();
    let pitch = SIZE + GAP;
    assert_eq!(
        canvas.get(column * pitch + 1, row * pitch + 1),
        Some(ALIVE_CELL)
    );
    assert_eq!(canvas.get(1, 1), Some(DEAD_CELL));
}
