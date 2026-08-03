# CHGKA Web Current State

- Snapshot date: 2026-08-04
- Branch at snapshot: `task/game-transitions`
- Last completed task commit before this snapshot: `1cf5320` (`Update transition task handoff`)

## Product decisions

- The web version is the target product.
- The parent Pyglet/VLC application is legacy and does not need continued support.
- The target environment is the public internet.
- Keeping the current localhost connection during development is acceptable. Production connectivity, HTTPS, origins, and secret management belong to a dedicated deployment task.
- `web` tracks `origin/web`. The current task branch contains local documentation and implementation commits to push after review/manual acceptance.

## Verified baseline

- Backend: 71 tests pass.
  - 47 question parser tests;
  - 4 state helper tests;
  - 3 wheel-sector/spin-selection tests;
  - 14 pure transition tests;
  - 3 handler concurrency/session tests.
- Frontend: `npm run build` succeeds.
- Backend startup loads the sample pack with all 13 questions and reaches application startup completion.
- `docker compose config --quiet` succeeds, with only a warning that the top-level Compose `version` field is obsolete.
- The branch also contains the development media-origin fix found during manual smoke testing. `frontend/package-lock.json` remains untracked pending the Build/CI roadmap decision.

The checks use the local installed environments. There is no clean-environment CI yet, so they prove the current checkout works locally, not full reproducibility.

## Implemented

- Player and admin login, session tokens, reconnect, pending approval, kick, and logout.
- Shared server-authoritative game state and phase-based UI.
- Wheel animation, random/forced selection, used-sector skipping, and sector 13 handling.
- Normal, blitz, and superblitz rounds.
- Scoring, discussion deadline, shared sounds, and admin logs.
- Strict parsing of 13-question packs with Markdown sections and media validation.
- Admin question card and image preview/share through temporary media tokens.
- Internal state split into `game`, `wheel`, `timer`, `presentation`, `pack`, and `logs`, while retaining the current flat frontend payload.

## Active task: game transitions

The current task is documented in `docs/tasks/0002-game-transitions.md`. Implementation and automated verification are complete; manual browser acceptance is in progress and branch integration remains.

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
- there are no frontend tests, Socket.IO integration tests, lint/typecheck, or CI.

## Repository artifacts

No Cursor-specific files remain. The useful continuity artifacts are `ROADMAP.md` and `docs/tasks/`.

Untracked files outside `web_chgka` belong to the legacy workspace. In particular, `questions/` contains about 88 MB of media and must not be treated as disposable. `intro_2024/` and the three root gong files duplicate tracked frontend assets, but should still be left untouched unless repository cleanup is explicitly requested.

Within `web_chgka`, ignored `frontend/node_modules`, `frontend/dist`, and Python/pytest caches are local build artifacts. `frontend/package-lock.json` is a real dependency lockfile but is intentionally undecided rather than ignored.

## Recommended continuation

1. Repeat media point 5 of the two-browser smoke test, then finish the remaining acceptance checks for sounds and reset during spin.
2. If accepted, push the branch commits, finish the task document, remove the completed roadmap item, and merge into `web`.
3. Take Build/CI next: commit and consistently use the lockfile, add clean backend/frontend jobs, and add `.dockerignore` files.
4. Before any public deployment, take a dedicated deployment/security task covering URL routing, HTTPS, allowed origins, required secrets, token lifecycle, and persistence expectations.

## Resume checklist

```bash
git status --short --branch
```

Then read, in order:

1. `AGENTS.md`;
2. this file;
3. the active item in `ROADMAP.md`;
4. `docs/tasks/0002-game-transitions.md`;
5. `backend/state.py` and the game handlers in `backend/main.py`.

Before changing code, rerun:

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm run build
```
