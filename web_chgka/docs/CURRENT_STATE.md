# CHGKA Web Current State

- Snapshot date: 2026-08-08
- Latest completed task: `docs/tasks/0018-transparent-table-background.md`
- Active task: `docs/tasks/0019-ui-russian-localization.md`
- Branch: `task/ui-russian-localization`
- Status: user-facing copy inventory and glossary are defined from synchronized `web` at `e086f39`; implementation is in progress.

## Repository checkpoint

- `web` and `origin/web` are synchronized at `e086f39` before task 0019.
- Task 0019 translates rendered copy, display labels, server messages and logs while preserving all internal English identifiers and wire contracts.
- Accepted terminology includes «Восстановление игры», «Отключить», «Затухание 3 с», «Выключить звук» and explicit Russian mappings for phases, question kinds and media sections.

- `web` and `origin/web` are synchronized at `68edc87` before task 0018.
- Task 0018 preserves both 2000×2000 table canvases and runtime paths, replacing only the white exterior with a clean alpha edge.
- The final assets contain no generated pixels: an image-model draft was rejected for geometry drift, then the installed alpha helper plus an original-pixel protection mask produced the accepted candidates.
- Task 0018 planning commit: `6d55db3` (`Plan transparent table background task`).
- Task 0018 implementation commit: `f22727d` (`Remove table image backgrounds`).
- Task 0018 closure commit: `79a0d9f` (`Close transparent table background task`).
- Task 0018 merge commit: `9ff59ab` (`Merge transparent table background task`).
- Task 0018 local verification: both RGBA assets have transparent corners and identical `1940×1940+30+30` content bounds, protected interiors have zero pixel difference, dark-background previews are clean, and frontend tests/build pass.
- Focused player/host browser smoke for the normal and post-sector-13 table variants is accepted.
- Roadmap item 16 records full user-facing UI localization as a separate future task; internal event/API/code identifiers remain out of scope for translation.

- `web` and `origin/web` are synchronized at `7db38dc` before task 0017.
- Login-entrypoint decisions: `/play` is player-only, `/admin` is host-only, every host screen uses a distinct indigo page background, `/` defaults to `/play`, route-scoped restore ignores the other role's stored token, forms have no redundant visible labels, user-facing copy says «ведущий», and backend authorization remains unchanged.
- Login-entrypoint implementation commits: `8e0bbd8`, `74ec133`, `64219dc`, and `39aadbd`.
- Login-entrypoint closure commit: `1aa198c` (`Close separate login entrypoints task`).
- Login-entrypoint merge commit: `ff341d6` (`Merge separate login entrypoints task`).
- Task 0017 local verification: 189 backend tests, 39 frontend tests across 9 files, production build, and direct Vite SPA responses for root/player/admin/trailing-slash/unknown paths pass.

- `web` and `origin/web` are synchronized at `8673c25` before black-box work.
- Black-box decisions are `1B + 2A`: show the static black-box image while its static music plays; dedicated Stop, Silence, natural completion, and completed Fade end the presentation; every ending returns to the table without restoring prior shared media. The host card also shows a reconnect-aware countdown for the measured 31.488-second track.
- The implementation working tree adds strict pack metadata, admin-only effective flags, a reconnect-aware generation-guarded presentation timeline, host Start/Stop, natural-end reporting, global Silence/Fade integration, the static transparent PNG, and sample sector 09 coverage.
- Black-box implementation commits: `dff34b5` (`Implement black box presentation`) and `f5a86dd` (`Add black box countdown`).
- Black-box closure commit: `f4699c8` (`Close black box task`).
- Black-box merge commit: `722065a` (`Merge black box task`).
- Full local verification passes: 189 backend tests with warnings as errors, 36 frontend assertions across 8 test files, production build, and sample-pack CLI validation. Native Compose validation remains blocked by the installed `snap-confine` capability failure.

