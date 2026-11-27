'''Build the browser versions of the Rust/bevy games into the static site.

Each game is compiled for `wasm32-unknown-unknown` with the size-optimised
`web-release` profile, run through `wasm-bindgen` (and `wasm-opt` when
installed), and staged as `build/site/rust/<path>/` with the page from
`rust/web/index.html`. Run it after `tools/build_web.py`, which recreates
`build/site`.

Usage:
    python tools/build_rust_web.py                  # every Rust game
    python tools/build_rust_web.py gameoflife       # only some games
    python tools/build_rust_web.py --site /tmp/site
'''

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUST = ROOT / 'rust'
TEMPLATE = RUST / 'web' / 'index.html'
SITE_DIR = ROOT / 'build' / 'site'
TARGET = 'wasm32-unknown-unknown'
PROFILE = 'web-release'
OUTPUT_NAME = 'game'


@dataclass(frozen=True)
class RustGame:
    path: str  # folder under site/rust/
    crate: str
    title: str


RUST_GAMES: tuple[RustGame, ...] = (
    RustGame('gameoflife', 'game-of-life', 'Game of Life'),
    RustGame('sandsimulator', 'sand-simulator', 'Sand Simulator'),
)
RUST_GAMES_BY_PATH = {game.path: game for game in RUST_GAMES}


def page(title: str, template: Path = TEMPLATE) -> str:
    return template.read_text().replace('{{TITLE}}', title).replace('{{NAME}}', OUTPUT_NAME)


def wasm_path(game: RustGame) -> Path:
    return RUST / 'target' / TARGET / PROFILE / f'{game.crate}.wasm'


def build_command(game: RustGame) -> list[str]:
    return ['cargo', 'build', '--profile', PROFILE, '--target', TARGET, '-p', game.crate]


def bindgen_command(game: RustGame, out_dir: Path) -> list[str]:
    return ['wasm-bindgen', '--target', 'web', '--no-typescript', '--out-dir', str(out_dir),
            '--out-name', OUTPUT_NAME, str(wasm_path(game))]


# The WebAssembly features Rust enables by default for wasm32-unknown-unknown.
WASM_FEATURES = ('bulk-memory', 'nontrapping-float-to-int', 'sign-ext', 'mutable-globals',
                 'reference-types', 'multivalue')


def optimise_command(wasm: Path) -> list[str]:
    features = [f'--enable-{feature}' for feature in WASM_FEATURES]
    return ['wasm-opt', '-Oz', *features, '--strip-debug', '--strip-producers',
            '-o', str(wasm), str(wasm)]


def run(command: list[str], cwd: Path = RUST) -> None:
    print('$', ' '.join(command))
    subprocess.run(command, cwd=cwd, check=True)


def build_game(game: RustGame, site_dir: Path) -> Path:
    out_dir = site_dir / 'rust' / game.path
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    run(build_command(game))
    run(bindgen_command(game, out_dir))
    wasm = out_dir / f'{OUTPUT_NAME}_bg.wasm'
    # Optional size pass: an old or missing wasm-opt only costs download size.
    if not shutil.which('wasm-opt'):
        print('wasm-opt not found: skipping the extra size pass')
    elif subprocess.run(optimise_command(wasm), check=False).returncode != 0:
        print('wasm-opt failed: keeping the unoptimised wasm')
    (out_dir / 'index.html').write_text(page(game.title))
    print(f'{game.path}: {wasm.stat().st_size / 1e6:.1f} MB wasm')
    return out_dir


def main(argv: list[str]) -> int:
    site_dir = SITE_DIR
    if '--site' in argv:
        site_dir = Path(argv[argv.index('--site') + 1]).resolve()
        argv = [a for i, a in enumerate(argv) if a != '--site' and argv[i - 1] != '--site']
    unknown = [path for path in argv if path not in RUST_GAMES_BY_PATH]
    if unknown:
        print(f'unknown game(s): {", ".join(unknown)}; choose from {", ".join(RUST_GAMES_BY_PATH)}')
        return 2
    games = tuple(RUST_GAMES_BY_PATH[path] for path in argv) or RUST_GAMES
    for game in games:
        build_game(game, site_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
