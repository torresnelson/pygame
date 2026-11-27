'''Build the browser versions of the games with pygbag and stage one static site.

pygbag packages a folder whose entry point is `main.py`. For each game this
script assembles such a folder from the existing sources (no code is
duplicated in git) under `build/web/<app>/`, runs pygbag, then stages the
publishable site in `build/site/`:

    build/site/index.html          landing page linking every game
    build/site/gameoflife/         Game of Life
    build/site/tetris/             Tetris
    build/site/sandsimulator/      Sand simulator

Usage:
    python tools/build_web.py                       # build every game + stage site
    python tools/build_web.py tetris                # build only some games + stage them
    python tools/build_web.py --serve gameoflife    # local test server for one game
    python tools/build_web.py --assemble-only
'''

import html
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
BUILD_DIR = ROOT / 'build' / 'web'
SITE_DIR = ROOT / 'build' / 'site'
# pygbag's default page plus a loading screen and a phone-friendly viewport.
TEMPLATE = ROOT / 'tools' / 'web_template.tmpl'
SHARED = tuple(SRC / 'shared' / name for name in ('pixelfont.py', 'touch.py', 'browser.py'))


@dataclass(frozen=True)
class Game:
    path: str  # site sub-folder and pygbag app name
    module: str  # entry module exposing `async def main()`
    title: str
    sources: tuple[Path, ...]


GAMES: tuple[Game, ...] = (
    Game('gameoflife', 'game_of_life', 'Game of Life',
         tuple(SRC / 'game_of_life' / f for f in ('game_of_life.py', 'life.py', 'patterns.py'))
         + SHARED),
    Game('tetris', 'tetris', 'Tetris',
         tuple(SRC / 'tetris' / f for f in ('tetris.py', 'tetris_logic.py', 'highscores.py'))
         + SHARED),
    Game('sandsimulator', 'sand_simulator', 'Sand Simulator',
         tuple(SRC / 'sand_simulator' / f for f in ('sand_simulator.py', 'world.py',
                                                    'materials.py'))
         + SHARED),
)
GAMES_BY_PATH = {game.path: game for game in GAMES}

# pygbag sets up packages based on the imports it finds in main.py, so pygame
# must be imported here, before any module that uses it.
MAIN_TEMPLATE = '''import asyncio

import pygame  # noqa: F401  (pygbag needs to see this import in main.py)

import {module}

asyncio.run({module}.main())
'''

LANDING_TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pygame sandbox</title>
<style>
  body {{ margin: 0; min-height: 100vh; background: #000; color: #fcfcfc;
         font: 16px/1.5 ui-monospace, "DejaVu Sans Mono", Menlo, monospace;
         display: flex; flex-direction: column; align-items: center; justify-content: center;
         padding: 48px 16px; box-sizing: border-box; }}
  ul {{ list-style: none; padding: 0; margin: 0; width: 100%; max-width: 520px; }}
  li a {{ display: block; margin: 0 0 16px; padding: 16px 20px; color: inherit;
          text-decoration: none; border: 2px solid #fcfcfc; outline: 2px solid #0058f8;
          outline-offset: -6px; text-transform: uppercase; }}
  li a:hover, li a:focus {{ background: #28285a; }}
  li strong {{ display: block; font-size: 20px; letter-spacing: 2px; }}
</style>
</head>
<body>
<ul>
{items}
</ul>
</body>
</html>
'''


def main_py(game: Game) -> str:
    return MAIN_TEMPLATE.format(module=game.module)


def landing_page(games: tuple[Game, ...] = GAMES) -> str:
    items = '\n'.join(
        f'<li><a href="{game.path}/"><strong>{html.escape(game.title)}</strong></a></li>'
        for game in games
    )
    return LANDING_TEMPLATE.format(items=items)


def assemble(game: Game, app_dir: Path) -> list[Path]:
    '''Recreate `app_dir` with the game sources and a pygbag `main.py`.'''
    if app_dir.exists():
        shutil.rmtree(app_dir)
    app_dir.mkdir(parents=True)
    copied = [Path(shutil.copy2(source, app_dir / source.name)) for source in game.sources]
    main = app_dir / 'main.py'
    main.write_text(main_py(game))
    return [*copied, main]


def pygbag_command(game: Game, app_dir: Path, serve: bool = False) -> list[str]:
    mode = [] if serve else ['--build']
    args = ['--ume_block', '0', '--title', game.title, '--template', str(TEMPLATE)]
    return [sys.executable, '-m', 'pygbag', *mode, *args, str(app_dir)]


def stage_site(games: tuple[Game, ...], build_dir: Path = BUILD_DIR,
               site_dir: Path = SITE_DIR) -> list[Path]:
    '''Copy each game's pygbag output to `site_dir/<path>/` and write the landing page.'''
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)
    staged = []
    for game in games:
        target = site_dir / game.path
        shutil.copytree(build_dir / game.path / 'build' / 'web', target)
        staged.append(target)
    (site_dir / 'index.html').write_text(landing_page(games))
    return staged


def select(names: list[str]) -> tuple[Game, ...]:
    unknown = [name for name in names if name not in GAMES_BY_PATH]
    if unknown:
        raise SystemExit(f'unknown game(s) {unknown}; choose from {list(GAMES_BY_PATH)}')
    return tuple(GAMES_BY_PATH[name] for name in names) or GAMES


def main(argv: list[str]) -> int:
    flags = {arg for arg in argv if arg.startswith('--')}
    games = select([arg for arg in argv if not arg.startswith('--')])
    for game in games:
        files = assemble(game, BUILD_DIR / game.path)
        print(f'{game.path}: assembled {len(files)} files')
    if '--assemble-only' in flags:
        return 0
    if '--serve' in flags:
        if len(games) != 1:
            raise SystemExit('--serve needs exactly one game')
        game = games[0]
        return subprocess.run(pygbag_command(game, BUILD_DIR / game.path, serve=True)).returncode
    for game in games:
        code = subprocess.run(pygbag_command(game, BUILD_DIR / game.path)).returncode
        if code != 0:
            return code
    staged = stage_site(games)
    print('site staged in build/site: ' + ', '.join(path.name for path in staged))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
