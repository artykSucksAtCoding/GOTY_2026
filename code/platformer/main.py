import os
import sys

# В собранном PyInstaller-установщике (см. installer/) все ассеты
# (images/, sound/, fonts/) распаковываются в sys._MEIPASS, а не лежат рядом
# с .exe. Игра грузит их по путям, заданным ОТНОСИТЕЛЬНО рабочей директории
# (например, "images/backgrounds/forest.png" в settings.py/game.py) — поэтому
# переключаем рабочую директорию на sys._MEIPASS ДО импорта settings/game,
# чтобы все такие относительные пути продолжали работать без изменений.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)

from settings import*
from game import Game


if __name__ == "__main__":
    Game().run()