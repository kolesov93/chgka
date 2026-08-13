# Task 0028: production Docker deployment

Статус: завершена и принята 2026-08-13.

Branch: `codex/docker-production-deployment`.

## Цель

Опубликовать web-приложение по адресу `https://example.com/chgka/` на существующем Ubuntu 24.04 VPS. Существующий host Nginx продолжает завершать TLS и обслуживать остальные маршруты домена; CHGKA работает в production Docker Compose и не открывает собственные публичные порты.

## Проверенный контекст VPS

- Ubuntu 24.04 x86_64, 1 CPU, 1.9 GiB RAM, 1.5 GiB swap, около 13 GiB свободного места.
- Nginx 1.24 и Certbot работают; certificate timer активен. Публично слушают только `22`, `80`, `443`.
- Docker и Node.js до задачи не установлены; Python 3.12, Git и rsync доступны.
- `example.com` уже маршрутизирует `/movieclub/` локально, `/books/` и `/podcasts/` на QNAP, а корень — на QNAP DSM. Текущий `/chgka/` попадает в корневой proxy и возвращает `401`.
- SSH доступен как `ssh vps`. Интерактивный login подключается к tmux, но non-interactive SSH-команды выполняются отдельно. Для `sudo` нужен пароль пользователя.

## Согласованные решения

- Docker Engine устанавливается из официального apt repository вместе с Buildx и Compose plugin; convenience script не используется.
- Пользователь `kolesov93` добавляется в группу `docker`. Пользователь понимает и принимает, что доступ к Docker daemon фактически даёт root-level возможности на VPS.
- Runtime topology:

  ```text
  public HTTPS
      -> host Nginx
      -> 127.0.0.1:18080
      -> production frontend Nginx container
      -> backend:8000 in the private Compose network
  ```

- Host публикует только frontend container и только на `127.0.0.1`; backend не имеет host `ports`. Backend и frontend соединены закрытой `internal`-сетью `app`, а отдельная `edge`-сеть frontend нужна для работающей loopback-публикации Docker.
- Frontend собирается с `VITE_BASE_PATH=/chgka/`. Container Nginx делает SPA fallback внутри `/chgka/`, снимает prefix только для `/socket.io`, `/media` и `/intro`, и проксирует их в backend.
- Backend запускает один Uvicorn process без `--reload` и без нескольких workers: live `AppState`, players и tokens остаются process-local.
- `CHGKA_ENV=production`, exact origin `https://example.com`, путь пака и SQLite задаются production env-файлом вне Git. Пароль ведущего пользователь создаёт сам и не передаёт агенту.
- Постоянная host-структура — `~/apps/chgka/{releases,questions,data,backups}`, symlink `current` плюс mode-`0600` env-файл. Question pack монтируется read-only, data/backups — read-write.
- Первый технический запуск использует repository sample pack. Реальный pack загружается отдельным rsync после успешного infrastructure smoke и parser validation.
- Compose использует health checks, restart policy и ограниченную ротацию логов. Изменение/replacement контейнера не меняет host SQLite или question pack.
- Host Nginx получает изолированный CHGKA include/location. Перед reload сохраняется backup текущего site config, выполняется `nginx -t`, а rollback не требует изменения остальных location.
- Релиз передаётся с development-машины через SSH/rsync; VPS не получает GitHub private key. Автоматический GitHub deployment пока не вводится.

## Безопасность и эксплуатационные границы

- Не коммитить production env, пароль, реальный pack, SQLite или backups.
- Docker socket не публикуется по TCP. Контейнерные порты не привязываются к `0.0.0.0`/`::`.
- Backend origin allowlist остаётся exact и HTTPS. TLS продолжает обслуживать существующий Certbot certificate домена.
- Backend restart прерывает текущую live-игру и отзывает in-memory sessions; SQLite сохраняет журнал, но не восстанавливает `AppState`.
- Встроенная видеосвязь, поддомен, zero-downtime multi-worker deployment, recovery текущей игры и GitHub CD остаются вне задачи.

## План проверки

- Полные backend tests с warnings-as-errors.
- Clean frontend install, tests, audit и builds для `/` и `/chgka/`.
- Production Compose config validation и build обоих images.
- Container health, loopback binding, отсутствие backend host port, production config rejection tests.
- HTTP/WebSocket smoke через production frontend proxy до изменения host Nginx.
- `nginx -t`, затем внешний HTTPS smoke и regression статусов существующих routes.
- Проверка persistence SQLite и backup после recreation backend container.

