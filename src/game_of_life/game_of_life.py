'''Conway's Game of Life with a pattern picker; runs on desktop and in the browser.

Start screen: up/down (or click) to pick a pattern, enter to load it.
Board: space run/pause, n step once, click toggles cells while paused,
+/- speed, r reload pattern, c clear, esc back to the pattern picker.

The loops are async and yield once per frame so the same code runs in the
browser through pygbag (see tools/build_life_web.py).
'''

import asyncio
import sys
from pathlib import Path

# Shared modules (pixel font) live in src/shared; the web build copies them alongside.
sys.path.append(str(Path(__file__).resolve().parents[1] / 'shared'))

import pixelfont
import pygame
from life import Cell, cell_at, next_generation, toggle
from patterns import CATALOGUE, Pattern, build

WEB = sys.platform == 'emscripten'

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
DISPLAY_SIZE = (BOARD_SIZE, BOARD_SIZE + STATUS_HEIGHT)

MENU_TOP = 96
MENU_ROW = 34
PREVIEW = pygame.Rect(BOARD_SIZE - 232, MENU_TOP - 4, 214, 214)
DESCRIPTION_CHARS = 17  # fits PREVIEW.width at font scale 2


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


def draw_menu(display: pygame.Surface, selected: int) -> None:
    display.fill(BACKGROUND)
    pixelfont.draw(display, 'GAME OF LIFE', (20, 18), ACCENT, 4, shadow=SHADOW)
    pixelfont.draw(display, 'UP/DOWN + ENTER, OR CLICK', (20, 60), MUTED, 2)
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
        pixelfont.draw(display, line, (PREVIEW.left, PREVIEW.bottom + 16 + i * 22), TEXT, 2)
    pygame.display.update()


async def pick_pattern(display: pygame.Surface, selected: int) -> int:
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
            if event.type == pygame.MOUSEMOTION:
                index = menu_index_at(event.pos)
                if index is not None:
                    selected = index
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = menu_index_at(event.pos)
                if index is not None:
                    return index
        draw_menu(display, selected)
        clock.tick(FPS)
        await asyncio.sleep(0)


# -- board -----------------------------------------------------------------


def draw_board(display: pygame.Surface, cells: set[Cell], pattern: Pattern, status: str) -> None:
    display.fill(BACKGROUND)
    for row in range(AMOUNT):
        for column in range(AMOUNT):
            color = ALIVE_CELL if (row, column) in cells else DEAD_CELL
            rect = (column * (SIZE + GAP), row * (SIZE + GAP), SIZE, SIZE)
            pygame.draw.rect(display, color, rect)
    pixelfont.draw(display, status, (8, BOARD_SIZE + 11), TEXT, 2)
    hint = 'SPC N +/- R C ESC'
    width, _ = pixelfont.text_size(hint)
    pixelfont.draw(display, pattern.name, (BOARD_SIZE - 8 - width, BOARD_SIZE + 8), ACCENT)
    pixelfont.draw(display, hint, (BOARD_SIZE - 8 - width, BOARD_SIZE + 21), MUTED)
    pygame.display.update()


async def play(display: pygame.Surface, pattern: Pattern) -> None:
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
            if event.type == pygame.QUIT and should_quit():
                quit_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not running:
                cell = cell_at(*event.pos, SIZE, GAP, AMOUNT)
                if cell is not None:
                    cells = toggle(cells, cell)
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_SPACE:
                running = not running and bool(cells)
            elif event.key == pygame.K_n and not running:
                step_once = True
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                speed = min(len(SPEEDS) - 1, speed + 1)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                speed = max(0, speed - 1)
            elif event.key == pygame.K_r:
                cells, generation, running = build(pattern, AMOUNT, AMOUNT), 0, False
            elif event.key == pygame.K_c:
                cells, generation, running = set(), 0, False
            elif event.key == pygame.K_ESCAPE:
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
        draw_board(display, cells, pattern, status)
        clock.tick(FPS)
        await asyncio.sleep(0)


async def main() -> None:
    pygame.init()
    pygame.display.set_caption('Game of life')
    display = pygame.display.set_mode(DISPLAY_SIZE)
    selected = 0
    while True:
        selected = await pick_pattern(display, selected)
        await play(display, CATALOGUE[selected])


if __name__ == '__main__':
    asyncio.run(main())
