from state import (
    PHASE_LOGIN,
    PHASE_PRE_ROUND,
    create_initial_app_state,
    public_game_state,
    reset_app_state,
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
        "playback_generation": 0,
        "has_next": False,
    }


def _intro_authors():
    groups = []
    for sector in range(1, 13):
        card_count = 3 if sector in (4, 7) else 1
        groups.append(
            [
                {
                    "sector": sector,
                    "slot": slot,
                    "name": f"Author {sector}.{slot}",
                    "city": "Moscow" if sector == 1 else None,
                    "has_photo": slot == 1,
                }
                for slot in range(1, card_count + 1)
            ]
        )
    return groups


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
    assert state["presentation"]["intro"] is None
    assert state["presentation"]["shared_media"] is None
    assert state["presentation"]["blackbox"] is None
    assert state["presentation"]["blackbox_generation"] == 0
    assert state["pack"]["question_types"] is None
    assert state["pack"]["intro_authors"] is None
    assert state["logs"] == []


def test_create_initial_app_state_copies_pack_ui_metadata():
    question_types = ["normal", "blitz", "superblitz"]
    intro_authors = _intro_authors()
    state = create_initial_app_state(
        question_types=question_types,
        intro_authors=intro_authors,
    )

    assert state["pack"]["question_types"] == question_types
    assert state["pack"]["question_types"] is not question_types
    assert state["pack"]["intro_authors"] == intro_authors
    assert state["pack"]["intro_authors"] is not intro_authors
    assert state["pack"]["intro_authors"][0] is not intro_authors[0]
    assert state["pack"]["intro_authors"][0][0] is not intro_authors[0][0]


def test_reset_app_state_clears_runtime_fields_and_preserves_pack_metadata():
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal", "blitz"],
        intro_authors=_intro_authors(),
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
    state["presentation"]["intro"] = {
        "slide_index": 7,
        "started_at_ms": 1_000,
        "duration_ms": 87_757,
    }
    state["presentation"]["shared_media"] = _shared_image()
    state["presentation"]["blackbox"] = {
        "started_at_ms": 10_000,
        "playback_generation": 4,
    }
    state["presentation"]["blackbox_generation"] = 4
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
    assert state["presentation"]["intro"] is None
    assert state["presentation"]["shared_media"] is None
    assert state["presentation"]["blackbox"] is None
    assert state["presentation"]["blackbox_generation"] == 5
    assert state["pack"]["question_types"] == ["normal", "blitz"]
    assert state["pack"]["intro_authors"] == _intro_authors()
    assert state["logs"] == []


def test_public_game_state_flattens_app_state_for_current_frontend():
    state = create_initial_app_state(question_types=["normal"])
    state["game"]["used_questions"].append(3)
    state["game"]["score"]["znatoki"] = 1
    state["game"]["round"] = {
        "kind": "normal",
        "sector": 3,
        "respondent": {
            "participant_id": "participant-1",
            "group_id": "group-1",
            "name": "Иван",
        },
    }
    state["wheel"]["current_sector"] = 3
    state["wheel"]["target_angle"] = 12.5
    state["wheel"]["playing_sector"] = 3
    state["wheel"]["spin_duration"] = 5.5
    state["wheel"]["is_spinning"] = True
    state["timer"]["discussion_deadline_ms"] = 12345
    state["presentation"]["shared_media"] = _shared_image()
    state["logs"].append("hello")

    payload = public_game_state(state, now_ms=999_000)

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
        "round": {
            "kind": "normal",
            "sector": 3,
            "respondent": {
                "participant_id": "participant-1",
                "group_id": "group-1",
                "name": "Иван",
            },
        },
        "intro": None,
        "shared_media": {
            "type": "image",
            "media_id": "abc",
            "playback_state": "stopped",
            "position_ms": 0,
            "started_at_ms": None,
            "server_now_ms": 999_000,
            "playback_generation": 0,
            "has_next": False,
        },
        "blackbox": None,
    }
    assert payload["score"] is not state["game"]["score"]
    assert payload["used_questions"] is not state["game"]["used_questions"]
    assert payload["round"] is not state["game"]["round"]
    assert "server_now_ms" not in state["presentation"]["shared_media"]
    assert "media_ref" not in payload["shared_media"]
    assert "section" not in payload["shared_media"]
    assert "name" not in payload["shared_media"]

    payload["score"]["znatoki"] = 6
    payload["used_questions"].append(4)
    payload["round"]["sector"] = 4
    payload["round"]["respondent"]["name"] = "Мария"

    assert state["game"]["score"]["znatoki"] == 1
    assert state["game"]["used_questions"] == [3]
    assert state["game"]["round"]["sector"] == 3
    assert state["game"]["round"]["respondent"]["name"] == "Иван"


def test_public_game_state_serializes_intro_timing_for_reconnect():
    state = create_initial_app_state(intro_authors=_intro_authors())
    state["presentation"]["intro"] = {
        "slide_index": 4,
        "started_at_ms": 10_000,
        "duration_ms": 87_757,
    }

    payload = public_game_state(state, now_ms=13_750)

    assert payload["intro"] == {
        "slide_index": 4,
        "started_at_ms": 10_000,
        "duration_ms": 87_757,
        "server_now_ms": 13_750,
        "authors": [
            {
                "sector": 4,
                "slot": slot,
                "name": f"Author 4.{slot}",
                "city": None,
                "has_photo": slot == 1,
            }
            for slot in range(1, 4)
        ],
    }
    assert "server_now_ms" not in state["presentation"]["intro"]

    state["presentation"]["intro"]["slide_index"] = 13
    assert public_game_state(state, now_ms=14_000)["intro"]["authors"] == []


def test_public_game_state_serializes_server_time_for_audio_reconnect():
    state = create_initial_app_state()
    state["presentation"]["shared_media"] = {
        "type": "audio",
        "media_id": "audio-token",
        "media_ref": "audio-ref",
        "section": "question",
        "name": "melody.mp3",
        "playback_state": "playing",
        "position_ms": 0,
        "started_at_ms": 10_000,
        "playback_generation": 3,
        "has_next": True,
    }

    payload = public_game_state(state, now_ms=13_750)

    assert payload["shared_media"]["server_now_ms"] == 13_750
    assert payload["shared_media"]["started_at_ms"] == 10_000
    assert payload["shared_media"]["playback_generation"] == 3
    assert payload["shared_media"]["has_next"] is True
    assert "server_now_ms" not in state["presentation"]["shared_media"]


def test_public_game_state_serializes_blackbox_timeline_for_reconnect():
    state = create_initial_app_state()
    state["presentation"]["blackbox"] = {
        "started_at_ms": 10_000,
        "playback_generation": 3,
    }
    state["presentation"]["blackbox_generation"] = 3

    payload = public_game_state(state, now_ms=13_750)

    assert payload["blackbox"] == {
        "started_at_ms": 10_000,
        "playback_generation": 3,
        "server_now_ms": 13_750,
    }
    assert "server_now_ms" not in state["presentation"]["blackbox"]
