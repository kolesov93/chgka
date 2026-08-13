# 0006: Pack Validator

Branch: `task/pack-validator`
Status: Completed

## Goal

Give pack authors a deterministic pre-start command that applies the same validation rules as backend startup, reports actionable failures without a traceback, and documents the supported question-pack format.

## Scope and decisions

- Add `python -m validate_pack /path/to/pack` as the canonical command from `backend/`.
- Reuse `parse_question_pack()` as the single validation source of truth.
- Print a stable human-readable summary for valid packs and parser errors to stderr for invalid packs.
- Return exit code 0 for a valid pack, 1 for an invalid path/content, and argparse's exit code 2 for invalid CLI usage.
- Reject extra two-digit numeric sector directories outside `01` through `13` while allowing named auxiliary root entries for future pack metadata or intro assets.
- Require local media references to stay inside their question/part directory and under its `media/` folder.

## Out of scope

- An HTTP validation endpoint, upload UI, JSON output, or automatic pack repair.
- Markdown HTML sanitization or support for new frontmatter fields.
- Changes to game state, Socket.IO contracts, or frontend behavior.

## Verification plan

- Cover valid summary output and all three exit-code classes.
- Cover invalid pack paths, sector-context parser errors, extra numeric sectors, absolute media paths, and relative path traversal.
- Run all backend tests and sample-pack startup.
- Run frontend build and Compose validation as repository integration checks.
- Require remote CI and a minimal admin/player sample-pack smoke before merge.

## Implementation

- Added `validate_pack.py` with stable valid-pack summary output and explicit exit codes.
- Kept `parse_question_pack()` as the shared validation path for CLI and backend startup.
- Rejected extra two-digit numeric sector directories while allowing named auxiliary root directories.
- Restricted local media to relative `media/` paths that remain inside the current question/part after resolving traversal and symlinks.
- Added a Russian pack-authoring guide and linked it from the README and architecture documentation.

## Verification

- The sample-pack CLI succeeds and reports 11 normal questions, one blitz, one superblitz, six parts, and nine media files by type.
- Nine new CLI, sector-directory, traversal, and symlink tests pass; the full backend suite now has 80 passing tests with warnings treated as errors.
- Clean `npm ci`, full `npm audit`, and the Vite production build pass with zero vulnerabilities.
- The backend Docker image builds; the CLI, `pip check`, all tests, and sample-pack startup pass in Python 3.14.
- `docker compose config --quiet` passes.
- All three remote GitHub Actions jobs pass.
- The minimal admin/player sample-pack smoke passes.
