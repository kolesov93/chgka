# Task 0030: close backup SQLite connections

## Goal

Restore the backend CI job on Python 3.14 by explicitly closing every short-lived
SQLite connection used by the database-backup utility and its tests.

## Context

Main-branch CI at `84f1c67` completed 263 tests and then failed while collecting
nine unraisable `ResourceWarning: unclosed database` warnings. The named game
minutes test is only where garbage collection surfaced the warnings. The nine
connections come from three backup test paths, each opening three connections.

`sqlite3.Connection.__enter__` and `__exit__` manage a transaction; they do not
close the connection. Python 3.14 reports unclosed connections during finalization,
and CI intentionally promotes warnings to errors.

## Decisions

- Keep the backup algorithm and public CLI unchanged.
- Wrap every short-lived connection in `contextlib.closing`.
- Update test helpers as well as production code; tests must not depend on garbage
  collection for resource cleanup.
- Add a regression test that observes all connections opened by `create_backup`
  and proves they are unusable after the function returns.
- Verify the complete backend suite under Python 3.14 with `-W error`.

## Out of scope

- Changing the long-lived `GameJournal` connection or its FastAPI lifespan.
- Changing the SQLite schema, backup retention, deployment, or game behavior.
- Browser smoke: this is a backend resource-lifecycle fix with no user-visible
  behavior change.
