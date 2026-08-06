# 0014: Авторизация и безопасность

Branch: `task/auth-security`
Status: In progress

## Goal

Убрать development-only границы из авторизации и обработки question packs: сделать запуск окружения явным, ограничить browser origins, дать admin-токену проверяемый жизненный цикл и исключить исполнение HTML из недоверенного пака.

## Current context

- Backend принимает `ADMIN_PASSWORD` с небезопасным fallback `admin123` во всех окружениях.
- FastAPI и Socket.IO разрешают любой origin; development использует разные localhost-порты, production планируется same-origin через HTTPS/WSS.
- Admin-токены — opaque random strings в памяти без TTL. Browser хранит токен в `localStorage`; явный logout и restart отзывают его, но повторная авторизация оставляет старые токены действующими.
- `require_admin` проверяет только Socket.IO role, поэтому срок токена нельзя ввести одной проверкой при reconnect.
- Player-token уже служит только ключом reconnect к записи игрока и не даёт admin-права.
- Python-Markdown сохраняет raw HTML, который затем попадает в `dangerouslySetInnerHTML` вопроса и admin-only intro-речи.

## Accepted behavior

- Требовать явный `CHGKA_ENV=development|production`; неизвестное или отсутствующее значение останавливает импорт приложения с понятной ошибкой.
- В обоих режимах требовать `ADMIN_PASSWORD` и `ALLOWED_ORIGINS`. Development Compose явно задаёт известный локальный пароль и `http://localhost:5173`; production не имеет code fallback, запрещает `admin123`, короткий пароль и не-HTTPS origins.
- Принимать comma-separated origins без wildcard, path, query или fragment и использовать один список для FastAPI CORS и Socket.IO origin checks.
- Выдавать один активный opaque admin-токен с фиксированным TTL, по умолчанию 12 часов. Новый password login отзывает прежние admin-токены; reconnect не продлевает TTL.
- Хранить admin token в Socket.IO session и проверять role, token и expiry на каждом privileged action. Истечение/отзыв переводит browser в player role, очищает private admin UI и требует повторного ввода пароля.
- Явный logout, новый login и restart backend отзывают admin-токен. Старый/неизвестный token при restore не восстанавливает admin role.
- Сохранить существующий player-token: он восстанавливает запись игрока, отзывается при logout/kick/restart и не получает временного TTL в этой задаче.
- Санитизировать весь HTML после Markdown conversion через строгий allowlist в обоих режимах. Сохранить безопасное форматирование, ссылки и generated `span.media-placeholder[data-media-ref]`; удалить executable/embedded content, event/style attributes и опасные URL-схемы.
- Добавить frontend-состояние для явного сообщения об истёкшей admin-сессии и предпочитать admin restore, если в `localStorage` неожиданно присутствуют оба вида токена.

## Implementation decisions

- Вынести parsing/validation env в отдельный testable `backend/config.py`; не читать `.env` и не хранить secrets в repository.
- Хранить opaque tokens server-side, не вводить JWT/signing secret или refresh token до persistence.
- Проверять фиксированный absolute expiry и не делать sliding sessions: двенадцати часов достаточно для одной игры, а поведение остаётся предсказуемым.
- Считать один token допустимым для reconnect/нескольких вкладок одного browser profile; новый password login создаёт новый token и отзывает предыдущий.
- Использовать `nh3` с pinned version и явным allowlist вместо собственного HTML parser.
- Сохранить current-origin frontend production routing; отдельный `VITE_BACKEND_URL` нужен только при будущем split-origin deployment.

## Production environment

Required:

```text
CHGKA_ENV=production
QUESTIONS_PACK_PATH=/data/questions
ADMIN_PASSWORD=<external secret, at least 12 characters>
ALLOWED_ORIGINS=https://chgka.example.com
```

Optional:

```text
ADMIN_TOKEN_TTL_SECONDS=43200
```

## Out of scope

- TLS certificates, reverse proxy, DNS, production images/deployment, trusted-host/rate-limit proxy policy, password recovery or separate user accounts.
- Persistence across restart, shared token store for multiple backend workers, match identity, player-token TTL/rotation, HttpOnly cookies and refresh tokens.
- CSRF cookies (authentication remains explicit Socket.IO bearer-style tokens), content-security-policy headers and a general upload UI for packs.

## Verification plan

- Pure config tests for missing/invalid environment, production password/origin guards, normalized multiple origins and token TTL bounds.
- Token tests for fixed expiry, revoke, single-token replacement, reconnect, logout and privileged action denial after expiration.
- FastAPI/Socket.IO configuration assertions and manual localhost origin smoke on ports 5173/5174.
- Parser tests proving scripts, event/style attributes, unsafe URLs and embeds are removed while normal Markdown and opaque media placeholders remain intact.
- Frontend tests/build for session-expiry state and mutually exclusive restore payloads.
- Full backend tests with warnings-as-errors, frontend tests/build, sample-pack validator and Compose validation.
