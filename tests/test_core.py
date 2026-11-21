"""Диагностические тесты (запуск: python -m unittest discover -s tests -v).
Сообщения написаны только для проверки и не входят в train/dev. Тесты проверяют,
что код работает и модель воспроизводит ноутбук, а не точность модели (её измеряет evaluate.py)."""
import sys
import unittest
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.detector import analyze_domains, check, check_batch, score_to_risk
from src.features import FEATURE_NAMES, extract_features
from src.model import fraud_probabilities, load_model
from src.normalization import normalize_text


class CoreTests(unittest.TestCase):
    def test_model_loads_and_classes(self):
        m = load_model()
        self.assertEqual(sorted(m.classes_), ["fraud", "ok"])
        self.assertEqual(m.predict([normalize_text("Срочно отправьте код")]).shape, (1,))

    def test_probability_matches_notebook(self):
        text = "Поздравляем! Вы выиграли приз. Перейдите по ссылке для получения."
        self.assertAlmostEqual(fraud_probabilities([text])[0], 0.9209912856293182, places=9)

    def test_feature_names_and_normalization(self):
        self.assertEqual(list(extract_features("x")), FEATURE_NAMES)
        self.assertEqual(normalize_text("Ср0чн0 отправьте к0д"), "срочно отправьте код")
        self.assertEqual(normalize_text("к о д отправьте срочно"), "код отправьте срочно")
        self.assertEqual(normalize_text(None), "")

    def test_thresholds(self):
        for s, r in [(0, "low"), (29, "low"), (30, "medium"), (64, "medium"), (65, "high"), (100, "high")]:
            self.assertEqual(score_to_risk(s), r)

    def test_domains(self):
        official = {"beeline.kg": True, "login.beeline.kg": True, "www.nbkr.kg/x": True,
                    "beeline.kg.fake-site.com": False, "fake-beeline.kg": False,
                    "mbank.kg.example": False, "http://mbank.kg@evil.com": False}
        for text, expected in official.items():
            self.assertEqual(analyze_domains(text)[0]["official"], expected, text)

    def test_empty_text(self):
        for bad in ("", "   ", None):
            with self.assertRaises(ValueError):
                check(bad)

    def test_response_shape_and_score_equals_probability(self):
        text = "Ваша карта заблокирована! Срочно подтвердите данные."
        r = check(text)
        self.assertEqual(set(["risk", "score", "reasons", "recommendation"]) - set(r), set())
        self.assertEqual(r["score"], round(fraud_probabilities([text])[0] * 100))

    def test_batch_equals_single(self):
        texts = ["Ваш баланс пополнен.", "Сообщите код из SMS срочно"]
        self.assertEqual([x["score"] for x in check_batch(texts)], [check(t)["score"] for t in texts])

    def test_scenarios(self):
        high = [
            "Ваш аккаунт в безопасности под угрозой. Сообщите код из SMS оператору.",
            "Ваша карта заблокирована! Срочно подтвердите данные.",
            "Поздравляем! Вы выиграли приз 100000 сом. Отправьте паспортные данные.",
            "Сиздин эсебиңиз бөгөттөлдү. Дароо кодду жөнөтүңүз.",
            "Ср0чн0 отправьте к0д, иначе сч3т заблокируют",
            "с р о ч н о   о т п р а в ь т е   к о д   п а р о л ь",
            "Ваш счёт заблокирован. Перейдите по ссылке: http://beeline.kg.fake-site.com/login",
        ]
        for t in high:
            self.assertEqual(check(t)["risk"], "high", t)
        self.assertEqual(check("MBank: ваш баланс пополнен на 300 сом. Спасибо, что с нами.")["risk"], "low")


if __name__ == "__main__":
    unittest.main()
