"""Юнит-тесты для констант в settings.py, которые напрямую завязаны на
поведение, добавленное по запросам пользователя в этой игре:
  * кулдаун рисования оружия — 3.5 секунды (DRAW_COOLDOWN_FRAMES);
  * длительность показа баннера с результатом распознавания;
  * пороги уверенности ML-распознавания (50% дефолт, 70% порог "распознано");
  * WEAPON_STATS — базовая структура характеристик оружия (использует
    Player.get_current_damage/get_attack_rect)."""
import unittest

from tests import testing_utils  # noqa: F401

from settings import (
    FPS,
    DRAW_COOLDOWN_FRAMES,
    DRAW_RESULT_MESSAGE_FRAMES,
    WEAPON_RECOGNITION_DEFAULT_CONFIDENCE,
    WEAPON_RECOGNITION_MIN_CONFIDENCE,
    WEAPON_STATS,
    WEAPON_ORDER,
)


class SettingsConstantsTestCase(unittest.TestCase):
    def test_draw_cooldown_is_three_and_a_half_seconds(self):
        self.assertEqual(DRAW_COOLDOWN_FRAMES, int(3.5 * FPS))

    def test_draw_result_message_duration_is_positive(self):
        self.assertGreater(DRAW_RESULT_MESSAGE_FRAMES, 0)

    def test_confidence_thresholds_are_in_valid_range_and_ordered(self):
        self.assertTrue(0.0 <= WEAPON_RECOGNITION_DEFAULT_CONFIDENCE <= 1.0)
        self.assertTrue(0.0 <= WEAPON_RECOGNITION_MIN_CONFIDENCE <= 1.0)
        # Порог "распознано" должен быть строже дефолтной (запасной) уверенности,
        # иначе низкоуверенные рисунки проходили бы как полноценно распознанные.
        self.assertGreater(WEAPON_RECOGNITION_MIN_CONFIDENCE, WEAPON_RECOGNITION_DEFAULT_CONFIDENCE)

    def test_min_confidence_threshold_is_70_percent(self):
        self.assertAlmostEqual(WEAPON_RECOGNITION_MIN_CONFIDENCE, 0.7)

    def test_weapon_stats_has_entry_for_every_weapon_in_order(self):
        for weapon_id in WEAPON_ORDER:
            self.assertIn(weapon_id, WEAPON_STATS)

    def test_weapon_stats_required_keys_present_and_non_negative(self):
        required_keys = {"damage", "duration_frames", "cooldown_frames", "width", "height"}
        for weapon_id, stats in WEAPON_STATS.items():
            with self.subTest(weapon=weapon_id):
                self.assertTrue(required_keys.issubset(stats.keys()))
                for key in required_keys:
                    self.assertGreaterEqual(stats[key], 0)

    def test_melee_weapons_have_positive_hitbox_size(self):
        for weapon_id in ("sword", "axe"):
            with self.subTest(weapon=weapon_id):
                self.assertGreater(WEAPON_STATS[weapon_id]["width"], 0)
                self.assertGreater(WEAPON_STATS[weapon_id]["height"], 0)
                self.assertGreater(WEAPON_STATS[weapon_id]["duration_frames"], 0)

    def test_axe_is_slower_but_stronger_than_sword(self):
        self.assertGreater(WEAPON_STATS["axe"]["damage"], WEAPON_STATS["sword"]["damage"])
        self.assertGreater(WEAPON_STATS["axe"]["cooldown_frames"], WEAPON_STATS["sword"]["cooldown_frames"])
        self.assertGreater(WEAPON_STATS["axe"]["width"], WEAPON_STATS["sword"]["width"])

    def test_bow_has_no_melee_hitbox(self):
        self.assertEqual(WEAPON_STATS["bow"]["width"], 0)
        self.assertEqual(WEAPON_STATS["bow"]["height"], 0)
        self.assertEqual(WEAPON_STATS["bow"]["duration_frames"], 0)


if __name__ == "__main__":
    unittest.main()
