import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_enemy_group
from .base import Room, RoomExit

ROOM_ID = "vault"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1200
ROOM_HEIGHT = HEIGHT


def build(game_difficulty="normal"):
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 250, 40),
        (330, HEIGHT - 40, 250, 40),
        (660, HEIGHT - 40, 250, 40),
        (300, HEIGHT - 160, 150, 20),
        (550, HEIGHT - 240, 150, 20),
        # платформа-сокровищница продлена до самого края комнаты — по ней уходим дальше, на луг
        (950, HEIGHT - 320, 250, 20),
        # уединённая площадка высоко над комнатой — только двойным прыжком с (550, HEIGHT-240)
        (480, 90, 70, 16),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    # Плотная "россыпь" монет — комната-награда после долгого пути наверх по stairs
    coin_positions = [
        (320, HEIGHT - 190), (350, HEIGHT - 190),
        (570, HEIGHT - 270), (600, HEIGHT - 270), (630, HEIGHT - 270),
        (700, HEIGHT - 80), (740, HEIGHT - 80), (780, HEIGHT - 80),
        (970, HEIGHT - 350), (1000, HEIGHT - 350), (1030, HEIGHT - 350),
        (1060, HEIGHT - 350), (1090, HEIGHT - 350),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    # Пара стражей у самого сокровища — последнее препятствие перед выходом дальше
    enemy_positions = [
        (680, HEIGHT - 40 - 32, 660, 900),
        (960, HEIGHT - 320 - 32, 950, 1190),
    ]
    enemies.add(spawn_enemy_group(enemy_positions, DIFFICULTY, game_difficulty))

    # уединённая площадка высоко в комнате остаётся бонусным паркуром за монетами —
    # все оружия у игрока уже доступны с начала игры
    weapons = pygame.sprite.Group()

    # Дверь назад — на лестницу; дверь вперёд — на солнечный луг (дальше по пути)
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="stairs",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="meadow",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                        # приход по лестнице
        "right": (ROOM_WIDTH - 90, HEIGHT - 320 - 48),      # возвращение с луга — на платформе-сокровищнице
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points, weapons=weapons,
    )