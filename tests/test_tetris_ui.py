import pytest
from highscores import NAME_LENGTH
from tetris_logic import create_grid, new_piece
from touch import button_at

from tetris import (
    HEIGHT,
    KEY_ROWS,
    KEYBOARD,
    LANDSCAPE,
    MENU_BOX,
    MENU_OPTIONS,
    MENU_ROW,
    PORTRAIT,
    REPEATING,
    WIDTH,
    Layout,
    accept_char,
    apply_move,
    menu_index_at,
    pick_layout,
    press_key,
    shade,
)

LAYOUTS = (LANDSCAPE, PORTRAIT)


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


def inside(rect: tuple[int, int, int, int], size: tuple[int, int] = (WIDTH, HEIGHT)) -> bool:
    x, y, width, height = rect
    return x >= 0 and y >= 0 and x + width <= size[0] and y + height <= size[1]


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def test_keyboard_fits_the_view_without_overlapping() -> None:
    assert all(inside(key.rect) for key in KEYBOARD)
    for i, a in enumerate(KEYBOARD):
        for b in KEYBOARD[i + 1:]:
            assert not overlaps(a.rect, b.rect), (a.action, b.action)


def layout_parts(layout: Layout) -> list[tuple[str, tuple[int, int, int, int]]]:
    '''Every box drawn on the game screen; the board includes its 5px frame.'''
    x, y, width, height = layout.board_rect
    parts = [('board', (x - 5, y - 5, width + 10, height + 10)), ('next', layout.next_box)]
    parts += [(f'stat{i}', box) for i, box in enumerate(layout.stat_boxes)]
    parts += [(title, box) for box, title, _ in layout.help_boxes]
    parts += [(button.action, button.rect) for button in layout.buttons]
    return parts


@pytest.mark.parametrize('layout', LAYOUTS, ids=lambda layout: layout.name)
def test_layout_parts_fit_the_canvas_without_overlapping(layout: Layout) -> None:
    parts = layout_parts(layout)
    for name, rect in parts:
        assert inside(rect, layout.size), name
    for i, (name_a, a) in enumerate(parts):
        for name_b, b in parts[i + 1:]:
            assert not overlaps(a, b), (name_a, name_b)


@pytest.mark.parametrize('layout', LAYOUTS, ids=lambda layout: layout.name)
def test_layouts_can_pause_and_end_and_centre_the_view(layout: Layout) -> None:
    actions = {button.action for button in layout.buttons}
    assert {'pause', 'end'} <= actions
    assert 0 <= layout.view_offset and layout.view_offset + HEIGHT <= layout.size[1]
    assert layout.size[0] == WIDTH


def test_portrait_is_taller_than_wide_and_has_thumb_controls() -> None:
    width, height = PORTRAIT.size
    assert height > width
    actions = {button.action for button in PORTRAIT.buttons}
    assert {'left', 'right', 'rotate', 'down', 'drop'} <= actions
    assert REPEATING <= actions
    assert PORTRAIT.block > LANDSCAPE.block


def test_pick_layout() -> None:
    assert pick_layout(True) is PORTRAIT
    assert pick_layout(False) is LANDSCAPE


def test_apply_move() -> None:
    grid = create_grid({})
    piece = new_piece()
    x = piece.x
    assert not apply_move(piece, grid, 'left')
    assert piece.x == x - 1
    assert not apply_move(piece, grid, 'right')
    assert piece.x == x
    assert apply_move(piece, grid, 'drop')
    assert piece.y > 10
    assert not apply_move(piece, grid, 'nothing')


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
