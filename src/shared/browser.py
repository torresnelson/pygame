'''Browser glue for the pygbag builds; every function is a no-op on desktop.'''

import sys

WEB = sys.platform == 'emscripten'


def _window() -> object:
    # pygbag replaces `platform` with a module whose `window` is the JS window.
    import platform

    return platform.window


VIEWPORT = 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'
# pygbag's page has two viewport tags and the second drops `width=device-width`,
# so a phone may lay the page out wider than the screen.
VIEWPORT_JS = (
    "document.querySelectorAll('meta[name=viewport]')"
    f".forEach(meta => meta.setAttribute('content', '{VIEWPORT}'))"
)
# Some browsers (Firefox for Android) still zoom on a double tap or a pinch;
# cancel those gestures page-wide. The game's own listeners on the canvas run
# first, so taps still reach it.
NO_ZOOM_JS = '''(() => {
  if (window.__noZoom) return;
  window.__noZoom = true;
  const options = {passive: false};
  let lastTouchEnd = 0;
  document.addEventListener('touchend', event => {
    const now = Date.now();
    if (now - lastTouchEnd < 400) event.preventDefault();
    lastTouchEnd = now;
  }, options);
  document.addEventListener('touchmove', event => {
    if (event.touches.length > 1) event.preventDefault();
  }, options);
  document.addEventListener('dblclick', event => event.preventDefault(), options);
  for (const name of ['gesturestart', 'gesturechange']) {
    document.addEventListener(name, event => event.preventDefault(), options);
  }
})()'''
FIT_EVERY_MS = 250
_last_fit_ms = -FIT_EVERY_MS


def prepare_page(background: str = '#000') -> None:
    '''Keep touch gestures on the game (no scrolling, zooming or pull-to-refresh)
    and drop the loading screen now that the game is running.'''
    if not WEB:
        return
    try:
        window = _window()
        document = window.document
        for style in (document.documentElement.style, document.body.style, window.canvas.style):
            style.touchAction = 'none'
            style.overscrollBehavior = 'none'
            style.userSelect = 'none'
            style.webkitUserSelect = 'none'
            style.webkitTouchCallout = 'none'  # no iOS long-press menu on held buttons
        document.documentElement.style.overflow = 'hidden'
        document.body.style.overflow = 'hidden'
        document.body.style.backgroundColor = background
        window.canvas.style.position = 'fixed'
        window.eval(VIEWPORT_JS)
        window.eval(NO_ZOOM_JS)
        window.eval('window.hide_loading && window.hide_loading()')  # see tools/web_template.tmpl
    except Exception as error:  # the game still works, just with a scrollier page
        print(f'prepare_page: {error}')


def is_portrait() -> bool:
    '''True when the browser window is taller than wide (always False on desktop).'''
    if not WEB:
        return False
    try:
        window = _window()
        return int(window.innerHeight) > int(window.innerWidth)
    except Exception:
        return False


def fit_box(outer_w: float, outer_h: float, width: int, height: int
            ) -> tuple[float, float, float, float]:
    '''Largest box with the aspect of `width` x `height` centred in the outer box.'''
    scale = min(outer_w / width, outer_h / height)
    w, h = width * scale, height * scale
    return (outer_w - w) / 2, (outer_h - h) / 2, w, h


def fit_canvas(width: int, height: int) -> None:
    '''Size and centre the canvas on the page for a `width` x `height` display.

    pygbag fits the canvas on the browser's resize event, which fires before a
    game notices a rotation and calls `set_mode` with the new shape, so a game
    that changes shape re-fits the canvas itself.
    '''
    if not WEB:
        return
    try:
        window = _window()
        x, y, w, h = fit_box(float(window.innerWidth), float(window.innerHeight), width, height)
        style = window.canvas.style
        style.width, style.height = f'{w}px', f'{h}px'
        style.left, style.top = f'{x}px', f'{y}px'
        style.right = style.bottom = 'auto'
        style.margin = '0'
    except Exception as error:
        print(f'fit_canvas: {error}')


def keep_fitted(width: int, height: int, now_ms: int) -> None:
    '''Call every frame: re-fit the canvas a few times a second.

    Some phones (Firefox for Android) lay the page out wider than the screen
    until `prepare_page` fixes the viewport, and pygbag has sized the canvas
    for that wider page by then; re-fitting corrects it within a moment.
    '''
    global _last_fit_ms
    if not WEB or now_ms - _last_fit_ms < FIT_EVERY_MS:
        return
    _last_fit_ms = now_ms
    fit_canvas(width, height)


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
