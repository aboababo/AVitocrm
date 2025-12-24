#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для локального запуска Flask приложения
Поддерживает Windows, Linux и macOS
"""

import os
import subprocess
import sys
from pathlib import Path

# Настройка кодировки UTF-8 для консоли Windows (важно делать ДО любых импортов/выводов)
if sys.platform == "win32":
    try:
        # Устанавливаем кодовую страницу UTF-8 в консоли Windows
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # CP_UTF8 = 65001
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass  # Если не удалось, продолжим

# Настройка кодировки для stdout/stderr
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        # Для Python < 3.7 или если reconfigure не поддерживается
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        import io

        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# Цвета для вывода (работают в большинстве терминалов)
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


# Для Windows без поддержки ANSI
if sys.platform == "win32":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        # Если не получилось, просто отключаем цвета
        class Colors:
            GREEN = YELLOW = RED = BLUE = CYAN = RESET = BOLD = ""


def print_colored(text, color=Colors.RESET):
    """Вывод цветного текста"""
    print(f"{color}{text}{Colors.RESET}")


def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 9):
        print_colored("❌ Требуется Python 3.9 или выше", Colors.RED)
        print_colored(f"   Текущая версия: {sys.version}", Colors.YELLOW)
        return False
    return True


def check_dependencies():
    """Проверка установленных зависимостей"""
    try:
        import flask

        return True
    except ImportError:
        print_colored("❌ Flask не установлен", Colors.RED)
        print_colored(
            "   Установите зависимости: pip install -r backend/requirements.txt",
            Colors.YELLOW,
        )
        return False


def install_dependencies():
    """Установка зависимостей"""
    print_colored("📦 Установка зависимостей...", Colors.BLUE)
    requirements_file = Path("backend/requirements.txt")

    if not requirements_file.exists():
        print_colored("❌ Файл requirements.txt не найден", Colors.RED)
        return False

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        print_colored("✅ Зависимости установлены", Colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        print_colored("❌ Ошибка при установке зависимостей", Colors.RED)
        return False


def check_env_file():
    """Проверка наличия .env файла"""
    env_file = Path(".env")
    env_sample = Path("backend/env.sample")

    if not env_file.exists():
        print_colored("⚠️  Файл .env не найден", Colors.YELLOW)
        if env_sample.exists():
            print_colored("   Создайте .env на основе backend/env.sample", Colors.YELLOW)
            print_colored("   Или запустите с --skip-env для пропуска проверки", Colors.YELLOW)
            return False
    return True


def setup_environment():
    """Настройка переменных окружения"""
    # Устанавливаем переменные по умолчанию для разработки
    os.environ.setdefault("FLASK_DEBUG", "True")
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ.setdefault("FLASK_PORT", "5000")

    # Загружаем .env если есть python-dotenv
    try:
        from dotenv import load_dotenv  # type: ignore

        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            print_colored("✅ Загружен .env файл", Colors.GREEN)
        else:
            print_colored(
                "⚠️  .env файл не найден, используются значения по умолчанию",
                Colors.YELLOW,
            )
    except ImportError:
        print_colored("⚠️  python-dotenv не установлен, .env не будет загружен", Colors.YELLOW)


def run_flask_app():
    """Запуск Flask приложения"""
    backend_dir = Path("backend")

    if not backend_dir.exists():
        print_colored("❌ Директория backend не найдена", Colors.RED)
        return False

    # Переходим в директорию backend
    os.chdir(backend_dir)

    # Импортируем и запускаем приложение
    try:
        print_colored("\n🚀 Запуск Flask приложения...", Colors.CYAN)
        print_colored("=" * 50, Colors.CYAN)
        print_colored(
            f"📍 URL: http://localhost:{os.environ.get('FLASK_PORT', '5000')}",
            Colors.GREEN,
        )
        print_colored(f"🔧 Debug: {os.environ.get('FLASK_DEBUG', 'True')}", Colors.GREEN)
        print_colored("=" * 50, Colors.CYAN)
        print_colored("💡 Нажмите Ctrl+C для остановки\n", Colors.YELLOW)

        # Импортируем приложение
        from app import app  # type: ignore

        # Получаем порт из переменной окружения
        port = int(os.environ.get("FLASK_PORT", 5000))
        debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

        # Запускаем приложение
        app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=True)
    except KeyboardInterrupt:
        print_colored("\n\n👋 Остановка сервера...", Colors.YELLOW)
        return True
    except Exception as e:
        print_colored(f"\n❌ Ошибка при запуске: {e}", Colors.RED)
        import traceback

        traceback.print_exc()
        return False


def main():
    """Главная функция"""
    print_colored("=" * 50, Colors.CYAN)
    print_colored("🚀 OSAGAMING CRM - Локальный запуск", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 50, Colors.CYAN)

    # Парсинг аргументов
    skip_env = "--skip-env" in sys.argv
    install_deps = "--install" in sys.argv or "-i" in sys.argv

    # Проверки
    if not check_python_version():
        sys.exit(1)

    if install_deps:
        if not install_dependencies():
            sys.exit(1)

    if not check_dependencies():
        print_colored(
            "\n💡 Запустите с флагом --install для автоматической установки",
            Colors.YELLOW,
        )
        response = input("Установить зависимости сейчас? (y/n): ").lower()
        if response == "y":
            if not install_dependencies():
                sys.exit(1)
        else:
            sys.exit(1)

    if not skip_env:
        if not check_env_file():
            response = input("Продолжить без .env файла? (y/n): ").lower()
            if response != "y":
                sys.exit(1)

    # Настройка окружения
    setup_environment()

    # Запуск приложения
    success = run_flask_app()

    if success:
        print_colored("\n✅ Сервер остановлен", Colors.GREEN)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
