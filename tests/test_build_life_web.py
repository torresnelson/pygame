import ast
from pathlib import Path

from build_life_web import MAIN, SOURCES, assemble, pygbag_command


def test_sources_exist() -> None:
    assert all(source.is_file() for source in SOURCES)


def test_assemble_copies_sources_and_writes_main(tmp_path: Path) -> None:
    app = tmp_path / 'app'
    (app / 'stale').mkdir(parents=True)
    files = assemble(app)
    names = sorted(path.name for path in app.iterdir())
    assert names == sorted([*(s.name for s in SOURCES), 'main.py'])
    assert len(files) == len(SOURCES) + 1
    assert (app / 'main.py').read_text() == MAIN


def test_main_imports_pygame_before_the_game() -> None:
    '''pygbag only sets up pygame when main.py itself imports it.'''
    imports = [
        alias.name
        for node in ast.parse(MAIN).body
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    assert imports.index('pygame') < imports.index('game_of_life')


def test_assembled_app_imports_resolve_within_the_folder(tmp_path: Path) -> None:
    '''Every local import in the app must be satisfied by a file in the folder.'''
    app = tmp_path / 'app'
    assemble(app)
    local = {path.stem for path in app.glob('*.py')}
    stdlib_or_pygame = {'asyncio', 'sys', 'pathlib', 'random', 'dataclasses', 'functools',
                        'collections', 'pygame'}
    for path in app.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split('.')[0]]
            for name in names:
                assert name in local | stdlib_or_pygame, f'{path.name} imports {name}'


def test_pygbag_command() -> None:
    build = pygbag_command(Path('/x/app'))
    assert build[1:4] == ['-m', 'pygbag', '--build']
    assert build[-1] == '/x/app'
    assert '--build' not in pygbag_command(Path('/x/app'), serve=True)
