'''Falling-sand sandbox; runs on desktop and in the browser.

Left mouse (or a finger) paints the selected tool, right mouse erases.
1 sand, 2 water, 3 stone, 4 eraser, mouse wheel or [ ] brush size,
space pause, c clear, esc back to the menu. The toolbar under the world
does the same with a click or a tap.

The loops are async and yield once per frame so the same code runs in the
browser through pygbag (see tools/build_web.py).
'''

import asyncio
import sys
from pathlib import Path

# Shared modules (pixel font, touch) live in src/shared; the web build copies them alongside.
sys.path.append(str(Path(__file__).resolve().parents[1] / 'shared'))

import pixelfont
import pygame
from browser import WEB, prepare_page
from materials import PROPS, Material, palette
from touch import Button, button_at, button_row
from world import World

S_WIDTH = 800
S_HEIGHT = 600
BAR_HEIGHT = 64
WINDOW_SIZE = (S_WIDTH, S_HEIGHT + BAR_HEIGHT)
CELL_SIZE = 5
COLUMNS = S_WIDTH // CELL_SIZE
ROWS = S_HEIGHT // CELL_SIZE
FPS = 60

MIN_BRUSH, MAX_BRUSH = 0, 12
# Granular materials are poured sparsely so they look like grains.
FILL = {Material.SAND: 0.5, Material.WATER: 0.6, Material.STONE: 1.0, Material.EMPTY: 1.0}
TOOLS = {
    'sand': Material.SAND,
    'water': Material.WATER,
    'stone': Material.STONE,
    'erase': Material.EMPTY,
}
KEY_ACTIONS = {
    pygame.K_1: 'sand',
    pygame.K_2: 'water',
    pygame.K_3: 'stone',
    pygame.K_4: 'erase',
    pygame.K_LEFTBRACKET: 'smaller',
    pygame.K_RIGHTBRACKET: 'bigger',
    pygame.K_SPACE: 'pause',
    pygame.K_c: 'clear',
    pygame.K_ESCAPE: 'menu',
}
TOOLBAR = button_row(
    (('sand', 'SAND'), ('water', 'WATER'), ('stone', 'STONE'), ('erase', 'ERASE'),
     ('smaller', 'SIZE-'), ('bigger', 'SIZE+'), ('pause', 'PAUSE'), ('clear', 'CLEAR'),
     ('menu', 'MENU')),
    8, S_HEIGHT + 8, S_WIDTH - 16, BAR_HEIGHT - 16, 6,
)

BLACK = (0, 0, 0)
WHITE = (252, 252, 252)
RED = (228, 52, 32)
DIM = (150, 150, 170)
GOLD = (248, 184, 0)
MUTED = (130, 130, 150)
BACKGROUND = (12, 12, 18)
BAR_BACKGROUND = (24, 24, 32)
BUTTON = (40, 40, 54)
BUTTON_ACTIVE = (70, 70, 100)
SAND = PROPS[Material.SAND].color
HELP = ('1 SAND  2 WATER  3 STONE  4 ERASE  LMB PAINT  RMB ERASE  WHEEL/[] BRUSH  '
        'SPC PAUSE  C CLEAR')

# Pre-rendered RGB bytes per (material, shade); empty cells use BACKGROUND.
PIXELS: list[list[bytes]] = [
    [bytes(BACKGROUND if m == Material.EMPTY else color) for color in shades]
    for m, shades in sorted(palette().items())
]


def tool_name(tool: Material) -> str:
    return 'eraser' if tool == Material.EMPTY else tool.name.lower()


def status_text(tool: Material, brush: int, fps: float, paused: bool) -> str:
    paused_flag = '  PAUSED' if paused else ''
    return f'{tool_name(tool).upper()}  BRUSH {brush}  {fps:.0f} FPS{paused_flag}'


def blink(period_ms: int = 500) -> bool:
    return pygame.time.get_ticks() // period_ms % 2 == 0


def to_cell(pixel: tuple[int, int]) -> tuple[int, int]:
    return pixel[0] // CELL_SIZE, pixel[1] // CELL_SIZE


def in_world(pixel: tuple[int, int]) -> bool:
    return 0 <= pixel[1] < S_HEIGHT


def resize_brush(brush: int, action: str) -> int:
    delta = {'smaller': -1, 'bigger': 1}.get(action, 0)
    return max(MIN_BRUSH, min(MAX_BRUSH, brush + delta))


