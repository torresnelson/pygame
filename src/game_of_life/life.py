'''Pure Conway's Game of Life rules on a bounded (non-wrapping) board.

Cells are `(row, column)` tuples; the board state is the set of live cells.
'''

from collections import Counter
from collections.abc import Iterable

Cell = tuple[int, int]

NEIGHBOUR_OFFSETS: tuple[Cell, ...] = tuple(
    (dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)
)


def neighbour_counts(cells: Iterable[Cell], rows: int, columns: int) -> Counter[Cell]:
    return Counter(
        (r + dr, c + dc)
        for r, c in cells
        for dr, dc in NEIGHBOUR_OFFSETS
        if 0 <= r + dr < rows and 0 <= c + dc < columns
    )


def next_generation(cells: set[Cell], rows: int, columns: int) -> set[Cell]:
    '''Birth on 3 neighbours, survival on 2 or 3, death otherwise.'''
    return {
        cell
        for cell, count in neighbour_counts(cells, rows, columns).items()
        if count == 3 or (count == 2 and cell in cells)
    }


def toggle(cells: set[Cell], cell: Cell) -> set[Cell]:
    return cells ^ {cell}


def cell_at(x: int, y: int, size: int, gap: int, amount: int) -> Cell | None:
    '''Map a pixel to the cell under it, or None for gaps and outside the board.'''
    pitch = size + gap
    row, row_offset = divmod(y, pitch)
    column, column_offset = divmod(x, pitch)
    if not (0 <= row < amount and 0 <= column < amount):
        return None
    if row_offset >= size or column_offset >= size:
        return None
    return row, column
