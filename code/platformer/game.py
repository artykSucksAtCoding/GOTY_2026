import pygame
import sys
from settings import *

from sprites.player import Player
from rooms import build_room, first_room_id
import leaderboard


class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("МЕГА-ПЛАТФОРМЕР")
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
        self.weapons = None
        self.flag = None
        self.level_width = 0
        self.camera_x = 0
        self.projectiles = None   # снаряды стрелков — переходное боевое состояние, не часть комнаты
        self.run_timer_frames = 0  # сколько кадров прошло с начала текущего прохождения (для лидерборда)

        # --- кастомные фоны комнат: room_id -> Surface ---
        # .get() при отрисовке подстрахует комнаты, для которых картинки ещё нет —
        # тогда просто используется процедурный тёмный фон
        self.backgrounds_dict = {
            "forest": pygame.image.load("images/backgrounds/forest.png").convert(),
            #"caves": pygame.image.load("images/backgrounds/caves.png").convert(),
            "bridge": pygame.image.load("images/backgrounds/bridge.png").convert(),
            #"vault": pygame.image.load("images/backgrounds/vault.png").convert(),
        }

        # --- иконки оружия для HUD: weapon_id -> Surface ---
        self.weapon_icons = {}
        for weapon_id, icon_path in WEAPON_ICON_PATHS.items():
            try:
                icon = pygame.image.load(icon_path).convert_alpha()
                icon = pygame.transform.smoothscale(icon, (WEAPON_ICON_HUD_SIZE, WEAPON_ICON_HUD_SIZE))
            except (pygame.error, FileNotFoundError):
                # заглушка, пока реальная иконка не подключена по этому пути
                icon = pygame.Surface((WEAPON_ICON_HUD_SIZE, WEAPON_ICON_HUD_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(icon, YELLOW, icon.get_rect(), border_radius=6)
            self.weapon_icons[weapon_id] = icon

        self.player = None

        # --- настройки: графика ---
        self.theme_index = 0          # индекс в BG_THEMES
        self.effects_quality = "normal"  # ключ в EFFECTS_QUALITY_LEVELS
        self.fullscreen = False

        # --- настройки: звук (множители 0.0-1.0 поверх базовых значений в settings.py) ---
        self.master_music_volume = 1.0
        self.master_sfx_volume = 1.0

        # --- музыка ---
        # Только ЗАГРУЖАЕМ дорожку здесь — играть она начнёт не сразу, а лишь когда
        # игрок реально нажмёт "играть" (см. new_level() -> start_music()).
        # Поэтому в главном меню музыки нет вообще.
        self._music_loaded = False
        try:
            pygame.mixer.music.load(MUSIC_PATH)
            self._music_loaded = True
        except pygame.error:
            pass

        # --- звук гейм-овера (одноразовый, не музыкальный канал) ---
        try:
            self.gameover_sound = pygame.mixer.Sound(GAME_OVER_SOUND_PATH)
        except pygame.error:
            self.gameover_sound = None
        self.apply_sfx_volume()

        # состояние, в которое нужно перейти после текущего кадра
        self.state = None
        self.next_state = None
        self.change_state(MenuState(self))

    @property
    def theme(self):
        """Текущая палитра фона/HUD — словарь из BG_THEMES."""
        return BG_THEMES[self.theme_index]

    @property
    def spore_count(self):
        """Сколько фоновых частиц рисовать — зависит от выбранного качества эффектов."""
        return EFFECTS_QUALITY_SPORE_COUNTS[self.effects_quality]

    def apply_sfx_volume(self):
        """Применяет текущую master_sfx_volume ко всем звуковым эффектам —
        и к гейм-оверу (живёт в Game), и к атаке/дэшу (живут в Player, если он уже создан)."""
        if self.gameover_sound is not None:
            self.gameover_sound.set_volume(GAME_OVER_SOUND_VOLUME * self.master_sfx_volume)
        if self.player is not None:
            self.player.attack_sound.set_volume(self.master_sfx_volume)
            self.player.dash_sound.set_volume(self.master_sfx_volume)

    def apply_fullscreen(self):
        """Переключает окно между обычным и полноэкранным режимом."""
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)

    def start_music(self):
        """Запускает фоновую музыку с начала. Вызывается только когда игрок
        реально начинает партию — из new_level() (старт из меню или рестарт)."""
        if not self._music_loaded:
            return
        try:
            pygame.mixer.music.play(loops=-1)
            pygame.mixer.music.set_volume(MUSIC_VOLUME_NORMAL * self.master_music_volume)
        except pygame.error:
            pass

    def stop_music(self):
        """Полностью останавливает музыку (гейм-овер, возврат в меню)."""
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    def change_state(self, new_state):
        """Запрашивает смену состояния — произойдёт в начале следующего кадра."""
        self.next_state = new_state

    def new_level(self):
        """Полный рестарт: новый игрок (свежий HP/счёт/оружие), первая комната,
        и именно отсюда стартует музыка — по нажатию "играть"/рестарт, не раньше."""
        self.score = 0
        self.player = None
        self.run_timer_frames = 0
        self.load_room(first_room_id(), "default")
        self.start_music()

    def load_room(self, room_id, entry_side="default"):
        """Загружает комнату по id и ставит игрока в точку появления,
        соответствующую стороне, с которой он вошёл (entry_side)."""
        self.room_id = room_id
        self.room = build_room(room_id)

        self.platforms = self.room.platforms
        self.coins = self.room.coins
        self.enemies = self.room.enemies
        self.weapons = self.room.weapons
        self.flag = self.room.flag
        self.level_width = self.room.width

        # снаряды — не часть статических данных комнаты, а переходное боевое состояние;
        # при входе в любую комнату (в т.ч. повторном) начинаем с чистого листа
        self.projectiles = pygame.sprite.Group()

        spawn_x, spawn_y = self.room.get_spawn(entry_side)

        if self.player is None:
            self.player = Player(spawn_x, spawn_y)
        else:
            # телепортируем существующего игрока — HP, счёт и оружие сохраняются
            self.player.reset_position(spawn_x, spawn_y)

        self.apply_sfx_volume()  # новый Player создаёт свои Sound на полной громкости — подгоняем под настройку

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
        # Любое состояние, кроме паузы, должно звучать на обычной громкости —
        # восстанавливаем её здесь; PausedState сам приглушит музыку сразу после
        # вызова super().__init__() в своём конструкторе.
        try:
            pygame.mixer.music.set_volume(MUSIC_VOLUME_NORMAL * self.game.master_music_volume)
        except pygame.error:
            pass

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
        # В главном меню музыки быть не должно — глушим на случай возврата
        # сюда через M из паузы/победы/поражения
        self.game.stop_music()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.game.new_level()
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_o:
                self.game.change_state(SettingsState(self.game))
            elif event.key == pygame.K_l:
                self.game.change_state(LeaderboardState(self.game))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def update(self):
        self.time += 1

    def draw(self, screen):
        g = self.game
        draw_dark_background(screen, self.time, g.theme, g.spore_count)

        draw_text_centered(screen, "МЕГА-ПЛАТФОРМЕР", g.title_font, g.theme["accent"], HEIGHT // 2 - 100)
        draw_text_centered(screen, "Нажми ПРОБЕЛ или ENTER, чтобы начать", g.font, WHITE, HEIGHT // 2 + 10)
        draw_text_centered(screen, "Управление: A/D или стрелки — движение, SPACE/W — прыжок",
                            g.small_font, GRAY, HEIGHT // 2 + 60)
        draw_text_centered(screen, "Двойной прыжок в воздухе, SHIFT — рывок (дэш)",
                            g.small_font, GRAY, HEIGHT // 2 + 85)
        draw_text_centered(screen, "J/X — атака, вниз+J в воздухе — удар вниз",
                            g.small_font, GRAY, HEIGHT // 2 + 108)
        draw_text_centered(screen, "P/ESC — пауза, R — рестарт, ESC в меню — выход",
                            g.small_font, GRAY, HEIGHT // 2 + 131)
        draw_text_centered(screen, "O — настройки",
                            g.small_font, GRAY, HEIGHT // 2 + 154)
        draw_text_centered(screen, "L — лидерборд",
                            g.small_font, GRAY, HEIGHT // 2 + 177)


# ===========================================================
# СОСТОЯНИЕ: НАСТРОЙКИ (управление, графика, звук)
# ===========================================================
class SettingsState(State):
    """Экран настроек из главного меню. Навигация: W/S или стрелки вверх/вниз —
    выбор пункта, A/D или стрелки влево/вправо — изменение значения,
    ESC/M — вернуться в меню. Каждое изменение применяется мгновенно."""

    # количество пунктов, которые можно листать стрелками влево/вправо
    OPTION_COUNT = 5  # тема, качество эффектов, полный экран, музыка, эффекты

    def __init__(self, game):
        super().__init__(game)
        self.time = 0
        self.selected = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        g = self.game

        if event.key in (pygame.K_ESCAPE, pygame.K_m):
            g.change_state(MenuState(g))
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % self.OPTION_COUNT
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % self.OPTION_COUNT
        elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
            self._adjust(self.selected, direction)

    def _adjust(self, index, direction):
        g = self.game

        if index == 0:  # тема оформления
            g.theme_index = (g.theme_index + direction) % len(BG_THEMES)

        elif index == 1:  # качество эффектов
            levels = EFFECTS_QUALITY_LEVELS
            current = levels.index(g.effects_quality)
            g.effects_quality = levels[(current + direction) % len(levels)]

        elif index == 2:  # полноэкранный режим — переключатель, направление неважно
            g.fullscreen = not g.fullscreen
            g.apply_fullscreen()

        elif index == 3:  # громкость музыки
            g.master_music_volume = round(
                min(1.0, max(0.0, g.master_music_volume + direction * VOLUME_STEP)), 2
            )
            # применяем сразу же, если музыка сейчас звучит (например, если зашли
            # в настройки через паузу во время игры)
            try:
                current_bg_volume = MUSIC_VOLUME_PAUSED if isinstance(g.state, PausedState) else MUSIC_VOLUME_NORMAL
                pygame.mixer.music.set_volume(current_bg_volume * g.master_music_volume)
            except pygame.error:
                pass

        elif index == 4:  # громкость эффектов
            g.master_sfx_volume = round(
                min(1.0, max(0.0, g.master_sfx_volume + direction * VOLUME_STEP)), 2
            )
            g.apply_sfx_volume()

    def update(self):
        self.time += 1

    def draw(self, screen):
        g = self.game
        draw_dark_background(screen, self.time, g.theme, g.spore_count)

        draw_text_centered(screen, "НАСТРОЙКИ", g.big_font, g.theme["accent"], 70)

        rows = [
            ("Тема оформления", g.theme["name"]),
            ("Качество эффектов", EFFECTS_QUALITY_LABELS[g.effects_quality]),
            ("Полноэкранный режим", "Вкл" if g.fullscreen else "Выкл"),
            ("Громкость музыки", f"{int(g.master_music_volume * 100)}%"),
            ("Громкость эффектов", f"{int(g.master_sfx_volume * 100)}%"),
        ]

        start_y = 160
        row_height = 42
        for i, (label, value) in enumerate(rows):
            y = start_y + i * row_height
            is_selected = i == self.selected
            label_color = g.theme["accent"] if is_selected else WHITE
            marker = "> " if is_selected else "   "
            draw_text_centered(screen, f"{marker}{label}", g.font, label_color, y, x=WIDTH // 2 - 120)
            draw_text_centered(screen, f"< {value} >" if is_selected else value,
                                g.font, label_color, y, x=WIDTH // 2 + 220)

        # блок с управлением — просто справочная информация, не редактируется
        controls_y = start_y + len(rows) * row_height + 30
        draw_text_centered(screen, "Управление", g.font, GRAY, controls_y)
        draw_text_centered(screen, "A/D или стрелки — движение, SPACE/W — прыжок (двойной в воздухе)",
                            g.small_font, GRAY, controls_y + 28)
        draw_text_centered(screen, "SHIFT — дэш, J/X — атака, вниз+J в воздухе — удар вниз",
                            g.small_font, GRAY, controls_y + 50)
        draw_text_centered(screen, "P/ESC — пауза, R — рестарт",
                            g.small_font, GRAY, controls_y + 72)

        draw_text_centered(screen, "↑/↓ — выбор пункта, ←/→ — изменить значение, ESC/M — назад",
                            g.small_font, GRAY, HEIGHT - 30)


# ===========================================================
# СОСТОЯНИЕ: ЛИДЕРБОРД (статистика результатов, график, фильтр)
# ===========================================================
class LeaderboardState(State):
    """Отдельная вкладка со статистикой прохождений. Загружает записи из
    leaderboard.json один раз при входе (не каждый кадр — файл не меняется,
    пока сам игрок не пройдёт уровень заново). ←/→ переключает фильтр
    сортировки, ESC/M — назад в меню."""

    FILTERS = ["coins", "time"]
    FILTER_LABELS = {"coins": "По монетам", "time": "По скорости (быстрее — выше)"}

    def __init__(self, game):
        super().__init__(game)
        self.time = 0
        self.filter_index = 0
        self.records = leaderboard.load_leaderboard()

    @property
    def current_filter(self):
        return self.FILTERS[self.filter_index]

    def _sorted_records(self):
        if self.current_filter == "coins":
            return sorted(self.records, key=lambda r: r["coins"], reverse=True)
        else:  # "time" — быстрее время — выше в списке
            return sorted(self.records, key=lambda r: r["time"])

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_ESCAPE, pygame.K_m):
            self.game.change_state(MenuState(self.game))
        elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
            self.filter_index = (self.filter_index + direction) % len(self.FILTERS)

    def update(self):
        self.time += 1

    def draw(self, screen):
        g = self.game
        draw_dark_background(screen, self.time, g.theme, g.spore_count)

        draw_text_centered(screen, "ЛИДЕРБОРД", g.big_font, g.theme["accent"], 60)
        draw_text_centered(screen, f"Фильтр: < {self.FILTER_LABELS[self.current_filter]} >",
                            g.font, WHITE, 105)

        rows = self._sorted_records()[:LEADERBOARD_DISPLAY_COUNT]

        if not rows:
            draw_text_centered(screen, "Пока нет результатов — пройди игру до конца!",
                                g.font, GRAY, HEIGHT // 2)
        else:
            self._draw_bar_chart(screen, rows)

        draw_text_centered(screen, "←/→ — сменить фильтр, ESC/M — назад в меню",
                            g.small_font, GRAY, HEIGHT - 30)

    def _draw_bar_chart(self, screen, rows):
        """Горизонтальные бары — длина пропорциональна значению по текущему фильтру.
        Для монет — само число монет. Для скорости — обратная величина от времени
        (чем быстрее прошёл, тем длиннее бар), чтобы "лучше" визуально значило "больше"."""
        g = self.game

        if self.current_filter == "coins":
            values = [r["coins"] for r in rows]
        else:
            values = [1.0 / max(r["time"], 0.01) for r in rows]

        max_value = max(values) if max(values) > 0 else 1

        chart_x = 90
        chart_max_width = WIDTH - chart_x - 260
        bar_height = 24
        gap = 12
        start_y = 145

        for i, (record, value) in enumerate(zip(rows, values)):
            y = start_y + i * (bar_height + gap)
            bar_width = max(4, int(chart_max_width * (value / max_value)))

            # ранг слева
            rank_text = g.small_font.render(f"{i + 1}.", True, WHITE)
            screen.blit(rank_text, (chart_x - 70, y + 2))

            # сам бар
            bar_rect = pygame.Rect(chart_x, y, bar_width, bar_height)
            pygame.draw.rect(screen, g.theme["accent"], bar_rect, border_radius=4)
            pygame.draw.rect(screen, g.theme["mask_outline"], bar_rect, 2, border_radius=4)

            # подпись справа от бара: монеты + время + дата
            label = f"{record['coins']} монет  •  {format_time(record['time'])}  •  {record['date']}"
            label_surf = g.small_font.render(label, True, WHITE)
            screen.blit(label_surf, (chart_x + chart_max_width + 12, y + 3))


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
        g.run_timer_frames += 1
        g.player.update(g.platforms)
        # Особые враги (Jumper/Shooter/Flyer) реагируют на игрока и стреляют —
        # поэтому им нужен доступ к platforms/player/projectiles, а не только к себе.
        # Базовый Enemy эти параметры просто игнорирует.
        g.enemies.update(g.platforms, g.player, g.projectiles)
        g.coins.update()
        g.weapons.update()
        g.projectiles.update()

        collected = pygame.sprite.spritecollide(g.player, g.coins, dokill=True)
        g.score += len(collected)

        # --- подбор оружия ---
        picked_weapons = pygame.sprite.spritecollide(g.player, g.weapons, dokill=True)
        for weapon in picked_weapons:
            g.player.equip_weapon(weapon.weapon_id)

        current_damage = WEAPON_DAMAGE[g.player.weapon_id]

        # --- атаки наносят врагам урон текущим оружием (раньше, чем сработает
        # урон от простого касания) ---
        attack_rect = g.player.get_attack_rect()
        if attack_rect is not None:
            for enemy in list(g.enemies):
                # attack_hit_ids не даёт одному взмаху бить одного врага несколько
                # кадров подряд, пока активен хитбокс
                if attack_rect.colliderect(enemy.rect) and id(enemy) not in g.player.attack_hit_ids:
                    g.player.attack_hit_ids.add(id(enemy))
                    enemy.take_damage(current_damage)

        down_attack_rect = g.player.get_down_attack_rect()
        if down_attack_rect is not None:
            hit_someone = False
            for enemy in list(g.enemies):
                if down_attack_rect.colliderect(enemy.rect):
                    enemy.take_damage(current_damage)
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
                        # запрыгнули врагу на голову — мгновенная смерть врага, урон не наносится игроку
                        enemy.kill()
                        g.player.vel_y = JUMP_STRENGTH / 1.5
                    else:
                        knockback_dir = -1 if g.player.rect.centerx < enemy.rect.centerx else 1
                        g.player.take_damage(ENEMY_CONTACT_DAMAGE, knockback_dir)

            # --- снаряды шутеров тоже наносят урон ---
            projectile_hits = pygame.sprite.spritecollide(g.player, g.projectiles, dokill=True)
            if projectile_hits:
                hit = projectile_hits[0]
                g.player.take_damage(PROJECTILE_DAMAGE, hit.direction)

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
        self.game.run_timer_frames += 1

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
    def __init__(self, game):
        super().__init__(game)
        # super().__init__ уже выставил обычную громкость — сразу приглушаем поверх неё
        try:
            pygame.mixer.music.set_volume(MUSIC_VOLUME_PAUSED * self.game.master_music_volume)
        except pygame.error:
            pass

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
    def __init__(self, game):
        super().__init__(game)
        # Победа — сохраняем результат в лидерборд один раз, сразу при входе в это состояние
        self.elapsed_seconds = game.run_timer_frames / FPS
        leaderboard.add_result(game.score, self.elapsed_seconds)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.game.new_level()
                self.game.change_state(PlayingState(self.game))
            elif event.key == pygame.K_m:
                self.game.change_state(MenuState(self.game))
            elif event.key == pygame.K_l:
                self.game.change_state(LeaderboardState(self.game))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def draw(self, screen):
        g = self.game
        draw_world(g, screen)
        draw_overlay(screen)
        draw_text_centered(screen, "Победа! Уровень пройден!", g.big_font, YELLOW, HEIGHT // 2 - 30)
        draw_text_centered(screen, f"Собрано монет: {g.score}  •  Время: {format_time(self.elapsed_seconds)}",
                            g.font, WHITE, HEIGHT // 2 + 20)
        draw_text_centered(screen, "R — рестарт  •  M — меню  •  L — лидерборд", g.font, WHITE, HEIGHT // 2 + 60)


# ===========================================================
# СОСТОЯНИЕ: ПОРАЖЕНИЕ
# ===========================================================
class LostState(State):
    def __init__(self, game):
        super().__init__(game)
        # Музыка полностью замолкает на гейм-овере (не просто тише, как на паузе) —
        # играть заново начнёт только после рестарта, из new_level()
        self.game.stop_music()
        if self.game.gameover_sound is not None:
            self.game.gameover_sound.play()

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


def format_time(seconds):
    """Форматирует секунды как MM:SS.ss — используется в HUD, на экране победы
    и в списке лидерборда, чтобы формат времени был одинаковым везде."""
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes:02d}:{secs:05.2f}"


def draw_text_centered(screen, text, font, color, y, x=WIDTH // 2):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(x, y))
    screen.blit(surf, rect)
    return rect


def draw_dark_background(screen, time_counter, theme, spore_count=14):
    """Тёмный фон с медленно плывущими 'спорами' — атмосфера в духе Hollow Knight.
    Используется как fallback, пока для комнаты не задана кастомная картинка.
    theme — словарь из BG_THEMES (выбирается в настройках), spore_count — сколько
    частиц рисовать (регулируется настройкой "Качество эффектов")."""
    screen.fill(theme["dark_bg"])

    for i in range(3):
        bx = (i * 340 + int(time_counter * 0.15)) % (WIDTH + 300) - 150
        by = HEIGHT - 80 - (i % 2) * 40
        pygame.draw.ellipse(screen, theme["dark_bg_mid"], (bx, by, 260, 160))

    for i in range(spore_count):
        px = (i * 97 + int(time_counter * (0.4 + (i % 3) * 0.2))) % (WIDTH + 40) - 20
        py = (i * 53) % HEIGHT
        radius = 2 + (i % 3)
        spore_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(spore_surf, (*theme["fog_color"], 90), (radius, radius), radius)
        screen.blit(spore_surf, (px, py))


def draw_background_image(screen, image):
    screen.blit(image, (0, 0))


def draw_hp_bar(screen, player, theme):
    """Полоски здоровья в виде 'масок' — как жизни рыцаря в Hollow Knight.
    Цвета берутся из текущей темы оформления (настройки графики)."""
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
        color = theme["mask_full"] if i < player.hp else theme["mask_empty"]
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, theme["mask_outline"], points, 2)


def draw_weapon_icon(screen, game):
    """Иконка текущего оружия — сразу справа от полосок здоровья."""
    icon = game.weapon_icons.get(game.player.weapon_id)
    if icon is None:
        return

    mask_size = 22
    gap = 8
    x0, y0 = 20, 50
    hp_row_width = game.player.max_hp * (mask_size + gap)

    x = x0 + hp_row_width + 12
    y = y0 - 3
    screen.blit(icon, (x, y))


def draw_world(game: Game, screen):
    bg_image = game.backgrounds_dict.get(game.room_id)
    if bg_image is not None:
        draw_background_image(screen, bg_image)
    else:
        draw_dark_background(screen, pygame.time.get_ticks() // 16, game.theme, game.spore_count)

    cam = game.camera_x

    for plat in game.platforms:
        screen.blit(plat.image, plat.rect.move(-cam, 0))

    for coin in game.coins:
        screen.blit(coin.image, coin.rect.move(-cam, 0))

    for weapon in game.weapons:
        screen.blit(weapon.image, weapon.rect.move(-cam, 0))

    for enemy in game.enemies:
        screen.blit(enemy.image, enemy.rect.move(-cam, 0))

    for projectile in game.projectiles:
        screen.blit(projectile.image, projectile.rect.move(-cam, 0))

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
    draw_hp_bar(screen, game.player, game.theme)
    draw_weapon_icon(screen, game)

    timer_text = game.font.render(format_time(game.run_timer_frames / FPS), True, WHITE)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 16, 12))