- `web` and `origin/web` were synchronized at `2e48860` before the next task was prepared.
- Played-question history is recorded as a problem without a chosen solution in local `web` commit `343af00`; runtime recovery is no longer P0.
- The media task starts from `343af00` on `task/media-video-sequence`.
- Media decisions are `1B + 2A + 3B + 4C`: explicit shared Next, host-reported completion, reset-to-start on end, and shared-token validity tied to the active context.
- Local media verification: 177 backend tests pass with warnings as errors; all 7 frontend test files and the production build pass. Native Compose validation is currently blocked by a broken snap-confine capability in this environment, not by a reported Compose configuration error.
- Media implementation commit `2415f5f` passed the focused two-browser smoke and is accepted.
- Media closure commit: `f60e6ac` (`Close video media sequence task`).
- Media merge commit: `aa91be0` (`Merge video media sequence task`).
- Base branch: `web`, synchronized with `origin/web` at `3d5dfca` before task work.
- Auth/security planning commit: `00a5d04` (`Plan authentication security task`).
- Auth/security implementation commit: `c371ad2` (`Implement authentication security layer`), published on `origin/task/auth-security` and browser-accepted.
- Auth/security origin-regression commit: `dc924bc` (`Automate origin acceptance checks`), published on `origin/task/auth-security`; GitHub reports no check-runs for this SHA.
- Auth/security acceptance commit: `1d3e257` (`Record auth security acceptance`), published on `origin/task/auth-security`; its push also created no Web CI run.
- Auth/security closure commit: `e9874ac` (`Close authentication security task`).
- Auth/security merge commit: `dd8b229` (`Merge authentication security task`).
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
- Intro implementation commits: `1b417a4`, `e7b7ad8`, `d18a57a`, `c6b0e70`, and `de4e847`; the latest commit includes accepted pack-backed normal/blitz author presentation.
- Intro closure commit: `3f3632a` (`Close managed intro task`).
- Intro merge commit: `e16f8c9` (`Merge managed intro task`).
- `origin/web` contains the accepted intro merge and handoff at `3d5dfca`.

## Product decisions

- The web version is the target product.
- The parent Pyglet/VLC application is legacy and does not need continued support.
- The target environment is the public internet.
- Keeping the current localhost connection during development is acceptable. Production connectivity, HTTPS, origins, and secret management belong to a dedicated deployment task.
- Completed task branches are integrated into `web` only after automated checks and manual browser acceptance.

## Verified baseline

- Backend: 177 tests pass with warnings treated as errors, including config, admin-token lifecycle, HTML sanitization, FastAPI preflight, real Engine.IO origin handshakes, video playback, bounded media sequencing, stale completion, and shared-token lifetime.
- A clean temporary Python environment passed the then-current full suite and `pip check` without broken requirements.
- Frontend: 31 pure playback/live-ops/sound-fade/inline-media/game-over/intro/session assertions pass after `npm ci`; production build and the previous full npm audit pass with zero vulnerabilities.
- Backend startup loads the sample pack with all 13 questions and reaches application startup completion.
- `docker compose config --quiet` succeeds without warnings.
- The last full development-image baseline (before tasks 0011–0012) built successfully: Python 3.14 passed `pip check` and 113 backend tests; Node 24 passed 13 frontend tests and the production build. The current source-only changes pass native tests/build and Compose validation; images were not rebuilt for task 0012.

All three GitHub Actions jobs and the focused admin/player browser smoke passed for tasks 0007, 0008, 0009, 0010, 0011, and 0012.

## Completed task: video media and sequence control

Implemented:

- resolve and privately preview pack-backed video, then share it through the existing context-bound media flow;
- render synchronized shared video with host-only Play/Pause/Stop and no native player controls;
- let the host explicitly replace shared media with the next ordered item without crossing a section, round scope, or blitz part;
- accept natural completion only from the authenticated host and only for the current playback generation, then reset the visible item to stopped position zero;
- keep an expired token usable only while it remains the exact active shared item, revoking it on Hide, replacement, or context change;
- restore shared media rendering and host controls after reconnect.

Verification: 177 backend tests with warnings as errors, 31 frontend assertions, and the production build pass. The focused sectors 02/06/08 two-browser smoke, playback completion, Next behavior, and reconnect passed. Remote CI remains the publication gate.

## Completed task: authorization and security

Implemented:

