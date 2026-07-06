import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy import Enemy
from sprites.flag import Flag
from sprites.weapon_pickup import WeaponPickup
from .base import Room, RoomExit

ROOM_WIDTH = 1200
ROOM_HEIGHT = HEIGHT


def build():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 250, 40),
        (330, HEIGHT - 40, 250, 40),
        (660, HEIGHT - 40, 250, 40),
        (300, HEIGHT - 160, 150, 20),
        (550, HEIGHT - 240, 150, 20),
        (950, HEIGHT - 320, 220, 20),   # платформа-сокровищница с флагом
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

    # Пара стражей у самого сокровища — последнее препятствие перед флагом
    enemies.add(Enemy(680, HEIGHT - 40 - 32, 660, 900))
    enemies.add(Enemy(960, HEIGHT - 320 - 32, 950, 1140))

    flag = Flag(1100, HEIGHT - 320 - 70)

    # --- оружие: sword3 (3 урона) — самый сильный клинок, спрятан выше всего в комнате ---
    weapons = pygame.sprite.Group()
    weapons.add(WeaponPickup(497, 90 - WEAPON_PICKUP_SIZE, "sword3"))

    # Только дверь назад — это последняя комната цепочки, дальше идти некуда
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="stairs",
            entry_side="right",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),   # приход по лестнице
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=flag, exits=exits, spawn_points=spawn_points, weapons=weapons,
    )