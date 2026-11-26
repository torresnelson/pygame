'''Browser glue for the pygbag builds; every function is a no-op on desktop.'''

import sys

WEB = sys.platform == 'emscripten'


def _window() -> object:
    # pygbag replaces `platform` with a module whose `window` is the JS window.
    import platform

    return platform.window


def prepare_page(background: str = '#000') -> None:
    '''Keep touch gestures on the game: no scrolling, zooming or pull-to-refresh.'''
    if not WEB:
        return
    try:
        window = _window()
        document = window.document
        for style in (document.documentElement.style, document.body.style, window.canvas.style):
            style.touchAction = 'none'
            style.overscrollBehavior = 'none'
            style.userSelect = 'none'
        document.body.style.backgroundColor = background
    except Exception as error:  # the game still works, just with a scrollier page
        print(f'prepare_page: {error}')


def load_text(key: str) -> str | None:
    '''Read `key` from the browser's localStorage (None on desktop or if missing).'''
    if not WEB:
        return None
    try:
        value = _window().localStorage.getItem(key)
    except Exception:
        return None
    return None if value is None else str(value)


def save_text(key: str, value: str) -> None:
    if not WEB:
        return
    try:
        _window().localStorage.setItem(key, value)
    except Exception as error:
        print(f'save_text: {error}')
