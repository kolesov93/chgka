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
- `frontend/src/components/` contains the shared intro screen with host-only speech/navigation, the admin question/media panel with private inline image thumbnails and black-box controls, synchronized black-box audio/static player screen, the shared final screen, normal admin controls with the always-visible director sound block, the separate danger-styled Live Ops recovery panel, shared-media renderer, header/notifications, table, login, waiting room, score, and log views.
- `frontend/src/intro.js` owns the static `00`/`13` boundary, fallback author asset, host next-step labels, and reconnect-aware music countdown math. Author photos for slides 1–12 come from the backend origin.
- `frontend/src/inlineMedia.js` safely turns resolved image placeholders into host-only thumbnail markup. Non-image and unknown placeholders remain unchanged.
- `frontend/src/blackbox.js` owns the static image/music sources and converts the public black-box timeline into the existing synchronized playback shape.
- Development connects Socket.IO and media requests directly to `http://localhost:8000`. A production build uses the current origin (`/`).

The frontend receives the shared game snapshot through `state_update`. Admin-only data uses separate events such as `players_update`, `pack_info`, and `admin_question`.

UI components may emit existing user actions through the shared socket, but they do not create connections or own session restoration. The decomposition preserves the existing Socket.IO event names, payloads, and flat `state_update` contract.

### Backend

- `backend/main.py` creates the FastAPI/Socket.IO application and currently contains authentication, player lifecycle, phase handlers, scoring, spin orchestration, media access, logging, and emits.
- `backend/config.py` validates the explicit development/production environment, admin password, exact browser-origin allowlist, and admin-token TTL before the application starts.
- `backend/auth.py` owns the single active opaque admin token and its fixed in-memory expiry/revocation lifecycle; every privileged Socket.IO action validates the role plus current token.
- `backend/safe_html.py` owns the `nh3` allowlist used after Markdown conversion for question sections and intro speech.
- `backend/state.py` defines the typed internal `AppState` and serializes it to the flat public payload expected by the frontend.
- `backend/transitions.py` owns synchronous intro, black-box presentation, phase, spin, scoring, blitz, round-end, and reset rules. It mutates `AppState` before network awaits and returns transport effects such as logs, sounds, media-token cleanup, and admin-question refresh.
- `backend/live_ops.py` owns exceptional admin recovery rules: exact score/sector edits, direct round opening, normalized phase forcing, stuck-spin cancellation, and timer repair. It uses the same transport effects without weakening normal transition guards.
- `backend/sound_control.py` owns the pure generation-based `normal`/`fading`/`stopped` lifecycle and synchronized fade progress math.
- `backend/questions.py` parses and validates filesystem question packs, required author/optional city/direct author-photo/strict black-box metadata, section-aware opaque question-media references, and Markdown sections.
- `backend/media.py` builds the media catalog for the exact current round/blitz part, creates and validates media-token context, and owns synchronous playback-state transitions.
- `backend/validate_pack.py` exposes that same parser as the pre-start `python -m validate_pack` CLI; it does not define separate validation rules.

The backend is authoritative. Clients request actions; they do not calculate scores or advance phases locally.

## Game state

Internal state is split by responsibility:

- `game`: phase, score, used questions, current round;
- `wheel`: sector and spin animation state;
- `timer`: discussion deadline;
- `presentation`: intro progress/timeline, shared media, and the synchronized black-box timeline/generation;
- `pack`: question types plus public intro-author metadata needed by the UI;
- `logs`: recent game log entries.

`public_game_state()` flattens these sections into the existing `state_update` contract. This compatibility layer allows the backend internals to evolve without combining a state refactor with a frontend protocol migration.

`wheel.spin_id` is internal and is not sent to clients. Reset increments it, so a sleeping async spin handler cannot apply an obsolete completion to the reset game.

Current phases are:

```text
LOGIN -> INTRO -> PRE_ROUND -> QUESTION_READING -> DISCUSSION
                                             -> TEAM_ANSWER -> POST_ROUND
                                                               |-> PRE_ROUND
                                                               `-> GAME_OVER
