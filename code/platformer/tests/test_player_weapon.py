"""Юнит-тесты для игровой логики оружия/урона игрока (sprites/player.py) —
equip_weapon()/get_current_damage(), которые масштабируют урон оружия по
проценту уверенности ML-распознавания (см. WEAPON_RECOGNITION_* в settings.py
и Game.finish_weapon_drawing в game.py)."""
import unittest

from tests import testing_utils  # noqa: F401

import pygame
from sprites.player import Player
from settings import WEAPON_STATS, WEAPON_RECOGNITION_DEFAULT_CONFIDENCE


def setUpModule():
    # Player.__init__ создаёт pygame.mixer.Sound(...) для звуков атаки/дэша —
    # нужен инициализированный (пусть и "немой", SDL_AUDIODRIVER=dummy) pygame.
    pygame.init()


def tearDownModule():
    pygame.quit()


class PlayerWeaponDamageTestCase(unittest.TestCase):
    def setUp(self):
        self.player = Player(0, 0)

    def test_default_weapon_is_sword_with_default_confidence(self):
        self.assertEqual(self.player.weapon_id, "sword")
        self.assertEqual(self.player.weapon_confidence, WEAPON_RECOGNITION_DEFAULT_CONFIDENCE)

    def test_equip_weapon_without_confidence_uses_default(self):
        self.player.equip_weapon("axe")
        self.assertEqual(self.player.weapon_id, "axe")
        self.assertEqual(self.player.weapon_confidence, WEAPON_RECOGNITION_DEFAULT_CONFIDENCE)

    def test_equip_weapon_with_explicit_confidence(self):
        self.player.equip_weapon("bow", confidence=0.92)
        self.assertEqual(self.player.weapon_id, "bow")
        self.assertEqual(self.player.weapon_confidence, 0.92)

    def test_get_current_damage_scales_linearly_with_confidence(self):
        # axe damage=3 (см. WEAPON_STATS) при 100% уверенности -> полный урон
        self.player.equip_weapon("axe", confidence=1.0)
        self.assertEqual(self.player.get_current_damage(), WEAPON_STATS["axe"]["damage"])

    def test_get_current_damage_at_recognition_threshold(self):
        # Порог распознавания (WEAPON_RECOGNITION_MIN_CONFIDENCE=0.7) — урон
        # округляется линейно: axe damage=3 * confidence=0.7 = 2.1 -> round -> 2
        self.player.equip_weapon("axe", confidence=0.7)
        self.assertEqual(self.player.get_current_damage(), round(3 * 0.7))

    def test_get_current_damage_never_drops_below_one(self):
        # sword damage=1 при низкой уверенности (после неудачного распознавания
        # оружие остаётся прежним с уроном по WEAPON_RECOGNITION_DEFAULT_CONFIDENCE=0.5,
        # round(1*0.5)=0 -> должно быть подстраховано max(1, ...) до 1.
        self.player.equip_weapon("sword", confidence=0.05)
        self.assertEqual(self.player.get_current_damage(), 1)

    def test_get_current_damage_uses_default_confidence_after_plain_switch(self):
        # Переключение клавишами 1/2/3 (без confidence) должно давать ровно
        # тот же урон, что и WEAPON_RECOGNITION_DEFAULT_CONFIDENCE предполагает.
        self.player.equip_weapon("axe")
        expected = max(1, round(WEAPON_STATS["axe"]["damage"] * WEAPON_RECOGNITION_DEFAULT_CONFIDENCE))
        self.assertEqual(self.player.get_current_damage(), expected)


if __name__ == "__main__":
    unittest.main()
