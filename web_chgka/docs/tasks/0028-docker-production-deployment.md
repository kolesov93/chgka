# Task 0028: production Docker deployment

Статус: в работе.

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

- Host публикует только frontend container и только на `127.0.0.1`; backend не имеет host `ports`.
- Frontend собирается с `VITE_BASE_PATH=/chgka/`. Container Nginx делает SPA fallback внутри `/chgka/`, снимает prefix только для `/socket.io`, `/media` и `/intro`, и проксирует их в backend.
- Backend запускает один Uvicorn process без `--reload` и без нескольких workers: live `AppState`, players и tokens остаются process-local.
- `CHGKA_ENV=production`, exact origin `https://example.com`, путь пака и SQLite задаются production env-файлом вне Git. Пароль ведущего пользователь создаёт сам и не передаёт агенту.
- Постоянная host-структура — `~/apps/chgka/{release,questions,data,backups}` плюс mode-`0600` env-файл. Question pack монтируется read-only, data/backups — read-write.
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

## Ручной production smoke

Статус: не пройден.

1. Открыть `https://example.com/chgka/`: URL канонизируется в `/chgka/play`, player login и все статические изображения загружаются без mixed-content/404.
2. Прямо открыть и обновить `/chgka/admin` и `/chgka/admin/history`: обе SPA-страницы остаются на правильных entrypoints; ведущий входит production-паролем.
3. Подключить с ноутбука player group из двух участников, разрешить группу ведущим; затем открыть `/chgka/play` с телефона в той же Wi-Fi или мобильной сети и проверить вторую группу/admission.
4. Начать sample-игру, запустить intro music, показать author photo и перейти к игре: звук, `/chgka/images`, `/chgka/sounds` и `/chgka/intro` работают по HTTPS.
5. Открыть сектор 2, показать inline image игрокам и запустить/остановить media audio/video: `/chgka/media` и WebSocket state synchronization работают на обеих машинах.
6. Обновить player и admin вкладки во время игры: роли восстанавливаются, состояние синхронизируется через WSS, в browser console нет CORS/mixed-content/WebSocket ошибок.
7. Вернуть тестовую игру в intro, отметить её тестовой и проверить `/chgka/admin/history`; затем пересоздать только backend container и убедиться, что запись истории сохранилась, а новая live-сессия ожидаемо требует повторного входа.
8. Запустить backup SQLite, проверить появление непустого backup-файла и выполнить его integrity check без подмены рабочей базы.
9. Проверить `https://example.com/movieclub/`, `/books/`, `/books/opds/`, `/podcasts/` и `/`: статусы и назначение совпадают с baseline до deployment.
10. С телефона повторно открыть `/chgka/play` после container recreation: frontend доступен, новый player login и admission проходят.

## Out of scope

- Покупка/настройка нового домена или `chgka.example.com`.
- Передача private SSH/GitHub keys или sudo/admin passwords агенту.
- Изменение игровых правил, wire contracts, question format или legacy-приложения.
- Полная observability stack, оркестратор, registry и автоматический CD.
