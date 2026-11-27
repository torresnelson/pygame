//! On-screen buttons and drag gestures (port of `src/shared/touch.py`), plus
//! the canvas fitting maths from `src/shared/browser.py`.
//!
//! Positions are in the game's virtual pixels; times in milliseconds.

pub use pixelfont::Rect;

pub type Point = (i32, i32);

/// Pixels a tap may wander before it counts as a drag.
pub const TAP_DISTANCE: i32 = 8;
pub const TAP_MS: u64 = 300;
pub const FLICK_DISTANCE: i32 = 30;
pub const FLICK_MS: u64 = 300;
/// A held button starts repeating after this long.
pub const REPEAT_DELAY_MS: u64 = 200;
pub const REPEAT_MS: u64 = 60;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Button {
    pub action: &'static str,
    pub label: &'static str,
    pub rect: Rect,
}

impl Button {
    pub const fn new(action: &'static str, label: &'static str, rect: Rect) -> Self {
        Self {
            action,
            label,
            rect,
        }
    }

    /// Half-open: the right and bottom edges belong to the next button.
    pub fn contains(&self, (x, y): Point) -> bool {
        let r = self.rect;
        r.x <= x && x < r.x + r.w && r.y <= y && y < r.y + r.h
    }
}

/// Action of the button under `pos`, if any.
pub fn button_at(buttons: &[Button], pos: Point) -> Option<&'static str> {
    buttons.iter().find(|b| b.contains(pos)).map(|b| b.action)
}

/// Lay `(action, label)` pairs out left to right in equal slots filling `width`.
pub fn button_row(
    specs: &[(&'static str, &'static str)],
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    gap: i32,
) -> Vec<Button> {
    let count = specs.len() as i32;
    let slot = (width - gap * (count - 1)).div_euclid(count);
    specs
        .iter()
        .enumerate()
        .map(|(i, &(action, label))| {
            Button::new(
                action,
                label,
                Rect::new(x + i as i32 * (slot + gap), y, slot, height),
            )
        })
        .collect()
}

/// One finger (or mouse button) press, from down to up.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Drag {
    pub start: Point,
    pub start_ms: u64,
    /// Where the last whole step was taken from.
    pub anchor: Point,
    pub moved: bool,
}

pub fn start_drag(pos: Point, now_ms: u64) -> Drag {
    Drag {
        start: pos,
        start_ms: now_ms,
        anchor: pos,
        moved: false,
    }
}

