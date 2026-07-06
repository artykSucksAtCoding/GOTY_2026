import pygame
from settings import *

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, left_bound, right_bound):
        super().__init__()
        self.image = pygame.Surface((31, 32), pygame.SRCALPHA)
        pygame.draw.rect(self.image, RED, (-1, 0, 32, 32), border_radius=6)
        pygame.draw.rect(self.image, BLACK, (5, 10, 6, 6))
        pygame.draw.rect(self.image, BLACK, (19, 10, 6, 6))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.left_bound = left_bound
        self.right_bound = right_bound
        self.speed = 1
        self.direction = 1

        # --- здоровье ---
        self.max_hp = ENEMY_MAX_HP
        self.hp = self.max_hp

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.left_bound:
            self.direction = 1
        elif self.rect.right >= self.right_bound:
            self.direction = -1

    def take_damage(self, amount):
        """Получает урон от атаки игрока; умирает (kill), когда HP заканчивается."""
        self.hp -= amount
        if self.hp <= 0:
            self.kill()