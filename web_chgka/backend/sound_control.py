"""Server-authoritative lifecycle for synchronized game sound fading."""

from __future__ import annotations

from copy import deepcopy
from typing import Literal, Optional, TypedDict


FADE_DURATION_MS = 3_000
# A 60 dB reduction is effectively silent before the final authoritative stop.
# Interpolating linearly in decibels means applying this exponential gain curve.
FADE_MIN_GAIN = 0.001

SoundMode = Literal["normal", "fading", "stopped"]


class SoundControlState(TypedDict):
    generation: int
    mode: SoundMode
    fade_started_at_ms: Optional[int]
    fade_duration_ms: Optional[int]
    fade_from: float


class PublicSoundControlState(SoundControlState):
    server_now_ms: int


def create_sound_control_state() -> SoundControlState:
    return {
        "generation": 0,
        "mode": "normal",
        "fade_started_at_ms": None,
        "fade_duration_ms": None,
        "fade_from": 1.0,
    }


def sound_level(state: SoundControlState, *, now_ms: int) -> float:
    """Return the current shared sound multiplier in the inclusive 0..1 range."""
    if state["mode"] == "stopped":
        return 0.0
    if state["mode"] != "fading":
        return 1.0

    started_at_ms = state["fade_started_at_ms"]
    duration_ms = state["fade_duration_ms"]
    if started_at_ms is None or duration_ms is None or duration_ms <= 0:
        return 0.0

    progress = max(0.0, min(1.0, (now_ms - started_at_ms) / duration_ms))
    if progress >= 1.0:
        return 0.0
    fade_curve = FADE_MIN_GAIN**progress
    return max(0.0, min(1.0, state["fade_from"] * fade_curve))


def begin_fade(
    state: SoundControlState,
    *,
    now_ms: int,
    duration_ms: int = FADE_DURATION_MS,
) -> int:
    """Start or smoothly restart a fade and return its captured generation."""
    if duration_ms <= 0:
        raise ValueError("Fade duration must be positive")

    fade_from = sound_level(state, now_ms=now_ms)
    state["generation"] += 1
    state["mode"] = "fading"
    state["fade_started_at_ms"] = now_ms
    state["fade_duration_ms"] = duration_ms
    state["fade_from"] = fade_from
    return state["generation"]


def supersede_fade(state: SoundControlState, *, mode: SoundMode) -> int:
    """Invalidate pending completion and select the current global sound mode."""
    if mode not in ("normal", "stopped"):
        raise ValueError(f"Unsupported superseding mode: {mode}")

    state["generation"] += 1
    state["mode"] = mode
    state["fade_started_at_ms"] = None
    state["fade_duration_ms"] = None
    state["fade_from"] = 1.0 if mode == "normal" else 0.0
    return state["generation"]


def complete_fade(state: SoundControlState, *, generation: int) -> bool:
    """Commit a fade stop only if no later sound command superseded it."""
    if state["generation"] != generation or state["mode"] != "fading":
        return False

    state["mode"] = "stopped"
    state["fade_started_at_ms"] = None
    state["fade_duration_ms"] = None
    state["fade_from"] = 0.0
    return True


def public_sound_control(
    state: SoundControlState,
    *,
    now_ms: int,
) -> PublicSoundControlState:
    payload = deepcopy(state)
    payload["server_now_ms"] = now_ms
    return payload
