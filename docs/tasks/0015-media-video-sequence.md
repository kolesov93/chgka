# 0015: Video media and sequence control

Branch: `task/media-video-sequence`
Status: Completed

## Goal

Complete the managed question-media flow with synchronized video and an explicit host action for ordered media sequences.

## Decisions

- Video reuses the existing opaque `media_ref`, context-bound token, shared presentation slot, and server-authoritative playback timeline.
- Resolving and private preview never affect players. Shared video has host-only Play/Pause/Stop and no native player controls.
- “Next media” immediately presents the next ordered item, but cannot cross source section, round/part scope, or wrap. Playable replacements start stopped; completion never advances automatically.
- Natural completion comes from the authenticated host browser. Media id plus playback generation reject stale completion after pause, replay, replacement, or Hide.
- Completion keeps the item visible but moves it to stopped position zero.
- An active shared token may outlive its private ten-minute TTL only while its exact round/part context remains current. Hide, replacement, and context transitions revoke it.
- If the host tab is absent exactly when playback ends, authoritative state can remain `playing` until the host returns or performs another media action; server duration timers remain out of scope.

## Implementation

- Generalized synchronized frontend playback for audio and video, including autoplay unlock, volume/fade, reconnect, natural-end reporting, and host-control restoration.
- Enabled video resolve/share and added backend-derived, generation-safe next-media and completion handlers.
- Added public playback generation and `has_next` fields while keeping references, sections, names, and paths admin-only.
- Preserved image/audio behavior and token isolation for normal rounds and the active blitz/superblitz part.

## Out of scope

- Automatic playlists, loops, shared scrubbing, duration extraction, server-side end timers, subtitles, transcoding, thumbnails, uploads, adaptive streaming, CDN/storage, and inline audio/video players inside question text.

## Verification and acceptance

- `python3 -W error -m pytest -q`: 177 tests passed.
- `npm test`: 31 assertions passed across 7 test files.
- `npm run build`: passed.
- Focused two-browser smoke passed for sector 06 question video, sector 08 answer video, sector 02 same-section Next, natural completion/reset, player control isolation, Hide, and admin/player reconnect.
- Local `docker compose config --quiet` could not start because the installed snap `docker` fails in `snap-confine`; remote Compose CI remains required after publication.
