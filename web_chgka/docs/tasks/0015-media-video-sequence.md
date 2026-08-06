# 0015: Video media and sequence control

Branch: `task/media-video-sequence`
Status: Planning

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

## Open product decisions

### Meaning of “next media”

- **A — private selection:** select/resolve the next item in the same section, then require the existing separate “show players” action.
- **B — explicit presentation step:** when the host presses “next media”, replace the currently shared item with the next item in the same section. Audio/video start stopped and still require Play. This is the recommended option because the click is itself an explicit director action and it materially shortens multi-image questions.
- **C — automatic sequence:** advance on media completion. This is not recommended because it can unexpectedly reveal content and does not fit images, which have no natural end.

### Natural audio/video completion

- **A — host browser reports completion:** the synchronized host element emits an authenticated event carrying the current media identity and playback generation; the backend ignores stale events and records an `ended` state. This is the recommended small-system option.
- **B — server schedules completion:** the browser first supplies duration metadata and the backend owns a generation-guarded timer. This survives a host-tab disconnect better, but adds asynchronous lifecycle machinery around browser-derived metadata.
- **C — keep completion local:** every browser stops naturally but the backend stays in `playing`. This is not recommended because labels and reconnect state become false.

If `ended` is added, the item remains visible at its final frame/position; Play restarts it from the beginning, Stop resets it, and Hide returns to the table.

## Proposed technical boundary

- Generalize the synchronized frontend element so audio and video use the same positioning, autoplay-unlock, volume, and reconnect behavior while rendering appropriate UI.
- Derive sequence order on the backend from the current catalog and the current item's `scope`, source section, and order; do not accept a client-supplied path or arbitrary next reference.
- Add a playback generation to shared playable media so a delayed `ended` event cannot stop a replayed or replaced item.
- Keep an actively shared token fetchable while its exact round/part context remains current; hiding or changing context must remove that exception. Private unresolved/unshared tokens retain their short expiry.
- Preserve the flat public `state_update` compatibility boundary and keep question/answer media descriptors admin-only.

## Out of scope

- Automatic playlists, looping, scrubbing shared playback, subtitles, transcoding, thumbnails, upload UI, adaptive streaming, or CDN/storage work.
- Inline audio/video players inside the question text; placeholders only select the existing private preview block.
- Cross-section sequencing, automatic answer reveals, persistence, or production deployment infrastructure.

## Verification plan

- Backend unit and handler tests for video resolve/share/play/pause/stop, section-bounded next-media behavior, stale completion rejection, token/context invalidation, and unchanged image/audio behavior.
- Frontend tests for generic position synchronization, ended emission guards, video rendering without player controls, private preview selection, and next-action availability.
- Full backend suite, frontend test/build, and Compose validation.
- Focused two-browser smoke with sample sector 06 video in the question, sector 08 video in the answer, sector 02 ordered question images, reconnect, and autoplay permission fallback.
