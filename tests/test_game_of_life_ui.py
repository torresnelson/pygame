import pytest
from patterns import CATALOGUE

from game_of_life import (
    DESCRIPTION_CHARS,
    MENU_ROW,
    MENU_TOP,
    PREVIEW,
    menu_index_at,
    status_text,
    wrap,
)


@pytest.mark.parametrize(
    ('value', 'width', 'lines'),
    [
        ('', 10, []),
        ('one', 10, ['one']),
        ('fires a new glider every 30', 10, ['fires a', 'new glider', 'every 30']),
        ('supercalifragilistic word', 5, ['supercalifragilistic', 'word']),
    ],
)
def test_wrap(value: str, width: int, lines: list[str]) -> None:
    assert wrap(value, width) == lines


def test_every_description_fits_the_preview_column() -> None:
    for pattern in CATALOGUE:
        assert all(len(line) <= DESCRIPTION_CHARS for line in wrap(pattern.description, 17))


def test_status_text() -> None:
    assert status_text(127, 58, 60, True) == 'GEN 127  POP 58  60/S  RUN'
    assert status_text(0, 0, 10, False).endswith('PAUSE')


def test_menu_index_at() -> None:
    for i in range(len(CATALOGUE)):
        assert menu_index_at((40, MENU_TOP + i * MENU_ROW + 4)) == i
    assert menu_index_at((PREVIEW.left + 5, MENU_TOP)) is None
    assert menu_index_at((40, MENU_TOP + len(CATALOGUE) * MENU_ROW + 10)) is None
