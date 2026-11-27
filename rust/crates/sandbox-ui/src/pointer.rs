//! Mouse and touch input as one list of pointers in canvas pixels.
//!
//! Every finger is its own pointer with its own id, so games can follow
//! several at once (multi-touch); the mouse's left and right buttons are
//! pointers too.

use bevy::input::InputSystems;
use bevy::input::touch::Touches;
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

use crate::display::PixelCanvas;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PointerId {
    MouseLeft,
    MouseRight,
    Touch(u64),
}

impl PointerId {
    pub fn is_touch(self) -> bool {
        matches!(self, PointerId::Touch(_))
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Pointer {
    pub id: PointerId,
    /// Current position in canvas pixels (may be outside the canvas).
    pub pos: (i32, i32),
    /// Where the press started.
    pub start: (i32, i32),
    pub start_ms: u64,
}

/// This frame's pointers. `pressed` and `released` only hold pointers that
/// went down or up this frame; `down` holds every pointer still pressed.
#[derive(Resource, Debug, Default)]
pub struct Pointers {
    pub down: Vec<Pointer>,
    pub pressed: Vec<Pointer>,
    pub released: Vec<Pointer>,
    /// Milliseconds since the app started.
    pub now_ms: u64,
}

impl Pointers {
    pub fn get(&self, id: PointerId) -> Option<&Pointer> {
        self.down.iter().find(|p| p.id == id)
    }

    fn press(&mut self, id: PointerId, pos: (i32, i32)) {
        let pointer = Pointer {
            id,
            pos,
            start: pos,
            start_ms: self.now_ms,
        };
        self.down.retain(|p| p.id != id);
        self.down.push(pointer);
        self.pressed.push(pointer);
    }

    fn move_to(&mut self, id: PointerId, pos: (i32, i32)) {
        if let Some(pointer) = self.down.iter_mut().find(|p| p.id == id) {
            pointer.pos = pos;
        }
    }

    fn release(&mut self, id: PointerId, pos: Option<(i32, i32)>) {
        if let Some(index) = self.down.iter().position(|p| p.id == id) {
            let mut pointer = self.down.remove(index);
            if let Some(pos) = pos {
                pointer.pos = pos;
            }
            self.released.push(pointer);
        }
    }
}

/// Map a window position (logical pixels, top-left origin) to canvas pixels,
/// through the same letterboxed fit the display uses.
pub fn window_to_canvas(pos: Vec2, window: Vec2, canvas: (i32, i32)) -> (i32, i32) {
    let (cw, ch) = (canvas.0 as f32, canvas.1 as f32);
    let (bx, by, bw, bh) = touch::fit_box(window.x, window.y, cw, ch);
    (
        ((pos.x - bx) * cw / bw).floor() as i32,
        ((pos.y - by) * ch / bh).floor() as i32,
    )
}

pub(crate) fn plugin(app: &mut App) {
    app.init_resource::<Pointers>()
        .add_systems(PreUpdate, update_pointers.after(InputSystems));
}

#[allow(clippy::too_many_arguments)]
fn update_pointers(
    mut pointers: ResMut<Pointers>,
    time: Res<Time>,
    mouse: Res<ButtonInput<MouseButton>>,
    touches: Res<Touches>,
    mut cursor_moves: MessageReader<CursorMoved>,
    mut last_cursor: Local<Option<Vec2>>,
    window: Single<&Window, With<PrimaryWindow>>,
    canvas: Res<PixelCanvas>,
) {
    pointers.now_ms = time.elapsed().as_millis() as u64;
    pointers.pressed.clear();
    pointers.released.clear();
    // Pointer positions are in the page's CSS pixels in the browser (see
    // `web::canvas_css_size`) and in logical window pixels on desktop.
    let size = crate::web::canvas_css_size().map_or(window.size(), |(w, h)| Vec2::new(w, h));
    let to_canvas = |pos: Vec2| window_to_canvas(pos, size, canvas.canvas.size());

    // The raw cursor position: `Window::cursor_position` drops positions it
    // thinks are outside the window, which on some browsers (pixel ratio
    // mismatches) includes most of the canvas.
    if let Some(moved) = cursor_moves.read().last() {
        *last_cursor = Some(moved.position);
    }
    let cursor = last_cursor.map(to_canvas);
    for (button, id) in [
        (MouseButton::Left, PointerId::MouseLeft),
        (MouseButton::Right, PointerId::MouseRight),
    ] {
        if mouse.just_pressed(button)
            && let Some(pos) = cursor
        {
            pointers.press(id, pos);
        }
        if let Some(pos) = cursor {
            pointers.move_to(id, pos);
        }
        if mouse.just_released(button) {
            pointers.release(id, cursor);
        }
    }

    for touch in touches.iter_just_pressed() {
        pointers.press(PointerId::Touch(touch.id()), to_canvas(touch.position()));
    }
    for touch in touches.iter() {
        pointers.move_to(PointerId::Touch(touch.id()), to_canvas(touch.position()));
    }
    for touch in touches
        .iter_just_released()
        .chain(touches.iter_just_canceled())
    {
        pointers.release(
            PointerId::Touch(touch.id()),
            Some(to_canvas(touch.position())),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn window_to_canvas_undoes_the_letterbox() {
        // A 400x350 canvas in an 844x390 window: 1.114x, bars on the sides.
        let window = Vec2::new(844.0, 390.0);
        let (bx, _, bw, bh) = touch::fit_box(844.0, 390.0, 400.0, 350.0);
        assert_eq!(
            window_to_canvas(Vec2::new(bx, 0.0), window, (400, 350)),
            (0, 0)
        );
        assert_eq!(
            window_to_canvas(Vec2::new(bx + bw - 0.1, bh - 0.1), window, (400, 350)),
            (399, 349)
        );
        assert_eq!(
            window_to_canvas(Vec2::new(422.0, 195.0), window, (400, 350)),
            (200, 175)
        );
        // Left of the canvas (in the bar) maps to a negative x.
        assert!(window_to_canvas(Vec2::new(1.0, 100.0), window, (400, 350)).0 < 0);
    }

    #[test]
    fn pointers_track_press_move_and_release_per_id() {
        let mut pointers = Pointers {
            now_ms: 100,
            ..default()
        };
        pointers.press(PointerId::Touch(1), (10, 10));
        pointers.press(PointerId::Touch(2), (50, 50));
        assert_eq!(pointers.down.len(), 2);
        pointers.move_to(PointerId::Touch(1), (12, 30));
        assert_eq!(pointers.get(PointerId::Touch(1)).unwrap().pos, (12, 30));
        assert_eq!(pointers.get(PointerId::Touch(1)).unwrap().start, (10, 10));
        pointers.release(PointerId::Touch(1), None);
        assert_eq!(pointers.down.len(), 1);
        assert_eq!(pointers.released[0].pos, (12, 30));
        assert_eq!(pointers.released[0].start_ms, 100);
        // Releasing an unknown pointer is ignored.
        pointers.release(PointerId::MouseLeft, Some((0, 0)));
        assert_eq!(pointers.released.len(), 1);
    }
}
