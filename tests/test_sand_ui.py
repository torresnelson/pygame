import pixelfont
from materials import Material

from sand_simulator import HELP, status_text


def test_status_text() -> None:
    assert status_text(Material.SAND, 3, 59.6, False) == 'SAND  BRUSH 3  60 FPS'
    assert status_text(Material.WATER, 0, 30, True).endswith('PAUSED')


def test_hud_text_only_uses_characters_the_pixel_font_can_draw() -> None:
    for text in (HELP, status_text(Material.STONE, 12, 60, True)):
        assert set(text.upper()) <= pixelfont.CHARSET, text
