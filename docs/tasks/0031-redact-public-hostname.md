# Task 0031: redact public deployment hostname

## Goal

Remove the private production hostname from all files and commits reachable from
the public `main` branch while keeping deployment examples useful.

## Context

The repository currently exposes the real hostname in README, architecture,
deployment examples, Compose defaults, and task history. The first occurrence is
in the configurable-base-path work; 24 commits from that point through the current
tip are affected. The legacy Pyglet tag predates the hostname and does not contain
it.

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

## Verification plan

- Search the current tree and every commit reachable from rewritten `main` for
  the private hostname.
- Confirm `example.com` appears in the intended current files.
- Confirm the legacy tag object and peeled commit remain unchanged.
- Run backend tests, frontend tests/builds, and Compose validation because the
  current deployment examples and Compose default change.
- Manual browser smoke is not required; runtime product behavior is unchanged.
