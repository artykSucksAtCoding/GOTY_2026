import pygame
from settings import *


def _draw_grunt_body(color):
    """Рисует детализированное тело врага, повёрнутое лицом вправо (движение
    вправо/direction=1) — асимметрично: более крупный "передний" глаз с
    бликом, рог на переднем верхнем углу и клык у пасти спереди-снизу.
    Используется базовым Enemy и JumperEnemy (только цвет отличается) —
    так оба класса получают детальный вид без дублирования отрисовки."""
    image = pygame.Surface((31, 32), pygame.SRCALPHA)
    pygame.draw.rect(image, color, (-1, 0, 32, 32), border_radius=6)
    # рог на переднем (правом) верхнем углу — указывает направление движения
    pygame.draw.polygon(image, GRAY, [(23, 1), (31, 1), (31, 8)])
    # задний (левый) глаз — маленький, полуприкрытый
    pygame.draw.rect(image, BLACK, (5, 12, 5, 5))
    # передний (правый) глаз — крупнее, с белым бликом ("смотрит" вперёд)
    pygame.draw.rect(image, BLACK, (19, 9, 8, 8))
    pygame.draw.rect(image, WHITE, (22, 11, 2, 2))
    # клык у пасти, смещён к переднему краю
    pygame.draw.polygon(image, BLACK, [(20, 24), (26, 24), (23, 29)])
    return image


class Enemy(pygame.sprite.Sprite):
    """Базовый враг — патрулирует между left_bound и right_bound.
    Сигнатура update() принимает platforms/player/projectiles, даже если сама
    не использует их — это нужно, чтобы pygame.sprite.Group.update(...) мог
    вызывать один и тот же набор аргументов для ЛЮБОГО типа врага в группе,
    включая особые типы (Jumper/Shooter/Flyer), которым эти данные нужны.

    Спрайт рисуется один раз лицом вправо (facing right), а зеркальная копия
    для движения влево кешируется рядом (image_right/image_left) — так не
    нужно ничего пересчитывать каждый кадр, только выбирать нужную картинку
    по знаку self.direction (без анимации, как и просили)."""

    def __init__(self, x, y, left_bound, right_bound):
        super().__init__()
        self.image_right = _draw_grunt_body(RED)
        self.image_left = pygame.transform.flip(self.image_right, True, False)
        self.image = self.image_right
        self.rect = self.image.get_rect(topleft=(x, y))
        self.left_bound = left_bound
        self.right_bound = right_bound
        self.speed = 1
        self.direction = 1

        # --- здоровье ---
        self.max_hp = ENEMY_MAX_HP
        self.hp = self.max_hp

    def update(self, platforms=None, player=None, projectiles=None):
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.left_bound:
            self.direction = 1
        elif self.rect.right >= self.right_bound:
            self.direction = -1
        self.image = self.image_right if self.direction >= 0 else self.image_left

    def take_damage(self, amount):
        """Получает урон от атаки игрока; умирает (kill), когда HP заканчивается."""
        self.hp -= amount
        if self.hp <= 0:
            self.kill()