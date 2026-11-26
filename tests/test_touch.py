from types import SimpleNamespace

import pytest
from touch import (
    FLICK_MS,
    Button,
    button_at,
    button_row,
    drag_steps,
    is_touch,
    release_gesture,
    repeats,
    start_drag,
)


def test_button_contains_is_half_open() -> None:
    button = Button('go', 'GO', (10, 20, 30, 40))
    assert button.contains((10, 20))
    assert button.contains((39, 59))
    assert not button.contains((40, 20))
    assert not button.contains((10, 60))


def test_button_row_fills_the_width_without_overlap() -> None:
    row = button_row((('a', 'A'), ('b', 'B'), ('c', 'C')), 8, 100, 300, 40, 6)
    assert [button.action for button in row] == ['a', 'b', 'c']
    assert all(button.rect[1] == 100 and button.rect[3] == 40 for button in row)
    for left, right in zip(row, row[1:], strict=False):
        assert left.rect[0] + left.rect[2] + 6 == right.rect[0]
    last = row[-1].rect
    assert last[0] + last[2] <= 8 + 300


def test_button_at() -> None:
    row = button_row((('a', 'A'), ('b', 'B')), 0, 0, 100, 10, 0)
    assert button_at(row, (5, 5)) == 'a'
    assert button_at(row, (55, 5)) == 'b'
    assert button_at(row, (55, 15)) is None


def test_is_touch() -> None:
    assert is_touch(SimpleNamespace(touch=True))
    assert not is_touch(SimpleNamespace(touch=False))
    assert not is_touch(SimpleNamespace())


def test_drag_steps_moves_whole_steps_and_keeps_the_remainder() -> None:
    drag = start_drag((100, 100), 0)
    assert drag_steps(drag, (110, 100), 15) == (0, 0)
    assert not drag.moved
    assert drag_steps(drag, (132, 100), 15) == (2, 0)
    assert drag.moved
    assert drag.anchor == (130, 100)
    assert drag_steps(drag, (114, 100), 15) == (-1, 0)


def test_drag_steps_never_moves_up() -> None:
    drag = start_drag((100, 100), 0)
    assert drag_steps(drag, (100, 40), 15) == (0, 0)
    assert drag_steps(drag, (100, 131), 15) == (0, 2)


@pytest.mark.parametrize(
    ('end', 'elapsed', 'gesture'),
    [
        ((102, 103), 100, 'tap'),
        ((102, 103), 1000, None),  # a long press is not a tap
        ((100, 160), 150, 'flick_down'),
        ((100, 160), FLICK_MS + 200, None),  # a slow drag is not a flick
        ((150, 160), 150, None),  # too diagonal
        ((100, 40), 150, None),  # flicking up does nothing
    ],
)
def test_release_gesture(end: tuple[int, int], elapsed: int, gesture: str | None) -> None:
    assert release_gesture(start_drag((100, 100), 0), end, elapsed) == gesture


def test_a_drag_that_moved_the_piece_is_not_a_tap() -> None:
    drag = start_drag((100, 100), 0)
    drag_steps(drag, (116, 100), 15)
    assert release_gesture(drag, (100, 100), 50) is None


def test_repeats_wait_for_the_delay_then_tick() -> None:
    assert repeats(0, 200, 60) == 0
    assert repeats(199, 200, 60) == 0
    assert repeats(200, 200, 60) == 1
    assert repeats(259, 200, 60) == 1
    assert repeats(260, 200, 60) == 2
