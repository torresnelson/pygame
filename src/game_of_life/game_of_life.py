'''Click cells to toggle them, press space to run/pause the simulation.'''

import pygame
from life import Cell, cell_at, next_generation, toggle

BACKGROUND = (0, 0, 0)
DEAD_CELL = (0, 0, 0)
ALIVE_CELL = (195, 195, 195)

# Can change those if you want
AMOUNT = 20
SIZE = 20
GAP = 1
FPS = 2

DISPLAY_SIZE = (AMOUNT * SIZE + (AMOUNT - 1) * GAP,) * 2


def draw(display: pygame.Surface, cells: set[Cell]) -> None:
    display.fill(BACKGROUND)
    for row in range(AMOUNT):
        for column in range(AMOUNT):
            color = ALIVE_CELL if (row, column) in cells else DEAD_CELL
            rect = (column * (SIZE + GAP), row * (SIZE + GAP), SIZE, SIZE)
            pygame.draw.rect(display, color, rect)
    pygame.display.update()


def main(display: pygame.Surface) -> None:
    clock = pygame.time.Clock()
    cells: set[Cell] = set()
    running = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.MOUSEBUTTONDOWN and not running:
                cell = cell_at(*event.pos, SIZE, GAP, AMOUNT)
                if cell is not None:
                    cells = toggle(cells, cell)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                running = not running and bool(cells)

        if running:
            cells = next_generation(cells, AMOUNT, AMOUNT)
            # Everything died: go back to editing instead of quitting.
            running = bool(cells)

        draw(display, cells)
        # Edit at full speed, simulate at FPS generations per second.
        clock.tick(FPS if running else 60)


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption('Game of life')
    main(pygame.display.set_mode(DISPLAY_SIZE))
    pygame.quit()
