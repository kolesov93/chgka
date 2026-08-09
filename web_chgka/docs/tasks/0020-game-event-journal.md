# 0020: Журнал игр и история сыгранных вопросов

Branch: `task/game-event-journal`
Status: In progress

## Goal

Сохранять полный структурированный журнал игровых сессий и автоматически получать из него достоверную историю открытых вопросов, включая отдельные части блица и суперблица.

## Decisions

- SQLite хранит все события, которые сейчас попадают в игровой лог, с типом, JSON payload, UTC timestamp и готовым русским display message. Низкоуровневые Socket.IO transport events не журналируются.
- `game_sessions.mode` — единственный признак `regular|debug`. Обе категории сохраняются; только `regular` участвует в сводной истории. Development по умолчанию создаёт `debug`, production — `regular`.
- Каждый `question.md`, включая родителя и части блица, обязан иметь явный канонический UUID в поле `id`. Fallback fingerprint не поддерживается. Для существующих паков будет отдельная безопасная команда назначения ID.
- Использованной единицей считается конкретный `question_id`, для блица — ID открытой части. Reconnect и повторная отправка состояния не создают событие открытия.
- Сессия начинается как lobby/draft при первом журналируемом событии, отмечается active при фактическом старте, закрывается как completed/reset, а незакрытые сессии прошлого процесса становятся interrupted.
- SQLite находится по `CHGKA_DB_PATH`; development Compose монтирует gitignored host directory в `/data`, production должен использовать persistent volume и backup.
- Ведущий получает admin-only историю: режим текущей/прошлой сессии, список сессий, полный лог, открытые вопросы и агрегированную историю вопросов.
- Запись отвечавших участников остаётся отдельной roadmap-задачей, но будет строиться на этом журнале.

## Consistency boundary

- Авторитетные переходы остаются синхронными и process-local.
- Принятое действие журналируется до Socket.IO broadcasts. Ошибка durable write не должна молча выглядеть для клиентов как успешно завершённое действие.
- `AppState`, игроки и токены по-прежнему не восстанавливаются после рестарта; task сохраняет историю, а не live runtime snapshot.

## Out of scope

- Restart recovery/undo всего `AppState`, удаление истории, награды, participant roster, экспорт в сторонние системы и production deployment.

## Verification plan

- Parser/CLI tests для UUID assignment, canonical format, duplicates и нормального/blitz pack.
- Repository tests для schema, session lifecycle, mode correction, ordering, full log and regular-only question aggregation.
- Handler tests для exact part-level `question_opened`, reset/completion boundaries, authorization and history responses.
- Frontend pure tests для history formatting plus production build.
- Full backend/frontend suites, pack validator, Compose validation and focused host smoke.
