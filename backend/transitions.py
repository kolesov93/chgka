"""Synchronous, testable game-state transitions.

Socket.IO handlers authorize requests and deliver the effects returned here.
All state mutation happens before the handler performs network awaits, keeping
phase checks and mutations atomic within the asyncio event loop.
"""

from dataclasses import dataclass
from typing import Mapping, Optional

from game_events import GameEvent, game_event
from state import (
    AppState,
    GamePhase,
    RespondentState,
    TimerSegment,
    PHASE_DISCUSSION,
    PHASE_GAME_OVER,
    PHASE_INTRO,
    PHASE_LOGIN,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
    reset_app_state,
)
from ui_text import phase_label


SECTORS_COUNT = 13
BLITZ_PARTS = 3
WINNING_SCORE = 6
INTRO_LAST_SLIDE = 13
INTRO_DURATION_MS = 87_757
EARNED_MINUTE_MS = 60_000
CAPTAIN_EARLY_ANSWER_WINDOW_MS = 5_000


class TransitionError(ValueError):
    """A requested transition is invalid for the current state."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TransitionEffects:
    """Side effects that the async transport layer must deliver."""

    events: tuple[GameEvent, ...] = ()
    sounds: tuple[str, ...] = ()
    clear_media_tokens: bool = False
    refresh_admin_question: bool = False
    clear_admin_question: bool = False
    stop_sounds: bool = False
    start_sound_output: bool = False
    spin_id: Optional[int] = None
    playing_sector: Optional[int] = None

    @property
    def logs(self) -> tuple[str, ...]:
        """Compatibility view used by transition-level tests and callers."""
        return tuple(event.message for event in self.events)


def _require_phase(state: AppState, expected: GamePhase) -> None:
    phase = state["game"]["phase"]
    if phase != expected:
        raise TransitionError(
            "bad_phase",
            f"Действие недоступно в фазе «{phase_label(phase)}»; "
            f"ожидается «{phase_label(expected)}»",
        )


def _valid_timestamp(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _clear_timer(state: AppState) -> None:
    timer = state["timer"]
    timer["discussion_deadline_ms"] = None
    timer["segment"] = None
    timer["started_at_ms"] = None
    timer["generation"] = timer.get("generation", 0) + 1


def _start_timer(
    state: AppState,
    *,
    segment: TimerSegment,
    started_at_ms: int,
    deadline_ms: int,
) -> None:
    if not _valid_timestamp(started_at_ms) or not _valid_timestamp(deadline_ms):
        raise TransitionError("invalid_time", "Некорректное время таймера")
    if deadline_ms <= started_at_ms:
        raise TransitionError("invalid_time", "Таймер должен завершаться после запуска")
    timer = state["timer"]
    timer["segment"] = segment
    timer["started_at_ms"] = started_at_ms
    timer["discussion_deadline_ms"] = deadline_ms
    timer["generation"] = timer.get("generation", 0) + 1


def _require_timer_generation(state: AppState, expected_generation: object) -> None:
    if expected_generation is None:
        return
    if (
        not isinstance(expected_generation, int)
        or isinstance(expected_generation, bool)
        or expected_generation != state["timer"].get("generation", 0)
    ):
        raise TransitionError("stale_timer", "Состояние таймера уже изменилось")


def _round_event_context(round_ctx: Mapping[str, object]) -> dict[str, object]:
    kind = round_ctx.get("kind", "normal")
    return {
        "sector": round_ctx.get("sector"),
        "kind": kind,
        "part_index": (
            int(round_ctx.get("part_index", 0))
            if kind in ("blitz", "superblitz")
            else None
        ),
    }


def _actor_payload(actor: Mapping[str, object]) -> dict[str, object]:
    role = actor.get("role")
    if role == "host":
        return {"actor_role": "host"}
    if role == "captain":
        return {
            "actor_role": "captain",
            "actor_participant_id": actor.get("participant_id"),
            "actor_group_id": actor.get("group_id"),
            "actor_name": actor.get("name"),
        }
    raise TransitionError("invalid_actor", "Некорректный инициатор действия")


def _game_winner(state: AppState) -> Optional[str]:
    score = state["game"]["score"]
    znatoki_won = score["znatoki"] >= WINNING_SCORE
    tv_won = score["tv"] >= WINNING_SCORE
    if znatoki_won and tv_won:
        raise TransitionError(
            "invalid_score",
            "Обе стороны не могут одновременно иметь победный счёт",
        )
    if znatoki_won:
        return "znatoki"
    if tv_won:
        return "tv"
    return None


def transition_start_game(state: AppState) -> TransitionEffects:
    _require_phase(state, PHASE_LOGIN)

    state["game"]["phase"] = PHASE_INTRO
    state["presentation"]["intro"] = {
        "slide_index": 0,
        "started_at_ms": None,
        "duration_ms": INTRO_DURATION_MS,
    }
    return TransitionEffects(events=(game_event("game_started", "Интро началось"),))


def transition_start_intro_music(
    state: AppState,
    *,
    now_ms: int,
) -> TransitionEffects:
    _require_phase(state, PHASE_INTRO)
    if not isinstance(now_ms, int) or isinstance(now_ms, bool) or now_ms < 0:
        raise TransitionError("invalid_time", "Некорректное время начала музыки")

    intro = state["presentation"]["intro"]
    if intro is None:
        raise TransitionError("missing_intro", "Нет активного интро")
    if intro["started_at_ms"] is not None:
        raise TransitionError("intro_music_started", "Музыка интро уже была запущена")

    intro["started_at_ms"] = now_ms
    return TransitionEffects(
        events=(game_event("intro_music_started", "Интро: музыка запущена"),),
        sounds=("intro",),
    )


def transition_advance_intro(
    state: AppState,
    *,
    expected_slide: int,
) -> TransitionEffects:
    _require_phase(state, PHASE_INTRO)
    if (
        not isinstance(expected_slide, int)
        or isinstance(expected_slide, bool)
        or not 0 <= expected_slide <= INTRO_LAST_SLIDE
    ):
        raise TransitionError("invalid_intro_slide", "Некорректный номер слайда интро")

    intro = state["presentation"]["intro"]
    if intro is None:
        raise TransitionError("missing_intro", "Нет активного интро")
    current_slide = intro["slide_index"]
    if current_slide != expected_slide:
        raise TransitionError(
            "stale_intro",
            f"Слайд интро уже изменился: сейчас {current_slide:02d}",
        )

    if current_slide < INTRO_LAST_SLIDE:
        next_slide = current_slide + 1
        intro["slide_index"] = next_slide
        return TransitionEffects(
            events=(
                game_event(
                    "intro_slide_changed",
                    f"Интро: слайд {next_slide:02d}",
                    slide_index=next_slide,
                ),
            )
        )

    state["presentation"]["intro"] = None
    state["game"]["phase"] = PHASE_PRE_ROUND
    return TransitionEffects(
        events=(
            game_event(
                "intro_completed",
                "Интро завершено. Фаза: ожидание первого вращения",
            ),
        ),
        stop_sounds=True,
    )


def transition_skip_intro(
    state: AppState,
    *,
    expected_slide: int,
) -> TransitionEffects:
    """Skip the remaining host-controlled intro in one guarded mutation."""
    _require_phase(state, PHASE_INTRO)
    if (
        not isinstance(expected_slide, int)
        or isinstance(expected_slide, bool)
        or not 0 <= expected_slide <= INTRO_LAST_SLIDE
    ):
        raise TransitionError("invalid_intro_slide", "Некорректный номер слайда интро")

    intro = state["presentation"]["intro"]
    if intro is None:
        raise TransitionError("missing_intro", "Нет активного интро")
    current_slide = intro["slide_index"]
    if current_slide != expected_slide:
        raise TransitionError(
            "stale_intro",
            f"Слайд интро уже изменился: сейчас {current_slide:02d}",
        )

    state["presentation"]["intro"] = None
    state["game"]["phase"] = PHASE_PRE_ROUND
    return TransitionEffects(
        events=(
            game_event(
                "intro_skipped",
                "Оставшаяся часть вступления пропущена. "
                "Фаза: ожидание первого вращения",
                slide_index=current_slide,
            ),
        ),
        stop_sounds=True,
    )


def clear_blackbox_presentation(state: AppState) -> bool:
    """End the active black-box presentation and invalidate stale commands."""
    if state["presentation"].get("blackbox") is None:
        return False
    state["presentation"]["blackbox"] = None
    state["presentation"]["blackbox_generation"] = (
        state["presentation"].get("blackbox_generation", 0) + 1
    )
    return True


def clear_author_presentation(state: AppState) -> bool:
    """Hide only a shared author card, leaving ordinary question media alone."""
    shared_media = state["presentation"].get("shared_media")
    if not shared_media or shared_media.get("presentation_kind") != "author":
        return False
    state["presentation"]["shared_media"] = None
    return True


def transition_start_blackbox(
    state: AppState,
    *,
    enabled: bool,
    now_ms: int,
) -> TransitionEffects:
    _require_phase(state, PHASE_QUESTION_READING)
    if not enabled:
        raise TransitionError(
            "blackbox_unavailable",
            "Текущий вопрос не отмечен как чёрный ящик",
        )
    if not isinstance(now_ms, int) or isinstance(now_ms, bool) or now_ms < 0:
        raise TransitionError("invalid_time", "Некорректное время запуска чёрного ящика")
    if state["presentation"].get("blackbox") is not None:
        raise TransitionError("blackbox_active", "Чёрный ящик уже запущен")

    generation = state["presentation"].get("blackbox_generation", 0) + 1
    state["presentation"]["blackbox_generation"] = generation
    state["presentation"]["shared_media"] = None
    state["presentation"]["blackbox"] = {
        "started_at_ms": now_ms,
        "playback_generation": generation,
    }
    return TransitionEffects(
        events=(
            game_event("blackbox_started", "Чёрный ящик: музыка запущена"),
        ),
        start_sound_output=True,
    )


def transition_end_blackbox(
    state: AppState,
    *,
    expected_generation: int,
    natural: bool = False,
) -> TransitionEffects:
    active = state["presentation"].get("blackbox")
    if active is None:
        raise TransitionError("blackbox_inactive", "Чёрный ящик сейчас не запущен")
    if (
        not isinstance(expected_generation, int)
        or isinstance(expected_generation, bool)
        or expected_generation < 0
    ):
        raise TransitionError("invalid_generation", "Некорректная версия чёрного ящика")
    if active["playback_generation"] != expected_generation:
        raise TransitionError("stale_blackbox", "Команда относится к прошлому запуску чёрного ящика")

    clear_blackbox_presentation(state)
    ending = "музыка завершилась" if natural else "остановлен ведущим"
    return TransitionEffects(
        events=(
            game_event(
                "blackbox_ended",
                f"Чёрный ящик: {ending}",
                natural=natural,
            ),
        )
    )


def transition_select_captain(
    state: AppState,
    *,
    participant_id: str,
    group_id: str,
    name: str,
) -> TransitionEffects:
    """Select one approved physical participant as captain for this game."""

    if state["game"]["phase"] == PHASE_GAME_OVER:
        raise TransitionError("game_finished", "В завершённой игре нельзя менять капитана")
    if not all(
        isinstance(value, str) and value
        for value in (participant_id, group_id, name)
    ):
        raise TransitionError("invalid_captain", "Некорректный участник")

    previous = state["game"]["team"].get("captain")
    if previous and previous.get("participant_id") == participant_id:
        raise TransitionError("captain_unchanged", f"{name} уже выбран капитаном")
    captain: RespondentState = {
        "participant_id": participant_id,
        "group_id": group_id,
        "name": name,
    }
    state["game"]["team"]["captain"] = captain
    return TransitionEffects(
        events=(
            game_event(
                "captain_selected",
                f"Капитан: {name}",
                **captain,
                previous_captain=dict(previous) if previous else None,
            ),
        ),
    )


def transition_clear_captain(
    state: AppState,
    *,
    expected_group_id: Optional[str] = None,
    reason: str = "cleared",
) -> TransitionEffects:
    captain = state["game"]["team"].get("captain")
    if captain is None:
        return TransitionEffects()
    if expected_group_id is not None and captain.get("group_id") != expected_group_id:
        return TransitionEffects()
    state["game"]["team"]["captain"] = None
    return TransitionEffects(
        events=(
            game_event(
                "captain_cleared",
                f"Капитан больше не выбран: {captain['name']}",
                **captain,
                reason=reason,
            ),
        ),
    )


def validate_spin_start(state: AppState) -> None:
    _require_phase(state, PHASE_PRE_ROUND)
    if state["game"]["team"]["credit"].get("repayment_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    if state["wheel"]["is_spinning"]:
        raise TransitionError("spinning", "Волчок уже вращается")
    if (
        state["game"]["score"]["znatoki"] >= WINNING_SCORE
        or state["game"]["score"]["tv"] >= WINNING_SCORE
    ):
        raise TransitionError(
            "game_finished",
            f"Одна из команд уже набрала {WINNING_SCORE} очков",
        )
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
    clear_blackbox_presentation(state)
    state["wheel"]["target_angle"] = raw_angle
    state["wheel"]["playing_sector"] = playing_sector
    state["wheel"]["spin_duration"] = duration
    state["wheel"]["is_spinning"] = True
    state["wheel"]["spin_id"] = spin_id

    log = f"Вращение! Угол: {raw_angle:.1f}° (сектор {raw_sector})"
    if forced:
        log += " [выбор ведущего]"
    log += f" → играет сектор: {playing_sector}"
    events = [
        game_event(
            "spin_started",
            log,
            raw_angle=raw_angle,
            raw_sector=raw_sector,
            playing_sector=playing_sector,
            forced=forced,
            spin_id=spin_id,
        )
    ]
    if playing_sector == SECTORS_COUNT:
        events.append(
            game_event(
                "sector_thirteen_selected",
                "Внимание! 13-й сектор!",
                sector=SECTORS_COUNT,
                spin_id=spin_id,
            )
        )

    return TransitionEffects(
        events=tuple(events),
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
    repayment = state["game"]["team"]["credit"].get("repayment_scheduled", False)
    if question_type in ("blitz", "superblitz"):
        state["game"]["round"] = {
            "kind": question_type,
            "sector": playing_sector,
            "part_index": 0,
            **({"credit_repayment": True} if repayment else {}),
        }
    else:
        state["game"]["round"] = {
            "kind": "normal",
            "sector": playing_sector,
            **({"credit_repayment": True} if repayment else {}),
        }

    _clear_timer(state)
    state["game"]["phase"] = PHASE_QUESTION_READING
    sounds = ("sector13",) if playing_sector == SECTORS_COUNT else ()
    return TransitionEffects(
        events=(
            game_event(
                "question_opened",
                "Фаза: зачитывание вопроса",
                sector=playing_sector,
                kind=question_type,
                part_index=0 if question_type in ("blitz", "superblitz") else None,
            ),
        ),
        sounds=sounds,
        refresh_admin_question=True,
        spin_id=spin_id,
        playing_sector=playing_sector,
    )


def transition_start_discussion(
    state: AppState,
    *,
    deadline_ms: int,
    started_at_ms: Optional[int] = None,
) -> TransitionEffects:
    _require_phase(state, PHASE_QUESTION_READING)
    round_ctx = state["game"].get("round") or {}
    if round_ctx.get("strategy_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    if round_ctx.get("kind") == "superblitz" and not round_ctx.get("respondent"):
        raise TransitionError(
            "respondent_required",
            "Сначала выберите участника суперблица",
        )
    if state["presentation"].get("blackbox") is not None:
        raise TransitionError(
            "blackbox_active",
            "Сначала дождитесь окончания чёрного ящика или остановите его",
        )
    if round_ctx.get("credit_repayment"):
        raise TransitionError(
            "credit_repayment",
            "Этот вопрос играется без обсуждения в счёт возврата кредита",
        )
    if started_at_ms is None:
        kind = round_ctx.get("kind", "normal")
        duration_ms = 20_000 if kind in ("blitz", "superblitz") else 60_000
        started_at_ms = deadline_ms - duration_ms
    author_hidden = clear_author_presentation(state)
    state["game"]["phase"] = PHASE_DISCUSSION
    _start_timer(
        state,
        segment="base",
        started_at_ms=started_at_ms,
        deadline_ms=deadline_ms,
    )
    return TransitionEffects(
        events=(
            *(
                (game_event("author_hidden", "Автор скрыт: началось обсуждение"),)
                if author_hidden
                else ()
            ),
            game_event("phase_changed", "Фаза: обсуждение", phase=PHASE_DISCUSSION),
        )
    )


def transition_team_answer(state: AppState) -> TransitionEffects:
    _require_phase(state, PHASE_DISCUSSION)
    round_ctx = state["game"].get("round") or {}
    if round_ctx.get("strategy_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    segment = state["timer"].get("segment")
    if segment is not None:
        round_ctx["answer_timer_segment"] = segment
    _clear_timer(state)
    state["game"]["phase"] = PHASE_TEAM_ANSWER
    return TransitionEffects(
        events=(
            game_event(
                "phase_changed",
                "Фаза: ответ команды",
                phase=PHASE_TEAM_ANSWER,
            ),
        ),
        sounds=("sig1",),
    )


def transition_early_answer(
    state: AppState,
    *,
    now_ms: int,
    actor: Mapping[str, object],
    expected_generation: object = None,
) -> TransitionEffects:
    phase = state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION):
        raise TransitionError(
            "bad_phase",
            "Досрочный ответ доступен во время чтения или основной минуты",
        )
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время ответа")
    round_ctx = state["game"].get("round") or {}
    if round_ctx.get("kind", "normal") != "normal" or round_ctx.get("credit_repayment"):
        raise TransitionError("early_answer_unavailable", "Досрочный ответ здесь недоступен")
    if round_ctx.get("strategy_request"):
        raise TransitionError("strategy_request_pending", "Запрос капитана уже ожидает решения")
    actor_info = _actor_payload(actor)
    if phase == PHASE_DISCUSSION:
        _require_timer_generation(state, expected_generation)
        timer = state["timer"]
        started_at_ms = timer.get("started_at_ms")
        deadline_ms = timer.get("discussion_deadline_ms")
        if timer.get("segment") != "base" or started_at_ms is None or deadline_ms is None:
            raise TransitionError("early_answer_unavailable", "Сейчас не идёт основная минута")
        if now_ms >= deadline_ms:
            raise TransitionError("timer_finished", "Основная минута уже закончилась")
        if (
            actor_info["actor_role"] == "captain"
            and now_ms >= started_at_ms + CAPTAIN_EARLY_ANSWER_WINDOW_MS
        ):
            raise TransitionError(
                "captain_window_closed",
                "Пятисекундное окно капитана уже закончилось; решение остаётся за ведущим",
            )

    round_ctx["early_answer"] = True
    round_ctx["early_answer_actor"] = dict(actor_info)
    if phase == PHASE_DISCUSSION:
        round_ctx["answer_timer_segment"] = "base"
    context = _round_event_context(round_ctx)
    author_hidden = clear_author_presentation(state)
    _clear_timer(state)
    state["game"]["phase"] = PHASE_TEAM_ANSWER
    return TransitionEffects(
        events=(
            *(
                (game_event("author_hidden", "Автор скрыт: принят досрочный ответ"),)
                if author_hidden
                else ()
            ),
            game_event(
                "early_answer_declared",
                "Заявлен досрочный ответ",
                **context,
                **actor_info,
                declared_phase=phase,
            ),
            game_event(
                "phase_changed",
                "Фаза: ответ команды",
                phase=PHASE_TEAM_ANSWER,
            ),
        ),
        sounds=("sig1",),
    )


def transition_request_early_answer(
    state: AppState,
    *,
    now_ms: int,
    actor: Mapping[str, object],
    expected_generation: object = None,
) -> TransitionEffects:
    phase = state["game"]["phase"]
    if phase not in (PHASE_QUESTION_READING, PHASE_DISCUSSION):
        raise TransitionError(
            "bad_phase",
            "Досрочный ответ доступен во время чтения или основной минуты",
        )
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время запроса")
    round_ctx = state["game"].get("round") or {}
    if round_ctx.get("kind", "normal") != "normal" or round_ctx.get("credit_repayment"):
        raise TransitionError("early_answer_unavailable", "Досрочный ответ здесь недоступен")
    if round_ctx.get("strategy_request"):
        raise TransitionError("strategy_request_pending", "Запрос капитана уже ожидает решения")
    actor_info = _actor_payload(actor)
    if actor_info["actor_role"] != "captain":
        raise TransitionError("invalid_actor", "Запрос может отправить только капитан")
    if phase == PHASE_DISCUSSION:
        _require_timer_generation(state, expected_generation)
        timer = state["timer"]
        started_at_ms = timer.get("started_at_ms")
        deadline_ms = timer.get("discussion_deadline_ms")
        if timer.get("segment") != "base" or started_at_ms is None or deadline_ms is None:
            raise TransitionError("early_answer_unavailable", "Сейчас не идёт основная минута")
        if now_ms >= deadline_ms:
            raise TransitionError("timer_finished", "Основная минута уже закончилась")
        if now_ms >= started_at_ms + CAPTAIN_EARLY_ANSWER_WINDOW_MS:
            raise TransitionError("captain_window_closed", "Пятисекундное окно капитана закончилось")

    request = {
        "type": "early_answer",
        "participant_id": actor.get("participant_id"),
        "group_id": actor.get("group_id"),
        "name": actor.get("name"),
        "requested_phase": phase,
        "requested_at_ms": now_ms,
        "timer_generation": state["timer"].get("generation", 0),
    }
    round_ctx["strategy_request"] = request
    return TransitionEffects(
        events=(
            game_event(
                "early_answer_requested",
                f"Капитан {request['name']} просит принять досрочный ответ",
                **_round_event_context(round_ctx),
                **actor_info,
                requested_phase=phase,
                requested_at_ms=now_ms,
            ),
        ),
    )


def _require_team_answer_extension(
    state: AppState,
    *,
    expected_generation: object,
) -> tuple[dict, TimerSegment]:
    _require_phase(state, PHASE_TEAM_ANSWER)
    _require_timer_generation(state, expected_generation)
    round_ctx = state["game"].get("round") or {}
    if round_ctx.get("strategy_request"):
        raise TransitionError("strategy_request_pending", "Запрос капитана уже ожидает решения")
    if round_ctx.get("credit_repayment"):
        raise TransitionError("credit_repayment", "Возврат кредита идёт без таймера")
    if round_ctx.get("early_answer"):
        raise TransitionError("early_answer_locked", "После досрочного ответа игровые минуты недоступны")
    previous_segment = round_ctx.get("answer_timer_segment")
    if previous_segment not in ("base", "earned"):
        raise TransitionError("timer_unavailable", "Игровую минуту можно взять после команды ведущего")
    return round_ctx, previous_segment


def transition_spend_earned_minute(
    state: AppState,
    *,
    now_ms: int,
    actor: Mapping[str, object],
    expected_generation: object = None,
) -> TransitionEffects:
    round_ctx, previous_segment = _require_team_answer_extension(
        state,
        expected_generation=expected_generation,
    )
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время запуска минуты")
    actor_info = _actor_payload(actor)
    team = state["game"]["team"]
    before = team["earned_minutes"]
    if before <= 0:
        raise TransitionError("no_earned_minutes", "Нет заработанных дополнительных минут")
    if round_ctx.get("credit_used"):
        raise TransitionError(
            "credit_already_started",
            "После кредитной минуты дополнительные минуты недоступны",
        )
    kind = round_ctx.get("kind", "normal")
    part_index = int(round_ctx.get("part_index", 0)) if kind in ("blitz", "superblitz") else None
    selected_part = round_ctx.get("extra_part_index")
    if selected_part is not None and selected_part != part_index:
        raise TransitionError(
            "earned_part_locked",
            "Дополнительные минуты уже использовались на другой части этого блица",
        )
    if part_index is not None and selected_part is None:
        round_ctx["extra_part_index"] = part_index

    team["earned_minutes"] = before - 1
    round_ctx["extra_minutes_spent"] = int(round_ctx.get("extra_minutes_spent", 0)) + 1
    round_ctx.pop("answer_timer_segment", None)
    if kind != "superblitz":
        round_ctx.pop("respondent", None)
    state["game"]["phase"] = PHASE_DISCUSSION
    _start_timer(
        state,
        segment="earned",
        started_at_ms=now_ms,
        deadline_ms=now_ms + EARNED_MINUTE_MS,
    )
    return TransitionEffects(
        events=(
            game_event(
                "earned_minute_spent",
                f"Использована дополнительная минута. Осталось: {before - 1}",
                **_round_event_context(round_ctx),
                **actor_info,
                previous_segment=previous_segment,
                balance_before=before,
                balance_after=before - 1,
                timer_generation=state["timer"]["generation"],
            ),
            game_event("phase_changed", "Фаза: дополнительная минута", phase=PHASE_DISCUSSION),
        ),
    )


def transition_take_credit_minute(
    state: AppState,
    *,
    now_ms: int,
    actor: Mapping[str, object],
    expected_generation: object = None,
) -> TransitionEffects:
    round_ctx, previous_segment = _require_team_answer_extension(
        state,
        expected_generation=expected_generation,
    )
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время запуска кредита")
    actor_info = _actor_payload(actor)
    score = state["game"]["score"]
    if score["tv"] != 5 or not 0 <= score["znatoki"] <= 4:
        raise TransitionError("credit_score", "Минута в кредит доступна только при счёте X:5")
    credit = state["game"]["team"]["credit"]
    if credit["used"]:
        raise TransitionError("credit_used", "Минута в кредит уже использована в этой игре")

    credit["used"] = True
    round_ctx["credit_used"] = True
    kind = round_ctx.get("kind", "normal")
    if kind in ("blitz", "superblitz"):
        round_ctx["credit_part_index"] = int(round_ctx.get("part_index", 0))
    round_ctx.pop("answer_timer_segment", None)
    if kind != "superblitz":
        round_ctx.pop("respondent", None)
    state["game"]["phase"] = PHASE_DISCUSSION
    _start_timer(
        state,
        segment="credit",
        started_at_ms=now_ms,
        deadline_ms=now_ms + EARNED_MINUTE_MS,
    )
    return TransitionEffects(
        events=(
            game_event(
                "credit_minute_taken",
                "Команда взяла минуту в кредит",
                **_round_event_context(round_ctx),
                **actor_info,
                previous_segment=previous_segment,
                score=dict(score),
                timer_generation=state["timer"]["generation"],
            ),
            game_event("phase_changed", "Фаза: минута в кредит", phase=PHASE_DISCUSSION),
        ),
    )


def transition_request_credit_minute(
    state: AppState,
    *,
    now_ms: int,
    actor: Mapping[str, object],
    expected_generation: object = None,
) -> TransitionEffects:
    round_ctx, previous_segment = _require_team_answer_extension(
        state,
        expected_generation=expected_generation,
    )
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время запроса")
    actor_info = _actor_payload(actor)
    if actor_info["actor_role"] != "captain":
        raise TransitionError("invalid_actor", "Запрос может отправить только капитан")
    score = state["game"]["score"]
    if score["tv"] != 5 or not 0 <= score["znatoki"] <= 4:
        raise TransitionError("credit_score", "Минута в кредит доступна только при счёте X:5")
    if state["game"]["team"]["credit"]["used"]:
        raise TransitionError("credit_used", "Минута в кредит уже использована в этой игре")

    request = {
        "type": "credit",
        "participant_id": actor.get("participant_id"),
        "group_id": actor.get("group_id"),
        "name": actor.get("name"),
        "requested_phase": PHASE_TEAM_ANSWER,
        "requested_at_ms": now_ms,
        "timer_generation": state["timer"].get("generation", 0),
    }
    round_ctx["strategy_request"] = request
    return TransitionEffects(
        events=(
            game_event(
                "credit_minute_requested",
                f"Капитан {request['name']} просит минуту в кредит",
                **_round_event_context(round_ctx),
                **actor_info,
                previous_segment=previous_segment,
                requested_at_ms=now_ms,
            ),
        ),
    )


def transition_resolve_strategy_request(
    state: AppState,
    *,
    approve: object,
    now_ms: int,
) -> TransitionEffects:
    if not isinstance(approve, bool):
        raise TransitionError("invalid_decision", "Некорректное решение ведущего")
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время решения")
    round_ctx = state["game"].get("round") or {}
    credit = state["game"]["team"]["credit"]
    request_owner = round_ctx
    request_key = "strategy_request"
    request = round_ctx.get(request_key)
    if not request:
        request_owner = credit
        request_key = "repayment_request"
        request = credit.get(request_key)
    if not request:
        raise TransitionError("no_strategy_request", "Нет ожидающего запроса капитана")
    if state["game"]["phase"] != request.get("requested_phase"):
        raise TransitionError("stale_strategy_request", "Состояние игры после запроса изменилось")

    request_type = request.get("type")
    if request_type not in ("early_answer", "credit", "repayment"):
        raise TransitionError("invalid_strategy_request", "Неизвестный запрос капитана")
    captain = {
        "role": "captain",
        "participant_id": request.get("participant_id"),
        "group_id": request.get("group_id"),
        "name": request.get("name"),
    }
    request_owner.pop(request_key, None)
    if approve:
        try:
            if request_type == "early_answer":
                effects = transition_early_answer(
                    state,
                    now_ms=request.get("requested_at_ms"),
                    actor=captain,
                    expected_generation=request.get("timer_generation"),
                )
            elif request_type == "credit":
                effects = transition_take_credit_minute(
                    state,
                    now_ms=now_ms,
                    actor=captain,
                    expected_generation=request.get("timer_generation"),
                )
            else:
                effects = transition_schedule_credit_repayment(
                    state,
                    actor=captain,
                )
        except TransitionError:
            request_owner[request_key] = request
            raise
        context = (
            _round_event_context(round_ctx)
            if request_type in ("early_answer", "credit")
            else {}
        )
        approved_event = game_event(
            "strategy_request_approved",
            "Ведущий одобрил запрос капитана",
            **context,
            request_type=request_type,
            actor_role="host",
            requested_by_participant_id=request.get("participant_id"),
            requested_by_group_id=request.get("group_id"),
            requested_by_name=request.get("name"),
        )
        return TransitionEffects(
            events=(approved_event, *effects.events),
            sounds=effects.sounds,
            clear_media_tokens=effects.clear_media_tokens,
            refresh_admin_question=effects.refresh_admin_question,
            clear_admin_question=effects.clear_admin_question,
            stop_sounds=effects.stop_sounds,
            start_sound_output=effects.start_sound_output,
            spin_id=effects.spin_id,
            playing_sector=effects.playing_sector,
        )

    event_type = {
        "early_answer": "early_answer_request_rejected",
        "credit": "credit_minute_request_rejected",
        "repayment": "credit_repayment_request_rejected",
    }[request_type]
    context = (
        _round_event_context(round_ctx)
        if request_type in ("early_answer", "credit")
        else {}
    )
    return TransitionEffects(
        events=(
            game_event(
                event_type,
                "Ведущий отклонил запрос капитана",
                **context,
                request_type=request_type,
                actor_role="host",
                requested_by_participant_id=request.get("participant_id"),
                requested_by_group_id=request.get("group_id"),
                requested_by_name=request.get("name"),
            ),
        ),
    )


def _require_credit_repayment_schedulable(state: AppState) -> dict:
    phase = state["game"]["phase"]
    if phase not in (PHASE_PRE_ROUND, PHASE_POST_ROUND):
        raise TransitionError(
            "repayment_too_late",
            "Возврат кредита нужно назначить до вращения волчка",
        )
    if state["wheel"]["is_spinning"]:
        raise TransitionError("repayment_too_late", "Волчок уже запущен")
    round_ctx = state["game"].get("round") or {}
    if phase == PHASE_POST_ROUND and round_ctx.get("advance_next_part"):
        raise TransitionError(
            "blitz_in_progress",
            "Возврат можно назначить после завершения всего блица",
        )
    credit = state["game"]["team"]["credit"]
    if not credit["debt"]:
        raise TransitionError("no_credit_debt", "У команды нет долга по кредиту")
    if credit["repayment_scheduled"]:
        raise TransitionError("repayment_scheduled", "Возврат уже назначен")
    return credit


def transition_request_credit_repayment(
    state: AppState,
    *,
    now_ms: int,
    actor: Mapping[str, object],
) -> TransitionEffects:
    if not _valid_timestamp(now_ms):
        raise TransitionError("invalid_time", "Некорректное время запроса")
    actor_info = _actor_payload(actor)
    if actor_info["actor_role"] != "captain":
        raise TransitionError("invalid_actor", "Запрос может отправить только капитан")
    credit = _require_credit_repayment_schedulable(state)
    if credit.get("repayment_request"):
        raise TransitionError("strategy_request_pending", "Запрос капитана уже ожидает решения")

    request = {
        "type": "repayment",
        "participant_id": actor.get("participant_id"),
        "group_id": actor.get("group_id"),
        "name": actor.get("name"),
        "requested_phase": state["game"]["phase"],
        "requested_at_ms": now_ms,
    }
    credit["repayment_request"] = request
    return TransitionEffects(
        events=(
            game_event(
                "credit_repayment_requested",
                f"Капитан {request['name']} просит вернуть минуту в кредит",
                **actor_info,
                requested_phase=state["game"]["phase"],
                requested_at_ms=now_ms,
                score=dict(state["game"]["score"]),
            ),
        ),
    )


def transition_schedule_credit_repayment(
    state: AppState,
    *,
    actor: Mapping[str, object],
    forced: bool = False,
) -> TransitionEffects:
    credit = _require_credit_repayment_schedulable(state)
    if credit.get("repayment_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    actor_info = _actor_payload(actor)
    credit["repayment_scheduled"] = True
    credit["forced"] = forced
    message = (
        "При счёте 5:5 возврат кредита назначен автоматически"
        if forced
        else "Возврат кредита назначен на следующий раунд"
    )
    return TransitionEffects(
        events=(
            game_event(
                "credit_repayment_scheduled",
                message,
                **actor_info,
                forced=forced,
                score=dict(state["game"]["score"]),
            ),
        ),
    )


def _complete_credit_repayment(state: AppState, round_ctx: dict) -> Optional[GameEvent]:
    credit = state["game"]["team"]["credit"]
    if not round_ctx.get("credit_repayment") or not credit["debt"]:
        return None
    kind = round_ctx.get("kind", "normal")
    part_index = int(round_ctx.get("part_index", 0)) if kind in ("blitz", "superblitz") else None
    if part_index is not None and part_index < BLITZ_PARTS - 1:
        return None
    credit["debt"] = False
    credit["repayment_scheduled"] = False
    credit["forced"] = False
    return game_event(
        "credit_repayment_completed",
        "Минута в кредит возвращена ответом без обсуждения",
        **_round_event_context(round_ctx),
    )


def transition_repayment_answer(state: AppState) -> TransitionEffects:
    _require_phase(state, PHASE_QUESTION_READING)
    round_ctx = state["game"].get("round") or {}
    if not round_ctx.get("credit_repayment"):
        raise TransitionError("no_credit_repayment", "Текущий раунд не возвращает кредит")
    if round_ctx.get("kind") == "superblitz" and not round_ctx.get("respondent"):
        raise TransitionError("respondent_required", "Сначала выберите участника суперблица")
    author_hidden = clear_author_presentation(state)
    _clear_timer(state)
    state["game"]["phase"] = PHASE_TEAM_ANSWER
    events = [
        *(
            [game_event("author_hidden", "Автор скрыт: принят ответ без обсуждения")]
            if author_hidden
            else []
        ),
        game_event(
            "credit_repayment_answered",
            "Ответ без обсуждения принят",
            **_round_event_context(round_ctx),
        ),
        game_event(
            "phase_changed",
            "Фаза: ответ команды",
            phase=PHASE_TEAM_ANSWER,
        ),
    ]
    completed = _complete_credit_repayment(state, round_ctx)
    if completed is not None:
        events.append(completed)
    return TransitionEffects(events=tuple(events), sounds=("sig1",))


def transition_select_respondent(
    state: AppState,
    *,
    participant_id: str,
    group_id: str,
    name: str,
) -> TransitionEffects:
    """Select the one physical participant answering the active question part."""

    round_ctx = state["game"].get("round")
    if not round_ctx:
        raise TransitionError("no_round", "Нет активного вопроса")
    if round_ctx.get("strategy_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    kind = round_ctx.get("kind", "normal")
    phase = state["game"]["phase"]
    if kind == "superblitz":
        if phase != PHASE_QUESTION_READING:
            raise TransitionError(
                "bad_phase",
                "Участника суперблица выбирают до начала обсуждения",
            )
        current = round_ctx.get("respondent")
        part_index = int(round_ctx.get("part_index", 0))
        if (
            current
            and part_index > 0
            and current.get("participant_id") != participant_id
        ):
            raise TransitionError(
                "respondent_locked",
                "Участник суперблица уже выбран на все три части",
            )
    elif phase != PHASE_TEAM_ANSWER:
        raise TransitionError(
            "bad_phase",
            "Отвечавшего выбирают после «Ответ команды»",
        )

    if not all(isinstance(value, str) and value for value in (participant_id, group_id, name)):
        raise TransitionError("invalid_respondent", "Некорректный участник")

    respondent: RespondentState = {
        "participant_id": participant_id,
        "group_id": group_id,
        "name": name,
    }
    round_ctx["respondent"] = respondent
    part_index = (
        int(round_ctx.get("part_index", 0))
        if kind in ("blitz", "superblitz")
        else None
    )
    return TransitionEffects(
        events=(
            game_event(
                "respondent_selected",
                f"Отвечает: {name}",
                participant_id=participant_id,
                group_id=group_id,
                name=name,
                sector=round_ctx.get("sector"),
                kind=kind,
                part_index=part_index,
            ),
        ),
    )


def transition_ten_seconds(state: AppState, *, deadline_ms: int) -> TransitionEffects:
    _require_phase(state, PHASE_DISCUSSION)
    if not _valid_timestamp(deadline_ms):
        raise TransitionError("invalid_time", "Некорректное время таймера")
    state["timer"]["discussion_deadline_ms"] = deadline_ms
    state["timer"]["generation"] = state["timer"].get("generation", 0) + 1
    return TransitionEffects(
        events=(
            game_event(
                "timer_changed",
                "Сигнал: 10 секунд (таймер сброшен на 10)",
                seconds=10,
            ),
        ),
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
    if _game_winner(state) is not None:
        raise TransitionError("game_finished", "Игра уже достигла победного счёта")
    if winner not in ("znatoki", "tv"):
        raise TransitionError("invalid_winner", "Некорректно указана победившая сторона")

    round_ctx = state["game"]["round"]
    if not round_ctx:
        raise TransitionError("no_round", "Нет активного раунда")
    if round_ctx.get("strategy_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    if not round_ctx.get("respondent"):
        raise TransitionError(
            "respondent_required",
            "Сначала выберите отвечавшего",
        )
    kind = round_ctx.get("kind", "normal")
    resource_events: list[GameEvent] = []

    if kind in ("blitz", "superblitz"):
        part_index = int(round_ctx.get("part_index", 0))
        if not 0 <= part_index < BLITZ_PARTS:
            raise TransitionError("invalid_round", "Некорректная часть блица")

        if winner == "tv":
            state["game"]["score"]["tv"] += 1
            events = (
                game_event(
                    "score_changed",
                    "Неверно. Очко Телезрителям!",
                    winner="tv",
                    score=dict(state["game"]["score"]),
                    part_index=part_index,
                ),
                game_event(
                    "phase_changed",
                    "Фаза: разбор ответа",
                    phase=PHASE_POST_ROUND,
                ),
            )
            sounds = (incorrect_sound,)
        elif part_index < BLITZ_PARTS - 1:
            round_ctx["advance_next_part"] = True
            state["game"]["round"] = round_ctx
            events = (
                game_event(
                    "blitz_part_answered",
                    f"Верно (часть {part_index + 1}/{BLITZ_PARTS}). Фаза: разбор ответа",
                    winner="znatoki",
                    part_index=part_index,
                ),
            )
            sounds = ()
        else:
            state["game"]["score"]["znatoki"] += 1
            events = (
                game_event(
                    "score_changed",
                    "Все ответы верны. Очко Знатокам!",
                    winner="znatoki",
                    score=dict(state["game"]["score"]),
                    part_index=part_index,
                ),
                game_event(
                    "phase_changed",
                    "Фаза: разбор ответа",
                    phase=PHASE_POST_ROUND,
                ),
            )
            sounds = (correct_sound,)
    elif kind == "normal":
        if winner == "znatoki":
            state["game"]["score"]["znatoki"] += 1
            events = (
                game_event(
                    "score_changed",
                    "Очко Знатокам!",
                    winner="znatoki",
                    score=dict(state["game"]["score"]),
                ),
                game_event(
                    "phase_changed",
                    "Фаза: разбор ответа",
                    phase=PHASE_POST_ROUND,
                ),
            )
            sounds = (correct_sound,)
        else:
            state["game"]["score"]["tv"] += 1
            events = (
                game_event(
                    "score_changed",
                    "Очко Телезрителям!",
                    winner="tv",
                    score=dict(state["game"]["score"]),
                ),
                game_event(
                    "phase_changed",
                    "Фаза: разбор ответа",
                    phase=PHASE_POST_ROUND,
                ),
            )
            sounds = (incorrect_sound,)
    else:
        raise TransitionError("invalid_round", "Неизвестный тип активного раунда")

    round_won = (
        winner == "znatoki"
        and (
            kind == "normal"
            or (
                kind in ("blitz", "superblitz")
                and int(round_ctx.get("part_index", 0)) == BLITZ_PARTS - 1
            )
        )
    )
    round_lost = winner == "tv"
    team = state["game"]["team"]
    if kind == "normal" and round_ctx.get("early_answer") and round_won:
        before = team["earned_minutes"]
        team["earned_minutes"] = before + 1
        resource_events.append(
            game_event(
                "earned_minute_awarded",
                f"Заработана дополнительная минута. В банке: {before + 1}",
                **_round_event_context(round_ctx),
                balance_before=before,
                balance_after=before + 1,
            )
        )

    credit = team["credit"]
    if round_ctx.get("credit_used") and round_won:
        credit["debt"] = True
        resource_events.append(
            game_event(
                "credit_debt_created",
                "Кредитная минута помогла выиграть раунд: минуту нужно вернуть",
                **_round_event_context(round_ctx),
                score=dict(state["game"]["score"]),
            )
        )
    elif round_ctx.get("credit_used") and round_lost:
        resource_events.append(
            game_event(
                "credit_round_lost",
                "Раунд с кредитной минутой проигран; долг не возник",
                **_round_event_context(round_ctx),
                score=dict(state["game"]["score"]),
            )
        )

    if (
        credit["debt"]
        and not credit["repayment_scheduled"]
        and state["game"]["score"] == {"znatoki": 5, "tv": 5}
    ):
        credit["repayment_scheduled"] = True
        credit["forced"] = True
        resource_events.append(
            game_event(
                "credit_repayment_scheduled",
                "При счёте 5:5 возврат кредита назначен автоматически",
                actor_role="system",
                forced=True,
                score=dict(state["game"]["score"]),
            )
        )

    if (
        round_ctx.get("credit_repayment")
        and round_lost
        and state["game"]["score"]["tv"] >= WINNING_SCORE
        and credit["debt"]
    ):
        credit["debt"] = False
        credit["repayment_scheduled"] = False
        credit["forced"] = False
        resource_events.append(
            game_event(
                "credit_repayment_terminated",
                "Игра завершилась во время возврата кредита",
                **_round_event_context(round_ctx),
            )
        )

    _clear_timer(state)
    state["game"]["phase"] = PHASE_POST_ROUND
    return TransitionEffects(
        events=tuple((*events, *resource_events)),
        sounds=sounds,
        refresh_admin_question=True,
    )


def transition_end_round(state: AppState, *, gong_sound: str) -> TransitionEffects:
    _require_phase(state, PHASE_POST_ROUND)
    if state["game"]["team"]["credit"].get("repayment_request"):
        raise TransitionError(
            "strategy_request_pending",
            "Сначала ответьте на запрос капитана",
        )
    round_ctx = state["game"]["round"] or {}
    kind = round_ctx.get("kind", "normal")
    winner = _game_winner(state)
    if winner is not None:
        score = state["game"]["score"]
        winner_label = "Знатоков" if winner == "znatoki" else "Телезрителей"
        state["game"]["round"] = None
        state["game"]["phase"] = PHASE_GAME_OVER
        state["presentation"]["shared_media"] = None
        _clear_timer(state)
        state["wheel"]["target_angle"] = None
        state["wheel"]["playing_sector"] = None
        state["wheel"]["spin_duration"] = 0
        state["wheel"]["is_spinning"] = False
        return TransitionEffects(
            events=(
                game_event(
                    "game_completed",
                    f"Игра завершена. Победа {winner_label}: "
                    f"{score['znatoki']}:{score['tv']}",
                    winner=winner,
                    score=dict(score),
                ),
            ),
            sounds=("final",),
            clear_media_tokens=True,
            clear_admin_question=True,
            stop_sounds=True,
        )

    advances_blitz = (
        kind in ("blitz", "superblitz")
        and round_ctx.get("advance_next_part") is True
    )
    next_part_index = int(round_ctx.get("part_index", 0)) + 1
    if advances_blitz and next_part_index >= BLITZ_PARTS:
        raise TransitionError("invalid_round", "У блица нет следующей части")
    if advances_blitz and kind == "superblitz" and not round_ctx.get("respondent"):
        raise TransitionError(
            "respondent_required",
            "Не выбран участник суперблица",
        )

    state["presentation"]["shared_media"] = None
    _clear_timer(state)

    if advances_blitz:
        round_ctx["part_index"] = next_part_index
        round_ctx.pop("advance_next_part", None)
        round_ctx.pop("answer_timer_segment", None)
        if kind == "blitz":
            round_ctx.pop("respondent", None)
        state["game"]["round"] = round_ctx
        state["game"]["phase"] = PHASE_QUESTION_READING
        events = [
            game_event(
                "question_opened",
                f"Переходим к части {next_part_index + 1}/{BLITZ_PARTS}. "
                "Фаза: зачитывание вопроса",
                sector=round_ctx["sector"],
                kind=kind,
                part_index=next_part_index,
            ),
        ]
        if kind == "superblitz":
            respondent = round_ctx.get("respondent")
            events.append(
                game_event(
                    "respondent_selected",
                    f"Суперблиц, часть {next_part_index + 1}: отвечает "
                    f"{respondent['name']}",
                    **respondent,
                    sector=round_ctx["sector"],
                    kind=kind,
                    part_index=next_part_index,
                    retained=True,
                )
            )
        return TransitionEffects(
            events=tuple(events),
            clear_media_tokens=True,
            refresh_admin_question=True,
        )

    state["game"]["round"] = None
    state["game"]["phase"] = PHASE_PRE_ROUND
    return TransitionEffects(
        events=(
            game_event(
                "round_completed",
                "Раунд завершён. Фаза: ожидание следующего вращения",
            ),
        ),
        sounds=(gong_sound,),
        clear_media_tokens=True,
    )


def transition_reset(state: AppState) -> TransitionEffects:
    old_phase = state["game"]["phase"]
    old_score = dict(state["game"]["score"])
    reset_app_state(state)
    return TransitionEffects(
        events=(
            game_event(
                "game_reset",
                "Игра сброшена",
                previous_phase=old_phase,
                score=old_score,
                target_phase=PHASE_LOGIN,
            ),
        ),
        clear_media_tokens=True,
        clear_admin_question=True,
        stop_sounds=True,
    )
