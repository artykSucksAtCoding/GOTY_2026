import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_enemy_group
from .base import Room, RoomExit

ROOM_ID = "summit"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1200
ROOM_HEIGHT = HEIGHT


def build(game_difficulty="normal"):
    """Вершина — предпоследняя комната цепочки, ведёт к логову босса (BOSS_ROOM_ID).
    Флаг финиша здесь больше не ставится — победа теперь наступает после того,
    как игрок одолеет босса в следующей комнате (см. PlayingState._tick_gameplay
    в game.py). Похожа по духу на сокровищницу — плотная россыпь монет и пара
    стражей на пути, — но выше и светлее (см. ROOM_BG_FALLBACK)."""
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 260, 40),
        (340, HEIGHT - 40, 260, 40),
        (680, HEIGHT - 40, 260, 40),
        (300, HEIGHT - 160, 150, 20),
        (600, HEIGHT - 260, 200, 20),
        # верхняя платформа продлена до самого края комнаты — по ней уходим к боссу
        (900, HEIGHT - 380, 300, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (320, HEIGHT - 190), (350, HEIGHT - 190),
        (630, HEIGHT - 290), (660, HEIGHT - 290), (690, HEIGHT - 290),
        (700, HEIGHT - 80), (740, HEIGHT - 80), (780, HEIGHT - 80),
        (930, HEIGHT - 410), (960, HEIGHT - 410), (990, HEIGHT - 410),
        (1020, HEIGHT - 410), (1050, HEIGHT - 410),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    # Последняя пара стражей перед логовом босса — самый высокий тир сложности
    # среди обычных комнат
    enemy_positions = [
        (700, HEIGHT - 40 - 32, 680, 920),
        (950, HEIGHT - 380 - 32, 900, 1170),
    ]
    enemies.add(spawn_enemy_group(enemy_positions, DIFFICULTY, game_difficulty))

    # Дверь назад — на небесную тропу; дверь вперёд — в логово босса
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="sky",
            entry_side="right",
        ),
        RoomExit(
            rect=pygame.Rect(ROOM_WIDTH - 10, 0, 10, ROOM_HEIGHT),
            target_room="boss",
            entry_side="left",
        ),
    ]

    spawn_points = {
        "default": (40, HEIGHT - 100),
        "left": (40, HEIGHT - 100),                        # приход с небесной тропы
        "right": (ROOM_WIDTH - 90, HEIGHT - 380 - 48),     # возвращение от босса — на верхней платформе
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )

