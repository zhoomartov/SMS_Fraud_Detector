"""check(text): скоринг, уровень риска, причины и проверка доменов."""
import re
from urllib.parse import urlparse

from src.features import extract_features
from src.model import fraud_probabilities

OFFICIAL_DOMAINS = ("beeline.kg", "balance.kg", "nbkr.kg", "mbank.kg")
BRAND_LABELS = ("beeline", "balance", "nbkr", "mbank")

URL_RE = re.compile(r"(?:https?://|www\.)[^\s]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"(?<![\w@.])(?:[a-z0-9-]+\.)+[a-z]{2,}(?![\w@-])")

# Сильные признаки показываем всегда, слабые — только при заметном риске
STRONG_REASONS = {
    "asks_code_password": "Просьба сообщить код или пароль",
    "urgency": "Давление срочностью",
    "blocking_threat": "Угроза блокировки",
    "prize": "Обещание выигрыша, приза или бонуса",
    "money_transfer": "Просьба перевести деньги",
    "callback_request": "Просьба перезвонить",
    "send_request": "Просьба отправить, ввести или подтвердить данные",
    "link_action": "Призыв перейти по ссылке",
}
WEAK_REASONS = {
    "has_url": "В сообщении есть ссылка или домен",
    "bank_operator": "Упоминается банк или оператор связи",
    "account_card": "Упоминается счёт, карта, аккаунт или пароль",
}

RECOMMENDATIONS = {
    "high": "Не сообщайте коды из SMS и не переходите по подозрительным ссылкам. "
            "Свяжитесь с банком или оператором по официальному номеру.",
    "medium": "Будьте осторожны: проверьте отправителя и не вводите личные данные, "
              "пока не убедитесь, что сообщение настоящее.",
    "low": "Явных признаков мошенничества не найдено. Всё равно никому не сообщайте "
           "коды и пароли из SMS.",
}


def score_to_risk(score: int) -> str:
    if score < 30:
        return "low"
    if score <= 64:
        return "medium"
    return "high"


def is_official_domain(host: str) -> bool:
    host = host.lower().strip(".")
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def extract_hosts(text: str) -> list:
    """Хосты из ссылок и «голых» доменов. Ссылки не открываются."""
    low = text.lower()
    hosts = []
    for m in URL_RE.finditer(low):
        raw = m.group(0).rstrip(".,;:!?)»\"'")
        try:
            host = urlparse(raw if "://" in raw else "//" + raw).hostname
        except ValueError:
            host = None
        if host:
            hosts.append(host.strip("."))
    rest = URL_RE.sub(" ", low)
    hosts += [m.group(0) for m in DOMAIN_RE.finditer(rest)]
    return list(dict.fromkeys(hosts))


def analyze_domains(text: str) -> list:
    result = []
    for host in extract_hosts(text):
        official = is_official_domain(host)
        imitation = (not official) and any(b in host for b in BRAND_LABELS)
        result.append({"domain": host, "official": official, "impersonation": imitation})
    return result


def build_reasons(text: str, score: int, domains: list) -> list:
    feats = extract_features(text)
    reasons = [txt for name, txt in STRONG_REASONS.items() if feats.get(name)]
    if score >= 30:
        reasons += [txt for name, txt in WEAK_REASONS.items() if feats.get(name)]
    for d in domains:
        if d["impersonation"]:
            reasons.append(f"Домен {d['domain']} похож на официальный, но не является им")
        elif not d["official"] and score >= 30:
            reasons.append(f"Ссылка ведёт на неофициальный домен {d['domain']} "
                           "(неизвестный домен сам по себе не доказывает обман)")
    return reasons


def _result(text: str, probability: float) -> dict:
    score = round(float(probability) * 100)
    risk = score_to_risk(score)
    domains = analyze_domains(text)
    return {
        "risk": risk,
        "score": score,
        "reasons": build_reasons(text, score, domains),
        "recommendation": RECOMMENDATIONS[risk],
        "domains": domains,
    }


def _validate(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Текст SMS не должен быть пустым")


def check(text: str) -> dict:
    _validate(text)
    return _result(text, fraud_probabilities([text])[0])


def check_batch(texts) -> list:
    texts = list(texts)
    for i, t in enumerate(texts):
        try:
            _validate(t)
        except ValueError:
            raise ValueError(f"Пустой текст в позиции {i}") from None
    if not texts:
        return []
    probs = fraud_probabilities(texts)
    return [_result(t, p) for t, p in zip(texts, probs)]
