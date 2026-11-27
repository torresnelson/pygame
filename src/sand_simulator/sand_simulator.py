'''Falling-sand sandbox; runs on desktop and in the browser.

Left mouse (or a finger) paints the selected tool, right mouse erases.
1 sand, 2 water, 3 stone, 4 eraser, mouse wheel or [ ] brush size,
space pause, c clear, esc back to the menu. The toolbar under the world
does the same with a click or a tap.

A phone held upright gets a portrait layout (a tall world and two rows of
big toolbar buttons); turning the phone switches layouts and keeps the sand.
On desktop, `--portrait` shows that layout.

The loops are async and yield once per frame so the same code runs in the
browser through pygbag (see tools/build_web.py).
'''

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Shared modules (pixel font, touch) live in src/shared; the web build copies them alongside.
sys.path.append(str(Path(__file__).resolve().parents[1] / 'shared'))

import pixelfont
import pygame
from browser import WEB, fit_canvas, is_portrait, prepare_page
from materials import PROPS, Material, palette
from touch import Button, button_at, button_row
from world import World

CELL_SIZE = 5
FPS = 60
ORIENTATION_CHECK_MS = 250

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


@dataclass(frozen=True)
class Layout:
    '''World area, window size and toolbar for one orientation.'''

    name: str
    world_size: tuple[int, int]  # pixels; the world grid is this / CELL_SIZE
    size: tuple[int, int]
    toolbar: tuple[Button, ...]
    label_scale: int
    status_scale: int

    @property
    def cells(self) -> tuple[int, int]:
        return self.world_size[0] // CELL_SIZE, self.world_size[1] // CELL_SIZE


S_WIDTH = 800
S_HEIGHT = 600
BAR_HEIGHT = 64
WINDOW_SIZE = (S_WIDTH, S_HEIGHT + BAR_HEIGHT)
TOOLBAR = button_row(
    (('sand', 'SAND'), ('water', 'WATER'), ('stone', 'STONE'), ('erase', 'ERASE'),
     ('smaller', 'SIZE-'), ('bigger', 'SIZE+'), ('pause', 'PAUSE'), ('clear', 'CLEAR'),
     ('menu', 'MENU')),
    8, S_HEIGHT + 8, S_WIDTH - 16, BAR_HEIGHT - 16, 6,
)
LANDSCAPE = Layout('landscape', (S_WIDTH, S_HEIGHT), WINDOW_SIZE, TOOLBAR, 2, 2)

