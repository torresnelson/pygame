from highscores import NAME_LENGTH

from tetris import MENU_BOX, MENU_OPTIONS, MENU_ROW, accept_char, menu_index_at, shade


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
