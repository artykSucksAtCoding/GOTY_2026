import math
import random
import pygame
from settings import *
from sprites.enemy import Enemy


class FlyerEnemy(Enemy):
    """Игнорирует гравитацию и платформы — свободно парит. Вне радиуса просто
    покачивается на месте; как только игрок входит в FLYER_AGGRO_RADIUS —
    медленно летит прямо к нему по прямой. difficulty увеличивает и радиус
    обнаружения, и скорость полёта."""

    def __init__(self, x, y, left_bound, right_bound, difficulty=1):
        super().__init__(x, y, left_bound, right_bound)
        # перекрашиваем в голубой, чтобы визуально отличался (летающий тип)
        self.image = pygame.Surface((31, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, CYAN, (-1, 4, 32, 24))
        pygame.draw.rect(self.image, BLACK, (7, 12, 6, 6))
        pygame.draw.rect(self.image, BLACK, (19, 12, 6, 6))
        self.rect = self.image.get_rect(topleft=(x, y))

        self.difficulty = difficulty
        self.aggro_radius = FLYER_AGGRO_RADIUS_BASE + (difficulty - 1) * FLYER_AGGRO_RADIUS_PER_TIER
        self.speed_toward_player = FLYER_SPEED_BASE + (difficulty - 1) * FLYER_SPEED_PER_TIER

        self._base_y = float(self.rect.centery)
        self._pos_x = float(self.rect.centerx)
        self._pos_y = float(self.rect.centery)
        self._bob_timer = random.uniform(0, 6.28)

    def update(self, platforms=None, player=None, projectiles=None):
        if player is not None:
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if 0 < dist <= self.aggro_radius:
                self._pos_x += self.speed_toward_player * dx / dist
                self._pos_y += self.speed_toward_player * dy / dist
                self.rect.centerx = int(self._pos_x)
                self.rect.centery = int(self._pos_y)
                return

        # вне радиуса — тихо парит на месте, лёгкое покачивание вверх-вниз
        self._bob_timer += 0.05
        self._pos_y = self._base_y + 6 * math.sin(self._bob_timer)
        self.rect.centery = int(self._pos_y)