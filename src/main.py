import sys
import pygame
import time

class Material(object):
    def __init__(self, name, pos, radius, gravity):
        self.name = name
        self.x = pos[0]
        self.y = pos[1]
        self.radius = radius
        self.gravity = gravity

allsands = []

HEIGHT = 600
WIDTH = 800

def game():
    pygame.init()
    display = pygame.display.set_mode((WIDTH, HEIGHT))

    pygame.display.set_caption("***Sandbox***")
    clock = pygame.time.Clock()

    black = (0,0,0)
    white = (255,255,255)
    red = (255,0,0)
    yellow = (194, 178, 128)
    currentFlowPosition = (WIDTH/2, 0)
    flow = True
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if flow: #event.type == pygame.MOUSEBUTTONUP:
                print(currentFlowPosition) #print(event.pos)
                allsands.append(Material("Sand", currentFlowPosition, 5, 9))

        display.fill(black)
        pygame.draw.rect(display, white, (300, 580, 200, 20))

        for sand in allsands:
            pygame.draw.circle(display, yellow, (sand.x, sand.y), sand.radius)
            if sand.y >= 0 and sand.y < 645:
                sand.y += sand.gravity
        

        pygame.display.update()
        clock.tick(60)

game()
