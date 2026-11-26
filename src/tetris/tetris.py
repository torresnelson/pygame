'''Tetris with a main menu and a top-10 high score table.

Menu: up/down + enter or the mouse. In game: left/right move, up rotates,
down soft drops, space hard drops, p pauses, esc ends the game.
'''

import sys
from dataclasses import dataclass
from functools import cache

import pygame
from highscores import (
    DEFAULT_NAME,
    NAME_LENGTH,
    Entry,
    best,
    insert,
    load,
    new_entry,
    qualifies,
    save,
)
from tetris_logic import (
    COLUMNS,
    ROWS,
    Grid,
    Piece,
    check_lost,
    clear_rows,
    create_grid,
    fall_interval,
    frame_positions,
    hard_drop,
    level_for_lines,
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
TOP_LEFT_Y = S_HEIGHT - PLAY_HEIGHT - 20
SIDE_X = TOP_LEFT_X + PLAY_WIDTH + 40
STATS_X = 40
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (128, 128, 128)
DIM = (150, 150, 160)
RED = (255, 0, 0)
GOLD = (255, 210, 80)
HIGHLIGHT = (60, 60, 90)

MENU_OPTIONS = ('Play', 'High scores', 'Quit')
MENU_TOP = 330
MENU_ROW = 60


@dataclass(frozen=True)
class GameResult:
    score: int
    lines: int
    level: int


@cache
def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont('comicsans', size, bold=bold)


def blit_text(surface: pygame.Surface, text: str, pos: tuple[float, float], size: int = 30,
              color: tuple = WHITE, bold: bool = False) -> pygame.Rect:
    label = get_font(size, bold).render(text, True, color)
    return surface.blit(label, pos)


def blit_center(surface: pygame.Surface, text: str, y: float, size: int = 30,
                color: tuple = WHITE, bold: bool = False, x: float = S_WIDTH / 2) -> pygame.Rect:
    label = get_font(size, bold).render(text, True, color)
    return surface.blit(label, (x - label.get_width() / 2, y - label.get_height() / 2))


def quit_game() -> None:
    pygame.quit()
    sys.exit()


# -- menu --------------------------------------------------------------------


def menu_index_at(pos: tuple[int, int]) -> int | None:
    index = (pos[1] - MENU_TOP + MENU_ROW // 2) // MENU_ROW
    if abs(pos[0] - S_WIDTH / 2) < 160 and 0 <= index < len(MENU_OPTIONS):
        return index
    return None


def draw_menu(surface: pygame.Surface, selected: int, entries: list[Entry]) -> None:
    surface.fill(BLACK)
    blit_center(surface, 'TETRIS', 150, 90, WHITE, bold=True)
    top = entries[0] if entries else None
    best_line = f'Best: {top.score}  ({top.name})' if top else 'No high scores yet'
    blit_center(surface, best_line, 240, 26, GOLD)
    for i, option in enumerate(MENU_OPTIONS):
        y = MENU_TOP + i * MENU_ROW
        if i == selected:
            pygame.draw.rect(surface, HIGHLIGHT, (S_WIDTH / 2 - 160, y - 25, 320, 50), 0, 8)
        blit_center(surface, option, y, 36, WHITE, bold=i == selected)
    blit_center(surface, 'up/down + enter, or click', 640, 18, DIM)
    pygame.display.update()


def main_menu(surface: pygame.Surface, entries: list[Entry]) -> str:
    '''Show the menu until an option is chosen; return its name.'''
    clock = pygame.time.Clock()
    selected = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(MENU_OPTIONS)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(MENU_OPTIONS)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return MENU_OPTIONS[selected]
                elif event.key == pygame.K_ESCAPE:
                    return 'Quit'
            if event.type == pygame.MOUSEMOTION:
                index = menu_index_at(event.pos)
                if index is not None:
                    selected = index
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = menu_index_at(event.pos)
                if index is not None:
                    return MENU_OPTIONS[index]
        draw_menu(surface, selected, entries)
        clock.tick(FPS)


# -- high scores -------------------------------------------------------------


def draw_highscores(surface: pygame.Surface, entries: list[Entry], highlight: int | None) -> None:
    surface.fill(BLACK)
    blit_center(surface, 'HIGH SCORES', 70, 60, GOLD, bold=True)
    columns = ((90, 'RANK'), (180, 'NAME'), (420, 'SCORE'), (560, 'LINES'), (660, 'LEVEL'))
    for x, title in columns:
        blit_text(surface, title, (x, 130), 20, DIM)
    if not entries:
        blit_center(surface, 'No scores yet. Go play!', 300, 30, WHITE)
    for i, entry in enumerate(entries):
        y = 170 + i * 42
        if i == highlight:
            pygame.draw.rect(surface, HIGHLIGHT, (70, y - 4, 680, 40), 0, 6)
        color = GOLD if i == 0 else WHITE
        values = (f'{i + 1}.', entry.name, str(entry.score), str(entry.lines), str(entry.level))
        for (x, _), value in zip(columns, values, strict=True):
            blit_text(surface, value, (x, y), 28, color)
    blit_center(surface, 'press any key to return', 650, 20, DIM)
    pygame.display.update()


def show_highscores(surface: pygame.Surface, entries: list[Entry],
                    highlight: int | None = None) -> None:
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ):
                return
        draw_highscores(surface, entries, highlight)
        clock.tick(FPS)


def enter_name(surface: pygame.Surface, result: GameResult, default: str) -> str:
    '''Let the player type a name for the high score table.'''
    clock = pygame.time.Clock()
    name = default
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return name
            if event.key == pygame.K_ESCAPE:
                return default
            if event.key == pygame.K_BACKSPACE:
                name = name[:-1]
            elif event.unicode and event.unicode.isprintable() and len(name) < NAME_LENGTH:
                name += event.unicode

        surface.fill(BLACK)
        blit_center(surface, 'NEW HIGH SCORE!', 180, 60, GOLD, bold=True)
        blit_center(surface, f'{result.score} points', 260, 36)
        blit_center(surface, f'{result.lines} lines, level {result.level}', 305, 24, DIM)
        blit_center(surface, 'Enter your name:', 380, 28)
        cursor = '_' if pygame.time.get_ticks() // 400 % 2 else ' '
        pygame.draw.rect(surface, HIGHLIGHT, (S_WIDTH / 2 - 180, 410, 360, 60), 0, 8)
        blit_center(surface, name + cursor, 440, 40, WHITE, bold=True)
        blit_center(surface, 'enter to save', 520, 20, DIM)
        pygame.display.update()
        clock.tick(FPS)


# -- game --------------------------------------------------------------------


def draw_grid_lines(surface: pygame.Surface) -> None:
    for i in range(ROWS):
        y = TOP_LEFT_Y + i * BLOCK_SIZE
        pygame.draw.line(surface, GREY, (TOP_LEFT_X, y), (TOP_LEFT_X + PLAY_WIDTH, y))
    for j in range(COLUMNS):
        x = TOP_LEFT_X + j * BLOCK_SIZE
        pygame.draw.line(surface, GREY, (x, TOP_LEFT_Y), (x, TOP_LEFT_Y + PLAY_HEIGHT))


def draw_next_shape(surface: pygame.Surface, piece: Piece) -> None:
    blit_text(surface, 'Next', (SIDE_X + 10, TOP_LEFT_Y + 10), 30)
    for j, i in frame_positions(piece.frame):
        rect = (SIDE_X + j * BLOCK_SIZE, TOP_LEFT_Y + 40 + i * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        pygame.draw.rect(surface, piece.color, rect)


def draw_stats(
    surface: pygame.Surface, score: int, lines: int, level: int, best_score: int
) -> None:
    rows = (('Best', max(best_score, score), GOLD), ('Score', score, WHITE),
            ('Level', level, WHITE), ('Lines', lines, WHITE))
    for i, (label, value, color) in enumerate(rows):
        y = TOP_LEFT_Y + 10 + i * 90
        blit_text(surface, label, (STATS_X, y), 24, DIM)
        blit_text(surface, str(value), (STATS_X, y + 30), 34, color, bold=True)


def draw_window(surface: pygame.Surface, grid: Grid) -> None:
    surface.fill(BLACK)
    blit_center(surface, 'TETRIS', 30, 50, WHITE, bold=True)
    for y, row in enumerate(grid):
        for x, color in enumerate(row):
            left = TOP_LEFT_X + x * BLOCK_SIZE
            top = TOP_LEFT_Y + y * BLOCK_SIZE
            pygame.draw.rect(surface, color, (left, top, BLOCK_SIZE, BLOCK_SIZE))
    draw_grid_lines(surface)
    pygame.draw.rect(surface, RED, (TOP_LEFT_X, TOP_LEFT_Y, PLAY_WIDTH, PLAY_HEIGHT), 5)


def draw_overlay(surface: pygame.Surface, title: str, subtitle: str) -> None:
    shade = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 180))
    surface.blit(shade, (TOP_LEFT_X, TOP_LEFT_Y))
    center_x = TOP_LEFT_X + PLAY_WIDTH / 2
    blit_center(surface, title, TOP_LEFT_Y + PLAY_HEIGHT / 2 - 20, 48, WHITE, True, center_x)
    blit_center(surface, subtitle, TOP_LEFT_Y + PLAY_HEIGHT / 2 + 30, 20, DIM, x=center_x)


