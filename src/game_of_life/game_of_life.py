'''Conway's Game of Life with a pattern picker; runs on desktop and in the browser.

Start screen: up/down (or click) to pick a pattern, enter or START to load
it. On a touch screen a tap previews a pattern and START loads it.
Board: space run/pause, n step once, click toggles cells while paused,
+/- speed, r reload pattern, c clear, esc back to the pattern picker. The
button bar under the board does the same with a tap.

A phone held upright gets a portrait layout (taller canvas, two rows of big
buttons); the layout follows the phone when it is turned. On desktop,
`--portrait` shows that layout.

The loops are async and yield once per frame so the same code runs in the
browser through pygbag (see tools/build_web.py).
'''

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Shared modules (pixel font) live in src/shared; the web build copies them alongside.
sys.path.append(str(Path(__file__).resolve().parents[1] / 'shared'))

import pixelfont
import pygame
from browser import WEB, fit_canvas, is_portrait, prepare_page
from life import Cell, cell_at, next_generation, toggle
from patterns import CATALOGUE, Pattern, build
from touch import Button, button_at, button_row, is_touch

BACKGROUND = (10, 10, 14)
DEAD_CELL = (24, 24, 30)
ALIVE_CELL = (195, 195, 195)
HIGHLIGHT = (40, 40, 70)
ACCENT = (120, 200, 255)
GOLD = (248, 184, 0)
TEXT = (230, 230, 230)
MUTED = (130, 130, 150)
SHADOW = (20, 40, 70)

# Can change those if you want
AMOUNT = 50
SIZE = 12
GAP = 1
SPEEDS = (1, 2, 5, 10, 20, 30, 60)
DEFAULT_SPEED = 3  # index into SPEEDS -> 10 generations per second
FPS = 60

BOARD_SIZE = AMOUNT * SIZE + (AMOUNT - 1) * GAP
STATUS_HEIGHT = 36
BAR_TOP = BOARD_SIZE + STATUS_HEIGHT
BAR_HEIGHT = 56
DISPLAY_SIZE = (BOARD_SIZE, BAR_TOP + BAR_HEIGHT)
ORIENTATION_CHECK_MS = 250

BOARD_BUTTONS = button_row(
    (('run', 'RUN'), ('step', 'STEP'), ('slower', '-'), ('faster', '+'),
     ('reset', 'RESET'), ('clear', 'CLEAR'), ('back', 'BACK')),
    8, BAR_TOP, BOARD_SIZE - 16, BAR_HEIGHT - 8, 8,
)
KEY_ACTIONS = {
    pygame.K_SPACE: 'run',
    pygame.K_n: 'step',
    pygame.K_PLUS: 'faster',
    pygame.K_EQUALS: 'faster',
    pygame.K_KP_PLUS: 'faster',
    pygame.K_MINUS: 'slower',
    pygame.K_KP_MINUS: 'slower',
    pygame.K_r: 'reset',
    pygame.K_c: 'clear',
    pygame.K_ESCAPE: 'back',
}

MENU_TOP = 96
MENU_ROW = 34
PREVIEW = pygame.Rect(BOARD_SIZE - 232, MENU_TOP - 4, 214, 214)
DESCRIPTION_CHARS = 17  # fits PREVIEW.width at font scale 2
DESCRIPTION_ROW = 22


@dataclass(frozen=True)
class Layout:
    '''Window size and touch targets for one orientation.'''

    name: str
    size: tuple[int, int]
    buttons: tuple[Button, ...]  # board controls
    start: Button  # loads the selected pattern from the picker
    label_scale: int


LANDSCAPE = Layout(
    name='landscape',
    size=DISPLAY_SIZE,
    buttons=BOARD_BUTTONS,
    start=Button('start', 'START', (PREVIEW.left, 452, PREVIEW.width, 48)),
    label_scale=2,
)

# Portrait: same board, then two rows of thumb-sized buttons under it.
PORTRAIT_ROW = 150
PORTRAIT = Layout(
    name='portrait',
    size=(BOARD_SIZE, BAR_TOP + 2 * PORTRAIT_ROW + 3 * 8),
    buttons=(
        button_row((('run', 'RUN'), ('step', 'STEP'), ('slower', '-'), ('faster', '+')),
                   8, BAR_TOP + 8, BOARD_SIZE - 16, PORTRAIT_ROW, 8)
        + button_row((('reset', 'RESET'), ('clear', 'CLEAR'), ('back', 'BACK')),
                     8, BAR_TOP + 16 + PORTRAIT_ROW, BOARD_SIZE - 16, PORTRAIT_ROW, 8)
    ),
    start=Button('start', 'START', (8, BAR_TOP + 16 + PORTRAIT_ROW, BOARD_SIZE - 16,
                                    PORTRAIT_ROW)),
    label_scale=3,
)


