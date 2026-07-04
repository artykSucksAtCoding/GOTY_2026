import pygame
from settings import*


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((36, 48), pygame.SRCALPHA)
        pygame.draw.rect(self.image, BLUE, (0, 0, 36, 48), border_radius=8)
        pygame.draw.rect(self.image, WHITE, (8, 12, 8, 8))
        pygame.draw.rect(self.image, WHITE, (22, 12, 8, 8))
        self.rect = self.image.get_rect(topleft=(x, y))

        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.alive = True
        self.spawn = (x, y)

        # --- прыжок: койот-тайм и контроль высоты по удержанию кнопки ---
        self.coyote_timer = 0        # сколько кадров ещё можно "прыгнуть с воздуха"
        self.jump_held_prev = False  # было ли зажато в прошлом кадре (для edge-детекта)
        self.is_jumping = False      # находимся ли в активной фазе прыжка (для jump-cut)

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

    def update(self, platforms):
        keys = pygame.key.get_pressed()

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
                elif self.air_jumps_used < MAX_AIR_JUMPS:
                    self.vel_y = AIR_JUMP_STRENGTH
                    self.air_jumps_used += 1
                    self.is_jumping = True
                    self.on_ground = False

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

            if (attack_pressed_now and self.attack_cooldown_timer <= 0
                    and not self.is_attacking and not self.down_attack_active):
                if down_held and not self.on_ground:
                    # удар вниз: резко бросаем игрока к земле, хитбокс — под ногами
                    self.down_attack_active = True
                    self.vel_y = DOWN_ATTACK_FALL_SPEED
                    self.attack_cooldown_timer = ATTACK_COOLDOWN_FRAMES
                else:
                    # обычный горизонтальный удар в сторону, куда смотрит игрок
                    self.is_attacking = True
                    self.attack_timer = ATTACK_DURATION_FRAMES
                    self.attack_cooldown_timer = ATTACK_COOLDOWN_FRAMES

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

        if self.rect.top > HEIGHT + 100:
            self.alive = False

        # --- анимация дэша: копим и старим "призраков" позади игрока ---
        for ghost in self.trail:
            ghost["age"] += 1
        self.trail = [g for g in self.trail if g["age"] < DASH_TRAIL_MAX_AGE]
        if self.is_dashing:
            self.trail.append({"rect": self.rect.copy(), "age": 0})

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
        """Хитбокс обычной атаки — прямоугольник сбоку от игрока, куда он смотрит."""
        if not self.is_attacking:
            return None
        if self.facing_right:
            x = self.rect.right
        else:
            x = self.rect.left - ATTACK_WIDTH
        y = self.rect.centery - ATTACK_HEIGHT // 2
        return pygame.Rect(x, y, ATTACK_WIDTH, ATTACK_HEIGHT)

    def get_down_attack_rect(self):
        """Хитбокс атаки вниз — узкая полоса прямо под ногами игрока."""
        if not self.down_attack_active:
            return None
        return pygame.Rect(self.rect.left, self.rect.bottom, self.rect.width, DOWN_ATTACK_HEIGHT)