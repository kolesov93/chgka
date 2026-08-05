import pytest

from live_ops import (
    live_ops_cancel_spin,
    live_ops_force_phase,
    live_ops_open_round,
    live_ops_reset_to_intro,
    live_ops_set_score,
    live_ops_set_sector_used,
    live_ops_set_timer,
)
from state import (
    PHASE_DISCUSSION,
    PHASE_INTRO,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    create_initial_app_state,
)
from transitions import (
    TransitionError,
    transition_complete_spin,
    transition_start_spin,
)


def _shared_image():
    return {
        "type": "image",
        "media_id": "abc",
        "media_ref": "image-ref",
        "section": "question",
        "name": "image.jpg",
        "playback_state": "stopped",
        "position_ms": 0,
        "started_at_ms": None,
    }


def _state(*, phase=PHASE_PRE_ROUND, question_types=None):
    return create_initial_app_state(
        phase=phase,
        question_types=question_types or ["normal"] * 13,
    )


def test_set_score_uses_exact_validated_values_without_changing_phase():
    state = _state(phase=PHASE_POST_ROUND)
    state["game"]["score"] = {"znatoki": 2, "tv": 3}

    effects = live_ops_set_score(state, znatoki=6, tv=1)

    assert state["game"]["score"] == {"znatoki": 6, "tv": 1}
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert effects.logs == ("Live Ops: счёт 2:3 -> 6:1",)

    with pytest.raises(TransitionError) as error:
        live_ops_set_score(state, znatoki=True, tv=0)
    assert error.value.code == "invalid_score"
    assert state["game"]["score"] == {"znatoki": 6, "tv": 1}


def test_toggle_sector_played_and_available_including_active_sector():
    state = _state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 4}
    state["game"]["used_questions"] = [2, 4]

    removed = live_ops_set_sector_used(state, sector=4, used=False)
    added = live_ops_set_sector_used(state, sector=3, used=True)

    assert state["game"]["used_questions"] == [2, 3]
    assert "true -> false" in removed.logs[0]
    assert "false -> true" in added.logs[0]


def test_open_normal_round_cancels_spin_and_normalizes_runtime_state():
    state = _state(phase=PHASE_PRE_ROUND)
    state["wheel"].update(
        {
            "is_spinning": True,
            "spin_id": 7,
            "target_angle": 120.0,
            "playing_sector": 8,
            "spin_duration": 5.0,
        }
    )
    state["timer"]["discussion_deadline_ms"] = 123
    state["presentation"]["shared_media"] = _shared_image()

    effects = live_ops_open_round(state, sector=5)

    assert state["game"]["phase"] == PHASE_QUESTION_READING
    assert state["game"]["round"] == {"kind": "normal", "sector": 5}
    assert state["game"]["used_questions"] == [5]
    assert state["wheel"]["current_sector"] == 5
    assert state["wheel"]["playing_sector"] == 5
    assert state["wheel"]["is_spinning"] is False
    assert state["wheel"]["spin_id"] == 8
    assert state["timer"]["discussion_deadline_ms"] is None
    assert state["presentation"]["shared_media"] is None
    assert effects.clear_media_tokens is True
    assert effects.refresh_admin_question is True
    assert effects.stop_sounds is True


def test_open_blitz_round_requires_valid_part_and_does_not_partially_mutate():
    question_types = ["normal"] * 13
    question_types[3] = "blitz"
    state = _state(question_types=question_types)

    with pytest.raises(TransitionError) as error:
        live_ops_open_round(state, sector=4)
    assert error.value.code == "invalid_part"
    assert state["game"]["round"] is None
    assert state["game"]["used_questions"] == []

    effects = live_ops_open_round(state, sector=4, part_index=1)

    assert state["game"]["round"] == {
        "kind": "blitz",
        "sector": 4,
        "part_index": 1,
    }
    assert "часть 2/3" in effects.logs[0]


def test_force_question_phase_requires_round_before_mutating_spin():
    state = _state()
    state["wheel"]["is_spinning"] = True
    state["wheel"]["spin_id"] = 9

    with pytest.raises(TransitionError) as error:
        live_ops_force_phase(
            state,
            phase=PHASE_QUESTION_READING,
            now_ms=1_000,
            normal_discussion_seconds=60,
            blitz_discussion_seconds=20,
        )

    assert error.value.code == "no_round"
    assert state["wheel"]["is_spinning"] is True
    assert state["wheel"]["spin_id"] == 9


