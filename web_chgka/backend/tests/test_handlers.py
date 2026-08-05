import asyncio
from pathlib import Path

import pytest

import main
from questions import parse_question_pack
from sound_control import begin_fade, create_sound_control_state
from state import (
    PHASE_DISCUSSION,
    PHASE_GAME_OVER,
    PHASE_INTRO,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    create_initial_app_state,
)


SAMPLE_PACK = Path(__file__).parent.parent.parent / "fixtures" / "sample_questions"


class FakeSio:
    def __init__(self, *, yield_on_emit=True):
        self.events = []
        self.sessions = {}
        self.yield_on_emit = yield_on_emit

    async def emit(self, event, data=None, **kwargs):
        self.events.append((event, data, kwargs))
        if self.yield_on_emit:
            await asyncio.sleep(0)

    async def save_session(self, sid, data):
        self.sessions[sid] = data

    async def get_session(self, sid):
        return self.sessions.get(sid, {"role": "player"})


async def _allow_admin(_sid):
    return True


async def _deny_admin(_sid):
    return False


@pytest.fixture(autouse=True)
def _isolated_global_settings(monkeypatch):
    monkeypatch.setattr(
        main,
        "global_settings",
        {"volume": 1.0, "sound_control": create_sound_control_state()},
    )


def test_concurrent_score_handlers_award_only_one_point(monkeypatch):
    fake_sio = FakeSio()
    state = create_initial_app_state(phase=PHASE_TEAM_ANSWER)
    state["game"]["round"] = {"kind": "normal", "sector": 1}
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "loaded_pack", None)
    monkeypatch.setattr(main, "players_list", [])

    async def run():
        await asyncio.gather(
            main.admin_score("admin", {"winner": "znatoki"}),
            main.admin_score("admin", {"winner": "znatoki"}),
        )

    asyncio.run(run())

    assert state["game"]["score"] == {"znatoki": 1, "tv": 0}
    assert any(event == "admin_notification" for event, _, _ in fake_sio.events)


def test_intro_handlers_broadcast_each_slide_once_and_stop_on_completion(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state()
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "players_list", [])
    monkeypatch.setattr(main, "_now_ms", lambda: 10_000)

    async def run():
        await main.start_game("admin")
        await asyncio.gather(
            main.admin_advance_intro("admin", {"expected_slide": 0}),
            main.admin_advance_intro("admin", {"expected_slide": 0}),
        )
        state["presentation"]["intro"]["slide_index"] = 13
        await main.admin_advance_intro("admin", {"expected_slide": 13})

    asyncio.run(run())

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["presentation"]["intro"] is None
    assert any(
        event == "play_sound" and data == {"sound": "intro"}
        for event, data, _kwargs in fake_sio.events
    )
    assert sum(
        event == "state_update"
        and bool(data["intro"])
        and data["intro"]["slide_index"] == 1
        for event, data, _kwargs in fake_sio.events
    ) == 1
    assert any(event == "admin_notification" for event, _, _ in fake_sio.events)
    assert any(event == "stop_sound" for event, _, _ in fake_sio.events)


def test_intro_advance_requires_admin(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_INTRO)
    state["presentation"]["intro"] = {
        "slide_index": 0,
        "started_at_ms": 10_000,
        "duration_ms": 87_757,
    }
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _deny_admin)
    monkeypatch.setattr(main, "app_state", state)

    asyncio.run(main.admin_advance_intro("player", {"expected_slide": 0}))

    assert state["presentation"]["intro"]["slide_index"] == 0
    assert fake_sio.events == []


def test_pack_info_includes_intro_speech_for_admin_only(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    fake_sio.sessions = {
        "admin": {"role": "admin"},
        "player": {"role": "player"},
    }
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(
        main,
        "pack_admin_info",
        {"question_titles": [], "question_types": [], "intro_html": "<p>Речь</p>"},
    )

    async def run():
        await main._emit_pack_info_to_admin("player")
        await main._emit_pack_info_to_admin("admin")

    asyncio.run(run())

    pack_events = [
        (data, kwargs)
        for event, data, kwargs in fake_sio.events
        if event == "pack_info"
    ]
    assert pack_events == [
        (
            {"pack": main.pack_admin_info},
            {"to": "admin"},
        )
    ]


def test_end_round_at_six_broadcasts_final_state_and_sound(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_POST_ROUND)
    state["game"]["round"] = {"kind": "normal", "sector": 6}
    state["game"]["score"] = {"znatoki": 6, "tv": 4}
    media_tokens = {"old": {"expires_at": 999.0}}
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "loaded_pack", None)
    monkeypatch.setattr(main, "media_tokens", media_tokens)
    monkeypatch.setattr(
        main,
        "players_list",
        [{"sid": "admin", "role": "admin", "online": True}],
    )

    asyncio.run(main.admin_end_round("admin"))

    assert state["game"]["phase"] == PHASE_GAME_OVER
    assert media_tokens == {}
    event_names = [event for event, _, _ in fake_sio.events]
    stop_index = event_names.index("stop_sound")
    final_index = next(
        index
        for index, (event, data, _kwargs) in enumerate(fake_sio.events)
        if event == "play_sound" and data == {"sound": "final"}
    )
    state_index = next(
        index
        for index, (event, data, _kwargs) in enumerate(fake_sio.events)
        if event == "state_update" and data["phase"] == PHASE_GAME_OVER
    )
    assert stop_index < final_index < state_index
    assert any(
        event == "admin_question" and data is None
        for event, data, _kwargs in fake_sio.events
    )


