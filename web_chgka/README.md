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

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

Что уже настроено в `docker-compose.yml`:

- backend получает `QUESTIONS_PACK_PATH=/fixtures/sample_questions`
- backend явно работает с `CHGKA_ENV=development`, паролем `admin123` и разрешённым frontend-origin `http://localhost:5173`
- папка `./fixtures` примонтирована в контейнер как `/fixtures`
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

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

## Примечания

- Backend требует явные `CHGKA_ENV`, `QUESTIONS_PACK_PATH`, `ADMIN_PASSWORD` и `ALLOWED_ORIGINS`; встроенных значений пароля или origins нет.
- `--reload` следит за исходниками и перезапускает development-процесс Uvicorn после изменений. В production этот флаг не используется.
- Production допускает только `CHGKA_ENV=production`, пароль длиной не менее 12 символов (не `admin123`) и точные HTTPS origins. Пример полного набора переменных есть в [`.env.example`](.env.example); сам backend `.env`-файлы не загружает.
- `ADMIN_TOKEN_TTL_SECONDS` необязателен: по умолчанию admin-сессия действует 12 часов без продления при reconnect; допустимый диапазон — от 60 секунд до 24 часов.

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
