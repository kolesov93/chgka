# 0004: Frontend Decomposition

Branch: `task/frontend-decomposition`
Status: Completed

## Goal

Split the 899-line `frontend/src/App.jsx` into clear session, timing, admin UI, and shared-media boundaries without changing application behavior or the Socket.IO wire contract.

## Context

`App.jsx` currently owns all of the following:

- backend URL and Socket.IO singleton configuration;
- session restoration, login lifecycle, players, pack/admin data, and notification events;
- discussion countdown and the local ten-second warning;
- admin question rendering and media preview/share;
- all admin game controls and player moderation;
- shared media rendering and top-level phase routing.

This makes media work, mobile UI, and future frontend tests risky because unrelated responsibilities share one component closure.

## Scope and decisions

- Move backend origin, media URL construction, and the Socket.IO singleton to one transport module.
- Move session/event state to a `useGameSession` hook while keeping sound events separate to avoid coupling session state to audio lifecycle.
- Move discussion countdown and ten-second notification bookkeeping to a dedicated hook.
- Extract admin question/media preview, admin controls, shared media, header, and notification components.
- Keep top-level phase routing and page layout in `App.jsx`.
- Keep all existing event names, payloads, storage keys, confirmation prompts, and visible behavior.
- Keep media preview local to the question panel and reset it by mounting the panel with a round/part key.

## Out of scope

- New UI, inline media thumbnails, mobile layout changes, or additional media types.
- Socket.IO protocol or backend changes.
- Dependency/toolchain upgrades.
- Adding a frontend test framework, lint, or typecheck.

## Verification plan

- Run `npm ci` and `npm run build`.
- Run the existing backend tests and Compose validation to guard repository integration.
- Push the branch and require all three existing CI jobs to pass.
- Run a focused two-browser regression smoke for admin/player login, session restore, normal/blitz controls, discussion timing/sounds, media preview/share/hide, player moderation, logout, and reset during spin.

## Implementation

- Moved backend origin, media URL construction, and the Socket.IO singleton to `frontend/src/socket.js`.
- Added `useGameSession` for session restore, shared state, players, pack/admin data, notifications, and logout.
- Kept audio listener wiring separate in `useSocketSoundEvents` and moved countdown state to `useDiscussionTimer`.
- Extracted `AdminQuestionPanel`, `AdminControls`, `SharedMediaRenderer`, `UserHeader`, and `NotificationsPanel`.
- Made media preview local to `AdminQuestionPanel`; the top-level round/part key resets it at the same lifecycle boundary as before.
- Reduced `App.jsx` from 899 to 156 lines while leaving top-level phase routing and layout there.

## Verification

- Clean `npm ci` and `npm run build` pass; Vite transforms 75 modules successfully.
- All 71 backend tests pass.
- `docker compose config --quiet` passes.
- Static review confirms the existing Socket.IO event names and payload shapes remain present after extraction.
- All three remote GitHub Actions jobs pass.
- The focused two-browser regression smoke passes.

## Follow-up work discovered

- Audio in sample question 03 remains unsupported by the current image-only frontend flow; the required regression case is recorded in roadmap item 8.
- A server-synchronized three-second fade action next to `Silence` is recorded in roadmap item 7.
