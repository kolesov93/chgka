import asyncio

import main
from state import PHASE_PRE_ROUND, PHASE_TEAM_ANSWER, create_initial_app_state


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
