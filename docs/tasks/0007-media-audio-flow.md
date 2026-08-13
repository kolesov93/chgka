# 0007: Managed Media Flow — Audio

Branch: `task/media-audio-flow`
Status: Completed

## Goal

Introduce the final section-aware media identity and token foundation, then use it to make sample question 03 audio previewable and server-synchronized for the admin and players.

## Scope and decisions

- Give every parsed media reference an opaque `media_ref` plus its source section and order.
- Send admin-only media descriptors with question content; clients resolve media by `media_ref`, never by a trusted client-supplied path or type.
- Bind each media token to the spin generation, sector/kind/part, source scope, section, exact reference, file, and expiry; validate that context on resolve, share, playback commands, and HTTP GET.
- Extend shared presentation state with `stopped`/`playing`/`paused`, position, and server timestamps so reconnecting clients can resume the current audio position.
- Keep image sharing behavior, migrate it to `media_ref`, and keep the existing separate preview block.
- Add admin show/play/pause/stop/hide controls; players render audio without browser controls.
- Treat stop as reset-to-start while keeping the selected media visible; hide removes it and returns players to the table.

## Out of scope

- Inline image previews inside question HTML; this remains a separate roadmap item.
- Video rendering, media queue/next, fade, waveform, duration extraction, or automatic server-side ended transitions.
- Product security, persistence, or production deployment changes outside media-token context validation.

## Implementation

- Parser media entries now carry section, per-section order, and an opaque reference; placeholders expose only that reference.
- The current-round catalog exposes only top-level blitz intro media plus the active part and never exposes a future part.
- Media tokens validate expiry and the complete spin/round/scope/section/reference/file identity on every protected operation.
- Shared audio has server-authoritative stopped/playing/paused state, position, start time, and serialization time for reconnect alignment.
- The admin can privately preview audio, show it to players, and play/pause/stop/hide it. Players see the shared audio state without native controls.
- Image resolution and sharing use the same reference/token contract while retaining the existing separate preview block.
- CI now runs the pure frontend playback synchronization tests before the production build.

## Verification and acceptance

Passed locally:

- `python3 -W error -m pytest -q`: 88 tests;
- clean `npm ci`, `npm audit`: 0 vulnerabilities;
- `npm test`: 4 tests;
- `npm run build`;
- `docker compose config --quiet` and both development image builds;
- Python 3.14 container: `pip check` and 88 tests;
- Node 24 container: 4 tests and production build.

Acceptance passed:

- all GitHub Actions jobs on `task/media-audio-flow` are green;
- the admin/player browser smoke passed, including sample question 03 audio and the existing question 02 image flow.
