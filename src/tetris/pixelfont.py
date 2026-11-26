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
def render(text: str, color: tuple, scale: int = 1, shadow: tuple | None = None) -> pygame.Surface:
    '''Render `text` to a transparent surface; `shadow` adds a 1-pixel drop shadow.'''
    text = normalise(text)
    width, height = text_size(text, scale)
    offset = scale if shadow else 0
    surface = pygame.Surface((max(1, width + offset), height + offset), pygame.SRCALPHA)
    advance = (GLYPH_WIDTH + SPACING) * scale
    layers = ([(shadow, offset)] if shadow else []) + [(color, 0)]
    for layer_color, shift in layers:
        for i, char in enumerate(text):
            for x, y in glyph_pixels(char):
                rect = (i * advance + x * scale + shift, y * scale + shift, scale, scale)
                surface.fill(layer_color, rect)
    return surface


def draw(surface: pygame.Surface, text: str, pos: tuple[float, float], color: tuple,
         scale: int = 1, shadow: tuple | None = None, center: bool = False) -> pygame.Rect:
    '''Blit `text` at `pos` (top-left, or centre when `center` is true).'''
    image = render(text, color, scale, shadow)
    x, y = pos
    if center:
        x -= image.get_width() // 2
        y -= image.get_height() // 2
    return surface.blit(image, (int(x), int(y)))
