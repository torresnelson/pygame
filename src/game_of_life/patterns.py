'''Catalogue of well-known Game of Life patterns (pure, no pygame).

Patterns are written as plaintext grids: 'O' is a live cell, '.' is dead.
'''

import random
from dataclasses import dataclass

from life import Cell


@dataclass(frozen=True)
class Pattern:
    name: str
    kind: str
    description: str
    rows: tuple[str, ...] = ()

    @property
    def cells(self) -> set[Cell]:
        return parse(self.rows)

    @property
    def size(self) -> tuple[int, int]:
        '''(height, width) of the pattern's bounding box.'''
        return len(self.rows), max((len(row) for row in self.rows), default=0)


def parse(rows: tuple[str, ...] | list[str]) -> set[Cell]:
    return {(r, c) for r, row in enumerate(rows) for c, char in enumerate(row) if char == 'O'}


def place(pattern_cells: set[Cell], rows: int, columns: int) -> set[Cell]:
    '''Centre `pattern_cells` on a `rows` x `columns` board, clipping what falls outside.'''
    if not pattern_cells:
        return set()
    height = max(r for r, _ in pattern_cells) + 1
    width = max(c for _, c in pattern_cells) + 1
    top, left = (rows - height) // 2, (columns - width) // 2
    return {
        (r + top, c + left)
        for r, c in pattern_cells
        if 0 <= r + top < rows and 0 <= c + left < columns
    }


def random_soup(
    rows: int, columns: int, density: float = 0.3, rng: random.Random | None = None
) -> set[Cell]:
    rng = rng or random.Random()
    return {(r, c) for r in range(rows) for c in range(columns) if rng.random() < density}


GLIDER = Pattern('Glider', 'spaceship', 'The smallest spaceship, moves diagonally', (
    '.O.',
    '..O',
    'OOO',
))

LWSS = Pattern('Lightweight spaceship', 'spaceship', 'Moves left 2 cells every 4 generations', (
    '.O..O',
    'O....',
    'O...O',
    'OOOO.',
))

BLINKER = Pattern('Blinker', 'oscillator', 'Period 2, the smallest oscillator', (
    'OOO',
))

TOAD = Pattern('Toad', 'oscillator', 'Period 2', (
    '.OOO',
    'OOO.',
))

BEACON = Pattern('Beacon', 'oscillator', 'Period 2, two blocks blinking at the corner', (
    'OO..',
    'OO..',
    '..OO',
    '..OO',
))

PULSAR = Pattern('Pulsar', 'oscillator', 'Period 3, the most common big oscillator', (
    '..OOO...OOO..',
    '.............',
    'O....O.O....O',
    'O....O.O....O',
    'O....O.O....O',
    '..OOO...OOO..',
    '.............',
    '..OOO...OOO..',
    'O....O.O....O',
    'O....O.O....O',
    'O....O.O....O',
    '.............',
    '..OOO...OOO..',
))

PENTADECATHLON = Pattern('Pentadecathlon', 'oscillator', 'Period 15', (
    '..O....O..',
    'OO.OOOO.OO',
    '..O....O..',
))

GOSPER_GUN = Pattern('Gosper glider gun', 'gun', 'Fires a new glider every 30 generations', (
    '........................O...........',
    '......................O.O...........',
    '............OO......OO............OO',
    '...........O...O....OO............OO',
    'OO........O.....O...OO..............',
    'OO........O...O.OO....O.O...........',
    '..........O.....O.......O...........',
    '...........O...O....................',
    '............OO......................',
))

R_PENTOMINO = Pattern('R-pentomino', 'methuselah', 'Stays chaotic for 1103 generations', (
    '.OO',
    'OO.',
    '.O.',
))

DIEHARD = Pattern('Diehard', 'methuselah', 'Vanishes completely after 130 generations', (
    '......O.',
    'OO......',
    '.O...OOO',
))

ACORN = Pattern('Acorn', 'methuselah', '7 cells that grow for 5206 generations', (
    '.O.....',
    '...O...',
    'OO..OOO',
))

RANDOM = Pattern('Random soup', 'random', 'Fill 30% of the board at random')
EMPTY = Pattern('Empty board', 'draw', 'Draw your own cells with the mouse')

CATALOGUE: tuple[Pattern, ...] = (
    GLIDER, LWSS, BLINKER, TOAD, BEACON, PULSAR, PENTADECATHLON,
    GOSPER_GUN, R_PENTOMINO, DIEHARD, ACORN, RANDOM, EMPTY,
)


def build(pattern: Pattern, rows: int, columns: int, rng: random.Random | None = None) -> set[Cell]:
    '''Initial live cells for `pattern` on a `rows` x `columns` board.'''
    if pattern is RANDOM:
        return random_soup(rows, columns, rng=rng)
    return place(pattern.cells, rows, columns)
