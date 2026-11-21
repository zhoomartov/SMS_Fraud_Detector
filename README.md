# SMS Fraud Detector

Определяет мошеннические SMS на русском и кыргызском языках (в том числе с обфускацией: цифры вместо букв,
пробелы и точки внутри слов, латиница вместо кириллицы).
Используется ваша обученная в Google Colab модель `models/sms_fraud_model.pkl`:
Pipeline(FeatureUnion[char TF-IDF, word TF-IDF, 11 числовых признаков] → LogisticRegression). Модель не переобучается.

## Структура
```
data/            sms_train.csv, sms_dev.csv (положите сюда свои файлы: столбцы id,text,label; метки fraud/ok)
models/          sms_fraud_model.pkl
src/             normalization.py, features.py, model.py, detector.py  (вся ML-логика)
api.py           FastAPI backend
app.py           Streamlit frontend
evaluate.py      оценка на CSV
tests/           python -m unittest discover -s tests -v
```

## Установка (Ubuntu)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
`scikit-learn` закреплён на 1.6.1: именно в этой версии сохранена модель. С другой версией sklearn выдаёт
`InconsistentVersionWarning`.

## Запуск
```bash
uvicorn api:app --reload          # API: http://127.0.0.1:8000  (документация: /docs)
streamlit run app.py              # интерфейс: http://localhost:8501 (в другом терминале)
python evaluate.py                # метрики на data/sms_dev.csv
python evaluate.py --file data/sms_train.csv
```
Если API работает по другому адресу: `SMS_API_URL=http://host:port streamlit run app.py`.

## Оценка риска
`score = round(P(fraud) * 100)`, где P(fraud) берётся из `predict_proba`, индекс класса `fraud` находится по `model.classes_`.

| Уровень | Score |
|---|---|
| low | < 30 |
| medium | 30–64 |
| high | ≥ 65 |

В `evaluate.py` high = fraud, low и medium = ok.
Домены beeline.kg, balance.kg, nbkr.kg, mbank.kg (и их поддомены) считаются официальными. Это дополнительный сигнал
для объяснения результата, на score он не влияет. Ссылки не открываются.

## Совместимость с pkl
Модель была сохранена из ноутбука, и pickle ссылается на `__main__.extract_features_for_model`.
`src/model.py` перед `joblib.load()` регистрирует функцию из `src/features.py` в `__main__`. Загружайте только доверенные pkl.

## API
`GET /health` → `{"status":"ok","model_loaded":true,"classes":["fraud","ok"]}` (503, если модель не загружена)

`POST /check`
```bash
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" \
  -d '{"text": "Ваш аккаунт заблокирован. Отправьте код."}'
```
```json
{"risk":"high","score":89,"reasons":["Угроза блокировки","..."],"recommendation":"...","domains":[]}
```

`POST /check/batch` (до 1000 сообщений)
```bash
curl -X POST http://127.0.0.1:8000/check/batch -H "Content-Type: application/json" \
  -d '{"texts": ["Ваш баланс пополнен.", "Срочно сообщите код из SMS"]}'
```
Пустой текст → HTTP 422, модель не загружена → 503, непредвиденная ошибка → 500.
