import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy import Enemy
from .base import Room, RoomExit

ROOM_WIDTH = 1300
ROOM_HEIGHT = HEIGHT


def build():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    # Каждая следующая ступень выше и уже предыдущей — комната проверяет
    # владение двойным прыжком и дэшем, а не просто бег по прямой
    level_data = [
        (0, HEIGHT - 40, 220, 40),      # стартовая земля
        (260, HEIGHT - 110, 160, 20),
        (470, HEIGHT - 190, 160, 20),
        (680, HEIGHT - 270, 160, 20),
        (890, HEIGHT - 350, 160, 20),
        (1100, HEIGHT - 430, 200, 20),  # верхняя ступень, доходит до края комнаты
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    # Монеты выстроены вдоль пути наверх — визуально показывают траекторию подъёма
    coin_positions = [
        (300, HEIGHT - 150), (330, HEIGHT - 150),
        (510, HEIGHT - 230), (540, HEIGHT - 230),
        (720, HEIGHT - 310), (750, HEIGHT - 310),
        (930, HEIGHT - 390), (960, HEIGHT - 390),
        (1150, HEIGHT - 470), (1190, HEIGHT - 470), (1230, HEIGHT - 470),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    # Враги поджидают на паре средних ступеней — надо разобраться с ними
    # прямо во время подъёма, не имея твёрдой земли под ногами вокруг
    enemies.add(Enemy(480, HEIGHT - 190 - 32, 470, 630))
    enemies.add(Enemy(900, HEIGHT - 350 - 32, 890, 1050))

    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="bridge",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="vault",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                          # приход с моста
        "right": (ROOM_WIDTH - 90, HEIGHT - 430 - 48),       # возвращение из vault — на верхней ступени
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )