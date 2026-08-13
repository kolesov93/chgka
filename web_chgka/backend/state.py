"""Typed server-state contract and serialization helpers.

`AppState` is the internal server-side state. It is split into domain sections
so game rules, wheel animation, timers, presentation, pack metadata, and logs do
not all live in one flat bucket.

`public_game_state()` serializes that internal state to the flat `state_update`
payload expected by the current frontend.
"""

from copy import deepcopy
import time
from typing import Literal, Optional, TypedDict

GamePhase = Literal[
    "LOGIN",
    "INTRO",
    "PRE_ROUND",
    "QUESTION_READING",
    "DISCUSSION",
    "TEAM_ANSWER",
    "POST_ROUND",
    "GAME_OVER",
]

# Phase constants are part of the state contract: backend guards and frontend
# rendering both depend on these exact string values. The `Literal` alias above
# must list raw string literals; the constants are typed against that alias.
PHASE_LOGIN: GamePhase = "LOGIN"
PHASE_INTRO: GamePhase = "INTRO"
PHASE_PRE_ROUND: GamePhase = "PRE_ROUND"
PHASE_QUESTION_READING: GamePhase = "QUESTION_READING"
PHASE_DISCUSSION: GamePhase = "DISCUSSION"
PHASE_TEAM_ANSWER: GamePhase = "TEAM_ANSWER"
PHASE_POST_ROUND: GamePhase = "POST_ROUND"
PHASE_GAME_OVER: GamePhase = "GAME_OVER"

QuestionKind = Literal["normal", "blitz", "superblitz"]
QuestionTypeValue = QuestionKind
SharedMediaType = Literal["image", "audio", "video"]
MediaPlaybackState = Literal["stopped", "playing", "paused"]
TimerSegment = Literal["base", "earned", "credit"]
StrategyRequestType = Literal["early_answer", "credit", "repayment"]


class ScoreState(TypedDict):
    """Public score shown to all clients."""

    znatoki: int
    tv: int


class RespondentState(TypedDict):
    """Immutable public snapshot of the physical participant answering now."""

    participant_id: str
    group_id: str
    name: str


class StrategyRequestState(TypedDict, total=False):
    """Reconnect-safe captain request awaiting an explicit host decision."""

    type: StrategyRequestType
    participant_id: str
    group_id: str
    name: str
    requested_phase: GamePhase
    requested_at_ms: int
    timer_generation: int


class _RequiredCreditState(TypedDict):
    """Persistent one-use credit lifecycle fields."""

    used: bool
    debt: bool
    repayment_scheduled: bool
    forced: bool


class CreditState(_RequiredCreditState, total=False):
    """Credit lifecycle plus an optional reconnect-safe repayment request."""

    repayment_request: StrategyRequestState


class TeamState(TypedDict):
    """Public strategic resources owned by the experts team."""

    captain: Optional[RespondentState]
    earned_minutes: int
    credit: CreditState


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
    respondent: RespondentState
    early_answer: bool
    early_answer_actor: dict
    answer_timer_segment: TimerSegment
    extra_minutes_spent: int
    extra_part_index: int
    credit_used: bool
    credit_part_index: int
    credit_repayment: bool
    strategy_request: StrategyRequestState


class SharedMediaState(TypedDict):
    """Media currently shown to all clients instead of the game table."""

    type: SharedMediaType
    media_id: str
    media_ref: str
    section: str
    name: str
    playback_state: MediaPlaybackState
    position_ms: int
    started_at_ms: Optional[int]
    playback_generation: int
    has_next: bool


class PublicSharedMediaState(TypedDict):
    """Public shared media without admin-only identity context."""

    type: SharedMediaType
    media_id: str
    playback_state: MediaPlaybackState
    position_ms: int
    started_at_ms: Optional[int]
    server_now_ms: int
    playback_generation: int
    has_next: bool


class GameProgressState(TypedDict):
    """Actual game progress governed by game rules."""

    # Current game phase. Drives backend action guards and frontend screens.
    phase: GamePhase

    # Public score shown to clients and used by backend game guards.
    score: ScoreState

    # Sectors that have already been played and should no longer show envelopes
    # or be available for normal selection.
    used_questions: list[int]

    # Current question/round context. Does not contain question text; admin-only
    # question content is sent separately via `admin_question`.
    round: Optional[RoundState]

    # Captain, earned minutes and the distinct credit lifecycle.
    team: TeamState


class WheelState(TypedDict):
    """Wheel/table animation and sector-selection state."""

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

    # True while the backend is waiting for the spin animation duration to pass.
    is_spinning: bool

    # Monotonically increasing generation used to reject stale async spin
    # completion after reset or a later spin.
    spin_id: int


class TimerState(TypedDict):
    """Discussion timer state."""

    # Unix timestamp in milliseconds for the end of discussion. Only the admin
    # UI currently renders the countdown.
    discussion_deadline_ms: Optional[int]
    segment: Optional[TimerSegment]
    started_at_ms: Optional[int]
    generation: int


class PublicTimerState(TimerState):
    """Timer timeline plus serialization time for reconnect-aware clients."""

    server_now_ms: int


class IntroState(TypedDict):
    """Internal intro progress shared by every connected client."""

    slide_index: int
    started_at_ms: Optional[int]
    duration_ms: int


class IntroAuthorState(TypedDict):
    """Public metadata for one author card on an intro screen."""

    sector: int
    slot: int
    name: str
    city: Optional[str]
    has_photo: bool


class PublicIntroState(IntroState):
    """Intro progress plus current public authors and serialization time."""

    server_now_ms: int
    authors: list[IntroAuthorState]


class BlackboxState(TypedDict):
    """Active synchronized black-box music presentation."""

    started_at_ms: int
    playback_generation: int


class PublicBlackboxState(BlackboxState):
    """Black-box timeline serialized for reconnect-aware browser playback."""

    server_now_ms: int


class PresentationState(TypedDict):
    """Shared presentation state shown to players."""

    # Current server-authoritative intro slide and music timeline.
    intro: Optional[IntroState]

    # Media currently shown to all clients instead of the game table.
    shared_media: Optional[SharedMediaState]

    # Static black-box presentation and its monotonic stale-event guard.
    blackbox: Optional[BlackboxState]
    blackbox_generation: int


class PackUiState(TypedDict):
    """Pack metadata needed by shared UI surfaces."""

    # Per-sector question kinds loaded from the pack. The frontend uses this to
    # render normal/blitz/superblitz envelope icons.
    question_types: Optional[list[QuestionTypeValue]]

    # One author-card group per sector 1..12. Photo paths stay in QuestionPack.
    intro_authors: Optional[list[list[IntroAuthorState]]]


class PublicGameState(TypedDict):
    """Flat `state_update` payload consumed by the current frontend."""

    phase: GamePhase
    score: ScoreState
    current_sector: int
    target_angle: Optional[float]
    playing_sector: Optional[int]
    spin_duration: float
    used_questions: list[int]
    is_spinning: bool
    logs: list[str]
    question_types: Optional[list[QuestionTypeValue]]
    discussion_deadline_ms: Optional[int]
    timer: PublicTimerState
    team: TeamState
    round: Optional[RoundState]
    intro: Optional[PublicIntroState]
    shared_media: Optional[PublicSharedMediaState]
    blackbox: Optional[PublicBlackboxState]


class AppState(TypedDict):
    """Internal server state grouped by domain."""

    game: GameProgressState
    wheel: WheelState
    timer: TimerState
    presentation: PresentationState
    pack: PackUiState
    logs: list[str]


def create_initial_app_state(
    *,
    phase: GamePhase = PHASE_LOGIN,
    question_types: Optional[list[QuestionTypeValue]] = None,
    intro_authors: Optional[list[list[IntroAuthorState]]] = None,
) -> AppState:
    """Create a fresh app state with no runtime round/spin/media context."""

    return {
        "game": {
            "phase": phase,
            "score": {"znatoki": 0, "tv": 0},
            "used_questions": [],
            "round": None,
            "team": {
                "captain": None,
                "earned_minutes": 0,
                "credit": {
                    "used": False,
                    "debt": False,
                    "repayment_scheduled": False,
                    "forced": False,
                },
            },
        },
        "wheel": {
            "current_sector": 1,
            "target_angle": None,
            "playing_sector": None,
            "spin_duration": 0,
            "is_spinning": False,
            "spin_id": 0,
        },
        "timer": {
            "discussion_deadline_ms": None,
            "segment": None,
            "started_at_ms": None,
            "generation": 0,
        },
        "presentation": {
            "intro": None,
            "shared_media": None,
            "blackbox": None,
            "blackbox_generation": 0,
        },
        "pack": {
            "question_types": list(question_types) if question_types is not None else None,
            "intro_authors": deepcopy(intro_authors) if intro_authors is not None else None,
        },
        "logs": [],
    }


