import json
from datetime import datetime
from pathlib import Path

from settings import (
    LEADERBOARD_FILE_NAME,
    LEADERBOARD_MAX_STORED,
    LEADERBOARD_NAME_MAX_LEN,
    LEADERBOARD_DEFAULT_NAME,
)

# Путь считается от расположения ЭТОГО файла, а не от текущей рабочей директории —
# так игра сохраняет результаты в одно и то же место независимо от того,
# из какой папки её запустили (PyCharm, терминал, двойной клик и т.п.)
BASE_DIR = Path(__file__).resolve().parent
LEADERBOARD_PATH = BASE_DIR / LEADERBOARD_FILE_NAME


def load_leaderboard():
    """Возвращает список результатов из файла. Если файла нет или он повреждён —
    возвращает пустой список, не роняя игру."""
    try:
        with open(LEADERBOARD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_leaderboard(records):
    """Сохраняет список результатов в файл. Ошибку записи (например, нет прав
    на диск) проглатываем — статистика необязательна для работы самой игры."""
    try:
        with open(LEADERBOARD_PATH, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def will_qualify(coins):
    """Проверяет, попадёт ли результат с таким числом монет в сохранённый
    лидерборд (до фактического сохранения) — используется, чтобы решить,
    стоит ли предлагать игроку вписать ник после победы. Правило то же самое,
    что и обрезка списка в add_result: пока хранится меньше LEADERBOARD_MAX_STORED
    записей — попадает любой результат, иначе нужно обойти худший из сохранённых."""
    records = load_leaderboard()
    if len(records) < LEADERBOARD_MAX_STORED:
        return True
    worst_coins = min(r["coins"] for r in records)
    return coins >= worst_coins


def add_result(coins, time_seconds, name=None):
    """Добавляет новый результат прохождения и сохраняет обновлённый список.
    Хранится не больше LEADERBOARD_MAX_STORED лучших результатов (по монетам),
    чтобы файл не рос бесконечно при частых перепрохождениях.
    name — ник, который игрок ввёл на экране победы; если пустой/не передан,
    используется LEADERBOARD_DEFAULT_NAME."""
    records = load_leaderboard()

    clean_name = (name or "").strip()[:LEADERBOARD_NAME_MAX_LEN] or LEADERBOARD_DEFAULT_NAME

    records.append({
        "name": clean_name,
        "coins": int(coins),
        "time": float(time_seconds),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    # обрезаем список, оставляя лучшие по монетам — просто чтобы файл не рос бесконечно;
    # при отображении на экране лидерборда сортировка выбирается отдельно (фильтром)
    records.sort(key=lambda r: r["coins"], reverse=True)
    records = records[:LEADERBOARD_MAX_STORED]

    save_leaderboard(records)
    return records


def remove_result(records, record):
    """Удаляет конкретную запись (старого лидера) из списка и сохраняет файл.
    records должен быть тем же списком объектов, что вернул load_leaderboard()/
    add_result() — record ищется и удаляется по идентичности элемента."""
    if record in records:
        records.remove(record)
    save_leaderboard(records)
    return records