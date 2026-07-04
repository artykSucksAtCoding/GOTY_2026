import pygame
import sys
from settings import*

# game.py
from sprites.player import Player
from sprites.platforms import Platform
from sprites.coins import Coin
from sprites.enemy import Enemy
from sprites.flag import Flag


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("2D Платформер")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("Arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)

        self.running = True
        self.score = 0

        # игровой мир — создаётся заново при старте/рестарте
        self.player = None
        self.platforms = None
        self.coins = None
        self.enemies = None
        self.flag = None
        self.level_width = 0
        self.camera_x = 0

        # состояние, в которое нужно перейти после текущего кадра
        self.state = None
        self.next_state = None
        self.change_state(MenuState(self))

    def change_state(self, new_state):
        """Запрашивает смену состояния — произойдёт в начале следующего кадра."""
        self.next_state = new_state

    def new_level(self):
        self.player = Player(50, HEIGHT - 100)
        self.platforms, self.coins, self.enemies, self.flag, self.level_width = build_level()
        self.score = 0
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
        screen.fill(SKY_BLUE)

        for i in range(4):
            cx = (i * 260 + int(self.time * 0.5)) % (WIDTH + 200) - 100
            cy = 80 + i * 60
            pygame.draw.ellipse(screen, WHITE, (cx, cy, 120, 40))
            pygame.draw.ellipse(screen, WHITE, (cx + 30, cy - 15, 90, 40))

        g = self.game
        draw_text_centered(screen, "2D ПЛАТФОРМЕР", g.title_font, DARK_GREEN, HEIGHT // 2 - 100)
        draw_text_centered(screen, "Нажми ПРОБЕЛ или ENTER, чтобы начать", g.font, BLACK, HEIGHT // 2 + 10)
        draw_text_centered(screen, "Управление: A/D или стрелки — движение, SPACE/W — прыжок",
                            g.small_font, BLACK, HEIGHT // 2 + 60)
        draw_text_centered(screen, "Двойной прыжок в воздухе, SHIFT — рывок (дэш)",
                            g.small_font, BLACK, HEIGHT // 2 + 85)
        draw_text_centered(screen, "J/X — атака, вниз+J в воздухе — удар вниз",
                            g.small_font, BLACK, HEIGHT // 2 + 108)
        draw_text_centered(screen, "P/ESC — пауза, R — рестарт, ESC в меню — выход",
                            g.small_font, BLACK, HEIGHT // 2 + 131)


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
                # удачная атака вниз подбрасывает игрока — как в классических "boots"
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
                        g.player.alive = False

        if not g.player.alive:
            g.change_state(LostState(g))
            return

        if g.player.rect.colliderect(g.flag.rect):
            g.change_state(WonState(g))
            return

        g.camera_x = g.player.rect.centerx - WIDTH // 2
        g.camera_x = max(0, min(g.camera_x, g.level_width - WIDTH))

    def draw(self, screen):
        draw_world(self.game, screen)


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



def build_level():
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    level_data = [
        (0, HEIGHT - 40, 300, 40),
        (380, HEIGHT - 40, 300, 40),
        (760, HEIGHT - 40, 400, 40),
        (250, HEIGHT - 150, 150, 20),
        (500, HEIGHT - 230, 150, 20),
        (700, HEIGHT - 330, 150, 20),
        (900, HEIGHT - 420, 200, 20),
    ]
    for (x, y, w, h) in level_data:
        platforms.add(Platform(x, y, w, h))

    coin_positions = [
        (300, HEIGHT - 180), (330, HEIGHT - 180),
        (550, HEIGHT - 260), (580, HEIGHT - 260),
        (750, HEIGHT - 360), (780, HEIGHT - 360),
        (950, HEIGHT - 450), (980, HEIGHT - 450), (1020, HEIGHT - 450),
    ]
    for (x, y) in coin_positions:
        coins.add(Coin(x, y))

    enemies.add(Enemy(400, HEIGHT - 40 - 32, 380, 660))
    enemies.add(Enemy(780, HEIGHT - 40 - 32, 760, 1140))

    flag = Flag(1070, HEIGHT - 420 - 70)

    level_width = 1200
    return platforms, coins, enemies, flag, level_width


def draw_overlay(screen):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(DARK_OVERLAY)
    screen.blit(overlay, (0, 0))


def draw_text_centered(screen, text, font, color, y, x=WIDTH // 2):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(x, y))
    screen.blit(surf, rect)
    return rect


def draw_world(game: Game, screen):
    screen.fill(SKY_BLUE)
    cam = game.camera_x

    for plat in game.platforms:
        screen.blit(plat.image, plat.rect.move(-cam, 0))

    for coin in game.coins:
        screen.blit(coin.image, coin.rect.move(-cam, 0))

    for enemy in game.enemies:
        screen.blit(enemy.image, enemy.rect.move(-cam, 0))

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
    if game.player.is_dashing:
        # лёгкое растяжение спрайта по направлению рывка — усиливает ощущение скорости
        stretched = pygame.transform.smoothscale(
            game.player.image,
            (int(player_rect.width * 1.3), int(player_rect.height * 0.8)),
        )
        stretched_rect = stretched.get_rect(center=player_rect.center)
        screen.blit(stretched, stretched_rect)
    else:
        screen.blit(game.player.image, player_rect)

    # --- визуализация обычной атаки: белая дуга-полоса сбоку от игрока ---
    attack_rect = game.player.get_attack_rect()
    if attack_rect is not None:
        r = attack_rect.move(-cam, 0)
        slash_surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.ellipse(slash_surf, (*WHITE, 200), slash_surf.get_rect())
        screen.blit(slash_surf, r)

    # --- визуализация атаки вниз: жёлтый клин под ногами игрока ---
    down_attack_rect = game.player.get_down_attack_rect()
    if down_attack_rect is not None:
        r = down_attack_rect.move(-cam, 0)
        spike_surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.polygon(
            spike_surf, (*YELLOW, 220),
            [(0, 0), (r.width, 0), (r.width // 2, r.height)]
        )
        screen.blit(spike_surf, r)

    score_text = game.font.render(f"Монеты: {game.score}", True, BLACK)
    screen.blit(score_text, (16, 12))
