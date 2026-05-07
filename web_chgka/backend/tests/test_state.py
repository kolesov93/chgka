from state import (
    PHASE_LOGIN,
    PHASE_PRE_ROUND,
    create_initial_game_state,
    public_game_state,
    reset_game_state,
)


def test_create_initial_game_state_defaults():
    state = create_initial_game_state()

    assert state["phase"] == PHASE_LOGIN
    assert state["score"] == {"znatoki": 0, "tv": 0}
    assert state["current_sector"] == 1
    assert state["target_angle"] is None
    assert state["playing_sector"] is None
    assert state["spin_duration"] == 0
    assert state["used_questions"] == []
    assert state["is_spinning"] is False
    assert state["logs"] == []
    assert state["question_types"] is None
    assert state["discussion_deadline_ms"] is None
    assert state["round"] is None
    assert state["shared_media"] is None


def test_create_initial_game_state_copies_question_types():
    question_types = ["normal", "blitz", "superblitz"]
    state = create_initial_game_state(question_types=question_types)

    assert state["question_types"] == question_types
    assert state["question_types"] is not question_types


def test_reset_game_state_clears_runtime_fields_and_preserves_question_types():
    state = create_initial_game_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal", "blitz"],
    )
    state["score"] = {"znatoki": 5, "tv": 4}
    state["current_sector"] = 9
    state["target_angle"] = 42.5
    state["playing_sector"] = 9
    state["spin_duration"] = 7.2
    state["used_questions"] = [1, 2, 9]
    state["is_spinning"] = True
    state["logs"] = ["old log"]
    state["discussion_deadline_ms"] = 12345
    state["round"] = {"kind": "blitz", "sector": 4, "part_index": 1, "advance_next_part": True}
    state["shared_media"] = {"type": "image", "media_id": "abc"}

    reset_game_state(state)

    assert state["phase"] == PHASE_PRE_ROUND
    assert state["score"] == {"znatoki": 0, "tv": 0}
    assert state["current_sector"] == 1
    assert state["target_angle"] is None
    assert state["playing_sector"] is None
    assert state["spin_duration"] == 0
    assert state["used_questions"] == []
    assert state["is_spinning"] is False
    assert state["logs"] == []
    assert state["question_types"] == ["normal", "blitz"]
    assert state["discussion_deadline_ms"] is None
    assert state["round"] is None
    assert state["shared_media"] is None


def test_public_game_state_is_wire_compatible_copy():
    state = create_initial_game_state(question_types=["normal"])
    state["used_questions"].append(3)
    state["score"]["znatoki"] = 1
    state["round"] = {"kind": "normal", "sector": 3}

    payload = public_game_state(state)

    assert payload == state
    assert payload is not state
    assert payload["score"] is not state["score"]
    assert payload["used_questions"] is not state["used_questions"]
    assert payload["round"] is not state["round"]

    payload["score"]["znatoki"] = 6
    payload["used_questions"].append(4)
    payload["round"]["sector"] = 4

    assert state["score"]["znatoki"] == 1
    assert state["used_questions"] == [3]
    assert state["round"]["sector"] == 3
