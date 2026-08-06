import asyncio
from dataclasses import replace
import shutil
from pathlib import Path

import pytest

import main
from auth import AdminTokenStore
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


def _authorized_admin(monkeypatch, fake_sio, *, sid="admin"):
    store = AdminTokenStore(
        60,
        token_factory=lambda: "valid-admin-token",
    )
    token = store.issue()
    monkeypatch.setattr(main, "admin_tokens", store)
    fake_sio.sessions[sid] = {
        "role": "admin",
        "admin_token": token,
    }
    return {
        "sid": sid,
        "name": main.ADMIN_NAME,
        "role": "admin",
        "token": token,
        "online": True,
    }


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
        assert not any(
            event == "play_sound" and data == {"sound": "intro"}
            for event, data, _kwargs in fake_sio.events
        )
        await asyncio.gather(
            main.admin_start_intro_music("admin"),
            main.admin_start_intro_music("admin"),
        )
        await asyncio.gather(
            main.admin_advance_intro("admin", {"expected_slide": 0}),
            main.admin_advance_intro("admin", {"expected_slide": 0}),
        )
        state["presentation"]["intro"]["slide_index"] = 13
        await main.admin_advance_intro("admin", {"expected_slide": 13})

    asyncio.run(run())

    assert state["game"]["phase"] == PHASE_PRE_ROUND
    assert state["presentation"]["intro"] is None
    assert sum(
        event == "play_sound" and data == {"sound": "intro"}
        for event, data, _kwargs in fake_sio.events
    ) == 1
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


def test_intro_author_photo_is_pack_backed_and_current_slide_only(tmp_path, monkeypatch):
    pack_path = tmp_path / "pack"
    shutil.copytree(SAMPLE_PACK, pack_path)
    photo_path = pack_path / "04" / "01" / "author.jpg"
    pack = parse_question_pack(pack_path)
    state = create_initial_app_state(phase=PHASE_INTRO)
    state["presentation"]["intro"] = {
        "slide_index": 4,
        "started_at_ms": None,
        "duration_ms": 87_757,
    }
    monkeypatch.setattr(main, "loaded_pack", pack)
    monkeypatch.setattr(main, "app_state", state)

    response = asyncio.run(main.get_intro_author_photo(4, 1))

    assert Path(response.path) == photo_path.resolve()
    assert response.headers["cache-control"] == "no-store"

    with pytest.raises(main.HTTPException) as error:
        asyncio.run(main.get_intro_author_photo(4, 2))
    assert error.value.status_code == 404

    with pytest.raises(main.HTTPException) as error:
        asyncio.run(main.get_intro_author_photo(4, 4))
    assert error.value.status_code == 404

    state["presentation"]["intro"]["slide_index"] = 2
    with pytest.raises(main.HTTPException) as error:
        asyncio.run(main.get_intro_author_photo(4, 1))
    assert error.value.status_code == 404

    with pytest.raises(main.HTTPException) as error:
        asyncio.run(main.get_intro_author_photo(13, 1))
    assert error.value.status_code == 404


def test_pack_info_includes_intro_speech_for_admin_only(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    fake_sio.sessions = {"player": {"role": "player"}}
    monkeypatch.setattr(main, "sio", fake_sio)
    _authorized_admin(monkeypatch, fake_sio)
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


def test_startup_builds_public_intro_authors_from_pack(monkeypatch):
    state = create_initial_app_state()
    monkeypatch.setenv("QUESTIONS_PACK_PATH", str(SAMPLE_PACK))
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "loaded_pack", None)
    monkeypatch.setattr(main, "pack_admin_info", {})

    main._load_question_pack_on_startup()

    authors = state["pack"]["intro_authors"]
    assert len(authors) == 12
    assert authors[0] == [
        {
            "sector": 1,
            "slot": 1,
            "name": "Михаил Савченко",
            "city": "Москва",
            "has_photo": True,
        }
    ]
    assert authors[3] == [
        {
            "sector": 4,
            "slot": slot,
            "name": "Ольга Петрова",
            "city": None,
            "has_photo": slot == 1,
        }
        for slot in range(1, 4)
    ]
    assert authors[11][0]["name"] == "Алексей Громов"
    assert all(card["sector"] != 13 for group in authors for card in group)


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
        [_authorized_admin(monkeypatch, fake_sio)],
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


def test_admin_login_replaces_previous_token_and_session(monkeypatch):
    now = [100.0]
    tokens = iter(("old-admin-token", "new-admin-token"))
    store = AdminTokenStore(
        60,
        clock=lambda: now[0],
        token_factory=lambda: next(tokens),
    )
    old_token = store.issue()
    fake_sio = FakeSio(yield_on_emit=False)
    fake_sio.sessions["old-admin"] = {
        "role": "admin",
        "admin_token": old_token,
    }
    old_record = {
        "sid": "old-admin",
        "name": main.ADMIN_NAME,
        "role": "admin",
        "token": old_token,
        "online": True,
    }
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "admin_tokens", store)
    monkeypatch.setattr(main, "players_list", [old_record])
    monkeypatch.setattr(
        main,
        "APP_CONFIG",
        replace(main.APP_CONFIG, admin_password="correct-password"),
    )

    asyncio.run(
        main.authenticate_admin("new-admin", {"password": "correct-password"})
    )

    assert store.validate(old_token) is False
    assert store.validate("new-admin-token") is True
    assert fake_sio.sessions["old-admin"] == {"role": "player"}
    assert fake_sio.sessions["new-admin"] == {
        "role": "admin",
        "admin_token": "new-admin-token",
    }
    assert main.players_list == [
        {
            "sid": "new-admin",
            "name": main.ADMIN_NAME,
            "role": "admin",
            "token": "new-admin-token",
            "online": True,
        }
    ]
    success = next(
        data for event, data, _kwargs in fake_sio.events if event == "auth_success"
    )
    assert success == {
        "token": "new-admin-token",
        "expires_at_ms": 160_000,
    }
    assert any(
        event == "auth_expired" and kwargs == {"to": "old-admin"}
        for event, _data, kwargs in fake_sio.events
    )


