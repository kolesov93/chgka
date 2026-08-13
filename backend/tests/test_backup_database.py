from contextlib import closing
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sqlite3

import pytest

from backup_database import create_backup, prune_backups


NOW = datetime(2026, 8, 13, 12, 34, 56, tzinfo=timezone.utc)


def _create_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, message TEXT)")
        connection.execute("INSERT INTO events (message) VALUES ('played')")
        connection.commit()


def test_create_backup_copies_and_verifies_live_database(tmp_path):
    source = tmp_path / "data" / "chgka.sqlite3"
    source.parent.mkdir()
    _create_database(source)

    backup = create_backup(source, tmp_path / "backups", now=NOW)

    assert backup.name == "chgka-20260813T123456Z.sqlite3"
    with closing(sqlite3.connect(backup)) as connection:
        assert connection.execute("SELECT message FROM events").fetchall() == [("played",)]
        assert connection.execute("PRAGMA quick_check").fetchone() == ("ok",)


def test_create_backup_closes_every_opened_connection(tmp_path, monkeypatch):
    source = tmp_path / "chgka.sqlite3"
    _create_database(source)
    opened_connections = []
    original_connect = sqlite3.connect

    def tracked_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        opened_connections.append(connection)
        return connection

    monkeypatch.setattr("backup_database.sqlite3.connect", tracked_connect)

    create_backup(source, tmp_path / "backups", now=NOW)

    assert len(opened_connections) == 3
    for connection in opened_connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_create_backup_refuses_missing_source_and_duplicate_name(tmp_path):
    with pytest.raises(RuntimeError, match="does not exist"):
        create_backup(tmp_path / "missing.sqlite3", tmp_path / "backups", now=NOW)

    source = tmp_path / "chgka.sqlite3"
    _create_database(source)
    create_backup(source, tmp_path / "backups", now=NOW)
    with pytest.raises(RuntimeError, match="already exists"):
        create_backup(source, tmp_path / "backups", now=NOW)


def test_prune_backups_removes_only_expired_managed_files(tmp_path):
    old_backup = tmp_path / "chgka-old.sqlite3"
    recent_backup = tmp_path / "chgka-recent.sqlite3"
    unrelated = tmp_path / "notes.txt"
    for path in (old_backup, recent_backup, unrelated):
        path.write_text("test", encoding="utf-8")
    old_timestamp = (NOW - timedelta(days=31)).timestamp()
    recent_timestamp = (NOW - timedelta(days=3)).timestamp()
    os.utime(old_backup, (old_timestamp, old_timestamp))
    os.utime(recent_backup, (recent_timestamp, recent_timestamp))
    os.utime(unrelated, (old_timestamp, old_timestamp))

    removed = prune_backups(tmp_path, retain_days=30, now=NOW)

    assert removed == [old_backup]
    assert not old_backup.exists()
    assert recent_backup.exists()
    assert unrelated.exists()


def test_prune_backups_rejects_non_positive_retention(tmp_path):
    with pytest.raises(ValueError, match="at least 1"):
        prune_backups(tmp_path, retain_days=0, now=NOW)
