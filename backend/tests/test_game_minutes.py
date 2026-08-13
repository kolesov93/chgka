import pytest

from state import (
    PHASE_DISCUSSION,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    create_initial_app_state,
)
from transitions import (
    TransitionError,
    transition_clear_captain,
    transition_early_answer,
    transition_end_round,
    transition_repayment_answer,
    transition_request_credit_minute,
    transition_request_credit_repayment,
    transition_request_early_answer,
    transition_resolve_strategy_request,
    transition_schedule_credit_repayment,
    transition_score,
    transition_select_captain,
    transition_select_respondent,
    transition_spend_earned_minute,
    transition_start_discussion,
    transition_start_spin,
    transition_take_credit_minute,
    transition_team_answer,
)


HOST = {"role": "host"}
CAPTAIN = {
    "role": "captain",
    "participant_id": "participant-1",
    "group_id": "group-1",
    "name": "Иван",
}
RESPONDENT = {
    "participant_id": "participant-1",
    "group_id": "group-1",
    "name": "Иван",
}


def _question_state(*, kind="normal", score=None):
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {
        "kind": kind,
        "sector": 2,
        **({"part_index": 0} if kind in ("blitz", "superblitz") else {}),
    }
    if score is not None:
        state["game"]["score"] = dict(score)
    return state


def _show_author(state):
    state["presentation"]["shared_media"] = {
        "type": "image",
        "media_id": "author-token",
        "media_ref": "author:question-id",
        "section": "author",
        "name": "Елена Орлова",
        "playback_state": "stopped",
        "position_ms": 0,
        "started_at_ms": None,
        "playback_generation": 0,
        "has_next": False,
        "presentation_kind": "author",
        "author_name": "Елена Орлова",
        "author_city": None,
        "author_asset": "photo",
        "has_photo": True,
    }


def _start_base(state, *, started=10_000, seconds=60):
    transition_start_discussion(
        state,
        started_at_ms=started,
        deadline_ms=started + seconds * 1_000,
    )


def _score(state, winner):
    if not state["game"]["round"].get("respondent"):
        transition_select_respondent(state, **RESPONDENT)
    return transition_score(
        state,
        winner=winner,
        correct_sound="yes1",
        incorrect_sound="no1",
    )


def test_captain_selection_replacement_and_group_scoped_clear():
    state = create_initial_app_state()

    selected = transition_select_captain(state, **RESPONDENT)
    assert state["game"]["team"]["captain"] == RESPONDENT
    assert selected.events[0].event_type == "captain_selected"

    with pytest.raises(TransitionError) as error:
        transition_select_captain(state, **RESPONDENT)
    assert error.value.code == "captain_unchanged"

    unchanged = transition_clear_captain(state, expected_group_id="other-group")
    assert unchanged.events == ()
    assert state["game"]["team"]["captain"] == RESPONDENT

    cleared = transition_clear_captain(
        state,
        expected_group_id="group-1",
        reason="player_kicked",
    )
    assert state["game"]["team"]["captain"] is None
    assert cleared.events[0].payload["reason"] == "player_kicked"


def test_early_answer_is_direct_for_host_but_captain_request_needs_decision():
    reading = _question_state()
    request = transition_request_early_answer(
        reading,
        now_ms=1_000,
        actor=CAPTAIN,
    )
    assert request.events[0].event_type == "early_answer_requested"
    assert reading["game"]["round"]["strategy_request"]["requested_phase"] == PHASE_QUESTION_READING
    with pytest.raises(TransitionError) as error:
        transition_start_discussion(reading, started_at_ms=2_000, deadline_ms=62_000)
    assert error.value.code == "strategy_request_pending"

    approved = transition_resolve_strategy_request(reading, approve=True, now_ms=3_000)
    assert reading["game"]["phase"] == PHASE_TEAM_ANSWER
    assert reading["game"]["round"]["early_answer"] is True
    assert [event.event_type for event in approved.events][:2] == [
        "strategy_request_approved",
        "early_answer_declared",
    ]

    rejected = _question_state()
    transition_request_early_answer(rejected, now_ms=1_000, actor=CAPTAIN)
    effects = transition_resolve_strategy_request(rejected, approve=False, now_ms=2_000)
    assert effects.events[0].event_type == "early_answer_request_rejected"
    assert "strategy_request" not in rejected["game"]["round"]
    assert rejected["game"]["phase"] == PHASE_QUESTION_READING

    direct = _question_state()
    _show_author(direct)
    direct_effects = transition_early_answer(direct, now_ms=1_000, actor=HOST)
    assert direct["game"]["phase"] == PHASE_TEAM_ANSWER
    assert direct["presentation"]["shared_media"] is None
    assert direct_effects.events[0].event_type == "author_hidden"