## Реализация и автоматическая проверка

- Planning commit: `4c66426`; production stack commit: `f14d24a`; edge-network fix после VPS smoke: `3c09e41`.
- На VPS из официального apt repository установлены Docker Engine `29.7.2`, Compose `5.4.0` и Buildx. Docker/containerd активны и включены в автозапуск; пользователь `kolesov93` входит в группу `docker`.
- Production release `3c09e41d3df3` установлен в `~/apps/chgka/releases/`, symlink `current` указывает на него. Закрытый mode-`0600` env-файл создан пользователем без передачи пароля агенту.
- Оба immutable image собраны на VPS. Backend и frontend работают непривилегированными UID, с read-only root filesystem, dropped capabilities и `no-new-privileges`; оба health check зелёные.
- Host слушает только frontend на `127.0.0.1:18080`; backend имеет только container port `8000`. Отдельная `edge`-сеть исправляет loopback publication, закрытая `app`-сеть остаётся единственной сетью backend.
- Sample pack прошёл container validator: 13 вопросов, 19 authored entries, 6 blitz/superblitz parts и 9 media files.
- До host Nginx проверены `200` для health/player/admin/history/static image, exact production CORS, WebSocket upgrade `101`, отсутствие error-level container logs и отказ `403` для чужого WebSocket origin.
- После Nginx reload те же player/admin/history/static routes доступны по публичному HTTPS, WSS даёт `101`, `/chgka` перенаправляет `308` в `/chgka/`. Baseline остальных маршрутов сохранён: `/` и `/movieclub/` — `401`, `/books/` — `302`, `/books/opds/` — `401`, `/podcasts/` — `404`.
- Online SQLite backup создан через SQLite backup API и прошёл `PRAGMA quick_check`; bind-mounted database сохранилась при принудительном recreation backend. Ежедневный backup установлен в user crontab на `04:15 UTC` с retention 30 дней.
- Локально проходят 264 backend tests с warnings-as-errors, все 17 frontend test files, root и `/chgka/` builds, npm audit с нулём уязвимостей и `git diff --check`. Production Compose реально валидирован и собран Docker Engine на VPS; локальный Snap Compose остаётся сломан внешним `snap-confine` defect.
- Встроенный браузер подтвердил публичную player login form, канонический `/chgka/play`, прямые `/chgka/admin` и `/chgka/admin/history`, правильные document titles и отсутствие console errors/warnings без использования production-пароля.

## Ручной production smoke

Статус: пройден пользователем 2026-08-13.

1. На ноутбуке открыть `https://example.com/chgka/`: URL становится `/chgka/play`, форма игрока и изображения загружаются. Прямо открыть/обновить `/chgka/admin` и `/chgka/admin/history`: остаются правильные формы и адреса; затем войти на `/chgka/admin` production-паролем.
2. До старта нажать у ведущего `Тестовая`, чтобы smoke не попал в обычную историю. На ноутбуке войти игроком как группа из двух участников: группа сразу появляется у ведущего и получает игровой экран без отдельного admission.
3. Начать игру. В intro нажать `Запустить музыку`, показать авторов сектора 1 и нажать `Перейти к игре`: музыка слышна, фото автора видно ведущему и игроку, затем обоим показывается стол.
4. После старта с телефона, лучше через мобильный интернет, открыть `https://example.com/chgka/play` и войти новой группой. Телефон показывает ожидание; ведущий видит заявку и разрешает вход; после разрешения телефон получает тот же стол/счёт.
5. Через Live Ops открыть сектор 2. У ведущего в тексте вопроса виден inline preview, но игроки продолжают видеть стол; после `Показать игрокам` одинаковое изображение появляется на ноутбуке и телефоне. Обновить admin и обе player-страницы: роли и текущее состояние восстанавливаются без CORS/mixed-content/WebSocket ошибок.
6. У ведущего выполнить `Сбросить до интро`, затем открыть `/chgka/admin/history`, войти и выбрать фильтр `Тестовые`: завершённая smoke-сессия присутствует, а в её логе/открытых вопросах виден сектор 2.

## Out of scope

- Покупка/настройка нового домена или `chgka.example.com`.
- Передача private SSH/GitHub keys или sudo/admin passwords агенту.
- Изменение игровых правил, wire contracts, question format или legacy-приложения.
- Полная observability stack, оркестратор, registry и автоматический CD.
