# CHGKA Web

## Документация

- [`AGENTS.md`](AGENTS.md) — правила и технические границы для coding agents.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — устройство приложения и runtime-контракты.
- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — актуальная точка продолжения, проверки и известные проблемы.
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
- папка `./fixtures` примонтирована в контейнер как `/fixtures`
- исходники примонтированы в контейнеры, backend работает с `--reload`, frontend запускает Vite dev server

Compose и Dockerfile пока не являются production-конфигурацией: в них нет reverse proxy, TLS и production frontend server.

## Локальный запуск

### Backend

Из каталога `web_chgka/backend`:

```bash
pip install -r requirements-dev.txt
export QUESTIONS_PACK_PATH="/home/kolesov93/Programming/chgka2/web_chgka/fixtures/sample_questions"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Проверка backend:

```bash
python -m pytest -q
```

### Frontend

Из каталога `web_chgka/frontend`:

```bash
npm ci
npm run dev
```

Проверка frontend:

```bash
npm run build
```

После запуска:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

## Примечания

- `QUESTIONS_PACK_PATH` обязателен для backend.
- Пароль админа по умолчанию: `admin123`, если не задан `ADMIN_PASSWORD`.
