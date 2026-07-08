"""Обёртка над готовой ML-моделью распознавания оружия.

Модель та же самая, что использует отдельная программа
code/weapon_recogniser/weapon_recogniser.py (LogisticRegression, обучена на
изображениях 240x240, лежит в code/weapon_recogniser/model.joblib — путь
берётся из WEAPON_RECOGNIZER_MODEL_PATH в settings.py, ничего вручную
подставлять не нужно).

Здесь та же идея холста, что в оригинальной tkinter-программе, просто
холст рисуется прямо поверх игры (см. Game.draw_canvas в game.py), а не в
отдельном окне: игрок рисует контур оружия, отпускает клавишу — эта функция
говорит, на какое из трёх оружий (sword/axe/bow) рисунок похож больше всего.
"""
import pygame

from settings import (
    WEAPON_RECOGNIZER_MODEL_PATH,
    WEAPON_RECOGNIZER_CLASS_TO_WEAPON,
    DRAW_CANVAS_MODEL_SIZE,
)

try:
    import numpy as np
    import joblib
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


class WeaponRecognizer:
    """Ленивая обёртка над моделью. Если библиотеки (numpy/joblib/scikit-learn)
    или сам файл модели недоступны — available остаётся False, и predict()
    просто ничего не возвращает (None), не роняя игру. Клавиша рисования при
    этом всё равно открывает холст, только оружие после отпускания не меняется."""

    def __init__(self):
        self.model = None
        self.class_names = None
        self.available = False

        if not _DEPS_AVAILABLE:
            return

        try:
            data = joblib.load(WEAPON_RECOGNIZER_MODEL_PATH)
        except Exception:
            return

        # Поддерживаем два формата сохранения — как в weapon_recogniser.py:
        # 1) {"model": LogisticRegression, "class_names": [...]}
        # 2) просто сама модель (тогда классы — числа 0..N-1)
        if isinstance(data, dict) and "model" in data:
            self.model = data["model"]
            self.class_names = data.get("class_names")
        else:
            self.model = data
            self.class_names = None

        self.available = self.model is not None

    def predict(self, canvas_surface):
        """canvas_surface — pygame.Surface с рисунком (белый фон, чёрные линии,
        как в холсте tkinter-программы). Возвращает weapon_id ("sword"/"axe"/"bow")
        или None, если распознавание недоступно/не удалось сопоставить класс."""
        if not self.available:
            return None

        # Уменьшаем холст до того же разрешения, в котором обучалась модель
        # (SAVE_SIZE=240 в weapon_recogniser.py), переводим в градации серого
        # и нормализуем в [0, 1] — один в один как _preprocess() в оригинале.
        small = pygame.transform.smoothscale(
            canvas_surface, (DRAW_CANVAS_MODEL_SIZE, DRAW_CANVAS_MODEL_SIZE)
        )
        rgb = pygame.surfarray.array3d(small).astype(np.float32)
        rgb = np.transpose(rgb, (1, 0, 2))  # pygame даёт (x, y, c) -> приводим к (y, x, c)
        gray = (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114) / 255.0

        flat = gray.reshape(1, -1)
        try:
            pred_idx = int(self.model.predict(flat)[0])
        except Exception:
            return None

        label = str(self.class_names[pred_idx]) if self.class_names else str(pred_idx)
        return WEAPON_RECOGNIZER_CLASS_TO_WEAPON.get(label.strip().lower())
