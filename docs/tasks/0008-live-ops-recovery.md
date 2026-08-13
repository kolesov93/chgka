# 0008: Live Ops Recovery

Branch: `task/live-ops-recovery`
Status: Completed

## Goal

Give the admin targeted recovery controls for correcting a live game without resetting all score, sector, round, media, and timer state.

## Accepted behavior

- Set both scores exactly to integers from 0 through 6; reaching six does not introduce `GAME_OVER`.
- Toggle any sector 1–13 between played and available, including the active sector.
- Open a sector without spinning. The question kind comes from the pack; blitz/superblitz requires a part from 1 through 3. Opening marks the sector played, cancels stale spin completion, clears timer/media/tokens, and enters `QUESTION_READING`.
- Force only `PRE_ROUND`, `QUESTION_READING`, `DISCUSSION`, `TEAM_ANSWER`, or `POST_ROUND`. Backend normalization keeps round, spin, timer, and media state consistent; question phases require a valid round.
- Cancel a stuck spin into a clean `PRE_ROUND` while preserving score, played sectors, and the last resting sector.
- In `DISCUSSION`, set 10/20/60 seconds, set a custom 1–600 seconds, or stop the timer.
- Reuse existing Hide media and Silence behavior in the recovery panel.
- Log every recovery mutation as old value to new value.

## Implementation decisions

- Keep exceptional recovery rules in synchronous backend functions, separate from Socket.IO authorization and emits.
- After admin authorization, validate and mutate state synchronously before any network emit await; increment `spin_id` whenever recovery invalidates an in-flight spin.
- Recovery phase changes do not score or play ordinary game-transition sounds.
- UI is a separate collapsible danger-styled panel. Score, sector/round, phase, and cancel-spin require confirmation; timer, Hide, and Silence are immediate.
- Clients do not update optimistically; authoritative `state_update` drives the rendered result.

## Out of scope

- `Fade 3s`; it will be a separate all-sound task covering shared audio, effects, and the wheel loop.
- Undo/snapshots, arbitrary state editing, persistence, `GAME_OVER`, question-pack editing, or player-role changes.

## Verification

- Pure backend recovery tests for validation, state normalization, logs/effects, and stale spin completion.
- Handler tests for admin-only access, acknowledgements, media-token cleanup, admin-question refresh/clear, and state emits.
- Frontend pure tests for numeric validation and normal/blitz round payloads, plus production build.
- Two-browser smoke covering every recovery control, invalid actions, reconnect, shared media, and stuck spin cancellation.

## Verification and acceptance

Passed:

- `python3 -W error -m pytest -q`: 101 tests;
- clean `npm ci`, `npm audit`: 0 vulnerabilities;
- `npm test`: 8 assertions across playback and live-ops helpers;
- `npm run build`;
- `docker compose config --quiet` and both development image builds;
- Python 3.14 container: `pip check` and 101 tests;
- Node 24 container: 8 frontend assertions and production build.

Acceptance passed:

- all three GitHub Actions jobs (`backend`, `frontend`, and `compose`) are green on implementation commit `7a1ee91`;
- the focused admin/player browser smoke covering the recovery controls passed.
