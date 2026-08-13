import pytest

from state import (
    PHASE_DISCUSSION,
    PHASE_GAME_OVER,
    PHASE_INTRO,
    PHASE_LOGIN,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    create_initial_app_state,
)
from transitions import (
    TransitionError,
    transition_advance_intro,
    transition_complete_spin,
    transition_end_round,
    transition_reset,
    transition_select_respondent,
    transition_skip_intro,
    transition_score,
    transition_start_discussion,
    transition_start_blackbox,
    transition_end_blackbox,
    transition_start_game,
    transition_start_intro_music,
    transition_start_spin,
    transition_team_answer,
    transition_ten_seconds,
)


def _respondent(name="Иван"):
    return {
        "participant_id": "participant-1",
        "group_id": "group-1",
        "name": name,
    }


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


def test_start_game_enters_silent_intro_and_music_starts_once_on_command():
    state = create_initial_app_state()

    effects = transition_start_game(state)

    assert state["game"]["phase"] == PHASE_INTRO
    assert state["presentation"]["intro"] == {
        "slide_index": 0,
        "started_at_ms": None,
        "duration_ms": 87_757,
    }
    assert effects.logs == ("Интро началось",)
    assert effects.sounds == ()
    with pytest.raises(TransitionError, match="Интро"):
        transition_start_game(state)

    music = transition_start_intro_music(state, now_ms=10_000)
    assert state["presentation"]["intro"]["started_at_ms"] == 10_000
    assert music.sounds == ("intro",)
    with pytest.raises(TransitionError) as exc_info:
        transition_start_intro_music(state, now_ms=10_001)
    assert exc_info.value.code == "intro_music_started"


def test_intro_advances_exactly_once_and_rejects_stale_repeat():
    state = create_initial_app_state()
    transition_start_game(state)

    effects = transition_advance_intro(state, expected_slide=0)

    assert state["presentation"]["intro"]["slide_index"] == 1
    assert effects.logs == ("Интро: слайд 01",)
    with pytest.raises(TransitionError) as exc_info:
        transition_advance_intro(state, expected_slide=0)
    assert exc_info.value.code == "stale_intro"
    assert state["presentation"]["intro"]["slide_index"] == 1


def test_final_intro_step_stops_music_and_enters_pre_round():
    state = create_initial_app_state()
    transition_start_game(state)
    for expected_slide in range(13):
        transition_advance_intro(state, expected_slide=expected_slide)
        assert state["presentation"]["intro"]["slide_index"] == expected_slide + 1

    effects = transition_advance_intro(state, expected_slide=13)

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["presentation"]["intro"] is None
    assert state["game"]["score"] == {"znatoki": 0, "tv": 0}
    assert effects.stop_sounds is True


@pytest.mark.parametrize("slide_index", range(14))
def test_intro_can_be_skipped_atomically_from_every_slide(slide_index):
    state = create_initial_app_state()
    transition_start_game(state)
    state["presentation"]["intro"]["slide_index"] = slide_index
    state["presentation"]["intro"]["started_at_ms"] = 10_000
    state["game"]["score"] = {"znatoki": 2, "tv": 1}

    effects = transition_skip_intro(state, expected_slide=slide_index)

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["presentation"]["intro"] is None
    assert state["game"]["score"] == {"znatoki": 2, "tv": 1}
    assert effects.stop_sounds is True
    assert effects.events[0].event_type == "intro_skipped"
    assert effects.events[0].payload["slide_index"] == slide_index


def test_intro_skip_rejects_stale_invalid_and_repeated_actions():
    state = create_initial_app_state()
    transition_start_game(state)
    state["presentation"]["intro"]["slide_index"] = 4

    with pytest.raises(TransitionError) as exc_info:
        transition_skip_intro(state, expected_slide=3)
    assert exc_info.value.code == "stale_intro"
    assert state["game"]["phase"] == PHASE_INTRO

    with pytest.raises(TransitionError) as exc_info:
        transition_skip_intro(state, expected_slide=True)
    assert exc_info.value.code == "invalid_intro_slide"

    transition_skip_intro(state, expected_slide=4)
    with pytest.raises(TransitionError) as exc_info:
        transition_skip_intro(state, expected_slide=4)
    assert exc_info.value.code == "bad_phase"


