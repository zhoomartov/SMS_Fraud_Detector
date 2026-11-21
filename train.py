"""Обучение SMS Fraud Detector на data/sms_train.csv.

Запуск: python train.py [--file data/sms_train.csv] [--output models/sms_fraud_model.pkl]
Модель обучается на тексте и 11 числовых признаках из src.features.
"""
import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer

from src.features import extract_features_for_model
from src.normalization import normalize_text

ROOT = Path(__file__).resolve().parent


def load_training_data(path: Path) -> tuple[list[str], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Файл обучения не найден: {path}")
    df = pd.read_csv(path, encoding="utf-8")
    required = {"id", "text", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"В CSV отсутствуют столбцы: {', '.join(sorted(missing))}")
    if df["text"].isna().any() or (df["text"].astype(str).str.strip() == "").any():
        raise ValueError("В обучающем CSV есть пустые SMS")
    labels = df["label"].astype(str).str.strip().str.lower()
    invalid = sorted(set(labels) - {"fraud", "ok"})
    if invalid:
        raise ValueError(f"Недопустимые метки: {invalid}; допустимы fraud и ok")
    if set(labels) != {"fraud", "ok"}:
        raise ValueError("Для обучения нужны оба класса: fraud и ok")
    texts = [normalize_text(str(t)) for t in df["text"].tolist()]
    return texts, labels.tolist()


def build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("char_tfidf", TfidfVectorizer(analyzer="char", ngram_range=(2, 5),
                                       min_df=1, sublinear_tf=True, max_features=30000)),
        ("word_tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                       token_pattern=r"(?u)\b\w+\b", min_df=1,
                                       sublinear_tf=True, max_features=20000)),
        ("manual_features", Pipeline([
            ("extract", FunctionTransformer(extract_features_for_model, validate=False)),
            ("vectorize", DictVectorizer(sparse=True)),
        ])),
    ])
    return Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced",
                                           solver="liblinear", random_state=42)),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучить модель обнаружения мошеннических SMS")
    parser.add_argument("--file", default=str(ROOT / "data" / "sms_train.csv"))
    parser.add_argument("--output", default=str(ROOT / "models" / "sms_fraud_model.pkl"))
    args = parser.parse_args()

    texts, labels = load_training_data(Path(args.file))
    model = build_pipeline()
    model.fit(texts, labels)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    print(f"Обучение завершено: {len(texts)} SMS")
    print(f"Классы: {list(model.classes_)}")
    print(f"Модель сохранена: {output}")
    print("Важно: качество проверяйте отдельно через evaluate.py на независимом наборе.")


if __name__ == "__main__":
    main()
