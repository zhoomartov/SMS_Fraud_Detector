"""Telegram-бот для проверки SMS. Токен задаётся через TELEGRAM_BOT_TOKEN."""
import logging
import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.detector import check
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

RISK_VIEW = {
    "low": ("🟢 НИЗКИЙ РИСК", "Явных признаков мошенничества не обнаружено."),
    "medium": ("🟡 СРЕДНИЙ РИСК", "Сообщение требует осторожности."),
    "high": ("🔴 ВЫСОКИЙ РИСК", "Вероятно мошенническое сообщение!"),
}


def format_result(result: dict) -> str:
    title, summary = RISK_VIEW[result["risk"]]
    lines = [title, f"Оценка риска: {result['score']}/100", "", summary]
    reasons = result.get("reasons") or []
    if reasons:
        lines += ["", "Причины:"] + [f"• {reason}" for reason in reasons[:8]]
    domains = result.get("domains") or []
    if domains:
        lines += ["", "Домены:"]
        for item in domains:
            status = "официальный" if item["official"] else "не входит в белый список"
            if item.get("impersonation"):
                status += ", возможная имитация бренда"
            lines.append(f"• {item['domain']} — {status}")
    if result.get("recommendation"):
        lines += ["", "Что делать:", result["recommendation"]]
    lines += ["", "⚠️ Не сообщайте никому SMS-коды, PIN и пароли. Бот не открывает ссылки."]
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🛡️ SMS Fraud Detector\n\n"
        "Отправьте мне текст SMS, и я оценю риск мошенничества. "
        "Поддерживаются русский, кыргызский и смешанный текст.\n\n"
        "Команды: /start — начало, /help — помощь."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Перешлите или вставьте текст SMS обычным сообщением.\n"
        "Я верну уровень риска, оценку 0–100, причины и рекомендацию.\n"
        "Ссылки не открываются; официальный список доменов используется только для проверки имени домена."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    text = (message.text or "").strip()
    if not text:
        await message.reply_text("Пришлите текст SMS.")
        return
    if len(text) > 5000:
        await message.reply_text("Сообщение слишком длинное. Максимум — 5000 символов.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        result = check(text)
        await message.reply_text(format_result(result))
    except Exception:
        logger.exception("Ошибка проверки SMS")
        await message.reply_text("Не удалось проверить сообщение. Попробуйте позже.")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Не задан TELEGRAM_BOT_TOKEN. Создайте бота через BotFather и задайте токен в окружении.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("SMS Fraud Telegram bot запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
