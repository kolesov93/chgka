import pytest

from state import (
    PHASE_DISCUSSION,
    PHASE_LOGIN,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    create_initial_app_state,
)
from transitions import (
    TransitionError,
    transition_complete_spin,
    transition_end_round,
    transition_reset,
    transition_score,
    transition_start_discussion,
    transition_start_game,
    transition_start_spin,
    transition_team_answer,
    transition_ten_seconds,
)


def test_start_game_changes_login_to_pre_round_once():
    state = create_initial_app_state()

    effects = transition_start_game(state)

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert effects.logs == ("Игра началась!",)
    with pytest.raises(TransitionError, match="PRE_ROUND"):
        transition_start_game(state)


def test_spin_skips_used_sectors_across_wrap_and_completes_normal_round():
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal"] * 13,
    )
    state["game"]["used_questions"] = [12, 13]

    started = transition_start_spin(
        state,
        raw_angle=10.0,
        raw_sector=12,
        duration=5.0,
    )

    assert started.playing_sector == 1
    assert started.spin_id == 1
    assert started.clear_media_tokens is True
    assert state["wheel"]["is_spinning"] is True

    completed = transition_complete_spin(state, spin_id=started.spin_id)

    assert state["game"]["phase"] == PHASE_QUESTION_READING
    assert state["game"]["round"] == {"kind": "normal", "sector": 1}
    assert state["game"]["used_questions"] == [12, 13, 1]
    assert completed.refresh_admin_question is True


def test_spin_completion_uses_pack_type_for_blitz():
    question_types = ["normal"] * 13
    question_types[3] = "blitz"
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=question_types,
    )

    started = transition_start_spin(
        state,
        raw_angle=20.0,
        raw_sector=4,
        duration=5.0,
    )
    transition_complete_spin(state, spin_id=started.spin_id)

    assert state["game"]["round"] == {
        "kind": "blitz",
        "sector": 4,
        "part_index": 0,
    }


def test_reset_invalidates_pending_spin_completion():
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal"] * 13,
    )
    started = transition_start_spin(
        state,
        raw_angle=20.0,
        raw_sector=2,
        duration=5.0,
    )

    transition_reset(state)

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["wheel"]["spin_id"] > started.spin_id
    with pytest.raises(TransitionError) as exc_info:
        transition_complete_spin(state, spin_id=started.spin_id)
    assert exc_info.value.code == "stale_spin"
    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["used_questions"] == []


def test_spin_rejects_when_all_sectors_are_used_without_mutation():
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    state["game"]["used_questions"] = list(range(1, 14))

    with pytest.raises(TransitionError) as exc_info:
        transition_start_spin(
            state,
            raw_angle=20.0,
            raw_sector=2,
            duration=5.0,
        )

    assert exc_info.value.code == "no_questions"
    assert state["wheel"]["is_spinning"] is False


def test_discussion_to_team_answer_flow_sets_timer_and_sound():
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 2}

    transition_start_discussion(state, deadline_ms=123_000)
    assert state["game"]["phase"] == PHASE_DISCUSSION
    assert state["timer"]["discussion_deadline_ms"] == 123_000

    effects = transition_team_answer(state)
    assert state["game"]["phase"] == PHASE_TEAM_ANSWER
    assert state["timer"]["discussion_deadline_ms"] is None
    assert effects.sounds == ("sig1",)


def test_ten_seconds_requires_discussion():
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)

    with pytest.raises(TransitionError) as exc_info:
        transition_ten_seconds(state, deadline_ms=10_000)

    assert exc_info.value.code == "bad_phase"
    assert state["timer"]["discussion_deadline_ms"] is None


def test_normal_score_is_atomic_and_second_score_is_rejected():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "normal", "sector": 2}

    effects = transition_score(
        state,
        winner="znatoki",
        correct_sound="yes1",
        incorrect_sound="no1",
    )

    assert state["game"]["score"] == {"znatoki": 1, "tv": 0}
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert effects.sounds == ("yes1",)

    with pytest.raises(TransitionError) as exc_info:
        transition_score(
            state,
            winner="znatoki",
            correct_sound="yes1",
            incorrect_sound="no1",
        )
    assert exc_info.value.code == "bad_phase"
    assert state["game"]["score"] == {"znatoki": 1, "tv": 0}


