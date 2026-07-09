import pygame
from settings import*

_DIRT_COLOR = (101, 67, 33)          # почва под травой
_DIRT_SHADOW = (78, 50, 24)          # тёмные вкрапления в почве + контур блока


def _draw_grass_platform(w, h):
    """Рисует детализированный блок платформы: земля с тёмными вкраплениями
    внизу и трава с торчащими травинками сверху — вместо сплошной заливки.
    Узор строится циклами по позиции (детерминированно, без random), поэтому
    выглядит одинаково при любой перезагрузке и подходит под любой размер
    платформы (w/h варьируются между комнатами)."""
    surface = pygame.Surface((w, h))
    surface.fill(_DIRT_COLOR)

    # тёмные вкрапления в почве — простой детерминированный "шум" по клеткам
    for yy in range(6, h, 6):
        for xx in range(0, w, 5):
            if (xx // 5 + yy // 6) % 3 == 0:
                pygame.draw.rect(surface, _DIRT_SHADOW, (xx, yy, 2, 2))

    # слой травы сверху
    grass_h = min(8, h)
    pygame.draw.rect(surface, DARK_GREEN, (0, 0, w, grass_h))

    # травинки, торчащие чуть выше края травы
    for xx in range(2, w, 6):
        blade_h = 3 if (xx // 6) % 2 == 0 else 5
        top_y = max(0, grass_h - blade_h)
        pygame.draw.line(surface, GREEN, (xx, grass_h), (xx, top_y), 2)

    # контур блока — чтобы платформа читалась как цельный "кирпич"
    pygame.draw.rect(surface, _DIRT_SHADOW, (0, 0, w, h), width=1)
    return surface


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=GREEN):
        super().__init__()
        if color == GREEN:
            # обычная платформа (трава/земля) — детализированный узор
            self.image = _draw_grass_platform(w, h)
        else:
            # особые платформы (например, невидимые стены арены босса,
            # color=BLACK + set_alpha(0)) остаются простой заливкой — им
            # текстура травы не нужна и не должна быть видна
            self.image = pygame.Surface((w, h))
            self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))