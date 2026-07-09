import pygame
import math
import sys
from collections import deque
from settings import *

from sprites.player import Player
from sprites.arrow import Arrow
from sprites.boss import BossEnemy
from rooms import build_room, first_room_id
from weapon_recognition import WeaponRecognizer
import leaderboard


def _load_bridge_background():
    """Фон комнаты "bridge" — слегка прозрачный (alpha чуть меньше 255),
    чтобы сквозь него немного проглядывал тёмный фон позади (см.
    draw_background_image) и картинка не выглядела совсем "плоской"."""
    image = pygame.image.load("images/backgrounds/bridge.png").convert_alpha()
    image.set_alpha(100)
    return image


class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Draw and attack!")
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
        self.player_arrows = None  # стрелы, выпущенные игроком из лука — тоже не часть комнаты
        self.run_timer_frames = 0  # сколько кадров прошло с начала текущего прохождения (для лидерборда)
        self.boss = None          # BossEnemy текущей комнаты, если это BOSS_ROOM_ID (для хелсбара/победы)

        # --- секретная комбинация клавиш для мгновенной телепортации к боссу (тесты) ---
        self._secret_key_buffer = deque(maxlen=len(SECRET_BOSS_KEY_SEQUENCE))

        # --- кастомные фоны комнат: room_id -> Surface ---
        # .get() при отрисовке подстрахует комнаты, для которых картинки ещё нет —
        # тогда просто используется процедурный тёмный фон
        self.backgrounds_dict = {
            "forest": pygame.image.load("images/backgrounds/forest.png").convert(),
            #"caves": pygame.image.load("images/backgrounds/caves.png").convert(),
            "bridge": _load_bridge_background(),
            #"vault": pygame.image.load("images/backgrounds/vault.png").convert(),
            #"meadow": pygame.image.load("images/backgrounds/meadow.png").convert(),
            #"orchard": pygame.image.load("images/backgrounds/orchard.png").convert(),
            #"sky": pygame.image.load("images/backgrounds/sky.png").convert(),
            #"summit": pygame.image.load("images/backgrounds/summit.png").convert(),
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

        # --- уровень сложности (выбирается в меню перед первым стартом, см.
        # DifficultySelectState) — сохраняется между рестартами (R), пока игрок
        # не вернётся в главное меню и не выберет заново ---
        self.difficulty = "normal"

        # --- распознавание оружия по рисунку (см. weapon_recognition.py) ---
        self.weapon_recognizer = WeaponRecognizer()
        self.drawing_mode = False                # True, пока зажата DRAW_WEAPON_KEY
        self.draw_canvas = pygame.Surface((DRAW_CANVAS_SIZE, DRAW_CANVAS_SIZE))
        self.draw_canvas.fill(WHITE)
        self.draw_last_pos = None                 # предыдущая точка мыши для рисования линии
        self.draw_slowmo_counter = 0              # счётчик кадров для эффекта замедления
        self.draw_result_text = ""                # что показать после распознавания ("Топор!" и т.п.)
        self.draw_result_timer = 0
        self.draw_cooldown_timer = 0              # пока > 0, рисовать снова нельзя (см. DRAW_COOLDOWN_FRAMES)

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
        """Переключает окно между обычным и полноэкранным режимом.
        В полноэкранном режиме используем флаг SCALED — иначе SDL пытается
        сменить реальное разрешение экрана на фиксированные WIDTH x HEIGHT,
        из-за чего изображение на мониторах с другим разрешением выходит
        растянутым/съехавшим. SCALED вместо этого рендерит в неизменном
        логическом разрешении и аккуратно масштабирует картинку под
        реальный экран, сохраняя пропорции (с чёрными полосами по краям)."""
        if self.fullscreen:
            flags = pygame.FULLSCREEN | pygame.SCALED
        else:
            flags = 0
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

    # --- рисование оружия (DRAW_WEAPON_KEY, см. weapon_recognition.py) ---
    def start_weapon_drawing(self):
        """Открывает холст — вызывается по нажатию DRAW_WEAPON_KEY."""
        self.drawing_mode = True
        self.draw_canvas.fill(WHITE)
        self.draw_last_pos = None
        self.draw_slowmo_counter = 0
        self.draw_result_text = ""
        self.draw_result_timer = 0

    def weapon_draw_line(self, screen_from, screen_to):
        """Рисует отрезок на холсте по координатам мыши в системе экрана —
        сама переводит их в локальные координаты холста и обрезает по его границам."""
        canvas_rect = self.get_draw_canvas_rect()
        local_from = (screen_from[0] - canvas_rect.left, screen_from[1] - canvas_rect.top)
        local_to = (screen_to[0] - canvas_rect.left, screen_to[1] - canvas_rect.top)
        pygame.draw.line(self.draw_canvas, BLACK, local_from, local_to, DRAW_BRUSH_SIZE)
        pygame.draw.circle(self.draw_canvas, BLACK, local_to, DRAW_BRUSH_SIZE // 2)

    def get_draw_canvas_rect(self):
        """Прямоугольник холста по центру экрана — общий для рисования и отрисовки."""
        return pygame.Rect(
            (WIDTH - DRAW_CANVAS_SIZE) // 2, (HEIGHT - DRAW_CANVAS_SIZE) // 2,
            DRAW_CANVAS_SIZE, DRAW_CANVAS_SIZE,
        )

    def finish_weapon_drawing(self):
        """Закрывает холст — вызывается по отпусканию DRAW_WEAPON_KEY. Холст
        убирается с экрана сразу же; распознанное оружие показывается крупной
        надписью вверху экрана (см. draw_weapon_result_banner), которая тоже
        гаснет сама по себе через DRAW_RESULT_MESSAGE_FRAMES кадров. После
        закрытия холста начинается кулдаун (DRAW_COOLDOWN_FRAMES) — рисовать
        снова можно только когда он истечёт."""
        self.drawing_mode = False
        self.draw_last_pos = None

        weapon_id, confidence = self.weapon_recognizer.predict(self.draw_canvas)
        if weapon_id is not None and confidence >= WEAPON_RECOGNITION_MIN_CONFIDENCE and self.player is not None:
            self.player.equip_weapon(weapon_id, confidence)
            names = {"sword": "Меч!", "axe": "Топор!", "bow": "Лук!"}
            weapon_name = names.get(weapon_id, weapon_id)
            self.draw_result_text = f"{weapon_name} ({confidence * 100:.0f}%)"
        elif weapon_id is not None:
            # Модель что-то распознала, но недостаточно уверенно — оружие
            # оставляем прежним, но со сниженным до 50% уроном.
            if self.player is not None:
                self.player.weapon_confidence = WEAPON_RECOGNITION_DEFAULT_CONFIDENCE
            self.draw_result_text = "Оружие не распознано"
        elif not self.weapon_recognizer.available:
            self.draw_result_text = "Модель распознавания недоступна"
        else:
            self.draw_result_text = "Не удалось распознать оружие"
        self.draw_result_timer = DRAW_RESULT_MESSAGE_FRAMES
        self.draw_cooldown_timer = DRAW_COOLDOWN_FRAMES

    def change_state(self, new_state):
        """Запрашивает смену состояния — произойдёт в начале следующего кадра."""
        self.next_state = new_state

    def check_secret_boss_sequence(self, key):
        """Копит последние нажатые клавиши и сравнивает с SECRET_BOSS_KEY_SEQUENCE
        (набрать подряд B-O-S-S) — секретная комбинация для мгновенной
        телепортации в комнату босса, чтобы не проходить всю игру заново
        при каждом тесте боя."""
        self._secret_key_buffer.append(key)
        if list(self._secret_key_buffer) == SECRET_BOSS_KEY_SEQUENCE:
            self.teleport_to_boss()

    def teleport_to_boss(self):
        """Мгновенно переносит игрока в комнату босса — создаёт нового игрока
        (если игра ещё не начиналась, например вызвано из главного меню) и
        переключает состояние на PlayingState."""
        if self.player is None:
            self.new_level()
        self.load_room(BOSS_ROOM_ID, "default")
        self.change_state(PlayingState(self))

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
        self.room = build_room(room_id, self.difficulty)

        self.platforms = self.room.platforms
        self.coins = self.room.coins
        self.enemies = self.room.enemies
        self.weapons = self.room.weapons
        self.flag = self.room.flag
        self.level_width = self.room.width

        # Ищем босса среди врагов комнаты (обычно есть только в BOSS_ROOM_ID) —
        # нужна отдельная ссылка для всегда видимого хелсбара и проверки победы
        self.boss = next((e for e in self.enemies if isinstance(e, BossEnemy)), None)

        # снаряды — не часть статических данных комнаты, а переходное боевое состояние;
        # при входе в любую комнату (в т.ч. повторном) начинаем с чистого листа
        self.projectiles = pygame.sprite.Group()
        self.player_arrows = pygame.sprite.Group()

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
                elif event.type == pygame.KEYDOWN:
                    self.check_secret_boss_sequence(event.key)
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
    # (внутреннее имя действия, подпись на кнопке, подсказка с клавишей)
    BUTTONS = [
        ("play", "ИГРАТЬ", "SPACE / ENTER"),
        ("settings", "НАСТРОЙКИ", "O"),
        ("leaderboard", "ЛИДЕРБОРД", "L"),
        ("quit", "ВЫХОД", "ESC"),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.time = 0
        # В главном меню музыки быть не должно — глушим на случай возврата
        # сюда через M из паузы/победы/поражения
        self.game.stop_music()
        self.hovered_action = None
        self.buttons = self._build_buttons()

    def _build_buttons(self):
        """Считает прямоугольники кнопок один раз — ими пользуются и клик мышью
        (handle_event), и отрисовка (draw), чтобы позиции не могли разъехаться."""
        button_width, button_height = 460, 46
        gap = 14
        start_y = 180
        buttons = []
        for i, (action, label, hint) in enumerate(self.BUTTONS):
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.center = (WIDTH // 2, start_y + i * (button_height + gap))
            buttons.append({"action": action, "label": label, "hint": hint, "rect": rect})
        return buttons

    def _activate(self, action):
        """Общая точка входа что для клавиатуры, что для клика мышью по кнопке —
        чтобы оба способа управления гарантированно вели к одному и тому же."""
        g = self.game
        if action == "play":
            g.change_state(DifficultySelectState(g))
        elif action == "settings":
            g.change_state(SettingsState(g))
        elif action == "leaderboard":
            g.change_state(LeaderboardState(g))
        elif action == "quit":
            g.running = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._activate("play")
            elif event.key == pygame.K_o:
                self._activate("settings")
            elif event.key == pygame.K_l:
                self._activate("leaderboard")
            elif event.key == pygame.K_ESCAPE:
                self._activate("quit")
        elif event.type == pygame.MOUSEMOTION:
            self.hovered_action = next(
                (b["action"] for b in self.buttons if b["rect"].collidepoint(event.pos)), None
            )
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button["rect"].collidepoint(event.pos):
                    self._activate(button["action"])
                    break

    def update(self):
        self.time += 1

    def draw(self, screen):
        g = self.game
        draw_dark_background(screen, self.time, g.theme, g.spore_count)

        draw_text_centered(screen, "Draw and attack!", g.title_font, g.theme["accent"], 80)

        for button in self.buttons:
            is_hovered = button["action"] == self.hovered_action
            bg_color = g.theme["accent"] if is_hovered else (40, 40, 50)
            text_color = BLACK if is_hovered else WHITE
            pygame.draw.rect(screen, bg_color, button["rect"], border_radius=8)
            pygame.draw.rect(screen, g.theme["accent"], button["rect"], width=2, border_radius=8)

            label_surf = g.font.render(f"{button['label']}  ({button['hint']})", True, text_color)
            label_rect = label_surf.get_rect(center=button["rect"].center)
            screen.blit(label_surf, label_rect)

        draw_text_centered(screen, "Мышью — клик по кнопке, либо клавишами (см. подсказки на кнопках)",
                            g.small_font, GRAY, HEIGHT - 92)
        draw_text_centered(screen, "Управление: A/D или стрелки — движение, SPACE/W — прыжок",
                            g.small_font, GRAY, HEIGHT - 68)
        draw_text_centered(screen, "Двойной прыжок, SHIFT — рывок, J/X — атака, P/ESC в игре — пауза",
                            g.small_font, GRAY, HEIGHT - 44)


# ===========================================================
# СОСТОЯНИЕ: ВЫБОР СЛОЖНОСТИ (перед первым стартом из меню)
# ===========================================================
class DifficultySelectState(State):
    """Экран выбора сложности — показывается один раз, после главного меню,
    перед самым первым стартом уровня. Влияет на game.difficulty, а через него —
    на количество врагов и параметр в spawn-формуле особых врагов (см.
    DIFFICULTY_* в settings.py и sprites/enemy_factory.spawn_enemy_group).
    ←/→ или ↑/↓ — выбор, ПРОБЕЛ/ENTER — подтвердить и начать игру, ESC — назад в меню."""

    def __init__(self, game):
        super().__init__(game)
        self.time = 0
        # начинаем выбор с текущей сложности игры (по умолчанию "normal")
        self.index = DIFFICULTY_LEVELS.index(self.game.difficulty) if self.game.difficulty in DIFFICULTY_LEVELS else 1

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.game.change_state(MenuState(self.game))
        elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            self.index = (self.index - 1) % len(DIFFICULTY_LEVELS)
        elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + 1) % len(DIFFICULTY_LEVELS)
        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.game.difficulty = DIFFICULTY_LEVELS[self.index]
            self.game.new_level()
            self.game.change_state(PlayingState(self.game))

    def update(self):
        self.time += 1

    def draw(self, screen):
        g = self.game
        draw_dark_background(screen, self.time, g.theme, g.spore_count)

        draw_text_centered(screen, "ВЫБОР СЛОЖНОСТИ", g.big_font, g.theme["accent"], 90)

        option_y = HEIGHT // 2 - 40
        option_gap = 70
        for i, level in enumerate(DIFFICULTY_LEVELS):
            y = option_y + i * option_gap
            is_selected = (i == self.index)
            color = g.theme["accent"] if is_selected else WHITE
            marker = "> " if is_selected else "   "
            draw_text_centered(screen, f"{marker}{DIFFICULTY_LABELS[level]}", g.font, color, y)

        desc = DIFFICULTY_DESCRIPTIONS[DIFFICULTY_LEVELS[self.index]]
        draw_text_centered(screen, desc, g.small_font, GRAY, option_y + len(DIFFICULTY_LEVELS) * option_gap + 20)

        draw_text_centered(
            screen,
            "←/→ или ↑/↓ — выбрать сложность  •  ПРОБЕЛ/ENTER — начать  •  ESC — назад",
            g.small_font, GRAY, HEIGHT - 30,
        )


# ===========================================================
# СОСТОЯНИЕ: НАСТРОЙКИ (управление, графика, звук)
# ===========================================================
class SettingsState(State):
    """Экран настроек из главного меню. Навигация: W/S или стрелки вверх/вниз —
    выбор пункта, A/D или стрелки влево/вправо — изменение значения,
    ESC/M — вернуться в меню. Те же действия доступны мышью: клик по стрелкам
    "<"/">" у значения меняет его, клик по строке просто выделяет её.
    Каждое изменение применяется мгновенно."""

    # количество пунктов, которые можно листать стрелками влево/вправо
    OPTION_COUNT = 5  # тема, качество эффектов, полный экран, музыка, эффекты

    START_Y = 160
    ROW_HEIGHT = 42
    LABEL_X = 150     # левый край подписи пункта
    VALUE_X = 710     # центр текста значения — стрелки </> считаются от его краёв

    def __init__(self, game):
        super().__init__(game)
        self.time = 0
        self.selected = 0
        self.rows = self._build_rows()

    def _build_rows(self):
        """Прямоугольники строк и стрелок "<"/">". row_rect (клик по строке —
        просто выделяет её) фиксирован, а left_rect/right_rect уточняются в
        draw() по фактической ширине текста значения (у разных пунктов оно
        разной длины), чтобы стрелки никогда не наезжали на текст."""
        rows = []
        for i in range(self.OPTION_COUNT):
            y = self.START_Y + i * self.ROW_HEIGHT
            row_rect = pygame.Rect(0, 0, 760, 36)
            row_rect.center = (WIDTH // 2, y)
            rows.append({
                "row_rect": row_rect,
                "left_rect": pygame.Rect(0, 0, 30, 30),
                "right_rect": pygame.Rect(0, 0, 30, 30),
            })
        return rows

    def handle_event(self, event):
        g = self.game

        if event.type == pygame.KEYDOWN:
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

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, row in enumerate(self.rows):
                if row["left_rect"].collidepoint(event.pos):
                    self.selected = i
                    self._adjust(i, -1)
                    break
                elif row["right_rect"].collidepoint(event.pos):
                    self.selected = i
                    self._adjust(i, 1)
                    break
                elif row["row_rect"].collidepoint(event.pos):
                    self.selected = i
                    break

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

        values = [
            g.theme["name"],
            EFFECTS_QUALITY_LABELS[g.effects_quality],
            "Вкл" if g.fullscreen else "Выкл",
            f"{int(g.master_music_volume * 100)}%",
            f"{int(g.master_sfx_volume * 100)}%",
        ]
        labels = [
            "Тема оформления",
            "Качество эффектов",
            "Полноэкранный режим",
            "Громкость музыки",
            "Громкость эффектов",
        ]

        mouse_pos = pygame.mouse.get_pos()

        for i, (label, value) in enumerate(zip(labels, values)):
            y = self.START_Y + i * self.ROW_HEIGHT
            row = self.rows[i]
            is_selected = i == self.selected
            label_color = g.theme["accent"] if is_selected else WHITE
            marker = "> " if is_selected else "   "

            label_surf = g.font.render(f"{marker}{label}", True, label_color)
            label_rect = label_surf.get_rect(midleft=(self.LABEL_X, y))
            screen.blit(label_surf, label_rect)

            value_surf = g.font.render(value, True, label_color)
            value_rect = value_surf.get_rect(center=(self.VALUE_X, y))
            screen.blit(value_surf, value_rect)

            # стрелки "<"/">" всегда кликабельны, ставим их сразу за краями текста
            # значения — так они никогда не наезжают на сам текст независимо от
            # его длины (у темы оформления она заметно больше, чем у "Вкл"/"Выкл")
            row["left_rect"].center = (value_rect.left - 25, y)
            row["right_rect"].center = (value_rect.right + 25, y)

            for arrow_rect, glyph in ((row["left_rect"], "<"), (row["right_rect"], ">")):
                is_hovered = arrow_rect.collidepoint(mouse_pos)
                arrow_color = g.theme["accent"] if (is_hovered or is_selected) else GRAY
                arrow_surf = g.font.render(glyph, True, arrow_color)
                arrow_text_rect = arrow_surf.get_rect(center=arrow_rect.center)
                screen.blit(arrow_surf, arrow_text_rect)

        # блок с управлением — просто справочная информация, не редактируется
        controls_y = self.START_Y + len(labels) * self.ROW_HEIGHT + 30
        draw_text_centered(screen, "Управление", g.font, GRAY, controls_y)
        draw_text_centered(screen, "A/D или стрелки — движение, SPACE/W — прыжок (двойной в воздухе)",
                            g.small_font, GRAY, controls_y + 28)
        draw_text_centered(screen, "SHIFT — дэш, J/X — атака, вниз+J в воздухе — удар вниз",
                            g.small_font, GRAY, controls_y + 50)
        draw_text_centered(screen, "P/ESC — пауза, R — рестарт",
                            g.small_font, GRAY, controls_y + 72)

        draw_text_centered(
            screen,
            "↑/↓ или клик по строке — выбор, ←/→ или клик по стрелкам < > — изменить значение, ESC/M — назад",
            g.small_font, GRAY, HEIGHT - 30,
        )


# ===========================================================
# СОСТОЯНИЕ: ЛИДЕРБОРД (статистика результатов, график, фильтр)
# ===========================================================
class LeaderboardState(State):
    """Отдельная вкладка со статистикой прохождений. Загружает записи из
    leaderboard.json один раз при входе (не каждый кадр — файл не меняется,
    пока сам игрок не пройдёт уровень заново, либо не удалит запись отсюда же).
    ←/→ переключает фильтр сортировки, ↑/↓ выбирает строку, DELETE/X удаляет
    выбранного старого лидера, ESC/M — назад в меню."""

    FILTERS = ["coins", "time"]
    FILTER_LABELS = {"coins": "По монетам", "time": "По скорости (быстрее — выше)"}

    def __init__(self, game):
        super().__init__(game)
        self.time = 0
        self.filter_index = 0
        self.records = leaderboard.load_leaderboard()
        self.selected_index = None  # ничего не выделено, пока игрок сам не нажмёт ↑/↓ —
                                     # раньше тут стоял 0, из-за чего 1-е место подсвечивалось само собой

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

        rows = self._sorted_records()[:LEADERBOARD_DISPLAY_COUNT]

        if event.key in (pygame.K_ESCAPE, pygame.K_m):
            self.game.change_state(MenuState(self.game))
        elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
            self.filter_index = (self.filter_index + direction) % len(self.FILTERS)
            self.selected_index = None
        elif event.key in (pygame.K_UP, pygame.K_w) and rows:
            self.selected_index = (
                len(rows) - 1 if self.selected_index is None else (self.selected_index - 1) % len(rows)
            )
        elif event.key in (pygame.K_DOWN, pygame.K_s) and rows:
            self.selected_index = (
                0 if self.selected_index is None else (self.selected_index + 1) % len(rows)
            )
        elif event.key in (pygame.K_DELETE, pygame.K_x) and rows and self.selected_index is not None:
            # Удаляем именно тот результат (старого лидера), что сейчас выделен,
            # а не по индексу в другом порядке сортировки
            record_to_remove = rows[self.selected_index]
            leaderboard.remove_result(self.records, record_to_remove)
            self.records = leaderboard.load_leaderboard()
            self.selected_index = max(0, min(self.selected_index, len(self.records) - 1)) if self.records else None

    def update(self):
        self.time += 1

    def draw(self, screen):
        g = self.game
        draw_dark_background(screen, self.time, g.theme, g.spore_count)

        draw_text_centered(screen, "ЛИДЕРБОРД", g.big_font, g.theme["accent"], 45)
        draw_text_centered(screen, f"Фильтр: < {self.FILTER_LABELS[self.current_filter]} >",
                            g.font, WHITE, 85)

        rows = self._sorted_records()[:LEADERBOARD_DISPLAY_COUNT]
        if self.selected_index is not None:
            self.selected_index = max(0, min(self.selected_index, len(rows) - 1)) if rows else None

        if not rows:
            draw_text_centered(screen, "Пока нет результатов — пройди игру до конца!",
                                g.font, GRAY, HEIGHT // 2)
        else:
            self._draw_rows(screen, rows)

        draw_text_centered(
            screen,
            "←/→ — фильтр  •  ↑/↓ — выбрать  •  DEL/X — удалить  •  ESC/M — в меню",
            g.small_font, GRAY, HEIGHT - 24,
        )

    def _draw_rows(self, screen, rows):
        """Список результатов в две строки на каждую запись — так помещается вся
        информация (ник, монеты, время, дата) без обрезания за край экрана."""
        g = self.game

        if self.current_filter == "coins":
            values = [r["coins"] for r in rows]
        else:
            values = [1.0 / max(r["time"], 0.01) for r in rows]
        max_value = max(values) if max(values) > 0 else 1

        chart_x = 56
        chart_max_width = 220
        row_height = 46
        start_y = 118

        for i, (record, value) in enumerate(zip(rows, values)):
            y = start_y + i * row_height
            is_selected = (self.selected_index is not None and i == self.selected_index)

            if is_selected:
                highlight_rect = pygame.Rect(16, y - 4, WIDTH - 32, row_height - 6)
                pygame.draw.rect(screen, (*g.theme["accent"], 40), highlight_rect, border_radius=6)
                pygame.draw.rect(screen, g.theme["accent"], highlight_rect, 2, border_radius=6)

            # ранг слева
            rank_text = g.small_font.render(f"{i + 1}.", True, WHITE)
            screen.blit(rank_text, (chart_x - 40, y))

            # бар — короткий, просто индикатор относительно других строк
            bar_width = max(4, int(chart_max_width * (value / max_value)))
            bar_rect = pygame.Rect(chart_x, y + 2, bar_width, 14)
            pygame.draw.rect(screen, g.theme["accent"], bar_rect, border_radius=4)
            pygame.draw.rect(screen, g.theme["mask_outline"], bar_rect, 1, border_radius=4)

            # строка 1: ник (жирным по смыслу — крупным шрифтом)
            name = record.get("name", LEADERBOARD_DEFAULT_NAME)
            name_surf = g.font.render(name, True, WHITE if not is_selected else g.theme["accent"])
            screen.blit(name_surf, (chart_x + chart_max_width + 16, y - 6))

            # строка 2: монеты + время + дата — мелким шрифтом, под ником
            details = f"{record['coins']} монет  •  {format_time(record['time'])}  •  {record['date']}"
            details_surf = g.small_font.render(details, True, GRAY)
            screen.blit(details_surf, (chart_x, y + 20))


# ===========================================================
# СОСТОЯНИЕ: ИГРОВОЙ ПРОЦЕСС
# ===========================================================
class PlayingState(State):
    def handle_event(self, event):
        g = self.game
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p) and not g.drawing_mode:
                # Паузу нельзя открыть посреди рисования — иначе холст
                # останется "подвешен", а KEYUP DRAW_WEAPON_KEY придёт уже
                # в PausedState и не закроет его как надо.
                self.game.change_state(PausedState(self.game))
            elif event.key == DRAW_WEAPON_KEY and not g.drawing_mode and g.draw_cooldown_timer <= 0:
                g.start_weapon_drawing()
        elif event.type == pygame.KEYUP:
            if event.key == DRAW_WEAPON_KEY and g.drawing_mode:
                g.finish_weapon_drawing()
        elif event.type == pygame.MOUSEMOTION and g.drawing_mode:
            # event.buttons[0] — зажата ли левая кнопка мыши прямо во время движения
            if event.buttons[0]:
                start = g.draw_last_pos if g.draw_last_pos is not None else event.pos
                g.weapon_draw_line(start, event.pos)
            g.draw_last_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and g.drawing_mode and event.button == 1:
            g.draw_last_pos = event.pos
            g.weapon_draw_line(event.pos, event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            g.draw_last_pos = None

    def update(self):
        g = self.game

        # --- надпись с результатом распознавания угасает сама по себе ---
        if g.draw_result_timer > 0:
            g.draw_result_timer -= 1

        # --- кулдаун на повторное рисование тоже тикает независимо от слоумо ---
        if g.draw_cooldown_timer > 0:
            g.draw_cooldown_timer -= 1

        if g.drawing_mode:
            # Пока открыт холст, игровой процесс не стоит на месте совсем,
            # а сильно замедляется — обычная логика тикает лишь раз в
            # DRAW_SLOWMO_DIVISOR кадров, остальное время экран просто "подвисает"
            # под затемнением, пока игрок рисует.
            g.draw_slowmo_counter += 1
            if g.draw_slowmo_counter % DRAW_SLOWMO_DIVISOR != 0:
                return

        self._tick_gameplay()

    def _tick_gameplay(self):
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
        g.player_arrows.update()

        # --- выстрел из лука: Player лишь просит выстрелить (arrow_requested),
        # саму стрелу создаём здесь, где есть доступ к группе снарядов игрока ---
        if g.player.arrow_requested:
            x, y, direction = g.player.get_arrow_spawn()
            arrow_damage = g.player.get_current_damage()
            g.player_arrows.add(Arrow(x, y, direction, arrow_damage))

        collected = pygame.sprite.spritecollide(g.player, g.coins, dokill=True)
        g.score += len(collected)

        # --- подбор оружия (на случай, если в комнатах ещё лежат предметы) ---
        picked_weapons = pygame.sprite.spritecollide(g.player, g.weapons, dokill=True)
        for weapon in picked_weapons:
            g.player.equip_weapon(weapon.weapon_id)

        current_damage = g.player.get_current_damage()

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

        # --- стрелы лука наносят урон первому врагу, в которого попадут ---
        for arrow in list(g.player_arrows):
            hit_enemy = pygame.sprite.spritecollideany(arrow, g.enemies)
            if hit_enemy is not None:
                hit_enemy.take_damage(arrow.damage)
                arrow.kill()

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
                        # запрыгнули врагу на голову — просто отскакиваем, враг остаётся жив
                        # (урон касанием игроку тоже не наносится, но и враг больше не умирает мгновенно)
                        g.player.vel_y = JUMP_STRENGTH / 1.5
                    else:
                        knockback_dir = -1 if g.player.rect.centerx < enemy.rect.centerx else 1
                        g.player.take_damage(ENEMY_CONTACT_DAMAGE, knockback_dir)

            # --- снаряды шутеров тоже наносят урон ---
            projectile_hits = pygame.sprite.spritecollide(g.player, g.projectiles, dokill=True)
            if projectile_hits:
                hit = projectile_hits[0]
                g.player.take_damage(PROJECTILE_DAMAGE, hit.direction)

            # --- зона урона "удара оземь" босса (danger_rect) — сама не входит
            # в enemies, поэтому обычная проверка касания её не ловит ---
            if g.boss is not None and g.boss.danger_rect is not None:
                if g.player.rect.colliderect(g.boss.danger_rect):
                    knockback_dir = -1 if g.player.rect.centerx < g.boss.rect.centerx else 1
                    g.player.take_damage(BOSS_SLAM_DAMAGE, knockback_dir)

        if not g.player.alive:
            g.change_state(LostState(g))
            return

        # --- победа над боссом сразу завершает игру — флага в его комнате нет ---
        if g.boss is not None and g.boss.hp <= 0:
            g.change_state(WonState(g))
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
        if self.game.boss is not None and self.game.boss.hp > 0:
            draw_boss_health_bar(screen, self.game)
        if self.game.drawing_mode:
            draw_weapon_canvas_overlay(self.game, screen)
        elif self.game.draw_result_timer > 0:
            draw_weapon_result_banner(self.game, screen)


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
        # Победа — решаем сразу, попадает ли результат в лидерборд. Если да —
        # сначала просим ввести ник и только потом сохраняем результат.
        self.elapsed_seconds = game.run_timer_frames / FPS
        self.qualifies = leaderboard.will_qualify(game.score)
        self.entering_name = self.qualifies
        self.name_input = ""
        self.cursor_timer = 0

        if not self.qualifies:
            # Результат всё равно сохраняется, просто без ника (не попал в топ) —
            # чтобы статистика прохождений не терялась
            leaderboard.add_result(game.score, self.elapsed_seconds)

    def _confirm_name(self):
        leaderboard.add_result(self.game.score, self.elapsed_seconds, self.name_input)
        self.entering_name = False

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.entering_name:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_name()
            elif event.key == pygame.K_ESCAPE:
                # Отмена ввода ника — результат всё равно сохраняется, но с именем по умолчанию
                self.name_input = ""
                self._confirm_name()
            elif event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.name_input) < LEADERBOARD_NAME_MAX_LEN:
                self.name_input += event.unicode
            return

        if event.key == pygame.K_r:
            self.game.new_level()
            self.game.change_state(PlayingState(self.game))
        elif event.key == pygame.K_m:
            self.game.change_state(MenuState(self.game))
        elif event.key == pygame.K_l:
            self.game.change_state(LeaderboardState(self.game))
        elif event.key == pygame.K_ESCAPE:
            self.game.running = False

    def update(self):
        self.cursor_timer += 1

    def draw(self, screen):
        g = self.game
        draw_world(g, screen)
        draw_overlay(screen)
        draw_text_centered(screen, "Победа! Уровень пройден!", g.big_font, YELLOW, HEIGHT // 2 - 30)
        draw_text_centered(screen, f"Собрано монет: {g.score}  •  Время: {format_time(self.elapsed_seconds)}",
                            g.font, WHITE, HEIGHT // 2 + 20)

        if self.entering_name:
            draw_text_centered(screen, "Новый результат в лидерборде! Впиши свой ник:",
                                g.font, g.theme["accent"], HEIGHT // 2 + 60)
            cursor = "_" if (self.cursor_timer // 20) % 2 == 0 else " "
            name_text = f"{self.name_input}{cursor}"
            draw_text_centered(screen, name_text, g.big_font, WHITE, HEIGHT // 2 + 100)
            draw_text_centered(screen, "ENTER — подтвердить  •  ESC — пропустить",
                                g.small_font, GRAY, HEIGHT // 2 + 150)
        else:
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
    # Заливаем тёмным фоном перед фоновой картинкой — если у неё уменьшена
    # прозрачность (alpha < 255, см. Game.__init__ — фон "bridge"), сквозь неё
    # будет проглядывать ровный тёмный фон, а не "призрак" прошлого кадра.
    screen.fill(DARK_BG)
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


def draw_boss_health_bar(screen, game):
    """Хелсбар босса — всегда виден, пока он жив (не только когда его атакуют),
    большой и по центру сверху экрана, чтобы сразу было понятно, что идёт бой
    с боссом. hp/max_hp берутся напрямую из game.boss (см. Game.load_room)."""
    boss = game.boss
    bar_width = 420
    bar_height = 22
    x = WIDTH // 2 - bar_width // 2
    y = 18

    label = game.small_font.render("БОСС", True, WHITE)
    screen.blit(label, (x, y - 20))

    pygame.draw.rect(screen, (30, 10, 12), (x, y, bar_width, bar_height), border_radius=4)
    ratio = max(0.0, boss.hp / boss.max_hp) if boss.max_hp else 0.0
    fill_width = int(bar_width * ratio)
    if fill_width > 0:
        pygame.draw.rect(screen, (200, 40, 50), (x, y, fill_width, bar_height), border_radius=4)
    pygame.draw.rect(screen, WHITE, (x, y, bar_width, bar_height), width=2, border_radius=4)

    hp_text = game.small_font.render(f"{max(0, boss.hp)}/{boss.max_hp}", True, WHITE)
    screen.blit(hp_text, (x + bar_width // 2 - hp_text.get_width() // 2, y + 1))


def draw_weapon_icon(screen, game):
    """Панель всех трёх оружий (все доступны сразу) справа от полосок здоровья —
    текущее выделено рамкой, рядом номер клавиши для быстрого переключения (1/2/3).
    Под панелью — процент уверенности распознавания текущего оружия (влияет на
    реальный урон, см. Player.get_current_damage())."""
    mask_size = 22
    gap = 8
    x0, y0 = 20, 50
    hp_row_width = game.player.max_hp * (mask_size + gap)

    x = x0 + hp_row_width + 12
    y = y0 - 3

    for i, weapon_id in enumerate(WEAPON_ORDER):
        icon = game.weapon_icons.get(weapon_id)
        if icon is None:
            continue
        slot_x = x + i * (WEAPON_ICON_HUD_SIZE + 6)
        slot_rect = pygame.Rect(slot_x - 2, y - 2, WEAPON_ICON_HUD_SIZE + 4, WEAPON_ICON_HUD_SIZE + 4)
        if weapon_id == game.player.weapon_id:
            pygame.draw.rect(screen, game.theme["accent"], slot_rect, border_radius=4)
        screen.blit(icon, (slot_x, y))
        number_text = game.small_font.render(str(i + 1), True, WHITE)
        screen.blit(number_text, (slot_x, y + WEAPON_ICON_HUD_SIZE + 2))

    confidence_pct = int(round(game.player.weapon_confidence * 100))
    confidence_text = game.small_font.render(f"Урон: {confidence_pct}%", True, WHITE)
    screen.blit(confidence_text, (x, y + WEAPON_ICON_HUD_SIZE + 22))


def draw_weapon_cooldown_indicator(game, screen):
    """Крупная красная надпись внизу экрана, пока действует кулдаун на
    повторное рисование оружия (см. Game.finish_weapon_drawing)."""
    seconds_left = game.draw_cooldown_timer / FPS
    cooldown_text = game.font.render(
        f"Рисование через {seconds_left:.1f}с", True, RED
    )
    cooldown_rect = cooldown_text.get_rect(center=(WIDTH // 2, HEIGHT - 32))
    screen.blit(cooldown_text, cooldown_rect)


# --- Анимации ближней атаки (меч/топор) — референс: взмахи оружия из Hollow
# Knight/Silksong (быстрая тонкая дуга "гвоздя" у меча, широкий тяжёлый замах
# у топора). Дуга всегда рисуется "лицом вправо" в пределах attack_rect
# (rect уже точно совпадает с хитбоксом атаки — см. Player.get_attack_rect),
# а затем отзеркаливается по player.facing_right — так же, как у спрайтов
# врагов/игрока. Анимации нет по кадрам, есть только процедурный "разворот"
# дуги во времени (progress = доля прошедшего времени взмаха), поэтому
# отдельных файлов кадров не требуется.
def _build_melee_slash_surface(weapon_id, w, h, progress):
    """progress: 0..1 — доля прошедшего времени взмаха (0 = начало, 1 = конец
    attack_timer). Возвращает surface размером (w, h), т.е. ровно как у
    attack_rect, чтобы дуга визуально точно совпадала с хитбоксом атаки."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    if weapon_id == "sword":
        # меч — короткий, очень быстрый тонкий взмах (как нейл-атака в HK)
        sweep_start_deg, sweep_end_deg = -55, 55
        max_width = 4
        color = (245, 245, 255)
        layers = 2
        reveal = min(1.0, progress / 0.6)
        fade = 1.0 if progress < 0.55 else max(0.0, 1.0 - (progress - 0.55) / 0.45)
        radius_scale = 1.15
    else:
        # топор — медленный, широкий и тяжёлый замах с сильной вспышкой удара
        sweep_start_deg, sweep_end_deg = -85, 85
        max_width = 8
        color = (255, 170, 60)
        layers = 3
        reveal = min(1.0, progress / 0.55)
        fade = 1.0 if progress < 0.7 else max(0.0, 1.0 - (progress - 0.7) / 0.3)
        radius_scale = 1.3

    if fade <= 0:
        return surf

    start_rad = math.radians(sweep_start_deg)
    end_rad = math.radians(sweep_start_deg + (sweep_end_deg - sweep_start_deg) * reveal)
    if end_rad <= start_rad:
        return surf

    bounding = pygame.Rect(0, 0, int(w * radius_scale), int(h * radius_scale))
    bounding.center = (w * 0.3, h * 0.5)

    outer_rect = None
    for i in range(layers):
        rect_i = bounding.inflate(i * 5, i * 5)
        if outer_rect is None:
            outer_rect = rect_i
        width_i = max(1, max_width - i * 2)
        alpha = int(255 * fade * (1 - i * 0.3))
        if alpha <= 0:
            continue
        pygame.draw.arc(surf, (*color, alpha), rect_i, start_rad, end_rad, width_i)

    # вспышка удара топора — заполненный клин в момент завершения замаха
    if weapon_id == "axe" and progress > 0.75:
        impact_alpha = int(180 * min(1.0, (progress - 0.75) / 0.2))
        tip_x = outer_rect.centerx + (outer_rect.width / 2) * math.cos(end_rad)
        tip_y = outer_rect.centery - (outer_rect.height / 2) * math.sin(end_rad)
        pygame.draw.circle(surf, (255, 210, 120, impact_alpha), (int(tip_x), int(tip_y)), 6)

    return surf


def draw_melee_slash(game, screen, cam):
    """Отрисовывает анимацию взмаха текущим ближним оружием поверх хитбокса
    атаки (attack_rect), если сейчас идёт удар мечом/топором (у лука ближнего
    хитбокса нет — get_attack_rect() вернёт None)."""
    player = game.player
    attack_rect = player.get_attack_rect()
    if attack_rect is None:
        return
    weapon_id = player.weapon_id
    if weapon_id not in ("sword", "axe"):
        return

    stats = WEAPON_STATS[weapon_id]
    duration = stats["duration_frames"]
    if duration <= 0:
        return
    progress = 1.0 - (player.attack_timer / duration)
    progress = max(0.0, min(1.0, progress))

    slash = _build_melee_slash_surface(weapon_id, attack_rect.width, attack_rect.height, progress)
    if not player.facing_right:
        slash = pygame.transform.flip(slash, True, False)
    screen.blit(slash, attack_rect.move(-cam, 0))


def draw_world(game: Game, screen):
    bg_image = game.backgrounds_dict.get(game.room_id)
    if bg_image is not None:
        draw_background_image(screen, bg_image)
    else:
        # Для комнат без готовой картинки, но с переопределением палитры
        # (ROOM_BG_FALLBACK — новые "весёлые" комнаты meadow/orchard/sky/summit),
        # подмешиваем её цвета поверх выбранной в настройках темы — только фон,
        # HUD (маски HP, акцент) остаётся в цветах глобальной темы.
        bg_theme = dict(game.theme)
        bg_theme.update(ROOM_BG_FALLBACK.get(game.room_id, {}))
        draw_dark_background(screen, pygame.time.get_ticks() // 16, bg_theme, game.spore_count)

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

    for arrow in game.player_arrows:
        screen.blit(arrow.image, arrow.rect.move(-cam, 0))

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

    draw_melee_slash(game, screen, cam)

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
    if game.draw_cooldown_timer > 0:
        draw_weapon_cooldown_indicator(game, screen)

    timer_text = game.font.render(format_time(game.run_timer_frames / FPS), True, WHITE)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 16, 12))


def draw_weapon_canvas_overlay(game, screen):
    """Затемнение поверх игры + белый холст, на котором игрок рисует оружие
    мышью, пока зажата DRAW_WEAPON_KEY. Как только клавиша отпускается, холст
    сразу пропадает (см. draw_weapon_result_banner для надписи с результатом)."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, DRAW_OVERLAY_ALPHA))
    screen.blit(overlay, (0, 0))

    canvas_rect = game.get_draw_canvas_rect()
    screen.blit(game.draw_canvas, canvas_rect)
    pygame.draw.rect(screen, game.theme["accent"], canvas_rect, 3)

    hint_text = game.small_font.render(
        "Рисуй оружие мышью — отпусти R, чтобы распознать", True, WHITE
    )
    hint_rect = hint_text.get_rect(center=(WIDTH // 2, canvas_rect.top - 24))
    screen.blit(hint_text, hint_rect)


def draw_weapon_result_banner(game, screen):
    """Крупная надпись вверху экрана с распознанным оружием — появляется сразу
    после закрытия холста (см. Game.finish_weapon_drawing) и сама гаснет через
    DRAW_RESULT_MESSAGE_FRAMES кадров (game.draw_result_timer)."""
    banner_text = game.big_font.render(game.draw_result_text, True, game.theme["accent"])
    banner_rect = banner_text.get_rect(center=(WIDTH // 2, 48))

    # Полупрозрачная плашка под текстом — чтобы крупные буквы не терялись на фоне уровня
    padding_x, padding_y = 24, 10
    bg_rect = banner_rect.inflate(padding_x * 2, padding_y * 2)
    bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 160))
    screen.blit(bg_surf, bg_rect)

    screen.blit(banner_text, banner_rect)
