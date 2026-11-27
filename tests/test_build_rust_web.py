import re
from pathlib import Path

from build_rust_web import (
    OUTPUT_NAME,
    PROFILE,
    RUST,
    RUST_GAMES,
    TEMPLATE,
    bindgen_command,
    build_command,
    page,
    wasm_path,
)


def test_every_rust_game_is_a_workspace_crate() -> None:
    for game in RUST_GAMES:
        manifest = RUST / 'games' / game.crate / 'Cargo.toml'
        assert f'name = "{game.crate}"' in manifest.read_text()


def test_the_size_profile_exists() -> None:
    assert f'[profile.{PROFILE}]' in (RUST / 'Cargo.toml').read_text()


def test_commands_build_bind_and_name_the_output(tmp_path: Path) -> None:
    game = RUST_GAMES[0]
    build = build_command(game)
    assert build[:2] == ['cargo', 'build'] and build[-1] == game.crate
    assert ['--profile', PROFILE] == build[2:4]
    bindgen = bindgen_command(game, tmp_path)
    assert bindgen[0] == 'wasm-bindgen' and bindgen[-1] == str(wasm_path(game))
    assert bindgen[bindgen.index('--out-name') + 1] == OUTPUT_NAME


def test_page_fills_title_and_module_name() -> None:
    html = page('Game of Life')
    assert '<title>Game of Life</title>' in html
    assert f"import init from './{OUTPUT_NAME}.js';" in html
    assert f"'./{OUTPUT_NAME}_bg.wasm'" in html
    assert '{{' not in html


def test_page_has_the_canvas_loading_screen_and_phone_settings() -> None:
    html = TEMPLATE.read_text()
    assert '<canvas id="bevy"' in html  # sandbox_ui::CANVAS_SELECTOR
    assert 'window.hide_loading = ' in html  # called by sandbox_ui::web::hide_loading
    viewports = re.findall(r'<meta name="viewport" content="([^"]+)"', html)
    assert len(viewports) == 1 and 'width=device-width' in viewports[0]
    assert 'touch-action: none' in html
