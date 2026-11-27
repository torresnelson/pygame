import re
from pathlib import Path

from build_web import GAMES_BY_PATH, TEMPLATE, pygbag_command


def template() -> str:
    return TEMPLATE.read_text()


def test_pygbag_builds_with_the_template() -> None:
    build = pygbag_command(GAMES_BY_PATH['tetris'], Path('/x/tetris'))
    assert build[build.index('--template') + 1] == str(TEMPLATE)
    assert TEMPLATE.is_file()


def test_template_keeps_what_pygbag_needs() -> None:
    page = template()
    assert page.startswith('<html lang="en-us"><script src="{{cookiecutter.cdn}}pythons.js"')
    for needed in ('async def custom_site():', '{{cookiecutter.archive}}', '# BEGIN BLOCK',
                   'id="canvas"', 'id="progress"', 'id="status"', 'id="infobox"',
                   'id="transfer"', 'function custom_onload'):
        assert needed in page, needed


def test_template_has_a_loading_screen_that_the_game_removes() -> None:
    page = template()
    assert 'id="loading"' in page
    assert '<h1>{{cookiecutter.title}}</h1>' in page
    assert 'window.hide_loading = ' in page
    assert 'platform.window.hide_loading()' in page


def test_only_placeholders_pygbag_fills_are_used() -> None:
    '''pygbag only replaces {{cookiecutter.<key>}}; anything else would leak into the page.'''
    keys = set(re.findall(r'\{\{cookiecutter\.(\w+)\}\}', template()))
    known = {'cdn', 'PYBUILD', 'title', 'archive', 'version', 'width', 'height', 'directory',
             'authors', 'spdx', 'comment', 'xtermjs', 'ume_block', 'can_close', 'autorun'}
    assert keys <= known
    assert '{{' not in re.sub(r'\{\{cookiecutter\.\w+\}\}', '', template())


def test_one_phone_friendly_viewport_and_a_dark_page() -> None:
    viewports = re.findall(r'<meta name="viewport" content="([^"]+)"', template())
    assert len(viewports) == 1
    assert 'width=device-width' in viewports[0]
    assert 'powderblue' not in template()
