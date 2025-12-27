@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ===============================================
echo     🔧 OSAGAMING CRM - Developer Tools
echo ===============================================
echo.

:MENU
echo Выберите действие:
echo.
echo 1. 🚀 Запустить CRM (Docker)
echo 2. ⚡ Запустить в режиме разработки
echo 3. 🛑 Остановить все сервисы
echo 4. 📊 Посмотреть логи
echo 5. 🗄️ Сбросить базу данных
echo 6. 🔄 Пересобрать контейнеры
echo 7. 📋 Показать статус сервисов
echo 8. 🧪 Запустить тесты
echo 9. 📚 Открыть документацию
echo 0. ❌ Выход
echo.
set /p choice="Введите номер (0-9): "

if "%choice%"=="1" goto START_DOCKER
if "%choice%"=="2" goto START_DEV
if "%choice%"=="3" goto STOP_SERVICES
if "%choice%"=="4" goto VIEW_LOGS
if "%choice%"=="5" goto RESET_DB
if "%choice%"=="6" goto REBUILD
if "%choice%"=="7" goto STATUS
if "%choice%"=="8" goto RUN_TESTS
if "%choice%"=="9" goto OPEN_DOCS
if "%choice%"=="0" goto EXIT
goto MENU

:START_DOCKER
echo.
echo 🚀 Запуск OSAGAMING CRM через Docker...
echo.
docker-compose down --remove-orphans
docker-compose up -d

echo.
echo ⏳ Ожидание запуска сервисов...
timeout /t 15 /nobreak >nul

echo.
echo ✅ CRM запущен!
echo.
echo 🌐 URLs:
echo    Frontend: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo 🔑 Логин: admin@osagaming.com / password
echo.

set /p open="Открыть в браузере? (y/n): "
if /i "!open!"=="y" start http://localhost:8000

pause
goto MENU

:START_DEV
echo.
echo ⚡ Запуск в режиме разработки...
echo.

REM Проверяем Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден! Установите Python 3.8+
    pause
    goto MENU
)

REM Проверяем Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js не найден! Установите Node.js 16+
    pause
    goto MENU
)

echo.
echo 🛠️ Настройка backend...
cd backend
if not exist venv (
    python -m venv venv
    echo ✅ Виртуальная среда создана
)

call venv\Scripts\activate
pip install -r requirements.txt >nul 2>&1

echo 🛠️ Настройка frontend...
cd ..\frontend
npm install >nul 2>&1

echo.
echo 🚀 Запуск серверов разработки...
echo Backend будет доступен на http://localhost:8000
echo Frontend будет доступен на http://localhost:3000
echo.
echo Нажмите Ctrl+C для остановки серверов
echo.

REM Запускаем backend в фоне
start "Backend Dev Server" cmd /k "cd backend && call venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Ожидаем немного для запуска backend
timeout /t 5 /nobreak >nul

REM Запускаем frontend
npm run dev

goto MENU

:STOP_SERVICES
echo.
echo 🛑 Остановка всех сервисов...
docker-compose down --remove-orphans

REM Останавливаем Python процессы на портах 8000 и 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000"') do taskkill /PID %%a /F >nul 2>&1

echo ✅ Все сервисы остановлены
pause
goto MENU

:VIEW_LOGS
echo.
echo 📊 Логи сервисов:
echo.
echo 1. Все сервисы
echo 2. Backend
echo 3. Frontend
echo 4. База данных
echo.
set /p log_choice="Выберите (1-4): "

if "%log_choice%"=="1" (
    docker-compose logs -f
) else if "%log_choice%"=="2" (
    docker-compose logs -f backend
) else if "%log_choice%"=="3" (
    docker-compose logs -f frontend
) else if "%log_choice%"=="4" (
    docker-compose logs -f postgres
) else (
    goto VIEW_LOGS
)
goto MENU

:RESET_DB
echo.
echo ⚠️ ВНИМАНИЕ: Это удалит все данные!
set /p confirm="Продолжить? (yes/no): "
if /i not "%confirm%"=="yes" goto MENU

echo.
echo 🗄️ Сброс базы данных...
docker-compose down
docker volume rm osagaming-crm_crm_data 2>nul
docker-compose up -d
echo ✅ База данных сброшена и пересоздана
pause
goto MENU

:REBUILD
echo.
echo 🔄 Пересборка контейнеров...
docker-compose down
docker-compose build --no-cache
docker-compose up -d
echo ✅ Контейнеры пересобраны и запущены
pause
goto MENU

:STATUS
echo.
echo 📋 Статус сервисов:
echo.
docker-compose ps
echo.
echo 💾 Использование диска:
docker system df
echo.
pause
goto MENU

:RUN_TESTS
echo.
echo 🧪 Запуск тестов...
echo.

echo Backend тесты:
cd backend
if exist venv (
    call venv\Scripts\activate
    if exist requirements.txt (
        pip install -r requirements.txt >nul 2>&1
        pytest tests/ -v --tb=short 2>nul || echo ⚠️ Тесты backend не найдены или не настроены
    ) else (
        echo ⚠️ requirements.txt не найден
    )
) else (
    echo ⚠️ Виртуальная среда не найдена
)

echo.
echo Frontend тесты:
cd ..\frontend
if exist package.json (
    npm test -- --watchAll=false --coverage 2>nul || echo ⚠️ Тесты frontend не найдены или не настроены
) else (
    echo ⚠️ package.json не найден
)

pause
goto MENU

:OPEN_DOCS
echo.
echo 📚 Открытие документации...
echo.
echo 1. API документация (Swagger)
echo 2. React компоненты
echo 3. README файл
echo 4. GitHub репозиторий
echo.
set /p doc_choice="Выберите (1-4): "

if "%doc_choice%"=="1" (
    start http://localhost:8000/docs
) else if "%doc_choice%"=="2" (
    explorer frontend\src\components
) else if "%doc_choice%"=="3" (
    explorer README.md
) else if "%doc_choice%"=="4" (
    start https://github.com
) else (
    goto OPEN_DOCS
)
goto MENU

:EXIT
echo.
echo 👋 До свидания!
timeout /t 2 >nul
exit /b 0

:INVALID_CHOICE
echo.
echo ❌ Неверный выбор. Попробуйте снова.
pause
goto MENU