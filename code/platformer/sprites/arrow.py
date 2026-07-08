import pygame
from settings import *


class Arrow(pygame.sprite.Sprite):
    """Стрела, выпущенная игроком из лука. Летит по прямой горизонтали в direction
    (-1 влево, 1 вправо) и наносит урон первому врагу, в которого попадёт.
    Самоуничтожается через ARROW_LIFETIME_FRAMES, если ни во что не попала."""

    def __init__(self, x, y, direction, damage):
        super().__init__()
        try:
            self.image = pygame.image.load(ARROW_ICON_PATH).convert_alpha()
            self.image = pygame.transform.smoothscale(self.image, (ARROW_SIZE * 3, ARROW_SIZE))
            if direction < 0:
                self.image = pygame.transform.flip(self.image, True, False)
        except (pygame.error, FileNotFoundError):
            # Заглушка на случай, если спрайт стрелы ещё не подключён по этому пути —
            # рисуем простой треугольный наконечник, указывающий в сторону полёта
            self.image = pygame.Surface((ARROW_SIZE * 3, ARROW_SIZE), pygame.SRCALPHA)
            w, h = self.image.get_size()
            if direction >= 0:
                points = [(0, 0), (0, h), (w, h // 2)]
            else:
                points = [(w, 0), (w, h), (0, h // 2)]
            pygame.draw.polygon(self.image, YELLOW, points)
            pygame.draw.polygon(self.image, MASK_OUTLINE, points, 1)

        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction
        self.speed = ARROW_SPEED
        self.damage = damage
        self.lifetime = ARROW_LIFETIME_FRAMES

    def update(self, platforms=None, player=None, projectiles=None):
        self.rect.x += int(self.speed * self.direction)
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
