from state import (
    PHASE_LOGIN,
    PHASE_PRE_ROUND,
    create_initial_app_state,
    public_game_state,
    reset_app_state,
)


def test_create_initial_app_state_defaults():
    state = create_initial_app_state()

    assert state["game"]["phase"] == PHASE_LOGIN
    assert state["game"]["score"] == {"znatoki": 0, "tv": 0}
    assert state["game"]["used_questions"] == []
    assert state["game"]["round"] is None
    assert state["wheel"]["current_sector"] == 1
    assert state["wheel"]["target_angle"] is None
    assert state["wheel"]["playing_sector"] is None
    assert state["wheel"]["spin_duration"] == 0
    assert state["wheel"]["is_spinning"] is False
    assert state["wheel"]["spin_id"] == 0
    assert state["timer"]["discussion_deadline_ms"] is None
    assert state["presentation"]["shared_media"] is None
    assert state["pack"]["question_types"] is None
    assert state["logs"] == []


def test_create_initial_app_state_copies_question_types():
    question_types = ["normal", "blitz", "superblitz"]
    state = create_initial_app_state(question_types=question_types)

    assert state["pack"]["question_types"] == question_types
    assert state["pack"]["question_types"] is not question_types


def test_reset_app_state_clears_runtime_fields_and_preserves_question_types():
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal", "blitz"],
    )
    state["game"]["score"] = {"znatoki": 5, "tv": 4}
    state["game"]["used_questions"] = [1, 2, 9]
    state["game"]["round"] = {"kind": "blitz", "sector": 4, "part_index": 1, "advance_next_part": True}
    state["wheel"]["current_sector"] = 9
    state["wheel"]["target_angle"] = 42.5
    state["wheel"]["playing_sector"] = 9
    state["wheel"]["spin_duration"] = 7.2
    state["wheel"]["is_spinning"] = True
    state["wheel"]["spin_id"] = 7
    state["timer"]["discussion_deadline_ms"] = 12345
    state["presentation"]["shared_media"] = {"type": "image", "media_id": "abc"}
    state["logs"] = ["old log"]

    reset_app_state(state)

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["score"] == {"znatoki": 0, "tv": 0}
    assert state["game"]["used_questions"] == []
    assert state["game"]["round"] is None
    assert state["wheel"]["current_sector"] == 1
    assert state["wheel"]["target_angle"] is None
    assert state["wheel"]["playing_sector"] is None
    assert state["wheel"]["spin_duration"] == 0
    assert state["wheel"]["is_spinning"] is False
    assert state["wheel"]["spin_id"] == 8
    assert state["timer"]["discussion_deadline_ms"] is None
    assert state["presentation"]["shared_media"] is None
    assert state["pack"]["question_types"] == ["normal", "blitz"]
    assert state["logs"] == []


def test_public_game_state_flattens_app_state_for_current_frontend():
    state = create_initial_app_state(question_types=["normal"])
    state["game"]["used_questions"].append(3)
    state["game"]["score"]["znatoki"] = 1
    state["game"]["round"] = {"kind": "normal", "sector": 3}
    state["wheel"]["current_sector"] = 3
    state["wheel"]["target_angle"] = 12.5
    state["wheel"]["playing_sector"] = 3
    state["wheel"]["spin_duration"] = 5.5
    state["wheel"]["is_spinning"] = True
    state["timer"]["discussion_deadline_ms"] = 12345
    state["presentation"]["shared_media"] = {"type": "image", "media_id": "abc"}
    state["logs"].append("hello")

    payload = public_game_state(state)

    assert payload == {
        "phase": PHASE_LOGIN,
        "score": {"znatoki": 1, "tv": 0},
        "current_sector": 3,
        "target_angle": 12.5,
        "playing_sector": 3,
        "spin_duration": 5.5,
        "used_questions": [3],
        "is_spinning": True,
        "logs": ["hello"],
        "question_types": ["normal"],
        "discussion_deadline_ms": 12345,
        "round": {"kind": "normal", "sector": 3},
        "shared_media": {"type": "image", "media_id": "abc"},
    }
    assert payload["score"] is not state["game"]["score"]
    assert payload["used_questions"] is not state["game"]["used_questions"]
    assert payload["round"] is not state["game"]["round"]

    payload["score"]["znatoki"] = 6
    payload["used_questions"].append(4)
    payload["round"]["sector"] = 4

    assert state["game"]["score"]["znatoki"] == 1
    assert state["game"]["used_questions"] == [3]
    assert state["game"]["round"]["sector"] == 3
