WIDTH, HEIGHT = 960, 540
FPS = 60

GRAVITY = 0.8
PLAYER_SPEED = 5
JUMP_STRENGTH = -16

# Время "койота" — сколько кадров после схода с платформы всё ещё можно прыгнуть
COYOTE_TIME_SEC = 0.12
COYOTE_TIME_FRAMES = int(COYOTE_TIME_SEC * FPS)

# Если отпустить прыжок раньше, вертикальная скорость "обрезается" до этого значения —
# короткий тап даёт низкий прыжок, удержание до пика даёт полный JUMP_STRENGTH
MIN_JUMP_VELOCITY = JUMP_STRENGTH * 0.4

# Двойной прыжок: сколько дополнительных прыжков доступно уже в воздухе
# (не считая обычного прыжка с земли/койот-тайма)
MAX_AIR_JUMPS = 1
AIR_JUMP_STRENGTH = JUMP_STRENGTH * 0.85  # прыжок в воздухе чуть слабее обычного

# Дэш — быстрый рывок по горизонтали на отдельной кнопке (Shift)
DASH_SPEED = 15
DASH_DURATION_SEC = 0.15
DASH_DURATION_FRAMES = int(DASH_DURATION_SEC * FPS)
DASH_COOLDOWN_SEC = 0.7
DASH_COOLDOWN_FRAMES = int(DASH_COOLDOWN_SEC * FPS)

# Сколько кадров живёт каждый "призрак" в шлейфе после дэша, пока не растворится
DASH_TRAIL_MAX_AGE = 14

# --- Атака ---
ATTACK_DURATION_FRAMES = int(0.15 * FPS)   # сколько кадров активен хитбокс удара
ATTACK_COOLDOWN_FRAMES = int(0.35 * FPS)   # общий откат между атаками (обычной и вниз)
ATTACK_WIDTH = 30                          # ширина хитбокса обычной атаки
ATTACK_HEIGHT = 34                         # высота хитбокса обычной атаки

# --- Атака вниз (удар в пол, работает только в воздухе) ---
DOWN_ATTACK_FALL_SPEED = 24     # с какой скоростью игрок резко падает вниз
DOWN_ATTACK_MAX_FALL = 26       # отдельный, чуть более высокий предел падения на время атаки
DOWN_ATTACK_HEIGHT = 18         # высота хитбокса под ногами
DOWN_ATTACK_BOUNCE = JUMP_STRENGTH * 0.6  # небольшой отскок вверх при успешном попадании

WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
SKY_BLUE = (135, 206, 235)
GREEN = (60, 180, 75)
DARK_GREEN = (30, 120, 40)
BROWN = (139, 90, 43)
RED = (220, 50, 50)
YELLOW = (255, 215, 0)
BLUE = (50, 100, 220)
GRAY = (100, 100, 100)
DARK_OVERLAY = (0, 0, 0, 160)
CYAN = (100, 230, 230)
