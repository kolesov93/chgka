# 0016: Чёрный ящик

Branch: `task/blackbox`
Status: Completed

## Goal

Добавить управляемую ведущим заставку чёрного ящика для отмеченных в question pack вопросов и частей блица/суперблица.

## Decisions

- `blackbox: true|false` — опциональный строгий boolean во frontmatter вопроса или части; отсутствие поля эквивалентно `false`.
- У блица/суперблица top-level флаг действует на весь блиц, а флаг отдельной части — только на эту часть. В `admin_question` приходит эффективное значение для текущей части; `pack_info` сохраняет отдельно top-level и part-флаги.
- Музыка `/sounds/yashik.mp3` и изображение `/images/blackbox.png` остаются статичными frontend-assets, а доступность кнопки определяется текущим pack-backed вопросом.
- Старт — отдельное осознанное действие ведущего только в `QUESTION_READING`. Он заменяет ранее показанное shared media и включает отдельное server-authoritative presentation state с reconnect-aware временной шкалой.
- Пока музыка играет, игрок видит статичное изображение чёрного ящика. Переход к обсуждению недоступен до окончания заставки.
- Естественное окончание подтверждает авторизованный host для текущего playback generation. Принудительное окончание происходит по отдельному Stop, по Silence или после полного трёхсекундного Fade.
- После любого окончания показывается обычный игровой стол; ранее показанное shared media не восстанавливается.
- Отдельный Stop завершает только чёрный ящик. Silence и Fade сохраняют своё глобальное действие на остальные игровые звуки.
- В карточке ведущего идёт reconnect-aware обратный отсчёт от измеренной длительности статичного трека `31.488` сек., по той же server-snapshot модели, что у intro.

## Out of scope

- Pack-backed музыка/изображение, пауза, ручная перемотка, повторное восстановление скрытого shared media, scoring/timer changes и отдельный тип игрового раунда.

## Implementation

- Parser и pack metadata поддерживают normal/top-level blitz/part flags и отдают эффективный флаг только ведущему.
- Отдельное server-authoritative presentation state синхронизирует статичный трек, player-заставку, reconnect и generation guards.
- Ведущий получил явные Start/Stop, индикатор режима и reconnect-aware countdown; Discussion и новый share блокируются до завершения заставки.
- Natural end, Stop, Silence, completed Fade, reset и Live Ops корректно завершают/инвалидируют presentation без восстановления прежнего media.

## Local verification

- `python3 -W error -m pytest -q`: 189 tests passed.
- `npm test`: 36 assertions across 8 test files passed.
- `npm run build`: passed.
- `python3 -m validate_pack ../fixtures/sample_questions`: passed.
- `docker compose config --quiet`: locally blocked before parsing by the installed `snap-confine` capability error; remote Compose CI remains the configuration gate.
- Focused browser behavior was accepted by the user; the branch is approved for local integration into `web` without publishing a remote task branch.
