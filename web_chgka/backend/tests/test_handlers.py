import asyncio
from pathlib import Path

import pytest

import main
from questions import parse_question_pack
from state import (
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
