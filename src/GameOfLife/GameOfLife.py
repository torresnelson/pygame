import pygame
from time import sleep
from square import square, superior
import copy

pygame.init()

#Colors
red         = (255,0,0)
yellow      = (255,255,0)
white       = (255,255,255)
grey        = (128,128,128)
blue        = (0,0,255)
light_blue  = (0,255,255)
green       = (0,255,0)
orange      = (255,165,0)
purple      = (128,0,128)
black       = (0,0,0)

background = black
deadCell = black
aliveCell = white

#Can change those if you want
amount = 20
size = 20

#Some math to calculate size of the screen based on size and amount of cells + space between them
display_size = ((amount*size) + amount - 1, (amount*size) + amount - 1) 
display = pygame.display.set_mode(display_size)

exitGame = False
gameStarted = False

grid = list()

#FPS control variables
FPS = 2
clock = pygame.time.Clock()

def create_array():
    global grid

    for row in range(0, amount):
        placeholder = []
        for column in range(0, amount):
            cell = square(row, column, column*size + column, row*size + row, amount, size)
            placeholder.append(cell)
        grid.append(placeholder)

def create_grid():
    display.fill(background)
    #Render grid
    for row in grid:
        for cell in row:
            if cell.alive:
                pygame.draw.rect(display, aliveCell, [cell.x, cell.y, size, size])
            else:
                pygame.draw.rect(display, deadCell, [cell.x, cell.y, size, size])
    pygame.display.update()

def check():
    global grid

    #Create old gird tamplate
    old_grid = copy.deepcopy(grid)

    for row in grid:
        for cell in row:
            alive = 0

            next_row = cell.row + 1
            previous_row = cell.row - 1

            next_column = cell.column + 1
            previous_column = cell.column - 1

            # To prevent calling old_grid[-1]
            if previous_row < 0:
                previous_row = len(row) + 100

            if previous_column < 0:
                previous_column = len(row) + 100

            #Check for alive neighbors
            try:
                if old_grid[next_row][cell.column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[previous_row][cell.column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[cell.row][previous_column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[cell.row][next_column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[previous_row][previous_column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[previous_row][next_column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[next_row][previous_column].alive:
                    alive += 1
            except:
                pass
            try:
                if old_grid[next_row][next_column].alive:
                    alive += 1
            except:
                pass

            if alive < 2 or alive > 3:
                cell.alive = False
            elif alive == 3:
                cell.alive = True

#Initialize grid list and render first grid view
create_array()
create_grid()

while not exitGame:

    for event in pygame.event.get():
        #Check if user wants to quit
        if event.type == pygame.QUIT:
            exitGame = True

        #Placing cells
        if event.type == pygame.MOUSEBUTTONDOWN and not gameStarted:
            for row in grid:
                for cell in row:
                    click = pygame.mouse.get_pos()
                    if cell.is_in_range(click[0], click[1]):
                        cell.alive = (not cell.alive)

        #Start the game
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                gameStarted = True

    if gameStarted: 
        check()

        #Check if all cells are dead
        if superior().number_alive == 0:
            exitGame = True

    #Render grid
    create_grid()   
    clock.tick(FPS)


pygame.quit()
quit()