- require explicit development/production configuration, an admin password, and exact allowed browser origins; production rejects the development password, short secrets, non-HTTPS origins, and wildcard/path origins;
- use one opaque admin token with a fixed 12-hour default TTL, replacement/revoke/logout behavior, and role-plus-token validation on every privileged Socket.IO event;
- keep one active host session intentionally: a new password login revokes the older or stuck host session instead of creating independent parallel admin sessions;
- carry the original expiry through reconnect and automatically clear the browser's admin role/private data with an explicit re-login message;
- apply the same exact-origin allowlist to FastAPI CORS and Socket.IO/WebSocket handshakes;
- sanitize every Markdown-derived question and intro fragment through a pinned `nh3` allowlist while retaining managed media placeholders;
- document development startup, production env injection, local CORS checks, and the remaining deployment boundary.

Verification: the full baseline above passes, and focused browser smoke passed on `c371ad2`. FastAPI preflight and actual Engine.IO allowed/denied-origin handshakes are automated and no longer belong to manual smoke. GitHub created no Web CI run for any of the three task-branch pushes despite the matching active workflow; the merged `web` push is the remaining remote gate.

## Completed task: intro

Implemented:

- add the authoritative `INTRO` phase between lobby and the first `PRE_ROUND`;
- enter intro silently, let the host start the existing meeting track once, and show static `00`, pack-backed author cards for sectors 1–12, then special static `13`;
- give the host current/next slide context, reconnect-aware remaining-track time, and guarded one-step navigation;
- parse optional root `intro.md` speech and expose it only through admin-only `pack_info`;
- transition after slide `13` to the real score/table view at 0:0 and stop any remaining intro sound.
- offer a dedicated Live Ops full reset to intro that clears progress/runtime context, stops audio, and restores silent slide `00` plus the manual music button.
- require author metadata across the pack, support optional city/direct author photos, show one card for a normal sector and three part-author cards in one row for blitz/superblitz, and independently use a generated static silhouette where a pack photo is absent.
- keep the twelve previous intro photos in the sample pack: normal-sector photos beside their questions, and the old sector 04/07 photos beside the first parts of the blitz/superblitz; EXIF/GPS metadata is removed.

Verification: all 139 backend tests with warnings treated as errors, all 25 frontend tests, the production build, sample-pack CLI validation, and Compose configuration pass locally. The focused admin/player smoke passed on `de4e847`; remote CI will run after integration into `web`.

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

- all runtime state is lost on backend restart;
- admin/player/media tokens and game state remain process-local and support only one backend worker;
- player reconnect tokens still have no TTL/rotation;
- production TLS, reverse proxy, DNS, secret injection, rate limiting, and deployment are not implemented;
- frontend development uses `localhost:8000`, so it does not yet support browsers running on other machines;
- video sharing/playback, media queue/next, duration extraction, and automatic ended state remain unimplemented;
- frontend coverage is limited to pure playback/live-ops/sound-fade/inline-media/game-over/intro/session helpers; there are no automated browser/component tests, full Socket.IO session integration tests, or lint/typecheck.

## Repository artifacts

No Cursor-specific files remain. The useful continuity artifacts are `ROADMAP.md` and `docs/tasks/`.

Untracked files outside `web_chgka` belong to the legacy workspace. In particular, `questions/` contains about 88 MB of media and must not be treated as disposable. `intro_2024/` and the three root gong files duplicate tracked frontend assets, but should still be left untouched unless repository cleanup is explicitly requested.

Within `web_chgka`, ignored `frontend/node_modules`, `frontend/dist`, and Python/pytest caches are local build artifacts. `frontend/package-lock.json` is now the committed source of truth for reproducible frontend installs.

## Recommended continuation

1. Publish local `web` with merge `9ff59ab` plus this handoff and confirm the Web CI run.
2. After green remote verification, remove the merged local task branch; no remote task branch was created.
3. Choose the next roadmap item; played-question history needs a product decision, while personal questions and full UI localization are bounded candidates.

## Resume checklist

```bash
git status --short --branch
```

Then read, in order:

1. `AGENTS.md`;
2. this file;
3. the next item in `ROADMAP.md`;
4. completed tasks 0018, 0017, 0016, 0015, 0014, 0013, 0012, 0011, 0010, 0009, 0008, 0007, 0006, 0005, 0004, 0003, and 0002 for the latest work;
5. `backend/state.py` and the game handlers in `backend/main.py`.

Before changing code, rerun:

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm ci && npm test && npm run build
```
