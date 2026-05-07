"""Typed game-state contract and serialization helpers.

The game state is the shared server-side snapshot that is broadcast to clients
through `state_update`. It includes the public game situation, client display
context, and a small amount of round workflow state needed by the current UI.
"""

from copy import deepcopy
from typing import Literal, Optional, TypedDict

GamePhase = Literal[
    "LOGIN",
    "PRE_ROUND",
    "QUESTION_READING",
    "DISCUSSION",
    "TEAM_ANSWER",
    "POST_ROUND",
]

# Phase constants are part of the state contract: backend guards and frontend
# rendering both depend on these exact string values. The `Literal` alias above
# must list raw string literals; the constants are typed against that alias.
PHASE_LOGIN: GamePhase = "LOGIN"
PHASE_PRE_ROUND: GamePhase = "PRE_ROUND"
PHASE_QUESTION_READING: GamePhase = "QUESTION_READING"
PHASE_DISCUSSION: GamePhase = "DISCUSSION"
PHASE_TEAM_ANSWER: GamePhase = "TEAM_ANSWER"
PHASE_POST_ROUND: GamePhase = "POST_ROUND"

QuestionKind = Literal["normal", "blitz", "superblitz"]
QuestionTypeValue = QuestionKind
SharedMediaType = Literal["image", "audio", "video"]


class ScoreState(TypedDict):
    """Public score shown to all clients."""

    znatoki: int
    tv: int


class RoundState(TypedDict, total=False):
    """Current round context.

    For a normal round, `kind` and `sector` are enough. Blitz/superblitz rounds
    also carry `part_index`. `advance_next_part` is a temporary admin workflow
    flag used after a correct intermediate blitz answer.
    """

    kind: QuestionKind
    sector: int
    part_index: int
    advance_next_part: bool


class SharedMediaState(TypedDict):
    """Media currently shown to all clients instead of the game table."""

    type: SharedMediaType
    media_id: str


class GameState(TypedDict):
    """State snapshot emitted through `state_update`.

    Field groups:
    - Game progress: `phase`, `score`, `used_questions`, `round`.
    - Table/spin display: `current_sector`, `target_angle`, `playing_sector`,
      `spin_duration`, `is_spinning`, `question_types`.
    - Admin/live context: `logs`, `discussion_deadline_ms`.
    - Shared presentation: `shared_media`.
    """

    # Current game phase. Drives backend action guards and frontend screens.
    phase: GamePhase

    # Public score shown to clients and used by backend game guards.
    score: ScoreState

    # Sector where the arrow/table should rest when there is no active spin.
    current_sector: int

    # Exact angle selected for the current spin animation, in degrees.
    # `None` means there is no active/new spin target.
    target_angle: Optional[float]

    # Sector that will actually be played after jump rules are applied.
    # It is set during spin handling and cleared by reset.
    playing_sector: Optional[int]

    # Spin animation duration in seconds. The frontend also uses it to time
    # the volchok sound fade.
    spin_duration: float

    # Sectors that have already been played and should no longer show envelopes
    # or be available for normal selection.
    used_questions: list[int]

    # True while the backend is waiting for the spin animation duration to pass.
    is_spinning: bool

    # Recent game log entries, newest first.
    logs: list[str]

    # Per-sector question kinds loaded from the pack. The frontend uses this to
    # render normal/blitz/superblitz envelope icons.
    question_types: Optional[list[QuestionTypeValue]]

    # Unix timestamp in milliseconds for the end of discussion. Only the admin
    # UI currently renders the countdown.
    discussion_deadline_ms: Optional[int]

    # Current question/round context. Does not contain question text; admin-only
    # question content is sent separately via `admin_question`.
    round: Optional[RoundState]

    # Media currently shown to all clients instead of the game table.
    shared_media: Optional[SharedMediaState]


def create_initial_game_state(
    *,
    phase: GamePhase = PHASE_LOGIN,
    question_types: Optional[list[QuestionTypeValue]] = None,
) -> GameState:
    """Create a fresh game state with no runtime round/spin/media context."""

    return {
        "phase": phase,
        "score": {"znatoki": 0, "tv": 0},
        "current_sector": 1,
        "target_angle": None,
        "playing_sector": None,
        "spin_duration": 0,
        "used_questions": [],
        "is_spinning": False,
        "logs": [],
        "question_types": list(question_types) if question_types is not None else None,
        "discussion_deadline_ms": None,
        "round": None,
        "shared_media": None,
    }


def reset_game_state(
    state: GameState,
    *,
    phase: GamePhase = PHASE_PRE_ROUND,
) -> None:
    """Reset an existing state dict in place.

    The in-place update preserves references held by `main.py`, while resetting
    runtime fields to the same shape as `create_initial_game_state()`. Loaded
    `question_types` are preserved because they come from the pack parsed at
    startup and are still needed after an admin reset.
    """

    question_types = state.get("question_types")
    state.clear()
    state.update(
        create_initial_game_state(
            phase=phase,
            question_types=question_types,
        )
    )


def public_game_state(state: GameState) -> GameState:
    """
    Return the current state_update payload.

    This is intentionally wire-compatible with the previous raw game_state dict.
    Keeping it as a helper makes the public boundary explicit and gives us a
    single place to narrow the payload later. A deep copy prevents accidental
    mutation of server state by code that treats the returned payload as a
    disposable message object.
    """
    return deepcopy(state)
