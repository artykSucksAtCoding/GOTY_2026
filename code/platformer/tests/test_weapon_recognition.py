"""Юнит-тесты для weapon_recognition.WeaponRecognizer — сопоставление
классов модели (Axe/Bow/Sword и рус. названия) с id оружия, регистронезависимость,
поведение при недоступных зависимостях/неизвестном классе. Настоящая ML-модель
(model.joblib) НЕ используется — вместо неё подставляется лёгкий фейковый объект
с predict()/predict_proba(), чтобы тест не зависел от обученной модели и от
наличия scikit-learn/joblib на машине."""
import unittest

from tests import testing_utils  # noqa: F401

from weapon_recognition import WeaponRecognizer


class _FakeModel:
    """Имитирует sklearn-классификатор: всегда предсказывает заранее заданный
    индекс класса с заданной вероятностью."""

    def __init__(self, pred_idx, proba_for_pred_idx=1.0, n_classes=3, has_proba=True):
        self.pred_idx = pred_idx
        self.proba_for_pred_idx = proba_for_pred_idx
        self.n_classes = n_classes
        self.has_proba = has_proba

    def predict(self, X):
        return [self.pred_idx]

    def predict_proba(self, X):
        if not self.has_proba:
            raise AttributeError("no predict_proba")
        row = [0.0] * self.n_classes
        row[self.pred_idx] = self.proba_for_pred_idx
        return [row]


def _make_recognizer(model, class_names):
    """Строит WeaponRecognizer в обход __init__ (который грузит настоящий
    model.joblib с диска) — подставляем фейковую модель напрямую, как и
    предполагает контракт класса (self.model/self.class_names/self.available)."""
    recognizer = WeaponRecognizer.__new__(WeaponRecognizer)
    recognizer.model = model
    recognizer.class_names = class_names
    recognizer.available = True
    return recognizer


def _make_canvas():
    import pygame
    surface = pygame.Surface((300, 300))
    surface.fill((255, 255, 255))
    return surface


class WeaponRecognizerTestCase(unittest.TestCase):
    def test_unavailable_recognizer_returns_none_and_zero_confidence(self):
        recognizer = WeaponRecognizer.__new__(WeaponRecognizer)
        recognizer.model = None
        recognizer.class_names = None
        recognizer.available = False
        weapon_id, confidence = recognizer.predict(_make_canvas())
        self.assertIsNone(weapon_id)
        self.assertEqual(confidence, 0.0)

    def test_predict_maps_english_class_name_to_weapon_id(self):
        recognizer = _make_recognizer(_FakeModel(pred_idx=0, proba_for_pred_idx=0.83), ["Axe", "Bow", "Sword"])
        weapon_id, confidence = recognizer.predict(_make_canvas())
        self.assertEqual(weapon_id, "axe")
        self.assertAlmostEqual(confidence, 0.83)

    def test_predict_is_case_insensitive(self):
        recognizer = _make_recognizer(_FakeModel(pred_idx=2, proba_for_pred_idx=0.9), ["Axe", "Bow", "SWORD"])
        weapon_id, _ = recognizer.predict(_make_canvas())
        self.assertEqual(weapon_id, "sword")

    def test_predict_maps_russian_class_names(self):
        recognizer = _make_recognizer(_FakeModel(pred_idx=1, proba_for_pred_idx=0.77), ["топор", "лук", "меч"])
        weapon_id, confidence = recognizer.predict(_make_canvas())
        self.assertEqual(weapon_id, "bow")
        self.assertAlmostEqual(confidence, 0.77)

    def test_predict_unknown_class_name_returns_none_weapon_id(self):
        recognizer = _make_recognizer(_FakeModel(pred_idx=0, proba_for_pred_idx=0.9), ["Shield"])
        weapon_id, confidence = recognizer.predict(_make_canvas())
        self.assertIsNone(weapon_id)
        self.assertAlmostEqual(confidence, 0.9)

    def test_predict_without_class_names_uses_numeric_index_and_fails_mapping(self):
        recognizer = _make_recognizer(_FakeModel(pred_idx=0, proba_for_pred_idx=0.6), None)
        weapon_id, confidence = recognizer.predict(_make_canvas())
        self.assertIsNone(weapon_id)  # индекс "0" не входит в WEAPON_RECOGNIZER_CLASS_TO_WEAPON
        self.assertAlmostEqual(confidence, 0.6)

    def test_predict_falls_back_to_confidence_1_when_no_predict_proba(self):
        recognizer = _make_recognizer(
            _FakeModel(pred_idx=0, has_proba=False), ["Sword"]
        )
        weapon_id, confidence = recognizer.predict(_make_canvas())
        self.assertEqual(weapon_id, "sword")
        self.assertEqual(confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
