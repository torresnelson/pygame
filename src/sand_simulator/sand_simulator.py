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
from functools import cache
from pathlib import Path

# Shared modules (pixel font, touch) live in src/shared; the web build copies them alongside.
sys.path.append(str(Path(__file__).resolve().parents[1] / 'shared'))

import pixelfont
import pygame
from browser import WEB, prepare_page
from materials import Material, palette
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
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BACKGROUND = (12, 12, 18)
BAR_BACKGROUND = (24, 24, 32)
BUTTON = (40, 40, 54)
BUTTON_ACTIVE = (70, 70, 100)
GOLD = (248, 184, 0)
MUTED = (130, 130, 150)

# Pre-rendered RGB bytes per (material, shade); empty cells use BACKGROUND.
PIXELS: list[list[bytes]] = [
    [bytes(BACKGROUND if m == Material.EMPTY else color) for color in shades]
    for m, shades in sorted(palette().items())
]


@cache
def get_font(size: int) -> pygame.font.Font:
    return pygame.font.SysFont('monospace', size, bold=True)


def draw_text(surface: pygame.Surface, text: str, size: int, color: tuple, y: float) -> None:
    label = get_font(size).render(text, True, color)
    surface.blit(label, (S_WIDTH / 2 - label.get_width() / 2, y - label.get_height() / 2))


def to_cell(pixel: tuple[int, int]) -> tuple[int, int]:
    return pixel[0] // CELL_SIZE, pixel[1] // CELL_SIZE


def in_world(pixel: tuple[int, int]) -> bool:
    return 0 <= pixel[1] < S_HEIGHT


def tool_name(tool: Material) -> str:
    return 'eraser' if tool == Material.EMPTY else tool.name.lower()


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
    win.blit(get_font(14).render(status, True, WHITE), (8, 6))
    win.fill(BAR_BACKGROUND, (0, S_HEIGHT, S_WIDTH, BAR_HEIGHT))
    for button in TOOLBAR:
        active = TOOLS.get(button.action) == tool or (button.action == 'pause' and paused)
        label = 'PLAY' if paused and button.action == 'pause' else button.label
        draw_button(win, button, label, active)
    pygame.display.update()


def quit_game() -> None:
    '''Close the game on desktop; a browser tab has nothing to quit to.'''
    if WEB:
        return
    pygame.quit()
    sys.exit()


async def play(win: pygame.Surface) -> None:
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

        status = (
            f'{tool_name(tool)}  brush {brush}  {clock.get_fps():.0f} fps'
            f'{"  [paused]" if paused else ""}'
        )
        if not WEB:
            status += '  |  1 sand 2 water 3 stone 4 erase, rmb erase'
        draw(win, world, status, tool, paused)
        clock.tick(FPS)
        await asyncio.sleep(0)


async def main_menu(win: pygame.Surface) -> None:
    clock = pygame.time.Clock()
    prompt = 'Tap to start.' if WEB else 'Press any key to continue.'
    while True:
        win.fill(BLACK)
        draw_text(win, prompt, 30, WHITE, WINDOW_SIZE[1] / 2)
        draw_text(win, 'titoreboot inc', 15, RED, 3 * WINDOW_SIZE[1] / 4)
        pygame.display.update()
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            quit_game()
        if any(event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) for event in events):
            await play(win)
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
