#!/bin/bash
# Скрипт для локального запуска Flask приложения на Linux/macOS
# Запуск: bash run_local.sh или ./run_local.sh

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================"
echo -e "  OSAGAMING CRM - Локальный запуск"
echo -e "================================================${NC}"
echo

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден. Установите Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python найден: $PYTHON_VERSION${NC}"

# Проверка версии Python
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo -e "${RED}❌ Требуется Python 3.9 или выше${NC}"
    exit 1
fi

echo

# Проверка зависимостей
if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Flask не установлен${NC}"
    echo
    read -p "Установить зависимости? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}📦 Установка зависимостей...${NC}"
        pip3 install -r backend/requirements.txt
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Ошибка при установке зависимостей${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Зависимости установлены${NC}"
    else
        echo -e "${RED}❌ Установка отменена${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Зависимости установлены${NC}"
fi

echo

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден${NC}"
    if [ -f "backend/env.sample" ]; then
        echo -e "${YELLOW}   Создайте .env на основе backend/env.sample${NC}"
    fi
    read -p "Продолжить без .env файла? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo
echo -e "${CYAN}================================================"
echo -e "  Запуск Flask приложения..."
echo -e "================================================${NC}"
echo
echo -e "${GREEN}📍 URL: http://localhost:5000${NC}"
echo -e "${GREEN}🔧 Debug: включен${NC}"
echo
echo -e "${YELLOW}💡 Нажмите Ctrl+C для остановки${NC}"
echo

# Переход в директорию backend и запуск
cd backend
python3 app.py