def test_captain_request_has_five_seconds_but_host_has_the_full_base_minute():
    state = _question_state()
    _start_base(state)
    generation = state["timer"]["generation"]

    effects = transition_request_early_answer(
        state,
        now_ms=14_999,
        actor=CAPTAIN,
        expected_generation=generation,
    )
    assert state["game"]["phase"] == PHASE_DISCUSSION
    assert state["timer"]["discussion_deadline_ms"] == 70_000
    assert state["game"]["round"]["strategy_request"]["type"] == "early_answer"
    assert effects.events[0].payload["actor_role"] == "captain"

    transition_resolve_strategy_request(state, approve=True, now_ms=20_000)
    assert state["game"]["phase"] == PHASE_TEAM_ANSWER

    state = _question_state()
    _start_base(state)
    with pytest.raises(TransitionError) as error:
        transition_request_early_answer(state, now_ms=15_000, actor=CAPTAIN)
    assert error.value.code == "captain_window_closed"

    transition_early_answer(state, now_ms=69_999, actor=HOST)
    assert state["game"]["phase"] == PHASE_TEAM_ANSWER

    state = _question_state()
    _start_base(state)
    with pytest.raises(TransitionError) as error:
        transition_early_answer(state, now_ms=70_000, actor=HOST)
    assert error.value.code == "timer_finished"


def test_stale_timer_repair_keeps_pending_request_for_a_host_decision():
    state = _question_state()
    _start_base(state)
    transition_request_early_answer(
        state,
        now_ms=12_000,
        actor=CAPTAIN,
        expected_generation=state["timer"]["generation"],
    )
    state["timer"]["generation"] += 1

    with pytest.raises(TransitionError) as error:
        transition_resolve_strategy_request(state, approve=True, now_ms=13_000)

    assert error.value.code == "stale_timer"
    assert state["game"]["round"]["strategy_request"]["type"] == "early_answer"
    assert state["game"]["phase"] == PHASE_DISCUSSION


def test_correct_early_answer_awards_once_and_wrong_answer_does_not():
    state = _question_state()
    transition_request_early_answer(state, now_ms=1_000, actor=CAPTAIN)
    transition_resolve_strategy_request(state, approve=True, now_ms=2_000)
    effects = _score(state, "znatoki")

    assert state["game"]["team"]["earned_minutes"] == 1
    assert [event.event_type for event in effects.events][-1] == "earned_minute_awarded"

    with pytest.raises(TransitionError) as error:
        _score(state, "znatoki")
    assert error.value.code == "bad_phase"
    assert state["game"]["team"]["earned_minutes"] == 1

    wrong = _question_state()
    _start_base(wrong)
    transition_early_answer(wrong, now_ms=12_000, actor=HOST)
    _score(wrong, "tv")
    assert wrong["game"]["team"]["earned_minutes"] == 0


def test_multiple_earned_minutes_follow_host_answer_without_waiting_for_deadline():
    state = _question_state()
    state["game"]["team"]["earned_minutes"] = 2
    _start_base(state, started=0)
    transition_team_answer(state)
    answer_generation = state["timer"]["generation"]

    first = transition_spend_earned_minute(
        state,
        now_ms=10_000,
        actor=CAPTAIN,
        expected_generation=answer_generation,
    )
    assert state["game"]["team"]["earned_minutes"] == 1
    assert state["game"]["phase"] == PHASE_DISCUSSION
    assert state["timer"]["segment"] == "earned"
    assert state["timer"]["discussion_deadline_ms"] == 70_000
    assert first.events[0].payload["balance_after"] == 1

    with pytest.raises(TransitionError) as error:
        transition_spend_earned_minute(
            state,
            now_ms=10_000,
            actor=HOST,
            expected_generation=answer_generation,
        )
    assert error.value.code == "bad_phase"

    transition_team_answer(state)
    transition_spend_earned_minute(state, now_ms=20_000, actor=HOST)
    assert state["game"]["team"]["earned_minutes"] == 0
    assert state["game"]["round"]["extra_minutes_spent"] == 2
    assert state["timer"]["discussion_deadline_ms"] == 80_000


