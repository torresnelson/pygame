import ast
from pathlib import Path

import pytest
from build_web import GAMES, GAMES_BY_PATH, assemble, landing_page, main_py, pygbag_command, select
from build_web import stage_site as stage

STDLIB_OR_PYGAME = {
    'asyncio', 'sys', 'pathlib', 'random', 'dataclasses', 'functools', 'collections',
    'enum', 'json', 'datetime', 'platform', 'pygame',
}


def test_site_paths() -> None:
    assert [game.path for game in GAMES] == ['gameoflife', 'tetris', 'sandsimulator']


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.path)
def test_sources_exist_and_include_entry_module(game) -> None:
    assert all(source.is_file() for source in game.sources)
    assert f'{game.module}.py' in {source.name for source in game.sources}


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.path)
def test_assemble_copies_sources_and_writes_main(game, tmp_path: Path) -> None:
    app = tmp_path / game.path
    (app / 'stale').mkdir(parents=True)
    files = assemble(game, app)
    assert sorted(p.name for p in app.iterdir()) == sorted(
        [*(s.name for s in game.sources), 'main.py']
    )
    assert len(files) == len(game.sources) + 1
    assert (app / 'main.py').read_text() == main_py(game)


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.path)
def test_assembled_app_imports_resolve_within_the_folder(game, tmp_path: Path) -> None:
    '''Every local import in the app must be satisfied by a file in the folder.'''
    app = tmp_path / game.path
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


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.path)
def test_main_imports_pygame_before_the_game_and_runs_its_main(game) -> None:
    '''pygbag only sets up pygame when main.py itself imports it.'''
    tree = ast.parse(main_py(game))
    imports = [alias.name for node in tree.body if isinstance(node, ast.Import)
               for alias in node.names]
    assert imports.index('pygame') < imports.index(game.module)
    assert f'asyncio.run({game.module}.main())' in main_py(game)


@pytest.mark.parametrize('game', GAMES, ids=lambda game: game.path)
def test_entry_module_has_async_main(game) -> None:
    entry = next(s for s in game.sources if s.name == f'{game.module}.py')
    tree = ast.parse(entry.read_text())
    assert any(isinstance(node, ast.AsyncFunctionDef) and node.name == 'main'
               for node in tree.body)


def test_stage_site_layout_and_landing_page(tmp_path: Path) -> None:
    build = tmp_path / 'build'
    for game in GAMES:
        web = build / game.path / 'build' / 'web'
        web.mkdir(parents=True)
        (web / 'index.html').write_text(game.title)
        (web / f'{game.path}.apk').write_bytes(b'apk')
    site = tmp_path / 'site'
    (site / 'stale').mkdir(parents=True)

    staged = stage(GAMES, build, site)

    assert [p.name for p in staged] == [game.path for game in GAMES]
    assert sorted(p.name for p in site.iterdir()) == sorted(
        ['index.html', *(game.path for game in GAMES)]
    )
    for game in GAMES:
        assert (site / game.path / 'index.html').read_text() == game.title
    landing = (site / 'index.html').read_text()
    for game in GAMES:
        assert f'href="{game.path}/"' in landing
        assert game.title in landing


def test_landing_page_escapes_text() -> None:
    from build_web import Game

    page = landing_page((Game('x', 'x', 'A <b> & C', ()),))
    assert 'A &lt;b&gt; &amp; C' in page


def test_landing_page_is_just_the_game_boxes() -> None:
    page = landing_page()
    body = page[page.index('<body>'):]
    assert body.count('<li>') == len(GAMES)
    for game in GAMES:
        assert f'<li><a href="{game.path}/"><strong>{game.title}</strong></a></li>' in body
    for gone in ('<h1>', 'Pick a game', '<footer>', 'Made with pygame', '<span>'):
        assert gone not in page, gone


def test_select() -> None:
    assert select([]) == GAMES
    assert select(['tetris']) == (GAMES_BY_PATH['tetris'],)
    with pytest.raises(SystemExit):
        select(['pong'])


def test_pygbag_command() -> None:
    game = GAMES_BY_PATH['tetris']
    build = pygbag_command(game, Path('/x/tetris'))
    assert build[1:4] == ['-m', 'pygbag', '--build']
    assert build[-1] == '/x/tetris'
    assert 'Tetris' in build
    assert '--build' not in pygbag_command(game, Path('/x/tetris'), serve=True)
