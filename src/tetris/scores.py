from pathlib import Path

SCORES_FILE = Path(__file__).with_name('scores.txt')


def read_max_score(path: Path = SCORES_FILE) -> int:
    '''Return the stored max score, or 0 when the file is missing or invalid.'''
    try:
        return int(path.read_text().strip() or 0)
    except (FileNotFoundError, ValueError):
        return 0


def save_max_score(score: int, path: Path = SCORES_FILE) -> int:
    '''Persist `score` if it beats the stored one; return the resulting max.'''
    best = max(read_max_score(path), score)
    path.write_text(f'{best}\n')
    return best
