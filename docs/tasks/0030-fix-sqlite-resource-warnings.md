# Task 0030: close backup SQLite connections

## Goal

Restore the backend CI job on Python 3.14 by explicitly closing every short-lived
SQLite connection used by the database-backup utility and its tests.

## Cause

Main-branch CI at `c1e37cb` completed 263 tests and then failed while collecting
nine unraisable `ResourceWarning: unclosed database` warnings. The named game
minutes test is only where garbage collection surfaced the warnings. The nine
connections come from three backup test paths, each opening three connections.

`sqlite3.Connection.__enter__` and `__exit__` manage a transaction; they do not
close the connection. Python 3.14 reports unclosed connections during finalization,
and CI intentionally promotes warnings to errors.

## Implemented

- The backup source, destination, and integrity-check connections are wrapped in
  `contextlib.closing`; the backup algorithm and CLI remain unchanged.
- Backup test helpers explicitly close their own connections and explicitly
  commit fixture setup.
- A regression test observes all three connections opened by `create_backup`
  and proves they are closed before the function returns.

## Verification

- Local Python 3.10: `python3 -W error -m pytest -q -p no:cacheprovider` —
  265 passed.
- One-off Python 3.14 container reproduction using the pinned dev requirements
  and the repository test layout: `python -m pip check` and
  `python -W error -m pytest -q` — 265 passed. This was performed before the
  environment boundary was clarified; future development and test workloads
  belong only on the local machine or in CI, never on the VPS.
- Manual browser smoke: not required; no runtime game or UI behavior changed.

## Out of scope

- Changing the long-lived `GameJournal` connection or its FastAPI lifespan.
- Changing the SQLite schema, backup retention, deployment, or game behavior.
- Browser smoke: this is a backend resource-lifecycle fix with no user-visible
  behavior change.
