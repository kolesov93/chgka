"""Create and verify a consistent backup of the live SQLite journal."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3


BACKUP_PREFIX = "chgka-"
BACKUP_SUFFIX = ".sqlite3"


def _backup_name(now: datetime) -> str:
    normalized = now.astimezone(timezone.utc)
    return f"{BACKUP_PREFIX}{normalized:%Y%m%dT%H%M%SZ}{BACKUP_SUFFIX}"


def create_backup(source: Path, destination_dir: Path, *, now: datetime) -> Path:
    source = source.resolve()
    destination_dir = destination_dir.resolve()
    if not source.is_file():
        raise RuntimeError(f"SQLite source does not exist: {source}")

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / _backup_name(now)
    if destination.exists():
        raise RuntimeError(f"Backup already exists: {destination}")

    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)

    with closing(sqlite3.connect(destination)) as backup_connection:
        result = backup_connection.execute("PRAGMA quick_check").fetchone()
    if result != ("ok",):
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"SQLite backup integrity check failed: {result!r}")
    return destination


def prune_backups(
    destination_dir: Path,
    *,
    retain_days: int,
    now: datetime,
) -> list[Path]:
    if retain_days < 1:
        raise ValueError("retain_days must be at least 1")
    cutoff = now.astimezone(timezone.utc) - timedelta(days=retain_days)
    removed = []
    for backup in destination_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"):
        modified = datetime.fromtimestamp(backup.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            backup.unlink()
            removed.append(backup)
    return removed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination_dir", type=Path)
    parser.add_argument("--retain-days", type=int, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    now = datetime.now(timezone.utc)
    destination = create_backup(args.source, args.destination_dir, now=now)
    removed = prune_backups(
        args.destination_dir,
        retain_days=args.retain_days,
        now=now,
    )
    print(f"Backup created: {destination}")
    print(f"Old backups removed: {len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
