"""Durable SQLite journal for game sessions and structured events."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
import uuid


MODE_REGULAR = "regular"
MODE_DEBUG = "debug"
GAME_MODES = (MODE_REGULAR, MODE_DEBUG)

STATUS_LOBBY = "lobby"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_RESET = "reset"
STATUS_INTERRUPTED = "interrupted"

SCHEMA_VERSION = 1


class JournalError(RuntimeError):
    pass


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class GameJournal:
    def __init__(
        self,
        db_path: str | Path,
        *,
        default_mode: str,
        clock: Callable[[], datetime] = _default_clock,
        id_factory: Callable[[], object] = uuid.uuid4,
    ):
        self._db_path = str(db_path)
        self._default_mode = self._validate_mode(default_mode)
        self._pending_mode = self._default_mode
        self._clock = clock
        self._id_factory = id_factory
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._current_session_id: str | None = None
        self._pack_fingerprint: str | None = None
        self._pack_name: str | None = None
        self._pack_path: str | None = None

    @staticmethod
    def _validate_mode(mode: object) -> str:
        if mode not in GAME_MODES:
            raise JournalError("Game mode must be regular or debug")
        return str(mode)

    def _timestamp(self) -> str:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")

    def initialize(self) -> None:
        with self._lock:
            if self._connection is not None:
                return
            if self._db_path != ":memory:":
                Path(self._db_path).expanduser().resolve().parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
            connection = sqlite3.connect(
                self._db_path,
                timeout=5,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            if self._db_path != ":memory:":
                connection.execute("PRAGMA journal_mode = WAL")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                connection.close()
                raise JournalError(
                    f"Unsupported game journal schema version: {version}"
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL CHECK (mode IN ('regular', 'debug')),
                    status TEXT NOT NULL CHECK (
                        status IN ('lobby', 'active', 'completed', 'reset', 'interrupted')
                    ),
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    ended_at TEXT,
                    pack_fingerprint TEXT NOT NULL,
                    pack_name TEXT NOT NULL,
                    pack_path TEXT NOT NULL,
                    score_znatoki INTEGER,
                    score_tv INTEGER
                );

                CREATE TABLE IF NOT EXISTS game_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES game_sessions(id),
                    sequence_number INTEGER NOT NULL,
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    display_message TEXT NOT NULL,
                    UNIQUE(session_id, sequence_number)
                );

                CREATE INDEX IF NOT EXISTS game_events_session_order
                    ON game_events(session_id, sequence_number);
                CREATE INDEX IF NOT EXISTS game_events_type
                    ON game_events(event_type);
                """
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
            self._connection = connection

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
            self._current_session_id = None
            self._pending_mode = self._default_mode

    def _db(self) -> sqlite3.Connection:
        self.initialize()
        assert self._connection is not None
        return self._connection

    def configure_pack(
        self,
        *,
        fingerprint: str,
        name: str,
        path: str | Path,
    ) -> None:
        if not fingerprint or not name:
            raise JournalError("Pack fingerprint and name are required")
        self._pack_fingerprint = fingerprint
        self._pack_name = name
        self._pack_path = str(Path(path).resolve())

    def recover_interrupted_sessions(self) -> int:
        with self._lock, self._db() as connection:
            cursor = connection.execute(
                """
                UPDATE game_sessions
                SET status = ?, ended_at = COALESCE(ended_at, ?)
                WHERE status IN (?, ?)
                """,
                (
                    STATUS_INTERRUPTED,
                    self._timestamp(),
                    STATUS_LOBBY,
                    STATUS_ACTIVE,
                ),
            )
            self._current_session_id = None
            return cursor.rowcount

    def _ensure_session(self) -> str:
        if self._current_session_id is not None:
            return self._current_session_id
        if not self._pack_fingerprint or not self._pack_name or not self._pack_path:
            raise JournalError("Question pack is not configured for the game journal")
        session_id = str(self._id_factory())
        created_at = self._timestamp()
        with self._db() as connection:
            connection.execute(
                """
                INSERT INTO game_sessions (
                    id, mode, status, created_at,
                    pack_fingerprint, pack_name, pack_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    self._pending_mode,
                    STATUS_LOBBY,
                    created_at,
                    self._pack_fingerprint,
                    self._pack_name,
                    self._pack_path,
                ),
            )
        self._current_session_id = session_id
        return session_id

    def mark_started(self) -> str:
        with self._lock:
            session_id = self._ensure_session()
            with self._db() as connection:
                row = connection.execute(
                    "SELECT status FROM game_sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
                if row is None:
                    raise JournalError("Current game session no longer exists")
                if row["status"] in (STATUS_COMPLETED, STATUS_RESET, STATUS_INTERRUPTED):
                    self._current_session_id = None
                    return self.mark_started()
                connection.execute(
                    """
                    UPDATE game_sessions
                    SET status = ?, started_at = COALESCE(started_at, ?)
                    WHERE id = ?
                    """,
                    (STATUS_ACTIVE, self._timestamp(), session_id),
                )
            return session_id

    def set_current_mode(self, mode: object) -> str:
        normalized = self._validate_mode(mode)
        with self._lock:
            self._pending_mode = normalized
            if self._current_session_id is not None:
                with self._db() as connection:
                    connection.execute(
                        "UPDATE game_sessions SET mode = ? WHERE id = ?",
                        (normalized, self._current_session_id),
                    )
        return normalized

    def set_session_mode(self, session_id: object, mode: object) -> str:
        if not isinstance(session_id, str) or not session_id:
            raise JournalError("Session id is required")
        normalized = self._validate_mode(mode)
        with self._lock, self._db() as connection:
            cursor = connection.execute(
                "UPDATE game_sessions SET mode = ? WHERE id = ?",
                (normalized, session_id),
            )
            if cursor.rowcount != 1:
                raise JournalError("Game session not found")
            if session_id == self._current_session_id:
                self._pending_mode = normalized
        return normalized

    def record_event(
        self,
        event_type: str,
        message: str,
        payload: Mapping[str, object] | None = None,
    ) -> dict:
        if not event_type or not message:
            raise JournalError("Event type and display message are required")
        with self._lock:
            session_id = self._ensure_session()
            occurred_at = self._timestamp()
            encoded_payload = json.dumps(
                dict(payload or {}),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            with self._db() as connection:
                sequence = connection.execute(
                    """
                    SELECT COALESCE(MAX(sequence_number), 0) + 1
                    FROM game_events WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO game_events (
                        session_id, sequence_number, occurred_at,
                        event_type, payload_json, display_message
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        sequence,
                        occurred_at,
                        event_type,
                        encoded_payload,
                        message,
                    ),
                )
            return {
                "session_id": session_id,
                "sequence_number": sequence,
                "occurred_at": occurred_at,
                "event_type": event_type,
                "payload": dict(payload or {}),
                "display_message": message,
            }

    def complete_current(self, score: Mapping[str, object]) -> None:
        with self._lock:
            if self._current_session_id is None:
                return
            with self._db() as connection:
                connection.execute(
                    """
                    UPDATE game_sessions
                    SET status = ?, ended_at = ?, score_znatoki = ?, score_tv = ?
                    WHERE id = ?
                    """,
                    (
                        STATUS_COMPLETED,
                        self._timestamp(),
                        score.get("znatoki"),
                        score.get("tv"),
                        self._current_session_id,
                    ),
                )

    def rotate_after_reset(self, score: Mapping[str, object]) -> str:
        with self._lock:
            if self._current_session_id is not None:
                with self._db() as connection:
                    row = connection.execute(
                        "SELECT status FROM game_sessions WHERE id = ?",
                        (self._current_session_id,),
                    ).fetchone()
                    if row is not None and row["status"] != STATUS_COMPLETED:
                        connection.execute(
                            """
                            UPDATE game_sessions
                            SET status = ?, ended_at = ?,
                                score_znatoki = ?, score_tv = ?
                            WHERE id = ?
                            """,
                            (
                                STATUS_RESET,
                                self._timestamp(),
                                score.get("znatoki"),
                                score.get("tv"),
                                self._current_session_id,
                            ),
                        )
            self._current_session_id = None
            self._pending_mode = self._default_mode
            return self.mark_started()

    @staticmethod
    def _session_dict(row: sqlite3.Row, opened_count: int) -> dict:
        score = None
        if row["score_znatoki"] is not None and row["score_tv"] is not None:
            score = {
                "znatoki": row["score_znatoki"],
                "tv": row["score_tv"],
            }
        return {
            "id": row["id"],
            "mode": row["mode"],
            "status": row["status"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "pack_fingerprint": row["pack_fingerprint"],
            "pack_name": row["pack_name"],
            "score": score,
            "opened_questions": opened_count,
        }

    def _opened_question_count(self, session_id: str) -> int:
        event_rows = self._db().execute(
            """
            SELECT payload_json FROM game_events
            WHERE session_id = ? AND event_type = 'question_opened'
            """,
            (session_id,),
        ).fetchall()
        return len(
            {
                payload.get("question_id")
                for event_row in event_rows
                for payload in [json.loads(event_row["payload_json"])]
                if payload.get("question_id")
            }
        )

    def _session_summary(self, session_id: str) -> dict | None:
        row = self._db().execute(
            "SELECT * FROM game_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return self._session_dict(row, self._opened_question_count(session_id))

    def list_sessions(
        self,
        *,
        limit: int = 50,
        mode: str | None = None,
    ) -> list[dict]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
            raise JournalError("Session limit must be between 1 and 200")
        normalized_mode = None if mode is None else self._validate_mode(mode)
        with self._lock:
            if normalized_mode is None:
                rows = self._db().execute(
                    """
                    SELECT * FROM game_sessions
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = self._db().execute(
                    """
                    SELECT * FROM game_sessions
                    WHERE mode = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (normalized_mode, limit),
                ).fetchall()
            return [
                self._session_dict(row, self._opened_question_count(row["id"]))
                for row in rows
            ]

    def get_session(self, session_id: object) -> dict:
        if not isinstance(session_id, str) or not session_id:
            raise JournalError("Session id is required")
        with self._lock:
            row = self._db().execute(
                "SELECT * FROM game_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise JournalError("Game session not found")
            event_rows = self._db().execute(
                """
                SELECT sequence_number, occurred_at, event_type,
                       payload_json, display_message
                FROM game_events
                WHERE session_id = ?
                ORDER BY sequence_number ASC
                """,
                (session_id,),
            ).fetchall()
            events = [
                {
                    "sequence_number": event_row["sequence_number"],
                    "occurred_at": event_row["occurred_at"],
                    "event_type": event_row["event_type"],
                    "payload": json.loads(event_row["payload_json"]),
                    "display_message": event_row["display_message"],
                }
                for event_row in event_rows
            ]
            opened: dict[str, dict] = {}
            for event in events:
                if event["event_type"] != "question_opened":
                    continue
                question_id = event["payload"].get("question_id")
                if not question_id:
                    continue
                item = opened.setdefault(
                    question_id,
                    {
                        **event["payload"],
                        "opened_at": event["occurred_at"],
                        "open_count": 0,
                    },
                )
                item["open_count"] += 1
                item["last_opened_at"] = event["occurred_at"]
            return {
                "session": self._session_dict(row, len(opened)),
                "events": events,
                "opened_questions": list(opened.values()),
            }

    def used_questions(self) -> list[dict]:
        with self._lock:
            rows = self._db().execute(
                """
                SELECT e.occurred_at, e.payload_json
                FROM game_events e
                JOIN game_sessions s ON s.id = e.session_id
                WHERE e.event_type = 'question_opened' AND s.mode = ?
                ORDER BY e.occurred_at ASC, e.id ASC
                """,
                (MODE_REGULAR,),
            ).fetchall()
            used: dict[str, dict] = {}
            for row in rows:
                payload = json.loads(row["payload_json"])
                question_id = payload.get("question_id")
                if not question_id:
                    continue
                item = used.setdefault(
                    question_id,
                    {
                        **payload,
                        "first_opened_at": row["occurred_at"],
                        "open_count": 0,
                    },
                )
                item["open_count"] += 1
                item["last_opened_at"] = row["occurred_at"]
            return sorted(
                used.values(),
                key=lambda item: (item.get("last_opened_at", ""), item["question_id"]),
                reverse=True,
            )

    def snapshot(self, *, limit: int = 50, mode: str | None = None) -> dict:
        with self._lock:
            current = None
            if self._current_session_id is not None:
                current = self._session_summary(self._current_session_id)
            return {
                "current_mode": current["mode"] if current else self._pending_mode,
                "current_session": current,
                "sessions": self.list_sessions(limit=limit, mode=mode),
                "used_questions": self.used_questions(),
            }
