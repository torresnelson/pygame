import string

import pygame
import pytest
from pixelfont import (
    CHARSET,
    GLYPH_HEIGHT,
    GLYPH_WIDTH,
    GLYPHS,
    glyph_pixels,
    normalise,
    render,
    text_size,
)


def test_every_glyph_is_5x7_of_on_and_off_cells() -> None:
    for char, rows in GLYPHS.items():
        assert len(rows) == GLYPH_HEIGHT, char
        assert all(len(row) == GLYPH_WIDTH and set(row) <= {'#', '.'} for row in rows), char


def test_letters_digits_and_ui_punctuation_are_covered() -> None:
    assert set(string.ascii_uppercase + string.digits + ' .:!?-/>') <= CHARSET


def test_glyphs_are_distinct_and_only_space_is_blank() -> None:
    shapes = [rows for char, rows in GLYPHS.items()]
    assert len(shapes) == len(set(shapes))
    assert [char for char in GLYPHS if not glyph_pixels(char)] == [' ']


def test_normalise_uppercases_and_replaces_unknown() -> None:
    assert normalise('Nelson 1st!') == 'NELSON 1ST!'
    assert normalise('a~b') == 'A?B'


@pytest.mark.parametrize(
    ('text', 'scale', 'size'),
    [('', 1, (0, 7)), ('A', 1, (5, 7)), ('AB', 1, (11, 7)), ('TETRIS', 3, (105, 21))],
)
def test_text_size(text: str, scale: int, size: tuple[int, int]) -> None:
    assert text_size(text, scale) == size


def test_render_draws_glyph_pixels_at_scale() -> None:
    white = (255, 255, 255)
    image = render('I', white, 2)
    assert image.get_size() == (10, 14)
    on = {(x, y) for x, y in glyph_pixels('I')}
    for y in range(GLYPH_HEIGHT):
        for x in range(GLYPH_WIDTH):
            alpha = image.get_at((x * 2 + 1, y * 2 + 1)).a
            assert (alpha > 0) == ((x, y) in on)


def test_render_shadow_adds_offset() -> None:
    plain = render('HI', (255, 255, 255), 2)
    shadowed = render('HI', (255, 255, 255), 2, shadow=(0, 0, 0))
    assert shadowed.get_width() == plain.get_width() + 2
    assert shadowed.get_height() == plain.get_height() + 2
    assert isinstance(shadowed, pygame.Surface)
