# CHGKA Web Current State

- Snapshot date: 2026-08-05
- Latest completed task: `docs/tasks/0012-game-over.md`
- Active task: `docs/tasks/0013-intro.md`
- Branch: `task/intro`
- Status: task 0012 is accepted and integrated locally; task 0013 contract is defined and implementation is in progress. Publishing the updated `web` branch is still pending.

## Repository checkpoint

- Base branch: `web`, synchronized with `origin/web` at `ad10ac8` before task work.
- Live Ops merge commit: `1708f1d` (`Merge live ops recovery task`).
- The task closure commit `8d104f4` and implementation commit `7a1ee91` are both reachable from local `web`.
- Live Ops implementation commit `7a1ee91` is published on `origin/task/live-ops-recovery` and accepted.
- Media/audio merge commit: `ae484f9` (`Merge managed audio media task`).
- The previous publication checkpoint is resolved: `origin/web` contains the Live Ops merge and handoff.
- Sound fade implementation commits `9c3ba27` and `bdd225e` are published on `origin/task/sound-fade` and accepted.
- Sound fade closure commit: `8cc7e96` (`Close synchronized sound fade task`).
- Sound fade merge commit: `3c6cccb` (`Merge synchronized sound fade task`).
- `origin/web` contains the accepted sound-fade merge and handoff at `218aa2a`.
- Director sound controls commit `2fda870` is published on `origin/task/director-sound-controls` and accepted.
- Director sound controls closure commit: `fd63ff3` (`Close director sound controls task`).
- Director sound controls merge commit: `1ee7156` (`Merge director sound controls task`).
- Director sound controls handoff commit: `c64d548` (`Record director sound controls handoff`).
- `origin/web` contains the accepted director sound controls merge and handoff at `c64d548`.
- Inline image previews commit `280f930` is published on `origin/task/inline-image-previews` and accepted.
- Inline image previews closure commit: `2a8aeeb` (`Close inline image preview task`).
- Inline image previews merge commit: `f8503e3` (`Merge inline image preview task`).
- Inline image previews handoff commit: `c829311` (`Record inline image preview handoff`).
- `origin/web` contains the accepted inline image preview merge and handoff at `c829311`.
- Game-over implementation commit `1e8a2aa` is published, remotely verified, and accepted; the temporary remote branch ref has since been removed.
- Game-over closure commit: `aef4553` (`Close explicit game over task`).
- Game-over merge commit: `ea46a55` (`Merge explicit game over task`).
- Local `web` contains the accepted merge and is ahead of `origin/web`; push is pending.

## Product decisions

- The web version is the target product.
- The parent Pyglet/VLC application is legacy and does not need continued support.
- The target environment is the public internet.
- Keeping the current localhost connection during development is acceptable. Production connectivity, HTTPS, origins, and secret management belong to a dedicated deployment task.
- Completed task branches are integrated into `web` only after automated checks and manual browser acceptance.

## Verified baseline

- Backend: 118 tests pass with warnings treated as errors.
  - 47 question parser tests;
  - 5 synchronized sound-control tests;
  - 9 live-ops recovery tests;
  - 5 media identity/playback tests;
  - 5 state helper tests;
  - 3 wheel-sector/spin-selection tests;
  - 18 pure transition tests;
  - 17 handler concurrency/session/media/live-ops/sound-control/game-over tests;
  - 9 pack-validator CLI, sector-directory, and media-path tests.
- Frontend: 20 pure playback/live-ops/sound-fade/inline-media/game-over tests and the production build pass; the last clean install and full audit reported zero vulnerabilities.
- Backend startup loads the sample pack with all 13 questions and reaches application startup completion.
- `docker compose config --quiet` succeeds without warnings.
- The last full development-image baseline (before tasks 0011–0012) built successfully: Python 3.14 passed `pip check` and 113 backend tests; Node 24 passed 13 frontend tests and the production build. The current source-only changes pass native tests/build and Compose validation; images were not rebuilt for task 0012.

All three GitHub Actions jobs and the focused admin/player browser smoke passed for tasks 0007, 0008, 0009, 0010, 0011, and 0012.

## Completed task: game over

Implemented:

- add the authoritative `GAME_OVER` phase after the host completes review of a six-point round;
- clear active round/media/timer/wheel context and play the existing final sound once;
- show all clients the graphical final score and a winner card, including after reconnect;
- replace normal host actions with a new-game reset while retaining director controls and recovery access.

Verification: all 118 backend tests with warnings treated as errors, all 20 frontend tests, the production build, and Compose validation pass locally; all three GitHub Actions jobs and the focused two-browser smoke passed on `1e8a2aa`.

## Completed task: inline image previews

Implemented:

- privately resolve current image refs through the existing context-bound admin media-token flow;
- replace blank image placeholders in host-only question HTML with compact lazy-loaded thumbnails and visible pending/error fallbacks;
- make thumbnail clicks reuse the private token in the existing media control block without changing player presentation;
- retry failed resolution on click and ignore late callbacks after the question/part changes;
- preserve non-image placeholders, backend token validation, sharing state, and the player UI.

