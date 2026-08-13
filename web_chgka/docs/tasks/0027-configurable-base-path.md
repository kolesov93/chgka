# Task 0027: настраиваемый URL-префикс

Статус: в работе.

Branch: `codex/configurable-base-path`.

## Цель

Подготовить одно frontend-приложение к двум вариантам размещения: текущему localhost от `/` и временному публичному адресу `https://example.com/chgka/`. Поддержка пути не должна мешать последующему переходу на `https://chgka.example.com/`.

## Согласованные решения

- Источник base path — Vite build setting `VITE_BASE_PATH`; значение по умолчанию `/`, для текущего публичного варианта `/chgka/`.
- Публичные entrypoints под префиксом: `/chgka/play`, `/chgka/admin`, `/chgka/admin/history`; `/chgka/` канонизируется во frontend в player entrypoint.
- Все статические изображения и звуки строятся через общий URL helper, а не через разбросанные абсолютные пути.
- В development backend остаётся на `http://localhost:8000`, поэтому привычный `docker compose up --build` не меняется.
- В production HTTP media/intro и Socket.IO используют тот же origin и base path: `/chgka/media/...`, `/chgka/intro/...`, `/chgka/socket.io/...`. Reverse proxy позднее снимет `/chgka` перед отправкой в существующий backend, API backend не переименовывается.
- Vite preview получает только локальное production-like проксирование prefixed backend routes в `localhost:8000`, чтобы полный smoke можно было пройти до доступа к VPS.
- Добавить чистые unit-тесты нормализации, маршрутов и backend URL для `/` и `/chgka/`, а также собрать оба варианта.

## Вне задачи

- Изменение DNS и обращение в Besthost.
- Подключение по SSH, правка существующего Nginx, TLS и фактическая публикация.
- Production Docker images, секреты, резервное копирование SQLite, health checks и автоматический deployment workflow.
- Изменение backend routes, Socket.IO events или игровых правил.

## Реализация и локальная проверка

- Planning commit: `cef8262` (`Plan configurable base path task`).
- Implementation commit: `25583a7` (`Support configurable frontend base path`).
- Добавлены чистые `appPaths.js` и `backendUrls.js`: Vite base определяет entrypoints, статические ресурсы, media/intro URL и Socket.IO transport path; development по-прежнему обращается напрямую к `http://localhost:8000` без префикса.
- Все прежние абсолютные image/sound URL, включая динамическую картинку счёта, переведены на общий helper. Structural test запрещает возвращать такие абсолютные пути в runtime source.
- Vite preview снимает внешний base path только с `/socket.io`, `/media` и `/intro`, а CI теперь собирает frontend как для `/`, так и для `/chgka/`.
- Development Compose разрешает отдельный точный preview-origin `http://localhost:4173`; production allowlist и backend API не менялись.
- Локально проходят `npm ci`, `npm audit` без уязвимостей, все 17 frontend test-файлов, root build, `/chgka/` build, 260 backend tests с warnings-as-errors и `git diff --check`.
- HTTP-проверка prefixed preview получила `200 text/html` для `/chgka/`, player/admin/history, `200` для score image и intro sound, backend JSON-ответы через prefixed media/intro proxy и успешный Engine.IO handshake через `/chgka/socket.io/`.
- Нативный `docker compose config --quiet` в текущем окружении по-прежнему не запускается из-за установленного Snap `snap-confine` без `cap_dac_override`; синтаксис Compose остаётся дополнительным GitHub CI gate.
- Полный ручной smoke ниже ещё не пройден пользователем.

## Ручной smoke

Перед smoke из корня `web_chgka` запустить обновлённый development Compose, чтобы backend получил preview-origin:

```bash
docker compose up --build
```

Затем во втором терминале собрать и запустить prefixed frontend:

```bash
cd frontend
VITE_BASE_PATH=/chgka/ npm run build
VITE_BASE_PATH=/chgka/ npm run preview -- --host 0.0.0.0
```

1. Открыть `http://localhost:4173/chgka/`: адрес канонизируется в `/chgka/play`, форма игрока отображается со всеми изображениями и без 404 в консоли/network.
2. Обновить напрямую `http://localhost:4173/chgka/admin` и `http://localhost:4173/chgka/admin/history`: обе SPA-страницы открываются на своих формах ведущего, пути не теряют `/chgka`.
3. На `/chgka/admin` войти с development-паролем `admin123`, на `/chgka/play` добавить одну тестовую группу и разрешить её вход ведущим. Убедиться, что roster и ожидание синхронизируются через `/chgka/socket.io/`.
4. Начать игру, на intro нажать `Запустить музыку`, затем показать авторов сектора 1: музыка слышна, статичные `/chgka/images/...`, `/chgka/sounds/...` и backend-фото `/chgka/intro/...` загружаются.
5. Перейти к игре, принудительно выбрать сектор 2, в тексте вопроса выбрать изображение и нажать `Показать игрокам`: private preview виден ведущему, а после показа то же изображение появляется у игрока через `/chgka/media/...`.
6. Обновить обе вкладки на текущих prefixed URL: роли восстанавливаются, экран и общее состояние синхронны.
7. Остановить preview, вернуть обычный development Compose и кратко проверить `http://localhost:5173/play` и `/admin`: root-режим не изменился.
