'''Build the browser version of the Game of Life with pygbag.

pygbag packages a folder whose entry point is `main.py`. This script
assembles that folder from the existing sources (no code is duplicated in
git), runs pygbag (output in `build/life_web/build/web/`), then stages the
publishable site in `build/site/`: the game under `gameoflife/` and a root
`index.html` that redirects there.

Usage:
    python tools/build_life_web.py            # assemble + build + stage site
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

WEB_DIR = APP_DIR / 'build' / 'web'
SITE_DIR = ROOT / 'build' / 'site'
SITE_PATH = 'gameoflife'
# Keeps the old site root working by sending visitors to the game's folder.
REDIRECT_HTML = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Game of Life</title>
<meta http-equiv="refresh" content="0; url={path}/">
<link rel="canonical" href="{path}/">
<script>location.replace('{path}/' + location.search + location.hash);</script>
</head>
<body>
<p><a href="{path}/">Game of Life</a></p>
</body>
</html>
'''


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


def stage_site(web_dir: Path = WEB_DIR, site_dir: Path = SITE_DIR,
               path: str = SITE_PATH) -> Path:
    '''Copy the pygbag output to `site_dir/path/` and add a redirecting root page.'''
    if site_dir.exists():
        shutil.rmtree(site_dir)
    game_dir = site_dir / path
    shutil.copytree(web_dir, game_dir)
    (site_dir / 'index.html').write_text(REDIRECT_HTML.format(path=path))
    return game_dir


def main(argv: list[str]) -> int:
    files = assemble()
    print(f'assembled {len(files)} files in {APP_DIR.relative_to(ROOT)}')
    if '--assemble-only' in argv:
        return 0
    serve = '--serve' in argv
    code = subprocess.run(pygbag_command(APP_DIR, serve=serve), check=False).returncode
    if code == 0 and not serve:
        game_dir = stage_site()
        print(f'site staged in {SITE_DIR.relative_to(ROOT)}, game in {game_dir.relative_to(ROOT)}')
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
