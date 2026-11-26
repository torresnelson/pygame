import pytest
from highscores import NAME_LENGTH
from touch import button_at

from tetris import (
    GAME_BUTTONS,
    HEIGHT,
    KEY_ROWS,
    KEYBOARD,
    MENU_BOX,
    MENU_OPTIONS,
    MENU_ROW,
    WIDTH,
    accept_char,
    menu_index_at,
    press_key,
    shade,
)


def test_shade_blends_towards_white_and_black() -> None:
    assert shade((100, 100, 100), 0.5) == (177, 177, 177)
    assert shade((100, 100, 100), -0.5) == (50, 50, 50)
    assert shade((10, 20, 30), 0) == (10, 20, 30)


def test_accept_char_uppercases_and_filters() -> None:
    assert accept_char('NEL', 's') == 'NELS'
    assert accept_char('A', '~') == 'A'
    assert accept_char('A', '\t') == 'A'
    assert accept_char('A', 'ab') == 'A'
    assert accept_char('X' * NAME_LENGTH, 'Y') == 'X' * NAME_LENGTH


def test_menu_index_at_maps_rows_inside_the_box() -> None:
    for i in range(len(MENU_OPTIONS)):
        y = MENU_BOX.y + 14 + i * MENU_ROW + 6
        assert menu_index_at((MENU_BOX.centerx, y)) == i
    assert menu_index_at((MENU_BOX.x - 5, MENU_BOX.centery)) is None
    assert menu_index_at((MENU_BOX.centerx, MENU_BOX.bottom + 5)) is None


def inside_canvas(rect: tuple[int, int, int, int]) -> bool:
    x, y, width, height = rect
    return x >= 0 and y >= 0 and x + width <= WIDTH and y + height <= HEIGHT


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@pytest.mark.parametrize('buttons', [GAME_BUTTONS, KEYBOARD], ids=['game', 'keyboard'])
def test_buttons_fit_the_canvas_without_overlapping(buttons: tuple) -> None:
    assert all(inside_canvas(button.rect) for button in buttons)
    for i, a in enumerate(buttons):
        for b in buttons[i + 1:]:
            assert not overlaps(a.rect, b.rect), (a.action, b.action)


def test_keyboard_has_every_character_plus_del_and_ok() -> None:
    actions = [key.action for key in KEYBOARD]
    assert actions == [*''.join(KEY_ROWS), 'DEL', 'OK']


def test_keyboard_keys_can_be_tapped() -> None:
    for key in KEYBOARD:
        x, y, width, height = key.rect
        assert button_at(KEYBOARD, (x + width // 2, y + height // 2)) == key.action


def test_press_key() -> None:
    assert press_key('AN', 'A') == 'ANA'
    assert press_key('ANA', 'DEL') == 'AN'
    assert press_key('', 'DEL') == ''
    assert press_key('X' * NAME_LENGTH, 'Q') == 'X' * NAME_LENGTH
