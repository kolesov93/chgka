"""Synchronous admin recovery operations for repairing a live game."""

from __future__ import annotations

import math
from typing import Optional

from state import (
    AppState,
    GamePhase,
    PHASE_DISCUSSION,
    PHASE_INTRO,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    reset_app_state,
)
from transitions import (
    BLITZ_PARTS,
    INTRO_DURATION_MS,
    SECTORS_COUNT,
    TransitionEffects,
    TransitionError,
    clear_blackbox_presentation,
)
from ui_text import phase_label, played_label, question_kind_label, timer_label


MAX_SCORE = 6
MAX_TIMER_SECONDS = 600
FORCEABLE_PHASES: tuple[GamePhase, ...] = (
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_DISCUSSION,
    PHASE_TEAM_ANSWER,
    PHASE_POST_ROUND,
)


def _require_int(value: object, *, minimum: int, maximum: int, code: str, label: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise TransitionError(
            code,
            f"{label} должно быть целым числом от {minimum} до {maximum}",
        )
    return value


def _invalidate_spin(state: AppState) -> bool:
    wheel = state["wheel"]
    was_spinning = wheel["is_spinning"]
    if was_spinning:
        wheel["spin_id"] = wheel.get("spin_id", 0) + 1
    wheel["target_angle"] = None
    wheel["playing_sector"] = None
    wheel["spin_duration"] = 0
    wheel["is_spinning"] = False
    return was_spinning


def _require_round(state: AppState) -> dict:
    round_ctx = state["game"].get("round")
    if not round_ctx:
        raise TransitionError(
            "no_round",
            "Сначала открой сектор, затем выбери фазу вопроса",
        )

    sector = round_ctx.get("sector")
    _require_int(
        sector,
        minimum=1,
        maximum=SECTORS_COUNT,
        code="invalid_round",
        label="Сектор активного раунда",
    )
    kind = round_ctx.get("kind", "normal")
    if kind not in ("normal", "blitz", "superblitz"):
        raise TransitionError("invalid_round", "Неизвестный тип активного раунда")
    if kind in ("blitz", "superblitz"):
        _require_int(
            round_ctx.get("part_index"),
            minimum=0,
            maximum=BLITZ_PARTS - 1,
            code="invalid_round",
            label="Часть блица",
        )
    return round_ctx


def live_ops_set_score(
    state: AppState,
    *,
    znatoki: object,
    tv: object,
) -> TransitionEffects:
    new_znatoki = _require_int(
        znatoki,
        minimum=0,
        maximum=MAX_SCORE,
        code="invalid_score",
        label="Счёт знатоков",
    )
    new_tv = _require_int(
        tv,
        minimum=0,
        maximum=MAX_SCORE,
        code="invalid_score",
        label="Счёт телезрителей",
    )
    old_score = dict(state["game"]["score"])
    new_score = {"znatoki": new_znatoki, "tv": new_tv}
    state["game"]["score"] = new_score
    return TransitionEffects(
        logs=(
            "Восстановление: счёт "
            f"{old_score['znatoki']}:{old_score['tv']} → {new_znatoki}:{new_tv}",
        ),
    )


def live_ops_set_sector_used(
    state: AppState,
    *,
    sector: object,
    used: object,
) -> TransitionEffects:
    sector_id = _require_int(
        sector,
        minimum=1,
        maximum=SECTORS_COUNT,
        code="invalid_sector",
        label="Сектор",
    )
    if not isinstance(used, bool):
        raise TransitionError(
            "invalid_used",
            "Признак сыгранного сектора должен быть логическим значением",
        )

    used_questions = state["game"]["used_questions"]
    was_used = sector_id in used_questions
    if used and not was_used:
        used_questions.append(sector_id)
    elif not used and was_used:
        state["game"]["used_questions"] = [
            value for value in used_questions if value != sector_id
        ]

    return TransitionEffects(
        logs=(
            f"Восстановление: сектор {sector_id} — "
            f"{played_label(was_used)} → {played_label(used)}",
        ),
    )


def live_ops_open_round(
    state: AppState,
    *,
    sector: object,
    part_index: object = None,
) -> TransitionEffects:
    sector_id = _require_int(
        sector,
        minimum=1,
        maximum=SECTORS_COUNT,
        code="invalid_sector",
        label="Сектор",
    )
    question_types = state["pack"].get("question_types") or []
    if len(question_types) != SECTORS_COUNT:
        raise TransitionError("pack_unavailable", "Типы вопросов пака недоступны")
    kind = question_types[sector_id - 1]
    if kind not in ("normal", "blitz", "superblitz"):
        raise TransitionError("invalid_question_type", "Неизвестный тип вопроса")

    if kind in ("blitz", "superblitz"):
        normalized_part = _require_int(
            part_index,
            minimum=0,
            maximum=BLITZ_PARTS - 1,
            code="invalid_part",
            label="Часть блица",
        )
        new_round = {
            "kind": kind,
            "sector": sector_id,
            "part_index": normalized_part,
        }
        part_label = f", часть {normalized_part + 1}/{BLITZ_PARTS}"
    else:
        if part_index is not None:
            raise TransitionError(
                "unexpected_part",
                "Номер части допустим только для блица/суперблица",
            )
        new_round = {"kind": "normal", "sector": sector_id}
        part_label = ""

    _invalidate_spin(state)
    state["wheel"]["current_sector"] = sector_id
    state["wheel"]["playing_sector"] = sector_id
    state["game"]["round"] = new_round
    state["game"]["phase"] = PHASE_QUESTION_READING
    state["timer"]["discussion_deadline_ms"] = None
    state["presentation"]["shared_media"] = None
    clear_blackbox_presentation(state)
    if sector_id not in state["game"]["used_questions"]:
        state["game"]["used_questions"].append(sector_id)

    return TransitionEffects(
        logs=(
            f"Восстановление: открыт сектор {sector_id} "
            f"({question_kind_label(kind)}{part_label})",
        ),
        clear_media_tokens=True,
        refresh_admin_question=True,
        stop_sounds=True,
        playing_sector=sector_id,
        spin_id=state["wheel"]["spin_id"],
    )


def live_ops_force_phase(
    state: AppState,
    *,
    phase: object,
    now_ms: int,
    normal_discussion_seconds: int,
    blitz_discussion_seconds: int,
) -> TransitionEffects:
    if phase not in FORCEABLE_PHASES:
        raise TransitionError("invalid_phase", "Эту фазу нельзя выставить вручную")
    new_phase: GamePhase = phase
    old_phase = state["game"]["phase"]
    round_ctx = None if new_phase == PHASE_PRE_ROUND else _require_round(state)
    was_spinning = _invalidate_spin(state)
    had_blackbox = clear_blackbox_presentation(state)

    if new_phase == PHASE_PRE_ROUND:
        state["game"]["round"] = None
        state["timer"]["discussion_deadline_ms"] = None
        state["presentation"]["shared_media"] = None
        state["game"]["phase"] = new_phase
        return TransitionEffects(
            logs=(
                f"Восстановление: фаза «{phase_label(old_phase)}» "
                f"→ «{phase_label(new_phase)}»",
            ),
            clear_media_tokens=True,
            clear_admin_question=True,
            stop_sounds=True,
            spin_id=state["wheel"]["spin_id"],
        )

    sector = round_ctx["sector"]
    state["wheel"]["current_sector"] = sector
    state["wheel"]["playing_sector"] = sector
    if new_phase in (
        PHASE_QUESTION_READING,
        PHASE_DISCUSSION,
        PHASE_TEAM_ANSWER,
    ):
        round_ctx.pop("advance_next_part", None)
    state["game"]["phase"] = new_phase
    clear_media = new_phase == PHASE_QUESTION_READING
    if clear_media:
        state["presentation"]["shared_media"] = None
    if new_phase == PHASE_DISCUSSION:
        kind = round_ctx.get("kind", "normal")
        seconds = (
            blitz_discussion_seconds
            if kind in ("blitz", "superblitz")
            else normal_discussion_seconds
        )
        state["timer"]["discussion_deadline_ms"] = now_ms + seconds * 1000
    else:
        state["timer"]["discussion_deadline_ms"] = None

    return TransitionEffects(
        logs=(
            f"Восстановление: фаза «{phase_label(old_phase)}» "
            f"→ «{phase_label(new_phase)}»",
        ),
        clear_media_tokens=clear_media,
        refresh_admin_question=clear_media,
        stop_sounds=was_spinning or clear_media or had_blackbox,
        spin_id=state["wheel"]["spin_id"],
    )


def live_ops_reset_to_intro(
    state: AppState,
) -> TransitionEffects:
    old_phase = state["game"]["phase"]
    old_score = dict(state["game"]["score"])
    reset_app_state(state, phase=PHASE_INTRO)
    state["presentation"]["intro"] = {
        "slide_index": 0,
        "started_at_ms": None,
        "duration_ms": INTRO_DURATION_MS,
    }
    return TransitionEffects(
        logs=(
            "Восстановление: полный сброс "
            f"из фазы «{phase_label(old_phase)}» при счёте "
            f"{old_score['znatoki']}:{old_score['tv']} → «{phase_label(PHASE_INTRO)}»",
        ),
        clear_media_tokens=True,
        clear_admin_question=True,
        stop_sounds=True,
        spin_id=state["wheel"]["spin_id"],
    )


def live_ops_cancel_spin(state: AppState) -> TransitionEffects:
    if not state["wheel"]["is_spinning"]:
        raise TransitionError("not_spinning", "Волчок сейчас не вращается")
    old_spin_id = state["wheel"]["spin_id"]
    _invalidate_spin(state)
    state["game"]["phase"] = PHASE_PRE_ROUND
    state["game"]["round"] = None
    state["timer"]["discussion_deadline_ms"] = None
    state["presentation"]["shared_media"] = None
    clear_blackbox_presentation(state)
    return TransitionEffects(
        logs=(
            f"Восстановление: вращение {old_spin_id} отменено, "
            f"фаза → «{phase_label(PHASE_PRE_ROUND)}»",
        ),
        clear_media_tokens=True,
        clear_admin_question=True,
        stop_sounds=True,
        spin_id=state["wheel"]["spin_id"],
    )


def _remaining_seconds(deadline_ms: Optional[int], *, now_ms: int) -> Optional[int]:
    if deadline_ms is None:
        return None
    return max(0, math.ceil((deadline_ms - now_ms) / 1000))


def live_ops_set_timer(
    state: AppState,
    *,
    seconds: object,
    now_ms: int,
) -> TransitionEffects:
    if state["game"]["phase"] != PHASE_DISCUSSION:
        raise TransitionError(
            "bad_phase",
            f"Таймер восстановления доступен только в фазе «{phase_label(PHASE_DISCUSSION)}»",
        )
    old_seconds = _remaining_seconds(
        state["timer"].get("discussion_deadline_ms"),
        now_ms=now_ms,
    )
    if seconds is None:
        new_seconds = None
        deadline_ms = None
    else:
        new_seconds = _require_int(
            seconds,
            minimum=1,
            maximum=MAX_TIMER_SECONDS,
            code="invalid_timer",
            label="Таймер",
        )
        deadline_ms = now_ms + new_seconds * 1000
    state["timer"]["discussion_deadline_ms"] = deadline_ms
    return TransitionEffects(
        logs=(
            f"Восстановление: таймер {timer_label(old_seconds)} "
            f"→ {timer_label(new_seconds)}",
        ),
    )
