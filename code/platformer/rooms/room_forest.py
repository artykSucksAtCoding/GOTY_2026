import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy import Enemy
from .base import Room, RoomExit

ROOM_WIDTH = 1200
ROOM_HEIGHT = HEIGHT


def build():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        # (x, y, w, h)
        (0, HEIGHT - 40, 300, 40),
        (380, HEIGHT - 40, 300, 40),
        (760, HEIGHT - 40, 400, 40),
        (250, HEIGHT - 150, 150, 20),
        (500, HEIGHT - 230, 150, 20),
        (700, HEIGHT - 330, 150, 20),
        # верхняя платформа продлена до самого края комнаты — по ней можно дойти до двери
        (900, HEIGHT - 420, 300, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (300, HEIGHT - 180), (330, HEIGHT - 180),
        (550, HEIGHT - 260), (580, HEIGHT - 260),
        (750, HEIGHT - 360), (780, HEIGHT - 360),
        (950, HEIGHT - 450), (980, HEIGHT - 450), (1020, HEIGHT - 450),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    enemies.add(Enemy(400, HEIGHT - 40 - 32, 380, 660))
    enemies.add(Enemy(780, HEIGHT - 40 - 32, 760, 1140))

    # --- дверь на правом краю комнаты — ведёт в пещеры ---
    exits = [
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="caves",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (50, HEIGHT - 100),               # старт уровня
        "right": (ROOM_WIDTH - 90, HEIGHT - 420 - 48),  # возвращение из пещер — на верхней платформе у двери
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )