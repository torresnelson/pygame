'''Touch helpers shared by the games (no pygame): on-screen buttons and drag gestures.

In the browser, taps and drags arrive as ordinary mouse events (SDL turns the
first finger into the mouse), so the games only need to handle the mouse.
'''

from dataclasses import dataclass

Rect = tuple[int, int, int, int]
Point = tuple[int, int]

TAP_DISTANCE = 8  # pixels a tap may wander before it counts as a drag
TAP_MS = 300
FLICK_DISTANCE = 30
FLICK_MS = 300


@dataclass(frozen=True)
class Button:
    action: str
    label: str
    rect: Rect

    def contains(self, pos: Point) -> bool:
        x, y, width, height = self.rect
        return x <= pos[0] < x + width and y <= pos[1] < y + height


def button_at(buttons: tuple[Button, ...] | list[Button], pos: Point) -> str | None:
    '''Action of the button under `pos`, if any.'''
    return next((button.action for button in buttons if button.contains(pos)), None)


def button_row(specs: tuple[tuple[str, str], ...], x: int, y: int, width: int, height: int,
               gap: int) -> tuple[Button, ...]:
    '''Lay `(action, label)` pairs out left to right in equal slots filling `width`.'''
    count = len(specs)
    slot = (width - gap * (count - 1)) // count
    return tuple(
        Button(action, label, (x + i * (slot + gap), y, slot, height))
        for i, (action, label) in enumerate(specs)
    )


def is_touch(event: object) -> bool:
    '''True for mouse events that SDL synthesised from a finger.'''
    return bool(getattr(event, 'touch', False))


@dataclass
class Drag:
    '''One finger (or mouse button) press, from down to up.'''

    start: Point
    start_ms: int
    anchor: Point  # where the last whole step was taken from
    moved: bool = False


def start_drag(pos: Point, now_ms: int) -> Drag:
    return Drag(pos, now_ms, pos)


def drag_steps(drag: Drag, pos: Point, step: int) -> tuple[int, int]:
    '''Whole `step`s moved since the anchor as (columns, rows down); advances the anchor.

    Upward movement never produces rows, so only falling is ever requested.
    '''
    columns = int((pos[0] - drag.anchor[0]) / step)
    rows = max(0, int((pos[1] - drag.anchor[1]) / step))
    if columns or rows:
        drag.anchor = (drag.anchor[0] + columns * step, drag.anchor[1] + rows * step)
        drag.moved = True
    return columns, rows


def release_gesture(drag: Drag, pos: Point, now_ms: int) -> str | None:
    '''Classify the end of a press: 'tap', 'flick_down' or None.'''
    dx, dy = pos[0] - drag.start[0], pos[1] - drag.start[1]
    elapsed = now_ms - drag.start_ms
    if dy >= FLICK_DISTANCE and abs(dy) > 2 * abs(dx) and elapsed <= FLICK_MS:
        return 'flick_down'
    small = abs(dx) <= TAP_DISTANCE and abs(dy) <= TAP_DISTANCE
    if not drag.moved and small and elapsed <= TAP_MS:
        return 'tap'
    return None