def test_blitz_earned_minutes_lock_to_the_first_selected_part():
    state = _question_state(kind="blitz")
    state["game"]["team"]["earned_minutes"] = 2
    _start_base(state, started=0, seconds=20)
    transition_team_answer(state)
    transition_spend_earned_minute(state, now_ms=5_000, actor=CAPTAIN)
    assert state["game"]["round"]["extra_part_index"] == 0

    transition_team_answer(state)
    _score(state, "znatoki")
    transition_end_round(state, gong_sound="gong1")
    _start_base(state, started=20_000, seconds=20)
    transition_team_answer(state)
    state["game"]["round"]["part_index"] = 1
    with pytest.raises(TransitionError) as error:
        transition_spend_earned_minute(state, now_ms=30_000, actor=CAPTAIN)
    assert error.value.code == "earned_part_locked"
    assert state["game"]["team"]["earned_minutes"] == 1


def test_credit_is_one_use_at_x_to_five_and_debt_needs_a_round_win():
    state = _question_state(score={"znatoki": 2, "tv": 5})
    _start_base(state, started=0)
    transition_team_answer(state)
    requested = transition_request_credit_minute(state, now_ms=10_000, actor=CAPTAIN)

    assert requested.events[0].event_type == "credit_minute_requested"
    assert state["game"]["team"]["credit"]["used"] is False
    assert state["game"]["round"]["strategy_request"]["type"] == "credit"
    with pytest.raises(TransitionError) as error:
        _score(state, "znatoki")
    assert error.value.code == "strategy_request_pending"

    taken = transition_resolve_strategy_request(state, approve=True, now_ms=12_000)

    assert state["game"]["team"]["credit"]["used"] is True
    assert state["game"]["phase"] == PHASE_DISCUSSION
    assert state["timer"]["segment"] == "credit"
    assert "credit_minute_taken" in [event.event_type for event in taken.events]

    transition_team_answer(state)
    effects = _score(state, "znatoki")
    assert state["game"]["score"] == {"znatoki": 3, "tv": 5}
    assert state["game"]["team"]["credit"] == {
        "used": True,
        "debt": True,
        "repayment_scheduled": False,
        "forced": False,
    }
    assert "credit_debt_created" in [event.event_type for event in effects.events]

    wrong = _question_state(score={"znatoki": 2, "tv": 5})
    _start_base(wrong, started=0)
    transition_team_answer(wrong)
    transition_take_credit_minute(wrong, now_ms=10_000, actor=HOST)
    transition_team_answer(wrong)
    effects = _score(wrong, "tv")
    assert wrong["game"]["score"]["tv"] == 6
    assert wrong["game"]["team"]["credit"]["debt"] is False
    assert "credit_round_lost" in [event.event_type for event in effects.events]


def test_credit_at_four_to_five_forces_next_repayment():
    state = _question_state(score={"znatoki": 4, "tv": 5})
    _start_base(state, started=0)
    transition_team_answer(state)
    transition_take_credit_minute(state, now_ms=10_000, actor=HOST)
    transition_team_answer(state)
    effects = _score(state, "znatoki")

    assert state["game"]["score"] == {"znatoki": 5, "tv": 5}
    assert state["game"]["team"]["credit"]["repayment_scheduled"] is True
    assert state["game"]["team"]["credit"]["forced"] is True
    assert "credit_repayment_scheduled" in [event.event_type for event in effects.events]


