'''Pure tetris rules: no pygame, so everything here is unit-testable.

The board is 10 x 20. Locked blocks live in a dict mapping `(x, y)` to a
color; `y` grows downwards and may be negative while a piece spawns.
'''

import random
from dataclasses import dataclass

Color = tuple[int, int, int]
Pos = tuple[int, int]
Grid = list[list[Color]]
Shape = list[list[str]]

ROWS = 20
COLUMNS = 10
EMPTY: Color = (0, 0, 0)
# Points for clearing 1, 2, 3 or 4 lines at once, multiplied by (level + 1).
LINE_POINTS = (0, 40, 100, 300, 1200)
LINES_PER_LEVEL = 10
BASE_FALL_S = 0.5
MIN_FALL_S = 0.05
FALL_STEP = 0.85

RED: Color = (255, 0, 0)
GREEN: Color = (0, 255, 0)
YELLOW: Color = (255, 255, 0)
ORANGE: Color = (255, 165, 0)
BLUE: Color = (0, 0, 255)
LIGHT_BLUE: Color = (0, 255, 255)
PURPLE: Color = (128, 0, 128)

# Each shape is a list of 5x5 rotation frames; '0' marks a block.
S: Shape = [['.....',
             '.....',
             '..00.',
             '.00..',
             '.....'],
            ['.....',
             '..0..',
             '..00.',
             '...0.',
             '.....']]

Z: Shape = [['.....',
             '.....',
             '.00..',
             '..00.',
             '.....'],
            ['.....',
             '..0..',
             '.00..',
             '.0...',
             '.....']]

I: Shape = [['..0..',  # noqa: E741
             '..0..',
             '..0..',
             '..0..',
             '.....'],
            ['.....',
             '0000.',
             '.....',
             '.....',
             '.....']]

O: Shape = [['.....',  # noqa: E741
             '.....',
             '.00..',
             '.00..',
             '.....']]

J: Shape = [['.....',
             '.0...',
             '.000.',
             '.....',
             '.....'],
            ['.....',
             '..00.',
             '..0..',
             '..0..',
             '.....'],
            ['.....',
             '.....',
             '.000.',
             '...0.',
             '.....'],
            ['.....',
             '..0..',
             '..0..',
             '.00..',
             '.....']]

L: Shape = [['.....',
             '...0.',
             '.000.',
             '.....',
             '.....'],
            ['.....',
             '..0..',
             '..0..',
             '..00.',
             '.....'],
            ['.....',
             '.....',
             '.000.',
             '.0...',
             '.....'],
            ['.....',
             '.00..',
             '..0..',
             '..0..',
             '.....']]

T: Shape = [['.....',
             '..0..',
             '.000.',
             '.....',
             '.....'],
            ['.....',
             '..0..',
             '..00.',
             '..0..',
             '.....'],
            ['.....',
             '.....',
             '.000.',
             '..0..',
             '.....'],
            ['.....',
             '..0..',
             '.00..',
             '..0..',
             '.....']]

SHAPES: list[Shape] = [S, Z, I, O, J, L, T]
SHAPE_COLORS: list[Color] = [GREEN, RED, LIGHT_BLUE, YELLOW, ORANGE, BLUE, PURPLE]


@dataclass
class Piece:
    x: int
    y: int
    shape: Shape
    color: Color
    rotation: int = 0

    @property
    def frame(self) -> list[str]:
        return self.shape[self.rotation % len(self.shape)]


def new_piece(rng: random.Random | None = None) -> Piece:
    index = (rng or random).randrange(len(SHAPES))
    return Piece(5, 0, SHAPES[index], SHAPE_COLORS[index])


def create_grid(locked: dict[Pos, Color] | None = None) -> Grid:
    locked = locked or {}
    return [[locked.get((x, y), EMPTY) for x in range(COLUMNS)] for y in range(ROWS)]


def frame_positions(frame: list[str], x: int = 0, y: int = 0) -> list[Pos]:
    '''Block coordinates of a 5x5 frame placed with its top-left at `(x, y)`.'''
    return [
        (x + j, y + i)
        for i, line in enumerate(frame)
        for j, cell in enumerate(line)
        if cell == '0'
    ]


def piece_positions(piece: Piece) -> list[Pos]:
    '''Board coordinates of `piece`; frames are anchored at offset (2, 4).'''
    return frame_positions(piece.frame, piece.x - 2, piece.y - 4)


def valid_space(piece: Piece, grid: Grid) -> bool:
    for x, y in piece_positions(piece):
        if not 0 <= x < COLUMNS or y >= ROWS:
            return False
        if y >= 0 and grid[y][x] != EMPTY:
            return False
    return True


def try_move(piece: Piece, grid: Grid, dx: int = 0, dy: int = 0, rotate: int = 0) -> bool:
    '''Apply the move if it lands in a valid space; return whether it did.'''
    piece.x += dx
    piece.y += dy
    piece.rotation = (piece.rotation + rotate) % len(piece.shape)
    if valid_space(piece, grid):
        return True
    piece.x -= dx
    piece.y -= dy
    piece.rotation = (piece.rotation - rotate) % len(piece.shape)
    return False


def hard_drop(piece: Piece, grid: Grid) -> None:
    while try_move(piece, grid, dy=1):
        pass


def lock_piece(piece: Piece, locked: dict[Pos, Color]) -> dict[Pos, Color]:
    return {**locked, **{pos: piece.color for pos in piece_positions(piece)}}


def check_lost(locked: dict[Pos, Color]) -> bool:
    return any(y < 1 for _, y in locked)


def clear_rows(locked: dict[Pos, Color]) -> tuple[dict[Pos, Color], int]:
    '''Remove full rows and drop every block by the number of cleared rows below it.

    Works for non-contiguous clears (e.g. rows 17 and 19 full, 18 not).
    '''
    full = {
        y for y in range(ROWS)
        if all((x, y) in locked for x in range(COLUMNS))
    }
    remaining = {
        (x, y + sum(1 for row in full if row > y)): color
        for (x, y), color in locked.items()
        if y not in full
    }
    return remaining, len(full)


def score_for_lines(lines: int, level: int = 0) -> int:
    '''Classic scoring: multi-line clears are worth more, scaled by level.'''
    return LINE_POINTS[min(lines, 4)] * (level + 1)


def level_for_lines(total_lines: int) -> int:
    return total_lines // LINES_PER_LEVEL


def fall_interval(level: int) -> float:
    '''Seconds between automatic drops; pieces fall faster every level.'''
    return max(MIN_FALL_S, BASE_FALL_S * FALL_STEP**level)
