from pathlib import Path

import pytest

from media import (
    MediaPlaybackError,
    complete_shared_media,
    create_media_token_info,
    create_shared_media,
    current_media_catalog,
    media_token_is_current,
    next_media_in_section,
    pause_shared_media,
    play_shared_media,
    stop_shared_media,
)
from questions import Media, MediaType, Question, QuestionPack, QuestionType, parse_question_pack
from state import PHASE_QUESTION_READING, create_initial_app_state


SAMPLE_PACK = Path(__file__).parent.parent.parent / "fixtures" / "sample_questions"


def _active_state(*, sector=3, kind="normal", part_index=0, spin_id=4):
    state = create_initial_app_state(phase=PHASE_QUESTION_READING)
    state["game"]["round"] = {"sector": sector, "kind": kind}
    if kind in ("blitz", "superblitz"):
        state["game"]["round"]["part_index"] = part_index
    state["wheel"]["spin_id"] = spin_id
    return state


def _question(title, *, media=None, qtype=QuestionType.NORMAL, parts=None):
    return Question(
        id=title,
        title=title,
        question_html="question",
        answer_html="answer" if qtype == QuestionType.NORMAL else None,
        media=media or [],
        type=qtype,
        parts=parts or [],
    )


def _media(path, *, ref, section="question", order=0):
    return Media(
        type=MediaType.AUDIO,
        path=path,
        section=section,
        order=order,
        ref=ref,
    )


def test_sample_question_03_exposes_one_question_audio_descriptor():
    pack = parse_question_pack(SAMPLE_PACK)
    state = _active_state(sector=3)

    catalog = current_media_catalog(pack, state)

    assert len(catalog) == 1
    descriptor = next(iter(catalog.values()))
    assert descriptor.type == "audio"
    assert descriptor.section == "question"
    assert descriptor.scope == "round"
    assert descriptor.order == 0
    assert descriptor.name == "melody.mp3"


def test_blitz_catalog_contains_intro_and_current_part_only(tmp_path):
    top = _media(tmp_path / "top.mp3", ref="top")
    part_zero = _media(tmp_path / "part-zero.mp3", ref="part-zero")
    part_one = _media(tmp_path / "part-one.mp3", ref="part-one")
    blitz = _question(
        "Blitz",
        media=[top],
        qtype=QuestionType.BLITZ,
        parts=[
            _question("Part 1", media=[part_zero]),
            _question("Part 2", media=[part_one]),
            _question("Part 3"),
        ],
    )
    pack = QuestionPack(
        questions=[_question(f"Q{i}") for i in range(1, 4)]
        + [blitz]
        + [_question(f"Q{i}") for i in range(5, 14)],
        path=tmp_path,
    )
    state = _active_state(sector=4, kind="blitz", part_index=0)

    catalog = current_media_catalog(pack, state)

    assert set(catalog) == {"top", "part-zero"}
    assert catalog["top"].scope == "round"
    assert catalog["top"].section == "intro"
    assert catalog["part-zero"].scope == "part"

    token = create_media_token_info(
        catalog["part-zero"],
        state,
        expires_at=200.0,
    )
    assert media_token_is_current(token, pack, state, now_ts=100.0)

    state["game"]["round"]["part_index"] = 1
    assert not media_token_is_current(token, pack, state, now_ts=100.0)


def test_token_rejects_expiry_and_reused_round_after_new_spin():
    pack = parse_question_pack(SAMPLE_PACK)
    state = _active_state(sector=3, spin_id=4)
    descriptor = next(iter(current_media_catalog(pack, state).values()))
    token = create_media_token_info(descriptor, state, expires_at=200.0)

    assert media_token_is_current(token, pack, state, now_ts=199.0)

    token["section"] = "answer"
    assert not media_token_is_current(token, pack, state, now_ts=100.0)
    token["section"] = "question"

    assert not media_token_is_current(token, pack, state, now_ts=200.0)
    assert media_token_is_current(
        token,
        pack,
        state,
        now_ts=200.0,
        allow_expired=True,
    )

    state["wheel"]["spin_id"] = 5
    assert not media_token_is_current(token, pack, state, now_ts=100.0)


def test_audio_play_pause_resume_and_stop_use_server_time():
    shared = create_shared_media(
        "token",
        {
            "media_ref": "audio-ref",
            "type": "audio",
            "section": "question",
            "name": "melody.mp3",
        },
    )

    assert play_shared_media(shared, now_ms=1_000)
    assert shared["playback_state"] == "playing"
    assert shared["started_at_ms"] == 1_000
    assert shared["playback_generation"] == 1

    assert pause_shared_media(shared, now_ms=2_250)
    assert shared["playback_state"] == "paused"
    assert shared["position_ms"] == 1_250
    assert shared["started_at_ms"] is None
    assert shared["playback_generation"] == 2

    assert play_shared_media(shared, now_ms=5_000)
    assert shared["started_at_ms"] == 3_750
    assert shared["playback_generation"] == 3

    assert not complete_shared_media(shared, expected_generation=1)
    assert shared["playback_state"] == "playing"

    assert complete_shared_media(shared, expected_generation=3)
    assert shared["playback_state"] == "stopped"
    assert shared["position_ms"] == 0
    assert shared["playback_generation"] == 4

    assert play_shared_media(shared, now_ms=6_000)

    assert stop_shared_media(shared)
    assert shared["playback_state"] == "stopped"
    assert shared["position_ms"] == 0
    assert shared["started_at_ms"] is None


def test_next_media_stays_in_the_same_section_and_does_not_wrap():
    pack = parse_question_pack(SAMPLE_PACK)
    state = _active_state(sector=2)
    catalog = current_media_catalog(pack, state)
    question_media = sorted(
        (media for media in catalog.values() if media.section == "question"),
        key=lambda media: media.order,
    )
    answer_media = next(
        media for media in catalog.values() if media.section == "answer"
    )

    assert len(question_media) == 2
    assert next_media_in_section(catalog, question_media[0].media_ref) == question_media[1]
    assert next_media_in_section(catalog, question_media[1].media_ref) is None
    assert next_media_in_section(catalog, answer_media.media_ref) is None
    assert next_media_in_section(catalog, "unknown") is None


def test_image_cannot_use_playback_actions():
    shared = create_shared_media(
        "token",
        {
            "media_ref": "image-ref",
            "type": "image",
            "section": "question",
            "name": "image.jpg",
        },
    )

    with pytest.raises(MediaPlaybackError) as error:
        play_shared_media(shared, now_ms=1_000)

    assert error.value.code == "unsupported_media_type"
