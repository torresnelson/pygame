'''Build the browser versions of the games with pygbag.

pygbag packages a folder whose entry point is `main.py`. For each game this
script assembles that folder from the existing sources (no code is
duplicated in git) and runs pygbag on it. A full build then gathers every
game under `build/site/<slug>/` next to a small landing page, ready for any
static host (GitHub Pages in CI).

Usage:
    python tools/build_web.py                    # build every game + landing page
    python tools/build_web.py tetris life        # build only these games
    python tools/build_web.py sand --serve       # local test server for one game
    python tools/build_web.py --assemble-only    # only write the app folders
'''

import shutil
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
BUILD_DIR = ROOT / 'build' / 'web'
SITE_DIR = ROOT / 'build' / 'site'
SHARED = (SRC / 'shared' / 'pixelfont.py', SRC / 'shared' / 'touch.py',
          SRC / 'shared' / 'browser.py')


@dataclass(frozen=True)
class Game:
    slug: str
    title: str
    module: str
    sources: tuple[Path, ...]
    blurb: str


GAMES = (
    Game('tetris', 'Tetris', 'tetris',
         (SRC / 'tetris' / 'tetris.py', SRC / 'tetris' / 'tetris_logic.py',
          SRC / 'tetris' / 'highscores.py', *SHARED),
         'Tap rotates, drag moves, flick down drops.'),
    Game('life', 'Game of Life', 'game_of_life',
         (SRC / 'game_of_life' / 'game_of_life.py', SRC / 'game_of_life' / 'life.py',
          SRC / 'game_of_life' / 'patterns.py', *SHARED),
         'Pick a pattern, tap cells, watch it evolve.'),
    Game('sand', 'Sand Simulator', 'sand_simulator',
         (SRC / 'sand_simulator' / 'sand_simulator.py', SRC / 'sand_simulator' / 'world.py',
          SRC / 'sand_simulator' / 'materials.py', *SHARED),
         'Paint sand, water and stone with a finger.'),
)
GAMES_BY_SLUG = {game.slug: game for game in GAMES}


def main_script(module: str) -> str:
    # pygbag sets up packages based on the imports it finds in main.py, so
    # pygame must be imported here, before any module that uses it.
    return f'''import asyncio

import pygame  # noqa: F401  (pygbag needs to see this import in main.py)

import {module}

asyncio.run({module}.main())
'''


def app_dir(game: Game, build_dir: Path = BUILD_DIR) -> Path:
    return build_dir / game.slug


def assemble(game: Game, target: Path) -> list[Path]:
    '''Recreate `target` with the game sources and a pygbag `main.py`.'''
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    copied = [Path(shutil.copy2(source, target / source.name)) for source in game.sources]
    main = target / 'main.py'
    main.write_text(main_script(game.module))
    return [*copied, main]


def pygbag_command(game: Game, target: Path, serve: bool = False) -> list[str]:
    mode = [] if serve else ['--build']
    return [sys.executable, '-m', 'pygbag', *mode, '--ume_block', '0',
            '--title', game.title, str(target)]


def landing_page(games: tuple[Game, ...]) -> str:
    links = '\n'.join(
        f'    <a href="{game.slug}/"><b>{escape(game.title)}</b>'
        f'<span>{escape(game.blurb)}</span></a>'
        for game in games
    )
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pygame sandbox</title>
  <style>
    body {{ margin: 0; min-height: 100vh; background: #0a0a0e; color: #e6e6e6;
           font-family: ui-monospace, monospace; display: flex; flex-direction: column;
           align-items: center; justify-content: center; gap: 16px; padding: 16px;
           box-sizing: border-box; }}
    h1 {{ color: #78c8ff; font-size: 28px; margin: 0 0 8px; }}
    a {{ display: flex; flex-direction: column; gap: 6px; width: min(420px, 100%);
         box-sizing: border-box; padding: 18px 20px; border: 2px solid #3a3a50;
         border-radius: 8px; background: #18182a; color: inherit; text-decoration: none; }}
    a:active, a:hover {{ border-color: #f8b800; }}
    b {{ font-size: 20px; }}
    span, p {{ color: #8c8ca0; font-size: 14px; }}
  </style>
</head>
<body>
  <h1>pygame sandbox</h1>
{links}
  <p>The first start downloads the Python runtime and takes a few seconds.</p>
</body>
</html>
'''


def build_site(games: tuple[Game, ...], build_dir: Path = BUILD_DIR,
               site_dir: Path = SITE_DIR) -> Path:
    '''Copy each built game into `site_dir/<slug>` and write the landing page.'''
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)
    for game in games:
        shutil.copytree(app_dir(game, build_dir) / 'build' / 'web', site_dir / game.slug)
    (site_dir / 'index.html').write_text(landing_page(games))
    return site_dir


def main(argv: list[str]) -> int:
    flags = {arg for arg in argv if arg.startswith('--')}
    slugs = [arg for arg in argv if not arg.startswith('--')]
    unknown = [slug for slug in slugs if slug not in GAMES_BY_SLUG]
    if unknown:
        print(f'unknown game(s): {", ".join(unknown)}; choose from {", ".join(GAMES_BY_SLUG)}')
        return 2
    games = tuple(GAMES_BY_SLUG[slug] for slug in slugs) or GAMES
    if '--serve' in flags and len(games) != 1:
        print('--serve needs exactly one game, e.g. python tools/build_web.py tetris --serve')
        return 2

    for game in games:
        target = app_dir(game)
        files = assemble(game, target)
        print(f'assembled {len(files)} files in {target.relative_to(ROOT)}')
        if '--assemble-only' in flags:
            continue
        command = pygbag_command(game, target, serve='--serve' in flags)
        code = subprocess.run(command, check=False).returncode
        if code:
            return code
    if not flags:
        print(f'site ready in {build_site(games).relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
