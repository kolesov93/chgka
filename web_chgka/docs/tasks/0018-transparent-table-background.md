# 0018: Прозрачный фон игрового стола

Branch: `task/transparent-table-background`
Status: Implemented; awaiting browser acceptance

## Goal

Убрать белый прямоугольный фон вокруг игрового стола, чтобы круглый стол естественно лежал на разных фонах player/admin экранов.

## Decisions

- Обработать оба runtime-asset: `table.png` до игры 13-го сектора и `table_all_arrows.png` после него.
- Сохранить PNG, canvas 2000×2000, центр, масштаб и все RGB-детали самого стола; меняется только внешний фон и сглаженный alpha-край.
- Не менять пути файлов и `GameTable.jsx`: это замена assets с прежним runtime-контрактом.
- Валидировать отсутствие белого ореола на графитовом player-фоне и индиговом фоне ведущего.

## Out of scope

- Перерисовка стола, стрелок, сектора 13, конвертов или волчка; изменение layout/анимации; оптимизация остальных изображений.

## Implementation

- Built-in image edit был проверен и отброшен, потому что менял геометрию исходника; генеративные пиксели в итоговые assets не попали.
- Белый фон преобразован в мягкий alpha matte штатным `imagegen` helper; защищённая внутренняя окружность затем побитово восстановлена из оригинала.
- Оба runtime-файла заменены на RGBA PNG под прежними путями; frontend-код не менялся.

## Local verification

- Оба PNG: 2000×2000 RGBA, corner alpha `0`, center alpha `1`, non-empty alpha bounds `1940×1940+30+30`.
- Максимальная RGB/alpha-разница внутри защищённой окружности для обоих вариантов равна нулю.
- Композитные preview на `#0f172a` player и `#1e1b4b` host backgrounds не показывают белого ореола.
- `npm test`: 9 test files passed.
- `npm run build`: passed.
- Остался browser smoke обоих runtime-состояний на player/admin экранах.
