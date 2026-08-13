# 0005: Dependency and Toolchain Refresh

Branch: `task/dependency-toolchain-refresh`
Status: Completed

## Goal

Remove the known Vite/esbuild audit findings and refresh the Python web stack for the repository's Node.js 24 and Python 3.14 runtimes without changing product behavior or public wire contracts.

## Scope and decisions

- Upgrade Vite and `@vitejs/plugin-react` to a compatible stable pair and commit the regenerated npm lockfile.
- Upgrade the directly pinned FastAPI, Uvicorn, and Python Socket.IO packages to stable Python 3.14-compatible releases.
- Let FastAPI resolve compatible Starlette and AnyIO versions instead of adding new direct pins.
- Keep React 18, Tailwind CSS 3, Node.js 24, Python 3.14, the current Vite development server behavior, and the FastAPI/Socket.IO ASGI composition.
- Preserve all Socket.IO event names and payloads, game-state serialization, storage keys, media APIs, and question-pack behavior.

## Out of scope

- React 19 or Tailwind CSS 4 migrations.
- New frontend test, lint, or typecheck frameworks.
- Product UI, game rules, security policy, deployment, or production networking changes.

## Verification plan

- Run a clean frontend install, production build, and full npm audit.
- Run a clean backend install, `pip check`, and all backend tests with warnings treated as errors.
- Build both Docker images and repeat frontend/backend checks in the pinned Node.js 24 and Python 3.14 images.
- Validate the Compose configuration.
- Require all three GitHub Actions jobs and the focused two-browser Socket.IO regression smoke to pass before merging.

## Implementation

- Upgraded Vite from 4.5.14 to 8.2.0 and `@vitejs/plugin-react` from 4.7.0 to 6.0.5; regenerated the npm lockfile.
- Upgraded FastAPI from 0.104.1 to 0.141.1, Uvicorn from 0.24.0 to 0.52.1, and Python Socket.IO from 5.10.0 to 5.16.3.
- Kept React at 18.3.1 and Tailwind CSS at 3.4.19.
- Added `pip check`, Python warnings-as-errors, and full `npm audit` enforcement to the existing CI jobs.

## Verification

- Clean `npm ci`, full `npm audit`, and the Vite 8 production build pass; npm reports zero vulnerabilities.
- A clean Python dependency install and `pip check` pass; all 71 tests pass with warnings treated as errors.
- Both development Docker images build successfully.
- The frontend production build passes inside the Node.js 24 image.
- `pip check`, all 71 warnings-as-errors tests, and sample-pack startup pass inside the Python 3.14 image.
- A real websocket-only Socket.IO handshake succeeds between isolated frontend and backend containers.
- `docker compose config --quiet` passes.
- All three remote GitHub Actions jobs pass.
- The focused two-browser Socket.IO smoke passes.
