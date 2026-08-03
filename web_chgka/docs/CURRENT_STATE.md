# CHGKA Web Current State

- Snapshot date: 2026-08-04
- Completed task: `docs/tasks/0002-game-transitions.md`
- Accepted task head before closure documentation: `5d1d71e` (`Record media smoke acceptance`)

## Product decisions

- The web version is the target product.
- The parent Pyglet/VLC application is legacy and does not need continued support.
- The target environment is the public internet.
- Keeping the current localhost connection during development is acceptable. Production connectivity, HTTPS, origins, and secret management belong to a dedicated deployment task.
- Completed task branches are integrated into `web` only after automated checks and manual browser acceptance.

## Verified baseline

- Backend: 71 tests pass.
  - 47 question parser tests;
  - 4 state helper tests;
  - 3 wheel-sector/spin-selection tests;
  - 14 pure transition tests;
  - 3 handler concurrency/session tests.
- Frontend: `npm run build` succeeds.
- Backend startup loads the sample pack with all 13 questions and reaches application startup completion.
- `docker compose config --quiet` succeeds without warnings.
- The game-transitions history includes the development media-origin fix found during manual smoke testing.

The task branch also has clean-install and container checks. The GitHub Actions workflow now exists, but its first remote run is pending the branch push.

## Active task: Build and CI

The task is documented in `docs/tasks/0003-build-ci.md` on branch `task/build-ci`. Local implementation and verification are complete; the first remote GitHub Actions run is still required before acceptance and merge.

Implemented:

- committed `frontend/package-lock.json` and standardized clean frontend installs on `npm ci`;
- refreshed dependencies within existing semver ranges, removing all production `npm audit` findings;
- declared backend test dependencies in `backend/requirements-dev.txt`;
- added path-filtered GitHub Actions jobs for backend tests, frontend build, and Compose validation;
- moved development images to Node.js 24 and Python 3.14;
- added backend/frontend `.dockerignore` files and removed the obsolete Compose `version` field;
- kept Docker/Compose explicitly development-only.

Local verification:

- clean frontend install and production build pass;
- clean backend install and all 71 tests pass;
- both Docker images build;
- frontend build passes in the Node.js 24 image;
- all 71 backend tests pass in the Python 3.14 image with fixtures mounted read-only;
- Compose validation passes without warnings.

Known follow-up: a full npm audit still reports two dev-only findings rooted in Vite 4 / `esbuild`, requiring a breaking Vite upgrade. Python 3.14 also shows dependency warnings from the old FastAPI/Starlette/AnyIO stack. A separate dependency/toolchain refresh is now in the roadmap.

## Implemented

- Player and admin login, session tokens, reconnect, pending approval, kick, and logout.
- Shared server-authoritative game state and phase-based UI.
- Wheel animation, random/forced selection, used-sector skipping, and sector 13 handling.
- Normal, blitz, and superblitz rounds.
- Scoring, discussion deadline, shared sounds, and admin logs.
- Strict parsing of 13-question packs with Markdown sections and media validation.
- Admin question card and image preview/share through temporary media tokens.
- Internal state split into `game`, `wheel`, `timer`, `presentation`, `pack`, and `logs`, while retaining the current flat frontend payload.

## Completed task: game transitions

The task is documented in `docs/tasks/0002-game-transitions.md`. Implementation, automated verification, and the complete two-browser smoke test have passed.

Completed:

- introduced the domain-oriented `AppState`;
- migrated `backend/main.py` to the new state shape;
- retained frontend wire compatibility;
- covered state construction, reset, and serialization helpers.
- added synchronous transitions for start, spin start/completion, discussion, answer, scoring, blitz progression, round end, and reset;
- added explicit transport effects for logs, sounds, media-token cleanup, state broadcasts, and admin-question refresh;
- added internal `spin_id` generation so reset invalidates sleeping spin completion;
- made scoring phase mutation happen before any network await;
- fixed pending-player reconnect to remain pending;
- added pure transition and handler-level concurrency/session tests.

Scope decision: task 0002 builds a reliable transition layer while preserving the current product behavior. The new `GAME_OVER` phase remains roadmap task 12. The transition API must be extensible so that task 12 can add the phase without moving game rules back into Socket.IO handlers.

## Resolved defects

The first three scenarios were reproduced against the old handlers and now have regression tests. The fourth was found during manual browser acceptance:

1. Concurrent `admin_score` calls now award one point; the later transition is rejected after the first moves the phase to `POST_ROUND`.
2. Reset increments `spin_id`; obsolete spin completion is ignored and the game remains reset.
3. A pending player who reconnects receives `join_pending` and keeps the pending flag.
4. Admin media previews and shared player images now use the backend origin in development; previously relative `/media/...` URLs were incorrectly requested from Vite on port 5173.

Additional known gaps:

- after the sixth point, there is no `GAME_OVER`; normal round end returns to `PRE_ROUND`, while further spin is silently rejected;
- admin tokens have no TTL and older generated tokens are not centrally revoked;
- all runtime state is lost on backend restart;
- wildcard CORS and the default admin password are development-only security;
- raw Markdown HTML is unsafe for untrusted question packs;
- frontend development uses `localhost:8000`, so it does not yet support browsers running on other machines;
- media sharing is image-only even though the parser recognizes audio and video;
- there are no frontend tests, Socket.IO integration tests, or lint/typecheck; the new CI workflow still needs its first remote run.

## Repository artifacts

No Cursor-specific files remain. The useful continuity artifacts are `ROADMAP.md` and `docs/tasks/`.

Untracked files outside `web_chgka` belong to the legacy workspace. In particular, `questions/` contains about 88 MB of media and must not be treated as disposable. `intro_2024/` and the three root gong files duplicate tracked frontend assets, but should still be left untouched unless repository cleanup is explicitly requested.

Within `web_chgka`, ignored `frontend/node_modules`, `frontend/dist`, and Python/pytest caches are local build artifacts. `frontend/package-lock.json` is now the committed source of truth for reproducible frontend installs.

## Recommended continuation

1. Push `task/build-ci` and verify all three GitHub Actions jobs on the first remote run.
2. If CI is green, close task 0003, merge it into `web`, and take frontend decomposition next.
3. Before expanding media or public deployment, schedule the dependency/toolchain refresh and the dedicated deployment/security task.

## Resume checklist

```bash
git status --short --branch
```

Then read, in order:

1. `AGENTS.md`;
2. this file;
3. the next item in `ROADMAP.md`;
4. `docs/tasks/0003-build-ci.md` for the active task and `docs/tasks/0002-game-transitions.md` for the latest completed game-state work;
5. `backend/state.py` and the game handlers in `backend/main.py`.

Before changing code, rerun:

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm ci && npm run build
```
