import random

import pytest
from life import Cell, next_generation
from patterns import (
    ACORN,
    BEACON,
    BLINKER,
    CATALOGUE,
    DIEHARD,
    EMPTY,
    GLIDER,
    GOSPER_GUN,
    LWSS,
    PENTADECATHLON,
    PULSAR,
    R_PENTOMINO,
    RANDOM,
    TOAD,
    Pattern,
    build,
    parse,
    place,
)

BIG = 120


def run(cells: set[Cell], generations: int, size: int = BIG) -> set[Cell]:
    for _ in range(generations):
        cells = next_generation(cells, size, size)
    return cells


def normalise(cells: set[Cell]) -> set[Cell]:
    top = min(r for r, _ in cells)
    left = min(c for _, c in cells)
    return {(r - top, c - left) for r, c in cells}


def centred(pattern: Pattern) -> set[Cell]:
    return build(pattern, BIG, BIG)


def test_parse() -> None:
    assert parse(('.O.', '..O', 'OOO')) == {(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)}


@pytest.mark.parametrize(
    ('pattern', 'population'),
    [
        (GLIDER, 5), (LWSS, 9), (BLINKER, 3), (TOAD, 6), (BEACON, 8), (PULSAR, 48),
        (PENTADECATHLON, 12), (GOSPER_GUN, 36), (R_PENTOMINO, 5), (DIEHARD, 7), (ACORN, 7),
    ],
)
def test_known_populations(pattern: Pattern, population: int) -> None:
    assert len(pattern.cells) == population


def test_catalogue_names_are_unique_and_described() -> None:
    names = [p.name for p in CATALOGUE]
    assert len(names) == len(set(names))
    assert all(p.description for p in CATALOGUE)


def test_place_centres_and_clips() -> None:
    assert place({(0, 0)}, 11, 11) == {(5, 5)}
    assert place(GLIDER.cells, 3, 3) == GLIDER.cells
    assert len(place(GOSPER_GUN.cells, 5, 5)) < len(GOSPER_GUN.cells)
    assert place(set(), 10, 10) == set()


@pytest.mark.parametrize(
    ('pattern', 'period'),
    [(BLINKER, 2), (TOAD, 2), (BEACON, 2), (PULSAR, 3), (PENTADECATHLON, 15)],
)
def test_oscillators_have_their_period(pattern: Pattern, period: int) -> None:
    start = centred(pattern)
    assert run(start, period) == start
    assert all(run(start, n) != start for n in range(1, period))


def test_glider_moves_one_cell_diagonally_every_4_generations() -> None:
    start = centred(GLIDER)
    assert run(start, 4) == {(r + 1, c + 1) for r, c in start}


def test_lwss_moves_two_cells_left_every_4_generations() -> None:
    start = centred(LWSS)
    assert run(start, 4) == {(r, c - 2) for r, c in start}


def test_gosper_gun_fires_one_glider_every_30_generations() -> None:
    start = centred(GOSPER_GUN)
    populations = [len(run(start, 30 * k)) for k in range(4)]
    assert [b - a for a, b in zip(populations, populations[1:], strict=False)] == [5, 5, 5]


def test_diehard_vanishes_after_130_generations() -> None:
    cells = run(centred(DIEHARD), 129)
    assert cells
    assert next_generation(cells, BIG, BIG) == set()


def test_r_pentomino_is_not_static() -> None:
    start = centred(R_PENTOMINO)
    assert normalise(run(start, 50)) != normalise(start)


def test_random_soup_and_empty() -> None:
    soup = build(RANDOM, 20, 20, random.Random(1))
    assert 60 < len(soup) < 180
    assert all(0 <= r < 20 and 0 <= c < 20 for r, c in soup)
    assert build(EMPTY, 20, 20) == set()
