import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_enemy_group
from .base import Room, RoomExit

ROOM_ID = "sky"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1350
ROOM_HEIGHT = HEIGHT

# Облачные платформы поднимаются и снова опускаются волной — в отличие от
# ровного моста (bridge) или монотонного подъёма (stairs), здесь высота
# скачет вверх-вниз, требуя точных прыжков без твёрдой земли между ними.


def build(game_difficulty="normal"):
    """Небесная тропа среди облаков — самая воздушная комната из новых четырёх,
    почти вся дорога держится на плавающих платформах без земли внизу."""
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 200, 40),        # стартовая земля
        (260, HEIGHT - 140, 140, 20),
        (470, HEIGHT - 220, 140, 20),
        (680, HEIGHT - 300, 140, 20),
        (890, HEIGHT - 220, 140, 20),
        # последнее облако продлено до самого края комнаты — по нему уходим на вершину
        (1100, HEIGHT - 140, 250, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (290, HEIGHT - 170), (320, HEIGHT - 170),
        (500, HEIGHT - 250), (530, HEIGHT - 250),
        (710, HEIGHT - 330), (740, HEIGHT - 330),
        (920, HEIGHT - 250), (950, HEIGHT - 250),
        (1150, HEIGHT - 170), (1190, HEIGHT - 170), (1230, HEIGHT - 170),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    # Летающие враги здесь особенно уместны — spawn_enemy_group сама подберёт
    # разнообразие особых типов согласно тиру сложности комнаты
    enemy_positions = [
        (500, HEIGHT - 220 - 32, 470, 610),
        (900, HEIGHT - 220 - 32, 890, 1030),
    ]
    enemies.add(spawn_enemy_group(enemy_positions, DIFFICULTY, game_difficulty))

    # --- дверь налево — обратно в сад; дверь направо — дальше, на вершину ---
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="orchard",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="summit",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                        # приход из сада
        "right": (ROOM_WIDTH - 90, HEIGHT - 140 - 48),     # возвращение с вершины
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )
