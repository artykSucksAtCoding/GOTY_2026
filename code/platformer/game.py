import pygame
import sys
from settings import *

from sprites.player import Player
from rooms import build_room, first_room_id


class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Холлоу найт but better")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("Arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)


        self.running = True
        self.score = 0

        # --- комнаты ---
        self.room = None        # текущий объект Room целиком
        self.room_id = None     # id текущей комнаты (ключ в ROOM_BUILDERS)
        self.platforms = None   # ссылки на группы спрайтов ТЕКУЩЕЙ комнаты
        self.coins = None
        self.enemies = None
        self.flag = None
        self.level_width = 0
        self.camera_x = 0

        self.backgrounds_dict = {
            "forest": pygame.image.load("images/forest.png").convert(),
            "caves": pygame.image.load("images/caves.png").convert()
        }

        self.player = None

        # состояние, в которое нужно перейти после текущего кадра
        self.state = None
        self.next_state = None
        self.change_state(MenuState(self))

    def change_state(self, new_state):
        """Запрашивает смену состояния — произойдёт в начале следующего кадра."""
        self.next_state = new_state

    def new_level(self):
        """Полный рестарт: новый игрок (свежий HP/счёт) и первая комната."""
        self.score = 0
        self.player = None
        self.load_room(first_room_id(), "default")

    def load_room(self, room_id, entry_side="default"):
        """Загружает комнату по id и ставит игрока в точку появления,
        соответствующую стороне, с которой он вошёл (entry_side)."""
        self.room_id = room_id
        self.room = build_room(room_id)

        self.platforms = self.room.platforms
        self.coins = self.room.coins
        self.enemies = self.room.enemies
        self.flag = self.room.flag
        self.level_width = self.room.width

        spawn_x, spawn_y = self.room.get_spawn(entry_side)

        if self.player is None:
            self.player = Player(spawn_x, spawn_y)
        else:
            # телепортируем существующего игрока — HP и счёт сохраняются
            self.player.reset_position(spawn_x, spawn_y)

        self.camera_x = 0

    def run(self):
        while self.running:
            self.clock.tick(FPS)

            if self.next_state is not None:
                self.state = self.next_state
                self.next_state = None

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                self.state.handle_event(event)

            self.state.update()
            self.state.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


class State:
    """Базовый интерфейс состояния игры."""

    def __init__(self, game: Game):
        self.game = game

    def handle_event(self, event):
        pass

    def update(self):
        pass

    def draw(self, screen):
        pass


# ===========================================================
# СОСТОЯНИЕ: СТАРТОВОЕ МЕНЮ
# ===========================================================
class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.time = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.game.new_level()
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def update(self):
        self.time += 1

    def draw(self, screen):
        draw_dark_background(screen, self.time)

        g = self.game
        draw_text_centered(screen, "2D ПЛАТФОРМЕР", g.title_font, MASK_FULL, HEIGHT // 2 - 100)
        draw_text_centered(screen, "Нажми ПРОБЕЛ или ENTER, чтобы начать", g.font, WHITE, HEIGHT // 2 + 10)
        draw_text_centered(screen, "Управление: A/D или стрелки — движение, SPACE/W — прыжок",
                            g.small_font, GRAY, HEIGHT // 2 + 60)
        draw_text_centered(screen, "Двойной прыжок в воздухе, SHIFT — рывок (дэш)",
                            g.small_font, GRAY, HEIGHT // 2 + 85)
        draw_text_centered(screen, "J/X — атака, вниз+J в воздухе — удар вниз",
                            g.small_font, GRAY, HEIGHT // 2 + 108)
        draw_text_centered(screen, "P/ESC — пауза, R — рестарт, ESC в меню — выход",
                            g.small_font, GRAY, HEIGHT // 2 + 131)


# ===========================================================
# СОСТОЯНИЕ: ИГРОВОЙ ПРОЦЕСС
# ===========================================================
class PlayingState(State):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.game.change_state(PausedState(self.game))

    def update(self):
        g = self.game
        g.player.update(g.platforms)
        g.enemies.update()
        g.coins.update()

        collected = pygame.sprite.spritecollide(g.player, g.coins, dokill=True)
        g.score += len(collected)

        # --- атаки убивают врагов раньше, чем сработает урон от простого касания ---
        attack_rect = g.player.get_attack_rect()
        if attack_rect is not None:
            for enemy in list(g.enemies):
                if attack_rect.colliderect(enemy.rect):
                    enemy.kill()

        down_attack_rect = g.player.get_down_attack_rect()
        if down_attack_rect is not None:
            hit_someone = False
            for enemy in list(g.enemies):
                if down_attack_rect.colliderect(enemy.rect):
                    enemy.kill()
                    hit_someone = True
            if hit_someone:
                g.player.vel_y = DOWN_ATTACK_BOUNCE
                g.player.down_attack_active = False

        # Во время атаки/удара вниз игрок ненадолго неуязвим к обычному касанию врага
        invulnerable = g.player.is_attacking or g.player.down_attack_active

        if not invulnerable:
            for enemy in g.enemies:
                if g.player.rect.colliderect(enemy.rect):
                    if g.player.vel_y > 0 and g.player.rect.bottom - enemy.rect.top < 20:
                        enemy.kill()
                        g.player.vel_y = JUMP_STRENGTH / 1.5
                    else:
                        knockback_dir = -1 if g.player.rect.centerx < enemy.rect.centerx else 1
                        g.player.take_damage(ENEMY_CONTACT_DAMAGE, knockback_dir)

        if not g.player.alive:
            g.change_state(LostState(g))
            return

        # --- двери между комнатами: касание триггерит фейд-переход ---
        for room_exit in g.room.exits:
            if g.player.rect.colliderect(room_exit.rect):
                g.change_state(TransitionState(g, room_exit.target_room, room_exit.entry_side))
                return

        if g.flag is not None and g.player.rect.colliderect(g.flag.rect):
            g.change_state(WonState(g))
            return

        g.camera_x = g.player.rect.centerx - WIDTH // 2
        g.camera_x = max(0, min(g.camera_x, g.level_width - WIDTH))

    def draw(self, screen):
        draw_world(self.game, screen)


# ===========================================================
# СОСТОЯНИЕ: ПЕРЕХОД МЕЖДУ КОМНАТАМИ (fade-to-black, как в Hollow Knight)
# ===========================================================
class TransitionState(State):
    """Пока экран полностью не почернел, игрок видит старую комнату — она "замирает"
    (update() комнаты не вызывается). В момент полного затемнения подменяем комнату
    и плавно проявляемся обратно уже в новом месте."""

    def __init__(self, game, target_room, entry_side):
        super().__init__(game)
        self.target_room = target_room
        self.entry_side = entry_side
        self.phase = "out"   # "out" -> "in"
        self.timer = 0
        self.alpha = 0

    def update(self):
        self.timer += 1

        if self.phase == "out":
            progress = min(1.0, self.timer / ROOM_TRANSITION_FADE_FRAMES)
            self.alpha = int(255 * progress)
            if self.timer >= ROOM_TRANSITION_FADE_FRAMES:
                self.game.load_room(self.target_room, self.entry_side)
                self.phase = "in"
                self.timer = 0
        else:  # "in"
            progress = min(1.0, self.timer / ROOM_TRANSITION_FADE_FRAMES)
            self.alpha = int(255 * (1 - progress))
            if self.timer >= ROOM_TRANSITION_FADE_FRAMES:
                self.game.change_state(PlayingState(self.game))

    def draw(self, screen):
        draw_world(self.game, screen)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self.alpha))
        screen.blit(overlay, (0, 0))


# ===========================================================
# СОСТОЯНИЕ: ПАУЗА
# ===========================================================
class PausedState(State):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_r:
                self.game.new_level()
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_m:
                self.game.change_state(MenuState(self.game))

    def draw(self, screen):
        g = self.game
        draw_world(g, screen)
        draw_overlay(screen)
        draw_text_centered(screen, "ПАУЗА", g.big_font, WHITE, HEIGHT // 2 - 40)
        draw_text_centered(screen, "P/ESC — продолжить  •  R — рестарт  •  M — меню",
                            g.font, WHITE, HEIGHT // 2 + 20)


# ===========================================================
# СОСТОЯНИЕ: ПОБЕДА
# ===========================================================
class WonState(State):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.game.new_level()
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_m:
                self.game.change_state(MenuState(self.game))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def draw(self, screen):
        g = self.game
        draw_world(g, screen)
        draw_overlay(screen)
        draw_text_centered(screen, "Победа! Уровень пройден!", g.big_font, YELLOW, HEIGHT // 2 - 30)
        draw_text_centered(screen, f"Собрано монет: {g.score}", g.font, WHITE, HEIGHT // 2 + 20)
        draw_text_centered(screen, "R — рестарт  •  M — меню", g.font, WHITE, HEIGHT // 2 + 60)


# ===========================================================
# СОСТОЯНИЕ: ПОРАЖЕНИЕ
# ===========================================================
class LostState(State):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.game.new_level()
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_m:
                self.game.change_state(MenuState(self.game))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def draw(self, screen):
        g = self.game
        draw_world(g, screen)
        draw_overlay(screen)
        draw_text_centered(screen, "Игра окончена", g.big_font, RED, HEIGHT // 2 - 30)
        draw_text_centered(screen, "R — рестарт  •  M — меню", g.font, WHITE, HEIGHT // 2 + 20)


# ===========================================================
# ОТРИСОВКА
# ===========================================================
def draw_overlay(screen):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(DARK_OVERLAY)
    screen.blit(overlay, (0, 0))


def draw_text_centered(screen, text, font, color, y, x=WIDTH // 2):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(x, y))
    screen.blit(surf, rect)
    return rect


def draw_dark_background(screen, time_counter):
    """Тёмный фон с медленно плывущими 'спорами' — атмосфера в духе Hollow Knight."""
    screen.fill(DARK_BG)

    for i in range(3):
        bx = (i * 340 + int(time_counter * 0.15)) % (WIDTH + 300) - 150
        by = HEIGHT - 80 - (i % 2) * 40
        pygame.draw.ellipse(screen, DARK_BG_MID, (bx, by, 260, 160))

    for i in range(14):
        px = (i * 97 + int(time_counter * (0.4 + (i % 3) * 0.2))) % (WIDTH + 40) - 20
        py = (i * 53) % HEIGHT
        radius = 2 + (i % 3)
        spore_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(spore_surf, (*FOG_COLOR, 90), (radius, radius), radius)
        screen.blit(spore_surf, (px, py))


def draw_hp_bar(screen, player):
    """Полоски здоровья в виде 'масок' — как жизни рыцаря в Hollow Knight."""
    mask_size = 22
    gap = 8
    x0, y0 = 20, 50

    for i in range(player.max_hp):
        cx = x0 + i * (mask_size + gap) + mask_size // 2
        cy = y0 + mask_size // 2
        half = mask_size // 2
        points = [
            (cx, cy - half),
            (cx + half, cy),
            (cx, cy + half),
            (cx - half, cy),
        ]
        color = MASK_FULL if i < player.hp else MASK_EMPTY
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, MASK_OUTLINE, points, 2)

def draw_background_image(screen, image):
    screen.blit(image, (0, 0))

 
def draw_world(game: Game, screen):
    if (game.room_id == "forest" or game.room_id == "caves"):
        draw_background_image(screen, game.backgrounds_dict[game.room_id])
    else:
        draw_dark_background(screen, pygame.time.get_ticks() // 16)
    cam = game.camera_x

    for plat in game.platforms:
        screen.blit(plat.image, plat.rect.move(-cam, 0))

    for coin in game.coins:
        screen.blit(coin.image, coin.rect.move(-cam, 0))

    for enemy in game.enemies:
        screen.blit(enemy.image, enemy.rect.move(-cam, 0))

    if game.flag is not None:
        screen.blit(game.flag.image, game.flag.rect.move(-cam, 0))

    # --- шлейф дэша: гаснущие "призраки" позади игрока ---
    for ghost in game.player.trail:
        fade = max(0.0, 1 - ghost["age"] / DASH_TRAIL_MAX_AGE)
        alpha = int(150 * fade)
        if alpha <= 0:
            continue
        ghost_rect = ghost["rect"].move(-cam, 0)
        ghost_surf = pygame.Surface(ghost_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(ghost_surf, (*CYAN, alpha), ghost_surf.get_rect(), border_radius=8)
        screen.blit(ghost_surf, ghost_rect)

    player_rect = game.player.rect.move(-cam, 0)
    flickering = game.player.invuln_timer > 0 and (game.player.invuln_timer // 4) % 2 == 0

    if not flickering:
        if game.player.is_dashing:
            stretched = pygame.transform.smoothscale(
                game.player.image,
                (int(player_rect.width * 1.3), int(player_rect.height * 0.8)),
            )
            stretched_rect = stretched.get_rect(center=player_rect.center)
            screen.blit(stretched, stretched_rect)
        else:
            screen.blit(game.player.image, player_rect)

    attack_rect = game.player.get_attack_rect()
    if attack_rect is not None:
        r = attack_rect.move(-cam, 0)
        slash_surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.ellipse(slash_surf, (*WHITE, 200), slash_surf.get_rect())
        screen.blit(slash_surf, r)

    down_attack_rect = game.player.get_down_attack_rect()
    if down_attack_rect is not None:
        r = down_attack_rect.move(-cam, 0)
        spike_surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.polygon(
            spike_surf, (*YELLOW, 220),
            [(0, 0), (r.width, 0), (r.width // 2, r.height)]
        )
        screen.blit(spike_surf, r)

    score_text = game.font.render(f"Монеты: {game.score}", True, WHITE)
    screen.blit(score_text, (16, 12))
    draw_hp_bar(screen, game.player)