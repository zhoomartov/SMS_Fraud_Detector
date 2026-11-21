"""Загрузка обученной модели и получение вероятности fraud."""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.features import extract_features_for_model
from src.normalization import normalize_text

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "sms_fraud_model.pkl"


def _register_main_compat():
    """Обученный pkl ссылается на __main__.extract_features_for_model (функция
    была объявлена в ноутбуке). Регистрируем функцию из src.features в __main__,
    чтобы joblib мог восстановить FunctionTransformer. Модель не меняется."""
    main = sys.modules["__main__"]
    if not hasattr(main, "extract_features_for_model"):
        setattr(main, "extract_features_for_model", extract_features_for_model)


@lru_cache(maxsize=1)
def _load(path: str):
    import joblib
    _register_main_compat()
    return joblib.load(path)  # только доверенный файл из этого проекта


def load_model(path=MODEL_PATH):
    return _load(str(path))


def fraud_index(model) -> int:
    return list(model.classes_).index("fraud")


def fraud_probabilities(texts, model=None) -> np.ndarray:
    """Вероятность класса fraud для списка исходных SMS (нормализация внутри)."""
    model = model or load_model()
    normalized = [normalize_text(t) for t in texts]
    return model.predict_proba(normalized)[:, fraud_index(model)]