def test_blackbox_start_replaces_media_and_natural_end_returns_table():
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 9}
    state["presentation"]["shared_media"] = _shared_image()

    started = transition_start_blackbox(state, enabled=True, now_ms=10_000)

    active = state["presentation"]["blackbox"]
    assert active == {"started_at_ms": 10_000, "playback_generation": 1}
    assert state["presentation"]["shared_media"] is None
    assert started.start_sound_output is True

    with pytest.raises(TransitionError) as exc_info:
        transition_start_discussion(state, deadline_ms=70_000)
    assert exc_info.value.code == "blackbox_active"
    assert state["game"]["phase"] == PHASE_QUESTION_READING

    ended = transition_end_blackbox(
        state,
        expected_generation=active["playback_generation"],
        natural=True,
    )

    assert state["presentation"]["blackbox"] is None
    assert state["presentation"]["shared_media"] is None
    assert "музыка завершилась" in ended.logs[0]
    transition_start_discussion(state, deadline_ms=70_000)
    assert state["game"]["phase"] == PHASE_DISCUSSION


def test_blackbox_rejects_unmarked_question_and_stale_stop():
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 1}

    with pytest.raises(TransitionError) as exc_info:
        transition_start_blackbox(state, enabled=False, now_ms=10_000)
    assert exc_info.value.code == "blackbox_unavailable"

    transition_start_blackbox(state, enabled=True, now_ms=10_000)
    with pytest.raises(TransitionError) as exc_info:
        transition_end_blackbox(state, expected_generation=0)
    assert exc_info.value.code == "stale_blackbox"
    assert state["presentation"]["blackbox"] is not None

    generation = state["presentation"]["blackbox"]["playback_generation"]
    stopped = transition_end_blackbox(state, expected_generation=generation)
    assert "остановлен ведущим" in stopped.logs[0]
    assert state["presentation"]["blackbox"] is None


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
    assert started.start_sound_output is True
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

    effects = transition_reset(state)

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["wheel"]["spin_id"] > started.spin_id
    with pytest.raises(TransitionError) as exc_info:
        transition_complete_spin(state, spin_id=started.spin_id)
    assert exc_info.value.code == "stale_spin"
    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["used_questions"] == []
    assert effects.stop_sounds is True
    assert effects.clear_admin_question is True


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


def test_normal_respondent_is_selected_only_after_team_answer_and_required_for_score():
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 2}

    with pytest.raises(TransitionError) as exc_info:
        transition_select_respondent(state, **_respondent())
    assert exc_info.value.code == "bad_phase"

    transition_start_discussion(state, deadline_ms=60_000)
    transition_team_answer(state)
    with pytest.raises(TransitionError) as exc_info:
        transition_score(
            state,
            winner="znatoki",
            correct_sound="yes1",
            incorrect_sound="no1",
        )
    assert exc_info.value.code == "respondent_required"

    effects = transition_select_respondent(state, **_respondent())
    assert state["game"]["round"]["respondent"] == _respondent()
    assert effects.events[0].event_type == "respondent_selected"
    assert effects.events[0].payload["part_index"] is None


def test_superblitz_requires_one_early_respondent_and_retains_them_for_next_part():
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {
        "kind": "superblitz",
        "sector": 7,
        "part_index": 0,
    }

    with pytest.raises(TransitionError) as exc_info:
        transition_start_discussion(state, deadline_ms=20_000)
    assert exc_info.value.code == "respondent_required"

    transition_select_respondent(state, **_respondent("Мария"))
    transition_start_discussion(state, deadline_ms=20_000)
    transition_team_answer(state)
    transition_score(
        state,
        winner="znatoki",
        correct_sound="yes1",
        incorrect_sound="no1",
    )
    effects = transition_end_round(state, gong_sound="gong1")

    assert state["game"]["round"]["part_index"] == 1
    assert state["game"]["round"]["respondent"] == _respondent("Мария")
    assert [event.event_type for event in effects.events] == [
        "question_opened",
        "respondent_selected",
    ]
    assert effects.events[1].payload["retained"] is True
    assert effects.events[1].payload["part_index"] == 1

    with pytest.raises(TransitionError) as exc_info:
        transition_select_respondent(
            state,
            participant_id="participant-2",
            group_id="group-2",
            name="Алексей",
        )
    assert exc_info.value.code == "respondent_locked"
    assert state["game"]["round"]["respondent"] == _respondent("Мария")


def test_ten_seconds_requires_discussion():
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)

    with pytest.raises(TransitionError) as exc_info:
        transition_ten_seconds(state, deadline_ms=10_000)

    assert exc_info.value.code == "bad_phase"
    assert state["timer"]["discussion_deadline_ms"] is None


def test_normal_score_is_atomic_and_second_score_is_rejected():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {
        "kind": "normal",
        "sector": 2,
        "respondent": _respondent(),
    }

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