def test_reset_during_spin_keeps_reset_state(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal"] * 13,
    )
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "calculate_spin_result", lambda *_args: (10.0, 2))

    async def reset_instead_of_wait(_duration):
        await main.admin_reset("admin")

    monkeypatch.setattr(main.asyncio, "sleep", reset_instead_of_wait)

    asyncio.run(main.admin_spin("admin"))

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["used_questions"] == []
    assert state["wheel"]["is_spinning"] is False
    assert any(event == "stop_sound" for event, _, _ in fake_sio.events)


def test_pending_player_stays_pending_after_restore(monkeypatch):
    fake_sio = FakeSio()
    player = {
        "sid": "old",
        "name": "Pending Player",
        "role": "player",
        "token": "player-token",
        "online": False,
        "pending": True,
    }
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "app_state", create_initial_app_state(phase=PHASE_PRE_ROUND))
    monkeypatch.setattr(main, "players_list", [player])

    asyncio.run(main.restore_session("new", {"player_token": "player-token"}))

    restored_events = [
        event
        for event, _, _ in fake_sio.events
        if event in ("join_pending", "join_success")
    ]
    assert restored_events == ["join_pending"]
    assert player["sid"] == "new"
    assert player["pending"] is True


def test_audio_resolve_share_play_pause_stop_and_http_context(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 3}
    state["wheel"]["spin_id"] = 7
    pack = parse_question_pack(SAMPLE_PACK)
    now = [100.0]

    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "loaded_pack", pack)
    monkeypatch.setattr(main, "media_tokens", {})
    monkeypatch.setattr(
        main,
        "players_list",
        [{"sid": "admin", "role": "admin", "online": True}],
    )
    monkeypatch.setattr(main.time, "time", lambda: now[0])

    descriptor = next(iter(main._get_current_media_catalog().values()))

    async def run_flow():
        await main._emit_current_question_to_admins()
        question_payload = next(
            data
            for event, data, _kwargs in fake_sio.events
            if event == "admin_question"
        )
        assert question_payload["media"] == [descriptor.public_descriptor()]
        assert "path" not in question_payload["media"][0]

        legacy = await main.admin_resolve_media(
            "admin",
            {"media_type": "audio", "media_path": "media/melody.mp3"},
        )
        assert legacy == {"ok": False, "error": "missing_media_ref"}

        resolved = await main.admin_resolve_media(
            "admin",
            {"media_ref": descriptor.media_ref},
        )
        assert resolved["ok"] is True
        assert resolved["type"] == "audio"
        assert resolved["section"] == "question"
        assert resolved["name"] == "melody.mp3"

        media_id = resolved["media_id"]
        response = await main.get_media(media_id)
        assert Path(response.path).name == "melody.mp3"

        await main.admin_share_media("admin", {"media_id": media_id})
        shared = state["presentation"]["shared_media"]
        assert shared["playback_state"] == "stopped"

        await main.admin_play_media("admin")
        assert shared["playback_state"] == "playing"
        assert shared["started_at_ms"] == 100_000

        now[0] = 102.5
        await main.admin_pause_media("admin")
        assert shared["playback_state"] == "paused"
        assert shared["position_ms"] == 2_500

        await main.admin_stop_media("admin")
        assert shared["playback_state"] == "stopped"
        assert shared["position_ms"] == 0

        state["wheel"]["spin_id"] = 8
        with pytest.raises(main.HTTPException) as error:
            await main.get_media(media_id)
        assert error.value.status_code == 404
        assert media_id not in main.media_tokens

    asyncio.run(run_flow())


def test_image_resolves_by_ref_and_preserves_share_behavior(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"kind": "normal", "sector": 2}
    state["wheel"]["spin_id"] = 3
    pack = parse_question_pack(SAMPLE_PACK)

    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "loaded_pack", pack)
    monkeypatch.setattr(main, "media_tokens", {})
    monkeypatch.setattr(main, "players_list", [])

    descriptor = next(iter(main._get_current_media_catalog().values()))

    async def run_flow():
        resolved = await main.admin_resolve_media(
            "admin",
            {"media_ref": descriptor.media_ref},
        )
        assert resolved["type"] == "image"

        await main.admin_share_media("admin", {"media_id": resolved["media_id"]})

    asyncio.run(run_flow())

    assert state["presentation"]["shared_media"]["type"] == "image"
    assert state["presentation"]["shared_media"]["media_ref"] == descriptor.media_ref


