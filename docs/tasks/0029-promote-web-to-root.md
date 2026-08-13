# Task 0029: promote web application to repository root

Статус: в работе.

Branch: `task/promote-web-to-root`.

## Цель

Сделать web-приложение единственным актуальным содержимым репозитория и ветки `main`: удалить tracked Pyglet/VLC-приложение, поднять содержимое `web_chgka/` в корень и сохранить доступ к последней legacy-версии через Git.

## Решения

- В репозитории фактическая основная ветка называется `main`; ветки `master` нет.
- `main` (`970ebc9`) — прямой предок `web`, а tracked legacy-файлы после этой точки не менялись.
- Последняя legacy-версия сохранена аннотированным тегом `legacy-pyglet-final` на `970ebc9`. GitHub Release не обязателен: это лишь оформленная публикация поверх тега.
- Корневые legacy Python-файлы, desktop-конфиги, изображения, звуки и генератор стола удаляются из нового дерева. Их история остаётся в Git и в теге.
- Всё tracked-содержимое `web_chgka/` перемещается в корень. CI запускается для `main` и `task/**` из `backend/`, `frontend/` и корня Compose.
- Production runtime на VPS не изменяется и не перезапускается. Будущие release archives создаются из всего корневого Git tree, а layout внутри VPS release остаётся прежним.
- Незатреканные legacy-данные нельзя сохранить тегом. `questions/`, `intro_2024/`, старые runtime-файлы и локальные артефакты перемещаются в соседний recoverable-каталог `/home/kolesov93/Programming/chgka2-legacy-local-files-20260813/`, а не удаляются.

## Проверка

- В tracked tree нет `web_chgka/` и файлов desktop-приложения; корень содержит web-проект.
- В актуальных инструкциях, CI и deployment-командах не осталось старых рабочих путей `web_chgka`.
- Backend tests проходят с warnings-as-errors.
- Frontend clean install/audit, tests и builds для `/` и `/chgka/` проходят.
- Sample question pack validation и Compose config validation проходят.
- Production runtime не изменяется. Он намеренно остановлен пользователем, поэтому доступность публичного URL не является условием приёмки repository-only задачи.
- После merge Git ancestry содержит обе линии истории, а `legacy-pyglet-final` указывает на точный прежний `main`.

## Smoke

Изменений runtime/UI нет, поэтому отдельный ручной smoke не требуется. Production намеренно остановлен пользователем и не должен запускаться для приёмки repository-only миграции.

## Найдено проверками

После clean install npm registry сообщил новый advisory для транзитивного `nanoid@3.3.17`, который приходит через `postcss`. Совместимое обновление lockfile до `nanoid@3.3.18` устраняет advisory без изменения прямых зависимостей или frontend API.

## Out of scope

- Изменение игрового поведения, question pack или production-конфигурации.
- Удаление веток `web`/`main` на remote и смена GitHub default branch без отдельного подтверждения после push.
- Создание GitHub Release или назначение semantic version web-приложению.
