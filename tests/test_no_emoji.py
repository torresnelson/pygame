import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKED = ('src', 'tests', 'tools', 'plans', '.github')
TEXT_SUFFIXES = {'.py', '.md', '.tmpl', '.html', '.yml', '.yaml', '.toml', '.nix', '.txt'}
# Code points, not literal characters, so this file stays free of emoji itself.
EMOJI_RANGES = (
    (0x2190, 0x21FF),  # arrows
    (0x2300, 0x23FF),  # miscellaneous technical (eject, play/pause, hourglass)
    (0x25A0, 0x25FF),  # geometric shapes (play triangle, squares)
    (0x2600, 0x27BF),  # miscellaneous symbols and dingbats
    (0x2B00, 0x2BFF),  # miscellaneous symbols and arrows
    (0x1F000, 0x1FAFF),  # emoji, pictographs, flags
    (0xFE0E, 0xFE0F),  # text / emoji variation selectors
    (0x200D, 0x200D),  # zero-width joiner
)
EMOJI = re.compile('[' + ''.join(f'{chr(a)}-{chr(b)}' for a, b in EMOJI_RANGES) + ']')


def checked_files() -> list[Path]:
    files = [ROOT / 'README.md', ROOT / 'pyproject.toml', ROOT / 'default.nix']
    for folder in CHECKED:
        files += [path for path in (ROOT / folder).rglob('*')
                  if path.is_file() and path.suffix in TEXT_SUFFIXES
                  and '__pycache__' not in path.parts]
    return files


def test_the_codebase_has_no_emoji() -> None:
    found = [
        f'{path.relative_to(ROOT)}:{number}: {line.strip()}'
        for path in checked_files()
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1)
        if EMOJI.search(line)
    ]
    assert not found, '\n'.join(found)


def test_the_pattern_catches_emoji_but_not_plain_text() -> None:
    for code in (0x23CF, 0x25B6, 0x25A0, 0x1F600, 0x2705, 0xFE0F):  # eject, play, stop, ...
        assert EMOJI.search(chr(code)), hex(code)
    assert not EMOJI.search('plain ascii -> <- [ ] and accents: ' + chr(0xE9))
