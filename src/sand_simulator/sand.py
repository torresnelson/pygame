'''Pure falling-sand cellular automaton.

Grains are `(x, y)` tuples with `y` growing downwards. Each step a grain
falls straight down if it can, otherwise slides diagonally down-left or
down-right (random order), otherwise rests.
'''

import random

Pos = tuple[int, int]


def in_bounds(pos: Pos, columns: int, rows: int) -> bool:
    x, y = pos
    return 0 <= x < columns and 0 <= y < rows


def step(grains: set[Pos], columns: int, rows: int, rng: random.Random | None = None) -> set[Pos]:
    '''Advance one tick. Rows are processed bottom-up so grains never overlap.'''
    rng = rng or random.Random()
    moved: set[Pos] = set()
    for x, y in sorted(grains, key=lambda pos: -pos[1]):
        sides = [-1, 1]
        rng.shuffle(sides)
        for dx in (0, *sides):
            target = (x + dx, y + 1)
            if in_bounds(target, columns, rows) and target not in moved:
                moved.add(target)
                break
        else:
            moved.add((x, y))
    return moved


def pour(grains: set[Pos], center: Pos, radius: int, columns: int, rows: int) -> set[Pos]:
    '''Add grains in a square brush around `center`, clipped to the board.'''
    cx, cy = center
    brush = {
        (cx + dx, cy + dy)
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
    }
    return grains | {pos for pos in brush if in_bounds(pos, columns, rows)}


def is_settled(grains: set[Pos], columns: int, rows: int) -> bool:
    return step(grains, columns, rows, random.Random(0)) == grains
