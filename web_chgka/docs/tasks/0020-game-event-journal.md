# 0020: Журнал игр и история сыгранных вопросов

Branch: `task/game-event-journal`
Status: Ready for browser acceptance

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

## Implemented

- `Question.id` обязателен для родителя и каждой части; parser проверяет UUID и pack-wide uniqueness. Sample/valid/invalid fixtures мигрированы, а `python -m assign_question_ids` добавляет только отсутствующие ID после полной предварительной проверки старого пака.
- `GameJournal` создаёт versioned SQLite schema для сессий и упорядоченных событий. Lobby/active/completed/reset/interrupted, итоговый счёт, pack identity и immediate commits покрыты repository-тестами.
- Все прежние строки live-лога теперь рождаются из typed transition events либо записываются как typed handler events. In-memory `logs` остаётся совместимой 50-строчной проекцией.
- `question_opened` обогащается на backend постоянным ID, parent ID, сектором, индексом части, названием и автором. Обычное вращение, Live Ops open и переход к следующей части блица являются авторитетными точками записи; reconnect — нет.
- На отдельном защищённом entrypoint `/admin/history` ведущий видит режим текущей игры, список сессий, regular-only сводку вопросов, точные части блица и полный хронологический лог. Waiting screen и live-панель `/admin` не показывают историю или режим. Режим текущей и прошлой сессии можно исправить.
- Список сессий фильтруется на backend по «Обычные / Тестовые / Все» и по умолчанию запрашивает только обычные игры. Лимит применяется после mode-фильтра, поэтому тестовые сессии не вытесняют обычные из ответа.
- History-only login/restore использует тот же admin token, но не добавляет ведущего в live roster, не создаёт пустую игровую сессию и при restore того же токена не перехватывает live host socket record.
- Development Compose хранит базу в gitignored `./runtime-data/chgka.sqlite3`; production config требует абсолютный durable `CHGKA_DB_PATH`.

Каждая новая development-сессия снова получает безопасный default `debug`, даже если предыдущую игру ведущий пометил regular. В production новый default — `regular`.

## Out of scope

- Restart recovery/undo всего `AppState`, удаление истории, награды, participant roster, экспорт в сторонние системы и production deployment.

## Verification plan

- Parser/CLI tests для UUID assignment, canonical format, duplicates и нормального/blitz pack.
- Repository tests для schema, session lifecycle, mode correction, ordering, full log and regular-only question aggregation.
- Handler tests для exact part-level `question_opened`, reset/completion boundaries, authorization and history responses.
- Frontend pure tests для history formatting plus production build.
- Full backend/frontend suites, pack validator, Compose validation and focused host smoke.

## Verification

- `python3 -W error -m pytest -q`: 207 passed.
- `npm test`: 11 test files passed.
- `npm run build`: passed.
- Direct Vite request to `/admin/history`: HTTP 200 with SPA entrypoint.
- `python3 -m validate_pack ../fixtures/sample_questions`: passed, 13 sectors / 19 authored question units / 6 blitz parts.
- Compose YAML and the `/data` journal mount were parsed and asserted independently. Native `docker compose config --quiet` is blocked before reading the project by the installed Snap `snap-confine` capability error (`cap_dac_override`), the same environment defect recorded for earlier tasks.
- Focused two-browser host/player smoke: pending.

## Focused browser smoke

1. Запустить development Compose, открыть `/admin/history`. Без admin token должна быть только форма пароля; после входа — только экран «История игр», без стола, игроков и игровых кнопок.
2. В списке сессий по умолчанию должен быть выбран фильтр «Обычные». Проверить переключение на «Тестовые» и «Все»: категории не смешиваются, а «Все» показывает обе. Вернуть «Обычные».
3. Проверить default текущей игры «Тестовая», переключить на «Обычная», обновить `/admin/history` и убедиться, что режим сохранился. Сам вход в историю не должен добавлять пустую сессию.
4. Перейти на `/admin`, открыть рядом `/play`, войти игроком и начать игру. На waiting screen и во всех фазах панели ведущего не должно быть истории или режима.
5. Через Live Ops открыть часть 1 блица. Пройти «обсуждение → ответ команды → верно → следующая часть», тем самым открыть часть 2.
6. Открыть `/admin/history` и обновить данные: в фильтре «Обычные» текущая сессия должна показывать два открытых вопроса, а детали — две разные части 1/3 и 2/3 плюс полный лог действий.
7. Обновить `/admin/history`. Количество открытий и вопросов не должно вырасти. Переключить сессию в «Тестовая»: в фильтре «Обычные» она исчезает вместе со своими вопросами из regular-сводки, но появляется с полным логом в «Тестовые». Там вернуть её в «Обычная» и убедиться, что она снова появляется в соответствующем фильтре и сводке.
8. Вернуться на `/admin`, выполнить Live Ops «Сбросить до интро», затем проверить `/admin/history`: предыдущая сессия «Сброшена» с сохранённым счётом, новая автоматически «Тестовая».
9. Перезапустить только backend-контейнер. История должна сохраниться, а незакрытая новая сессия — стать «Прервана». Текущий `AppState` при этом ожидаемо начнётся заново.
