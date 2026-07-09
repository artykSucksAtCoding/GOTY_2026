import math
import random
import pygame
from settings import *
from sprites.enemy import Enemy


def _draw_flyer_body():
    """Рисует тело летуна лицом вправо: острый клюв спереди (справа) и
    небольшой хвост сзади (слева) — направление хорошо видно даже без
    отдельного глаза, т.к. форма тела уже асимметрична."""
    image = pygame.Surface((31, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(image, CYAN, (-1, 4, 32, 24))
    # хвост сзади (слева), треугольником
    pygame.draw.polygon(image, CYAN, [(2, 12), (2, 22), (-4, 17)])
    # клюв спереди (справа), торчит за пределы овала тела
    pygame.draw.polygon(image, GRAY, [(27, 13), (34, 16), (27, 20)])
    pygame.draw.rect(image, BLACK, (7, 12, 6, 6))
    pygame.draw.rect(image, BLACK, (19, 12, 6, 6))
    return image


class FlyerEnemy(Enemy):
    """Игнорирует гравитацию и платформы — свободно парит. Вне радиуса просто
    покачивается на месте; как только игрок входит в FLYER_AGGRO_RADIUS —
    медленно летит прямо к нему по прямой. difficulty увеличивает и радиус
    обнаружения, и скорость полёта."""

    def __init__(self, x, y, left_bound, right_bound, difficulty=1):
        super().__init__(x, y, left_bound, right_bound)
        # перекрашиваем в голубой и добавляем клюв/хвост, чтобы визуально
        # отличался (летающий тип) и показывал направление полёта
        self.image_right = _draw_flyer_body()
        self.image_left = pygame.transform.flip(self.image_right, True, False)
        self.image = self.image_right
        self.rect = self.image.get_rect(topleft=(x, y))
        self.facing_right = True

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
                if dx != 0:
                    self.facing_right = dx > 0
                    self.image = self.image_right if self.facing_right else self.image_left
                return

        # вне радиуса — тихо парит на месте, лёгкое покачивание вверх-вниз
        self._bob_timer += 0.05
        self._pos_y = self._base_y + 6 * math.sin(self._bob_timer)
        self.rect.centery = int(self._pos_y)