def test_live_ops_handlers_apply_authoritative_state_and_reject_invalid_input(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "players_list", [])

    async def run_flow():
        score_response = await main.admin_set_score(
            "admin",
            {"znatoki": 4, "tv": 2},
        )
        assert score_response == {"ok": True}

        sector_response = await main.admin_set_sector_used(
            "admin",
            {"sector": 3, "used": True},
        )
        assert sector_response == {"ok": True}

        invalid_response = await main.admin_set_score(
            "admin",
            {"znatoki": 7, "tv": 0},
        )
        assert invalid_response["ok"] is False
        assert invalid_response["error"] == "invalid_score"

    asyncio.run(run_flow())

    assert state["game"]["score"] == {"znatoki": 4, "tv": 2}
    assert state["game"]["used_questions"] == [3]
    assert sum(event == "state_update" for event, _, _ in fake_sio.events) == 2
    assert any(event == "admin_notification" for event, _, _ in fake_sio.events)
    assert any("Live Ops: счёт" in entry for entry in state["logs"])


def test_live_ops_open_round_force_phase_timer_and_clear_question(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    pack = parse_question_pack(SAMPLE_PACK)
    state["pack"]["question_types"] = [question.type.value for question in pack.questions]
    state["presentation"]["shared_media"] = {
        "type": "image",
        "media_id": "old-media",
        "media_ref": "old-ref",
        "section": "question",
        "name": "old.jpg",
        "playback_state": "stopped",
        "position_ms": 0,
        "started_at_ms": None,
    }
    now = [100.0]

    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "loaded_pack", pack)
    monkeypatch.setattr(main, "media_tokens", {"old-media": {"expires_at": 999.0}})
    monkeypatch.setattr(
        main,
        "players_list",
        [{"sid": "admin", "role": "admin", "online": True}],
    )
    monkeypatch.setattr(main.time, "time", lambda: now[0])

    async def run_flow():
        opened = await main.admin_open_round("admin", {"sector": 3})
        assert opened == {"ok": True}
        assert state["game"]["phase"] == PHASE_QUESTION_READING
        assert state["game"]["round"] == {"kind": "normal", "sector": 3}
        assert main.media_tokens == {}

        discussion = await main.admin_force_phase(
            "admin",
            {"phase": PHASE_DISCUSSION},
        )
        assert discussion == {"ok": True}
        assert state["timer"]["discussion_deadline_ms"] == 160_000

        timer = await main.admin_set_timer("admin", {"seconds": 20})
        assert timer == {"ok": True}
        assert state["timer"]["discussion_deadline_ms"] == 120_000

        pre_round = await main.admin_force_phase(
            "admin",
            {"phase": PHASE_PRE_ROUND},
        )
        assert pre_round == {"ok": True}

    asyncio.run(run_flow())

    question_events = [
        data for event, data, _kwargs in fake_sio.events if event == "admin_question"
    ]
    assert question_events[0]["sector"] == 3
    assert question_events[-1] is None
    assert any(event == "stop_sound" for event, _, _ in fake_sio.events)
    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["round"] is None


def test_live_ops_cancel_spin_prevents_sleeping_handler_completion(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal"] * 13,
    )
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "players_list", [])
    monkeypatch.setattr(main, "media_tokens", {"old": {"expires_at": 999.0}})
    monkeypatch.setattr(main, "calculate_spin_result", lambda *_args: (10.0, 2))

    async def cancel_instead_of_wait(_duration):
        response = await main.admin_cancel_spin("admin")
        assert response == {"ok": True}

    monkeypatch.setattr(main.asyncio, "sleep", cancel_instead_of_wait)

    asyncio.run(main.admin_spin("admin"))

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["game"]["used_questions"] == []
    assert state["wheel"]["is_spinning"] is False
    assert main.media_tokens == {}
    assert any(event == "stop_sound" for event, _, _ in fake_sio.events)


def test_live_ops_handlers_require_admin(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _deny_admin)
    monkeypatch.setattr(main, "app_state", state)

    response = asyncio.run(
        main.admin_set_score("player", {"znatoki": 1, "tv": 0})
    )

    assert response == {"ok": False, "error": "not_admin"}
    assert state["game"]["score"] == {"znatoki": 0, "tv": 0}
    assert fake_sio.events == []


