import random

from sand import Pos, is_settled, pour, step

W, H = 8, 6


def settle(grains: set[Pos], seed: int = 0) -> set[Pos]:
    rng = random.Random(seed)
    for _ in range(W * H):
        grains = step(grains, W, H, rng)
    return grains


def test_grain_falls_one_row_per_step() -> None:
    assert step({(3, 0)}, W, H) == {(3, 1)}


def test_grain_rests_on_floor() -> None:
    assert step({(3, H - 1)}, W, H) == {(3, H - 1)}


def test_grain_slides_diagonally_off_another() -> None:
    result = step({(3, H - 1), (3, H - 2)}, W, H, random.Random(0))
    assert (3, H - 1) in result
    assert result - {(3, H - 1)} <= {(2, H - 1), (4, H - 1)}
    assert len(result) == 2


def test_grain_slides_to_only_free_side_at_wall() -> None:
    assert step({(0, H - 1), (0, H - 2)}, W, H) == {(0, H - 1), (1, H - 1)}
    right = W - 1
    assert step({(right, H - 1), (right, H - 2)}, W, H) == {(right, H - 1), (right - 1, H - 1)}


def test_grain_rests_when_supported_on_three_sides() -> None:
    floor = {(2, H - 1), (3, H - 1), (4, H - 1)}
    grains = floor | {(3, H - 2)}
    assert step(grains, W, H) == grains


def test_column_spreads_into_pyramid() -> None:
    grains = settle({(3, y) for y in range(4)})
    assert len(grains) == 4
    assert is_settled(grains, W, H)
    assert all(y >= H - 2 for _, y in grains)


def test_grains_are_conserved_and_stay_in_bounds() -> None:
    rng = random.Random(42)
    grains = {(rng.randrange(W), rng.randrange(H)) for _ in range(30)}
    count = len(grains)
    for _ in range(50):
        grains = step(grains, W, H, rng)
        assert len(grains) == count
        assert all(0 <= x < W and 0 <= y < H for x, y in grains)


def test_full_board_does_not_move() -> None:
    full = {(x, y) for x in range(W) for y in range(H)}
    assert step(full, W, H) == full


def test_pour_clips_brush_at_edges() -> None:
    assert pour(set(), (0, 0), 1, W, H) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert len(pour(set(), (4, 3), 1, W, H)) == 9
    right, bottom = W - 1, H - 1
    assert pour(set(), (right, bottom), 1, W, H) == {
        (right - 1, bottom - 1), (right - 1, bottom), (right, bottom - 1), (right, bottom)
    }


def test_pour_keeps_existing_grains() -> None:
    assert pour({(0, 0)}, (5, 5), 0, W, H) == {(0, 0), (5, 5)}
