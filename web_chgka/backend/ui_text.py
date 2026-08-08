"""Russian display labels for values that remain language-neutral internally."""

from __future__ import annotations

from typing import Mapping

from state import (
    PHASE_DISCUSSION,
    PHASE_GAME_OVER,
    PHASE_INTRO,
    PHASE_LOGIN,
    PHASE_POST_ROUND,
    PHASE_PRE_ROUND,
    PHASE_QUESTION_READING,
    PHASE_TEAM_ANSWER,
)


_PHASE_LABELS = {
    PHASE_LOGIN: "Ожидание игроков",
    PHASE_INTRO: "Интро",
    PHASE_PRE_ROUND: "Ожидание вращения",
    PHASE_QUESTION_READING: "Чтение вопроса",
    PHASE_DISCUSSION: "Обсуждение",
    PHASE_TEAM_ANSWER: "Ответ команды",
    PHASE_POST_ROUND: "Разбор ответа",
    PHASE_GAME_OVER: "Игра завершена",
}

_QUESTION_KIND_LABELS = {
    "normal": "обычный вопрос",
    "blitz": "блиц",
    "superblitz": "суперблиц",
}

_MEDIA_TYPE_LABELS = {
    "image": "изображение",
    "audio": "аудио",
    "video": "видео",
}

_SOUND_LABELS = {
    "volchok": "вращение волчка",
    "gong1": "гонг 1",
    "gong2": "гонг 2",
    "gong3": "гонг 3",
    "sig1": "сигнал ответа",
    "sig2": "сигнал десяти секунд",
    "sig3": "сигнал 3",
    "intro": "музыка интро",
    "yes1": "верный ответ 1",
    "yes2": "верный ответ 2",
    "no1": "неверный ответ 1",
    "no2": "неверный ответ 2",
    "sector13": "13-й сектор",
    "final": "финал",
}


def phase_label(value: object) -> str:
    return _PHASE_LABELS.get(value, "Неизвестная фаза")


def question_kind_label(value: object) -> str:
    return _QUESTION_KIND_LABELS.get(value, "неизвестный тип вопроса")


def media_type_label(value: object) -> str:
    return _MEDIA_TYPE_LABELS.get(value, "медиа")


def media_display_name(info: Mapping[str, object]) -> str:
    name = info.get("name")
    if isinstance(name, str) and name.strip():
        return name
    return media_type_label(info.get("type"))


def sound_label(value: object) -> str:
    return _SOUND_LABELS.get(value, "неизвестный звук")


def played_label(value: bool) -> str:
    return "сыгран" if value else "доступен"


def timer_label(seconds: object) -> str:
    return "выключен" if seconds is None else f"{seconds} с"
