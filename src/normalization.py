"""Нормализация SMS. Код перенесён из ноутбука sms_fraud_model.ipynb без изменений логики."""
import re
import unicodedata

# Защищённые слова
PROTECTED_WORDS = {
    "sim", "sms", "url", "pin",
    "megacom", "beeline", "mbank", "kicb"
}

# Кириллические символы, похожие на латинские
CYRILLIC_TO_LATIN = str.maketrans({
    "а": "a", "с": "c", "е": "e",
    "о": "o", "р": "p", "х": "x",
    "у": "y", "к": "k", "м": "m",
    "т": "t", "в": "b", "н": "h"
})

# Замена цифр и символов в кириллических словах
CYRILLIC_OBFUSCATION = str.maketrans({
    "0": "о", "3": "з", "4": "ч",
    "6": "б", "@": "а", "$": "с"
})


def normalize_word(word: str) -> str:

    if word in PROTECTED_WORDS:
        return word

    has_latin = bool(re.search(r"[a-z]", word))
    has_cyrillic = bool(re.search(r"[а-яёөүң]", word))

    if has_latin:
        word = word.translate(CYRILLIC_TO_LATIN)
        word = word.replace("@", "a")
        word = word.replace("3", "e")
        word = word.replace("1", "i")

    elif has_cyrillic:
        word = word.translate(CYRILLIC_OBFUSCATION)

    return word


def normalize_text(text: str) -> str:

    if not isinstance(text, str):
        return ""

    text = unicodedata.normalize("NFKC", text).lower()

    # Сохраняем ссылки
    urls = []

    def save_url(match):
        urls.append(match.group(0))
        return f" URLTOKEN{len(urls) - 1}END "

    text = re.sub(
        r"(?:https?://|www\.)[^\s]+",
        save_url,
        text
    )

    # Сохраняем домены
    domains = []

    def save_domain(match):
        domains.append(match.group(0))
        return f" DOMAINTOKEN{len(domains) - 1}END "

    text = re.sub(
        r"(?<![\w@])(?:[a-z0-9-]+\.)+[a-z]{2,}(?![\w-])",
        save_domain,
        text
    )

    # Сохраняем телефонные номера
    phones = []

    def save_phone(match):
        phones.append(match.group(0))
        return f" PHONETOKEN{len(phones) - 1}END "

    text = re.sub(
        r"(?<!\w)(?:\+?\d[\d\s()\-]{6,}\d)(?!\w)",
        save_phone,
        text
    )

    # Убираем разделители внутри слов
    text = re.sub(
        r"(?<=[а-яёөүңa-z])[._*]+(?=[а-яёөүңa-z])",
        "",
        text
    )

    text = re.sub(
        r"\b(sim|sms|url|pin)-(?=[а-яёөүң])",
        r"\1 ",
        text
    )

    text = re.sub(
        r"(?<=[а-яёөүңa-z])-(?=[а-яёөүңa-z])",
        "",
        text
    )

    # Объединяем раздельные буквы
    text = re.sub(
        r"(?<!\S)(?:[а-яёөүңa-z]\s+){2,}[а-яёөүңa-z](?=\s+[а-яёөүңa-z]{2,}|[^\w\s]|$)",
        lambda m: re.sub(r"\s+", "", m.group(0)),
        text
    )

    # Исправляем написание слов
    def fix_word(match):
        word = match.group(0)

        if word in PROTECTED_WORDS:
            return word

        return normalize_word(word)

    text = re.sub(
        r"[а-яёөүңa-z0-9@$]+",
        fix_word,
        text
    )

    # Возвращаем ссылки
    for i, url in enumerate(urls):
        text = text.replace(f"URLTOKEN{i}END", url)

    # Возвращаем домены
    for i, domain in enumerate(domains):
        text = text.replace(f"DOMAINTOKEN{i}END", domain)

    # Возвращаем телефоны
    for i, phone in enumerate(phones):
        text = text.replace(f"PHONETOKEN{i}END", phone)

    text = re.sub(r"\s+", " ", text).strip()

    return text