# Portrait: a tall world with the same number of cells (same speed), then two
# rows of thumb-sized buttons.
P_WIDTH, P_HEIGHT = 600, 800
P_ROW = 110
PORTRAIT = Layout(
    'portrait',
    (P_WIDTH, P_HEIGHT),
    (P_WIDTH, P_HEIGHT + 3 * 8 + 2 * P_ROW),
    button_row((('sand', 'SAND'), ('water', 'WATER'), ('stone', 'STONE'), ('erase', 'ERASE'),
                ('pause', 'PAUSE')), 8, P_HEIGHT + 8, P_WIDTH - 16, P_ROW, 8)
    + button_row((('smaller', 'SIZE-'), ('bigger', 'SIZE+'), ('clear', 'CLEAR'),
                  ('menu', 'MENU')), 8, P_HEIGHT + 16 + P_ROW, P_WIDTH - 16, P_ROW, 8),
    3,
    3,
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


@dataclass
class Screen:
    window: pygame.Surface
    layout: Layout
    checked_ms: int = 0


def pick_layout(portrait: bool) -> Layout:
    return PORTRAIT if portrait else LANDSCAPE


def make_screen(layout: Layout) -> Screen:
    return Screen(pygame.display.set_mode(layout.size), layout, pygame.time.get_ticks())


def follow_orientation(screen: Screen) -> bool:
    '''In the browser, switch layouts when the phone is turned and keep the canvas
    fitted; True when the layout changed.'''
    now = pygame.time.get_ticks()
    if not WEB or now - screen.checked_ms < ORIENTATION_CHECK_MS:
        return False
    screen.checked_ms = now
    layout = pick_layout(is_portrait())
    changed = layout != screen.layout
    if changed:
        screen.window = pygame.display.set_mode(layout.size)
        screen.layout = layout
    fit_canvas(*screen.layout.size)
    return changed


def tool_name(tool: Material) -> str:
    return 'eraser' if tool == Material.EMPTY else tool.name.lower()


def status_text(tool: Material, brush: int, fps: float, paused: bool) -> str:
    paused_flag = '  PAUSED' if paused else ''
    return f'{tool_name(tool).upper()}  BRUSH {brush}  {fps:.0f} FPS{paused_flag}'


def blink(period_ms: int = 500) -> bool:
    return pygame.time.get_ticks() // period_ms % 2 == 0


def to_cell(pixel: tuple[int, int]) -> tuple[int, int]:
    return pixel[0] // CELL_SIZE, pixel[1] // CELL_SIZE


def in_world(pixel: tuple[int, int], layout: Layout = LANDSCAPE) -> bool:
    width, height = layout.world_size
    return 0 <= pixel[0] < width and 0 <= pixel[1] < height


def resize_brush(brush: int, action: str) -> int:
    delta = {'smaller': -1, 'bigger': 1}.get(action, 0)
    return max(MIN_BRUSH, min(MAX_BRUSH, brush + delta))


def render(world: World) -> bytes:
    return b''.join(PIXELS[m][s] for m, s in zip(world.material, world.shade, strict=True))


def draw_button(win: pygame.Surface, button: Button, label: str, active: bool,
                scale: int) -> None:
    pygame.draw.rect(win, BUTTON_ACTIVE if active else BUTTON, button.rect)
    pygame.draw.rect(win, GOLD if active else MUTED, button.rect, 2 if active else 1)
    pixelfont.draw(win, label, pygame.Rect(button.rect).center, WHITE, scale, center=True)


def draw(win: pygame.Surface, layout: Layout, world: World, status: str, tool: Material,
         paused: bool) -> None:
    width, height = layout.world_size
    frame = pygame.image.frombuffer(render(world), (world.width, world.height), 'RGB')
    win.blit(pygame.transform.scale(frame, (width, height)), (0, 0))
    pixelfont.draw(win, status, (8, 8), WHITE, layout.status_scale, shadow=BLACK)
    if not WEB:
        pixelfont.draw(win, HELP, (8, 12 + 7 * layout.status_scale), DIM, shadow=BLACK)
    win.fill(BAR_BACKGROUND, (0, height, layout.size[0], layout.size[1] - height))
    for button in layout.toolbar:
        active = TOOLS.get(button.action) == tool or (button.action == 'pause' and paused)
        label = 'PLAY' if paused and button.action == 'pause' else button.label
        draw_button(win, button, label, active, layout.label_scale)
    pygame.display.update()


def quit_game() -> None:
    '''Quit on desktop; in the browser there is nothing to quit to.'''
    if WEB:
        return
    pygame.quit()
    sys.exit()


async def sandbox(screen: Screen) -> None:
    '''Run the sandbox until the player goes back to the menu.'''
    clock = pygame.time.Clock()
    world = World(*screen.layout.cells)
    tool = Material.SAND
    brush = 3
    paused = False
    buttons = {1: False, 3: False}
    cursor = (world.width // 2, 0)

    while True:
        layout = screen.layout
        for event in pygame.event.get():
            action = None
            if event.type == pygame.QUIT:
                quit_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in buttons:
                if in_world(event.pos, layout):
                    buttons[event.button] = True
                    cursor = to_cell(event.pos)
                elif event.button == 1:
                    action = button_at(layout.toolbar, event.pos)
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

        status = status_text(tool, brush, clock.get_fps(), paused)
        draw(screen.window, layout, world, status, tool, paused)
        if follow_orientation(screen):
            world = world.resized(*screen.layout.cells)
            buttons = {1: False, 3: False}
        clock.tick(FPS)
        await asyncio.sleep(0)


def draw_menu(win: pygame.Surface, size: tuple[int, int]) -> None:
    width, height = size
    middle = height // 2
    win.fill(BLACK)
    pixelfont.draw(win, 'SAND', (width // 2, middle - 150), SAND, 10, shadow=(90, 70, 30),
                   center=True)
    pixelfont.draw(win, 'SIMULATOR', (width // 2, middle - 60), SAND, 6, shadow=(90, 70, 30),
                   center=True)
    if blink():
        prompt = 'TAP TO START' if WEB else 'PRESS ANY KEY'
        pixelfont.draw(win, prompt, (width // 2, middle + 50), WHITE, 3, center=True)
    pixelfont.draw(win, 'TITOREBOOT INC', (width // 2, middle + 190), RED, 2, center=True)
    pygame.display.update()


async def main_menu(screen: Screen) -> None:
    clock = pygame.time.Clock()
    while True:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            quit_game()
        if any(event.type == pygame.KEYDOWN
               or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
               for event in events):
            await sandbox(screen)
        draw_menu(screen.window, screen.layout.size)
        follow_orientation(screen)
        clock.tick(FPS)
        await asyncio.sleep(0)


async def main() -> None:
    pygame.init()
    prepare_page()
    pygame.display.set_caption('sand_simulator')
    portrait = is_portrait() if WEB else '--portrait' in sys.argv
    await main_menu(make_screen(pick_layout(portrait)))


if __name__ == '__main__':
    asyncio.run(main())