```

`start_game` enters `INTRO` on static slide `00` without autoplay. A separate guarded host action records the start timestamp and broadcasts the one-shot `meeting.mp3`; until then the timeline is explicitly not started. Slides 1–12 use pack-backed author cards: one top-level card for a normal question, or three part cards in one row for blitz/superblitz. Every card has its own optional city and pack photo or static fallback. Slide 13 is the existing special-sector graphic. The action after `13` stops intro sound and enters `PRE_ROUND`. Music and slide actions are independent, and repeated/concurrent requests cannot start the track twice or skip a slide. Reconnecting clients recover the current slide/authors/countdown snapshot, but the one-shot audio is deliberately not replayed or seeked after reconnect.

Blitz and superblitz use the later game phases plus `round.part_index` and the temporary `advance_next_part` flag.

The sixth point still enters `POST_ROUND`, preserving the host's answer/commentary review. The following end-round action enters `GAME_OVER` instead of `PRE_ROUND`, clears round/media/timer/wheel context, stops older effects, and then broadcasts the one-shot `final` sound. `GAME_OVER` is stable in the public snapshot, so reconnecting clients recover the final score/winner screen without replaying the sound. Normal game actions remain guarded by their expected phases; reset starts a new `PRE_ROUND` game with the same pack and connected players.

## Live Ops recovery

The admin has a separate collapsed recovery panel; it is not part of the normal game flow. New actions use explicit Socket.IO events rather than accepting arbitrary state patches:

- `admin_set_score` and `admin_set_sector_used` repair exact progress values;
- `admin_open_round` derives question kind from the loaded pack and enters `QUESTION_READING` without a spin;
- `admin_force_phase` accepts only the five recoverable non-final game phases and normalizes round, timer, spin, media, and admin-question context;
- `admin_reset_to_intro` performs an explicit full progress reset, invalidates active runtime context, stops audio, and restores intro slide `00` with music waiting for the host command;
- `admin_cancel_spin` increments `spin_id`, so a sleeping spin handler cannot overwrite recovered state;
- `admin_set_timer` sets or stops the deadline only in `DISCUSSION`.

After admin authorization, every operation validates its complete input before mutation, mutates synchronously before any network emit await, logs the recovery, and then broadcasts authoritative state. Hide media reuses its existing event and remains in this panel. Recovery does not play normal phase/scoring sounds; reset-to-intro stops existing audio and leaves the explicit music start to the host. Recovery does not introduce arbitrary state editing, snapshots, or undo.

## Sound control

Master volume and the server-authoritative sound-control snapshot travel through `settings_update`, separately from the flat game-state compatibility payload. The snapshot contains a monotonically increasing generation, mode, optional fade start/duration, fade starting level, and current server time. It is sent before game state on connect so a reconnecting browser cannot briefly restart audible shared audio or a wheel loop that is fading/stopped.

The normal admin panel keeps master volume, `Fade 3s`, and `Silence` together in one always-visible director sound block. Fade and Silence are routine live-production actions and do not require opening the Live Ops recovery panel. They reuse the existing sound events and state contract.

`admin_fade_sounds` starts a three-second fade and captures its generation. Clients combine server progress with local time since receipt and apply one multiplier to managed shared audio, the black-box track, one-shot effects, and the wheel loop. Gain follows a uniform 60 dB reduction (exponential amplitude) with 25 ms browser updates, leaving the sound effectively silent before final Stop. Repeated Fade starts from the current multiplier. At completion the backend stops shared-media playback, ends an active black-box presentation, and emits `stop_sound` for effects and the wheel.

Every later server sound command advances the generation synchronously before its first emit. Play/effect/spin restores normal output; Silence and transition recovery stops select stopped output; explicit shared-media Play/Pause/Stop cancels pending global completion. A sleeping fade checks its captured generation before stopping anything, so it cannot affect newer audio. Private admin preview is deliberately outside this shared control plane.

## Question packs

A pack contains 13 required sector directories named `01` through `13`. Each sector and every blitz part requires an author; city and a direct sibling author photo are optional. Question media remain under local `media/`. An optional root `intro.md` contains Markdown speech shown only to the admin through `pack_info`; media in that file are unsupported.

Supported question kinds are `normal`, `blitz`, and `superblitz`. Blitz variants contain three nested parts, also named `01` through `03`. Optional strict `blackbox: true|false` metadata can mark a normal question, a whole blitz/superblitz from its top-level file, or an individual nested part.

The parser validates required sectors and sections, section order, media existence and usage, supported extensions, local media-path containment, and blitz structure. Extra two-digit numeric sector directories are rejected; named root-level auxiliary directories are ignored. It intentionally supports only simple `key: value` frontmatter rather than the full YAML language. The authoring contract and validator usage are documented in `docs/QUESTION_PACKS.md`.

Markdown is converted to HTML on the backend and then sanitized through a strict allowlist. Safe formatting and links remain available; executable/embedded content, event/style attributes, unsafe URL schemes, and raw image elements are removed. Generated `span.media-placeholder[data-media-ref]` elements remain available to the managed admin media flow.

## Black-box presentation

The pack is authoritative for whether the current normal question or blitz part offers black-box controls. `pack_info` contains separate top-level/part flags, while `admin_question.blackbox` contains the effective flag for the exact current reading context. Players never choose or infer this state.

`admin_start_blackbox` is allowed only for an enabled question in `QUESTION_READING`. The synchronous transition removes shared media, advances a monotonic presentation generation, stores the start timestamp, restores normal shared sound output, and broadcasts the public reconnect-aware timeline. Every client plays the static `/sounds/yashik.mp3`; players see `/images/blackbox.png`, while the host retains the question card and dedicated Stop. Discussion and new shared-media presentation are guarded until the black box ends.

The authenticated host reports natural completion with the current generation. Dedicated Stop clears only the black-box presentation; global Silence clears it immediately, and Fade keeps the image/music active through the three-second curve and clears it only at completion. Stale completion/stop commands cannot affect a later start. Every ending returns players to the normal game table and never restores the shared media replaced at start. Live Ops/reset operations also clear and invalidate this state.

## Media flow

The parser recognizes images, audio, and video. Each Markdown occurrence receives an opaque `media_ref`, source section, and order. A file referenced in both question and answer therefore has two different references. Question HTML contains only the opaque reference; paths and inferred types are not trusted from the browser.

Author photos are deliberately separate from managed question media. The flat intro snapshot exposes only the current sector's ordered author cards with sector, slot, name, city, and `has_photo`; filesystem paths remain in `QuestionPack`. `GET /intro/author-photo/{sector}/{slot}` serves only a card of sectors 1–12 while that exact sector slide is current and disables caching. Normal questions have slot 1; blitz variants map slots 1–3 to their nested parts. Missing/failed photos independently use the static generated fallback. The special sector 13 never requests an author photo.

The managed image/audio/video flow is:

1. `admin_question` sends the admin the current round/part HTML and admin-only media descriptors.
2. The admin UI automatically resolves current image refs through `admin_resolve_media` and renders their temporary URLs as compact inline thumbnails. Audio and video refs remain click-to-resolve placeholders; video gets a private browser-controlled preview in the existing media block.
3. The backend looks each requested reference up in the current catalog and creates a temporary `media_id` token.
4. The token is bound to its expiry, spin generation, sector/kind/part, round/part scope, section, exact reference, type, name, and file. The same validation runs on share, playback commands, and `GET /media/{media_id}`.
5. Clicking an inline thumbnail only selects the same private token in the existing admin media block. `admin_share_media` remains the explicit action that puts an image or stopped audio/video item into shared presentation state. The public serializer removes the internal reference, section, and filename; clients receive only the type/token/playback/sequence fields and fetch the file from the backend origin.
6. Audio/video play/pause/stop actions mutate server-authoritative playback state. `state_update` includes the stored position, playback start timestamp, serialization time, and playback generation so current and reconnecting clients align their local media elements.
7. If the current source section has another ordered attachment, an explicit host-only next action asks the backend to derive it from the current shared token. The replacement cannot cross round/part scope or source section, does not wrap, and puts playable media into stopped state.
8. Natural completion is reported only by the synchronized admin element with the current media id and playback generation. The backend rejects stale completions, records stopped position zero, and keeps the media visible; it never automatically advances or hides it.

Players receive no native playback controls. Browser autoplay restrictions are handled by a local permission button, which does not change server playback state. Stop and natural completion reset audio/video to the beginning while keeping it visible; hide removes it. Shared audio/video participates in the global server-synchronized sound fade; private preview does not. A shared token remains fetchable beyond the normal ten-minute private TTL only while it is the exact active item in the exact current round/part context; hide, replacement, and context transitions revoke that exception. Inline image thumbnails and the larger media block reuse one private token and never change player presentation without the explicit share action. Duration extraction, server-side end timers, and automatic playlists remain out of scope.

## Persistence and concurrency

All mutable runtime data is process-local. A backend restart loses the game, players, sessions, logs, media tokens, volume, and sound-control generation.

Admin authentication is also process-local. The backend accepts one active opaque token with a fixed, non-sliding TTL (12 hours by default); a new password login, explicit logout, expiry, or backend restart revokes the old session. The browser stores it in `localStorage` for reconnect, but the backend validates the token again for every privileged event. Player reconnect tokens keep their previous untimed in-memory lifecycle and never grant admin rights.

Socket.IO handlers are asynchronous and can overlap. UI button disabling is not a concurrency boundary. Core game and recovery handlers therefore call synchronous transitions before their first network await. Repeated scoring is rejected by the changed phase, intro navigation validates the expected slide index, and spin completion is accepted only for the current `spin_id`; reset and recovery cancellation both advance that generation.

## Deployment status

`docker-compose.yml` is development-only: it bind-mounts source code and both Dockerfiles run development servers. There is no reverse proxy, TLS configuration, persistent store, health check, production image, or CI deployment workflow yet.

Backend startup nevertheless has an explicit security mode. Development Compose supplies its local password and exact `http://localhost:5173` origin. Production requires an externally injected password and exact HTTPS origins; the same allowlist protects FastAPI CORS and Socket.IO/WebSocket handshakes. The production frontend still assumes same-origin HTTP and WebSocket routing through a future TLS reverse proxy.
