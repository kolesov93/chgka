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
    |-- synchronous admin recovery operations (backend/live_ops.py)
    |-- players and session tokens in memory
    |-- question pack loaded from the filesystem
    `-- temporary media tokens -> GET /media/{media_id}
```

### Frontend

- `frontend/src/App.jsx` owns only top-level phase routing and the main page layout.
- `frontend/src/socket.js` owns the single Socket.IO client plus backend/media URL construction.
- `frontend/src/hooks/useGameSession.js` owns session restore, shared server state, players, pack/admin data, notifications, logout, and non-audio socket listeners.
- `frontend/src/hooks/useDiscussionTimer.js` owns the admin countdown and one-shot local ten-second notification; `useSocketSoundEvents.js` bridges sound events to `useGameSound.js`.
- `frontend/src/hooks/useSoundFade.js` derives one reconnect-aware emergency fade multiplier from the server sound-control snapshot. Shared media, effects, and the wheel consume that multiplier; the wheel also retains its intrinsic end-of-spin fade.
- `frontend/src/components/` contains the admin question/media panel, normal admin controls with the always-visible director sound block, the separate danger-styled Live Ops recovery panel, shared-media renderer, header/notifications, table, login, waiting room, score, and log views.
- Development connects Socket.IO and media requests directly to `http://localhost:8000`. A production build uses the current origin (`/`).

The frontend receives the shared game snapshot through `state_update`. Admin-only data uses separate events such as `players_update`, `pack_info`, and `admin_question`.

UI components may emit existing user actions through the shared socket, but they do not create connections or own session restoration. The decomposition preserves the existing Socket.IO event names, payloads, and flat `state_update` contract.

### Backend

- `backend/main.py` creates the FastAPI/Socket.IO application and currently contains authentication, player lifecycle, phase handlers, scoring, spin orchestration, media access, logging, and emits.
- `backend/state.py` defines the typed internal `AppState` and serializes it to the flat public payload expected by the frontend.
- `backend/transitions.py` owns synchronous phase, spin, scoring, blitz, round-end, and reset rules. It mutates `AppState` before network awaits and returns transport effects such as logs, sounds, media-token cleanup, and admin-question refresh.
- `backend/live_ops.py` owns exceptional admin recovery rules: exact score/sector edits, direct round opening, normalized phase forcing, stuck-spin cancellation, and timer repair. It uses the same transport effects without weakening normal transition guards.
- `backend/sound_control.py` owns the pure generation-based `normal`/`fading`/`stopped` lifecycle and synchronized fade progress math.
- `backend/questions.py` parses and validates filesystem question packs, assigns section-aware opaque media references, and converts Markdown sections to HTML.
- `backend/media.py` builds the media catalog for the exact current round/blitz part, creates and validates media-token context, and owns synchronous playback-state transitions.
- `backend/validate_pack.py` exposes that same parser as the pre-start `python -m validate_pack` CLI; it does not define separate validation rules.

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

## Live Ops recovery

The admin has a separate collapsed recovery panel; it is not part of the normal game flow. New actions use explicit Socket.IO events rather than accepting arbitrary state patches:

- `admin_set_score` and `admin_set_sector_used` repair exact progress values;
- `admin_open_round` derives question kind from the loaded pack and enters `QUESTION_READING` without a spin;
- `admin_force_phase` accepts only the five implemented game phases and normalizes round, timer, spin, media, and admin-question context;
- `admin_cancel_spin` increments `spin_id`, so a sleeping spin handler cannot overwrite recovered state;
- `admin_set_timer` sets or stops the deadline only in `DISCUSSION`.

After admin authorization, every operation validates its complete input before mutation, mutates synchronously before any network emit await, logs the recovery, and then broadcasts authoritative state. Hide media reuses its existing event and remains in this panel. Recovery does not play normal phase/scoring sounds and does not introduce arbitrary state editing, snapshots, or undo.

## Sound control

Master volume and the server-authoritative sound-control snapshot travel through `settings_update`, separately from the flat game-state compatibility payload. The snapshot contains a monotonically increasing generation, mode, optional fade start/duration, fade starting level, and current server time. It is sent before game state on connect so a reconnecting browser cannot briefly restart audible shared audio or a wheel loop that is fading/stopped.

