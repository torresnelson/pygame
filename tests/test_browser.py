import pytest
from browser import WEB, fit_box, is_portrait, keep_fitted, load_text


@pytest.mark.parametrize(
    ('outer', 'size', 'box'),
    [
        # portrait phone, portrait tetris: fills the width, centred vertically
        ((390, 844), (800, 1520), (0, (844 - 741) / 2, 390, 741)),
        # landscape phone, landscape tetris: fills the height, centred horizontally
        ((844, 390), (800, 700), ((844 - 390 * 800 / 700) / 2, 0, 390 * 800 / 700, 390)),
        ((800, 700), (800, 700), (0, 0, 800, 700)),
    ],
)
def test_fit_box_keeps_the_aspect_and_centres(outer: tuple, size: tuple, box: tuple) -> None:
    assert fit_box(*outer, *size) == pytest.approx(box, abs=0.6)


def test_desktop_fallbacks() -> None:
    assert not WEB
    assert is_portrait() is False
    assert load_text('anything') is None


def test_keep_fitted_is_a_no_op_on_desktop() -> None:
    keep_fitted(800, 600, 10_000)
