'''Built-in 5x7 bitmap font for an 8-bit look, drawn with plain rectangles.

Each glyph is 7 rows of 5 cells ('#' on, '.' off). Text is upper-cased;
unknown characters render as '?'.
'''

from functools import cache

import pygame

GLYPH_WIDTH = 5
GLYPH_HEIGHT = 7
SPACING = 1

_RAW = {
    'A': '.###. #...# #...# ##### #...# #...# #...#',
    'B': '####. #...# #...# ####. #...# #...# ####.',
    'C': '.###. #...# #.... #.... #.... #...# .###.',
    'D': '####. #...# #...# #...# #...# #...# ####.',
    'E': '##### #.... #.... ####. #.... #.... #####',
    'F': '##### #.... #.... ####. #.... #.... #....',
    'G': '.###. #...# #.... #.### #...# #...# .####',
    'H': '#...# #...# #...# ##### #...# #...# #...#',
    'I': '.###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.',
    'J': '..### ...#. ...#. ...#. ...#. #..#. .##..',
    'K': '#...# #..#. #.#.. ##... #.#.. #..#. #...#',
    'L': '#.... #.... #.... #.... #.... #.... #####',
    'M': '#...# ##.## #.#.# #.#.# #...# #...# #...#',
    'N': '#...# #...# ##..# #.#.# #..## #...# #...#',
    'O': '.###. #...# #...# #...# #...# #...# .###.',
    'P': '####. #...# #...# ####. #.... #.... #....',
    'Q': '.###. #...# #...# #...# #.#.# #..#. .##.#',
    'R': '####. #...# #...# ####. #.#.. #..#. #...#',
    'S': '.#### #.... #.... .###. ....# ....# ####.',
    'T': '##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..',
    'U': '#...# #...# #...# #...# #...# #...# .###.',
    'V': '#...# #...# #...# #...# #...# .#.#. ..#..',
    'W': '#...# #...# #...# #.#.# #.#.# #.#.# .#.#.',
    'X': '#...# #...# .#.#. ..#.. .#.#. #...# #...#',
    'Y': '#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..',
    'Z': '##### ....# ...#. ..#.. .#... #.... #####',
    '0': '.###. #...# #..## #.#.# ##..# #...# .###.',
    '1': '..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.',
    '2': '.###. #...# ....# ...#. ..#.. .#... #####',
    '3': '####. ....# ....# .###. ....# ....# ####.',
    '4': '...#. ..##. .#.#. #..#. ##### ...#. ...#.',
    '5': '##### #.... ####. ....# ....# #...# .###.',
    '6': '.###. #.... #.... ####. #...# #...# .###.',
    '7': '##### ....# ...#. ..#.. .#... .#... .#...',
    '8': '.###. #...# #...# .###. #...# #...# .###.',
    '9': '.###. #...# #...# .#### ....# ....# .###.',
    ' ': '..... ..... ..... ..... ..... ..... .....',
    '.': '..... ..... ..... ..... ..... .##.. .##..',
    ',': '..... ..... ..... ..... .##.. ..#.. .#...',
    ':': '..... .##.. .##.. ..... .##.. .##.. .....',
    '!': '..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..',
    '?': '.###. #...# ....# ...#. ..#.. ..... ..#..',
    '-': '..... ..... ..... ##### ..... ..... .....',
    '+': '..... ..#.. ..#.. ##### ..#.. ..#.. .....',
    '/': '....# ....# ...#. ..#.. .#... #.... #....',
    '>': '.#... ..#.. ...#. ....# ...#. ..#.. .#...',
    '<': '...#. ..#.. .#... #.... .#... ..#.. ...#.',
    '(': '...#. ..#.. .#... .#... .#... ..#.. ...#.',
    ')': '.#... ..#.. ...#. ...#. ...#. ..#.. .#...',
    '_': '..... ..... ..... ..... ..... ..... #####',
    '[': '.###. .#... .#... .#... .#... .#... .###.',
    ']': '.###. ...#. ...#. ...#. ...#. ...#. .###.',
    "'": '..#.. ..#.. .#... ..... ..... ..... .....',
}

GLYPHS: dict[str, tuple[str, ...]] = {char: tuple(rows.split()) for char, rows in _RAW.items()}
CHARSET = frozenset(GLYPHS)


def normalise(text: str) -> str:
    '''Upper-case `text` and replace characters the font lacks with '?'.'''
    return ''.join(char if char in GLYPHS else '?' for char in text.upper())


def text_size(text: str, scale: int = 1) -> tuple[int, int]:
    if not text:
        return 0, GLYPH_HEIGHT * scale
    advance = (GLYPH_WIDTH + SPACING) * scale
    return len(text) * advance - SPACING * scale, GLYPH_HEIGHT * scale


def glyph_pixels(char: str) -> list[tuple[int, int]]:
    '''(x, y) cells that are on for `char`.'''
    rows = GLYPHS[normalise(char)]
    return [(x, y) for y, row in enumerate(rows) for x, cell in enumerate(row) if cell == '#']


@cache
def pixel_rects(text: str, scale: int = 1) -> tuple[tuple[int, int, int, int], ...]:
    '''Rectangles (relative to the text's top-left) that make up `text`.'''
    advance = (GLYPH_WIDTH + SPACING) * scale
    return tuple(
        (i * advance + x * scale, y * scale, scale, scale)
        for i, char in enumerate(normalise(text))
        for x, y in glyph_pixels(char)
    )


def draw(surface: pygame.Surface, text: str, pos: tuple[float, float], color: tuple,
         scale: int = 1, shadow: tuple | None = None, center: bool = False) -> pygame.Rect:
    '''Draw `text` straight onto `surface` at `pos` (top-left, or centre).

    Glyph pixels are filled directly on the target (no intermediate
    per-pixel-alpha surface), so the result does not depend on the display's
    pixel format. `shadow` adds a drop shadow offset by one font pixel.
    '''
    text = normalise(text)
    width, height = text_size(text, scale)
    x, y = pos
    if center:
        x -= width // 2
        y -= height // 2
    x, y = int(x), int(y)
    rects = pixel_rects(text, scale)
    if shadow:
        for rx, ry, w, h in rects:
            surface.fill(shadow, (x + rx + scale, y + ry + scale, w, h))
    for rx, ry, w, h in rects:
        surface.fill(color, (x + rx, y + ry, w, h))
    offset = scale if shadow else 0
    return pygame.Rect(x, y, width + offset, height + offset)
