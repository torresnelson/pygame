'''Conway's Game of Life with a pattern picker.

Start screen: up/down (or click) to pick a pattern, enter to load it.
Board: space run/pause, n step once, click toggles cells while paused,
+/- speed, r reload pattern, c clear, esc back to the pattern picker.
'''

import sys
from functools import cache

import pygame
from life import Cell, cell_at, next_generation, toggle
from patterns import CATALOGUE, Pattern, build

BACKGROUND = (10, 10, 14)
DEAD_CELL = (24, 24, 30)
ALIVE_CELL = (195, 195, 195)
HIGHLIGHT = (60, 60, 80)
ACCENT = (120, 200, 255)
TEXT = (230, 230, 230)
MUTED = (140, 140, 150)

# Can change those if you want
AMOUNT = 50
SIZE = 12
GAP = 1
SPEEDS = (1, 2, 5, 10, 20, 30, 60)
DEFAULT_SPEED = 3  # index into SPEEDS -> 10 generations per second

BOARD_SIZE = AMOUNT * SIZE + (AMOUNT - 1) * GAP
STATUS_HEIGHT = 28
DISPLAY_SIZE = (BOARD_SIZE, BOARD_SIZE + STATUS_HEIGHT)

MENU_TOP = 84
MENU_ROW = 34
PREVIEW = pygame.Rect(BOARD_SIZE - 270, MENU_TOP, 250, 250)


@cache
def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont('monospace', size, bold=bold)


def text(display: pygame.Surface, value: str, pos: tuple[int, int], size: int = 16,
         color: tuple = TEXT, bold: bool = False) -> None:
    display.blit(get_font(size, bold).render(value, True, color), pos)


def quit_game() -> None:
    pygame.quit()
    sys.exit()


# -- pattern picker ----------------------------------------------------------


def menu_index_at(pos: tuple[int, int]) -> int | None:
    x, y = pos
    index = (y - MENU_TOP) // MENU_ROW
    if x < PREVIEW.left - 10 and y >= MENU_TOP and 0 <= index < len(CATALOGUE):
        return index
    return None


def draw_preview(display: pygame.Surface, pattern: Pattern) -> None:
    pygame.draw.rect(display, DEAD_CELL, PREVIEW)
    cells = pattern.cells
    if not cells:
        label = 'random' if pattern.kind == 'random' else 'empty'
        text(display, label, (PREVIEW.centerx - 30, PREVIEW.centery - 8), color=MUTED)
        return
    height, width = pattern.size
    cell = max(2, min(20, (PREVIEW.width - 20) // max(height, width)))
    left = PREVIEW.centerx - width * cell // 2
    top = PREVIEW.centery - height * cell // 2
    for r, c in cells:
        pygame.draw.rect(display, ALIVE_CELL, (left + c * cell, top + r * cell, cell - 1, cell - 1))


def draw_menu(display: pygame.Surface, selected: int) -> None:
    display.fill(BACKGROUND)
    text(display, 'Game of Life', (20, 18), 28, ACCENT, bold=True)
    text(display, 'pick a pattern: up/down + enter, or click', (20, 50), 13, MUTED)
    for i, pattern in enumerate(CATALOGUE):
        y = MENU_TOP + i * MENU_ROW
        if i == selected:
            pygame.draw.rect(display, HIGHLIGHT, (12, y - 4, PREVIEW.left - 30, MENU_ROW - 4))
        text(display, pattern.name, (24, y), 17, TEXT, bold=i == selected)
        text(display, pattern.kind, (24 + 250, y + 2), 13, MUTED)
    pattern = CATALOGUE[selected]
    draw_preview(display, pattern)
    words, line, lines = pattern.description.split(), '', []
    for word in words:
        if len(line) + len(word) > 28:
            lines.append(line)
            line = ''
        line += word + ' '
    lines.append(line)
    for i, value in enumerate(lines):
        text(display, value.strip(), (PREVIEW.left, PREVIEW.bottom + 14 + i * 20), 14, TEXT)
    pygame.display.update()


def pick_pattern(display: pygame.Surface, selected: int) -> int:
    '''Show the picker until a pattern is chosen; return its index.'''
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_k):
                    selected = (selected - 1) % len(CATALOGUE)
                elif event.key in (pygame.K_DOWN, pygame.K_j):
                    selected = (selected + 1) % len(CATALOGUE)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return selected
                elif event.key == pygame.K_ESCAPE:
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
        clock.tick(60)


# -- board -----------------------------------------------------------------


def draw_board(display: pygame.Surface, cells: set[Cell], status: str) -> None:
    display.fill(BACKGROUND)
    for row in range(AMOUNT):
        for column in range(AMOUNT):
            color = ALIVE_CELL if (row, column) in cells else DEAD_CELL
            rect = (column * (SIZE + GAP), row * (SIZE + GAP), SIZE, SIZE)
            pygame.draw.rect(display, color, rect)
    text(display, status, (8, BOARD_SIZE + 6), 14, TEXT)
    pygame.display.update()


def play(display: pygame.Surface, pattern: Pattern) -> None:
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
            if event.type == pygame.QUIT:
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

        state = 'running' if running else 'paused'
        status = (
            f'{pattern.name} | gen {generation} | pop {len(cells)} | '
            f'{SPEEDS[speed]}/s | {state} | space n +/- r c esc'
        )
        draw_board(display, cells, status)
        clock.tick(60)


def main(display: pygame.Surface) -> None:
    selected = 0
    while True:
        selected = pick_pattern(display, selected)
        play(display, CATALOGUE[selected])


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption('Game of life')
    main(pygame.display.set_mode(DISPLAY_SIZE))
