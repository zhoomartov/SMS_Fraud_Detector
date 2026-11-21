import subprocess
import sys
import time
import socket
import os
from dotenv import load_dotenv

# Загружаем настройки из .env
load_dotenv()

processes = []

def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0

try:
    print("🚀 Запуск SMS Fraud Detector...")

    # Проверяем Telegram-токен
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise RuntimeError("TELEGRAM_BOT_TOKEN не найден в файле .env")

    # Проверяем свободные порты
    for port in [8000, 8501]:
        if not port_is_free(port):
            raise RuntimeError(
                f"Порт {port} занят. Освободите порт {port}."
            )

    # 1. FastAPI
    api = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "api:app",
        "--host", "127.0.0.1",
        "--port", "8000"
    ])
    processes.append(api)

    print("⏳ Запуск FastAPI...")

    for _ in range(30):
        if api.poll() is not None:
            raise RuntimeError("FastAPI не запустился.")

        try:
            with socket.create_connection(
                ("127.0.0.1", 8000), timeout=1
            ):
                break
        except OSError:
            time.sleep(1)
    else:
        raise RuntimeError("Время ожидания FastAPI истекло.")

    print("✅ FastAPI: http://127.0.0.1:8000")

    # 2. Streamlit
    streamlit = subprocess.Popen([
        sys.executable, "-m", "streamlit",
        "run", "app.py",
        "--server.port", "8501"
    ])
    processes.append(streamlit)

    print("✅ Streamlit: http://localhost:8501")

    # 3. Telegram Bot
    bot = subprocess.Popen([
        sys.executable, "-m", "bot.telegram_bot"
    ])
    processes.append(bot)

    print("✅ Telegram Bot запускается!")

    print("\n" + "=" * 45)
    print("🛡️ SMS FRAUD DETECTOR ЗАПУЩЕН!")
    print("=" * 45)
    print("🌐 Web:      http://localhost:8501")
    print("⚙️ API:      http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("🤖 Telegram: работает в Telegram")
    print("=" * 45)
    print("Для остановки нажмите CTRL+C.")

    while True:
        for name, process in [
            ("FastAPI", api),
            ("Streamlit", streamlit),
            ("Telegram Bot", bot)
        ]:
            if process.poll() is not None:
                raise RuntimeError(
                    f"{name} неожиданно остановился."
                )

        time.sleep(1)

except KeyboardInterrupt:
    print("\n⏹ Остановка всех компонентов...")

except RuntimeError as e:
    print(f"\n❌ Ошибка: {e}")

finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    print("✅ Все компоненты остановлены.")