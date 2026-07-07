import random
from settings import *
from sprites.enemy import Enemy
from sprites.enemy_jumper import JumperEnemy
from sprites.enemy_shooter import ShooterEnemy
from sprites.enemy_flyer import FlyerEnemy

_SPECIAL_TYPES = [JumperEnemy, ShooterEnemy, FlyerEnemy]


def spawn_enemy(x, y, left_bound, right_bound, difficulty=1):
    """Создаёт врага на позиции (x, y). С небольшим шансом (растёт с difficulty)
    вместо обычного Enemy создаётся один из трёх особых типов — тоже усиленный
    под текущий уровень сложности. difficulty обычно берётся из
    settings.ROOM_DIFFICULTY[room_id] в момент постройки комнаты."""
    chance = min(
        SPECIAL_ENEMY_MAX_CHANCE,
        SPECIAL_ENEMY_BASE_CHANCE + (difficulty - 1) * SPECIAL_ENEMY_CHANCE_PER_TIER,
    )
    if random.random() < chance:
        enemy_cls = random.choice(_SPECIAL_TYPES)
        return enemy_cls(x, y, left_bound, right_bound, difficulty=difficulty)
    return Enemy(x, y, left_bound, right_bound)