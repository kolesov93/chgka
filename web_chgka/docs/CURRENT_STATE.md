# CHGKA Web Current State

Snapshot date: 2026-08-03  
Branch at snapshot: `task/game-transitions`  
Commit at snapshot: `efa65e2` (`Split app state into domains`)

## Product decisions

- The web version is the target product.
- The parent Pyglet/VLC application is legacy and does not need continued support.
- The target environment is the public internet.
- Keeping the current localhost connection during development is acceptable. Production connectivity, HTTPS, origins, and secret management belong to a dedicated deployment task.
- `web` and `task/game-transitions` were pushed and track their corresponding remote branches at this snapshot.

## Verified baseline

- Backend: 53 tests pass.
  - 47 question parser tests;
  - 4 state helper tests;
  - 2 wheel-sector geometry tests.
- Frontend: `npm run build` succeeds.
- Backend startup loads the sample pack with all 13 questions and reaches application startup completion.
- `docker compose config --quiet` succeeds, with only a warning that the top-level Compose `version` field is obsolete.
- There are no tracked working-tree changes at the snapshot. `frontend/package-lock.json` remains untracked pending the Build/CI roadmap decision.

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

The current task is documented in `docs/tasks/0002-game-transitions.md` and remains incomplete.

Completed:

- introduced the domain-oriented `AppState`;
- migrated `backend/main.py` to the new state shape;
- retained frontend wire compatibility;
- covered state construction, reset, and serialization helpers.

Still required:

- define the transition API and how it reports side effects;
- extract spin, scoring, blitz progression, phase changes, round end, and reset from Socket.IO handlers;
- make handlers thin authorization/validation/emit adapters;
- add focused transition and invalid-phase tests;
- define cancellation or generation semantics for stale spin completion.

Scope decision: task 0002 builds a reliable transition layer while preserving the current product behavior. The new `GAME_OVER` phase remains roadmap task 12. The transition API must be extensible so that task 12 can add the phase without moving game rules back into Socket.IO handlers.

## Reproduced defects

These scenarios were reproduced against the current handlers, not inferred only from code:

1. Two concurrent `admin_score` calls can both observe `TEAM_ANSWER` and award two points.
2. Reset during an active spin does not invalidate the sleeping spin handler. When it resumes, it moves the reset game to `QUESTION_READING`.
3. A pending player who reconnects with a valid player token receives `join_success` instead of remaining pending.

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

1. Finish the pure transition layer, starting with scoring and spin completion/reset because they already have reproduced race failures.
2. Fix pending reconnect behavior and add session lifecycle tests.
3. Complete the task with backend tests and frontend build, then merge it into `web` according to `ROADMAP.md`.
4. Take Build/CI next: commit and consistently use the lockfile, add clean backend/frontend jobs, and add `.dockerignore` files.
5. Before any public deployment, take a dedicated deployment/security task covering URL routing, HTTPS, allowed origins, required secrets, token lifecycle, and persistence expectations.

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