def reset_app_state(
    state: AppState,
    *,
    phase: GamePhase = PHASE_PRE_ROUND,
) -> None:
    """Reset an existing state dict in place.

    The in-place update preserves references held by `main.py`, while resetting
    runtime fields to the same shape as `create_initial_app_state()`. Loaded
    Pack UI metadata is preserved because it comes from the pack parsed at
    startup and is still needed after an admin reset.
    """

    question_types = state["pack"]["question_types"]
    intro_authors = state["pack"]["intro_authors"]
    next_spin_id = state["wheel"].get("spin_id", 0) + 1
    next_blackbox_generation = (
        state["presentation"].get("blackbox_generation", 0) + 1
    )
    next_timer_generation = state["timer"].get("generation", 0) + 1
    state.clear()
    state.update(
        create_initial_app_state(
            phase=phase,
            question_types=question_types,
            intro_authors=intro_authors,
        )
    )
    # Invalidate completion callbacks belonging to the pre-reset state. This
    # field is internal and intentionally absent from PublicGameState.
    state["wheel"]["spin_id"] = next_spin_id
    state["presentation"]["blackbox_generation"] = next_blackbox_generation
    state["timer"]["generation"] = next_timer_generation


def public_game_state(
    state: AppState,
    *,
    now_ms: Optional[int] = None,
) -> PublicGameState:
    """
    Return the current state_update payload.

    The current frontend expects a flat payload. Keeping that serialization here
    lets backend internals become cleaner without forcing a frontend protocol
    migration in the same step.
    """
    internal_media = state["presentation"]["shared_media"]
    timestamp_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    internal_intro = state["presentation"]["intro"]
    intro: Optional[PublicIntroState] = None
    if internal_intro is not None:
        slide_index = internal_intro["slide_index"]
        intro_authors = state["pack"]["intro_authors"] or []
        authors = (
            intro_authors[slide_index - 1]
            if 1 <= slide_index <= 12 and len(intro_authors) >= slide_index
            else []
        )
        intro = {
            **internal_intro,
            "server_now_ms": timestamp_ms,
            "authors": authors,
        }
    shared_media: Optional[PublicSharedMediaState] = None
    if internal_media is not None:
        shared_media = {
            "type": internal_media["type"],
            "media_id": internal_media["media_id"],
            "playback_state": internal_media["playback_state"],
            "position_ms": internal_media["position_ms"],
            "started_at_ms": internal_media["started_at_ms"],
            "server_now_ms": timestamp_ms,
            "playback_generation": int(internal_media.get("playback_generation", 0)),
            "has_next": bool(internal_media.get("has_next", False)),
        }
    internal_blackbox = state["presentation"].get("blackbox")
    blackbox: Optional[PublicBlackboxState] = None
    if internal_blackbox is not None:
        blackbox = {
            **internal_blackbox,
            "server_now_ms": timestamp_ms,
        }

    return deepcopy(
        {
            "phase": state["game"]["phase"],
            "score": state["game"]["score"],
            "current_sector": state["wheel"]["current_sector"],
            "target_angle": state["wheel"]["target_angle"],
            "playing_sector": state["wheel"]["playing_sector"],
            "spin_duration": state["wheel"]["spin_duration"],
            "used_questions": state["game"]["used_questions"],
            "is_spinning": state["wheel"]["is_spinning"],
            "logs": state["logs"],
            "question_types": state["pack"]["question_types"],
            "discussion_deadline_ms": state["timer"]["discussion_deadline_ms"],
            "timer": {
                "discussion_deadline_ms": state["timer"]["discussion_deadline_ms"],
                "segment": state["timer"].get("segment"),
                "started_at_ms": state["timer"].get("started_at_ms"),
                "generation": int(state["timer"].get("generation", 0)),
                "server_now_ms": timestamp_ms,
            },
            "team": state["game"]["team"],
            "round": state["game"]["round"],
            "intro": intro,
            "shared_media": shared_media,
            "blackbox": blackbox,
        }
    )
