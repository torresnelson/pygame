import pixelfont
import pytest
from materials import Material

from sand_simulator import (
    FILL,
    HELP,
    KEY_ACTIONS,
    LANDSCAPE,
    MAX_BRUSH,
    MIN_BRUSH,
    PORTRAIT,
    S_HEIGHT,
    TOOLBAR,
    TOOLS,
    WINDOW_SIZE,
    Layout,
    in_world,
    pick_layout,
    resize_brush,
    status_text,
    tool_name,
)


def test_status_text() -> None:
    assert status_text(Material.SAND, 3, 59.6, False) == 'SAND  BRUSH 3  60 FPS'
    assert status_text(Material.WATER, 0, 30, True).endswith('PAUSED')
    assert status_text(Material.EMPTY, 2, 60, False).startswith('ERASER')


def test_hud_text_only_uses_characters_the_pixel_font_can_draw() -> None:
    texts = [HELP, status_text(Material.STONE, 12, 60, True), 'TAP TO START', 'PLAY']
    texts += [button.label for button in TOOLBAR]
    for text in texts:
        assert set(text.upper()) <= pixelfont.CHARSET, text


def test_toolbar_sits_below_the_world_inside_the_window() -> None:
    width, height = WINDOW_SIZE
    for button in TOOLBAR:
        x, y, w, h = button.rect
        assert y >= S_HEIGHT
        assert x >= 0 and x + w <= width and y + h <= height


def test_every_key_has_a_button_and_every_tool_can_paint() -> None:
    assert set(KEY_ACTIONS.values()) == {button.action for button in TOOLBAR}
    assert all(tool in FILL for tool in TOOLS.values())


def test_in_world() -> None:
    assert in_world((10, 0))
    assert in_world((10, S_HEIGHT - 1))
    assert not in_world((10, S_HEIGHT))


def test_resize_brush_is_clamped() -> None:
    assert resize_brush(3, 'bigger') == 4
    assert resize_brush(3, 'smaller') == 2
    assert resize_brush(MAX_BRUSH, 'bigger') == MAX_BRUSH
    assert resize_brush(MIN_BRUSH, 'smaller') == MIN_BRUSH


def test_tool_name() -> None:
    assert tool_name(Material.SAND) == 'sand'
    assert tool_name(Material.EMPTY) == 'eraser'


LAYOUTS = (LANDSCAPE, PORTRAIT)


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@pytest.mark.parametrize('layout', LAYOUTS, ids=lambda layout: layout.name)
def test_layout_toolbar_fits_below_the_world(layout: Layout) -> None:
    width, height = layout.size
    for button in layout.toolbar:
        x, y, w, h = button.rect
        assert y >= layout.world_size[1], button.action
        assert x >= 0 and x + w <= width and y + h <= height, button.action
        assert not in_world((x + 1, y + 1), layout)
    for i, a in enumerate(layout.toolbar):
        for b in layout.toolbar[i + 1:]:
            assert not overlaps(a.rect, b.rect), (a.action, b.action)
    assert {button.action for button in layout.toolbar} == set(KEY_ACTIONS.values())


def test_portrait_is_tall_with_the_same_cell_count_and_bigger_buttons() -> None:
    assert PORTRAIT.size[1] > PORTRAIT.size[0]
    columns, rows = PORTRAIT.cells
    assert columns * rows == LANDSCAPE.cells[0] * LANDSCAPE.cells[1]
    assert min(b.rect[3] for b in PORTRAIT.toolbar) > 2 * max(b.rect[3] for b in TOOLBAR)
    assert PORTRAIT.status_scale > LANDSCAPE.status_scale


def test_in_world_depends_on_the_layout() -> None:
    assert in_world((700, 100), LANDSCAPE)
    assert not in_world((700, 100), PORTRAIT)
    assert in_world((100, 700), PORTRAIT)
    assert not in_world((100, 700), LANDSCAPE)


def test_pick_layout() -> None:
    assert pick_layout(True) is PORTRAIT
    assert pick_layout(False) is LANDSCAPE
