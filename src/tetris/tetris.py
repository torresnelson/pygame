import sys
from functools import cache

import pygame
from scores import read_max_score, save_max_score
from tetris_logic import (
    COLUMNS,
    ROWS,
    Grid,
    Piece,
    check_lost,
    clear_rows,
    create_grid,
    frame_positions,
    hard_drop,
    lock_piece,
    new_piece,
    piece_positions,
    score_for_lines,
    try_move,
)

S_WIDTH = 800
S_HEIGHT = 700
BLOCK_SIZE = 30
PLAY_WIDTH = COLUMNS * BLOCK_SIZE
PLAY_HEIGHT = ROWS * BLOCK_SIZE
TOP_LEFT_X = (S_WIDTH - PLAY_WIDTH) // 2
TOP_LEFT_Y = S_HEIGHT - PLAY_HEIGHT
SIDE_X = TOP_LEFT_X + PLAY_WIDTH + 50
SIDE_Y = TOP_LEFT_Y + PLAY_HEIGHT // 2 - 100

FALL_SPEED_S = 0.27

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (128, 128, 128)
RED = (255, 0, 0)


@cache
def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont('comicsans', size, bold=bold)


def draw_text_middle(surface: pygame.Surface, text: str, size: int, color: tuple) -> None:
    label = get_font(size, bold=True).render(text, True, color)
    surface.blit(label, (
        TOP_LEFT_X + PLAY_WIDTH / 2 - label.get_width() / 2,
        TOP_LEFT_Y + PLAY_HEIGHT / 2 - label.get_height() / 2,
    ))


def draw_grid_lines(surface: pygame.Surface) -> None:
    for i in range(ROWS):
        y = TOP_LEFT_Y + i * BLOCK_SIZE
        pygame.draw.line(surface, GREY, (TOP_LEFT_X, y), (TOP_LEFT_X + PLAY_WIDTH, y))
    for j in range(COLUMNS):
        x = TOP_LEFT_X + j * BLOCK_SIZE
        pygame.draw.line(surface, GREY, (x, TOP_LEFT_Y), (x, TOP_LEFT_Y + PLAY_HEIGHT))


def draw_next_shape(surface: pygame.Surface, piece: Piece) -> None:
    for j, i in frame_positions(piece.frame):
        rect = (SIDE_X + j * BLOCK_SIZE, SIDE_Y + i * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        pygame.draw.rect(surface, piece.color, rect)
    label = get_font(30).render('Next Shape', True, WHITE)
    surface.blit(label, (SIDE_X + 10, SIDE_Y - 30))


def draw_window(surface: pygame.Surface, grid: Grid, score: int, max_score: int) -> None:
    surface.fill(BLACK)

    title = get_font(60).render('TETRIS', True, WHITE)
    surface.blit(title, (TOP_LEFT_X + PLAY_WIDTH / 2 - title.get_width() / 2, BLOCK_SIZE))
    surface.blit(get_font(30).render(f'Score: {score}', True, WHITE), (SIDE_X + 10, SIDE_Y - 80))
    surface.blit(
        get_font(30).render(f'Max score: {max_score}', True, WHITE), (SIDE_X + 10, SIDE_Y - 160)
    )

    for y, row in enumerate(grid):
        for x, color in enumerate(row):
            left = TOP_LEFT_X + x * BLOCK_SIZE
            top = TOP_LEFT_Y + y * BLOCK_SIZE
            pygame.draw.rect(surface, color, (left, top, BLOCK_SIZE, BLOCK_SIZE))

    draw_grid_lines(surface)
    pygame.draw.rect(surface, RED, (TOP_LEFT_X, TOP_LEFT_Y, PLAY_WIDTH, PLAY_HEIGHT), 5)


def quit_game() -> None:
    pygame.quit()
    sys.exit()


def main(win: pygame.Surface) -> None:
    locked: dict = {}
    current_piece = new_piece()
    next_piece = new_piece()
    clock = pygame.time.Clock()
    fall_time = 0
    score = 0
    max_score = read_max_score()

    while True:
        grid = create_grid(locked)
        fall_time += clock.get_rawtime()
        clock.tick()
        lock_now = False

        if fall_time / 1000 >= FALL_SPEED_S:
            fall_time = 0
            if not try_move(current_piece, grid, dy=1) and current_piece.y > 0:
                lock_now = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_LEFT:
                try_move(current_piece, grid, dx=-1)
            elif event.key == pygame.K_RIGHT:
                try_move(current_piece, grid, dx=1)
            elif event.key == pygame.K_UP:
                try_move(current_piece, grid, rotate=1)
            elif event.key == pygame.K_DOWN:
                try_move(current_piece, grid, dy=1)
            elif event.key == pygame.K_SPACE:
                hard_drop(current_piece, grid)
                lock_now = True

        for x, y in piece_positions(current_piece):
            if y >= 0:
                grid[y][x] = current_piece.color

        if lock_now:
            locked, lines = clear_rows(lock_piece(current_piece, locked))
            score += score_for_lines(lines)
            current_piece, next_piece = next_piece, new_piece()
            grid = create_grid(locked)

        draw_window(win, grid, score, max_score)
        draw_next_shape(win, next_piece)
        pygame.display.update()

        if check_lost(locked):
            break

    draw_text_middle(win, 'You Lost', 40, WHITE)
    pygame.display.update()
    save_max_score(score)
    pygame.time.delay(2000)


def main_menu(win: pygame.Surface) -> None:
    while True:
        win.fill(BLACK)
        draw_text_middle(win, 'Press any key to begin.', 60, WHITE)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN:
                main(win)


if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((S_WIDTH, S_HEIGHT))
    pygame.display.set_caption('Tetris')
    main_menu(window)