def test_sixth_point_stays_in_post_round_until_explicit_final_action():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {
        "kind": "normal",
        "sector": 6,
        "respondent": _respondent(),
    }
    state["game"]["score"]["znatoki"] = 5
    state["presentation"]["shared_media"] = _shared_image()
    state["timer"]["discussion_deadline_ms"] = 123
    state["wheel"]["target_angle"] = 42.0
    state["wheel"]["playing_sector"] = 6
    state["wheel"]["spin_duration"] = 5.0

    transition_score(
        state,
        winner="znatoki",
        correct_sound="yes1",
        incorrect_sound="no1",
    )

    assert state["game"]["score"]["znatoki"] == 6
    assert state["game"]["phase"] == PHASE_POST_ROUND
    effects = transition_end_round(state, gong_sound="gong1")

    assert state["game"]["phase"] == PHASE_GAME_OVER
    assert state["game"]["round"] is None
    assert state["presentation"]["shared_media"] is None
    assert state["timer"]["discussion_deadline_ms"] is None
    assert state["wheel"]["target_angle"] is None
    assert state["wheel"]["playing_sector"] is None
    assert state["wheel"]["spin_duration"] == 0
    assert effects.sounds == ("final",)
    assert effects.stop_sounds is True
    assert effects.clear_media_tokens is True
    assert effects.clear_admin_question is True
    assert "Победа Знатоков: 6:0" in effects.logs[0]

    with pytest.raises(TransitionError) as exc_info:
        transition_start_spin(
            state,
            raw_angle=20.0,
            raw_sector=2,
            duration=5.0,
        )
    assert exc_info.value.code == "bad_phase"
    assert state["game"]["score"]["znatoki"] == 6


def test_pre_round_score_guard_still_blocks_spin_at_six_points():
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    state["game"]["score"]["tv"] = 6

    with pytest.raises(TransitionError) as exc_info:
        transition_start_spin(
            state,
            raw_angle=20.0,
            raw_sector=2,
            duration=5.0,
        )

    assert exc_info.value.code == "game_finished"


def test_scoring_rejects_recovery_state_that_already_has_a_winner():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "normal", "sector": 2}
    state["game"]["score"] = {"znatoki": 2, "tv": 6}

    with pytest.raises(TransitionError) as exc_info:
        transition_score(
            state,
            winner="znatoki",
            correct_sound="yes1",
            incorrect_sound="no1",
        )

    assert exc_info.value.code == "game_finished"
    assert state["game"]["score"] == {"znatoki": 2, "tv": 6}
    assert state["game"]["phase"] == PHASE_TEAM_ANSWER


def test_tv_win_and_pending_blitz_advance_finalize_instead_of_advancing():
    state = create_initial_app_state(phase=PHASE_POST_ROUND)
    state["game"]["round"] = {
        "kind": "blitz",
        "sector": 4,
        "part_index": 0,
        "advance_next_part": True,
    }
    state["game"]["score"]["tv"] = 6

    effects = transition_end_round(state, gong_sound="gong1")

    assert state["game"]["phase"] == PHASE_GAME_OVER
    assert state["game"]["round"] is None
    assert effects.sounds == ("final",)
    assert "Победа Телезрителей: 0:6" in effects.logs[0]


def test_ambiguous_recovery_score_must_be_fixed_before_finalization():
    state = create_initial_app_state(phase=PHASE_POST_ROUND)
    state["game"]["round"] = {"kind": "normal", "sector": 6}
    state["game"]["score"] = {"znatoki": 6, "tv": 6}

    with pytest.raises(TransitionError) as exc_info:
        transition_end_round(state, gong_sound="gong1")

    assert exc_info.value.code == "invalid_score"
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert state["game"]["round"] == {"kind": "normal", "sector": 6}


def test_blitz_correct_intermediate_answer_advances_after_post_round():
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {
        "kind": "blitz",
        "sector": 4,
        "part_index": 0,
        "respondent": _respondent(),
    }

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
    state["game"]["round"] = {
        "kind": "superblitz",
        "sector": 7,
        "part_index": 1,
        "respondent": _respondent(),
    }

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
    state["game"]["round"] = {
        "kind": "blitz",
        "sector": 4,
        "part_index": 2,
        "respondent": _respondent(),
    }

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
    state["presentation"]["shared_media"] = _shared_image()
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
    state["presentation"]["shared_media"] = _shared_image()
    state["timer"]["discussion_deadline_ms"] = 123

    with pytest.raises(TransitionError) as exc_info:
        transition_end_round(state, gong_sound="gong1")

    assert exc_info.value.code == "invalid_round"
    assert state["game"]["phase"] == PHASE_POST_ROUND
    assert state["presentation"]["shared_media"] == _shared_image()
    assert state["timer"]["discussion_deadline_ms"] == 123
