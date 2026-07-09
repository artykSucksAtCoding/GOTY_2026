import pygame
from settings import *

# ===========================================================
# ПИКСЕЛЬНЫЙ РЫЦАРЬ ИГРОКА
# ===========================================================
# Спрайт рисуется по пикселям на маленькой сетке 12x16, а потом увеличивается
# БЕЗ сглаживания (pygame.transform.scale, а не smoothscale) — так сохраняются
# чёткие пиксельные грани, как в ретро-играх. 12x16 при масштабе x3 даёт ровно
# 36x48 — прежний размер хитбокса игрока не меняется.
#
# Чтобы силуэт читался как ЧЕЛОВЕК в доспехе, а не как робот/маска:
# - между шлемом и плечами есть узкая шея (открытый тон кожи, а не сплошной
#   металл встык, как раньше) — главный визуальный признак "человека";
# - забрало — узкая прорезь-щель (2 пикселя, как глаза), а не сплошная чёрная
#   панель на всю ширину шлема (это раньше и делало голову похожей на робота);
# - торс сужается к поясу (плечи шире талии) — человеческая V-образная фигура
#   вместо прямоугольного "кирпича";
# - ноги расходятся на две отдельные ступни-сапога.
#
# Символы сетки: '.' прозрачно, 'C' плюмаж/гребень шлема, 'H'/'h' шлем
# (светлый/теневой), 'V' прорезь-щель забрала (глаза), 'S' открытая кожа шеи,
# 'B' доспех торса, 'A' рука, 'G' пояс, 'L' нога, 'l' сапог.
_KNIGHT_PIXEL_GRID = [
    ".....CC.....",
    "....HHHH....",
    "...HHHHHH...",
    "..HHHHHHHH..",
    "..HHhVVhHH..",
    "..HHHHHHHH..",
    "....SSSS....",
    ".AABBBBBBAA.",
    ".AABBBBBBAA.",
    "..ABBBBBBA..",
    "..ABBBBBBA..",
    "...BBBBBB...",
    "...GGGGGG...",
    "...LLLLLL...",
    "...LL..LL...",
    "..lll..lll..",
]

# Второй кадр — ноги сведены вместе (без просвета между ними). Используется как
# шаг цикла ходьбы (чередуется со стойкой выше) и как поза в прыжке/падении —
# минимальная, но заметная анимация без лишних новых спрайтов.
_KNIGHT_PIXEL_GRID_STEP = (
    _KNIGHT_PIXEL_GRID[:13]
    + [
        "...LLLLLL...",
        "...LLLLLL...",
        "...llllll...",
    ]
)

_KNIGHT_SHADOW = (150, 150, 165)   # тень доспеха/рук — темнее базового BLUE
_KNIGHT_SKIN = (215, 175, 145)     # тон кожи открытой шеи — единственный "неметаллический" акцент

_KNIGHT_COLORS = {
    "C": CYAN,             # плюмаж/гребень шлема — тот же акцент, что у шлейфа дэша
    "H": BLUE,             # шлем, светлая сторона
    "h": _KNIGHT_SHADOW,   # шлем, теневая сторона (над прорезью забрала)
    "V": BLACK,            # прорезь-щель забрала (глаза)
    "S": _KNIGHT_SKIN,     # открытая кожа шеи
    "B": BLUE,             # доспех торса
    "A": _KNIGHT_SHADOW,   # рука
    "G": GRAY,             # пояс
    "L": _KNIGHT_SHADOW,   # нога
    "l": BLACK,            # сапог
}

_KNIGHT_PIXEL_SIZE = 3  # 12x16 сетка * 3 = 36x48 — совпадает со старым размером игрока

_WALK_ANIM_FRAME_DELAY = 8  # кадров между сменой ноги в цикле ходьбы (~7.5 раз/сек при 60 FPS)


def _build_knight_surface(grid=_KNIGHT_PIXEL_GRID):
    """Собирает спрайт рыцаря из сетки (по умолчанию _KNIGHT_PIXEL_GRID) —
    маленькая сетка рисуется по пикселям, а затем увеличивается без сглаживания.
    Принимает grid, чтобы можно было собрать разные кадры анимации (стойка/шаг)
    из одной и той же функции без дублирования кода отрисовки."""
    grid_width = len(grid[0])
    grid_height = len(grid)
    small = pygame.Surface((grid_width, grid_height), pygame.SRCALPHA)
    for row_index, row in enumerate(grid):
        for col_index, ch in enumerate(row):
            color = _KNIGHT_COLORS.get(ch)
            if color is not None:
                small.set_at((col_index, row_index), color)
    return pygame.transform.scale(
        small, (grid_width * _KNIGHT_PIXEL_SIZE, grid_height * _KNIGHT_PIXEL_SIZE)
    )


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # --- анимация: два кадра (стойка/шаг) собираются один раз при создании
        # игрока и переиспользуются каждый кадр в update() ниже — сама отрисовка
        # для дэша (растяжение) в game.py трогает game.player.image как обычно,
        # ей не важно, какой из двух кадров сейчас выбран.
        self.image_stand = _build_knight_surface(_KNIGHT_PIXEL_GRID)
        self.image_step = _build_knight_surface(_KNIGHT_PIXEL_GRID_STEP)
        self.image = self.image_stand
        self.rect = self.image.get_rect(topleft=(x, y))
        self.anim_timer = 0        # тикает, пока игрок идёт по земле — переключает кадр шага
        self.anim_walk_frame = False  # False = стойка (кадр 1), True = шаг (кадр 2)

        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.alive = True
        self.spawn = (x, y)

        # --- здоровье ---
        self.max_hp = PLAYER_MAX_HP
        self.hp = self.max_hp
        self.invuln_timer = 0  # >0 пока действует неуязвимость после удара

        # --- прыжок: койот-тайм и контроль высоты по удержанию кнопки ---
        self.coyote_timer = 0        # сколько кадров ещё можно "прыгнуть с воздуха"
        self.jump_held_prev = False  # было ли зажато в прошлом кадре (для edge-детекта)
        self.is_jumping = False      # находимся ли в активной фазе прыжка (для jump-cut)
        self.just_jumped = False     # True ровно в кадр, когда стартовал прыжок (для реакций врагов)

        # --- двойной прыжок ---
        self.air_jumps_used = 0      # сколько прыжков в воздухе уже потрачено

        # --- дэш ---
        self.dash_held_prev = False   # для edge-детекта нажатия Shift
        self.dash_timer = 0           # >0 пока идёт сам рывок
        self.dash_cooldown_timer = 0  # >0 пока дэш на перезарядке
        self.dash_dir = 1             # направление рывка (1 вправо, -1 влево)
        self.is_dashing = False
        self.trail = []               # шлейф "призраков" позади игрока во время дэша

        # --- атака ---
        self.attack_held_prev = False
        self.attack_timer = 0            # >0 пока активен хитбокс обычной атаки
        self.attack_cooldown_timer = 0   # общий откат для обеих атак
        self.is_attacking = False
        self.down_attack_active = False  # выполняется ли сейчас атака вниз
        self.attack_hit_ids = set()      # какие враги уже получили урон в текущем ударе

        # --- оружие ---
        # Все оружия доступны сразу — просто переключаются клавишами 1/2/3
        # (WEAPON_SWITCH_KEYS в settings.py), подбирать/находить их не нужно.
        self.weapon_id = "sword"          # см. WEAPON_ICON_PATHS / WEAPON_STATS в settings.py
        # Уверенность ML-распознавания текущего оружия (0..1) — масштабирует урон
        # (см. get_current_damage()). По умолчанию (переключение клавишами,
        # старт игры) считаем 50% — см. WEAPON_RECOGNITION_DEFAULT_CONFIDENCE.
        self.weapon_confidence = WEAPON_RECOGNITION_DEFAULT_CONFIDENCE
        self.arrow_requested = False      # True ровно в кадр выстрела из лука (game.py создаёт стрелу)

        # --- саунд эффекты ---
        self.attack_sound = pygame.mixer.Sound(ATTACK_SOUND_PATH)
        self.dash_sound = pygame.mixer.Sound(DASH_SOUND_PATH)

    def take_damage(self, amount, knockback_dir=None):
        """Наносит урон игроку, если он не в состоянии неуязвимости.
        knockback_dir: -1 (влево) или 1 (вправо) — куда отбросить игрока.
        Если не указано, отбрасывает в сторону, противоположную взгляду."""
        if self.invuln_timer > 0 or not self.alive:
            return

        self.hp -= amount
        self.invuln_timer = PLAYER_INVULN_FRAMES

        if knockback_dir is None:
            knockback_dir = -1 if self.facing_right else 1
        self.vel_x = knockback_dir * KNOCKBACK_SPEED_X
        self.vel_y = KNOCKBACK_SPEED_Y

        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def reset_position(self, x, y):
        """Телепортирует игрока в новую точку (переход между комнатами).
        HP и счёт не трогает — только позицию и переходные таймеры движения,
        чтобы игрок не влетел в новую комнату посреди дэша/атаки/прыжка."""
        self.rect.topleft = (x, y)
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False

        self.coyote_timer = 0
        self.is_jumping = False
        self.air_jumps_used = 0
        self.just_jumped = False

        self.is_dashing = False
        self.dash_timer = 0
        self.trail = []

        self.is_attacking = False
        self.attack_timer = 0
        self.down_attack_active = False
        self.attack_hit_ids = set()

        self.anim_timer = 0
        self.anim_walk_frame = False
        self.image = self.image_stand

    def equip_weapon(self, weapon_id, confidence=None):
        """Переключает текущее оружие игрока на weapon_id (см. WEAPON_STATS в settings.py).
        confidence — уверенность ML-распознавания (0..1), если оружие подключено через
        холст рисования (см. Game.finish_weapon_drawing); при обычном переключении
        (клавиши/подбор предмета) confidence не передаётся — используется дефолт 50%."""
        self.weapon_id = weapon_id
        self.weapon_confidence = confidence if confidence is not None else WEAPON_RECOGNITION_DEFAULT_CONFIDENCE

    def get_current_damage(self):
        """Реальный урон текущего оружия — WEAPON_STATS[...]["damage"] масштабируется
        линейно процентом уверенности ML-распознавания (weapon_confidence), но не
        меньше 1 (иначе неудачный рисунок оставлял бы оружие бесполезным)."""
        max_damage = WEAPON_STATS[self.weapon_id]["damage"]
        return max(1, round(max_damage * self.weapon_confidence))

    def update(self, platforms):
        keys = pygame.key.get_pressed()

        # Сбрасываем каждый кадр — станет True только в момент старта прыжка ниже
        self.just_jumped = False
        # Сбрасываем каждый кадр — станет True только в момент выстрела из лука ниже
        self.arrow_requested = False

        # Неуязвимость после удара тикает каждый кадр независимо от прочей логики
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        dash_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        # Койот-тайм и сброс запаса прыжков в воздухе при приземлении
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME_FRAMES
            self.air_jumps_used = 0
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        # --- ДЭШ: перезарядка тикает всегда, независимо от того, дэшим мы или нет ---
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1

        dash_pressed_now = dash_held and not self.dash_held_prev
        if (dash_pressed_now and self.dash_cooldown_timer <= 0
                and self.dash_timer <= 0 and not self.is_dashing):
            self.dash_timer = DASH_DURATION_FRAMES
            self.dash_sound.play()
            self.dash_cooldown_timer = DASH_COOLDOWN_FRAMES
            self.is_dashing = True
            self.dash_dir = 1 if self.facing_right else -1

        self.dash_held_prev = dash_held

        if self.is_dashing:
            
            # Во время рывка — фиксированная горизонтальная скорость, гравитация не действует
            self.vel_x = self.dash_dir * DASH_SPEED
            self.vel_y = 0
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
        else:
            # --- обычное горизонтальное движение ---
            self.vel_x = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vel_x = -PLAYER_SPEED
                self.facing_right = False
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vel_x = PLAYER_SPEED
                self.facing_right = True

            # --- прыжок: сначала обычный (земля/койот-тайм), затем двойной (в воздухе) ---
            jump_pressed_now = jump_held and not self.jump_held_prev
            if jump_pressed_now:
                if self.coyote_timer > 0:
                    self.vel_y = JUMP_STRENGTH
                    self.coyote_timer = 0
                    self.is_jumping = True
                    self.on_ground = False
                    self.just_jumped = True
                elif self.air_jumps_used < MAX_AIR_JUMPS:
                    self.vel_y = AIR_JUMP_STRENGTH
                    self.air_jumps_used += 1
                    self.is_jumping = True
                    self.on_ground = False
                    self.just_jumped = True

            # Контроль высоты: раннее отпускание обрезает вертикальную скорость
            if self.is_jumping and not jump_held and self.vel_y < MIN_JUMP_VELOCITY:
                self.vel_y = MIN_JUMP_VELOCITY

            if self.vel_y >= 0:
                self.is_jumping = False

            # --- атака: обычный удар и удар вниз (Down + атака, только в воздухе) ---
            attack_held = keys[pygame.K_j] or keys[pygame.K_x]
            down_held = keys[pygame.K_DOWN] or keys[pygame.K_s]
            attack_pressed_now = attack_held and not self.attack_held_prev
            self.attack_held_prev = attack_held

            if self.attack_cooldown_timer > 0:
                self.attack_cooldown_timer -= 1

            # --- переключение оружия: 1 = меч, 2 = топор, 3 = лук (все доступны сразу) ---
            # Блокируем переключение посреди удара/замаха, чтобы не сбить уже
            # запущенный таймер атаки текущим оружием.
            if not self.is_attacking and not self.down_attack_active:
                for key, weapon_id in WEAPON_SWITCH_KEYS.items():
                    if keys[key] and weapon_id != self.weapon_id:
                        self.equip_weapon(weapon_id)
                        break

            weapon_stats = WEAPON_STATS[self.weapon_id]

            if (attack_pressed_now and self.attack_cooldown_timer <= 0
                    and not self.is_attacking and not self.down_attack_active):
                if down_held and not self.on_ground:
                    # удар вниз: резко бросаем игрока к земле, хитбокс — под ногами
                    self.down_attack_active = True
                    self.vel_y = DOWN_ATTACK_FALL_SPEED
                    self.attack_cooldown_timer = ATTACK_COOLDOWN_FRAMES
                elif self.weapon_id == "bow":
                    # лук: не ближний хитбокс, а выстрел стрелой — саму стрелу
                    # создаёт game.py (там есть доступ до группы снарядов игрока)
                    self.arrow_requested = True
                    self.attack_cooldown_timer = weapon_stats["cooldown_frames"]
                    self.attack_sound.play()
                else:
                    # ближний удар в сторону, куда смотрит игрок — дальность и скорость
                    # зависят от текущего оружия (меч быстрый и короткий, топор — наоборот)
                    self.is_attacking = True
                    self.attack_timer = weapon_stats["duration_frames"]
                    self.attack_cooldown_timer = weapon_stats["cooldown_frames"]
                    self.attack_hit_ids = set()  # новый удар — список поражённых врагов чист

            if self.is_attacking:
                self.attack_timer -= 1
                if self.attack_timer <= 0:
                    self.is_attacking = False

            if self.down_attack_active and self.on_ground:
                self.down_attack_active = False

            self.vel_y += GRAVITY
            max_fall = DOWN_ATTACK_MAX_FALL if self.down_attack_active else 20
            if self.vel_y > max_fall:
                self.vel_y = max_fall

        self.jump_held_prev = jump_held

        self.rect.x += self.vel_x
        self.collide(platforms, "x")

        self.rect.y += self.vel_y
        self.on_ground = False
        self.collide(platforms, "y")

        # Падение в пропасть — мгновенная смерть независимо от HP (как яма в HK)
        if self.rect.top > HEIGHT + 100:
            self.alive = False
            self.hp = 0

        # --- анимация дэша: копим и старим "призраков" позади игрока ---
        for ghost in self.trail:
            ghost["age"] += 1
        self.trail = [g for g in self.trail if g["age"] < DASH_TRAIL_MAX_AGE]
        if self.is_dashing:
            self.trail.append({"rect": self.rect.copy(), "age": 0})

        # --- минимальная анимация ходьбы/прыжка: выбираем один из двух готовых
        # кадров (self.image_stand / self.image_step) в зависимости от того,
        # идёт игрок по земле или находится в воздухе.
        # Используем on_ground ИЛИ coyote_timer, а не только on_ground — из-за
        # особенностей физики (сброс vel_y при приземлении + gravity < 1px)
        # on_ground мигает True/False каждый кадр даже стоя на месте на ровной
        # платформе, а coyote_timer остаётся высоким, пока игрок реально на
        # земле, и сглаживает это мигание, не давая анимации дёргаться. ---
        grounded = self.on_ground or self.coyote_timer > 0
        if not grounded:
            # в воздухе (прыжок/падение) — ноги сведены вместе
            self.anim_timer = 0
            self.image = self.image_step
        elif self.vel_x != 0:
            self.anim_timer += 1
            if self.anim_timer >= _WALK_ANIM_FRAME_DELAY:
                self.anim_timer = 0
                self.anim_walk_frame = not self.anim_walk_frame
            self.image = self.image_step if self.anim_walk_frame else self.image_stand
        else:
            # стоим на месте — стойка, таймер шага сбрасывается
            self.anim_timer = 0
            self.anim_walk_frame = False
            self.image = self.image_stand

    def collide(self, platforms, direction):
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if direction == "x":
                    if self.vel_x > 0:
                        self.rect.right = plat.rect.left
                    elif self.vel_x < 0:
                        self.rect.left = plat.rect.right
                elif direction == "y":
                    if self.vel_y > 0:
                        self.rect.bottom = plat.rect.top
                        self.vel_y = 0
                        self.on_ground = True
                    elif self.vel_y < 0:
                        self.rect.top = plat.rect.bottom
                        self.vel_y = 0

    def get_attack_rect(self):
        """Хитбокс обычной атаки — прямоугольник сбоку от игрока, куда он смотрит.
        Размер зависит от текущего оружия (WEAPON_STATS): у меча — маленькая
        дальность, у топора — большая. У лука ближнего хитбокса нет вовсе —
        он стреляет стрелами (см. Player.arrow_requested и sprites/arrow.py)."""
        if not self.is_attacking:
            return None
        self.attack_sound.play()
        stats = WEAPON_STATS[self.weapon_id]
        width, height = stats["width"], stats["height"]
        if width <= 0 or height <= 0:
            return None
        if self.facing_right:
            x = self.rect.right
        else:
            x = self.rect.left - width
        y = self.rect.centery - height // 2
        return pygame.Rect(x, y, width, height)

    def get_arrow_spawn(self):
        """Точка появления стрелы (центр игрока по высоте, чуть впереди) и
        направление полёта — для создания Arrow в game.py."""
        direction = 1 if self.facing_right else -1
        x = self.rect.right if self.facing_right else self.rect.left
        y = self.rect.centery
        return x, y, direction

    def get_down_attack_rect(self):
        """Хитбокс атаки вниз — узкая полоса прямо под ногами игрока."""
        if not self.down_attack_active:
            return None
        return pygame.Rect(self.rect.left, self.rect.bottom, self.rect.width, DOWN_ATTACK_HEIGHT)