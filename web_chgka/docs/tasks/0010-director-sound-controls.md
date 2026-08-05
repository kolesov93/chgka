# 0010: Director sound controls

Branch: `task/director-sound-controls`
Status: In progress

## Goal

Make the routine `Fade 3s` and `Silence` actions immediately available to the host beside master volume instead of hiding them in the collapsed Live Ops recovery panel.

## Decisions

- Add one always-visible director sound block to the normal admin controls with master volume, `Fade 3s`, and `Silence`.
- Keep both actions immediate and reuse the existing `admin_fade_sounds` and `admin_stop_sounds` events.
- Preserve the local immediate stop used by `Silence` in addition to the server command.
- Leave `Hide media` in Live Ops because this task only reclassifies sound controls.
- Do not change backend behavior, state, authorization, or the sound-control wire contract.

## Verification

- Frontend assertions and production build.
- Browser check that the two actions are visible without opening Live Ops, keep their existing behavior, and `Hide media` remains in Live Ops.

## Local verification status

Passed locally:

- `npm test`;
- `npm run build`.

Pending: GitHub Actions and the focused browser check.
