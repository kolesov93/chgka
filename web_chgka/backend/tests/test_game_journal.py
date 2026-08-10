from datetime import datetime, timedelta, timezone

from game_journal import (
    MODE_DEBUG,
    MODE_REGULAR,
    STATUS_COMPLETED,
    STATUS_INTERRUPTED,
    STATUS_RESET,
    GameJournal,
)


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def _journal(tmp_path, *, mode=MODE_DEBUG, id_factory=None):
    journal = GameJournal(
        tmp_path / "journal.sqlite3",
        default_mode=mode,
        clock=Clock(),
        id_factory=id_factory or (lambda: "session-1"),
    )
    journal.initialize()
    journal.configure_pack(
        fingerprint="pack-fingerprint",
        name="sample_questions",
        path=tmp_path / "pack",
    )
    return journal


def _opened(question_id, *, title, sector, part_index=None):
    return {
        "question_id": question_id,
        "title": title,
        "author": "Автор",
        "sector": sector,
        "kind": "blitz" if part_index is not None else "normal",
        "part_index": part_index,
    }


def test_journal_persists_ordered_full_log_and_part_level_questions(tmp_path):
    journal = _journal(tmp_path)
    journal.record_event("player_joined", "Игрок присоединился", {"name": "Иван"})
    journal.mark_started()
    journal.record_event(
        "question_opened",
        "Открыта часть 1",
        _opened("part-1", title="Первый вопрос", sector=4, part_index=0),
    )
    journal.record_event(
        "question_opened",
        "Открыта часть 1 повторно",
        _opened("part-1", title="Первый вопрос", sector=4, part_index=0),
    )
    journal.record_event(
        "question_opened",
        "Открыта часть 2",
        _opened("part-2", title="Второй вопрос", sector=4, part_index=1),
    )
    journal.record_event("answer_scored", "Очко знатокам", {"winner": "znatoki"})
    journal.complete_current({"znatoki": 6, "tv": 3})

    snapshot = journal.snapshot()
    assert snapshot["current_mode"] == MODE_DEBUG
    assert snapshot["sessions"][0]["status"] == STATUS_COMPLETED
    assert snapshot["sessions"][0]["score"] == {"znatoki": 6, "tv": 3}
    assert snapshot["sessions"][0]["opened_questions"] == 2

    detail = journal.get_session("session-1")
    assert [event["sequence_number"] for event in detail["events"]] == [1, 2, 3, 4, 5]
    assert [item["question_id"] for item in detail["opened_questions"]] == [
        "part-1",
        "part-2",
    ]
    assert detail["opened_questions"][0]["open_count"] == 2
    assert snapshot["used_questions"] == []


def test_regular_mode_is_the_only_question_history_filter(tmp_path):
    ids = iter(("debug-session", "regular-session"))
    journal = _journal(tmp_path, id_factory=lambda: next(ids))
    journal.mark_started()
    journal.record_event(
        "question_opened",
        "Отладочный вопрос",
        _opened("debug-question", title="Отладочный", sector=1),
    )
    journal.rotate_after_reset({"znatoki": 0, "tv": 0})
    journal.set_current_mode(MODE_REGULAR)
    assert journal.current_mode() == MODE_REGULAR
    journal.record_event(
        "question_opened",
        "Обычный вопрос",
        _opened("regular-question", title="Настоящий", sector=2),
    )

    assert [item["id"] for item in journal.list_sessions(mode=MODE_REGULAR)] == [
        "regular-session"
    ]
    assert [item["id"] for item in journal.list_sessions(mode=MODE_DEBUG)] == [
        "debug-session"
    ]
    debug_snapshot = journal.snapshot(mode=MODE_DEBUG)
    assert debug_snapshot["current_session"]["id"] == "regular-session"
    assert [item["id"] for item in debug_snapshot["sessions"]] == [
        "debug-session"
    ]

    assert [item["question_id"] for item in journal.used_questions()] == [
        "regular-question"
    ]

    journal.set_session_mode("debug-session", MODE_REGULAR)
    assert {item["question_id"] for item in journal.used_questions()} == {
        "debug-question",
        "regular-question",
    }
    journal.set_session_mode("regular-session", MODE_DEBUG)
    assert journal.current_mode() == MODE_DEBUG
    assert [item["question_id"] for item in journal.used_questions()] == [
        "debug-question"
    ]


def test_session_mode_filter_is_applied_before_limit(tmp_path):
    ids = iter(("regular-session", "newer-debug-session"))
    journal = _journal(tmp_path, id_factory=lambda: next(ids))
    journal.set_current_mode(MODE_REGULAR)
    journal.mark_started()
    journal.rotate_after_reset({"znatoki": 0, "tv": 0})

    assert [
        item["id"] for item in journal.list_sessions(limit=1, mode=MODE_REGULAR)
    ] == ["regular-session"]
    assert [
        item["id"] for item in journal.list_sessions(limit=1, mode=MODE_DEBUG)
    ] == ["newer-debug-session"]
    assert [item["id"] for item in journal.list_sessions(limit=1)] == [
        "newer-debug-session"
    ]


def test_reset_rotates_session_and_restart_marks_open_session_interrupted(tmp_path):
    ids = iter(("session-before-reset", "session-after-reset"))
    journal = _journal(tmp_path, id_factory=lambda: next(ids))
    journal.mark_started()
    journal.record_event("spin_started", "Вращение", {})
    new_session_id = journal.rotate_after_reset({"znatoki": 2, "tv": 1})

    assert new_session_id == "session-after-reset"
    sessions = {item["id"]: item for item in journal.list_sessions()}
    assert sessions["session-before-reset"]["status"] == STATUS_RESET
    assert sessions["session-before-reset"]["score"] == {"znatoki": 2, "tv": 1}
    assert sessions["session-after-reset"]["mode"] == MODE_DEBUG

    journal.close()
    restarted = GameJournal(
        tmp_path / "journal.sqlite3",
        default_mode=MODE_DEBUG,
        clock=Clock(),
    )
    restarted.initialize()
    assert restarted.recover_interrupted_sessions() == 1
    sessions = {item["id"]: item for item in restarted.list_sessions()}
    assert sessions["session-after-reset"]["status"] == STATUS_INTERRUPTED
