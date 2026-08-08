# 0019: Русификация пользовательского интерфейса

Branch: `task/ui-russian-localization`
Status: In progress

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
