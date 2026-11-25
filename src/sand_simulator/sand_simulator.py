'''Hold the left mouse button to pour sand, press C to clear, Esc for the menu.'''

import sys
from functools import cache

import pygame
from sand import Pos, pour, step

S_WIDTH = 800
S_HEIGHT = 600
BLOCK_SIZE = 10
COLUMNS = S_WIDTH // BLOCK_SIZE
ROWS = S_HEIGHT // BLOCK_SIZE
BRUSH_RADIUS = 1
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
SAND = (230, 200, 90)


@cache
def get_font(size: int) -> pygame.font.Font:
    return pygame.font.SysFont('monospace', size, bold=True)


def draw_text(surface: pygame.Surface, text: str, size: int, color: tuple, y: float) -> None:
    label = get_font(size).render(text, True, color)
    surface.blit(label, (S_WIDTH / 2 - label.get_width() / 2, y - label.get_height() / 2))


def to_cell(pixel: tuple[int, int]) -> Pos:
    return pixel[0] // BLOCK_SIZE, pixel[1] // BLOCK_SIZE


def draw(surface: pygame.Surface, grains: set[Pos]) -> None:
    surface.fill(BLACK)
    for x, y in grains:
        pygame.draw.rect(surface, SAND, (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
    pygame.display.update()


def quit_game() -> None:
    pygame.quit()
    sys.exit()


def main(win: pygame.Surface) -> None:
    clock = pygame.time.Clock()
    grains: set[Pos] = set()
    pouring = False
    cursor: Pos = (COLUMNS // 2, 0)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pouring, cursor = True, to_cell(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                pouring = False
            elif event.type == pygame.MOUSEMOTION:
                cursor = to_cell(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    grains = set()
                elif event.key == pygame.K_ESCAPE:
                    return

        if pouring:
            grains = pour(grains, cursor, BRUSH_RADIUS, COLUMNS, ROWS)
        grains = step(grains, COLUMNS, ROWS)
        draw(win, grains)
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