def play(surface: pygame.Surface, best_score: int) -> GameResult:
    locked: dict = {}
    current_piece = new_piece()
    next_piece = new_piece()
    clock = pygame.time.Clock()
    fall_ms = 0.0
    score = lines = level = 0
    paused = False

    while True:
        elapsed = clock.tick(FPS)
        grid = create_grid(locked)
        lock_now = False
        ended = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_p:
                paused = not paused
            elif event.key == pygame.K_ESCAPE:
                ended = True
            elif paused:
                continue
            elif event.key == pygame.K_LEFT:
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

        if not paused:
            fall_ms += elapsed
            if fall_ms / 1000 >= fall_interval(level):
                fall_ms = 0.0
                if not try_move(current_piece, grid, dy=1) and current_piece.y > 0:
                    lock_now = True

        if lock_now:
            locked, cleared = clear_rows(lock_piece(current_piece, locked))
            score += score_for_lines(cleared, level)
            lines += cleared
            level = level_for_lines(lines)
            current_piece, next_piece = next_piece, new_piece()
            grid = create_grid(locked)

        for x, y in piece_positions(current_piece):
            if y >= 0:
                grid[y][x] = current_piece.color

        draw_window(surface, grid)
        draw_stats(surface, score, lines, level, best_score)
        draw_next_shape(surface, next_piece)
        if paused:
            draw_overlay(surface, 'PAUSED', 'p to resume, esc to end')
        pygame.display.update()

        if ended or check_lost(locked):
            draw_overlay(surface, 'GAME OVER', f'{score} points')
            pygame.display.update()
            pygame.time.delay(1500)
            pygame.event.clear()
            return GameResult(score, lines, level)


def main(surface: pygame.Surface) -> None:
    entries = load()
    last_name = DEFAULT_NAME
    while True:
        choice = main_menu(surface, entries)
        if choice == 'Quit':
            quit_game()
        if choice == 'High scores':
            show_highscores(surface, entries)
            continue

        result = play(surface, best(entries))
        if not qualifies(entries, result.score):
            show_highscores(surface, entries)
            continue
        last_name = enter_name(surface, result, last_name)
        entry = new_entry(last_name, result.score, result.lines, result.level)
        entries, rank = insert(entries, entry)
        save(entries)
        show_highscores(surface, entries, rank)


if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((S_WIDTH, S_HEIGHT))
    pygame.display.set_caption('Tetris')
    main(window)
