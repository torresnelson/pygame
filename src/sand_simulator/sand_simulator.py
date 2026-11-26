'''Falling-sand sandbox; runs on desktop and in the browser.

Left mouse paints the selected material, right mouse erases.
1 sand, 2 water, 3 stone, mouse wheel or [ ] brush size,
space pause, c clear, esc back to the menu.

The loops are async and yield once per frame so the same code runs in the
browser through pygbag (see tools/build_web.py).
'''

import asyncio
import sys
from pathlib import Path

# Shared modules (pixel font) live in src/shared; the web build copies them alongside.
sys.path.append(str(Path(__file__).resolve().parents[1] / 'shared'))

import pixelfont
import pygame
from materials import PROPS, Material, palette
from world import World

WEB = sys.platform == 'emscripten'

S_WIDTH = 800
S_HEIGHT = 600
CELL_SIZE = 5
COLUMNS = S_WIDTH // CELL_SIZE
ROWS = S_HEIGHT // CELL_SIZE
FPS = 60

MIN_BRUSH, MAX_BRUSH = 0, 12
# Granular materials are poured sparsely so they look like grains.
FILL = {Material.SAND: 0.5, Material.WATER: 0.6, Material.STONE: 1.0}
KEY_MATERIALS = {
    pygame.K_1: Material.SAND,
    pygame.K_2: Material.WATER,
    pygame.K_3: Material.STONE,
}

BLACK = (0, 0, 0)
WHITE = (252, 252, 252)
RED = (228, 52, 32)
DIM = (150, 150, 170)
BACKGROUND = (12, 12, 18)
SAND = PROPS[Material.SAND].color
HELP = '1 SAND  2 WATER  3 STONE  LMB PAINT  RMB ERASE  WHEEL/[] BRUSH  SPC PAUSE  C CLEAR'

# Pre-rendered RGB bytes per (material, shade); empty cells use BACKGROUND.
PIXELS: list[list[bytes]] = [
    [bytes(BACKGROUND if m == Material.EMPTY else color) for color in shades]
    for m, shades in sorted(palette().items())
]


def status_text(material: Material, brush: int, fps: float, paused: bool) -> str:
    paused_flag = '  PAUSED' if paused else ''
    return f'{material.name}  BRUSH {brush}  {fps:.0f} FPS{paused_flag}'


def blink(period_ms: int = 500) -> bool:
    return pygame.time.get_ticks() // period_ms % 2 == 0


def to_cell(pixel: tuple[int, int]) -> tuple[int, int]:
    return pixel[0] // CELL_SIZE, pixel[1] // CELL_SIZE


def render(world: World) -> bytes:
    return b''.join(PIXELS[m][s] for m, s in zip(world.material, world.shade, strict=True))


def draw(win: pygame.Surface, world: World, status: str) -> None:
    frame = pygame.image.frombuffer(render(world), (world.width, world.height), 'RGB')
    win.blit(pygame.transform.scale(frame, (S_WIDTH, S_HEIGHT)), (0, 0))
    pixelfont.draw(win, status, (8, 8), WHITE, 2, shadow=BLACK)
    pixelfont.draw(win, HELP, (8, 28), DIM, shadow=BLACK)
    pygame.display.update()


def quit_game() -> None:
    '''Quit on desktop; in the browser there is nothing to quit to.'''
    if WEB:
        return
    pygame.quit()
    sys.exit()


async def sandbox(win: pygame.Surface) -> None:
    clock = pygame.time.Clock()
    world = World(COLUMNS, ROWS)
    selected = Material.SAND
    brush = 3
    paused = False
    buttons = {1: False, 3: False}
    cursor = (COLUMNS // 2, 0)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in buttons:
                buttons[event.button] = True
                cursor = to_cell(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button in buttons:
                buttons[event.button] = False
            elif event.type == pygame.MOUSEMOTION:
                cursor = to_cell(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                brush = max(MIN_BRUSH, min(MAX_BRUSH, brush + event.y))
            elif event.type == pygame.KEYDOWN:
                if event.key in KEY_MATERIALS:
                    selected = KEY_MATERIALS[event.key]
                elif event.key == pygame.K_LEFTBRACKET:
                    brush = max(MIN_BRUSH, brush - 1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    brush = min(MAX_BRUSH, brush + 1)
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_c:
                    world.clear()
                elif event.key == pygame.K_ESCAPE:
                    return

        if buttons[1]:
            world.paint(*cursor, brush, selected, FILL[selected])
        if buttons[3]:
            world.paint(*cursor, brush, Material.EMPTY)
        if not paused:
            world.step()

        draw(win, world, status_text(selected, brush, clock.get_fps(), paused))
        clock.tick(FPS)
        await asyncio.sleep(0)


def draw_menu(win: pygame.Surface) -> None:
    win.fill(BLACK)
    pixelfont.draw(win, 'SAND', (S_WIDTH // 2, 180), SAND, 10, shadow=(90, 70, 30), center=True)
    pixelfont.draw(win, 'SIMULATOR', (S_WIDTH // 2, 270), SAND, 6, shadow=(90, 70, 30),
                   center=True)
    if blink():
        pixelfont.draw(win, 'PRESS ANY KEY', (S_WIDTH // 2, 380), WHITE, 3, center=True)
    pixelfont.draw(win, 'TITOREBOOT INC', (S_WIDTH // 2, 3 * S_HEIGHT // 4 + 40), RED, 2,
                   center=True)
    pygame.display.update()


async def main_menu(win: pygame.Surface) -> None:
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ):
                await sandbox(win)
        draw_menu(win)
        clock.tick(FPS)
        await asyncio.sleep(0)


async def main() -> None:
    pygame.init()
    window = pygame.display.set_mode((S_WIDTH, S_HEIGHT))
    pygame.display.set_caption('sand_simulator')
    await main_menu(window)


if __name__ == '__main__':
    asyncio.run(main())
