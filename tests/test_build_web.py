import ast
from pathlib import Path

import pytest
from build_web import (
    GAMES,
    Game,
    app_dir,
    assemble,
    build_site,
    landing_page,
    main_script,
    pygbag_command,
)

STDLIB_OR_PYGAME = {'asyncio', 'sys', 'pathlib', 'random', 'dataclasses', 'functools',
                    'collections', 'json', 'datetime', 'enum', 'platform', 'pygame'}


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.slug)
def test_sources_exist(game: Game) -> None:
    assert all(source.is_file() for source in game.sources)


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.slug)
def test_assemble_copies_sources_and_writes_main(game: Game, tmp_path: Path) -> None:
    app = tmp_path / 'app'
    (app / 'stale').mkdir(parents=True)
    files = assemble(game, app)
    names = sorted(path.name for path in app.iterdir())
    assert names == sorted([*(s.name for s in game.sources), 'main.py'])
    assert len(files) == len(game.sources) + 1
    assert (app / 'main.py').read_text() == main_script(game.module)


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.slug)
def test_main_imports_pygame_before_the_game(game: Game) -> None:
    '''pygbag only sets up pygame when main.py itself imports it.'''
    imports = [
        alias.name
        for node in ast.parse(main_script(game.module)).body
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    assert imports.index('pygame') < imports.index(game.module)


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.slug)
def test_assembled_app_imports_resolve_within_the_folder(game: Game, tmp_path: Path) -> None:
    '''Every local import in the app must be satisfied by a file in the folder.'''
    app = tmp_path / 'app'
    assemble(game, app)
    local = {path.stem for path in app.glob('*.py')}
    for path in app.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split('.')[0]]
            for name in names:
                assert name in local | STDLIB_OR_PYGAME, f'{path.name} imports {name}'


def test_slugs_are_unique() -> None:
    assert len({game.slug for game in GAMES}) == len(GAMES)


def test_pygbag_command() -> None:
    game = GAMES[0]
    build = pygbag_command(game, Path('/x/app'))
    assert build[1:4] == ['-m', 'pygbag', '--build']
    assert build[-1] == '/x/app'
    assert game.title in build
    assert '--build' not in pygbag_command(game, Path('/x/app'), serve=True)


def test_landing_page_links_every_game() -> None:
    page = landing_page(GAMES)
    for game in GAMES:
        assert f'href="{game.slug}/"' in page
    assert 'name="viewport"' in page


def test_build_site_collects_each_game(tmp_path: Path) -> None:
    build_dir, site_dir = tmp_path / 'build', tmp_path / 'site'
    for game in GAMES:
        web = app_dir(game, build_dir) / 'build' / 'web'
        web.mkdir(parents=True)
        (web / 'index.html').write_text(game.title)
    build_site(GAMES, build_dir, site_dir)
    for game in GAMES:
        assert (site_dir / game.slug / 'index.html').read_text() == game.title
    assert (site_dir / 'index.html').is_file()
