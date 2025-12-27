<<<<<<< Updated upstream
Avito CRM (локальный проект)

Кратко
- **Назначение:** Система для интеграции с Avito (парсинг, бот/мессенджер, обработка заявок, синхронизация объявлений и статистики) — backend на Flask + frontend статические файлы.
- **Статус:** Репозиторий содержит серверную часть в `backend/`, статические ресурсы в `frontend/` и вспомогательные скрипты для локального запуска и деплоя.

**Технологии:**
- **Backend:** Python 3.10+ (Flask, SQLAlchemy, Redis, RQ)
- **Frontend:** статические JS/CSS (сборка через `esbuild` в `package.json`)
- **Хранилище/кеш:** Postgres/MySQL (через SQLAlchemy), Redis для кэша и очередей
- **Очереди/таски:** `rq`, `rq-scheduler`

**Зависимости (основные):**
- **Python:** перечислены в `backend/requirements.txt` (flask, requests, beautifulsoup4, redis, pandas, sqlalchemy, marshmallow, pytest и др.)
- **Node/dev:** `esbuild` для сборки фронтенда (описан в `package.json`)

Устройство репозитория (основное)
- **`backend/`**: сервер Flask, API, сервисы, задачи синхронизации
- **`frontend/`**: статические файлы (js/css), сборка
- **`data/`**: примеры данных / fixtures
- Скрипты запуска: `run_local.py`, `run_local.sh`, `run_local.bat`, `start.sh`, `stop.sh`, `start_auto_sync.sh`, `start_sync_forever.sh` и пр.

Переменные окружения
- Шаблон переменных приведён в `backend/env.sample`. Важные переменные:
  - `AVITO_APPLY_SECRET`, `AVITO_JOB_CLIENT_ID`, `AVITO_JOB_CLIENT_SECRET`
  - `AVITO_APPLY_WEBHOOK_URL`, `AVITO_WEBHOOK_URL`, `AVITO_WEBHOOK_TYPES`
  - `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `USE_SQLALCHEMY`
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
  - `FLASK_DEBUG`, `FLASK_PORT`, `SECRET_KEY`

Установка и запуск (локально)
- Рекомендуется создать виртуальное окружение и установить зависимости:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix
source .venv/bin/activate
pip install -r backend/requirements.txt
```

- Настройте `.env` или экспортируйте переменные окружения на основе `backend/env.sample`.

- Запуск сервера (варианты):
  - Python-скрипт локально:

```bash
python run_local.py
```

  - Через shell-скрипт (Unix):

```bash
./run_local.sh
```

  - Для Windows (батник):

```powershell
.\run_local.bat
```

- Сборка фронтенда (если нужно):

```bash
npm install
npm run build
# или
node build.js
```

Работа очередей и синхронизации
- Для фоновых задач используется Redis + RQ.
- Скрипты управления синхронизацией:
  - `start_auto_sync.sh`, `stop_auto_sync.sh` — автозапуск синхронизации
  - `start_sync_forever.sh`, `stop_sync.sh` — постоянная синхронизация

Тесты
- В проекте есть тесты на `pytest` (папка `backend/tests/` / `tests/`).
- Запуск тестов:

```bash
pytest -q
```

Конфигурация БД
- Поддерживается использование SQLAlchemy (см. `backend/database/`), конфигурация подключения задаётся через переменные окружения (файл `backend/env.sample`).

Архитектурные примечания
- Основная логика разбита по слоям: routes -> services -> utils/helpers.
- Пул подключений к БД и использование Redis для кэширования минимизируют нагрузку при массовой синхронизации объявлений.

Файлы и важные точки входа
- Сервер: [backend/app.py](backend/app.py)
- Конфигурация: [backend/config.py](backend/config.py)
- Скрипты сборки: [package.json](package.json), [build.js](build.js)
- Переменные окружения: [backend/env.sample](backend/env.sample)



Деплой (кратко)
- Предпочтительно: systemd service / Docker / WSGI (например, Passenger или Gunicorn + Nginx) — в репозитории есть `passenger_wsgi.py` и скрипты `start.sh` для управления.
- Для продакшна: включите переменные окружения, используйте надежный брокер Redis и реляционную БД (резервные копии в `database_backups/`).

Безопасность
- Никогда не храните секреты в репозитории — используйте провайдер секретов или переменные окружения.
- Ограничьте доступ к webhook-эндпойнтам по IP/подписи (используйте `AVITO_APPLY_SECRET`).

