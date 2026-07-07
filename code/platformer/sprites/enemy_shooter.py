import pygame
from settings import *
from sprites.enemy import Enemy
from sprites.projectile import Projectile


class ShooterEnemy(Enemy):
    """Патрулирует как обычный враг. Если игрок оказывается примерно на той же
    высоте (SHOOTER_ALIGNMENT_TOLERANCE по Y) — стреляет снарядом в его сторону.
    difficulty увеличивает скорость снаряда и уменьшает откат между выстрелами."""

    def __init__(self, x, y, left_bound, right_bound, difficulty=1):
        super().__init__(x, y, left_bound, right_bound)
        # перекрашиваем в фиолетовый, чтобы визуально отличался
        self.image = pygame.Surface((31, 32), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (150, 90, 190), (-1, 0, 32, 32), border_radius=6)
        pygame.draw.rect(self.image, BLACK, (5, 10, 6, 6))
        pygame.draw.rect(self.image, BLACK, (19, 10, 6, 6))

        self.difficulty = difficulty
        self.projectile_speed = PROJECTILE_SPEED_BASE + (difficulty - 1) * PROJECTILE_SPEED_PER_TIER
        cooldown = SHOOTER_COOLDOWN_BASE_FRAMES - (difficulty - 1) * SHOOTER_COOLDOWN_PER_TIER_FRAMES
        self.shoot_cooldown_max = max(SHOOTER_COOLDOWN_MIN_FRAMES, cooldown)
        self.shoot_cooldown = 0

    def update(self, platforms=None, player=None, projectiles=None):
        # обычное горизонтальное патрулирование, как у базового врага
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.left_bound:
            self.direction = 1
        elif self.rect.right >= self.right_bound:
            self.direction = -1

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if (player is not None and projectiles is not None and self.shoot_cooldown <= 0
                and abs(player.rect.centery - self.rect.centery) <= SHOOTER_ALIGNMENT_TOLERANCE):
            direction = 1 if player.rect.centerx >= self.rect.centerx else -1
            projectiles.add(
                Projectile(self.rect.centerx, self.rect.centery, direction, self.projectile_speed)
            )
            self.shoot_cooldown = self.shoot_cooldown_max