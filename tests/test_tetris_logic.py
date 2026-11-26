import random

import pytest
from tetris_logic import (
    COLUMNS,
    EMPTY,
    ROWS,
    SHAPE_COLORS,
    SHAPES,
    Color,
    I,
    O,
    Piece,
    Pos,
    T,
    check_lost,
    clear_rows,
    create_grid,
    fall_interval,
    hard_drop,
    level_for_lines,
    lock_piece,
    new_piece,
    piece_positions,
    score_for_lines,
    try_move,
    valid_space,
)

R: Color = (255, 0, 0)


def full_row(y: int) -> dict[Pos, Color]:
    return {(x, y): R for x in range(COLUMNS)}


def test_create_grid_places_locked_blocks() -> None:
    grid = create_grid({(3, 7): R})
    assert len(grid) == ROWS and all(len(row) == COLUMNS for row in grid)
    assert grid[7][3] == R
    assert sum(cell != EMPTY for row in grid for cell in row) == 1


def test_create_grid_default_is_not_shared() -> None:
    first = create_grid()
    first[0][0] = R
    assert create_grid()[0][0] == EMPTY


def test_piece_positions_o_shape() -> None:
    assert sorted(piece_positions(Piece(5, 4, O, R))) == [(4, 2), (4, 3), (5, 2), (5, 3)]


def test_clear_single_bottom_row_shifts_above() -> None:
    locked = {**full_row(19), (0, 18): R}
    remaining, lines = clear_rows(locked)
    assert lines == 1
    assert remaining == {(0, 19): R}


def test_clear_non_contiguous_rows_keeps_every_block() -> None:
    # Rows 19 and 17 are full; row 18 and row 16 each hold one block.
    locked = {**full_row(19), **full_row(17), (0, 18): R, (0, 16): R}
    remaining, lines = clear_rows(locked)
    assert lines == 2
    assert remaining == {(0, 19): R, (0, 18): R}


def test_clear_rows_without_full_rows_is_noop() -> None:
    locked = {(0, 19): R, (5, 10): R}
    assert clear_rows(locked) == (locked, 0)


def test_clear_four_rows_tetris() -> None:
    locked = {**full_row(16), **full_row(17), **full_row(18), **full_row(19), (2, 15): R}
    remaining, lines = clear_rows(locked)
    assert lines == 4
    assert remaining == {(2, 19): R}


@pytest.mark.parametrize(
    ('lines', 'level', 'points'),
    [(0, 0, 0), (1, 0, 40), (2, 0, 100), (3, 0, 300), (4, 0, 1200), (1, 2, 120), (4, 9, 12000)],
)
def test_score_for_lines(lines: int, level: int, points: int) -> None:
    assert score_for_lines(lines, level) == points


@pytest.mark.parametrize(('total', 'level'), [(0, 0), (9, 0), (10, 1), (25, 2), (100, 10)])
def test_level_for_lines(total: int, level: int) -> None:
    assert level_for_lines(total) == level


def test_fall_interval_speeds_up_and_is_capped() -> None:
    intervals = [fall_interval(level) for level in range(40)]
    assert intervals[0] == pytest.approx(0.5)
    assert all(a >= b for a, b in zip(intervals, intervals[1:], strict=False))
    assert intervals[1] < intervals[0]
    assert intervals[-1] == pytest.approx(0.05)


def test_valid_space_rejects_walls_floor_and_blocks() -> None:
    grid = create_grid({(5, 10): R})
    assert valid_space(Piece(5, 5, O, R), grid)
    assert not valid_space(Piece(0, 5, O, R), grid)  # x = -1
    assert not valid_space(Piece(10, 5, O, R), grid)  # x = 9..10
    assert not valid_space(Piece(5, 24, O, R), grid)  # y = 20
    assert not valid_space(Piece(6, 12, O, R), grid)  # overlaps (5, 10)
    assert valid_space(Piece(6, 13, O, R), grid)  # just below it


def test_valid_space_allows_spawn_above_board() -> None:
    assert valid_space(Piece(5, 0, I, R), create_grid())


def test_rotation_wraps_and_reverts_when_blocked() -> None:
    grid = create_grid()
    piece = Piece(5, 10, T, R, rotation=3)
    assert try_move(piece, grid, rotate=1)
    assert piece.rotation == 0

    # Vertical I against the left wall cannot rotate to horizontal.
    piece = Piece(0, 10, I, R)
    assert not try_move(piece, grid, rotate=1)
    assert piece.rotation == 0


def test_try_move_reverts_on_collision() -> None:
    grid = create_grid()
    piece = Piece(1, 10, O, R)
    assert not try_move(piece, grid, dx=-1)
    assert piece.x == 1


def test_hard_drop_lands_on_floor_and_on_blocks() -> None:
    piece = Piece(5, 0, O, R)
    hard_drop(piece, create_grid())
    assert max(y for _, y in piece_positions(piece)) == ROWS - 1

    piece = Piece(5, 0, O, R)
    hard_drop(piece, create_grid(full_row(19)))
    assert max(y for _, y in piece_positions(piece)) == ROWS - 2


def test_lock_piece_does_not_mutate_input() -> None:
    locked: dict[Pos, Color] = {}
    result = lock_piece(Piece(5, 5, O, R), locked)
    assert locked == {}
    assert len(result) == 4


def test_check_lost() -> None:
    assert not check_lost({(0, 19): R})
    assert check_lost({(0, 0): R})
    assert check_lost({(0, -1): R})


def test_new_piece_color_matches_shape() -> None:
    rng = random.Random(1)
    for _ in range(20):
        piece = new_piece(rng)
        assert piece.color == SHAPE_COLORS[SHAPES.index(piece.shape)]
