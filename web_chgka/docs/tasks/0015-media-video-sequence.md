# 0015: Video media and sequence control

Branch: `task/media-video-sequence`
Status: In progress

## Goal

Complete the managed question-media flow by making video usable by the host and players and by reducing the number of manual steps needed when one section contains several ordered media items.

## Current context

- The pack parser and validator already recognize video files and assign every media occurrence an opaque `media_ref`, section, and per-section order.
- The current-round catalog already isolates a normal round or the active blitz/superblitz part. Tokens are bound to that context, but `admin_resolve_media` currently rejects video.
- Backend playback transitions already accept both audio and video. The public state and frontend renderer implement synchronized audio only.
- Images are privately resolved into inline host thumbnails. Audio is resolved on click. The video placeholder currently displays an unsupported-feature notification.
- A shared audio item has server-authoritative `stopped`, `playing`, and `paused` state. Natural browser completion is not reported, so the server can remain in `playing` after the file has ended.
- Private media tokens expire after ten minutes even while the item remains shared.

## Decisions already implied by the existing flow

- Sharing remains an explicit host action; resolving or privately previewing media must not show it to players.
- Players get no native media controls. Play, pause, stop, sequence changes, and hide remain host actions.
- Video reuses the existing media identity, context validation, shared presentation slot, and playback timeline instead of introducing a parallel protocol.
- Video is resolved on click and privately previewed with browser controls; it is not automatically downloaded just because the question opened.
- A next-media action must never cross into another section, a future blitz part, or another round, and it must not wrap from the last item to the first.
- Natural completion must not automatically reveal the next media item. Advancing the presentation remains a deliberate host action.

## Accepted product decisions

- “Next media” is an explicit presentation step: it immediately replaces the currently shared item with the next item in the same section. A new audio/video item starts stopped and still requires Play.
- The synchronized host browser reports natural audio/video completion through an authenticated event. The backend validates media identity and playback generation so a stale event cannot affect a replay or replacement.
- Natural completion uses the existing `stopped` state and resets the item to the beginning while keeping it visible. It does not add an `ended` state, hide the item, or advance the sequence.
- An actively shared token remains fetchable beyond the private ten-minute TTL only while it is the exact current shared item in the exact current round/part context. Hide, replacement, or a context change removes that exception.
- The accepted client-ended approach assumes the host tab is present during playback. If it disappears at the moment of completion, authoritative state can remain `playing` until the host returns or performs another media action; server duration timers remain out of scope.

## Implementation

- The synchronized frontend element now renders audio or video with the same positioning, autoplay-unlock, volume, natural-end, and reconnect behavior. Private video preview retains native host controls; shared video has no player controls.
- The backend derives sequence order from the current catalog and the current item's `scope`, source section, and order. Next requires the expected current media id, preventing concurrent duplicate actions from skipping an item; it never accepts a client path or arbitrary next reference.
- Every play/pause/stop/completion transition advances a playback generation. A delayed `ended` event cannot stop a replayed, paused, replaced, or hidden item.
- An actively shared token remains fetchable while its exact round/part context remains current. Hide and replacement revoke it immediately; normal context transitions already clear all media tokens. Private unresolved/unshared tokens retain their short expiry.
- The flat public `state_update` contract adds only playback generation and whether a same-section next item exists. Question/answer references, sections, names, and files remain admin-only.

## Out of scope

- Automatic playlists, looping, scrubbing shared playback, subtitles, transcoding, thumbnails, upload UI, adaptive streaming, or CDN/storage work.
- Inline audio/video players inside the question text; placeholders only select the existing private preview block.
- Cross-section sequencing, automatic answer reveals, persistence, or production deployment infrastructure.

## Verification plan

- Backend unit and handler tests for video resolve/share/play/pause/stop, section-bounded next-media behavior, stale completion rejection, token/context invalidation, and unchanged image/audio behavior.
- Frontend tests for generic position synchronization, ended emission guards, video rendering without player controls, private preview selection, and next-action availability.
- Full backend suite, frontend test/build, and Compose validation.
- Focused two-browser smoke with sample sector 06 video in the question, sector 08 video in the answer, sector 02 ordered question images, reconnect, and autoplay permission fallback.

## Local verification status

- `python3 -W error -m pytest -q`: 177 tests passed.
- `npm test`: all 7 test files passed.
- `npm run build`: passed.
- `docker compose config --quiet`: not executable in the current sandbox because the installed snap `docker` fails in `snap-confine` before Compose starts; no Compose validation error was produced.
