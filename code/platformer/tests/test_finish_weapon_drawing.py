"""Юнит-тесты для Game.finish_weapon_drawing (game.py) — сценарий закрытия
холста рисования оружия:
  * confidence >= WEAPON_RECOGNITION_MIN_CONFIDENCE (0.7) -> оружие меняется,
    в баннере показывается его название и процент уверенности;
  * confidence < 0.7, но модель что-то распознала -> оружие НЕ меняется,
    урон снижается до WEAPON_RECOGNITION_DEFAULT_CONFIDENCE (50%), баннер
    показывает "Оружие не распознано";
  * модель недоступна / не смогла сопоставить класс -> отдельные сообщения,
    оружие не трогается.
Настоящая ML-модель не используется — вместо неё подставляется fake predict(),
чтобы тест был детерминированным и не зависел от обученного model.joblib."""
import unittest
from unittest import mock

from tests import testing_utils  # noqa: F401

import pygame
import game as game_module
from settings import (
    WEAPON_RECOGNITION_MIN_CONFIDENCE,
    WEAPON_RECOGNITION_DEFAULT_CONFIDENCE,
    DRAW_RESULT_MESSAGE_FRAMES,
    DRAW_COOLDOWN_FRAMES,
)
from sprites.player import Player


class FinishWeaponDrawingTestCase(unittest.TestCase):
    def setUp(self):
        self.game = game_module.Game()
        self.game.player = Player(0, 0)
        self.game.player.equip_weapon("sword", confidence=1.0)

    def tearDown(self):
        pygame.quit()

    def _with_fake_prediction(self, weapon_id, confidence, available=True):
        self.game.weapon_recognizer.predict = mock.Mock(return_value=(weapon_id, confidence))
        self.game.weapon_recognizer.available = available

    def test_high_confidence_switches_weapon_and_shows_name_with_percent(self):
        self._with_fake_prediction("axe", 0.95)
        self.game.finish_weapon_drawing()
        self.assertEqual(self.game.player.weapon_id, "axe")
        self.assertEqual(self.game.player.weapon_confidence, 0.95)
        self.assertIn("Топор", self.game.draw_result_text)
        self.assertIn("95", self.game.draw_result_text)

    def test_confidence_exactly_at_threshold_switches_weapon(self):
        self._with_fake_prediction("bow", WEAPON_RECOGNITION_MIN_CONFIDENCE)
        self.game.finish_weapon_drawing()
        self.assertEqual(self.game.player.weapon_id, "bow")

    def test_low_confidence_keeps_previous_weapon_with_default_damage_confidence(self):
        self._with_fake_prediction("axe", 0.4)  # ниже порога 0.7
        self.game.finish_weapon_drawing()
        self.assertEqual(self.game.player.weapon_id, "sword")  # оружие не поменялось
        self.assertEqual(self.game.player.weapon_confidence, WEAPON_RECOGNITION_DEFAULT_CONFIDENCE)
        self.assertEqual(self.game.draw_result_text, "Оружие не распознано")

    def test_recognizer_unavailable_shows_dedicated_message_and_keeps_weapon(self):
        self._with_fake_prediction(None, 0.0, available=False)
        self.game.finish_weapon_drawing()
        self.assertEqual(self.game.player.weapon_id, "sword")
        self.assertEqual(self.game.draw_result_text, "Модель распознавания недоступна")

    def test_unmapped_class_shows_generic_failure_message(self):
        self._with_fake_prediction(None, 0.0, available=True)
        self.game.finish_weapon_drawing()
        self.assertEqual(self.game.player.weapon_id, "sword")
        self.assertEqual(self.game.draw_result_text, "Не удалось распознать оружие")

    def test_finish_drawing_closes_canvas_and_starts_cooldown(self):
        self.game.drawing_mode = True
        self._with_fake_prediction("sword", 0.99)
        self.game.finish_weapon_drawing()
        self.assertFalse(self.game.drawing_mode)
        self.assertEqual(self.game.draw_result_timer, DRAW_RESULT_MESSAGE_FRAMES)
        self.assertEqual(self.game.draw_cooldown_timer, DRAW_COOLDOWN_FRAMES)


if __name__ == "__main__":
    unittest.main()
