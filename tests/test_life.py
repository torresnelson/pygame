import pytest
from life import Cell, cell_at, next_generation, toggle

N = 10


def test_empty_board_stays_empty() -> None:
    assert next_generation(set(), N, N) == set()


def test_lonely_cell_dies() -> None:
    assert next_generation({(5, 5)}, N, N) == set()


def test_block_is_still_life() -> None:
    block = {(1, 1), (1, 2), (2, 1), (2, 2)}
    assert next_generation(block, N, N) == block


def test_blinker_oscillates() -> None:
    horizontal = {(5, 4), (5, 5), (5, 6)}
    vertical = {(4, 5), (5, 5), (6, 5)}
    assert next_generation(horizontal, N, N) == vertical
    assert next_generation(vertical, N, N) == horizontal


def test_glider_moves_diagonally() -> None:
    glider = {(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)}
    cells = glider
    for _ in range(4):
        cells = next_generation(cells, N, N)
    assert cells == {(r + 1, c + 1) for r, c in glider}


def test_board_edges_do_not_wrap() -> None:
    # A blinker on the top edge loses its out-of-board cells.
    top_edge = {(0, 4), (0, 5), (0, 6)}
    assert next_generation(top_edge, N, N) == {(0, 5), (1, 5)}

    # Corner block survives without wrapping neighbours.
    corner = {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert next_generation(corner, N, N) == corner


def test_toggle_adds_and_removes() -> None:
    cells = toggle(set(), (1, 1))
    assert cells == {(1, 1)}
    assert toggle(cells, (1, 1)) == set()


@pytest.mark.parametrize(
    ('x', 'y', 'expected'),
    [
        (0, 0, (0, 0)),
        (19, 19, (0, 0)),
        (20, 0, None),  # gap column
        (21, 0, (0, 1)),
        (21 * 19 + 5, 21 * 3 + 5, (3, 19)),
        (21 * 20, 0, None),  # past the right edge
        (-1, 0, None),
    ],
)
def test_cell_at(x: int, y: int, expected: Cell | None) -> None:
    assert cell_at(x, y, size=20, gap=1, amount=20) == expected
