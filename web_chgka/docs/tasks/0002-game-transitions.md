# 0002: Game Transitions

Branch: `task/game-transitions`

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

## Decisions To Make

- What exact sections should internal state have: `game`, `wheel`, `timer`, `presentation`, `pack`, `logs`?
- Should the internal root type be called `AppState`, `ServerState`, or something else?
- How far should `main.py` be migrated in this task versus using compatibility accessors?
- Should transitions mutate the internal state in place or return a new state?
- What should a transition return besides state mutation: logs, sounds, notifications, admin question refresh flags?
- Which transition should be extracted first: scoring, round end, reset, spin result, or discussion timer transitions?
- How much side-effect description belongs in transition results versus remaining in handlers?

## Current Direction

- First reshape state into domain sections.
- Keep `public_game_state()` returning the existing flat frontend payload.
- Do not change Socket.IO event names or frontend behavior.
- Only start extracting transition functions after this state split is in place.

## Decisions

- Use `AppState` as the internal root state name.
- Split state into `game`, `wheel`, `timer`, `presentation`, `pack`, and `logs`.
- Keep `PublicGameState` as the flat `state_update` payload for the current frontend.
- Rename the global backend variable from `game_state` to `app_state` to match the new meaning.
- Do not add transition functions until the state split is complete and tested.
