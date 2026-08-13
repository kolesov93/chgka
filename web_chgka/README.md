# CHGKA Web

## Документация

- [`AGENTS.md`](AGENTS.md) — правила и технические границы для coding agents.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — устройство приложения и runtime-контракты.
- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — актуальная точка продолжения, проверки и известные проблемы.
- [`docs/QUESTION_PACKS.md`](docs/QUESTION_PACKS.md) — формат пака вопросов, медиа и команда валидации.
- [`ROADMAP.md`](ROADMAP.md) — приоритетный backlog и workflow задач.

## Запуск через Docker (только разработка)

Из каталога `web_chgka`:

```bash
docker compose up --build
```

После запуска:

- игроки: `http://localhost:5173/play`
- ведущий: `http://localhost:5173/admin`
- история игр: `http://localhost:5173/admin/history`
- корневой `http://localhost:5173/` перенаправляет на player-entrypoint
- backend: `http://localhost:8000`

Что уже настроено в `docker-compose.yml`:

- backend получает `QUESTIONS_PACK_PATH=/fixtures/sample_questions`
- backend явно работает с `CHGKA_ENV=development`, паролем `admin123` и разрешёнными frontend-origin `http://localhost:5173` и `http://localhost:4173`; второй нужен только для локального smoke production-like сборки
- папка `./fixtures` примонтирована в контейнер как `/fixtures`
- SQLite-журнал хранится на хосте в `./runtime-data/chgka.sqlite3` и переживает пересоздание backend-контейнера
- исходники примонтированы в контейнеры, backend работает с `--reload`, frontend запускает Vite dev server

Compose и Dockerfile пока не являются production-конфигурацией: в них нет reverse proxy, TLS и production frontend server.

## Локальный запуск

### Backend

Из каталога `web_chgka/backend`:

```bash
pip install -r requirements-dev.txt
export CHGKA_ENV=development
export QUESTIONS_PACK_PATH="/home/kolesov93/Programming/chgka2/web_chgka/fixtures/sample_questions"
export ADMIN_PASSWORD=admin123
export ALLOWED_ORIGINS=http://localhost:5173
export CHGKA_DB_PATH="/home/kolesov93/Programming/chgka2/web_chgka/runtime-data/chgka.sqlite3"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Проверка backend:

```bash
python3 -m pytest -q
```

Проверка пака вопросов до запуска backend:

```bash
python3 -m validate_pack /path/to/pack
```

Для старого пака без обязательных UUID сначала выполните
`python3 -m assign_question_ids /path/to/pack`, сохраните изменённые
`question.md`, а затем запустите валидатор. Подробности формата — в
[`docs/QUESTION_PACKS.md`](docs/QUESTION_PACKS.md).

### Frontend

Из каталога `web_chgka/frontend`:

```bash
npm ci
npm run dev
```

Проверка frontend:

```bash
npm test
npm run build
```

После запуска:

- игроки: `http://localhost:5173/play`
- ведущий: `http://localhost:5173/admin`
- история игр: `http://localhost:5173/admin/history`
- корневой `http://localhost:5173/` перенаправляет на player-entrypoint
- backend: `http://localhost:8000`

### Локальная проверка сборки под URL-префиксом

Обычная development-сборка работает от `/`. Чтобы проверить будущую публикацию на
`https://example.com/chgka/`, при уже запущенном backend из `frontend/` выполнить:

```bash
VITE_BASE_PATH=/chgka/ npm run build
VITE_BASE_PATH=/chgka/ npm run preview -- --host 0.0.0.0
```

После этого доступны `http://localhost:4173/chgka/play`,
`http://localhost:4173/chgka/admin` и
`http://localhost:4173/chgka/admin/history`. Preview проксирует
`/chgka/socket.io`, `/chgka/media` и `/chgka/intro` в локальный backend на
порту `8000`, снимая только внешний префикс `/chgka`. Это средство smoke,
а не production-сервер.

## Примечания

- Backend требует явные `CHGKA_ENV`, `QUESTIONS_PACK_PATH`, `ADMIN_PASSWORD`, `ALLOWED_ORIGINS` и `CHGKA_DB_PATH`; встроенных значений пароля, origins или пути базы нет.
- `--reload` следит за исходниками и перезапускает development-процесс Uvicorn после изменений. В production этот флаг не используется.
- Production допускает только `CHGKA_ENV=production`, пароль длиной не менее 12 символов (не `admin123`) и точные HTTPS origins. Пример полного набора переменных есть в [`.env.example`](.env.example); сам backend `.env`-файлы не загружает.
- В production `CHGKA_DB_PATH` должен быть абсолютным путём на durable volume. SQLite хранит историю, но не восстанавливает текущий `AppState`, игроков или токены после рестарта.
- `ADMIN_TOKEN_TTL_SECONDS` необязателен: по умолчанию admin-сессия действует 12 часов без продления при reconnect; допустимый диапазон — от 60 секунд до 24 часов.
- `/play` восстанавливает только player token, а `/admin` и `/admin/history` — только admin token. История не отображается на экранах запуска/ведения игры и доступна отдельной страницей после той же авторизации ведущего. Разделение форм улучшает UX, но не является границей безопасности: backend по-прежнему проверяет пароль, роль и токен для каждой привилегированной операции.
- Прямое открытие и refresh `/play`, `/admin` и `/admin/history` работают в Vite development/preview. При `VITE_BASE_PATH=/chgka/` те же entrypoints находятся под `/chgka`; production frontend server/reverse proxy должен использовать SPA fallback внутри выбранного base path.

## Диагностика CORS локально

Автоматические тесты проверяют разрешённый и запрещённый origins для FastAPI и Socket.IO. Если нужно диагностировать конкретный локальный запуск, публичный адрес не нужен: разрешённый frontend-origin возвращает заголовок `Access-Control-Allow-Origin`:

```bash
curl -i -X OPTIONS http://localhost:8000/ \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: GET'
```

Для незаявленного origin тот же preflight-запрос отклоняется без разрешающего заголовка:

```bash
curl -i -X OPTIONS http://localhost:8000/ \
  -H 'Origin: http://localhost:5174' \
  -H 'Access-Control-Request-Method: GET'
```

Та же allowlist применяется к Socket.IO/WebSocket handshake. В development frontend подключается к `ws://localhost:8000`; за HTTPS reverse proxy production-соединение должно стать защищённым `wss://` на текущем origin.
