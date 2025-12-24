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


