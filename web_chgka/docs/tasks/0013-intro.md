# 0013: Интро

Branch: `task/intro`
Status: In progress

## Goal

Добавить управляемое ведущим вступление между лобби и первым раундом: общий показ intro-слайдов под музыкальный трек, admin-only текст речи и явный переход к табло 0:0.

## Current context

- `start_game` сейчас переводит `LOGIN` напрямую в `PRE_ROUND`.
- Временные assets уже хранятся во frontend: `images/intro/00_owl.png`, `01.jpg`…`12.jpg`, `13.png` и `sounds/meeting.mp3`.
- Question pack содержит ровно 13 игровых директорий и допускает именованные вспомогательные файлы/директории в корне.
- Состояние игры и звуковые события живут только в памяти; одноразовые эффекты не восстанавливаются после reconnect.

## Accepted behavior

- Добавить авторитетную фазу `INTRO`; `start_game` переводит `LOGIN -> INTRO`, показывает слайд `00` и один раз запускает `meeting.mp3`.
- Ведущий последовательно переключает `00 -> 01 -> … -> 13`; следующий шаг после `13` переводит игру в `PRE_ROUND`, где все видят обычное живое табло 0:0.
- Все клиенты получают текущий slide index из `state_update`; игроки видят только слайд, без текста и органов управления.
- Ведущий видит текущий слайд, название следующего шага, оставшееся время трека и текст речи.
- Клиент отправляет вместе с переключением ожидаемый slide index. Сервер отклоняет повторный/устаревший запрос, поэтому двойной клик не пропускает слайды.
- При переходе из последнего слайда в `PRE_ROUND` intro-трек останавливается, если ещё играет.
- Необязательный корневой `intro.md` question pack хранит Markdown речи. Backend валидирует UTF-8/непустое содержимое, преобразует его в HTML и включает только в admin-only `pack_info`.
- Reset и normal phase guards продолжают быть серверными; reset из intro возвращает игру в `PRE_ROUND` согласно уже принятому контракту reset.
- Live Ops содержит отдельный полный «Сброс до интро»: он обнуляет счёт и сыгранные сектора, очищает раунд/таймер/медиа/возможное вращение, возвращает слайд `00` и перезапускает intro-трек. Обычный Reset по-прежнему ведёт в `PRE_ROUND`.

## Implementation decisions

- Хранить intro runtime context в `presentation.intro`, рядом с остальным общим представлением, и сериализовать его отдельным полем `intro` в существующий плоский `state_update`.
- Передавать `started_at_ms`, `duration_ms` и `server_now_ms`; frontend добавляет локальное время получения snapshot и обновляет countdown без серверного тика.
- Зафиксировать длительность временного `meeting.mp3` как backend-константу текущего asset (`87_757 ms`).
- Использовать `pack_info`, потому что это уже admin-only канал metadata; отдельное публичное событие для речи не создавать.
- После слайда `13` рендерить реальный `ScoreBoard`/`GameTable`, а не временный файл `14_table00.png`.

## Out of scope

- Перенос картинок и музыки внутрь question pack, настраиваемая последовательность/длительность, загрузка intro-assets через media tokens.
- Автоматический replay/seek одноразового intro-трека после reconnect или перезагрузки страницы.
- Возврат к предыдущему слайду, произвольный выбор слайда, autoplay после окончания трека, редактирование речи из UI.
- Изменения legacy Pyglet/VLC приложения, production deployment и persistence.

## Verification plan

- Parser/CLI tests: pack без `intro.md`, корректный Markdown, пустой/не-UTF-8 файл, admin-only startup payload.
- State/transition tests: `LOGIN -> INTRO`, time snapshot, последовательное переключение, stale click rejection, последний слайд -> `PRE_ROUND`, cleanup/sound effects, reset.
- Handler test: start/advance emits, authorization boundary and repeated action behavior.
- Frontend pure tests: asset mapping, next-step labels and reconnect-aware countdown.
- Full backend tests with warnings-as-errors, frontend tests/build and Compose validation.
- Two-browser smoke: lobby -> intro, player/admin parity, speech privacy, all slides, music countdown/stop and transition to table 0:0.

## Local verification status

Implemented locally:

- authoritative `LOGIN -> INTRO -> PRE_ROUND` flow with slides `00`–`13`;
- one-shot meeting track, shared slide state and reconnect-aware admin countdown;
- stale expected-slide guard against double-click/concurrent skipping;
- admin-only optional `intro.md` speech with UTF-8, containment, empty-file and media validation;
- dedicated player/admin intro screen and direct transition from the final slide to the real table at 0:0.
- dedicated Live Ops full reset to slide `00`, including progress cleanup and stop-then-restart intro audio ordering.

Passed locally:

- `python3 -B -W error -m pytest -p no:cacheprovider -q`: 131 backend tests;
- `npm test`: 24 frontend tests;
- `npm run build`;
- sample-pack validator CLI;
- `docker compose config --quiet`.

Remote CI and focused two-browser smoke are pending.
