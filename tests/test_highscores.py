from datetime import date
from pathlib import Path

import highscores
from highscores import (
    DEFAULT_NAME,
    LIMIT,
    Entry,
    best,
    clean_name,
    from_json,
    insert,
    load,
    new_entry,
    qualifies,
    ranked,
    save,
    to_json,
)


def table(*scores: int) -> list[Entry]:
    return [Entry(f'P{i}', score) for i, score in enumerate(scores)]


def test_clean_name() -> None:
    assert clean_name('  ana  ') == 'ana'
    assert clean_name('averyveryverylongname') == 'averyveryv'
    assert clean_name('') == DEFAULT_NAME
    assert clean_name('\n\t') == DEFAULT_NAME


def test_ranked_sorts_desc_keeps_tie_order_and_limits() -> None:
    entries = [Entry('a', 10), Entry('b', 30), Entry('c', 10), *table(*range(1, 9))]
    result = ranked(entries)
    assert len(result) == LIMIT
    assert result[0] == Entry('b', 30)
    assert result.index(Entry('a', 10)) < result.index(Entry('c', 10))


def test_qualifies() -> None:
    assert not qualifies([], 0)
    assert qualifies([], 40)
    full = table(*range(100, 100 + LIMIT))
    assert not qualifies(full, 100)
    assert qualifies(full, 101)


def test_insert_returns_rank() -> None:
    entries = table(500, 300, 100)
    new = Entry('me', 400)
    result, rank = insert(entries, new)
    assert rank == 1
    assert [e.score for e in result] == [500, 400, 300, 100]

    full = table(*range(100, 100 + LIMIT))
    _, rank = insert(full, Entry('low', 50))
    assert rank is None


def test_best() -> None:
    assert best([]) == 0
    assert best(table(10, 90, 30)) == 90


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / 'highscores.json'
    entries = [new_entry('ana', 1200, 12, 1, date(2026, 11, 26)), Entry('bob', 40)]
    save(entries, path)
    assert load(path, tmp_path / 'none.txt') == ranked(entries)
    assert load(path)[0].day == '2026-11-26'


def test_load_missing_or_corrupt_is_empty(tmp_path: Path) -> None:
    missing = tmp_path / 'nope.json'
    assert load(missing, tmp_path / 'nope.txt') == []
    corrupt = tmp_path / 'bad.json'
    corrupt.write_text('{not json')
    assert load(corrupt, tmp_path / 'nope.txt') == []
    wrong_shape = tmp_path / 'shape.json'
    wrong_shape.write_text('[{"unexpected": 1}]')
    assert load(wrong_shape, tmp_path / 'nope.txt') == []


def test_load_imports_legacy_scores_txt(tmp_path: Path) -> None:
    legacy = tmp_path / 'scores.txt'
    legacy.write_text('340\n')
    assert load(tmp_path / 'highscores.json', legacy) == [Entry('LEGACY', 340)]
    legacy.write_text('0\n')
    assert load(tmp_path / 'highscores.json', legacy) == []


def test_default_paths_live_next_to_module() -> None:
    assert highscores.HIGHSCORES_FILE.parent.name == 'tetris'
    assert highscores.LEGACY_FILE.name == 'scores.txt'


def test_json_roundtrip_and_bad_input() -> None:
    entries = [Entry('b', 40), Entry('a', 1200, 12, 1, '2026-11-26')]
    assert from_json(to_json(entries)) == ranked(entries)
    assert from_json(None) == []
    assert from_json('') == []
    assert from_json('{not json') == []
    assert from_json('[{"unexpected": 1}]') == []
