# 0001: Game State Schema

Branch: `task/game-state-schema`

## Goal

Make the server game state explicit and easier to change safely before adding more phases, admin controls, media flow, intro, blackbox, personal questions, and game over.

## Context

Current state is stored mostly in mutable module-level dictionaries in `backend/main.py`:

- `game_state`: public-ish game state broadcast to clients via `state_update`.
- `global_settings`: global audio/settings state.
- `players_list`: player/admin session records.
- `admin_tokens`: in-memory admin auth tokens.
- `media_tokens`: temporary media access tokens.
- `pack_admin_info`: admin-only pack metadata.
- `loaded_pack`: parsed question pack kept server-side.

The first target is `game_state`, because it mixes public client state, admin workflow state, round context, media state, logs, timers, and spin state.

## Initial Scope

- Inventory all fields in `game_state` and their readers/writers.
- Decide how to represent the schema: `TypedDict`, dataclass, Pydantic model, or a smaller transitional structure.
- Separate public state from admin-only state at the API boundary.
- Keep existing Socket.IO event names and frontend behavior unless a small compatibility change is clearly justified.
- Add focused tests or type-oriented checks if the chosen representation makes that practical.

## Out Of Scope

- Full transition-service refactor.
- Persisting state across backend restarts.
- Reworking player/session storage.
- Implementing new product features from the roadmap.
- Major frontend redesign.

## Decisions

- No schema approach is chosen yet. Compare options before implementation.
- Prefer a low-risk migration that preserves the current runtime behavior.
- Treat roadmap sub-bullets as hypotheses, not final requirements.

## Notes

- Current tests cover question parsing and sector angle mapping, not game-state transitions.
- `game_state` currently includes fields that are safe for all clients, but the boundary is implicit.

## State Inventory

Current `game_state` fields:

| Field | Shape | Notes |
| --- | --- | --- |
| `phase` | string enum | Main game phase. Used by backend guards and frontend conditional rendering. |
| `score` | `{znatoki: int, tv: int}` | Public score. Mutated by `admin_score` and `admin_reset`. |
| `current_sector` | int | Last/current table sector used to restore arrow position. |
| `target_angle` | float/null | Spin target angle broadcast to animate clients. |
| `playing_sector` | int/null | Sector selected after jump rules; mostly spin context. |
| `spin_duration` | float/int | Seconds for frontend table animation and volchok sound fade. |
| `used_questions` | list[int] | Played sectors; drives disabled buttons and envelopes. |
| `is_spinning` | bool | Spin lock and frontend table/sound behavior. |
| `logs` | list[str] | Public/admin log currently broadcast in full state. |
| `question_types` | list[str]/null | Loaded from pack; used by frontend table to show normal/blitz/superblitz icons. |
| `discussion_deadline_ms` | int/null | Unix ms deadline for admin-side timer. |
| `round` | dict/null | Current round context: kind, sector, optional part_index and advance_next_part. |
| `shared_media` | dict/null | Public media currently shown to all clients instead of table. |

Related state outside `game_state`:

| Name | Shape | Notes |
| --- | --- | --- |
| `global_settings` | dict | Broadcast through `settings_update`; currently volume only. |
| `players_list` | list[dict] | Contains sid/name/role/token/online/pending; admin-only projection is sent through `players_update`. |
| `admin_tokens` | dict | In-memory admin auth tokens. |
| `media_tokens` | dict | Temporary media ids, file paths, type, round key and expiry. |
| `pack_admin_info` | dict | Admin-only pack path/titles/types. |
| `loaded_pack` | `QuestionPack/null` | Server-side parsed pack; not broadcast directly. |

Current client-facing channels:

- `state_update`: sends `game_state` as-is to every client.
- `settings_update`: sends `global_settings`.
- `players_update`: admin-only player projection.
- `pack_info`: admin-only pack metadata.
- `admin_question`: admin-only current question content.

Initial observation: `game_state` is not purely public game state. It also contains admin workflow helpers (`round.advance_next_part`), loaded pack metadata (`question_types`), animation context (`target_angle`, `spin_duration`), and media state. The first schema pass should make these categories explicit even if the wire payload remains compatible.