def test_captain_repayment_request_needs_host_decision_before_the_next_spin():
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    state["game"]["team"]["credit"].update({"used": True, "debt": True})

    requested = transition_request_credit_repayment(
        state,
        now_ms=10_000,
        actor=CAPTAIN,
    )
    request = state["game"]["team"]["credit"]["repayment_request"]
    assert request["type"] == "repayment"
    assert request["requested_phase"] == PHASE_PRE_ROUND
    assert requested.events[0].event_type == "credit_repayment_requested"
    assert state["game"]["team"]["credit"]["repayment_scheduled"] is False

    with pytest.raises(TransitionError) as error:
        transition_start_spin(
            state,
            raw_angle=10.0,
            raw_sector=3,
            duration=1.0,
        )
    assert error.value.code == "strategy_request_pending"

    with pytest.raises(TransitionError) as error:
        transition_schedule_credit_repayment(state, actor=HOST)
    assert error.value.code == "strategy_request_pending"

    rejected = transition_resolve_strategy_request(state, approve=False, now_ms=11_000)
    assert rejected.events[0].event_type == "credit_repayment_request_rejected"
    assert "repayment_request" not in state["game"]["team"]["credit"]
    assert state["game"]["team"]["credit"]["repayment_scheduled"] is False

    transition_request_credit_repayment(state, now_ms=12_000, actor=CAPTAIN)
    effects = transition_resolve_strategy_request(state, approve=True, now_ms=13_000)
    assert state["game"]["team"]["credit"]["repayment_scheduled"] is True
    assert [event.event_type for event in effects.events] == [
        "strategy_request_approved",
        "credit_repayment_scheduled",
    ]
    assert effects.events[1].payload["actor_role"] == "captain"

    with pytest.raises(TransitionError) as error:
        transition_schedule_credit_repayment(state, actor=HOST)
    assert error.value.code == "repayment_scheduled"

    late = _question_state()
    late["game"]["team"]["credit"].update({"used": True, "debt": True})
    with pytest.raises(TransitionError) as error:
        transition_schedule_credit_repayment(late, actor=HOST)
    assert error.value.code == "repayment_too_late"


def test_post_round_repayment_request_blocks_round_end_and_stale_resolution():
    state = _question_state()
    state["game"]["phase"] = PHASE_POST_ROUND
    state["game"]["team"]["credit"].update({"used": True, "debt": True})

    transition_request_credit_repayment(state, now_ms=20_000, actor=CAPTAIN)
    with pytest.raises(TransitionError) as error:
        transition_end_round(state, gong_sound="gong1")
    assert error.value.code == "strategy_request_pending"

    state["game"]["phase"] = PHASE_PRE_ROUND
    with pytest.raises(TransitionError) as error:
        transition_resolve_strategy_request(state, approve=True, now_ms=21_000)
    assert error.value.code == "stale_strategy_request"
    assert state["game"]["team"]["credit"]["repayment_request"]["type"] == "repayment"


def test_normal_repayment_enters_answer_without_timer_and_clears_debt():
    state = _question_state()
    _show_author(state)
    state["game"]["round"]["credit_repayment"] = True
    state["game"]["team"]["credit"] = {
        "used": True,
        "debt": True,
        "repayment_scheduled": True,
        "forced": False,
    }

    with pytest.raises(TransitionError) as error:
        transition_start_discussion(state, started_at_ms=0, deadline_ms=60_000)
    assert error.value.code == "credit_repayment"

    effects = transition_repayment_answer(state)
    assert state["game"]["phase"] == PHASE_TEAM_ANSWER
    assert state["presentation"]["shared_media"] is None
    assert state["timer"]["discussion_deadline_ms"] is None
    assert state["game"]["team"]["credit"] == {
        "used": True,
        "debt": False,
        "repayment_scheduled": False,
        "forced": False,
    }
    event_types = [event.event_type for event in effects.events]
    assert event_types[0] == "author_hidden"
    assert "credit_repayment_completed" in event_types


def test_blitz_credit_debt_appears_only_after_the_third_correct_part():
    state = _question_state(kind="blitz", score={"znatoki": 1, "tv": 5})
    _start_base(state, started=0, seconds=20)
    transition_team_answer(state)
    transition_take_credit_minute(state, now_ms=10_000, actor=HOST)
    transition_team_answer(state)
    _score(state, "znatoki")
    assert state["game"]["team"]["credit"]["debt"] is False

    transition_end_round(state, gong_sound="gong1")
    _start_base(state, started=100_000, seconds=20)
    transition_team_answer(state)
    _score(state, "znatoki")
    assert state["game"]["team"]["credit"]["debt"] is False

    transition_end_round(state, gong_sound="gong1")
    _start_base(state, started=200_000, seconds=20)
    transition_team_answer(state)
    effects = _score(state, "znatoki")
    assert state["game"]["score"] == {"znatoki": 2, "tv": 5}
    assert state["game"]["team"]["credit"]["debt"] is True
    assert "credit_debt_created" in [event.event_type for event in effects.events]
