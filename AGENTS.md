# CHGKA: instructions for coding agents

## Scope

These instructions apply to the whole repository.

- The web application in this repository is the target and only maintained product.
- The removed Pyglet/VLC application is preserved by the annotated Git tag `legacy-pyglet-final`. Do not restore or modify it unless the user explicitly asks.
- The target deployment is the public internet. During development, the current localhost-based frontend/backend connection is intentional; do not introduce production infrastructure incidentally as part of unrelated work.
- Never commit real question packs, local runtime databases or archived legacy runtime data.

## Sources of truth

- `ROADMAP.md` — prioritized product and engineering backlog.
- `docs/CURRENT_STATE.md` — dated handoff: verified state, known defects, and the next continuation point.
- `docs/ARCHITECTURE.md` — current runtime structure and technical boundaries.
- `docs/tasks/` — decisions and scope for individual branches/tasks.

Before non-trivial work, read this file, `docs/CURRENT_STATE.md`, the relevant roadmap item, and its task file. If they disagree, call out the conflict before implementing a consequential decision.

## Development commands

Run commands from the directories shown below.

Backend checks, from `backend/`:

```bash
python3 -m pytest -q
```

Frontend checks, from `frontend/`:

```bash
npm ci
npm test
npm run build
```

Compose validation, from the repository root:

```bash
docker compose config --quiet
```

Development startup is documented in `README.md`. The backend requires `QUESTIONS_PACK_PATH`; the repository sample pack is `fixtures/sample_questions`.

## Technical boundaries

- The backend is authoritative for game state and phase transitions.
- Internal runtime state is `AppState`, split into `game`, `wheel`, `timer`, `presentation`, `pack`, and `logs`.
- `public_game_state()` is the compatibility boundary for the existing flat `state_update` Socket.IO payload. Change that wire contract only as an explicit migration.
- Question text and answers are admin-only and travel separately through `admin_question`.
- Keep the frontend Socket.IO singleton and backend URL construction in `frontend/src/socket.js`. Session event wiring belongs in `useGameSession`; do not create additional socket connections inside UI components.
- Keep Socket.IO handlers focused on authorization, input validation, transition invocation, and emits. Put game rules in testable synchronous functions/services, not directly in handlers.
- Treat spin completion, reset, scoring, reconnect, and repeated admin actions as concurrent scenarios even when the UI normally serializes them.
- Question packs contain exactly 13 sector directories. Preserve parser validation for normal, blitz, superblitz, section order, and media usage.
- Runtime state, players, admin tokens, and media tokens are currently in memory. Do not imply restart recovery until persistence is implemented.

## Security and deployment

- Never commit passwords, tokens, real question packs, or environment files.
- Treat the VPS strictly as a release and deployment target. Do not upload
  uncommitted development code, run development servers, or use it for test
  workloads; development and pre-release verification belong on the local
  machine and in CI.
- The default admin password and wildcard CORS are development behavior, not acceptable production defaults.
- Raw Markdown HTML is not safe for untrusted packs. Public deployment requires an explicit sanitization decision.
- Production is deployed under `/chgka/` with same-origin HTTPS/WSS, an exact origin allowlist and external secret injection. Keep root-path localhost behavior for development unless a task explicitly changes deployment routing.

## Change discipline

- Preserve user changes and unrelated untracked files.
- Follow the branch/task workflow in `ROADMAP.md`.
- Add or update tests for behavior changes. At minimum, run backend tests for backend work and the frontend build for frontend work.
- For every change that needs manual acceptance, keep an exact focused smoke checklist in the task file and reproduce the complete current checklist in the user-facing handoff message. Never provide only a link to the Markdown checklist.
- `frontend/package-lock.json` is committed and is the dependency source of truth. Keep it synchronized with `package.json` through npm and use `npm ci` for clean installs, Docker, and CI.
- When a task changes architecture or the handoff point, update `docs/ARCHITECTURE.md` or `docs/CURRENT_STATE.md`. Keep stable rules here and time-sensitive status in `CURRENT_STATE.md`.
