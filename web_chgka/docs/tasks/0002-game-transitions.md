# 0002: Game Transitions

Branch: `task/game-transitions`
Status: Completed

## Goal

Extract core game transition logic from Socket.IO handlers into a testable backend layer. Before doing that, reshape the server state so transition code can operate on clear domain sections instead of one mixed snapshot.

## Context

`backend/main.py` handlers currently mix several responsibilities:

- role/phase validation;
- game-state mutation;
- transition rules for spin, scoring, blitz progression, discussion, answer, and round end;
- side effects such as sounds, logs, media cleanup, and `state_update` emits;
- admin-only question refreshes.

The previous task added `backend/state.py`, so there is now an explicit typed state boundary. Discussion showed that the flat state shape still mixed game rules, wheel animation, pack UI metadata, timers, presentation, and logs. Building transitions directly on that shape would reproduce the same mess in a new module.

## Initial Scope

- Decompose the internal state into domain sections while preserving the current flat `state_update` payload.
- Decide transition layer shape and naming after the state shape is cleaner.
- Identify which transitions to extract first.
- Keep Socket.IO event names and frontend behavior compatible.
- Add focused tests for extracted transition logic.
- Keep actual network emits in `main.py`.

## Out Of Scope

- Full rewrite of all Socket.IO handlers.
- New product features such as game over, intro, blackbox, media flow, or god mode.
- Persistence/recovery.
- Frontend refactor.

`GAME_OVER` remains roadmap task 12. This task must leave an extension point for it but does not add the new phase or final-screen behavior.

## Implementation

- Added `backend/transitions.py` with synchronous transitions for game start, spin start/completion, discussion, team answer, ten-second warning, scoring, blitz progression, round end, and reset.
- Transitions mutate the existing `AppState` in place before the handler performs any network await.
- `TransitionEffects` describes transport work: logs, sounds, media-token cleanup, state broadcast, and admin-question refresh.
- `TransitionError` rejects invalid phases/actions without partial mutation.
- Added internal `wheel.spin_id`. Start increments it; reset invalidates it; completion must present the current ID.
- Socket.IO handlers now authorize, prepare nondeterministic inputs such as time/random sound, invoke a transition, and deliver effects.
- Pending-player session restore now emits `join_pending` rather than bypassing approval.

## Verification

- 71 backend tests pass, including pure transition and handler concurrency/session tests.
- Frontend production build passes.
- Backend startup loads all 13 sample questions.
- Docker Compose configuration validates; its existing obsolete `version` warning remains.
- Manual two-browser acceptance reached point 5, where image preview/share exposed a development URL bug: relative `/media/...` requests went to Vite on port 5173 instead of the backend on port 8000.
- Both admin preview and player rendering now build media URLs from the backend origin. The frontend build, all 71 backend tests, and a focused `painting1.jpg` media-token/file response check pass after the fix.
- The repeated point 5 passes: the image appears in both the admin preview and the player shared-media view.
- The complete two-browser smoke test passes, including login/reconnect, normal and blitz rounds, sounds, media, and reset during spin.

## Decisions

- Use `AppState` as the internal root state name.
- Split state into `game`, `wheel`, `timer`, `presentation`, `pack`, and `logs`.
- Keep `PublicGameState` as the flat `state_update` payload for the current frontend.
- Rename the global backend variable from `game_state` to `app_state` to match the new meaning.
- Keep transitions synchronous and use in-place mutation so phase validation and mutation are atomic within the asyncio event loop.
- Keep actual Socket.IO emits in `main.py`; transitions return explicit effects instead.
- Keep `GAME_OVER` as roadmap task 12 while ensuring it can be added through this transition layer.
