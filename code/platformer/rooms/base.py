import pygame


class RoomExit:
    """Дверь на границе комнаты. Когда игрок касается rect — начинается переход
    в target_room, где он появится в точке spawn_points[entry_side]."""

    def __init__(self, rect: pygame.Rect, target_room: str, entry_side: str):
        self.rect = rect
        self.target_room = target_room
        self.entry_side = entry_side


class Room:
    """Данные одной комнаты уровня: спрайты, размеры, точки появления и переходы к соседям.

    spawn_points — словарь {сторона: (x, y)}. Ключ "default" используется, если игрок
    попадает в комнату не через дверь (например, самый первый запуск уровня).
    Остальные ключи ("left", "right", "top", "bottom") — куда поставить игрока,
    если он вошёл именно с этой стороны комнаты.
    """

    def __init__(self, platforms, coins, enemies, width, height,
                 flag=None, exits=None, spawn_points=None, weapons=None):
        self.platforms = platforms
        self.coins = coins
        self.enemies = enemies
        self.width = width
        self.height = height
        self.flag = flag                       # флаг финиша — обычно только в одной "конечной" комнате
        self.exits = exits or []               # список RoomExit
        self.spawn_points = spawn_points or {}  # side -> (x, y)
        # weapons — необязательный параметр: большинство комнат оружия не содержат,
        # тогда просто создаётся пустая группа
        self.weapons = weapons if weapons is not None else pygame.sprite.Group()

    def get_spawn(self, entry_side):
        return (self.spawn_points.get(entry_side)
                or self.spawn_points.get("default")
                or (50, self.height - 100))
