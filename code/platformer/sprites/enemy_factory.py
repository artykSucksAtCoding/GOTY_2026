import random
import pygame
from settings import *
from sprites.enemy import Enemy
from sprites.enemy_jumper import JumperEnemy
from sprites.enemy_shooter import ShooterEnemy
from sprites.enemy_flyer import FlyerEnemy
from sprites.boss import BossEnemy

_SPECIAL_TYPES = [JumperEnemy, ShooterEnemy, FlyerEnemy]


def spawn_boss(x, y, left_bound, right_bound, game_difficulty="normal"):
    """Создаёт босса финальной комнаты (BOSS_ROOM_ID) — ХП зависит от глобальной
    сложности игрока (BOSS_MAX_HP в settings.py), а не от тира комнаты."""
    return BossEnemy(x, y, left_bound, right_bound, game_difficulty=game_difficulty)


def resolve_difficulty(room_tier, game_difficulty="normal"):
    """Итоговый параметр сложности для spawn-формулы особых врагов — тир текущей
    комнаты (ROOM_DIFFICULTY[room_id]) со сдвигом от глобальной сложности,
    выбранной игроком в меню (DIFFICULTY_TIER_OFFSET). Не даём уйти ниже 1."""
    offset = DIFFICULTY_TIER_OFFSET.get(game_difficulty, 0)
    return max(1, room_tier + offset)


def spawn_enemy(x, y, left_bound, right_bound, difficulty=1):
    """Создаёт врага на позиции (x, y). С небольшим шансом (растёт с difficulty)
    вместо обычного Enemy создаётся один из трёх особых типов — тоже усиленный
    под текущий уровень сложности. difficulty обычно берётся из
    resolve_difficulty(ROOM_DIFFICULTY[room_id], game_difficulty)."""
    chance = min(
        SPECIAL_ENEMY_MAX_CHANCE,
        SPECIAL_ENEMY_BASE_CHANCE + (difficulty - 1) * SPECIAL_ENEMY_CHANCE_PER_TIER,
    )
    if random.random() < chance:
        enemy_cls = random.choice(_SPECIAL_TYPES)
        return enemy_cls(x, y, left_bound, right_bound, difficulty=difficulty)
    return Enemy(x, y, left_bound, right_bound)


def spawn_enemy_group(positions, room_tier, game_difficulty="normal"):
    """Заполняет группу врагов по набору точек спавна (x, y, left_bound, right_bound) —
    так комнатам не нужно вручную дублировать вызовы spawn_enemy на каждой позиции.
    Учитывает и тир сложности комнаты (room_tier — ROOM_DIFFICULTY[room_id]), и
    глобальную сложность игрока, выбранную в меню перед стартом (game_difficulty):
      - итоговый difficulty для spawn-формулы особых врагов сдвигается
        (см. resolve_difficulty / DIFFICULTY_TIER_OFFSET в settings.py);
      - на лёгкой сложности враг на точке спавна иногда пропускается совсем
        (DIFFICULTY_SKIP_ENEMY_CHANCE) — состав жиже;
      - на сложной сложности на той же точке иногда дополнительно появляется
        ещё один враг чуть в стороне (DIFFICULTY_EXTRA_ENEMY_CHANCE) — состав
        гуще, без переделки карт комнат."""
    difficulty = resolve_difficulty(room_tier, game_difficulty)
    skip_chance = DIFFICULTY_SKIP_ENEMY_CHANCE.get(game_difficulty, 0.0)
    extra_chance = DIFFICULTY_EXTRA_ENEMY_CHANCE.get(game_difficulty, 0.0)

    group = pygame.sprite.Group()
    for (x, y, left_bound, right_bound) in positions:
        if skip_chance > 0 and random.random() < skip_chance:
            continue

        group.add(spawn_enemy(x, y, left_bound, right_bound, difficulty=difficulty))

        if extra_chance > 0 and random.random() < extra_chance:
            offset_x = random.choice([-40, 40])
            extra_x = min(max(x + offset_x, left_bound), max(left_bound, right_bound - 30))
            group.add(spawn_enemy(extra_x, y, left_bound, right_bound, difficulty=difficulty))

    return group