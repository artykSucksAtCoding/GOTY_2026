import pygame
from settings import *


class Projectile(pygame.sprite.Sprite):
    """Летит по прямой горизонтали в direction (-1 влево, 1 вправо).
    Самоуничтожается через PROJECTILE_LIFETIME_FRAMES, если ни во что не попал —
    так не нужно знать границы текущей комнаты, чтобы не улетать в бесконечность."""

    def __init__(self, x, y, direction, speed):
        super().__init__()
        self.image = pygame.Surface((PROJECTILE_SIZE, PROJECTILE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(
            self.image, YELLOW,
            (PROJECTILE_SIZE // 2, PROJECTILE_SIZE // 2), PROJECTILE_SIZE // 2
        )
        pygame.draw.circle(
            self.image, MASK_OUTLINE,
            (PROJECTILE_SIZE // 2, PROJECTILE_SIZE // 2), PROJECTILE_SIZE // 2, 1
        )
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction
        self.speed = speed
        self.lifetime = PROJECTILE_LIFETIME_FRAMES

    def update(self, platforms=None, player=None, projectiles=None):
        self.rect.x += int(self.speed * self.direction)
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()