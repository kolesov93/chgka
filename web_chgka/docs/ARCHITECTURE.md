# CHGKA Web Architecture

## Product boundary

`web_chgka` is the target application. The older Pyglet/VLC application in the parent Git repository is legacy and is not part of the maintained runtime.

The intended end state is a public-internet web application. The repository currently provides a development topology with separate localhost frontend and backend servers; production routing and deployment have not been designed yet.

## Runtime map

```text
React clients
    |
    | Socket.IO events and state_update payloads
    v
FastAPI + python-socketio (backend/main.py)
    |-- AppState in memory
    |-- synchronous game transitions (backend/transitions.py)
    |-- players and session tokens in memory
    |-- question pack loaded from the filesystem
    `-- temporary media tokens -> GET /media/{media_id}
```

### Frontend

- `frontend/src/App.jsx` owns the socket connection, session restore, shared state, discussion timer, media preview, notifications, and most admin UI.
- `frontend/src/components/` contains the table, login, waiting room, score, and log views.
- `frontend/src/hooks/useGameSound.js` manages the wheel loop, fade-out, and effect sounds.
- Development connects Socket.IO and media requests directly to `http://localhost:8000`. A production build uses the current origin (`/`).

The frontend receives the shared game snapshot through `state_update`. Admin-only data uses separate events such as `players_update`, `pack_info`, and `admin_question`.

### Backend

- `backend/main.py` creates the FastAPI/Socket.IO application and currently contains authentication, player lifecycle, phase handlers, scoring, spin orchestration, media access, logging, and emits.
- `backend/state.py` defines the typed internal `AppState` and serializes it to the flat public payload expected by the frontend.
- `backend/transitions.py` owns synchronous phase, spin, scoring, blitz, round-end, and reset rules. It mutates `AppState` before network awaits and returns transport effects such as logs, sounds, media-token cleanup, and admin-question refresh.
- `backend/questions.py` parses and validates filesystem question packs and converts Markdown sections to HTML.

The backend is authoritative. Clients request actions; they do not calculate scores or advance phases locally.

## Game state

Internal state is split by responsibility:

- `game`: phase, score, used questions, current round;
- `wheel`: sector and spin animation state;
- `timer`: discussion deadline;
- `presentation`: shared media;
- `pack`: question types needed by the UI;
- `logs`: recent game log entries.

`public_game_state()` flattens these sections into the existing `state_update` contract. This compatibility layer allows the backend internals to evolve without combining a state refactor with a frontend protocol migration.

`wheel.spin_id` is internal and is not sent to clients. Reset increments it, so a sleeping async spin handler cannot apply an obsolete completion to the reset game.

Current phases are:

```text
LOGIN -> PRE_ROUND -> QUESTION_READING -> DISCUSSION
      -> TEAM_ANSWER -> POST_ROUND -> PRE_ROUND
```

Blitz and superblitz use the same phases plus `round.part_index` and the temporary `advance_next_part` flag. `GAME_OVER` and `INTRO` are roadmap items and are not current phases.

## Question packs

A pack is a directory with exactly 13 directories named `01` through `13`. Each sector contains `question.md`; media live under a local `media/` directory.

Supported question kinds are `normal`, `blitz`, and `superblitz`. Blitz variants contain three nested parts, also named `01` through `03`.

The parser validates required sections, section order, media existence and usage, supported extensions, and blitz structure. It intentionally supports only simple `key: value` frontmatter rather than the full YAML language.

Markdown is converted to HTML on the backend. Media references become placeholders for the admin UI. Raw HTML is currently possible and therefore assumes a trusted pack.

## Media flow

The parser recognizes images, audio, and video. The share flow currently supports images only:

1. The admin clicks a media placeholder.
2. The backend resolves the relative path against media allowed for the current round.
3. The backend creates a temporary `media_id` bound to the round context.
4. The admin shares that ID through `admin_share_media`.
5. All clients request `/media/{media_id}` from the backend origin and render it from shared presentation state.

Audio/video playback state, server timestamps, pause/resume, and synchronization remain unimplemented.

## Persistence and concurrency

All mutable runtime data is process-local. A backend restart loses the game, players, sessions, logs, and media tokens.

Socket.IO handlers are asynchronous and can overlap. UI button disabling is not a concurrency boundary. Core game handlers therefore call synchronous transitions before their first network await. Repeated scoring is rejected by the changed phase, and spin completion is accepted only for the current `spin_id`.

## Deployment status

`docker-compose.yml` is development-only: it bind-mounts source code and both Dockerfiles run development servers. There is no reverse proxy, TLS configuration, persistent store, health check, production image, or CI deployment workflow yet.
