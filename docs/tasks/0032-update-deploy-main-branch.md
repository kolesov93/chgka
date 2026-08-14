# Task 0032: use `main` in the deployment runbook

## Goal and result

Remove the stale instruction to deploy a `web` branch revision after the web
application was promoted to the repository root and `main` became the release
branch.

- The runbook now requires a committed `main` revision with green GitHub CI.
- The preparation commands switch to `main` before checking status, pulling, and
  creating the release archive.
- No deployment commands, runtime configuration, or application behavior changed.

## Verification

- The deployment runbook contains neither `` `web` revision`` nor
  `git switch web`.
- `git diff --check` passes.
- Manual smoke is not required for this documentation-only correction.
