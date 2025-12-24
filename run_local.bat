@echo off
REM Скрипт для локального запуска Flask приложения на Windows
REM Запуск: run_local.bat

REM Настройка кодировки UTF-8 для корректного отображения русского текста
chcp 65001 >nul 2>&1

setlocal enabledelayedexpansion

echo ================================================
echo   OSAGAMING CRM - Локальный запуск (Windows)
echo ================================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python 3.9+
    pause
    exit /b 1
)

echo [OK] Python найден
echo.

REM Проверка зависимостей
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Flask не установлен
    echo.
    set /p install="Установить зависимости? (y/n): "
    if /i "!install!"=="y" (
        echo [УСТАНОВКА] Установка зависимостей...
        pip install -r backend\requirements.txt
        if errorlevel 1 (
            echo [ОШИБКА] Не удалось установить зависимости
            pause
            exit /b 1
        )
        echo [OK] Зависимости установлены
    ) else (
        echo [ОТМЕНА] Установка отменена
        pause
        exit /b 1
    )
)

echo.
echo ================================================
echo   Запуск Flask приложения...
echo ================================================
echo.
echo URL: http://localhost:5000
echo Нажмите Ctrl+C для остановки
echo.

REM Переход в директорию backend и запуск
cd backend
python app.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой
    pause
    exit /b 1
)

pause

