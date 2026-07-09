import pygame
from settings import *
from sprites.enemy import Enemy, _draw_grunt_body


class JumperEnemy(Enemy):
    """Патрулирует как обычный враг, но следит за прыжками игрока: если игрок
    прыгнул (player.just_jumped) в пределах JUMPER_TRIGGER_RANGE по X — этот враг
    тоже подскакивает, причём максимально высоко (сильнее, чем прыжок игрока),
    пытаясь достать игрока в воздухе. difficulty увеличивает силу прыжка."""

    def __init__(self, x, y, left_bound, right_bound, difficulty=1):
        super().__init__(x, y, left_bound, right_bound)
        # перекрашиваем в жёлтый, чтобы визуально отличался от обычного врага
        # (тело/рог/глаза/клык те же, что у базового врага — см. _draw_grunt_body)
        self.image_right = _draw_grunt_body(YELLOW)
        self.image_left = pygame.transform.flip(self.image_right, True, False)
        self.image = self.image_right if self.direction >= 0 else self.image_left

        self.difficulty = difficulty
        self.jump_strength = JUMPER_JUMP_STRENGTH_BASE + (difficulty - 1) * JUMPER_JUMP_STRENGTH_PER_TIER

        self.vel_y = 0
        self.on_ground = True
        self.jump_cooldown = 0

    def update(self, platforms=None, player=None, projectiles=None):
        # обычное горизонтальное патрулирование, как у базового врага
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.left_bound:
            self.direction = 1
        elif self.rect.right >= self.right_bound:
            self.direction = -1
        self.image = self.image_right if self.direction >= 0 else self.image_left

        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1

        # реакция на прыжок игрока рядом
        if (player is not None and self.on_ground and self.jump_cooldown <= 0
                and getattr(player, "just_jumped", False)):
            distance = abs(player.rect.centerx - self.rect.centerx)
            if distance <= JUMPER_TRIGGER_RANGE:
                self.vel_y = self.jump_strength
                self.on_ground = False
                self.jump_cooldown = JUMPER_COOLDOWN_FRAMES

        # простая вертикальная физика с приземлением на платформу под собой
        self.vel_y += GRAVITY
        if self.vel_y > 20:
            self.vel_y = 20
        self.rect.y += self.vel_y

        if platforms is not None and self.vel_y >= 0:
            for plat in platforms:
                if self.rect.colliderect(plat.rect):
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    break