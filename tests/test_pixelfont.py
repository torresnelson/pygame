import string

import pygame
import pytest
from pixelfont import (
    CHARSET,
    GLYPH_HEIGHT,
    GLYPH_WIDTH,
    GLYPHS,
    draw,
    glyph_pixels,
    normalise,
    pixel_rects,
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


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


@pytest.mark.parametrize('depth', [16, 24, 32])
def test_draw_fills_glyph_pixels_on_any_surface_format(depth: int) -> None:
    # Plain surfaces without per-pixel alpha, like a real display canvas.
    surface = pygame.Surface((40, 30), depth=depth)
    surface.fill(BLACK)
    rect = draw(surface, 'I', (3, 4), WHITE, 2)
    assert rect == pygame.Rect(3, 4, 10, 14)
    on = set(glyph_pixels('I'))
    for y in range(GLYPH_HEIGHT):
        for x in range(GLYPH_WIDTH):
            lit = surface.get_at((3 + x * 2 + 1, 4 + y * 2 + 1))[:3] != BLACK
            assert lit == ((x, y) in on)


def test_draw_center_and_shadow() -> None:
    surface = pygame.Surface((40, 30))
    surface.fill(BLACK)
    rect = draw(surface, 'HI', (20, 15), WHITE, 1, shadow=(100, 0, 0), center=True)
    assert rect == pygame.Rect(15, 12, 12, 8)
    # 'H' top-left pixel is lit; the shadow sits one pixel down-right of the last row.
    assert surface.get_at((15, 12))[:3] == WHITE
    assert surface.get_at((16, 19))[:3] == (100, 0, 0)


def test_pixel_rects_count_matches_glyphs() -> None:
    assert len(pixel_rects('HI', 3)) == len(glyph_pixels('H')) + len(glyph_pixels('I'))
    assert pixel_rects('', 1) == ()