def render(world: World) -> bytes:
    return b''.join(PIXELS[m][s] for m, s in zip(world.material, world.shade, strict=True))


def draw_button(win: pygame.Surface, button: Button, label: str, active: bool) -> None:
    pygame.draw.rect(win, BUTTON_ACTIVE if active else BUTTON, button.rect)
    pygame.draw.rect(win, GOLD if active else MUTED, button.rect, 2 if active else 1)
    pixelfont.draw(win, label, pygame.Rect(button.rect).center, WHITE, 2, center=True)


def draw(win: pygame.Surface, world: World, status: str, tool: Material, paused: bool) -> None:
    frame = pygame.image.frombuffer(render(world), (world.width, world.height), 'RGB')
    win.blit(pygame.transform.scale(frame, (S_WIDTH, S_HEIGHT)), (0, 0))
    pixelfont.draw(win, status, (8, 8), WHITE, 2, shadow=BLACK)
    if not WEB:
        pixelfont.draw(win, HELP, (8, 28), DIM, shadow=BLACK)
    win.fill(BAR_BACKGROUND, (0, S_HEIGHT, S_WIDTH, BAR_HEIGHT))
    for button in TOOLBAR:
        active = TOOLS.get(button.action) == tool or (button.action == 'pause' and paused)
        label = 'PLAY' if paused and button.action == 'pause' else button.label
        draw_button(win, button, label, active)
    pygame.display.update()


def quit_game() -> None:
    '''Quit on desktop; in the browser there is nothing to quit to.'''
    if WEB:
        return
    pygame.quit()
    sys.exit()


async def sandbox(win: pygame.Surface) -> None:
    '''Run the sandbox until the player goes back to the menu.'''
    clock = pygame.time.Clock()
    world = World(COLUMNS, ROWS)
    tool = Material.SAND
    brush = 3
    paused = False
    buttons = {1: False, 3: False}
    cursor = (COLUMNS // 2, 0)

    while True:
        for event in pygame.event.get():
            action = None
            if event.type == pygame.QUIT:
                quit_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in buttons:
                if in_world(event.pos):
                    buttons[event.button] = True
                    cursor = to_cell(event.pos)
                elif event.button == 1:
                    action = button_at(TOOLBAR, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button in buttons:
                buttons[event.button] = False
            elif event.type == pygame.MOUSEMOTION:
                cursor = to_cell(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                brush = max(MIN_BRUSH, min(MAX_BRUSH, brush + event.y))
            elif event.type == pygame.KEYDOWN:
                action = KEY_ACTIONS.get(event.key)

            if action in TOOLS:
                tool = TOOLS[action]
            elif action in ('smaller', 'bigger'):
                brush = resize_brush(brush, action)
            elif action == 'pause':
                paused = not paused
            elif action == 'clear':
                world.clear()
            elif action == 'menu':
                return

        if buttons[1]:
            world.paint(*cursor, brush, tool, FILL[tool])
        if buttons[3]:
            world.paint(*cursor, brush, Material.EMPTY)
        if not paused:
            world.step()

        draw(win, world, status_text(tool, brush, clock.get_fps(), paused), tool, paused)
        clock.tick(FPS)
        await asyncio.sleep(0)


def draw_menu(win: pygame.Surface) -> None:
    win.fill(BLACK)
    pixelfont.draw(win, 'SAND', (S_WIDTH // 2, 180), SAND, 10, shadow=(90, 70, 30), center=True)
    pixelfont.draw(win, 'SIMULATOR', (S_WIDTH // 2, 270), SAND, 6, shadow=(90, 70, 30),
                   center=True)
    if blink():
        prompt = 'TAP TO START' if WEB else 'PRESS ANY KEY'
        pixelfont.draw(win, prompt, (S_WIDTH // 2, 380), WHITE, 3, center=True)
    pixelfont.draw(win, 'TITOREBOOT INC', (S_WIDTH // 2, 3 * S_HEIGHT // 4 + 40), RED, 2,
                   center=True)
    pygame.display.update()


async def main_menu(win: pygame.Surface) -> None:
    clock = pygame.time.Clock()
    while True:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            quit_game()
        if any(event.type == pygame.KEYDOWN
               or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
               for event in events):
            await sandbox(win)
        draw_menu(win)
        clock.tick(FPS)
        await asyncio.sleep(0)


async def main() -> None:
    pygame.init()
    prepare_page()
    window = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption('sand_simulator')
    await main_menu(window)


if __name__ == '__main__':
    asyncio.run(main())
