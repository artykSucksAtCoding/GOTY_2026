"""Юнит-тесты для leaderboard.py — сохранение/загрузка результатов, обрезка
списка до LEADERBOARD_MAX_STORED, дефолтное имя, отбор для "попадёт ли в
таблицу лидеров" (will_qualify) и удаление записи."""
import json
import tempfile
import unittest
from pathlib import Path

from tests import testing_utils  # noqa: F401  (настраивает sys.path и headless-драйверы)

import leaderboard
from settings import LEADERBOARD_MAX_STORED, LEADERBOARD_NAME_MAX_LEN, LEADERBOARD_DEFAULT_NAME


class LeaderboardTestCase(unittest.TestCase):
    """Каждый тест работает с отдельным временным файлом вместо настоящего
    leaderboard.json игрока — реальный файл никогда не читается и не
    перезаписывается тестами."""

    def setUp(self):
        self._original_path = leaderboard.LEADERBOARD_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(setattr, leaderboard, "LEADERBOARD_PATH", self._original_path)
        self.fake_path = Path(self._tmpdir.name) / "leaderboard_test.json"
        leaderboard.LEADERBOARD_PATH = self.fake_path

    # --- load_leaderboard -------------------------------------------------

    def test_load_missing_file_returns_empty_list(self):
        self.assertFalse(self.fake_path.exists())
        self.assertEqual(leaderboard.load_leaderboard(), [])

    def test_load_corrupted_json_returns_empty_list(self):
        self.fake_path.write_text("{ не валидный json", encoding="utf-8")
        self.assertEqual(leaderboard.load_leaderboard(), [])

    def test_load_non_list_json_returns_empty_list(self):
        self.fake_path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
        self.assertEqual(leaderboard.load_leaderboard(), [])

    # --- save_leaderboard / roundtrip --------------------------------------

    def test_save_and_load_roundtrip(self):
        records = [{"name": "Тест", "coins": 5, "time": 12.3, "date": "2026-01-01 00:00"}]
        leaderboard.save_leaderboard(records)
        self.assertEqual(leaderboard.load_leaderboard(), records)

    # --- add_result -----------------------------------------------------------

    def test_add_result_uses_default_name_when_missing(self):
        records = leaderboard.add_result(coins=3, time_seconds=10.0, name=None)
        self.assertEqual(records[0]["name"], LEADERBOARD_DEFAULT_NAME)

    def test_add_result_uses_default_name_when_blank(self):
        records = leaderboard.add_result(coins=3, time_seconds=10.0, name="   ")
        self.assertEqual(records[0]["name"], LEADERBOARD_DEFAULT_NAME)

    def test_add_result_truncates_long_name(self):
        long_name = "Оч" * (LEADERBOARD_NAME_MAX_LEN + 5)
        records = leaderboard.add_result(coins=3, time_seconds=10.0, name=long_name)
        self.assertEqual(len(records[0]["name"]), LEADERBOARD_NAME_MAX_LEN)

    def test_add_result_stores_coins_and_time_as_correct_types(self):
        records = leaderboard.add_result(coins="7", time_seconds="42.5", name="Игрок1")
        self.assertEqual(records[0]["coins"], 7)
        self.assertIsInstance(records[0]["coins"], int)
        self.assertEqual(records[0]["time"], 42.5)
        self.assertIsInstance(records[0]["time"], float)

    def test_add_result_sorts_by_coins_descending(self):
        leaderboard.add_result(coins=1, time_seconds=1.0, name="A")
        leaderboard.add_result(coins=9, time_seconds=1.0, name="B")
        records = leaderboard.add_result(coins=5, time_seconds=1.0, name="C")
        coins_in_order = [r["coins"] for r in records]
        self.assertEqual(coins_in_order, sorted(coins_in_order, reverse=True))

    def test_add_result_trims_to_max_stored(self):
        records = []
        for i in range(LEADERBOARD_MAX_STORED + 10):
            records = leaderboard.add_result(coins=i, time_seconds=1.0, name=f"P{i}")
        self.assertEqual(len(records), LEADERBOARD_MAX_STORED)
        # После обрезки должны остаться лучшие результаты (самые большие coins)
        self.assertEqual(records[0]["coins"], LEADERBOARD_MAX_STORED + 9)

    # --- will_qualify -----------------------------------------------------------

    def test_will_qualify_true_when_leaderboard_not_full(self):
        leaderboard.add_result(coins=1, time_seconds=1.0, name="A")
        self.assertTrue(leaderboard.will_qualify(coins=0))

    def test_will_qualify_true_when_beats_worst_stored(self):
        for i in range(LEADERBOARD_MAX_STORED):
            leaderboard.add_result(coins=i + 1, time_seconds=1.0, name=f"P{i}")
        self.assertTrue(leaderboard.will_qualify(coins=1000))

    def test_will_qualify_false_when_worse_than_worst_stored(self):
        for i in range(LEADERBOARD_MAX_STORED):
            leaderboard.add_result(coins=i + 1, time_seconds=1.0, name=f"P{i}")
        self.assertFalse(leaderboard.will_qualify(coins=0))

    # --- remove_result -----------------------------------------------------------

    def test_remove_result_deletes_record_and_saves(self):
        leaderboard.add_result(coins=1, time_seconds=1.0, name="A")
        records = leaderboard.add_result(coins=2, time_seconds=1.0, name="B")
        target = records[0]
        updated = leaderboard.remove_result(records, target)
        self.assertNotIn(target, updated)
        self.assertEqual(leaderboard.load_leaderboard(), updated)

    def test_remove_result_missing_record_is_noop(self):
        records = leaderboard.add_result(coins=1, time_seconds=1.0, name="A")
        fake_record = {"name": "ghost", "coins": 999, "time": 0.0, "date": "x"}
        updated = leaderboard.remove_result(list(records), fake_record)
        self.assertEqual(updated, records)


if __name__ == "__main__":
    unittest.main()
