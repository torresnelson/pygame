'''Falling-sand sandbox.

Left mouse paints the selected material, right mouse erases.
1 sand, 2 water, 3 stone, mouse wheel or [ ] brush size,
space pause, c clear, esc back to the menu.
'''

import sys
from functools import cache

import pygame
from materials import Material, palette
from world import World

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
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BACKGROUND = (12, 12, 18)

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


def render(world: World) -> bytes:
    return b''.join(PIXELS[m][s] for m, s in zip(world.material, world.shade, strict=True))


def draw(win: pygame.Surface, world: World, status: str) -> None:
    frame = pygame.image.frombuffer(render(world), (world.width, world.height), 'RGB')
    win.blit(pygame.transform.scale(frame, (S_WIDTH, S_HEIGHT)), (0, 0))
    win.blit(get_font(14).render(status, True, WHITE), (8, 6))
    pygame.display.update()


def quit_game() -> None:
    pygame.quit()
    sys.exit()


def main(win: pygame.Surface) -> None:
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

        status = (
            f'{selected.name.lower()}  brush {brush}  {clock.get_fps():.0f} fps'
            f'{"  [paused]" if paused else ""}  |  1 sand 2 water 3 stone, rmb erase'
        )
        draw(win, world, status)
        clock.tick(FPS)


def main_menu(win: pygame.Surface) -> None:
    while True:
        win.fill(BLACK)
        draw_text(win, 'Press any key to continue.', 30, WHITE, S_HEIGHT / 2)
        draw_text(win, 'titoreboot inc', 15, RED, 3 * S_HEIGHT / 4)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN:
                main(win)


if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((S_WIDTH, S_HEIGHT))
    pygame.display.set_caption('sand_simulator')
    main_menu(window)
