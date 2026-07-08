import pygame
from settings import *
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy_factory import spawn_boss
from .base import Room, RoomExit

ROOM_ID = "boss"
DIFFICULTY = ROOM_DIFFICULTY[ROOM_ID]

ROOM_WIDTH = 1000
ROOM_HEIGHT = HEIGHT


def build(game_difficulty="normal"):
    """Арена финального босса — ровный пол на всю комнату плюс пара невысоких
    платформ по краям, чтобы было куда запрыгнуть и увернуться от атак (см.
    sprites/boss.py: рывок/очередь снарядов/удар оземь). ХП босса зависит от
    game_difficulty (BOSS_MAX_HP в settings.py — 50 на "normal")."""
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, ROOM_WIDTH, 40),        # сплошной пол через всю арену
        (120, HEIGHT - 160, 160, 20),             # платформа слева — манёвр/укрытие
        (ROOM_WIDTH - 280, HEIGHT - 160, 160, 20),  # платформа справа — симметрично
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    # Небольшая награда по краям арены — не мешает бою в центре
    coin_positions = [
        (150, HEIGHT - 190), (180, HEIGHT - 190),
        (ROOM_WIDTH - 250, HEIGHT - 190), (ROOM_WIDTH - 220, HEIGHT - 190),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    boss = spawn_boss(
        ROOM_WIDTH // 2 - 35, HEIGHT - 40 - 90,
        160, ROOM_WIDTH - 160,
        game_difficulty=game_difficulty,
    )
    enemies.add(boss)

    # Дверь назад — на вершину. Дальше пути нет: победа над боссом сразу
    # завершает игру (см. PlayingState._tick_gameplay в game.py).
    exits = [
        RoomExit(
            rect=pygame.Rect(0, 0, 10, ROOM_HEIGHT),
            target_room="summit",
            entry_side="right",
        ),
    ]

    spawn_points = {
        "default": (60, HEIGHT - 100),
        "left": (60, HEIGHT - 100),   # приход с вершины
    }

    return Room(
        platforms, coins, enemies, ROOM_WIDTH, ROOM_HEIGHT,
        flag=None, exits=exits, spawn_points=spawn_points,
    )
