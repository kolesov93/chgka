# 0001: Game State Schema

Branch: `task/game-state-schema`

## Summary

Made the server game state explicit without changing the current Socket.IO payload shape. This is a low-risk first step before extracting transition logic or adding more game modes.

## What Changed

- Added `backend/state.py`.
- Moved game phase constants from `main.py` to `state.py`.
- Added `TypedDict` models for score, round, shared media, and game state.
- Added state helpers:
  - `create_initial_game_state()`
  - `reset_game_state()`
  - `public_game_state()`
- Replaced the literal `game_state` initializer in `main.py` with `create_initial_game_state()`.
- Routed `state_update` emits through `emit_state_update()`, which uses `public_game_state()`.
- Replaced manual `admin_reset` field mutation with `reset_game_state()`.
- Added focused tests in `backend/tests/test_state.py`.

## Decisions

- Use `TypedDict` for the first iteration.
- Do not introduce Pydantic or dataclass models yet.
- Keep `state_update` wire-compatible with the current frontend.
- Keep `public_game_state()` as a compatibility boundary for now; it currently returns a deep copy of the same payload.
- `admin_reset` resets to `PRE_ROUND`, clears runtime fields, and preserves loaded `question_types`.
- Re-evaluate Pydantic/dataclass later only if runtime validation, persistence, or stricter public/admin payload models create a real need.

## Why

The current `game_state` was an implicit mutable dict in `main.py`. A full model or transition-service refactor would be too much for this first task. `TypedDict` plus helper functions documents the current contract and gives later work a clear migration point without changing runtime behavior broadly.

## State Boundary Notes

Current `state_update` remains intentionally compatible. It still includes fields such as `question_types`, animation context, logs, current round context, and shared media. The boundary is now explicit in code, so later tasks can narrow public/admin payloads in one place.

Related state still outside this task:

- `global_settings`
- `players_list`
- `admin_tokens`
- `media_tokens`
- `pack_admin_info`
- `loaded_pack`

## What Remains

- Extract real transition logic from Socket.IO handlers.
- Decide whether public/admin payloads should diverge.
- Decide whether a future runtime model should be Pydantic, dataclass, or remain `TypedDict`.
- Add broader tests for game transitions once that layer exists.
