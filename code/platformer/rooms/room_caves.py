import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy import Enemy
from .base import Room, RoomExit

ROOM_WIDTH = 1350
ROOM_HEIGHT = HEIGHT


def build():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 260, 40),
        (330, HEIGHT - 40, 260, 40),
        (660, HEIGHT - 120, 220, 20),
        (940, HEIGHT - 210, 220, 20),
        # верхняя платформа продлена до самого края — по ней уходим дальше, в bridge
        (1180, HEIGHT - 300, 170, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (280, HEIGHT - 80), (600, HEIGHT - 80),
        (700, HEIGHT - 150), (740, HEIGHT - 150),
        (980, HEIGHT - 240), (1020, HEIGHT - 240),
        (1220, HEIGHT - 330), (1260, HEIGHT - 330),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    enemies.add(Enemy(340, HEIGHT - 40 - 32, 330, 590))
    enemies.add(Enemy(660, HEIGHT - 120 - 32, 660, 880))

    # --- дверь налево — обратно в лес; дверь направо — дальше, на мост ---
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="forest",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="bridge",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                       # приход из леса через правую дверь
        "right": (ROOM_WIDTH - 90, HEIGHT - 300 - 48),    # возвращение с моста — на верхней платформе
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )