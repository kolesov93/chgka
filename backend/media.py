"""Current-round media identity, token context, and playback rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from questions import Question, QuestionPack


MediaScope = Literal["round", "part"]
PlaybackState = Literal["stopped", "playing", "paused"]


@dataclass(frozen=True)
class CurrentMedia:
    """One media reference that is selectable in the current round context."""

    media_ref: str
    type: str
    path: Path
    scope: MediaScope
    section: str
    source_section: str
    order: int
    name: str

    def public_descriptor(self) -> dict:
        return {
            "media_ref": self.media_ref,
            "type": self.type,
            "section": self.section,
            "order": self.order,
            "name": self.name,
        }


@dataclass(frozen=True)
class CurrentAuthorMedia:
    """The author card for the exact current question or blitz part."""

    media_ref: str
    path: Optional[Path]
    scope: MediaScope
    name: str
    city: Optional[str]
    asset: Literal["photo", "fallback", "sector13"]

    def public_descriptor(self) -> dict:
        return {
            "media_ref": self.media_ref,
            "type": "image",
            "section": "author",
            "name": self.name,
            "presentation_kind": "author",
            "author_name": self.name,
            "author_city": self.city,
            "author_asset": self.asset,
            "has_photo": self.asset == "photo",
        }


class MediaPlaybackError(Exception):
    """A shared media item cannot perform the requested playback action."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def current_round_key(state: dict) -> Optional[tuple[int, str, int]]:
    round_ctx = state["game"].get("round")
    if not round_ctx:
        return None
    sector = round_ctx.get("sector")
    if not isinstance(sector, int) or not 1 <= sector <= 13:
        return None
    kind = round_ctx.get("kind", "normal")
    part_index = (
        int(round_ctx.get("part_index", 0))
        if kind in ("blitz", "superblitz")
        else 0
    )
    return (sector, kind, part_index)


def _add_question_media(
    catalog: dict[str, CurrentMedia],
    question: Question,
    *,
    scope: MediaScope,
    only_section: Optional[str] = None,
    section_override: Optional[str] = None,
) -> None:
    for item in question.media:
        if only_section is not None and item.section != only_section:
            continue
        descriptor = CurrentMedia(
            media_ref=item.ref,
            type=item.type.value,
            path=item.path,
            scope=scope,
            section=section_override or item.section,
            source_section=item.section,
            order=item.order,
            name=item.path.name,
        )
        catalog[descriptor.media_ref] = descriptor


def current_media_catalog(
    pack: Optional[QuestionPack],
    state: dict,
) -> dict[str, CurrentMedia]:
    """Return the exact media references selectable in the active round/part."""
    key = current_round_key(state)
    if pack is None or key is None:
        return {}

    sector, kind, part_index = key
    try:
        question = pack.get_by_sector(sector)
    except (IndexError, ValueError):
        return {}

    catalog: dict[str, CurrentMedia] = {}
    if kind in ("blitz", "superblitz"):
        _add_question_media(
            catalog,
            question,
            scope="round",
            only_section="question",
            section_override="intro",
        )
        if 0 <= part_index < len(question.parts):
            _add_question_media(catalog, question.parts[part_index], scope="part")
        return catalog

    _add_question_media(catalog, question, scope="round")
    return catalog


def current_author_media(
    pack: Optional[QuestionPack],
    state: dict,
) -> Optional[CurrentAuthorMedia]:
    """Return the author card for the exact active normal question or part."""
    key = current_round_key(state)
    if pack is None or key is None:
        return None

    sector, kind, part_index = key
    try:
        question = pack.get_by_sector(sector)
    except (IndexError, ValueError):
        return None

    scope: MediaScope = "round"
    authored_question = question
    if kind in ("blitz", "superblitz"):
        if not 0 <= part_index < len(question.parts):
            return None
        authored_question = question.parts[part_index]
        scope = "part"

    if sector == 13:
        return CurrentAuthorMedia(
            media_ref=f"author:{authored_question.id}",
            path=None,
            scope=scope,
            name="13-й сектор",
            city=None,
            asset="sector13",
        )

    photo = authored_question.author_photo
    return CurrentAuthorMedia(
        media_ref=f"author:{authored_question.id}",
        path=photo,
        scope=scope,
        name=authored_question.author or "Автор вопроса",
        city=authored_question.city,
        asset="photo" if photo is not None else "fallback",
    )


def next_media_in_section(
    catalog: dict[str, CurrentMedia],
    current_ref: str,
) -> Optional[CurrentMedia]:
    """Return the next ordered item without crossing scope or source section."""
    current = catalog.get(current_ref)
    if current is None:
        return None

    candidates = (
        media
        for media in catalog.values()
        if media.scope == current.scope
        and media.source_section == current.source_section
        and media.order > current.order
    )
    return min(candidates, key=lambda media: media.order, default=None)


def create_media_token_info(
    media: CurrentMedia,
    state: dict,
    *,
    expires_at: float,
) -> dict:
    """Create the server-side record stored behind an opaque media token."""
    return {
        "path": str(media.path),
        "type": media.type,
        "round_key": current_round_key(state),
        "spin_id": state["wheel"].get("spin_id", 0),
        "scope": media.scope,
        "section": media.section,
        "source_section": media.source_section,
        "media_ref": media.media_ref,
        "name": media.name,
        "expires_at": expires_at,
    }


def create_author_media_token_info(
    author: CurrentAuthorMedia,
    state: dict,
    *,
    expires_at: float,
) -> dict:
    """Create a round/part-bound token for a private author preview."""
    return {
        "path": str(author.path) if author.path is not None else None,
        "type": "image",
        "round_key": current_round_key(state),
        "spin_id": state["wheel"].get("spin_id", 0),
        "scope": author.scope,
        "section": "author",
        "source_section": "author",
        "media_ref": author.media_ref,
        "name": author.name,
        "presentation_kind": "author",
        "author_name": author.name,
        "author_city": author.city,
        "author_asset": author.asset,
        "has_photo": author.asset == "photo",
        "expires_at": expires_at,
    }


def media_token_is_current(
    info: dict,
    pack: Optional[QuestionPack],
    state: dict,
    *,
    now_ts: float,
    allow_expired: bool = False,
) -> bool:
    """Validate expiry plus every current-round identity field of a token."""
    if not allow_expired and info.get("expires_at", 0) <= now_ts:
        return False
    if info.get("round_key") != current_round_key(state):
        return False
    if info.get("spin_id") != state["wheel"].get("spin_id", 0):
        return False

    if info.get("presentation_kind") == "author":
        author = current_author_media(pack, state)
        if author is None:
            return False
        return all(
            (
                info.get("path") == (
                    str(author.path) if author.path is not None else None
                ),
                info.get("type") == "image",
                info.get("scope") == author.scope,
                info.get("section") == "author",
                info.get("source_section") == "author",
                info.get("media_ref") == author.media_ref,
                info.get("name") == author.name,
                info.get("author_name") == author.name,
                info.get("author_city") == author.city,
                info.get("author_asset") == author.asset,
                info.get("has_photo") == (author.asset == "photo"),
            )
        )

    media_ref = info.get("media_ref")
    media = current_media_catalog(pack, state).get(media_ref)
    if media is None:
        return False

    return all(
        (
            info.get("path") == str(media.path),
            info.get("type") == media.type,
            info.get("scope") == media.scope,
            info.get("section") == media.section,
            info.get("source_section") == media.source_section,
            info.get("name") == media.name,
        )
    )


def create_shared_media(media_id: str, info: dict, *, has_next: bool = False) -> dict:
    shared = {
        "media_id": media_id,
        "media_ref": info["media_ref"],
        "type": info["type"],
        "section": info["section"],
        "name": info["name"],
        "playback_state": "stopped",
        "position_ms": 0,
        "started_at_ms": None,
        "playback_generation": 0,
        "has_next": has_next,
    }
    if info.get("presentation_kind") == "author":
        shared.update(
            {
                "presentation_kind": "author",
                "author_name": info.get("author_name"),
                "author_city": info.get("author_city"),
                "author_asset": info.get("author_asset"),
                "has_photo": bool(info.get("has_photo")),
            }
        )
    return shared


def _require_playable(shared_media: Optional[dict]) -> dict:
    if shared_media is None:
        raise MediaPlaybackError("no_shared_media")
    if shared_media.get("type") not in ("audio", "video"):
        raise MediaPlaybackError("unsupported_media_type")
    return shared_media


def play_shared_media(shared_media: Optional[dict], *, now_ms: int) -> bool:
    media = _require_playable(shared_media)
    if media.get("playback_state") == "playing":
        return False
    position_ms = max(0, int(media.get("position_ms", 0)))
    media["playback_state"] = "playing"
    media["started_at_ms"] = now_ms - position_ms
    media["playback_generation"] = int(media.get("playback_generation", 0)) + 1
    return True


def pause_shared_media(shared_media: Optional[dict], *, now_ms: int) -> bool:
    media = _require_playable(shared_media)
    if media.get("playback_state") != "playing":
        return False
    started_at_value = media.get("started_at_ms")
    started_at_ms = now_ms if started_at_value is None else int(started_at_value)
    media["position_ms"] = max(0, now_ms - started_at_ms)
    media["started_at_ms"] = None
    media["playback_state"] = "paused"
    media["playback_generation"] = int(media.get("playback_generation", 0)) + 1
    return True


def stop_shared_media(shared_media: Optional[dict]) -> bool:
    media = _require_playable(shared_media)
    changed = (
        media.get("playback_state") != "stopped"
        or int(media.get("position_ms", 0)) != 0
    )
    media["playback_state"] = "stopped"
    media["position_ms"] = 0
    media["started_at_ms"] = None
    if changed:
        media["playback_generation"] = int(media.get("playback_generation", 0)) + 1
    return changed


def complete_shared_media(
    shared_media: Optional[dict],
    *,
    expected_generation: int,
) -> bool:
    """Accept a natural end only for the exact currently playing generation."""
    media = _require_playable(shared_media)
    if media.get("playback_state") != "playing":
        return False
    if int(media.get("playback_generation", 0)) != expected_generation:
        return False
    return stop_shared_media(media)
