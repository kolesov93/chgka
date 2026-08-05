"""Synchronous, testable game-state transitions.

Socket.IO handlers authorize requests and deliver the effects returned here.
All state mutation happens before the handler performs network awaits, keeping
phase checks and mutations atomic within the asyncio event loop.
"""

from dataclasses import dataclass
from typing import Optional

from state import (
    AppState,
    GamePhase,
    PHASE_DISCUSSION,
    PHASE_LOGIN,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    reset_app_state,
)


SECTORS_COUNT = 13
BLITZ_PARTS = 3


class TransitionError(ValueError):
    """A requested transition is invalid for the current state."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TransitionEffects:
    """Side effects that the async transport layer must deliver."""

    logs: tuple[str, ...] = ()
    sounds: tuple[str, ...] = ()
    clear_media_tokens: bool = False
    refresh_admin_question: bool = False
    clear_admin_question: bool = False
    stop_sounds: bool = False
    start_sound_output: bool = False
    spin_id: Optional[int] = None
    playing_sector: Optional[int] = None


def _require_phase(state: AppState, expected: GamePhase) -> None:
    phase = state["game"]["phase"]
    if phase != expected:
        raise TransitionError(
            "bad_phase",
            f"Действие недоступно в фазе {phase}; ожидается {expected}",
        )


def transition_start_game(state: AppState) -> TransitionEffects:
    _require_phase(state, PHASE_LOGIN)
    state["game"]["phase"] = PHASE_PRE_ROUND
    return TransitionEffects(logs=("Игра началась!",))


def validate_spin_start(state: AppState) -> None:
    _require_phase(state, PHASE_PRE_ROUND)
    if state["wheel"]["is_spinning"]:
        raise TransitionError("spinning", "Волчок уже вращается")
    if state["game"]["score"]["znatoki"] >= 6 or state["game"]["score"]["tv"] >= 6:
        raise TransitionError("game_finished", "Одна из команд уже набрала 6 очков")
    if len(set(state["game"]["used_questions"])) >= SECTORS_COUNT:
        raise TransitionError("no_questions", "Все секторы уже сыграны")


def _next_available_sector(raw_sector: int, used_questions: list[int]) -> int:
    if not isinstance(raw_sector, int) or isinstance(raw_sector, bool) or not 1 <= raw_sector <= SECTORS_COUNT:
        raise TransitionError("invalid_sector", f"Некорректный сектор: {raw_sector}")

    used = set(used_questions)
    for offset in range(SECTORS_COUNT):
        candidate = ((raw_sector - 1 + offset) % SECTORS_COUNT) + 1
        if candidate not in used:
            return candidate
    raise TransitionError("no_questions", "Все секторы уже сыграны")


def transition_start_spin(
    state: AppState,
    *,
    raw_angle: float,
    raw_sector: int,
    duration: float,
    forced: bool = False,
) -> TransitionEffects:
    validate_spin_start(state)
    if duration <= 0:
        raise TransitionError("invalid_duration", "Длительность вращения должна быть положительной")

    playing_sector = _next_available_sector(raw_sector, state["game"]["used_questions"])
    spin_id = state["wheel"].get("spin_id", 0) + 1

    state["presentation"]["shared_media"] = None
    state["wheel"]["target_angle"] = raw_angle
    state["wheel"]["playing_sector"] = playing_sector
    state["wheel"]["spin_duration"] = duration
    state["wheel"]["is_spinning"] = True
    state["wheel"]["spin_id"] = spin_id

    log = f"Вращение! Угол: {raw_angle:.1f}° (Сектор {raw_sector})"
    if forced:
        log += " [FORCED]"
    log += f" -> Играет: {playing_sector}"
    logs = [log]
    if playing_sector == SECTORS_COUNT:
        logs.append("Внимание! 13-й сектор!")

    return TransitionEffects(
        logs=tuple(logs),
        clear_media_tokens=True,
        start_sound_output=True,
        spin_id=spin_id,
        playing_sector=playing_sector,
    )


def transition_complete_spin(state: AppState, *, spin_id: int) -> TransitionEffects:
    wheel = state["wheel"]
    if not wheel["is_spinning"] or wheel.get("spin_id") != spin_id:
        raise TransitionError("stale_spin", "Результат вращения устарел")

    _require_phase(state, PHASE_PRE_ROUND)
    playing_sector = wheel["playing_sector"]
    if playing_sector is None:
        raise TransitionError("invalid_spin", "У вращения нет выбранного сектора")

    wheel["is_spinning"] = False
    wheel["current_sector"] = playing_sector
    wheel["spin_duration"] = 0
    if playing_sector not in state["game"]["used_questions"]:
        state["game"]["used_questions"].append(playing_sector)

    question_types = state["pack"]["question_types"] or []
    question_type = (
        question_types[playing_sector - 1]
        if len(question_types) >= playing_sector
        else "normal"
    )
    if question_type in ("blitz", "superblitz"):
        state["game"]["round"] = {
            "kind": question_type,
            "sector": playing_sector,
            "part_index": 0,
        }
    else:
        state["game"]["round"] = {"kind": "normal", "sector": playing_sector}

    state["timer"]["discussion_deadline_ms"] = None
    state["game"]["phase"] = PHASE_QUESTION_READING
    sounds = ("sector13",) if playing_sector == SECTORS_COUNT else ()
    return TransitionEffects(
        logs=("Фаза: зачитывание вопроса",),
        sounds=sounds,
        refresh_admin_question=True,
        spin_id=spin_id,
        playing_sector=playing_sector,
    )


def transition_start_discussion(state: AppState, *, deadline_ms: int) -> TransitionEffects:
    _require_phase(state, PHASE_QUESTION_READING)
    state["game"]["phase"] = PHASE_DISCUSSION
    state["timer"]["discussion_deadline_ms"] = deadline_ms
    return TransitionEffects(logs=("Фаза: обсуждение",))


def transition_team_answer(state: AppState) -> TransitionEffects:
    _require_phase(state, PHASE_DISCUSSION)
    state["timer"]["discussion_deadline_ms"] = None
    state["game"]["phase"] = PHASE_TEAM_ANSWER
    return TransitionEffects(
        logs=("Фаза: ответ команды",),
        sounds=("sig1",),
    )


def transition_ten_seconds(state: AppState, *, deadline_ms: int) -> TransitionEffects:
    _require_phase(state, PHASE_DISCUSSION)
    state["timer"]["discussion_deadline_ms"] = deadline_ms
    return TransitionEffects(
        logs=("Сигнал: 10 секунд (таймер сброшен на 10)",),
        sounds=("sig2",),
    )


def transition_score(
    state: AppState,
    *,
    winner: str,
    correct_sound: str,
    incorrect_sound: str,
) -> TransitionEffects:
    _require_phase(state, PHASE_TEAM_ANSWER)
    if winner not in ("znatoki", "tv"):
        raise TransitionError("invalid_winner", f"Некорректный победитель: {winner}")

    round_ctx = state["game"]["round"]
    if not round_ctx:
        raise TransitionError("no_round", "Нет активного раунда")
    kind = round_ctx.get("kind", "normal")

    if kind in ("blitz", "superblitz"):
        part_index = int(round_ctx.get("part_index", 0))
        if not 0 <= part_index < BLITZ_PARTS:
            raise TransitionError("invalid_round", "Некорректная часть блица")

        if winner == "tv":
            state["game"]["score"]["tv"] += 1
            logs = (
                "Неверно. Очко Телезрителям!",
                "Фаза: послераунд (обсуждение ответа)",
            )
            sounds = (incorrect_sound,)
        elif part_index < BLITZ_PARTS - 1:
            round_ctx["advance_next_part"] = True
            state["game"]["round"] = round_ctx
            logs = (f"Верно (часть {part_index + 1}/{BLITZ_PARTS}). Фаза: послераунд",)
            sounds = ()
        else:
            state["game"]["score"]["znatoki"] += 1
            logs = (
                "Все ответы верны. Очко Знатокам!",
                "Фаза: послераунд (обсуждение ответа)",
            )
            sounds = (correct_sound,)
    elif kind == "normal":
        if winner == "znatoki":
            state["game"]["score"]["znatoki"] += 1
            logs = (
                "Очко Знатокам!",
                "Фаза: послераунд (обсуждение ответа)",
            )
            sounds = (correct_sound,)
        else:
            state["game"]["score"]["tv"] += 1
            logs = (
                "Очко Телезрителям!",
                "Фаза: послераунд (обсуждение ответа)",
            )
            sounds = (incorrect_sound,)
    else:
        raise TransitionError("invalid_round", f"Неизвестный тип раунда: {kind}")

    state["timer"]["discussion_deadline_ms"] = None
    state["game"]["phase"] = PHASE_POST_ROUND
    return TransitionEffects(
        logs=logs,
        sounds=sounds,
        refresh_admin_question=True,
    )


def transition_end_round(state: AppState, *, gong_sound: str) -> TransitionEffects:
    _require_phase(state, PHASE_POST_ROUND)
    round_ctx = state["game"]["round"] or {}
    kind = round_ctx.get("kind", "normal")
    advances_blitz = (
        kind in ("blitz", "superblitz")
        and round_ctx.get("advance_next_part") is True
    )
    next_part_index = int(round_ctx.get("part_index", 0)) + 1
    if advances_blitz and next_part_index >= BLITZ_PARTS:
        raise TransitionError("invalid_round", "У блица нет следующей части")

    state["presentation"]["shared_media"] = None
    state["timer"]["discussion_deadline_ms"] = None

    if advances_blitz:
        round_ctx["part_index"] = next_part_index
        round_ctx.pop("advance_next_part", None)
        state["game"]["round"] = round_ctx
        state["game"]["phase"] = PHASE_QUESTION_READING
        return TransitionEffects(
            logs=(
                f"Переходим к части {next_part_index + 1}/{BLITZ_PARTS}. "
                "Фаза: зачитывание вопроса",
            ),
            clear_media_tokens=True,
            refresh_admin_question=True,
        )

    state["game"]["round"] = None
    state["game"]["phase"] = PHASE_PRE_ROUND
    return TransitionEffects(
        logs=("Раунд завершён. Фаза: ожидание следующего вращения",),
        sounds=(gong_sound,),
        clear_media_tokens=True,
    )


def transition_reset(state: AppState) -> TransitionEffects:
    reset_app_state(state)
    return TransitionEffects(
        logs=("Игра сброшена",),
        clear_media_tokens=True,
    )
