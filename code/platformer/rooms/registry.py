from . import room_forest
from . import room_caves
from . import room_bridge
from . import room_stairs
from . import room_vault
from . import room_meadow
from . import room_orchard
from . import room_sky
from . import room_summit
from . import room_boss

# --- Реестр комнат ---
# Чтобы добавить новую комнату:
#   1) создать файл rooms/room_<название>.py с функцией build() -> Room
#      (см. существующие room_*.py как образец)
#   2) импортировать модуль здесь и добавить строку в ROOM_BUILDERS
#   3) добавить RoomExit в соседних комнатах, указывающий на новый room_id
ROOM_BUILDERS = {
    "forest": room_forest.build,
    "caves": room_caves.build,
    "bridge": room_bridge.build,
    "stairs": room_stairs.build,
    "vault": room_vault.build,
    "meadow": room_meadow.build,
    "orchard": room_orchard.build,
    "sky": room_sky.build,
    "summit": room_summit.build,
    "boss": room_boss.build,
}


def build_room(room_id, game_difficulty="normal"):
    """Создаёт свежий экземпляр комнаты по её id (заново собирает спрайты —
    так что монеты/враги каждый раз восстанавливаются при повторном заходе).
    game_difficulty — глобальная сложность, выбранная игроком в меню перед
    стартом (см. DIFFICULTY_LEVELS в settings.py) — влияет на количество
    врагов и их параметры (см. sprites/enemy_factory.spawn_enemy_group)."""
    try:
        builder = ROOM_BUILDERS[room_id]
    except KeyError:
        raise ValueError(
            f"Неизвестная комната '{room_id}'. "
            f"Доступные: {', '.join(ROOM_BUILDERS.keys())}"
        )
    return builder(game_difficulty)


def first_room_id():
    """Комната, с которой начинается игра."""
    return "forest"