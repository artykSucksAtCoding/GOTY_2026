import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_enemy
from .base import Room, RoomExit

ROOM_ID = "bridge"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1300
ROOM_HEIGHT = HEIGHT

# Все сегменты моста — на одной высоте (земля), между ними — провалы,
# требующие точного прыжка (в отличие от лесенок-платформ в других комнатах)
BRIDGE_Y = HEIGHT - 40


def build():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, BRIDGE_Y, 220, 40),
        (280, BRIDGE_Y, 180, 40),    # провал 60px
        (540, BRIDGE_Y, 180, 40),    # провал 80px
        (800, BRIDGE_Y, 180, 40),    # провал 80px
        (1060, BRIDGE_Y, 240, 40),   # провал 80px, последний сегмент доходит до края комнаты
        # уединённая площадка над провалом — сюда не дойти по земле, только прыжком
        (605, BRIDGE_Y - 150, 60, 14),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    # Монеты над провалами — награда за риск, часть требует прыжка "по пути"
    coin_positions = [
        (150, BRIDGE_Y - 40), (190, BRIDGE_Y - 40),
        (315, BRIDGE_Y - 90),                        # над первым провалом
        (595, BRIDGE_Y - 110),                        # над вторым провалом
        (860, BRIDGE_Y - 90),                          # над третьим провалом
        (1120, BRIDGE_Y - 40), (1160, BRIDGE_Y - 40), (1200, BRIDGE_Y - 40),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    # По одному патрульному врагу на каждом среднем сегменте — заставляют
    # тайминг прыжка сочетать с уклонением, а не просто бежать по прямой
    enemies.add(spawn_enemy(300, BRIDGE_Y - 32, 280, 460, difficulty=DIFFICULTY))
    enemies.add(spawn_enemy(560, BRIDGE_Y - 32, 540, 720, difficulty=DIFFICULTY))
    enemies.add(spawn_enemy(820, BRIDGE_Y - 32, 800, 980, difficulty=DIFFICULTY))

    # уединённая площадка над провалом (605, BRIDGE_Y - 150) остаётся просто
    # бонусным паркуром за монетами — все оружия у игрока уже доступны с начала игры
    weapons = pygame.sprite.Group()

    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="caves",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="stairs",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, BRIDGE_Y - 60),
        "left": (40, BRIDGE_Y - 60),                # приход из caves через правую дверь
        "right": (ROOM_WIDTH - 90, BRIDGE_Y - 60),  # возвращение со stairs
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points, weapons=weapons,
    )