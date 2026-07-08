# pip install pillow scikit-learn joblib

import numpy as np
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw

import joblib

PATH_TO_MODEL = ...

# ============================================================
# КОНСТАНТЫ ХОЛСТА
# ============================================================
SCALE = 3
SAVE_SIZE = 240                    # размер, в котором обучалась модель
CANVAS_SIZE = SAVE_SIZE * SCALE
BRUSH_SIZE = 3
BG_COLOR = "white"
DRAW_COLOR = "black"


def load_logreg_model(path):
    data = joblib.load(path)
    # Поддерживаем два формата сохранения:
    # 1) {"model": LogisticRegression, "class_names": [...]}
    # 2) просто сама модель (тогда классы будут просто числами 0..N-1)
    if isinstance(data, dict) and "model" in data:
        return data["model"], data.get("class_names")
    return data, None


# ============================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================
class RecognizerApp:
    def __init__(self, root, model, class_names):
        self.root = root
        self.root.title("Распознавание оружия (LogReg)  |  S - распознать, C - очистить, Q - выход")

        self.model = model
        self.class_names = class_names

        # ---------- UI ----------
        self.canvas = tk.Canvas(
            root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg=BG_COLOR, cursor="cross"
        )
        self.canvas.pack(padx=10, pady=10)

        self.prediction_label = tk.Label(root, text="Нарисуй что-нибудь и нажми S", font=("Arial", 14))
        self.prediction_label.pack(pady=(0, 10))

        # ---------- изображение в PIL (для распознавания), без ресайза/интерполяции ----------
        self.image = Image.new("RGB", (SAVE_SIZE, SAVE_SIZE), BG_COLOR)
        self.draw = ImageDraw.Draw(self.image)
        self.last_x, self.last_y = None, None

        # Мышь
        self.canvas.bind("<ButtonPress-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)

        # Клавиатура
        self.root.bind("<KeyPress-s>", self.recognize)
        self.root.bind("<KeyPress-S>", self.recognize)
        self.root.bind("<KeyPress-c>", self.clear_canvas)
        self.root.bind("<KeyPress-C>", self.clear_canvas)
        self.root.bind("<KeyPress-q>", self.quit_app)
        self.root.bind("<KeyPress-Q>", self.quit_app)
        self.root.bind("<Escape>", self.quit_app)

        self.canvas.focus_set()

    # ---------- отрисовка (координаты пересчитываются в масштаб SAVE_SIZE) ----------
    @staticmethod
    def _to_image_coords(x, y):
        return x / SCALE, y / SCALE

    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def paint(self, event):
        x, y = event.x, event.y
        if self.last_x is not None:
            self.canvas.create_line(
                self.last_x, self.last_y, x, y,
                width=BRUSH_SIZE * SCALE, fill=DRAW_COLOR,
                capstyle=tk.ROUND, smooth=True
            )
            ix0, iy0 = self._to_image_coords(self.last_x, self.last_y)
            ix1, iy1 = self._to_image_coords(x, y)
            self.draw.line([ix0, iy0, ix1, iy1], fill=DRAW_COLOR, width=BRUSH_SIZE)
        self.last_x, self.last_y = x, y

    def stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def clear_canvas(self, event=None):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (SAVE_SIZE, SAVE_SIZE), BG_COLOR)
        self.draw = ImageDraw.Draw(self.image)
        self.prediction_label.config(text="Нарисуй что-нибудь и нажми S")

    # ---------- распознавание ----------
    def _preprocess(self):
        """Готовит нарисованное изображение к распознаванию: grayscale + нормализация."""
        gray = self.image.convert("L")
        arr = np.array(gray, dtype=np.float32) / 255.0  # (240, 240), значения [0, 1]
        return arr

    def _predict_logreg(self, arr):
        flat = arr.reshape(1, -1)
        pred_idx = int(self.model.predict(flat)[0])
        confidence = None
        if hasattr(self.model, "predict_proba"):
            confidence = float(self.model.predict_proba(flat)[0][pred_idx])
        label = self.class_names[pred_idx] if self.class_names else str(pred_idx)
        return label, confidence

    def recognize(self, event=None):
        arr = self._preprocess()
        label, confidence = self._predict_logreg(arr)

        if confidence is not None:
            text = f"Это похоже на: {label}  ({confidence * 100:.1f}%)"
        else:
            text = f"Это похоже на: {label}"
        self.prediction_label.config(text=text)

    def quit_app(self, event=None):
        self.root.destroy()


# ============================================================
# ЗАПУСК
# ============================================================
def main():
    try:
        model, class_names = load_logreg_model(PATH_TO_MODEL)
    except Exception as e:
        # Временное окно нужно, чтобы messagebox вообще отобразился
        tmp_root = tk.Tk()
        tmp_root.withdraw()
        messagebox.showerror("Ошибка загрузки модели", f"Не удалось загрузить {PATH_TO_MODEL}:\n{e}")
        return

    root = tk.Tk()
    RecognizerApp(root, model, class_names)
    root.mainloop()


if __name__ == "__main__":
    main()