Verification: all 17 frontend tests and the production build pass locally; all three GitHub Actions jobs and the focused sample-question-02 browser smoke passed on `280f930`.

## Completed task: director sound controls

Implemented:

- one always-visible director sound block containing master volume, `Fade 3s`, and `Silence`;
- unchanged sound events and local immediate-stop behavior for Silence;
- `Hide media` retained as the only media action at the bottom of Live Ops.

Verification: frontend assertions and the production build pass locally; all three GitHub Actions jobs and the focused browser check passed on `2fda870`.

## Completed task: synchronized sound fade

Implemented:

- a reconnect-aware `settings_update.sound_control` snapshot with `normal`, `fading`, and `stopped` modes;
- generation guards preventing sleeping Fade completion from stopping later effect, Silence, spin, media playback, or repeated Fade commands;
- smooth repeated Fade from the current level and a persistent stopped mode for reconnect;
- a shared 0 to -60 dB curve with 25 ms updates, avoiding the perceived end-cutoff of linear amplitude fading;
- one frontend multiplier shared by managed audio, effects, and the wheel's existing intrinsic fade;
- a `Fade 3s` button beside Silence in Live Ops and authoritative shared-audio stop at completion.

Verification: clean install/audit, 113 backend tests, 13 frontend assertions, production build, Compose validation, both image builds, Python 3.14 dependency/tests, and Node 24 tests/build pass.

Acceptance: all three GitHub Actions jobs passed on `bdd225e`; the focused two-browser smoke passed, including the perceptual fade of the wheel sound.

## Completed task: live-ops recovery

Implemented:

- exact 0–6 score repair and played/available sector toggles;
- direct normal/blitz/superblitz opening with selected blitz part and played marking;
- invariant-preserving force phase controls for all five implemented phases;
- stuck-spin cancellation protected by `spin_id` generation;
- discussion timer presets, custom 1–600 seconds, and stop;
- a separate collapsible danger-styled admin panel reusing Hide media and Silence;
- acknowledgements, admin notifications, authoritative state updates, and old-to-new logs.

Acceptance: all three GitHub Actions jobs and the focused two-browser recovery smoke passed on implementation commit `7a1ee91`.

## Completed task: managed media flow — audio

Implemented:

- section-aware opaque `media_ref` values replace client-supplied media paths/types;
- current-round catalogs isolate normal questions and current blitz parts;
- temporary tokens are bound to expiry, spin generation, round/part, scope, section, exact reference, type, name, and file;
- image sharing is migrated to the same contract;
- sample question 03 audio can be privately previewed, shown, and controlled by the admin through server-authoritative play/pause/stop state;
- current and reconnecting clients align playback using server timestamps; players have no native playback controls;
- inline image preview remains deliberately separate as roadmap item 16.

Acceptance: all GitHub Actions jobs and the focused two-browser smoke passed, including sample question 03 audio and the existing question 02 image flow.

## Completed task: pack validator

The task is documented in `docs/tasks/0006-pack-validator.md` on branch `task/pack-validator`. Implementation, automated verification, remote CI, and minimal browser acceptance are complete.

Implemented:

- added `python -m validate_pack /path/to/pack` with stable human-readable output and exit codes 0/1/2;
- reused the backend startup parser instead of creating a second validation path;
- rejected extra two-digit numeric sectors, absolute media paths, traversal, and symlinks escaping a question folder;
- documented pack structure, frontmatter, sections, blitz/superblitz, media rules, CLI usage, and raw-HTML trust limitations.

Local verification:

- all 80 backend tests pass with warnings treated as errors;
- sample-pack CLI output reports the expected question, part, and media counts;
- clean frontend install, full npm audit, and production build pass with zero vulnerabilities;
- backend image build, CLI, dependency check, all tests, and sample-pack startup pass in Python 3.14;
- Compose configuration validates without warnings.

Acceptance: all three GitHub Actions jobs and the minimal two-browser sample-pack smoke pass.

## Completed task: dependency and toolchain refresh

The task is documented in `docs/tasks/0005-dependency-toolchain-refresh.md` on branch `task/dependency-toolchain-refresh`. Implementation, automated verification, remote CI, and focused browser regression acceptance are complete.

Implemented:

- upgraded Vite/plugin-react to 8.2.0/6.0.5 while keeping React 18 and Tailwind CSS 3;
- upgraded FastAPI/Uvicorn/Python Socket.IO to 0.141.1/0.52.1/5.16.3 while leaving Starlette and AnyIO transitively managed by FastAPI;
- added full npm audit, pip dependency checks, and Python warnings-as-errors to CI.

Local verification:

