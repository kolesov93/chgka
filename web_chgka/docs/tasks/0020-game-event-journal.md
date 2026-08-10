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
- Ведущий выбирает режим текущей игры на `/admin`; отдельная admin-only история содержит классификацию сессий, полный лог, открытые вопросы и агрегированную историю вопросов.
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
- На отдельном защищённом entrypoint `/admin/history` ведущий видит список сессий, regular-only сводку вопросов, точные части блица и полный хронологический лог. Отдельного блока текущего режима там нет; классификацию любой показанной сессии можно исправить.
- Режим текущей игры всегда виден и управляется на `/admin`: в комнате ожидания и в live-панели. Backend отдаёт его отдельным admin-only событием и обновляет UI после ручного изменения, переклассификации текущей сессии и сброса к новому development-default `debug`.
- `/admin/history` и его форма входа используют отдельный тёмно-бирюзовый фон, чтобы визуально не смешиваться ни с серой player-зоной, ни с индиго-панелью ведущего.
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

1. Запустить development Compose, открыть `/admin/history`. Форма входа и экран после авторизации должны иметь отдельный тёмно-бирюзовый фон, отличный от `/play` и `/admin`. Без admin token должна быть только форма пароля; после входа — только экран «История игр», без стола, игроков, игровых кнопок и отдельного блока режима текущей игры. Сам вход в историю не должен добавлять пустую сессию.
2. В списке сессий по умолчанию должен быть выбран фильтр «Обычные». Проверить переключение на «Тестовые» и «Все»: категории не смешиваются, а «Все» показывает обе. Вернуть «Обычные».
3. Перейти на `/admin`: в комнате ожидания должен быть виден режим текущей игры с default «Тестовая». Переключить на «Обычная», обновить `/admin` и убедиться, что выбор сохранился.
4. Открыть рядом `/play`, войти игроком и начать игру. Блок режима должен остаться видимым в live-панели ведущего во всех фазах; самой истории на `/admin` быть не должно.
5. Через Live Ops открыть часть 1 блица. Пройти «обсуждение → ответ команды → верно → следующая часть», тем самым открыть часть 2.
6. Открыть `/admin/history` и обновить данные: в фильтре «Обычные» текущая сессия должна показывать два открытых вопроса, а детали — две разные части 1/3 и 2/3 плюс полный лог действий.
7. Обновить `/admin/history`. Количество открытий и вопросов не должно вырасти. Переключить сессию в «Тестовая»: открытый `/admin` должен сразу показать тот же режим, а в истории сессия исчезает из фильтра «Обычные» вместе со своими вопросами из regular-сводки, но появляется с полным логом в «Тестовые». Там вернуть её в «Обычная» и убедиться, что `/admin` и соответствующие фильтр/сводка снова обновились.
8. Вернуться на `/admin`, выполнить Live Ops «Сбросить до интро»: блок режима должен сразу переключиться на «Тестовая». Затем проверить `/admin/history`: предыдущая сессия «Сброшена» с сохранённым счётом, новая автоматически «Тестовая».
9. Перезапустить только backend-контейнер. История должна сохраниться, а незакрытая новая сессия — стать «Прервана». Текущий `AppState` при этом ожидаемо начнётся заново.
