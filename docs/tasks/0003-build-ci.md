# 0003: Build and CI

Branch: `task/build-ci`
Status: Completed

## Goal

Make the current web application reproducible to install and verify in a clean environment before further frontend and product work.

## Context

- `frontend/package-lock.json` exists locally but is not tracked.
- Local frontend setup and the frontend Dockerfile use `npm install`, so dependency resolution can drift.
- Backend runtime dependencies are pinned, but test dependencies are not declared.
- The repository has no CI workflow.
- Docker contexts include local build/cache artifacts, Compose still has an obsolete top-level `version`, and both Dockerfiles run development servers.
- `ROADMAP.md` lists frontend decomposition before Build/CI, while the latest handoff recommends Build/CI first. The user explicitly selected Build/CI as the next task.

## Scope and decisions

- Commit `frontend/package-lock.json` and use `npm ci` in documented clean setup, Docker, and CI.
- Declare backend test dependencies separately from runtime dependencies.
- Add path-filtered GitHub Actions checks for backend tests, frontend build, and Compose configuration.
- Use Node.js 24 LTS and Python 3.14 consistently between Docker and CI. Node 18 and Python 3.9 in the old Dockerfiles are end-of-life.
- Add backend/frontend `.dockerignore` files and remove the obsolete Compose `version` field.
- Keep Docker Compose explicitly development-only, with bind mounts and reload servers.

## Out of scope

- Production images, reverse proxy, TLS, domain/routing, deployment, and secret injection.
- Adding lint, typecheck, frontend tests, or browser automation.
- Locking the full transitive Python dependency graph.
- Changing application behavior or dependency versions beyond what build compatibility requires.

## Verification plan

- Install frontend dependencies from only `package.json` and `package-lock.json` with `npm ci`, then run `npm run build`.
- Install backend runtime and test requirements in an isolated environment, then run `python -m pytest -q`.
- Validate `docker compose config --quiet` without warnings.
- Build both Docker images if the local Docker daemon is available.

## Implementation

- Added a root, path-filtered GitHub Actions workflow with backend, frontend, and Compose jobs for pushes to `web`, `task/**`, and pull requests.
- Committed the frontend lockfile and switched Docker, CI, and clean local setup to `npm ci`.
- Refreshed packages within the existing `package.json` semver ranges. This moved Socket.IO transitive dependencies to non-vulnerable versions without a major upgrade.
- Added `requirements-dev.txt` with the test dependency while keeping the runtime image on `requirements.txt`.
- Updated development images to Node.js 24 and Python 3.14, added per-context `.dockerignore` files, and removed the obsolete Compose `version` field.
- Documented that Docker Compose remains development-only.

## Verification

- A clean `npm ci` followed by `npm run build` passes.
- `npm audit --omit=dev` reports zero production dependency vulnerabilities.
- A clean temporary Python environment installs `requirements-dev.txt`; all 71 backend tests pass.
- Both Docker images build. The frontend build passes inside the Node.js 24 image; all 71 backend tests pass inside the Python 3.14 image with repository fixtures mounted read-only.
- `docker compose config --quiet` passes without the previous obsolete-version warning.
- The first remote GitHub Actions run passes all three jobs: backend, frontend, and Compose.

## Follow-up discovered

The full npm audit still reports two dev-toolchain findings rooted in Vite 4 / `esbuild`; npm requires a breaking Vite upgrade to resolve them. Python 3.14 also exposes warnings in the currently pinned FastAPI/Starlette/AnyIO stack. Both are recorded as a separate dependency/toolchain roadmap item rather than mixed into this reproducibility task.
