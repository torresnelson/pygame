'''Build the browser version of the Game of Life with pygbag.

pygbag packages a folder whose entry point is `main.py`. This script
assembles that folder from the existing sources (no code is duplicated in
git), then runs pygbag to produce a static site in
`build/life_web/build/web/` (index.html + .apk) ready for any static host.

Usage:
    python tools/build_life_web.py            # assemble + build
    python tools/build_life_web.py --serve    # assemble + local test server
    python tools/build_life_web.py --assemble-only
'''

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / 'build' / 'life_web'
SOURCES = (
    ROOT / 'src' / 'game_of_life' / 'game_of_life.py',
    ROOT / 'src' / 'game_of_life' / 'life.py',
    ROOT / 'src' / 'game_of_life' / 'patterns.py',
    ROOT / 'src' / 'shared' / 'pixelfont.py',
)
# pygbag sets up packages based on the imports it finds in main.py, so pygame
# must be imported here, before any module that uses it.
MAIN = '''import asyncio

import pygame  # noqa: F401  (pygbag needs to see this import in main.py)

import game_of_life

asyncio.run(game_of_life.main())
'''
PYGBAG_ARGS = ('--ume_block', '0', '--title', 'Game of Life')


def assemble(app_dir: Path = APP_DIR, sources: tuple[Path, ...] = SOURCES) -> list[Path]:
    '''Recreate `app_dir` with the game sources and a pygbag `main.py`.'''
    if app_dir.exists():
        shutil.rmtree(app_dir)
    app_dir.mkdir(parents=True)
    copied = [Path(shutil.copy2(source, app_dir / source.name)) for source in sources]
    main = app_dir / 'main.py'
    main.write_text(MAIN)
    return [*copied, main]


def pygbag_command(app_dir: Path, serve: bool = False) -> list[str]:
    mode = [] if serve else ['--build']
    return [sys.executable, '-m', 'pygbag', *mode, *PYGBAG_ARGS, str(app_dir)]


def main(argv: list[str]) -> int:
    files = assemble()
    print(f'assembled {len(files)} files in {APP_DIR.relative_to(ROOT)}')
    if '--assemble-only' in argv:
        return 0
    return subprocess.run(pygbag_command(APP_DIR, serve='--serve' in argv), check=False).returncode


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