- clean npm install, full audit, and production build pass with zero vulnerabilities;
- clean Python install, `pip check`, and all 71 warnings-as-errors tests pass;
- both Docker images build;
- the frontend build passes in Node.js 24;
- backend dependency checks, all tests, and sample-pack startup pass in Python 3.14;
- an isolated cross-container Socket.IO websocket handshake succeeds;
- Compose configuration validates without warnings.

Acceptance: all three remote GitHub Actions jobs and the focused two-browser smoke pass.

## Completed task: frontend decomposition

The task is documented in `docs/tasks/0004-frontend-decomposition.md` on branch `task/frontend-decomposition`. The implementation, automated checks, remote CI, and focused browser regression smoke are complete.

Implemented:

- reduced `frontend/src/App.jsx` from 899 to 156 lines, leaving phase routing and layout at the top level;
- centralized backend/media URLs and the Socket.IO singleton in `frontend/src/socket.js`;
- moved session state/event wiring, discussion timing, and sound-event bridging into dedicated hooks;
- extracted admin question/media, admin controls, shared media, header, and notification components;
- preserved existing Socket.IO event names, payloads, storage keys, confirmations, and state ownership.

Verification:

- clean frontend install and production build pass;
- all 71 backend tests pass;
- Compose validation passes without warnings.
- all three GitHub Actions jobs pass;
- the focused two-browser smoke covering login/session restore, normal and blitz controls, discussion timing/sounds, media preview/share/hide, moderation/logout, and reset during spin passes.

## Completed task: Build and CI

The task is documented in `docs/tasks/0003-build-ci.md` on branch `task/build-ci`. Local clean-environment checks, container checks, and the remote backend/frontend/Compose CI jobs all pass.

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

The Vite/esbuild audit findings and Python 3.14 dependency warnings discovered in this task are resolved by the completed dependency/toolchain refresh.

## Implemented

- Player and admin login, session tokens, reconnect, pending approval, kick, and logout.
- Shared server-authoritative game state and phase-based UI.
- Wheel animation, random/forced selection, used-sector skipping, and sector 13 handling.
- Normal, blitz, and superblitz rounds.
- Scoring, discussion deadline, shared sounds, and admin logs.
- Strict parsing of 13-question packs with Markdown sections and media validation.
- Admin question card and managed image/audio preview/share through context-bound temporary media tokens.
- Server-authoritative audio play/pause/stop state with reconnect synchronization and no player controls.
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

Scope decision: task 0002 built the transition layer while preserving the then-current product behavior. Task 0012 now adds `GAME_OVER` through that transition API without moving game rules back into Socket.IO handlers.

## Resolved defects

The first three scenarios were reproduced against the old handlers and now have regression tests. The fourth was found during manual browser acceptance:

1. Concurrent `admin_score` calls now award one point; the later transition is rejected after the first moves the phase to `POST_ROUND`.
2. Reset increments `spin_id`; obsolete spin completion is ignored and the game remains reset.
3. A pending player who reconnects receives `join_pending` and keeps the pending flag.
4. Admin media previews and shared player images now use the backend origin in development; previously relative `/media/...` URLs were incorrectly requested from Vite on port 5173.

Additional known gaps:

- admin tokens have no TTL and older generated tokens are not centrally revoked;
- all runtime state is lost on backend restart;
- wildcard CORS and the default admin password are development-only security;
- raw Markdown HTML is unsafe for untrusted question packs;
- frontend development uses `localhost:8000`, so it does not yet support browsers running on other machines;
- video sharing/playback, media queue/next, duration extraction, and automatic ended state remain unimplemented;
- frontend coverage is limited to pure playback/live-ops/sound-fade/inline-media/game-over helpers; there are no browser/component tests, Socket.IO integration tests, or lint/typecheck.

## Repository artifacts

No Cursor-specific files remain. The useful continuity artifacts are `ROADMAP.md` and `docs/tasks/`.

Untracked files outside `web_chgka` belong to the legacy workspace. In particular, `questions/` contains about 88 MB of media and must not be treated as disposable. `intro_2024/` and the three root gong files duplicate tracked frontend assets, but should still be left untouched unless repository cleanup is explicitly requested.

Within `web_chgka`, ignored `frontend/node_modules`, `frontend/dist`, and Python/pytest caches are local build artifacts. `frontend/package-lock.json` is now the committed source of truth for reproducible frontend installs.

## Recommended continuation

1. Publish the updated `web` branch containing the accepted task 0012 merge.
2. Take roadmap item 9 in a separate branch and define the intro pack/state/UI contract before implementation.
3. Keep authorization/security and persistence as mandatory gates before public deployment.

## Resume checklist

```bash
git status --short --branch
```

Then read, in order:

1. `AGENTS.md`;
2. this file;
3. the next item in `ROADMAP.md`;
4. completed tasks 0012, 0011, 0010, 0009, 0008, 0007, 0006, 0005, 0004, 0003, and 0002 for the latest work;
5. `backend/state.py` and the game handlers in `backend/main.py`.

Before changing code, rerun:

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm ci && npm test && npm run build
```