/// Whole `step`s moved since the anchor as (columns, rows down); advances the anchor.
///
/// Upward movement never produces rows, so only falling is ever requested.
pub fn drag_steps(drag: &mut Drag, pos: Point, step: i32) -> (i32, i32) {
    // Integer division truncates toward zero, like Python's int(dx / step).
    let columns = (pos.0 - drag.anchor.0) / step;
    let rows = ((pos.1 - drag.anchor.1) / step).max(0);
    if columns != 0 || rows != 0 {
        drag.anchor = (drag.anchor.0 + columns * step, drag.anchor.1 + rows * step);
        drag.moved = true;
    }
    (columns, rows)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Gesture {
    Tap,
    FlickDown,
}

/// Classify the end of a press: a tap, a downward flick, or nothing.
pub fn release_gesture(drag: &Drag, pos: Point, now_ms: u64) -> Option<Gesture> {
    let (dx, dy) = (pos.0 - drag.start.0, pos.1 - drag.start.1);
    let elapsed = now_ms.saturating_sub(drag.start_ms);
    if dy >= FLICK_DISTANCE && dy.abs() > 2 * dx.abs() && elapsed <= FLICK_MS {
        return Some(Gesture::FlickDown);
    }
    let small = dx.abs() <= TAP_DISTANCE && dy.abs() <= TAP_DISTANCE;
    if !drag.moved && small && elapsed <= TAP_MS {
        return Some(Gesture::Tap);
    }
    None
}

/// Repeats a button held for `held_ms` should have fired so far (not counting the press).
pub fn repeats(held_ms: u64, delay: u64, interval: u64) -> u64 {
    if held_ms < delay {
        0
    } else {
        1 + (held_ms - delay) / interval
    }
}

/// Largest box with the aspect of `width` x `height` centred in the outer box,
/// as (x, y, w, h).
pub fn fit_box(outer_w: f32, outer_h: f32, width: f32, height: f32) -> (f32, f32, f32, f32) {
    let scale = (outer_w / width).min(outer_h / height);
    let (w, h) = (width * scale, height * scale);
    ((outer_w - w) / 2.0, (outer_h - h) / 2.0, w, h)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn button_contains_is_half_open() {
        let button = Button::new("go", "GO", Rect::new(10, 20, 30, 40));
        assert!(button.contains((10, 20)));
        assert!(button.contains((39, 59)));
        assert!(!button.contains((40, 20)));
        assert!(!button.contains((10, 60)));
    }

    #[test]
    fn button_row_fills_the_width_without_overlap() {
        let row = button_row(&[("a", "A"), ("b", "B"), ("c", "C")], 8, 100, 300, 40, 6);
        let actions: Vec<&str> = row.iter().map(|b| b.action).collect();
        assert_eq!(actions, ["a", "b", "c"]);
        assert!(row.iter().all(|b| b.rect.y == 100 && b.rect.h == 40));
        for pair in row.windows(2) {
            assert_eq!(pair[0].rect.x + pair[0].rect.w + 6, pair[1].rect.x);
        }
        let last = row.last().unwrap().rect;
        assert!(last.x + last.w <= 8 + 300);
    }

    #[test]
    fn button_at_finds_the_button_under_a_point() {
        let row = button_row(&[("a", "A"), ("b", "B")], 0, 0, 100, 10, 0);
        assert_eq!(button_at(&row, (5, 5)), Some("a"));
        assert_eq!(button_at(&row, (55, 5)), Some("b"));
        assert_eq!(button_at(&row, (55, 15)), None);
    }

    #[test]
    fn drag_steps_moves_whole_steps_and_keeps_the_remainder() {
        let mut drag = start_drag((100, 100), 0);
        assert_eq!(drag_steps(&mut drag, (110, 100), 15), (0, 0));
        assert!(!drag.moved);
        assert_eq!(drag_steps(&mut drag, (132, 100), 15), (2, 0));
        assert!(drag.moved);
        assert_eq!(drag.anchor, (130, 100));
        assert_eq!(drag_steps(&mut drag, (114, 100), 15), (-1, 0));
    }

    #[test]
    fn drag_steps_never_moves_up() {
        let mut drag = start_drag((100, 100), 0);
        assert_eq!(drag_steps(&mut drag, (100, 40), 15), (0, 0));
        assert_eq!(drag_steps(&mut drag, (100, 131), 15), (0, 2));
    }

    #[test]
    fn release_gesture_classifies_presses() {
        let cases: [(Point, u64, Option<Gesture>); 6] = [
            ((102, 103), 100, Some(Gesture::Tap)),
            ((102, 103), 1000, None), // a long press is not a tap
            ((100, 160), 150, Some(Gesture::FlickDown)),
            ((100, 160), FLICK_MS + 200, None), // a slow drag is not a flick
            ((150, 160), 150, None),            // too diagonal
            ((100, 40), 150, None),             // flicking up does nothing
        ];
        for (end, elapsed, gesture) in cases {
            assert_eq!(
                release_gesture(&start_drag((100, 100), 0), end, elapsed),
                gesture
            );
        }
    }

    #[test]
    fn a_drag_that_moved_the_piece_is_not_a_tap() {
        let mut drag = start_drag((100, 100), 0);
        drag_steps(&mut drag, (116, 100), 15);
        assert_eq!(release_gesture(&drag, (100, 100), 50), None);
    }

    #[test]
    fn repeats_wait_for_the_delay_then_tick() {
        assert_eq!(repeats(0, 200, 60), 0);
        assert_eq!(repeats(199, 200, 60), 0);
        assert_eq!(repeats(200, 200, 60), 1);
        assert_eq!(repeats(259, 200, 60), 1);
        assert_eq!(repeats(260, 200, 60), 2);
    }

    fn approx(a: (f32, f32, f32, f32), b: (f32, f32, f32, f32)) -> bool {
        [a.0 - b.0, a.1 - b.1, a.2 - b.2, a.3 - b.3]
            .iter()
            .all(|d| d.abs() <= 0.6)
    }

    #[test]
    fn fit_box_keeps_the_aspect_and_centres() {
        // Portrait phone, portrait tetris: fills the width, centred vertically.
        let portrait = fit_box(390.0, 844.0, 800.0, 1520.0);
        assert!(
            approx(portrait, (0.0, (844.0 - 741.0) / 2.0, 390.0, 741.0)),
            "{portrait:?}"
        );
        // Landscape phone, landscape tetris: fills the height, centred horizontally.
        let landscape = fit_box(844.0, 390.0, 800.0, 700.0);
        let width = 390.0 * 800.0 / 700.0;
        assert!(
            approx(landscape, ((844.0 - width) / 2.0, 0.0, width, 390.0)),
            "{landscape:?}"
        );
        assert!(approx(
            fit_box(800.0, 700.0, 800.0, 700.0),
            (0.0, 0.0, 800.0, 700.0)
        ));
    }
}
