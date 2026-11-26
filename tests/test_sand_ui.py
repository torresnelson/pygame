from materials import Material

from sand_simulator import (
    FILL,
    KEY_ACTIONS,
    MAX_BRUSH,
    MIN_BRUSH,
    S_HEIGHT,
    TOOLBAR,
    TOOLS,
    WINDOW_SIZE,
    in_world,
    resize_brush,
    tool_name,
)


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