def test_sixth_point_still_finishes_post_round_but_blocks_next_spin():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "normal", "sector": 6}
    state["game"]["score"]["znatoki"] = 5

    transition_score(
        state,
        winner="znatoki",
        correct_sound="yes1",
        incorrect_sound="no1",
    )

    assert state["game"]["score"]["znatoki"] == 6
    assert state["game"]["phase"] == PHASE_POST_ROUND
    transition_end_round(state, gong_sound="gong1")
    assert state["game"]["phase"] == PHASE_PRE_ROUND
    with pytest.raises(TransitionError) as exc_info:
        transition_start_spin(
            state,
            raw_angle=20.0,
            raw_sector=2,
            duration=5.0,
        )
    assert exc_info.value.code == "game_finished"
    assert state["game"]["score"]["znatoki"] == 6


def test_blitz_correct_intermediate_answer_advances_after_post_round():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "blitz", "sector": 4, "part_index": 0}

    score_effects = transition_score(
        state,
        winner="znatoki",
        correct_sound="yes1",
        incorrect_sound="no1",
    )

    assert state["game"]["score"] == {"znatoki": 0, "tv": 0}
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert state["game"]["round"]["advance_next_part"] is True
    assert score_effects.sounds == ()

    end_effects = transition_end_round(state, gong_sound="gong1")

    assert state["game"]["phase"] == PHASE_QUESTION_READING
    assert state["game"]["round"] == {"kind": "blitz", "sector": 4, "part_index": 1}
    assert end_effects.sounds == ()
    assert end_effects.clear_media_tokens is True
    assert end_effects.refresh_admin_question is True


def test_blitz_wrong_answer_awards_tv_and_ends_round():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "superblitz", "sector": 7, "part_index": 1}

    effects = transition_score(
        state,
        winner="tv",
        correct_sound="yes1",
        incorrect_sound="no2",
    )

    assert state["game"]["score"] == {"znatoki": 0, "tv": 1}
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert effects.sounds == ("no2",)


def test_last_blitz_answer_awards_znatoki():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "blitz", "sector": 4, "part_index": 2}

    effects = transition_score(
        state,
        winner="znatoki",
        correct_sound="yes2",
        incorrect_sound="no1",
    )

    assert state["game"]["score"] == {"znatoki": 1, "tv": 0}
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert effects.sounds == ("yes2",)


def test_normal_end_round_clears_round_media_and_timer():
    state = create_initial_app_state(phase=PHASE_POST_ROUND)
    state["game"]["round"] = {"kind": "normal", "sector": 3}
    state["presentation"]["shared_media"] = {"type": "image", "media_id": "abc"}
    state["timer"]["discussion_deadline_ms"] = 123

    effects = transition_end_round(state, gong_sound="gong3")

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["round"] is None
    assert state["presentation"]["shared_media"] is None
    assert state["timer"]["discussion_deadline_ms"] is None
    assert effects.sounds == ("gong3",)
    assert effects.clear_media_tokens is True


def test_invalid_blitz_advance_does_not_partially_mutate_state():
    state = create_initial_app_state(phase=PHASE_POST_ROUND)
    state["game"]["round"] = {
        "kind": "blitz",
        "sector": 4,
        "part_index": 2,
        "advance_next_part": True,
    }
    state["presentation"]["shared_media"] = {"type": "image", "media_id": "abc"}
    state["timer"]["discussion_deadline_ms"] = 123

    with pytest.raises(TransitionError) as exc_info:
        transition_end_round(state, gong_sound="gong1")

    assert exc_info.value.code == "invalid_round"
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert state["presentation"]["shared_media"] == {"type": "image", "media_id": "abc"}
    assert state["timer"]["discussion_deadline_ms"] == 123