def test_sound_fade_stops_shared_audio_and_publishes_stopped_mode(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["presentation"]["shared_media"] = {
        "type": "audio",
        "media_id": "audio-token",
        "media_ref": "audio-ref",
        "section": "question",
        "name": "melody.mp3",
        "playback_state": "playing",
        "position_ms": 0,
        "started_at_ms": 1_000,
    }
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main.time, "time", lambda: 1.0)

    async def finish_immediately(_duration):
        return None

    monkeypatch.setattr(main.asyncio, "sleep", finish_immediately)

    response = asyncio.run(main.admin_fade_sounds("admin"))

    assert response == {"ok": True, "completed": True}
    assert state["presentation"]["shared_media"]["playback_state"] == "stopped"
    assert state["presentation"]["shared_media"]["position_ms"] == 0
    assert main.global_settings["sound_control"]["mode"] == "stopped"
    settings = [
        data for event, data, _kwargs in fake_sio.events if event == "settings_update"
    ]
    assert [payload["sound_control"]["mode"] for payload in settings] == [
        "fading",
        "stopped",
    ]
    assert sum(event == "stop_sound" for event, _, _ in fake_sio.events) == 1
    assert any("Затухание звука" in entry for entry in state["logs"])


def test_later_effect_supersedes_sleeping_fade_completion(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)

    async def play_effect_instead_of_wait(_duration):
        await main.admin_sound("admin", {"sound": "gong1"})

    monkeypatch.setattr(main.asyncio, "sleep", play_effect_instead_of_wait)

    response = asyncio.run(main.admin_fade_sounds("admin"))

    assert response == {"ok": True, "completed": False}
    assert main.global_settings["sound_control"]["mode"] == "normal"
    assert any(event == "play_sound" for event, _, _ in fake_sio.events)
    assert not any(event == "stop_sound" for event, _, _ in fake_sio.events)


def test_explicit_media_stop_supersedes_fade_when_media_is_already_stopped(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["presentation"]["shared_media"] = {
        "type": "audio",
        "media_id": "audio-token",
        "media_ref": "audio-ref",
        "section": "question",
        "name": "melody.mp3",
        "playback_state": "stopped",
        "position_ms": 0,
        "started_at_ms": None,
    }
    generation = begin_fade(main.global_settings["sound_control"], now_ms=1_000)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(
        main,
        "_get_current_shared_media_token_info",
        lambda: {"name": "melody.mp3"},
    )

    asyncio.run(main.admin_stop_media("admin"))

    assert main.global_settings["sound_control"]["mode"] == "normal"
    assert main.complete_fade(
        main.global_settings["sound_control"],
        generation=generation,
    ) is False
    settings = [
        data for event, data, _kwargs in fake_sio.events if event == "settings_update"
    ]
    assert settings[-1]["sound_control"]["mode"] == "normal"


def test_later_silence_supersedes_fade_without_duplicate_stop(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)

    async def silence_instead_of_wait(_duration):
        await main.admin_stop_sounds("admin")

    monkeypatch.setattr(main.asyncio, "sleep", silence_instead_of_wait)

    response = asyncio.run(main.admin_fade_sounds("admin"))

    assert response == {"ok": True, "completed": False}
    assert main.global_settings["sound_control"]["mode"] == "stopped"
    assert sum(event == "stop_sound" for event, _, _ in fake_sio.events) == 1


def test_later_spin_supersedes_fade_and_keeps_wheel_sound_enabled(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(
        phase=PHASE_PRE_ROUND,
        question_types=["normal"] * 13,
    )
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)

    async def start_spin_instead_of_wait(_duration):
        effects = main.transition_start_spin(
            state,
            raw_angle=20.0,
            raw_sector=2,
            duration=5.0,
        )
        await main._apply_transition_effects(effects)

    monkeypatch.setattr(main.asyncio, "sleep", start_spin_instead_of_wait)

    response = asyncio.run(main.admin_fade_sounds("admin"))

    assert response == {"ok": True, "completed": False}
    assert state["wheel"]["is_spinning"] is True
    assert main.global_settings["sound_control"]["mode"] == "normal"
    assert not any(event == "stop_sound" for event, _, _ in fake_sio.events)


def test_connect_receives_current_fade_snapshot_before_game_state(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_PRE_ROUND)
    begin_fade(main.global_settings["sound_control"], now_ms=1_000)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main.time, "time", lambda: 2.5)

    asyncio.run(main.connect("player", {}))

    assert [event for event, _, _ in fake_sio.events[:3]] == [
        "settings_update",
        "state_update",
        "role_update",
    ]
    sound_control = fake_sio.events[0][1]["sound_control"]
    assert sound_control["mode"] == "fading"
    assert sound_control["server_now_ms"] == 2_500


def test_sound_fade_requires_admin(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _deny_admin)

    response = asyncio.run(main.admin_fade_sounds("player"))

    assert response == {"ok": False, "error": "not_admin"}
    assert main.global_settings["sound_control"] == create_sound_control_state()
    assert fake_sio.events == []
