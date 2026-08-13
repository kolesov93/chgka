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

## Ручной smoke

Перед smoke запустить backend на `localhost:8000` с обычной development-конфигурацией, затем собрать и запустить prefixed frontend:

```bash
cd frontend
VITE_BASE_PATH=/chgka/ npm run build
VITE_BASE_PATH=/chgka/ npm run preview -- --host 0.0.0.0
```

1. Открыть `http://localhost:4173/chgka/`: адрес канонизируется в `/chgka/play`, форма игрока отображается со всеми изображениями и без 404 в консоли/network.
2. Обновить напрямую `http://localhost:4173/chgka/admin` и `http://localhost:4173/chgka/admin/history`: обе SPA-страницы открываются на своих формах ведущего, пути не теряют `/chgka`.
3. Войти ведущим на `/chgka/admin`, игроком на `/chgka/play`, разрешить вход и убедиться, что состояние синхронизируется через `/chgka/socket.io/`.
4. Начать игру, на intro запустить музыку и перейти хотя бы к одному фото автора: статичные `/chgka/images/...`, `/chgka/sounds/...` и backend-фото `/chgka/intro/...` загружаются.
5. Перейти к игре, открыть сектор с медиа, проверить private preview и `Показать игрокам`: запрос `/chgka/media/...` работает у ведущего и игрока.
6. Обновить обе вкладки на текущих prefixed URL: роли восстанавливаются, экран и общее состояние синхронны.
7. Остановить preview, вернуть обычный development Compose и кратко проверить `http://localhost:5173/play` и `/admin`: root-режим не изменился.