@dataclass
class Screen:
    display: pygame.Surface
    layout: Layout
    checked_ms: int = 0


def pick_layout(portrait: bool) -> Layout:
    return PORTRAIT if portrait else LANDSCAPE


def make_screen(layout: Layout) -> Screen:
    return Screen(pygame.display.set_mode(layout.size), layout, pygame.time.get_ticks())


def follow_orientation(screen: Screen) -> None:
    '''In the browser, switch layouts when the phone is turned and keep the canvas fitted.'''
    now = pygame.time.get_ticks()
    if not WEB or now - screen.checked_ms < ORIENTATION_CHECK_MS:
        return
    screen.checked_ms = now
    layout = pick_layout(is_portrait())
    if layout != screen.layout:
        screen.display = pygame.display.set_mode(layout.size)
        screen.layout = layout
    fit_canvas(*screen.layout.size)


def wrap(value: str, width: int) -> list[str]:
    '''Greedy word wrap to lines of at most `width` characters.'''
    lines: list[str] = []
    line = ''
    for word in value.split():
        candidate = f'{line} {word}' if line else word
        if len(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def status_text(generation: int, population: int, speed: int, running: bool) -> str:
    state = 'RUN' if running else 'PAUSE'
    return f'GEN {generation}  POP {population}  {speed}/S  {state}'


def should_quit() -> bool:
    '''Closing the window quits on desktop; a browser tab has nothing to quit to.'''
    return not WEB


def quit_game() -> None:
    pygame.quit()
    sys.exit()


# -- pattern picker ----------------------------------------------------------


def pick_tap(index: int, touch: bool) -> tuple[int, bool]:
    '''Handle a click on menu row `index`: return (selected, start it?).

    A mouse hovers before it clicks, so a click starts right away. A finger
    cannot hover, so a tap only selects (to show the preview) and START loads
    it; asking for a second tap would be a double tap, which some phone
    browsers turn into a zoom.
    '''
    return index, not touch


def menu_index_at(pos: tuple[int, int]) -> int | None:
    x, y = pos
    index = (y - MENU_TOP + 8) // MENU_ROW
    if x < PREVIEW.left - 8 and y >= MENU_TOP - 8 and 0 <= index < len(CATALOGUE):
        return index
    return None


def draw_preview(display: pygame.Surface, pattern: Pattern) -> None:
    pygame.draw.rect(display, DEAD_CELL, PREVIEW)
    pygame.draw.rect(display, MUTED, PREVIEW, 1)
    cells = pattern.cells
    if not cells:
        label = 'RANDOM' if pattern.kind == 'random' else 'EMPTY'
        pixelfont.draw(display, label, PREVIEW.center, MUTED, 2, center=True)
        return
    height, width = pattern.size
    cell = max(2, min(20, (PREVIEW.width - 20) // max(height, width)))
    left = PREVIEW.centerx - width * cell // 2
    top = PREVIEW.centery - height * cell // 2
    for r, c in cells:
        pygame.draw.rect(display, ALIVE_CELL, (left + c * cell, top + r * cell, cell - 1, cell - 1))


def draw_button(display: pygame.Surface, button: Button, label: str, scale: int,
                color: tuple = TEXT) -> None:
    pygame.draw.rect(display, HIGHLIGHT, button.rect)
    pygame.draw.rect(display, MUTED, button.rect, 1)
    pixelfont.draw(display, label, pygame.Rect(button.rect).center, color, scale, center=True)


def draw_menu(display: pygame.Surface, layout: Layout, selected: int) -> None:
    display.fill(BACKGROUND)
    pixelfont.draw(display, 'GAME OF LIFE', (20, 18), ACCENT, 4, shadow=SHADOW)
    hint = 'TAP A PATTERN, THEN START' if WEB else 'UP/DOWN + ENTER, OR CLICK'
    pixelfont.draw(display, hint, (20, 60), MUTED, 2)
    for i, pattern in enumerate(CATALOGUE):
        y = MENU_TOP + i * MENU_ROW
        if i == selected:
            pygame.draw.rect(display, HIGHLIGHT, (12, y - 9, PREVIEW.left - 20, MENU_ROW - 2))
            pixelfont.draw(display, '>', (16, y), GOLD, 2)
        color = TEXT if i == selected else MUTED
        pixelfont.draw(display, pattern.name, (32, y), color, 2)
        pixelfont.draw(display, pattern.kind, (300, y + 4), MUTED)
    pattern = CATALOGUE[selected]
    draw_preview(display, pattern)
    for i, line in enumerate(wrap(pattern.description, DESCRIPTION_CHARS)):
        y = PREVIEW.bottom + 16 + i * DESCRIPTION_ROW
        pixelfont.draw(display, line, (PREVIEW.left, y), TEXT, 2)
    draw_button(display, layout.start, layout.start.label, layout.label_scale, GOLD)
    pygame.display.update()


async def pick_pattern(screen: Screen, selected: int) -> int:
    '''Show the picker until a pattern is chosen; return its index.'''
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT and should_quit():
                quit_game()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_k):
                    selected = (selected - 1) % len(CATALOGUE)
                elif event.key in (pygame.K_DOWN, pygame.K_j):
                    selected = (selected + 1) % len(CATALOGUE)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return selected
                elif event.key == pygame.K_ESCAPE and should_quit():
                    quit_game()
            if event.type == pygame.MOUSEMOTION and not is_touch(event):
                index = menu_index_at(event.pos)
                if index is not None:
                    selected = index
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if screen.layout.start.contains(event.pos):
                    return selected
                index = menu_index_at(event.pos)
                if index is not None:
                    selected, start = pick_tap(index, is_touch(event))
                    if start:
                        return selected
        draw_menu(screen.display, screen.layout, selected)
        follow_orientation(screen)
        clock.tick(FPS)
        await asyncio.sleep(0)


# -- board -----------------------------------------------------------------


def draw_board(display: pygame.Surface, layout: Layout, cells: set[Cell], pattern: Pattern,
               status: str, running: bool) -> None:
    display.fill(BACKGROUND)
    for row in range(AMOUNT):
        for column in range(AMOUNT):
            color = ALIVE_CELL if (row, column) in cells else DEAD_CELL
            rect = (column * (SIZE + GAP), row * (SIZE + GAP), SIZE, SIZE)
            pygame.draw.rect(display, color, rect)
    pixelfont.draw(display, status, (8, BOARD_SIZE + 11), TEXT, 2)
    hint = '' if WEB else 'SPC N +/- R C ESC'
    width = max(pixelfont.text_size(hint)[0], pixelfont.text_size(pattern.name)[0])
    pixelfont.draw(display, pattern.name, (BOARD_SIZE - 8 - width, BOARD_SIZE + 8), ACCENT)
    pixelfont.draw(display, hint, (BOARD_SIZE - 8 - width, BOARD_SIZE + 21), MUTED)
    for button in layout.buttons:
        label = 'PAUSE' if running and button.action == 'run' else button.label
        draw_button(display, button, label, layout.label_scale)
    pygame.display.update()


async def play(screen: Screen, pattern: Pattern) -> None:
    '''Run the board for `pattern`; returns when the player goes back to the picker.'''
    clock = pygame.time.Clock()
    cells = build(pattern, AMOUNT, AMOUNT)
    generation = 0
    running = False
    speed = DEFAULT_SPEED
    last_step = 0

    while True:
        step_once = False
        for event in pygame.event.get():
            action = None
            if event.type == pygame.QUIT and should_quit():
                quit_game()
            if event.type == pygame.KEYDOWN:
                action = KEY_ACTIONS.get(event.key)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = button_at(screen.layout.buttons, event.pos)
                cell = cell_at(*event.pos, SIZE, GAP, AMOUNT)
                if action is None and cell is not None and not running:
                    cells = toggle(cells, cell)
            if action == 'run':
                running = not running and bool(cells)
            elif action == 'step' and not running:
                step_once = True
            elif action == 'faster':
                speed = min(len(SPEEDS) - 1, speed + 1)
            elif action == 'slower':
                speed = max(0, speed - 1)
            elif action == 'reset':
                cells, generation, running = build(pattern, AMOUNT, AMOUNT), 0, False
            elif action == 'clear':
                cells, generation, running = set(), 0, False
            elif action == 'back':
                return

        now = pygame.time.get_ticks()
        due = running and now - last_step >= 1000 / SPEEDS[speed]
        if due or step_once:
            cells = next_generation(cells, AMOUNT, AMOUNT)
            generation += 1
            last_step = now
            # Everything died: go back to editing instead of running empty.
            running = running and bool(cells)

        status = status_text(generation, len(cells), SPEEDS[speed], running)
        draw_board(screen.display, screen.layout, cells, pattern, status, running)
        follow_orientation(screen)
        clock.tick(FPS)
        await asyncio.sleep(0)


async def main() -> None:
    pygame.init()
    prepare_page()
    pygame.display.set_caption('Game of life')
    portrait = is_portrait() if WEB else '--portrait' in sys.argv
    screen = make_screen(pick_layout(portrait))
    selected = 0
    while True:
        selected = await pick_pattern(screen, selected)
        await play(screen, CATALOGUE[selected])


if __name__ == '__main__':
    asyncio.run(main())
