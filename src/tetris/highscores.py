'''Top-N high score table stored as JSON next to the game (no pygame).'''

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

HIGHSCORES_FILE = Path(__file__).with_name('highscores.json')
LEGACY_FILE = Path(__file__).with_name('scores.txt')
LIMIT = 10
NAME_LENGTH = 10
DEFAULT_NAME = 'PLAYER'


@dataclass(frozen=True)
class Entry:
    name: str
    score: int
    lines: int = 0
    level: int = 0
    day: str = ''


def clean_name(name: str) -> str:
    '''Keep printable characters, trim to `NAME_LENGTH`, fall back to a default.'''
    kept = ''.join(char for char in name if char.isprintable()).strip()[:NAME_LENGTH]
    return kept or DEFAULT_NAME


def ranked(entries: list[Entry], limit: int = LIMIT) -> list[Entry]:
    '''Highest score first; ties keep the earlier entry ahead.'''
    return sorted(entries, key=lambda entry: -entry.score)[:limit]


def qualifies(entries: list[Entry], score: int, limit: int = LIMIT) -> bool:
    if score <= 0:
        return False
    return len(entries) < limit or score > ranked(entries, limit)[-1].score


def insert(
    entries: list[Entry], entry: Entry, limit: int = LIMIT
) -> tuple[list[Entry], int | None]:
    '''Add `entry`; return the new table and its 0-based rank (None if it missed the cut).'''
    table = ranked([*entries, entry], limit)
    rank = next((i for i, item in enumerate(table) if item is entry), None)
    return table, rank


def best(entries: list[Entry]) -> int:
    return max((entry.score for entry in entries), default=0)


def from_json(text: str) -> list[Entry]:
    '''Parse a saved table; raises ValueError or TypeError if it is malformed.'''
    return ranked([Entry(**item) for item in json.loads(text)])


def to_json(entries: list[Entry]) -> str:
    return json.dumps([asdict(entry) for entry in ranked(entries)], indent=2) + '\n'


def load(path: Path = HIGHSCORES_FILE, legacy: Path = LEGACY_FILE) -> list[Entry]:
    '''Read the table; import the old single-number `scores.txt` once if present.'''
    try:
        return from_json(path.read_text())
    except FileNotFoundError:
        pass
    except (ValueError, TypeError):
        return []
    try:
        legacy_score = int(legacy.read_text().strip() or 0)
    except (FileNotFoundError, ValueError):
        return []
    return [Entry('LEGACY', legacy_score)] if legacy_score > 0 else []


def save(entries: list[Entry], path: Path = HIGHSCORES_FILE) -> None:
    path.write_text(to_json(entries))


def new_entry(name: str, score: int, lines: int, level: int, today: date | None = None) -> Entry:
    return Entry(clean_name(name), score, lines, level, (today or date.today()).isoformat())
