# 0013: Интро

Branch: `task/intro`
Status: Completed

## Goal

Добавить управляемое ведущим вступление между лобби и первым раундом: общий показ intro-слайдов под музыкальный трек, admin-only текст речи и явный переход к табло 0:0.

## Current context

- `start_game` сейчас переводит `LOGIN` напрямую в `PRE_ROUND`.
- Статичные assets приложения: `images/intro/00_owl.png`, особый `13.png`, fallback автора и `sounds/meeting.mp3`. Авторские фото секторов 1–12 принадлежат question pack.
- Question pack содержит ровно 13 игровых директорий и допускает именованные вспомогательные файлы/директории в корне.
- Состояние игры и звуковые события живут только в памяти; одноразовые эффекты не восстанавливаются после reconnect.

## Accepted behavior

- Добавить авторитетную фазу `INTRO`; `start_game` переводит `LOGIN -> INTRO` и показывает слайд `00` без autoplay. Ведущий отдельной кнопкой один раз запускает `meeting.mp3`, после чего начинается countdown.
- Ведущий последовательно переключает `00 -> 01 -> … -> 13`; следующий шаг после `13` переводит игру в `PRE_ROUND`, где все видят обычное живое табло 0:0.
- Все клиенты получают текущий slide index и metadata только соответствующих текущему сектору авторов из `state_update`; игроки видят общий слайд с именами/городами, но без речи и органов управления.
- Ведущий видит текущий слайд, название следующего шага, оставшееся время трека и текст речи.
- Клиент отправляет вместе с переключением ожидаемый slide index. Сервер отклоняет повторный/устаревший запрос, поэтому двойной клик не пропускает слайды.
- При переходе из последнего слайда в `PRE_ROUND` intro-трек останавливается, если ещё играет.
- Необязательный корневой `intro.md` question pack хранит Markdown речи. Backend валидирует UTF-8/непустое содержимое, преобразует его в HTML и включает только в admin-only `pack_info`.
- Reset и normal phase guards продолжают быть серверными; reset из intro возвращает игру в `PRE_ROUND` согласно уже принятому контракту reset.
- Live Ops содержит отдельный полный «Сброс до интро»: он обнуляет счёт и сыгранные сектора, очищает раунд/таймер/медиа/возможное вращение, останавливает звук и возвращает слайд `00` с незапущенной музыкой. Обычный Reset по-прежнему ведёт в `PRE_ROUND`.
- Каждый вопрос и каждая часть блица имеют обязательный `author`, optional `city` и optional `author_photo`. Intro-слайды 1–12 публично показывают одну карточку верхнего normal-вопроса либо три карточки частей блица/суперблица в один ряд; каждая карточка независимо использует pack-backed фото или fallback. Сектор 13 остаётся особым статичным слайдом.

## Implementation decisions

- Хранить intro runtime context в `presentation.intro`, рядом с остальным общим представлением, и сериализовать его отдельным полем `intro` в существующий плоский `state_update`.
- Передавать nullable `started_at_ms`, `duration_ms` и `server_now_ms`; до команды ведущего UI показывает «Не запущена», затем frontend добавляет локальное время получения snapshot и обновляет countdown без серверного тика.
- Зафиксировать длительность временного `meeting.mp3` как backend-константу текущего asset (`87_757 ms`).
- Использовать `pack_info`, потому что это уже admin-only канал metadata; отдельное публичное событие для речи не создавать.
- После слайда `13` рендерить реальный `ScoreBoard`/`GameTable`, а не временный файл `14_table00.png`.
- Хранить в `AppState.pack` упорядоченные группы публичных карточек с sector/slot/именем/городом/наличием фото для первых 12 секторов; абсолютные пути остаются внутри parsed `QuestionPack`.
- Выдавать pack-backed фото карточки через отдельный endpoint только во время соответствующего текущего intro-слайда, с `no-store`; при 404 frontend независимо переключает эту карточку на статичный fallback.

## Out of scope

- Перенос музыки, стартового/особого слайдов или fallback внутрь question pack, настраиваемая последовательность/длительность.
- Автоматический replay/seek одноразового intro-трека после reconnect или перезагрузки страницы.
- Возврат к предыдущему слайду, произвольный выбор слайда, autoplay после окончания трека, редактирование речи из UI.
- Изменения legacy Pyglet/VLC приложения, production deployment и persistence.

## Verification plan

- Parser/CLI tests: обязательные авторы, optional city/photo, containment/format фото, pack без `intro.md`, корректный Markdown, пустой/не-UTF-8 файл, admin-only startup payload.
- State/transition tests: `LOGIN -> INTRO`, time snapshot, последовательное переключение, stale click rejection, последний слайд -> `PRE_ROUND`, cleanup/sound effects, reset.
- Handler test: silent start, guarded music start, slide advance emits, authorization boundary and repeated action behavior.
- Frontend pure tests: static/dynamic asset boundary, fallback mapping, sector-oriented labels and reconnect-aware countdown; production build validates three-card JSX.
- Full backend tests with warnings-as-errors, frontend tests/build and Compose validation.
- Two-browser smoke: lobby -> silent intro, manual shared music start, player/admin parity, speech privacy, all slides, music countdown/stop and transition to table 0:0.

## Verification and acceptance

Implemented locally:

- authoritative `LOGIN -> INTRO -> PRE_ROUND` flow with slides `00`–`13`;
- explicit one-shot meeting-track button, shared slide state and reconnect-aware admin countdown without autoplay;
- stale expected-slide guard against double-click/concurrent skipping;
- admin-only optional `intro.md` speech with UTF-8, containment, empty-file and media validation;
- dedicated player/admin intro screen and direct transition from the final slide to the real table at 0:0.
- dedicated Live Ops full reset to silent slide `00`, including progress cleanup and audio stop.
- required pack authors plus optional city/direct author photo, one normal or three blitz-part public cards, context-bound per-slot photo delivery, and a generated static fallback silhouette.
- restored twelve former intro photos into the sample pack, assigned the blitz/superblitz sector photos to their first parts, and stripped EXIF/GPS metadata after applying orientation.

Passed locally:

- `python3 -B -W error -m pytest -p no:cacheprovider -q`: 139 backend tests;
- `npm test`: 25 frontend tests;
- `npm run build`;
- sample-pack validator CLI;
- `docker compose config --quiet`.

Acceptance:

- the focused admin/player browser smoke passed on `de4e847`, including normal author photos, three-card blitz/superblitz rows, fallback silhouettes, the special static sector 13, manual music start, and reset-to-intro;
- remote CI will run on the merged `web` branch; the task branch is intentionally not published.
