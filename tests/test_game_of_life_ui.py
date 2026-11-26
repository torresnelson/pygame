import pytest
from patterns import CATALOGUE

from game_of_life import (
    BOARD_BUTTONS,
    BOARD_SIZE,
    DESCRIPTION_CHARS,
    DESCRIPTION_ROW,
    DISPLAY_SIZE,
    KEY_ACTIONS,
    LANDSCAPE,
    MENU_ROW,
    MENU_TOP,
    PORTRAIT,
    PREVIEW,
    STATUS_HEIGHT,
    Layout,
    menu_index_at,
    pick_layout,
    pick_tap,
    status_text,
    wrap,
)


@pytest.mark.parametrize(
    ('value', 'width', 'lines'),
    [
        ('', 10, []),
        ('one', 10, ['one']),
        ('fires a new glider every 30', 10, ['fires a', 'new glider', 'every 30']),
        ('supercalifragilistic word', 5, ['supercalifragilistic', 'word']),
    ],
)
def test_wrap(value: str, width: int, lines: list[str]) -> None:
    assert wrap(value, width) == lines


def test_every_description_fits_the_preview_column() -> None:
    for pattern in CATALOGUE:
        assert all(len(line) <= DESCRIPTION_CHARS for line in wrap(pattern.description, 17))


def test_status_text() -> None:
    assert status_text(127, 58, 60, True) == 'GEN 127  POP 58  60/S  RUN'
    assert status_text(0, 0, 10, False).endswith('PAUSE')


def test_menu_index_at() -> None:
    for i in range(len(CATALOGUE)):
        assert menu_index_at((40, MENU_TOP + i * MENU_ROW + 4)) == i
    assert menu_index_at((PREVIEW.left + 5, MENU_TOP)) is None
    assert menu_index_at((40, MENU_TOP + len(CATALOGUE) * MENU_ROW + 10)) is None


def test_pick_tap_mouse_starts_right_away() -> None:
    assert pick_tap(3, touch=False) == (3, True)


def test_pick_tap_touch_only_selects_even_when_tapped_again() -> None:
    '''Starting on a second tap would be a double tap, which phones zoom on.'''
    assert pick_tap(3, touch=True) == (3, False)
    assert pick_tap(3, touch=True) == (3, False)


LAYOUTS = (LANDSCAPE, PORTRAIT)


def inside(rect: tuple[int, int, int, int], size: tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x >= 0 and y >= 0 and x + w <= size[0] and y + h <= size[1]


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@pytest.mark.parametrize('layout', LAYOUTS, ids=lambda layout: layout.name)
def test_layout_buttons_fit_below_the_board_without_overlapping(layout: Layout) -> None:
    for button in layout.buttons:
        assert inside(button.rect, layout.size), button.action
        assert button.rect[1] >= BOARD_SIZE + STATUS_HEIGHT, button.action
    for i, a in enumerate(layout.buttons):
        for b in layout.buttons[i + 1:]:
            assert not overlaps(a.rect, b.rect), (a.action, b.action)
    assert set(KEY_ACTIONS.values()) == {button.action for button in layout.buttons}


@pytest.mark.parametrize('layout', LAYOUTS, ids=lambda layout: layout.name)
def test_start_button_is_clear_of_the_menu_preview_and_descriptions(layout: Layout) -> None:
    start = layout.start.rect
    assert inside(start, layout.size)
    menu_bottom = MENU_TOP + len(CATALOGUE) * MENU_ROW
    longest = max(len(wrap(p.description, DESCRIPTION_CHARS)) for p in CATALOGUE)
    description_bottom = PREVIEW.bottom + 16 + longest * DESCRIPTION_ROW
    assert start[1] >= description_bottom
    assert start[1] >= menu_bottom or start[0] >= PREVIEW.left - 8
    assert menu_index_at((start[0] + 2, start[1] + 2)) is None


def test_portrait_is_taller_with_bigger_buttons() -> None:
    assert PORTRAIT.size[1] > PORTRAIT.size[0]
    assert PORTRAIT.size[0] == LANDSCAPE.size[0]
    assert min(b.rect[3] for b in PORTRAIT.buttons) > 2 * max(b.rect[3] for b in LANDSCAPE.buttons)


def test_pick_layout() -> None:
    assert pick_layout(True) is PORTRAIT
    assert pick_layout(False) is LANDSCAPE


def test_board_buttons_sit_below_the_board_inside_the_window() -> None:
    width, height = DISPLAY_SIZE
    for button in BOARD_BUTTONS:
        x, y, w, h = button.rect
        assert y >= BOARD_SIZE + STATUS_HEIGHT - 1
        assert x >= 0 and x + w <= width and y + h <= height


def test_every_board_key_has_a_button() -> None:
    assert set(KEY_ACTIONS.values()) == {button.action for button in BOARD_BUTTONS}
