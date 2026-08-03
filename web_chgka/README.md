# CHGKA Web

## Документация

- [`AGENTS.md`](AGENTS.md) — правила и технические границы для coding agents.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — устройство приложения и runtime-контракты.
- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — актуальная точка продолжения, проверки и известные проблемы.
- [`ROADMAP.md`](ROADMAP.md) — приоритетный backlog и workflow задач.

## Запуск через Docker

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

## Локальный запуск

### Backend

Из каталога `web_chgka/backend`:

```bash
pip install -r requirements.txt
export QUESTIONS_PACK_PATH="/home/kolesov93/Programming/chgka2/web_chgka/fixtures/sample_questions"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

Из каталога `web_chgka/frontend`:

```bash
npm install
npm run dev
```

После запуска:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

## Примечания

- `QUESTIONS_PACK_PATH` обязателен для backend.
- Пароль админа по умолчанию: `admin123`, если не задан `ADMIN_PASSWORD`.
