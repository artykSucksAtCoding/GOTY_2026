import pygame
from settings import*

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=GREEN):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        if color == GREEN:
            pygame.draw.rect(self.image, DARK_GREEN, (0, 0, w, 6))
        self.rect = self.image.get_rect(topleft=(x, y))