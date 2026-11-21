"""Оценка на размеченном CSV (id,text,label). HIGH = fraud, LOW и MEDIUM = ok."""
import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)

from src.detector import check_batch
from src.model import load_model
from src.normalization import normalize_text

LABELS = ["ok", "fraud"]
# Справка: результаты прошлых запусков (НЕ этого запуска)
REF_TZ = "Accuracy 0.975, Precision 0.952, Recall 1.0, [[19,1],[0,20]] (указано в ТЗ)"
REF_NOTEBOOK = "Accuracy 1.0, Precision 1.0, Recall 1.0, [[20,0],[0,20]] (вывод в сохранённом ноутбуке)"


def load_csv(path):
    if not Path(path).exists():
        sys.exit(f"Файл не найден: {path}. Положите sms_dev.csv в папку data/ или укажите --file")
    df = pd.read_csv(path)
    missing = {"id", "text", "label"} - set(df.columns)
    if missing:
        sys.exit(f"В {path} нет столбцов: {', '.join(sorted(missing))}. Нужны: id,text,label")
    if df["text"].isna().any() or (df["text"].astype(str).str.strip() == "").any():
        sys.exit(f"В {path} есть пустые тексты")
    bad = sorted(set(df["label"].astype(str)) - set(LABELS))
    if bad:
        sys.exit(f"В {path} неизвестные метки: {bad}. Допустимы: fraud, ok")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/sms_dev.csv")
    args = ap.parse_args()
    warnings.filterwarnings("default")

    df = load_csv(args.file)
    results = check_batch(df["text"].astype(str).tolist())
    df["score"] = [r["score"] for r in results]
    df["risk"] = [r["risk"] for r in results]
    df["pred"] = ["fraud" if r == "high" else "ok" for r in df["risk"]]

    y, p = df["label"], df["pred"]
    cm = confusion_matrix(y, p, labels=LABELS)
    print(f"Файл: {args.file}  (сообщений: {len(df)})")
    print(f"Accuracy:         {accuracy_score(y, p):.4f}")
    print(f"Precision(fraud): {precision_score(y, p, pos_label='fraud', zero_division=0):.4f}")
    print(f"Recall(fraud):    {recall_score(y, p, pos_label='fraud', zero_division=0):.4f}")
    print(f"F1(fraud):        {f1_score(y, p, pos_label='fraud', zero_division=0):.4f}")
    print("Confusion Matrix (порядок классов: ok, fraud):")
    print(cm)
    print("Уровни риска:", df["risk"].value_counts().to_dict())

    model = load_model()
    raw = pd.Series(model.predict(df["text"].astype(str).map(normalize_text)), index=df.index)
    print(f"Справочно: accuracy по model.predict (argmax, без порогов ТЗ) = {accuracy_score(y, raw):.4f}")

    errors = df[df["label"] != df["pred"]]
    print(f"\nОшибок классификации: {len(errors)}")
    for _, r in errors.iterrows():
        print(f"  id={r['id']} | истина={r['label']} | предсказано={r['pred']} | score={r['score']} | {r['text']}")
    print(f"\nПрошлые запуски (не этот): {REF_TZ}; {REF_NOTEBOOK}")


if __name__ == "__main__":
    main()
