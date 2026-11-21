"""Признаки SMS. Код перенесён из ноутбука sms_fraud_model.ipynb без изменений логики.

extract_features_for_model должна быть импортируема отсюда: обученный pkl ссылается на неё по имени.
"""
from src.normalization import normalize_text

import re

FEATURE_NAMES = [
    "has_url", "asks_code_password", "urgency", "blocking_threat", "prize",
    "bank_operator", "money_transfer", "callback_request", "send_request",
    "account_card", "link_action",
]

def extract_features(text: str) -> dict:
    text = normalize_text(text)

    features = {
        # 1. Наличие ссылки
        "has_url": int(bool(re.search(
            r"(https?://|www\.|[a-z0-9-]+\.[a-z]{2,})",
            text
        ))),

        # 2. Запрос кода или пароля
        "asks_code_password": int(bool(re.search(
            r"(код|кодду|кодун|парол[ья]|сырсөз|сырсөзүңүз|pin|sms.?код)",
            text
        ))),

        # 3. Срочность
        "urgency": int(bool(re.search(
            r"(срочно|немедленно|быстро|сейчас|тез|дароо|азыр)",
            text
        ))),

        # 4. Угроза блокировки
        "blocking_threat": int(bool(re.search(
            r"(заблокирован|блокировка|блоктолот|блоктолду|бөгөттөлдү|бөгөттөлөт|жабылат|жабылды)",
            text
        ))),

        # 5. Выигрыш или приз
        "prize": int(bool(re.search(
            r"(bonus|бонус|выиграл|выиграли|победител\w*|приз|подарок|байге|уттуңуз|утту|жеңүүчү|утуп алдыңыз)",
            text
        ))),

        # 6. Банк или оператор
        "bank_operator": int(bool(re.search(
            r"(банк|bank|mbank|kicb|рск|оптима|megacom|beeline|элкарт)",
            text
        ))),

        # 7. Перевод денег
        "money_transfer": int(bool(re.search(
            r"(переведите|перевод|отправьте деньги|пополните счет|акча котор|акча жөнөт|акчаңызды)",
            text
        ))),

        # 8. Просьба перезвонить
        "callback_request": int(bool(re.search(
            r"(перезвоните|позвоните|обратитесь по номеру|чалгыла|кайра чалыңыз)",
            text
        ))),

        # 9. Просьба отправить или предоставить информацию
        "send_request": int(bool(re.search(
            r"(отправьте|сообщите|введите|подтвердите|подтвердить|активируйте|активировать|активдештир|aktivdeshtir|aktivirovat|жөнөтүңүз|жибериңиз|жазыңыз|бериңиз|киргизиңиз)",
            text
        ))),

        # 10. Упоминание аккаунта или карты
        "account_card": int(bool(re.search(
            r"(аккаунт|сч[её]т|карта|card|эсебиңиз|эсеп|картаңыз|пароль|парол[ья]|сырсөз|кабинет)",
            text
        ))),

        # 11. Просьба перейти по ссылке
        "link_action": int(bool(re.search(
            r"(перейдите по ссылке|перейти по ссылке|шилтемеге өт|шилтемени бас|ссылка боюнча өт)",
            text
        )))
    }

    return features


def extract_features_for_model(texts):
    return [
        extract_features(text)
        for text in texts
    ]
