from pathlib import Path

import scores
from scores import read_max_score, save_max_score


def test_missing_file_reads_as_zero(tmp_path: Path) -> None:
    assert read_max_score(tmp_path / 'scores.txt') == 0


def test_empty_or_garbage_file_reads_as_zero(tmp_path: Path) -> None:
    path = tmp_path / 'scores.txt'
    path.write_text('')
    assert read_max_score(path) == 0
    path.write_text('not a number')
    assert read_max_score(path) == 0


def test_save_creates_file_and_keeps_best(tmp_path: Path) -> None:
    path = tmp_path / 'scores.txt'
    assert save_max_score(30, path) == 30
    assert save_max_score(10, path) == 30
    assert read_max_score(path) == 30
    assert save_max_score(50, path) == 50
    assert read_max_score(path) == 50


def test_default_path_is_next_to_module() -> None:
    assert scores.SCORES_FILE.parent.name == 'tetris'
