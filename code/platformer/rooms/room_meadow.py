import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_enemy_group
from .base import Room, RoomExit

ROOM_ID = "meadow"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1250
ROOM_HEIGHT = HEIGHT


def build(game_difficulty="normal"):
    """Солнечный луг — первая из четырёх новых комнат за сокровищницей. Пологие
    платформы почти на одном уровне — комната-передышка после длинного подъёма
    по stairs/vault, светлее и веселее по фону (см. ROOM_BG_FALLBACK в settings.py)."""
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 300, 40),
        (380, HEIGHT - 40, 300, 40),
        (760, HEIGHT - 40, 300, 40),
        (250, HEIGHT - 140, 150, 20),
        (550, HEIGHT - 220, 150, 20),
        # верхняя платформа продлена до самого края комнаты — по ней уходим дальше, в сад
        (900, HEIGHT - 300, 350, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (300, HEIGHT - 170), (330, HEIGHT - 170),
        (600, HEIGHT - 250), (630, HEIGHT - 250),
        (950, HEIGHT - 330), (980, HEIGHT - 330), (1020, HEIGHT - 330),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    enemy_positions = [
        (400, HEIGHT - 40 - 32, 380, 660),
        (780, HEIGHT - 40 - 32, 760, 1060),
    ]
    enemies.add(spawn_enemy_group(enemy_positions, DIFFICULTY, game_difficulty))

    # --- дверь налево — обратно в сокровищницу; дверь направо — дальше, в сад ---
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="vault",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="orchard",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                        # приход из сокровищницы
        "right": (ROOM_WIDTH - 90, HEIGHT - 300 - 48),     # возвращение из сада — на верхней платформе
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )
