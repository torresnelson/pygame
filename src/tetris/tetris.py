'''Tetris with an 8-bit look, a main menu and a top-10 high score table.

Everything is drawn on a 400x350 canvas with a built-in pixel font, then
scaled up 2x without smoothing and overlaid with faint scanlines.

Menu: up/down + enter or the mouse. In game: left/right move, up rotates,
down soft drops, space hard drops, p pauses, esc ends the game.
'''

import random
import sys
from dataclasses import dataclass

import pixelfont
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
    EMPTY,
    ROWS,
    SHAPE_COLORS,
    Color,
    Grid,
    Piece,
    check_lost,
    clear_rows,
    create_grid,
    fall_interval,
    frame_positions,
    full_rows,
    hard_drop,
    level_for_lines,
    lock_piece,
    new_piece,
    piece_positions,
    score_for_lines,
    try_move,
)

SCALE = 2
WIDTH, HEIGHT = 400, 350
WINDOW_SIZE = (WIDTH * SCALE, HEIGHT * SCALE)
FPS = 60

BLOCK = 15
BOARD_W, BOARD_H = COLUMNS * BLOCK, ROWS * BLOCK
BOARD_X = (WIDTH - BOARD_W) // 2
BOARD_Y = 40

BLACK: Color = (0, 0, 0)
WHITE: Color = (252, 252, 252)
GREY: Color = (124, 124, 124)
DIM: Color = (120, 120, 150)
BOARD_BG: Color = (8, 8, 24)
GRID_DOT: Color = (36, 36, 64)
BOX_BLUE: Color = (0, 88, 248)
GOLD: Color = (248, 184, 0)
SILVER: Color = (188, 188, 188)
BRONZE: Color = (200, 108, 40)
RANK_COLORS = (GOLD, SILVER, BRONZE)

MENU_OPTIONS = ('PLAY', 'HIGH SCORES', 'QUIT')
MENU_BOX = pygame.Rect(105, 150, 190, 92)
MENU_ROW = 26


@dataclass(frozen=True)
class GameResult:
    score: int
    lines: int
    level: int


@dataclass
class Screen:
    window: pygame.Surface
    canvas: pygame.Surface
    scanlines: pygame.Surface


def make_screen(window: pygame.Surface) -> Screen:
    scanlines = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
    for y in range(1, WINDOW_SIZE[1], SCALE):
        scanlines.fill((0, 0, 0, 70), (0, y, WINDOW_SIZE[0], 1))
    return Screen(window, pygame.Surface((WIDTH, HEIGHT)), scanlines)


def present(screen: Screen) -> None:
    '''Scale the low-res canvas up with hard pixel edges and add scanlines.'''
    screen.window.blit(pygame.transform.scale(screen.canvas, WINDOW_SIZE), (0, 0))
    screen.window.blit(screen.scanlines, (0, 0))
    pygame.display.update()


def to_canvas(pos: tuple[int, int]) -> tuple[int, int]:
    return pos[0] // SCALE, pos[1] // SCALE


def blink(period_ms: int = 400) -> bool:
    return pygame.time.get_ticks() // period_ms % 2 == 0


def cycle_color(period_ms: int = 120) -> Color:
    return SHAPE_COLORS[pygame.time.get_ticks() // period_ms % len(SHAPE_COLORS)]


def quit_game() -> None:
    pygame.quit()
    sys.exit()


# -- drawing primitives ------------------------------------------------------


def shade(color: Color, amount: float) -> Color:
    '''Blend towards white (amount > 0) or black (amount < 0).'''
    target = 255 if amount > 0 else 0
    r, g, b = (int(c + (target - c) * abs(amount)) for c in color)
    return r, g, b


def draw_tile(surface: pygame.Surface, color: Color, x: int, y: int, size: int = BLOCK) -> None:
    '''A bevelled 8-bit block: light top-left edge, dark bottom-right edge, glint.'''
    surface.fill(color, (x, y, size, size))
    light, dark = shade(color, 0.5), shade(color, -0.55)
    surface.fill(light, (x, y, size, 1))
    surface.fill(light, (x, y, 1, size))
    surface.fill(dark, (x, y + size - 1, size, 1))
    surface.fill(dark, (x + size - 1, y, 1, size))
    if size >= 8:
        surface.fill(shade(color, 0.85), (x + 2, y + 2, 2, 2))


def draw_box(surface: pygame.Surface, rect: pygame.Rect | tuple, title: str | None = None) -> None:
    '''NES-style dialog box: black fill, white outer line, blue inner line.'''
    rect = pygame.Rect(rect)
    surface.fill(BLACK, rect)
    pygame.draw.rect(surface, WHITE, rect, 1)
    pygame.draw.rect(surface, BOX_BLUE, rect.inflate(-4, -4), 1)
    if title:
        width, height = pixelfont.text_size(title)
        surface.fill(BLACK, (rect.x + 5, rect.y - 3, width + 4, height))
        pixelfont.draw(surface, title, (rect.x + 7, rect.y - 3), WHITE)


def draw_title(surface: pygame.Surface, center_y: int, scale: int) -> None:
    '''"TETRIS" with each letter in a different piece colour and a hard shadow.'''
    word = 'TETRIS'
    width, _ = pixelfont.text_size(word, scale)
    x = (WIDTH - width) // 2
    advance = (pixelfont.GLYPH_WIDTH + pixelfont.SPACING) * scale
    for i, letter in enumerate(word):
        color = SHAPE_COLORS[i % len(SHAPE_COLORS)]
        image = pixelfont.render(letter, color, scale, shadow=shade(color, -0.7))
        surface.blit(image, (x + i * advance, center_y - image.get_height() // 2))


# -- menu --------------------------------------------------------------------


@dataclass
class Drop:
    x: int
    y: float
    speed: float
    color: Color


def new_drop(rng: random.Random, anywhere: bool = False) -> Drop:
    y = rng.uniform(0, HEIGHT) if anywhere else -10.0
    return Drop(rng.randrange(WIDTH // 10) * 10, y, rng.uniform(0.3, 1.1), rng.choice(SHAPE_COLORS))


def menu_index_at(pos: tuple[int, int]) -> int | None:
    x, y = pos
    index = (y - MENU_BOX.y - 10) // MENU_ROW
    if MENU_BOX.collidepoint(x, y) and 0 <= index < len(MENU_OPTIONS):
        return index
    return None


def draw_menu(canvas: pygame.Surface, selected: int, entries: list[Entry],
              drops: list[Drop]) -> None:
    canvas.fill(BLACK)
    for drop in drops:
        draw_tile(canvas, shade(drop.color, -0.6), drop.x, int(drop.y), 10)
    draw_title(canvas, 70, 6)
    top = entries[0] if entries else None
    top_line = f'TOP {top.score}  {top.name}' if top else 'NO HIGH SCORES YET'
    pixelfont.draw(canvas, top_line, (WIDTH // 2, 122), GOLD, center=True)

    draw_box(canvas, MENU_BOX)
    for i, option in enumerate(MENU_OPTIONS):
        y = MENU_BOX.y + 14 + i * MENU_ROW
        color = WHITE if i == selected else GREY
        pixelfont.draw(canvas, option, (MENU_BOX.x + 36, y), color, 2)
        if i == selected and blink():
            pixelfont.draw(canvas, '>', (MENU_BOX.x + 14, y), GOLD, 2)

    if blink(500):
        pixelfont.draw(canvas, 'PRESS ENTER', (WIDTH // 2, 278), WHITE, 2, center=True)
    pixelfont.draw(canvas, 'UP/DOWN + ENTER OR MOUSE', (WIDTH // 2, 330), DIM, center=True)


def main_menu(screen: Screen, entries: list[Entry]) -> str:
    '''Show the menu until an option is chosen; return its name.'''
    clock = pygame.time.Clock()
    rng = random.Random()
    drops = [new_drop(rng, anywhere=True) for _ in range(28)]
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
                    return 'QUIT'
            if event.type == pygame.MOUSEMOTION:
                index = menu_index_at(to_canvas(event.pos))
                if index is not None:
                    selected = index
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                index = menu_index_at(to_canvas(event.pos))
                if index is not None:
                    return MENU_OPTIONS[index]
        for i, drop in enumerate(drops):
            drop.y += drop.speed
            if drop.y > HEIGHT:
                drops[i] = new_drop(rng)
        draw_menu(screen.canvas, selected, entries, drops)
        present(screen)
        clock.tick(FPS)


# -- high scores -------------------------------------------------------------

SCORE_COLUMNS = ((16, 'RANK'), (50, 'NAME'), (178, 'SCORE'), (284, 'LINES'), (350, 'LV'))


def draw_highscores(canvas: pygame.Surface, entries: list[Entry], highlight: int | None) -> None:
    canvas.fill(BLACK)
    pixelfont.draw(canvas, 'HIGH SCORES', (WIDTH // 2, 22), GOLD, 3,
                   shadow=shade(GOLD, -0.7), center=True)
    draw_box(canvas, (8, 46, WIDTH - 16, 268))
    for x, title in SCORE_COLUMNS:
        pixelfont.draw(canvas, title, (x, 56), DIM)
    if not entries:
        pixelfont.draw(canvas, 'NO SCORES YET', (WIDTH // 2, 170), WHITE, 2, center=True)
    for i, entry in enumerate(entries):
        y = 72 + i * 24
        if i == highlight:
            color = cycle_color()
        else:
            color = RANK_COLORS[i] if i < len(RANK_COLORS) else WHITE
        values = (str(i + 1), entry.name, str(entry.score), str(entry.lines), str(entry.level))
        for (x, _), value in zip(SCORE_COLUMNS, values, strict=True):
            pixelfont.draw(canvas, value, (x, y), color, 2)
    if blink(500):
        pixelfont.draw(canvas, 'PRESS ANY KEY', (WIDTH // 2, 332), WHITE, center=True)


def show_highscores(screen: Screen, entries: list[Entry], highlight: int | None = None) -> None:
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ):
                return
        draw_highscores(screen.canvas, entries, highlight)
        present(screen)
        clock.tick(FPS)


def accept_char(name: str, char: str) -> str:
    '''Append `char` (upper-cased) if the pixel font can draw it and there is room.'''
    char = char.upper()
    if len(char) == 1 and char in pixelfont.CHARSET and len(name) < NAME_LENGTH:
        return name + char
    return name


def draw_name_entry(canvas: pygame.Surface, result: GameResult, name: str) -> None:
    canvas.fill(BLACK)
    pixelfont.draw(canvas, 'NEW HIGH SCORE!', (WIDTH // 2, 60), cycle_color(), 3,
                   shadow=BLACK, center=True)
    pixelfont.draw(canvas, str(result.score), (WIDTH // 2, 112), GOLD, 4,
                   shadow=shade(GOLD, -0.7), center=True)
    details = f'{result.lines} LINES  LEVEL {result.level}'
    pixelfont.draw(canvas, details, (WIDTH // 2, 145), DIM, center=True)
    pixelfont.draw(canvas, 'ENTER YOUR NAME', (WIDTH // 2, 190), WHITE, 2, center=True)
    box = pygame.Rect(80, 210, 240, 36)
    draw_box(canvas, box)
    text_rect = pixelfont.draw(canvas, name, (box.x + 14, box.y + 11), WHITE, 2)
    if blink(300) and len(name) < NAME_LENGTH:
        canvas.fill(GOLD, (text_rect.right + 2 if name else box.x + 14, box.y + 11, 10, 14))
    pixelfont.draw(canvas, 'ENTER TO SAVE', (WIDTH // 2, 275), DIM, center=True)


def enter_name(screen: Screen, result: GameResult, default: str) -> str:
    '''Let the player type a name for the high score table.'''
    clock = pygame.time.Clock()
    name = default.upper()
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
            elif event.unicode:
                name = accept_char(name, event.unicode)
        draw_name_entry(screen.canvas, result, name)
        present(screen)
        clock.tick(FPS)


# -- game --------------------------------------------------------------------


def draw_board(canvas: pygame.Surface, grid: Grid, flash: set[int] | None = None) -> None:
    # Frame made of small grey tiles.
    for x in range(BOARD_X - 5, BOARD_X + BOARD_W + 5, 5):
        draw_tile(canvas, GREY, x, BOARD_Y - 5, 5)
        draw_tile(canvas, GREY, x, BOARD_Y + BOARD_H, 5)
    for y in range(BOARD_Y, BOARD_Y + BOARD_H, 5):
        draw_tile(canvas, GREY, BOARD_X - 5, y, 5)
        draw_tile(canvas, GREY, BOARD_X + BOARD_W, y, 5)

    canvas.fill(BOARD_BG, (BOARD_X, BOARD_Y, BOARD_W, BOARD_H))
    for y, row in enumerate(grid):
        for x, color in enumerate(row):
            px, py = BOARD_X + x * BLOCK, BOARD_Y + y * BLOCK
            if flash and y in flash:
                draw_tile(canvas, WHITE, px, py)
            elif color != EMPTY:
                draw_tile(canvas, color, px, py)
            else:
                canvas.set_at((px + BLOCK // 2, py + BLOCK // 2), GRID_DOT)


def draw_stats(canvas: pygame.Surface, score: int, lines: int, level: int, top: int) -> None:
    rows = (('TOP', max(top, score), GOLD), ('SCORE', score, WHITE),
            ('LEVEL', level, WHITE), ('LINES', lines, WHITE))
    for i, (label, value, color) in enumerate(rows):
        box = pygame.Rect(10, BOARD_Y + i * 52, 100, 40)
        draw_box(canvas, box, label)
        pixelfont.draw(canvas, str(value), (box.x + 10, box.y + 14), color, 2)


def draw_next(canvas: pygame.Surface, piece: Piece) -> None:
    box = pygame.Rect(WIDTH - 110, BOARD_Y, 100, 80)
    draw_box(canvas, box, 'NEXT')
    cells = frame_positions(piece.frame)
    size = 12
    min_x, max_x = min(x for x, _ in cells), max(x for x, _ in cells)
    min_y, max_y = min(y for _, y in cells), max(y for _, y in cells)
    left = box.centerx - (max_x - min_x + 1) * size // 2
    top = box.centery - (max_y - min_y + 1) * size // 2 + 2
    for x, y in cells:
        draw_tile(canvas, piece.color, left + (x - min_x) * size, top + (y - min_y) * size, size)


def draw_keys(canvas: pygame.Surface) -> None:
    box = pygame.Rect(WIDTH - 110, BOARD_Y + 104, 100, 104)
    draw_box(canvas, box, 'KEYS')
    keys = ('<> MOVE', 'UP ROTATE', 'DN SOFT', 'SPC DROP', 'P  PAUSE', 'ESC END')
    for i, line in enumerate(keys):
        pixelfont.draw(canvas, line, (box.x + 10, box.y + 12 + i * 14), DIM)


def draw_game(canvas: pygame.Surface, grid: Grid, next_piece: Piece, score: int,
              lines: int, level: int, top: int, flash: set[int] | None = None) -> None:
    canvas.fill(BLACK)
    draw_title(canvas, 17, 2)
    draw_board(canvas, grid, flash)
    draw_stats(canvas, score, lines, level, top)
    draw_next(canvas, next_piece)
    draw_keys(canvas)


def draw_overlay(canvas: pygame.Surface, title: str, subtitle: str) -> None:
    box = pygame.Rect(BOARD_X + 5, BOARD_Y + BOARD_H // 2 - 30, BOARD_W - 10, 60)
    draw_box(canvas, box)
    pixelfont.draw(canvas, title, (box.centerx, box.y + 20), WHITE, 2, center=True)
    pixelfont.draw(canvas, subtitle, (box.centerx, box.y + 42), DIM, center=True)


def flash_rows(screen: Screen, grid: Grid, rows: set[int], *stats: object) -> None:
    '''Blink completed rows a few times before they are cleared.'''
    for i in range(6):
        draw_game(screen.canvas, grid, *stats, flash=rows if i % 2 == 0 else None)
        present(screen)
        pygame.event.pump()
        pygame.time.delay(55)


def play(screen: Screen, top: int) -> GameResult:
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
            locked = lock_piece(current_piece, locked)
            completed = full_rows(locked)
            if completed:
                flash_rows(screen, create_grid(locked), completed,
                           next_piece, score, lines, level, top)
            locked, cleared = clear_rows(locked)
            score += score_for_lines(cleared, level)
            lines += cleared
            level = level_for_lines(lines)
            current_piece, next_piece = next_piece, new_piece()
            grid = create_grid(locked)

        for x, y in piece_positions(current_piece):
            if y >= 0:
                grid[y][x] = current_piece.color

        draw_game(screen.canvas, grid, next_piece, score, lines, level, top)
        if paused:
            draw_overlay(screen.canvas, 'PAUSED', 'P RESUME  ESC END')
        present(screen)

        if ended or check_lost(locked):
            draw_overlay(screen.canvas, 'GAME OVER', f'{score} POINTS')
            present(screen)
            pygame.time.delay(1500)
            pygame.event.clear()
            return GameResult(score, lines, level)


def main(screen: Screen) -> None:
    entries = load()
    last_name = DEFAULT_NAME
    while True:
        choice = main_menu(screen, entries)
        if choice == 'QUIT':
            quit_game()
        if choice == 'HIGH SCORES':
            show_highscores(screen, entries)
            continue

        result = play(screen, best(entries))
        if not qualifies(entries, result.score):
            show_highscores(screen, entries)
            continue
        last_name = enter_name(screen, result, last_name)
        entry = new_entry(last_name, result.score, result.lines, result.level)
        entries, rank = insert(entries, entry)
        save(entries)
        show_highscores(screen, entries, rank)


if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption('Tetris')
    main(make_screen(window))