The normal admin panel keeps master volume, `Fade 3s`, and `Silence` together in one always-visible director sound block. Fade and Silence are routine live-production actions and do not require opening the Live Ops recovery panel. They reuse the existing sound events and state contract.

`admin_fade_sounds` starts a three-second fade and captures its generation. Clients combine server progress with local time since receipt and apply one multiplier to managed shared audio, one-shot effects, and the wheel loop. Gain follows a uniform 60 dB reduction (exponential amplitude) with 25 ms browser updates, leaving the sound effectively silent before final Stop. Repeated Fade starts from the current multiplier. At completion the backend stops shared-media playback authoritatively and emits `stop_sound` for effects and the wheel.

Every later server sound command advances the generation synchronously before its first emit. Play/effect/spin restores normal output; Silence and transition recovery stops select stopped output; explicit shared-media Play/Pause/Stop cancels pending global completion. A sleeping fade checks its captured generation before stopping anything, so it cannot affect newer audio. Private admin preview is deliberately outside this shared control plane.

## Question packs

A pack contains 13 required sector directories named `01` through `13`. Each sector contains `question.md`; media live under a local `media/` directory.

Supported question kinds are `normal`, `blitz`, and `superblitz`. Blitz variants contain three nested parts, also named `01` through `03`.

The parser validates required sectors and sections, section order, media existence and usage, supported extensions, local media-path containment, and blitz structure. Extra two-digit numeric sector directories are rejected; named root-level auxiliary directories are ignored. It intentionally supports only simple `key: value` frontmatter rather than the full YAML language. The authoring contract and validator usage are documented in `docs/QUESTION_PACKS.md`.

Markdown is converted to HTML on the backend. Media references become placeholders for the admin UI. Raw HTML is currently possible and therefore assumes a trusted pack.

## Media flow

The parser recognizes images, audio, and video. Each Markdown occurrence receives an opaque `media_ref`, source section, and order. A file referenced in both question and answer therefore has two different references. Question HTML contains only the opaque reference; paths and inferred types are not trusted from the browser.

The managed image/audio flow is:

1. `admin_question` sends the admin the current round/part HTML and admin-only media descriptors.
2. The admin clicks a placeholder and resolves its `media_ref` through `admin_resolve_media`.
3. The backend looks the reference up in the current catalog and creates a temporary `media_id` token.
4. The token is bound to its expiry, spin generation, sector/kind/part, round/part scope, section, exact reference, type, name, and file. The same validation runs on share, playback commands, and `GET /media/{media_id}`.
5. `admin_share_media` puts an image or stopped audio item into shared presentation state. The public serializer removes the internal reference, section, and filename; clients receive only the type/token/playback fields and fetch the file from the backend origin.
6. Audio play/pause/stop actions mutate server-authoritative playback state. `state_update` includes the stored position, playback start timestamp, and serialization time so current and reconnecting clients align their local audio elements.

Players receive no native playback controls. Browser autoplay restrictions are handled by a local permission button, which does not change server playback state. Stop resets audio to the beginning while keeping it visible; hide removes it. Shared audio participates in the global server-synchronized sound fade; private preview does not. Video, queue/next, duration extraction, and automatic server-side end detection remain roadmap work. Image preview stays in the separate media block; inline image previews are a separate task.

## Persistence and concurrency

All mutable runtime data is process-local. A backend restart loses the game, players, sessions, logs, media tokens, volume, and sound-control generation.

Socket.IO handlers are asynchronous and can overlap. UI button disabling is not a concurrency boundary. Core game and recovery handlers therefore call synchronous transitions before their first network await. Repeated scoring is rejected by the changed phase, and spin completion is accepted only for the current `spin_id`; reset and recovery cancellation both advance that generation.

## Deployment status

`docker-compose.yml` is development-only: it bind-mounts source code and both Dockerfiles run development servers. There is no reverse proxy, TLS configuration, persistent store, health check, production image, or CI deployment workflow yet.