=======
# 🎮 OSAGAMING CRM
>>>>>>> Stashed changes

> Современная система управления взаимоотношениями с клиентами для игрового бизнеса

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)

## 🌟 О проекте

**OSAGAMING CRM** — это полноценная CRM-система для управления клиентской базой в игровом бизнесе. Проект разработан с нуля как современное портфолио full-stack разработчика.

### Основные возможности:
- 🔐 **JWT-авторизация** — безопасный вход в систему
- 💬 **Управление чатами** — создание и просмотр чатов с клиентами
- 📊 **Дашборд** — статистика и метрики в реальном времени
- ⚙️ **Настройки** — управление профилем пользователя
- 🎨 **Современный UI** — адаптивный дизайн на Tailwind CSS

## 🚀 Быстрый старт

### Предварительные требования:
- Python 3.8+
- Node.js 16+
- npm или yarn

### Запуск проекта

**1. Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd osagaming-crm
```

**2. Запустите backend:**
```bash
cd backend
pip install -r requirements.txt
python main_simple.py
```
Backend будет доступен по адресу: http://localhost:8000

**3. Запустите frontend (в отдельном терминале):**
```bash
cd frontend
npm install
npm run dev
```
Frontend будет доступен по адресу: http://localhost:3000 (режим разработки)

**4. Запуск в Docker (production):**
```bash
docker-compose up --build
```
Приложение будет доступно по адресу: http://localhost:8000

### Тестовые данные для входа:
```
Email: admin@osagaming.com
Пароль: admin123
```

## 📁 Структура проекта

```
osagaming-crm/
├── backend/
│   ├── main_simple.py      # FastAPI приложение
│   ├── requirements.txt    # Python зависимости
│   └── crm.db             # SQLite база данных
├── frontend/
│   ├── src/
│   │   ├── pages/         # Страницы приложения
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ChatsPage.tsx
│   │   │   ├── ChatDetailPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── AnalyticsPage.tsx
│   │   ├── components/    # Переиспользуемые компоненты
│   │   │   └── Layout.tsx
│   │   ├── services/      # API клиенты
│   │   │   └── api.ts
│   │   ├── store/         # Глобальное состояние
│   │   │   └── authStore.ts
│   │   ├── App.tsx        # Главный компонент
│   │   ├── main.tsx       # Точка входа
│   │   └── index.css      # Глобальные стили
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
└── README.md
```

## 🛠️ Технологический стек

### Backend
- **FastAPI** — высокопроизводительный веб-фреймворк
- **SQLAlchemy** — ORM для работы с базой данных
- **Pydantic** — валидация данных
- **JWT** — аутентификация
- **SQLite** — встроенная база данных

### Frontend  
- **React 18** — библиотека для создания UI
- **TypeScript** — типизированный JavaScript
- **Vite** — быстрый инструмент сборки
- **Tailwind CSS** — utility-first CSS фреймворк
- **Zustand** — управление состоянием
- **React Query** — управление серверным состоянием
- **React Router** — маршрутизация

## 📚 API Endpoints

### Аутентификация
- `POST /api/auth/login` — вход в систему
- `POST /api/auth/register` — регистрация
- `GET /api/auth/me` — информация о текущем пользователе

### Чаты
- `GET /api/chats` — список всех чатов
- `POST /api/chats` — создание нового чата
- `GET /api/chats/{id}` — детали чата
- `DELETE /api/chats/{id}` — удаление чата

### Сообщения
- `GET /api/chats/{chat_id}/messages` — сообщения в чате
- `POST /api/chats/{chat_id}/messages` — отправка сообщения

### Пользователи
- `GET /api/users` — список пользователей
- `PUT /api/users/me` — обновление профиля

### Статистика
- `GET /api/analytics/dashboard` — данные для дашборда

## 📖 Документация

После запуска backend доступна интерактивная документация API:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Подробное руководство пользователя: [USER_GUIDE.md](USER_GUIDE.md)

## 🎯 Цель проекта

Этот проект демонстрирует навыки:
- **Backend** — FastAPI, SQLAlchemy, асинхронное программирование
- **Frontend** — React, TypeScript, современные практики
- **Базы данных** — проектирование, миграции, оптимизация
- **Архитектура** — чистый код, модульность, масштабируемость
- **UI/UX** — адаптивный дизайн, accessibility

## 📝 Лицензия

MIT License

---

**Разработано с ❤️ как портфолио full-stack разработчика**