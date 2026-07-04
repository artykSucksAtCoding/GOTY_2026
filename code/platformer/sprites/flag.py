import pygame
from settings import*

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((40, 70), pygame.SRCALPHA)
        pygame.draw.rect(self.image, GRAY, (18, 0, 4, 70))
        pygame.draw.polygon(self.image, YELLOW, [(22, 4), (40, 14), (22, 24)])
        self.rect = self.image.get_rect(topleft=(x, y))
 