def test_admin_password_comparison_supports_unicode(monkeypatch):
    monkeypatch.setattr(
        main,
        "APP_CONFIG",
        replace(main.APP_CONFIG, admin_password="надёжный-пароль"),
    )

    assert main._admin_password_matches("надёжный-пароль") is True
    assert main._admin_password_matches("другой-пароль") is False
    assert main._admin_password_matches(None) is False


def test_expired_admin_token_denies_action_and_downgrades_socket(monkeypatch):
    now = [100.0]
    store = AdminTokenStore(
        60,
        clock=lambda: now[0],
        token_factory=lambda: "admin-token",
    )
    token = store.issue()
    fake_sio = FakeSio(yield_on_emit=False)
    fake_sio.sessions["admin"] = {
        "role": "admin",
        "admin_token": token,
    }
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "admin_tokens", store)
    monkeypatch.setattr(
        main,
        "players_list",
        [
            {
                "sid": "admin",
                "name": main.ADMIN_NAME,
                "role": "admin",
                "token": token,
                "online": True,
            }
        ],
    )
    now[0] = 160.0

    allowed = asyncio.run(main.require_admin("admin"))

    assert allowed is False
    assert fake_sio.sessions["admin"] == {"role": "player"}
    assert main.players_list == []
    assert any(event == "auth_expired" for event, _data, _kwargs in fake_sio.events)


def test_restore_rejects_revoked_admin_token(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    store = AdminTokenStore(60)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "admin_tokens", store)
    monkeypatch.setattr(main, "players_list", [])

    asyncio.run(main.restore_session("browser", {"token": "revoked-token"}))

    assert fake_sio.sessions["browser"] == {"role": "player"}
    assert any(event == "auth_expired" for event, _data, _kwargs in fake_sio.events)


def test_restore_reports_the_original_admin_expiry(monkeypatch):
    now = [100.0]
    store = AdminTokenStore(
        60,
        clock=lambda: now[0],
        token_factory=lambda: "admin-token",
    )
    token = store.issue()
    now[0] = 120.0
    fake_sio = FakeSio(yield_on_emit=False)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "admin_tokens", store)
    monkeypatch.setattr(main, "players_list", [])

    asyncio.run(main.restore_session("browser", {"token": token}))

    restored = next(
        data for event, data, _kwargs in fake_sio.events if event == "auth_restored"
    )
    assert restored == {"expires_at_ms": 160_000}
    assert fake_sio.sessions["browser"] == {
        "role": "admin",
        "admin_token": token,
    }


def test_admin_logout_revokes_token(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    admin = _authorized_admin(monkeypatch, fake_sio)
    store = main.admin_tokens
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "players_list", [admin])

    asyncio.run(main.leave_game("admin"))

    assert store.validate(admin["token"]) is False
    assert fake_sio.sessions["admin"] == {"role": "player"}
    assert main.players_list == []


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
        [_authorized_admin(monkeypatch, fake_sio)],
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
        [_authorized_admin(monkeypatch, fake_sio)],
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


def test_live_ops_reset_to_intro_stops_audio_and_waits_for_manual_music(monkeypatch):
    fake_sio = FakeSio(yield_on_emit=False)
    state = create_initial_app_state(phase=PHASE_POST_ROUND)
    state["game"]["score"] = {"znatoki": 5, "tv": 4}
    state["game"]["used_questions"] = [1, 3, 5]
    state["game"]["round"] = {"kind": "normal", "sector": 5}
    media_tokens = {"old": {"expires_at": 999.0}}
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "require_admin", _allow_admin)
    monkeypatch.setattr(main, "app_state", state)
    monkeypatch.setattr(main, "media_tokens", media_tokens)
    monkeypatch.setattr(main, "_now_ms", lambda: 50_000)
    monkeypatch.setattr(
        main,
        "players_list",
        [_authorized_admin(monkeypatch, fake_sio)],
    )

    response = asyncio.run(main.admin_reset_to_intro("admin"))

    assert response == {"ok": True}
    assert state["game"]["phase"] == PHASE_INTRO
    assert state["game"]["score"] == {"znatoki": 0, "tv": 0}
    assert state["game"]["used_questions"] == []
    assert state["presentation"]["intro"]["slide_index"] == 0
    assert state["presentation"]["intro"]["started_at_ms"] is None
    assert media_tokens == {}
    event_names = [event for event, _data, _kwargs in fake_sio.events]
    stop_index = event_names.index("stop_sound")
    state_index = next(
        index
        for index, (event, data, _kwargs) in enumerate(fake_sio.events)
        if event == "state_update" and data["phase"] == PHASE_INTRO
    )
    assert stop_index < state_index
    assert not any(
        event == "play_sound" and data == {"sound": "intro"}
        for event, data, _kwargs in fake_sio.events
    )
    assert any(
        event == "admin_question" and data is None
        for event, data, _kwargs in fake_sio.events
    )


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
