import pygame
from settings import*
import math
import random

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(self.image, YELLOW, (10, 10), 9)
        pygame.draw.circle(self.image, (200, 160, 0), (10, 10), 9, 2)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.base_y = y
        self.timer = random.uniform(0, 6.28)

    def update(self):
        self.timer += 0.1
        self.rect.y = self.base_y + int(4 * math.sin(self.timer))