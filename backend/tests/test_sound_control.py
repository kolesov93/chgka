import pytest

from sound_control import (
    FADE_DURATION_MS,
    begin_fade,
    complete_fade,
    create_sound_control_state,
    public_sound_control,
    sound_level,
    supersede_fade,
)


def test_fade_progresses_from_full_volume_to_zero():
    state = create_sound_control_state()

    generation = begin_fade(state, now_ms=1_000)

    assert generation == 1
    assert sound_level(state, now_ms=1_000) == 1.0
    assert sound_level(state, now_ms=2_500) == pytest.approx(0.001**0.5)
    assert sound_level(state, now_ms=3_500) == pytest.approx(0.001 ** (5 / 6))
    assert sound_level(state, now_ms=4_000) == 0.0


def test_repeated_fade_continues_from_current_level_without_jump():
    state = create_sound_control_state()
    begin_fade(state, now_ms=1_000)

    generation = begin_fade(state, now_ms=2_500)

    assert generation == 2
    assert state["fade_from"] == pytest.approx(0.001**0.5)
    assert sound_level(state, now_ms=2_500) == pytest.approx(0.001**0.5)
    assert sound_level(state, now_ms=4_000) == pytest.approx(0.001)
    assert sound_level(state, now_ms=5_500) == 0.0


def test_later_sound_command_invalidates_old_completion():
    state = create_sound_control_state()
    generation = begin_fade(state, now_ms=1_000)

    supersede_fade(state, mode="normal")

    assert complete_fade(state, generation=generation) is False
    assert state["mode"] == "normal"
    assert sound_level(state, now_ms=10_000) == 1.0


def test_completion_and_silence_remain_stopped_for_reconnect():
    state = create_sound_control_state()
    generation = begin_fade(state, now_ms=1_000)

    assert complete_fade(state, generation=generation) is True
    assert sound_level(state, now_ms=10_000) == 0.0

    supersede_fade(state, mode="normal")
    assert sound_level(state, now_ms=10_000) == 1.0

    supersede_fade(state, mode="stopped")
    snapshot = public_sound_control(state, now_ms=12_345)
    assert snapshot["mode"] == "stopped"
    assert snapshot["server_now_ms"] == 12_345


def test_fade_rejects_non_positive_duration():
    state = create_sound_control_state()

    with pytest.raises(ValueError):
        begin_fade(state, now_ms=1_000, duration_ms=0)

    assert state == create_sound_control_state()
    assert FADE_DURATION_MS == 3_000
