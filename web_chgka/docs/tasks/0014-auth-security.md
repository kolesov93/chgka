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

## Implemented locally

- Added strict startup configuration for environment, password, exact origins, and bounded admin-token TTL; development Compose supplies explicit local values and production has no code defaults.
- Replaced the unbounded admin-token dictionary with one opaque in-memory token with fixed expiry, revoke/replacement/logout behavior, and role-plus-token checks on every privileged event.
- Added browser expiry handling: reconnect preserves the original deadline, the UI automatically drops admin role/private data at expiry, and stale/replaced sessions show a re-login message.
- Applied one CORS allowlist to FastAPI and Socket.IO and disabled credentialed cross-origin HTTP requests.
- Sanitized all question/answer/comment/source/intro HTML with pinned `nh3`, preserving only safe formatting, links, and managed media placeholders.
- Added production env documentation, a non-secret `.env.example`, local CORS commands, and focused backend/frontend regression coverage.

## Local verification

- 172 backend tests pass with warnings treated as errors, both in the working environment and a clean temporary venv; `pip check` reports no broken requirements there.
- 30 frontend assertions pass after `npm ci`; the production build succeeds and `npm audit` reports zero vulnerabilities.
- The sample pack validator reports 13 valid questions, 19 authors, 6 parts, and 9 media files.
- `docker compose config --quiet` succeeds.

Manual browser acceptance and remote CI are still pending.

## Focused manual acceptance

1. Start normal development Compose, log in as the host with `admin123`, join from a second browser as a player, and confirm normal lobby/game controls plus the private question card.
2. Reload the host browser and confirm the role, controls, pack info, and current private question are restored without another password prompt.
3. Log in as the host from a second browser/profile. The original host must return to login with the replacement-session message; its old token must not restore on reload.
4. Log out from the current host, reload, and confirm the browser remains logged out.
5. Restart with `ADMIN_TOKEN_TTL_SECONDS=60 docker compose up --build`, log in as the host, and do not click anything. After 60 seconds the browser must automatically return to login, clear private admin UI, and show the expiry message.
6. Run both CORS preflight commands from `README.md`: port 5173 must be allowed and port 5174 rejected.
7. Open the sample image question and confirm its inline preview still renders; ordinary Markdown formatting in question/answer/intro must remain intact.
