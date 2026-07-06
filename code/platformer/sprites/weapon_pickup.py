import math
import pygame
from settings import *


class WeaponPickup(pygame.sprite.Sprite):
    """Оружие, лежащее в комнате. weapon_id — ключ в WEAPON_ICON_PATHS / WEAPON_DAMAGE
    (settings.py) — просто подставь туда свои готовые файлы картинок."""

    def __init__(self, x, y, weapon_id):
        super().__init__()
        self.weapon_id = weapon_id

        icon_path = WEAPON_ICON_PATHS[weapon_id]
        try:
            self.image = pygame.image.load(icon_path).convert_alpha()
            self.image = pygame.transform.smoothscale(
                self.image, (WEAPON_PICKUP_SIZE, WEAPON_PICKUP_SIZE)
            )
        except (pygame.error, FileNotFoundError):
            # Заглушка на случай, если картинка ещё не подключена по этому пути —
            # чтобы игра не падала, пока ты не положишь реальные ассеты на место
            self.image = pygame.Surface((WEAPON_PICKUP_SIZE, WEAPON_PICKUP_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(self.image, YELLOW, self.image.get_rect(), border_radius=6)
            pygame.draw.rect(self.image, MASK_OUTLINE, self.image.get_rect(), 2, border_radius=6)

        self.rect = self.image.get_rect(topleft=(x, y))
        self._base_y = y
        self._bob_timer = 0.0

    def update(self):
        # лёгкое покачивание вверх-вниз — чтобы предмет было заметно на фоне
        self._bob_timer += 0.08
        self.rect.y = self._base_y + int(3 * math.sin(self._bob_timer))