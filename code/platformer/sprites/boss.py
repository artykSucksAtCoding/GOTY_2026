import random
import pygame
from settings import *
from sprites.enemy import Enemy
from sprites.projectile import Projectile


def _draw_boss_body(color):
    """Рисует тело босса лицом вправо для заданного цвета корпуса (обычный
    или "телеграф" перед ударом оземь) — асимметрично: более крупный шип на
    переднем (правом) плече, поменьше на заднем, и когтистая лапа, тянущаяся
    вперёд. Возвращает новую Surface — вызывается заново каждый кадр, т.к.
    цвет корпуса и текущее направление (facing) могут поменяться."""
    image = pygame.Surface((70, 90), pygame.SRCALPHA)
    pygame.draw.rect(image, color, (0, 0, 70, 90), border_radius=10)
    pygame.draw.rect(image, (150, 30, 40), (0, 0, 70, 90), border_radius=10, width=3)
    # шип на заднем (левом) плече — маленький
    pygame.draw.polygon(image, (150, 30, 40), [(18, 10), (4, 3), (13, 20)])
    # шип на переднем (правом) плече — крупный, указывает направление
    pygame.draw.polygon(image, (150, 30, 40), [(52, 7), (68, -2), (59, 19)])
    pygame.draw.rect(image, BLACK, (16, 26, 12, 12))
    pygame.draw.rect(image, BLACK, (42, 26, 12, 12))
    # ряд зубов
    for tooth_x in range(20, 50, 7):
        pygame.draw.polygon(image, BLACK, [(tooth_x, 44), (tooth_x + 5, 44), (tooth_x + 2, 50)])
    # когтистая лапа, тянущаяся вперёд (вправо)
    pygame.draw.polygon(image, (150, 30, 40), [(56, 46), (70, 50), (64, 63), (55, 60)])
    return image


class BossEnemy(Enemy):
    """Финальный босс (комната BOSS_ROOM_ID). ХП зависит от глобальной сложности
    (BOSS_MAX_HP), а не от тира комнаты, как у обычных врагов. Между атаками
    стоит на месте и разворачивается к игроку; когда откат истёк — выбирает
    случайно одну из трёх атак (веса — BOSS_ATTACK_WEIGHTS):

      * "charge" — быстрый рывок в сторону игрока (урон при касании — как у
        обычных врагов, см. ENEMY_CONTACT_DAMAGE в game.py);
      * "ranged" — короткая очередь снарядов (Projectile), как у ShooterEnemy;
      * "slam"   — удар оземь: сперва короткий "телеграф" (босс вспыхивает),
        затем широкая зона урона на полу вокруг него (danger_rect — game.py
        сам проверяет столкновение с игроком, как с down_attack_rect)."""

    def __init__(self, x, y, left_bound, right_bound, game_difficulty="normal"):
        super().__init__(x, y, left_bound, right_bound)

        # крупный тёмный силуэт — явно отличается от рядовых врагов
        self._base_color = (60, 20, 30)
        self._telegraph_color = (200, 60, 40)
        self.facing = 1  # 1 = лицом вправо, -1 = влево; обновляется по позиции игрока
        self.image = _draw_boss_body(self._base_color)
        self.rect = self.image.get_rect(topleft=(x, y))

        self.max_hp = BOSS_MAX_HP.get(game_difficulty, BOSS_MAX_HP["normal"])
        self.hp = self.max_hp

        self.speed = 0  # не патрулирует сам по себе — двигается только во время атак
        self.state = "idle"           # idle / charge / ranged / slam_telegraph / slam_active
        self.state_timer = 0
        self.attack_cooldown = BOSS_ATTACK_COOLDOWN_FRAMES // 2  # первая атака чуть раньше обычного отката

        self.charge_dir = 1
        self.ranged_shots_left = 0
        self.ranged_shot_timer = 0

        self.danger_rect = None  # активная зона урона от "slam" — читает game.py

    def take_damage(self, amount):
        super().take_damage(amount)
        if self.hp <= 0:
            self.danger_rect = None

    def _pick_attack(self):
        options = list(BOSS_ATTACK_WEIGHTS.keys())
        weights = [BOSS_ATTACK_WEIGHTS[o] for o in options]
        return random.choices(options, weights=weights, k=1)[0]

    def _start_attack(self, player):
        attack = self._pick_attack()
        if attack == "charge":
            self.state = "charge"
            self.state_timer = BOSS_CHARGE_DURATION_FRAMES
            self.charge_dir = 1 if player.rect.centerx >= self.rect.centerx else -1
        elif attack == "ranged":
            self.state = "ranged"
            self.ranged_shots_left = BOSS_RANGED_BURST_COUNT
            self.ranged_shot_timer = 0
        else:  # "slam"
            self.state = "slam_telegraph"
            self.state_timer = BOSS_SLAM_TELEGRAPH_FRAMES

    def update(self, platforms=None, player=None, projectiles=None):
        if self.hp <= 0:
            return

        if self.state == "idle":
            if self.attack_cooldown > 0:
                self.attack_cooldown -= 1
            elif player is not None:
                self._start_attack(player)
            self._sync_facing(player)
            return

        if self.state == "charge":
            self.rect.x += int(BOSS_CHARGE_SPEED * self.charge_dir)
            self.rect.left = max(self.left_bound, self.rect.left)
            self.rect.right = min(self.right_bound, self.rect.right)
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "idle"
                self.attack_cooldown = BOSS_ATTACK_COOLDOWN_FRAMES

        elif self.state == "ranged":
            if self.ranged_shot_timer > 0:
                self.ranged_shot_timer -= 1
            elif self.ranged_shots_left > 0 and player is not None and projectiles is not None:
                direction = 1 if player.rect.centerx >= self.rect.centerx else -1
                projectiles.add(
                    Projectile(self.rect.centerx, self.rect.centery, direction, BOSS_RANGED_PROJECTILE_SPEED)
                )
                self.ranged_shots_left -= 1
                self.ranged_shot_timer = BOSS_RANGED_BURST_DELAY_FRAMES
                if self.ranged_shots_left <= 0:
                    self.state = "idle"
                    self.attack_cooldown = BOSS_ATTACK_COOLDOWN_FRAMES

        elif self.state == "slam_telegraph":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "slam_active"
                self.state_timer = BOSS_SLAM_ACTIVE_FRAMES
                self.danger_rect = pygame.Rect(
                    self.rect.centerx - BOSS_SLAM_RANGE, self.rect.bottom - 16,
                    BOSS_SLAM_RANGE * 2, 16,
                )

        elif self.state == "slam_active":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.danger_rect = None
                self.state = "idle"
                self.attack_cooldown = BOSS_ATTACK_COOLDOWN_FRAMES

        # Перекрашиваем корпус во время телеграфа удара оземь — заметное
        # предупреждение игроку, что вот-вот будет урон на полу
        color = self._telegraph_color if self.state == "slam_telegraph" else self._base_color
        self._sync_facing(player, color)

    def _sync_facing(self, player, color=None):
        """Перерисовывает тело босса (нужно для смены цвета во время телеграфа
        удара оземь) и разворачивает его лицом к игроку — тело лицом вправо
        рисуется заново, затем отзеркаливается, если игрок сейчас слева."""
        if player is not None and player.rect.centerx != self.rect.centerx:
            self.facing = 1 if player.rect.centerx >= self.rect.centerx else -1
        body_color = color if color is not None else self._base_color
        canonical = _draw_boss_body(body_color)
        self.image = canonical if self.facing >= 0 else pygame.transform.flip(canonical, True, False)
