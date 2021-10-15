import pygame
import random
 
# GLOBALS VARS
s_width = 800
s_height = 600
play_width = 800  # meaning 600 // 20 = 20 width per block
play_height = 600  # meaning 300 // 10 = 30 height per block
block_size = 10
rows = 600 // 10
columns = 800 // 10
 
top_left_x = (s_width - play_width)
top_left_y = (s_height - play_height)
 
# SAND GRAIN FORMAT
sand = ['0']

sand_color = (255, 255, 0)
black = (0,0,0)
white = (255,255,255)
red = (255, 0, 0)
  
class Piece(object):
    def __init__(self, column, row):
        self.x = column
        self.y = row
        self.grain = sand
        self.color = sand_color
 
def create_grid(locked_positions={}):
    grid = [[black for x in range(columns)] for x in range(rows)]
 
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if (j,i) in locked_positions:
                c = locked_positions[(j,i)]
                grid[i][j] = c
    return grid
 
def convert_sand_format(sand):
    positions = []
    format = sand.grain
 
    for i, line in enumerate(format):
        row = list(line)
        for j, column in enumerate(row):
            if column == '0':
                positions.append((sand.x + j, sand.y + i))
 
    for i, pos in enumerate(positions):
        positions[i] = (pos[0], pos[1])
 
    return positions
 
 
def valid_space(sand, grid):
    accepted_positions = [[(j, i) for j in range(columns) if grid[i][j] == black] for i in range(rows)]
    accepted_positions = [j for sub in accepted_positions for j in sub]
    
    formatted = convert_sand_format(sand)

    for pos in formatted:
        if pos not in accepted_positions:
            if pos[1] > -1:
                return False
    
    return True
 
 
def check_full(positions):
    for pos in positions:
        x, y = pos
        if y < 1:
            return True
    return False
 
 
def get_grain():
    return Piece(columns//2, 0)

pygame.font.init()
 
def draw_text_middle(text, size, color, surface):
    font = pygame.font.SysFont('comicsans', size, bold=True)
    label = font.render(text, 1, color)
 
    surface.blit(label, (top_left_x + play_width/2 - (label.get_width() / 2), top_left_y + play_height/2 - label.get_height()/2))
 
 
def draw_grid(surface, row, col):
    sx = top_left_x
    sy = top_left_y
    for i in range(row):
        pygame.draw.line(surface, (128,128,128), (sx, sy + i*block_size), (sx + play_width, sy + i*block_size))  # horizontal lines
        for j in range(col):
            pygame.draw.line(surface, (128,128,128), (sx + j*block_size, sy), (sx + j*block_size, sy + play_height))  # vertical lines 

def draw_window(surface):
    surface.fill(black)
 
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            pygame.draw.rect(surface, grid[i][j], (top_left_x + j* block_size, top_left_y + i * block_size, block_size, block_size), 0)
 
    # draw grid and border
    draw_grid(surface, rows, columns)
    pygame.draw.rect(surface, black, (top_left_x, top_left_y, play_width, play_height), 5) 
 
def main():
    global grid
 
    locked_positions = {}  # (x,y):(255,0,0)
    grid = create_grid(locked_positions)
 
    change_grain = False
    run = True
    current_grain = get_grain()
    next_grain = get_grain()
    clock = pygame.time.Clock()
    fall_time = 0
 
    while run:
        fall_speed = 1
 
        grid = create_grid(locked_positions)
        fall_time += clock.get_rawtime()
        clock.tick()
 
        # PIECE FALLING CODE 
        # TODO: add grain's falling logic
        if fall_time >= fall_speed:
            fall_time = 0
            current_grain.y += 1
            # if (valid_space(current_grain, grid)):

            if not (valid_space(current_grain, grid)) and current_grain.y > 0:                
                current_grain.y -= 1
                change_grain = True
 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.display.quit()
                quit()
 
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    current_grain.x -= 1
                    if not valid_space(current_grain, grid):
                        current_grain.x += 1
 
                elif event.key == pygame.K_RIGHT:
                    current_grain.x += 1
                    if not valid_space(current_grain, grid):
                        current_grain.x -= 1
 
                if event.key == pygame.K_DOWN:
                    # move grain down
                    current_grain.y += 1
                    if not valid_space(current_grain, grid):
                        current_grain.y -= 1
 
                if event.key == pygame.K_SPACE:
                   while valid_space(current_grain, grid):
                       current_grain.y += 1
                   current_grain.y -= 1
                   print(convert_sand_format(current_grain))  # todo fix
 
        grain_pos = convert_sand_format(current_grain)
 
        # add piece to the grid for drawing
        for i in range(len(grain_pos)):
            x, y = grain_pos[i]
            if y > -1:
                grid[y][x] = current_grain.color

 
        # IF PIECE HIT GROUND or another sand grain
        if change_grain:
            for pos in grain_pos:
                p = (pos[0], pos[1])
                locked_positions[p] = red #current_grain.color
            current_grain = next_grain
            next_grain = get_grain()
            change_grain = False
 
        draw_window(win)

        pygame.display.update()
 
        # Check if sand reached ceiling
        if check_full(locked_positions):
            run = False
 
    pygame.display.update()
    pygame.time.delay(2000)
 
 
def main_menu():
    run = True
    while run:
        win.fill((0,0,0))
        draw_text_middle('Sand...', 40, (255, 255, 255), win)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
 
            if event.type == pygame.KEYDOWN:
                main()
    pygame.quit()
 
 
win = pygame.display.set_mode((s_width, s_height))
pygame.display.set_caption('SandSimulator')
 
main_menu()  
