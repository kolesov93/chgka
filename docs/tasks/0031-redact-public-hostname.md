# Task 0031: redact public deployment hostname

## Goal

Remove the private production hostname from all files and commits reachable from
the public `main` branch while keeping deployment examples useful.

## Context and result

The repository exposed the real hostname in README, architecture, deployment
examples, Compose defaults, and task history. Its first occurrence was in the
configurable-base-path work; that commit and the 23 following pre-task commits
received new SHA values. The complete 247-commit branch was replayed one-to-one,
preserving topology and metadata. The legacy Pyglet tag predates the hostname and
was not changed.

## Decisions

- Replace only the exact private hostname with the reserved documentation domain
  `example.com`; paths and protocol examples remain intact.
- Rewrite the affected `main` lineage while preserving commit topology, authors,
  dates, messages, and the unchanged legacy tag.
- Update documentation references to rewritten commit SHA values.
- Replace GitHub `main` only with `--force-with-lease` against the previously
  observed public tip; never use an unguarded force push.
- Keep an offline rollback bundle until the rewritten remote and local repository
  are verified, then remove the bundle and old local backup refs.
- Do not access or modify the VPS. This task changes only the repository and its
  public Git history.

## Verification

- The current tree, every snapshot in the 247-commit rewritten lineage, and all
  commit messages contain no private hostname.
- `example.com` appears only as an explicitly documented reserved placeholder.
- All seven-character commit references in `docs/` resolve after updating the
  affected SHA values. The installed release directory's old name remains
  documented as external filesystem state, not as a current Git identifier.
- Legacy tag object `ce8130a` and peeled commit `970ebc9` are unchanged.
- Backend: 265 tests pass with warnings as errors.
- Frontend: clean install/audit reports zero vulnerabilities; all 72 tests and
  both root and `/chgka/` production builds pass.
- `docker compose config --quiet` passes locally without starting containers.
- Manual browser smoke is not required; runtime product behavior is unchanged.

## Publication boundary

The rewritten public `main` must be updated with `--force-with-lease` pinned to
the previously observed remote tip. The legacy tag must not be force-updated.
Offline rollback data and local rewrite backup refs remain until the remote result
is verified, then can be removed.

The guarded replacement and cleanup completed successfully. GitHub exposes no
`refs/pull/*`, but its API still resolves the unreachable pre-redaction commits
when their old SHA is supplied directly. This is outside branch history and is
normal GitHub object retention after a rewrite. A literal server-side purge
requires GitHub Support; old Actions runs were not deleted because that is a
separate destructive operation and does not guarantee object-cache removal.
