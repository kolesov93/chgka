# 0014: Авторизация и безопасность

Branch: `task/auth-security`
Status: Completed

## Result

- Backend requires explicit `CHGKA_ENV=development|production`, `ADMIN_PASSWORD`, and exact comma-separated `ALLOWED_ORIGINS`; production rejects `admin123`, passwords shorter than 12 characters, non-HTTPS origins, wildcards, and origin paths.
- Development Compose keeps the explicit local password/origin, while `.env.example` documents externally injected production values without loading or committing secrets.
- One opaque in-memory admin token has a fixed non-sliding TTL (12 hours by default). New password login, logout, expiry, and backend restart revoke the previous host session; every privileged event validates role plus token.
- The browser restores the original expiry deadline, automatically drops admin role/private data at expiry, and displays replacement/expiry messages. Admin restore takes precedence over an accidentally retained player token.
- FastAPI CORS and Socket.IO use the same exact-origin allowlist. Automated tests exercise both HTTP preflight and real allowed/denied Engine.IO handshakes.
- All Markdown-derived question, answer, comment, source, and intro HTML is sanitized with pinned `nh3`; safe formatting, links, and managed media placeholders remain available.

## Decisions

- Keep a single active host session: a new password login is the simple recovery mechanism for an old, lost, or stuck admin session. Independent concurrent hosts and a separate “logout all sessions” flow are intentionally not introduced.
- Keep opaque server-side tokens instead of JWT/refresh tokens until persistence exists. Player reconnect-token behavior is unchanged.
- Keep localhost split-origin development and current-origin production frontend routing; TLS, reverse proxy, DNS, deployment, rate limiting, and multi-worker/shared state remain separate work.
- Sanitize after Markdown conversion with an allowlist rather than trying to validate raw Markdown/HTML manually.

## Verification

- 173 backend tests pass with warnings treated as errors; a clean temporary Python environment passed the then-current full suite and `pip check`.
- 30 frontend assertions pass after `npm ci`; production build and zero-vulnerability npm audit pass.
- Sample-pack validation and `docker compose config --quiet` pass.
- Focused browser acceptance passed on implementation commit `c371ad2`, covering login, reconnect, host replacement, logout, 60-second expiry, private question data, and inline media regression.
- Implementation commits `c371ad2` and `dc924bc` are published on `origin/task/auth-security`. GitHub did not create a Web CI run for the task pushes despite the matching active workflow; the merged `web` push remains the final remote CI gate.

## Remaining boundaries

- All game state and all token stores are process-local, support one backend worker, and disappear on restart.
- Player tokens still have no TTL/rotation. TLS/HTTPS/WSS termination, secret injection, trusted-host/rate-limit policy, and production deployment are not implemented.