def test_force_phases_normalize_timer_media_and_round_context():
    state = _state(phase=PHASE_POST_ROUND)
    state["game"]["round"] = {
        "kind": "normal",
        "sector": 6,
        "advance_next_part": True,
    }
    state["presentation"]["shared_media"] = _shared_image()

    reading = live_ops_force_phase(
        state,
        phase=PHASE_QUESTION_READING,
        now_ms=10_000,
        normal_discussion_seconds=60,
        blitz_discussion_seconds=20,
    )
    assert state["game"]["phase"] == PHASE_QUESTION_READING
    assert "advance_next_part" not in state["game"]["round"]
    assert state["presentation"]["shared_media"] is None
    assert reading.clear_media_tokens is True
    assert reading.refresh_admin_question is True

    live_ops_force_phase(
        state,
        phase=PHASE_DISCUSSION,
        now_ms=10_000,
        normal_discussion_seconds=60,
        blitz_discussion_seconds=20,
    )
    assert state["timer"]["discussion_deadline_ms"] == 70_000

    live_ops_force_phase(
        state,
        phase=PHASE_TEAM_ANSWER,
        now_ms=20_000,
        normal_discussion_seconds=60,
        blitz_discussion_seconds=20,
    )
    assert state["timer"]["discussion_deadline_ms"] is None

    live_ops_force_phase(
        state,
        phase=PHASE_POST_ROUND,
        now_ms=20_000,
        normal_discussion_seconds=60,
        blitz_discussion_seconds=20,
    )
    assert state["game"]["phase"] == PHASE_POST_ROUND

    pre_round = live_ops_force_phase(
        state,
        phase=PHASE_PRE_ROUND,
        now_ms=20_000,
        normal_discussion_seconds=60,
        blitz_discussion_seconds=20,
    )
    assert state["game"]["round"] is None
    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert pre_round.clear_admin_question is True


def test_force_discussion_uses_blitz_duration():
    state = _state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "superblitz", "sector": 7, "part_index": 2}

    live_ops_force_phase(
        state,
        phase=PHASE_DISCUSSION,
        now_ms=1_000,
        normal_discussion_seconds=60,
        blitz_discussion_seconds=20,
    )

    assert state["timer"]["discussion_deadline_ms"] == 21_000


def test_reset_to_intro_clears_progress_and_restarts_timeline():
    state = _state(phase=PHASE_POST_ROUND)
    state["game"]["score"] = {"znatoki": 4, "tv": 3}
    state["game"]["used_questions"] = [1, 2, 8]
    state["game"]["round"] = {"kind": "normal", "sector": 8}
    state["wheel"].update(
        {
            "current_sector": 8,
            "target_angle": 45.0,
            "playing_sector": 8,
            "spin_duration": 5.0,
            "is_spinning": True,
            "spin_id": 7,
        }
    )
    state["timer"]["discussion_deadline_ms"] = 99_000
    state["presentation"]["shared_media"] = _shared_image()

    effects = live_ops_reset_to_intro(state, now_ms=50_000)

    assert state["game"] == {
        "phase": PHASE_INTRO,
        "score": {"znatoki": 0, "tv": 0},
        "used_questions": [],
        "round": None,
    }
    assert state["wheel"]["spin_id"] == 8
    assert state["wheel"]["is_spinning"] is False
    assert state["timer"]["discussion_deadline_ms"] is None
    assert state["presentation"] == {
        "intro": {
            "slide_index": 0,
            "started_at_ms": 50_000,
            "duration_ms": 87_757,
        },
        "shared_media": None,
    }
    assert effects.sounds == ("intro",)
    assert effects.stop_sounds is True
    assert effects.clear_media_tokens is True
    assert effects.clear_admin_question is True


def test_cancel_spin_invalidates_sleeping_completion_and_preserves_progress():
    state = _state()
    state["game"]["score"] = {"znatoki": 2, "tv": 1}
    state["game"]["used_questions"] = [1, 3]
    state["wheel"]["current_sector"] = 3
    started = transition_start_spin(
        state,
        raw_angle=20.0,
        raw_sector=4,
        duration=5.0,
    )

    effects = live_ops_cancel_spin(state)

    assert state["game"]["score"] == {"znatoki": 2, "tv": 1}
    assert state["game"]["used_questions"] == [1, 3]
    assert state["wheel"]["current_sector"] == 3
    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert effects.stop_sounds is True
    with pytest.raises(TransitionError) as error:
        transition_complete_spin(state, spin_id=started.spin_id)
    assert error.value.code == "stale_spin"


def test_timer_recovery_supports_custom_value_stop_and_validation():
    state = _state(phase=PHASE_DISCUSSION)
    state["game"]["round"] = {"kind": "normal", "sector": 2}
    state["timer"]["discussion_deadline_ms"] = 15_000

    set_effects = live_ops_set_timer(state, seconds=60, now_ms=10_000)
    assert state["timer"]["discussion_deadline_ms"] == 70_000
    assert set_effects.logs == ("Live Ops: таймер 5 -> 60 сек.",)

    stop_effects = live_ops_set_timer(state, seconds=None, now_ms=20_000)
    assert state["timer"]["discussion_deadline_ms"] is None
    assert stop_effects.logs == ("Live Ops: таймер 50 -> None сек.",)

    with pytest.raises(TransitionError) as error:
        live_ops_set_timer(state, seconds=601, now_ms=20_000)
    assert error.value.code == "invalid_timer"

    state["game"]["phase"] = PHASE_TEAM_ANSWER
    with pytest.raises(TransitionError) as error:
        live_ops_set_timer(state, seconds=10, now_ms=20_000)
    assert error.value.code == "bad_phase"
