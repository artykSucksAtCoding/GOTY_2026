"""Общие вспомогательные функции для тестов: настраивает headless-режим
pygame (без реального окна/звука — то же самое, что использовалось для
ручных smoke-тестов в течение разработки) и гарантирует, что модули игры
(settings, leaderboard, sprites.player и т.д.) можно импортировать по
коротким именам независимо от того, откуда запущен unittest.
"""
import os
import sys
from pathlib import Path

# Headless-драйверы должны быть выставлены ДО первого pygame.init() —
# иначе тесты попытаются открыть настоящее окно/звуковое устройство и
# упадут в среде без дисплея (например, в CI).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PLATFORMER_DIR = Path(__file__).resolve().parent.parent
if str(PLATFORMER_DIR) not in sys.path:
    sys.path.insert(0, str(PLATFORMER_DIR))
