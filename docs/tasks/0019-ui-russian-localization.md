# 0019: Русификация пользовательского интерфейса

Branch: `task/ui-russian-localization`
Status: Accepted; ready to merge into `web`

## Goal

Убрать смешение русского и английского во всех пользовательских экранах, сообщениях и игровом логе, не меняя внутренние контракты приложения.

## Decisions

- В UI использовать «ведущий» и «игрок»; технические `admin`/`player` остаются во внутренних ролях, route, events и payload.
- `Live Ops` переводится как «Восстановление игры», `Reset` — «Сброс», `Kick` — «Отключить», media controls — «Воспроизвести / Пауза / Остановить», `Fade` — «Затухание 3 с», `Silence` — «Выключить звук».
- Все game phase, question kind, media section/type и timer state проходят через явные русские display mappings. Сырые `PRE_ROUND`, `superblitz`, `answer`, `None` и error codes пользователю не показываются.
- Неизвестная серверная ошибка получает понятный общий русский fallback; технический code остаётся доступен в console для диагностики.
- Перевести browser title, `lang`, alt/accessibility/fallback-тексты и публичные HTTP error messages.
- Названия файлов пака, авторский контент вопросов и `intro.md` не переводятся как данные пользователя.

## Out of scope

- i18n framework, переключатель языка, изменение Socket.IO events/API fields/backend constants, перевод документации и внутренних комментариев.

## Verification plan

- Pure frontend tests для display mappings фаз, типов вопросов, секций медиа и русского error fallback.
- Backend tests для русских phase/log/timer mappings и обновлённых публичных сообщений.
- Статический аудит оставшихся латинских пользовательских строк, полные backend/frontend tests и frontend build.
- Browser smoke основных player/host экранов, media/black-box controls, ошибок и панели восстановления.

## Implemented

- Добавлен единый frontend-словарь для фаз, типов вопросов, секций и типов медиа, состояний воспроизведения и безопасных сообщений об ошибках.
- Переведены видимые кнопки, заголовки, подтверждения, статусы, browser title, accessibility-тексты и fallback-состояния.
- Добавлен backend-словарь для фаз, типов вопросов и медиа, звуков, сыгранности сектора и состояния таймера.
- Игровой лог и сообщения переходов больше не показывают `Live Ops`, raw phase/kind/sound identifiers, `None`, `boolean`, `played` или `[FORCED]`.
- Публичные FastAPI status/404 messages переведены; внутренние Socket.IO events, payload fields, roles и error codes не изменены.

## Local verification

- `python3 -W error -m pytest -q`: 192 passed.
- `npm ci` and `npm test`: 10 test files passed.
- `npm run build`: passed.
- `docker compose config --quiet`: passed outside the restricted sandbox required by the local snap package.
- Static audit found no remaining English text in rendered JSX controls, titles, alt text, or the targeted server log/error paths.

## Browser smoke

1. Open `/admin` and `/play`; check the Russian browser title and the existing separate host/player login presentation.
2. Start a game and reach the table; check the Russian phase label, host controls and game-log entries after a spin and a score action.
3. Open «Восстановление игры»; check sector type labels, phase buttons, timer controls and confirmation text. Submit an invalid score and check the Russian warning.
4. Open sample sector 03 audio; check «Предпросмотр», the Russian section name and «Воспроизвести / Пауза / Остановить» on the host, plus the Russian playback state on the player.
5. Open sample sector 09 black box; check the Russian start/stop copy and return to the table after stopping.

## Acceptance

- The user approved integration into `web` on 2026-08-09.
- Remote CI remains the publication gate after pushing the merged `web` branch.
