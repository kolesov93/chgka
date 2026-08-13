"""Structured events shared by synchronous transitions and the durable journal."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GameEvent:
    event_type: str
    message: str
    payload: dict[str, object] = field(default_factory=dict)


def game_event(event_type: str, message: str, **payload: object) -> GameEvent:
    return GameEvent(event_type=event_type, message=message, payload=payload)
