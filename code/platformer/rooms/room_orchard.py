import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_enemy_group
from .base import Room, RoomExit

ROOM_ID = "orchard"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1300
ROOM_HEIGHT = HEIGHT


def build(game_difficulty="normal"):
    """Цветущий сад — терраса за террасой поднимается к небесному пути дальше.
    Чуть более резкий подъём, чем на лугу, — комната готовит игрока к прыжкам
    среди облаков в sky."""
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 280, 40),
        (360, HEIGHT - 40, 280, 40),
        (720, HEIGHT - 110, 220, 20),
        (300, HEIGHT - 190, 150, 20),
        # верхняя терраса продлена до самого края комнаты — по ней уходим дальше, к небу
        (980, HEIGHT - 190, 320, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (280, HEIGHT - 220), (310, HEIGHT - 220),
        (500, HEIGHT - 80), (540, HEIGHT - 80),
        (760, HEIGHT - 150), (800, HEIGHT - 150),
        (1020, HEIGHT - 230), (1060, HEIGHT - 230), (1100, HEIGHT - 230),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    enemy_positions = [
        (400, HEIGHT - 40 - 32, 360, 640),
        (760, HEIGHT - 110 - 32, 720, 940),
    ]
    enemies.add(spawn_enemy_group(enemy_positions, DIFFICULTY, game_difficulty))

    # --- дверь налево — обратно на луг; дверь направо — дальше, в небеса ---
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="meadow",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="sky",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                        # приход с луга
        "right": (ROOM_WIDTH - 90, HEIGHT - 190 - 48),     # возвращение с неба — на верхней террасе
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )
