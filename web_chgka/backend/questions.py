"""
Question models and parser for ЧГК game.

Question format: Markdown files with YAML frontmatter.
See fixtures/sample_questions for examples.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import re


class QuestionType(Enum):
    NORMAL = "normal"
    BLITZ = "blitz"
    SUPERBLITZ = "superblitz"


class MediaType(Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class Media:
    """Media attachment (image, audio, or video)."""
    type: MediaType
    path: Path  # absolute path to file


@dataclass
class Question:
    """
    A single question.
    
    For blitz/superblitz, the top-level question contains intro text
    and `parts` contains the actual sub-questions.
    """
    # Required
    title: str
    question_html: str  # markdown converted to HTML with media placeholders
    
    # Required for normal questions, None for blitz/superblitz top-level
    answer_html: Optional[str] = None
    
    # Optional metadata
    author: Optional[str] = None
    comment_html: Optional[str] = None
    sources_html: Optional[str] = None
    
    # Media extracted from markdown (referenced by placeholders in HTML)
    question_media: list[Media] = field(default_factory=list)
    answer_media: list[Media] = field(default_factory=list)
    
    # Question type
    type: QuestionType = QuestionType.NORMAL
    
    # Sub-questions for blitz/superblitz
    parts: list["Question"] = field(default_factory=list)


class QuestionParseError(Exception):
    """Raised when question parsing fails."""
    pass


_FRONTMATTER_DELIM = "---"
_SECTION_TITLES = ("Вопрос", "Ответ", "Комментарий", "Источник")
_SECTION_ORDER = {name: i for i, name in enumerate(_SECTION_TITLES)}

_MEDIA_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")

_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
_AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
_VIDEO_EXTS = {".mp4", ".webm"}


def _read_text_file(path: Path) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError as e:
        raise QuestionParseError(f"question.md not found: {path}") from e
    if not data or data.strip() == b"":
        raise QuestionParseError("question.md is empty")
    if b"\x00" in data:
        raise QuestionParseError("question.md looks like binary data")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise QuestionParseError("question.md is not valid UTF-8 (binary?)") from e


def _parse_frontmatter(md: str) -> tuple[dict[str, str], str]:
    # Must start with '---'
    lines = md.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise QuestionParseError("Missing YAML frontmatter (expected leading ---)")

    # Find closing '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_DELIM:
            end_idx = i
            break
    if end_idx is None:
        raise QuestionParseError("Invalid YAML frontmatter: missing closing ---")

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")

    # Minimal YAML: only "key: value" scalar pairs (no sequences, no maps).
    fm: dict[str, str] = {}
    for raw in fm_lines:
        line = raw.strip()
        if not line:
            continue
        if ":" not in line:
            raise QuestionParseError("Invalid YAML in frontmatter")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise QuestionParseError("Invalid YAML in frontmatter")
        if key in fm:
            raise QuestionParseError(f"Duplicate field in frontmatter: {key}")
        # Reject YAML structures; we support only plain scalars.
        if value.startswith(("[", "{", "-")):
            raise QuestionParseError("Invalid YAML in frontmatter")
        if any(tok in value for tok in ("[", "]", "{", "}", "\t")):
            # Keeps fixtures like "author: [некорректный yaml" invalid
            raise QuestionParseError("Invalid YAML in frontmatter")
        fm[key] = value

    return fm, body


def _split_sections(body_md: str) -> tuple[dict[str, str], list[str]]:
    """
    Split markdown body into sections by '# <Title>' headings.
    Returns (sections, order).
    """
    sections: dict[str, list[str]] = {}
    order: list[str] = []
    current: Optional[str] = None

    for raw_line in body_md.splitlines():
        line = raw_line.rstrip("\n")
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            name = m.group(1).strip()
            if name in _SECTION_ORDER:
                if name in sections:
                    raise QuestionParseError(f"Duplicate section: {name}")
                sections[name] = []
                order.append(name)
                current = name
                continue
        if current is not None:
            sections[current].append(line)

    # Convert lists to strings
    sections_str: dict[str, str] = {k: "\n".join(v).strip() for k, v in sections.items()}
    return sections_str, order


def _validate_section_order(order: list[str]) -> None:
    if not order:
        return
    last = -1
    for name in order:
        idx = _SECTION_ORDER[name]
        if idx < last:
            raise QuestionParseError("Invalid section order (expected: Вопрос -> Ответ -> Комментарий -> Источник)")
        last = idx


def _infer_media_type(alt: str, path: str) -> MediaType:
    alt_norm = alt.strip().lower()
    suffix = Path(path).suffix.lower()
    if alt_norm == "audio":
        return MediaType.AUDIO
    if alt_norm == "video":
        return MediaType.VIDEO
    # fallback by extension
    if suffix in _IMAGE_EXTS:
        return MediaType.IMAGE
    if suffix in _AUDIO_EXTS:
        return MediaType.AUDIO
    if suffix in _VIDEO_EXTS:
        return MediaType.VIDEO
    raise QuestionParseError(f"Unsupported media format: {path}")


def _extract_media_and_replace(md: str, base_folder: Path) -> tuple[str, list[Media], set[Path]]:
    media_list: list[Media] = []
    used_rel: set[Path] = set()

    def repl(match: re.Match) -> str:
        alt = match.group("alt")
        rel = match.group("path").strip()
        rel_path = Path(rel)
        # Only treat local paths
        if "://" in rel:
            return match.group(0)
        mtype = _infer_media_type(alt, rel)
        full = (base_folder / rel_path).resolve()
        if not full.exists():
            raise QuestionParseError(f"Media file not found: {rel}")
        media_list.append(Media(type=mtype, path=full))
        used_rel.add(rel_path)
        # Placeholder for later rendering by admin UI
        return (
            f'<span class="media-placeholder" data-media-type="{mtype.value}" '
            f'data-media-path="{rel}"></span>'
        )

    new_md = _MEDIA_RE.sub(repl, md)
    return new_md, media_list, used_rel


def _simple_markdown_to_html(md: str) -> str:
    # Very small subset sufficient for fixtures/tests.
    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md, flags=re.DOTALL)
    # Bullet lists (- item)
    lines = html.splitlines()
    out: list[str] = []
    in_ul = False
    for line in lines:
        m = re.match(r"^\s*-\s+(.*)$", line)
        if m:
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{m.group(1).strip()}</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if line.strip() == "":
                continue
            out.append(f"<p>{line}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def _validate_media_usage(base_folder: Path, used_rel_paths: set[Path]) -> None:
    media_dir = base_folder / "media"
    if not media_dir.exists():
        if used_rel_paths:
            # referenced media but no media dir; treated as missing earlier, but keep defensive
            missing = next(iter(used_rel_paths))
            raise QuestionParseError(f"Media file not found: {missing.as_posix()}")
        return

    existing_files: set[Path] = set()
    for p in media_dir.rglob("*"):
        if p.is_file():
            existing_files.add(Path("media") / p.relative_to(media_dir))

    # If there are files with unsupported formats at all, fail fast (fixture expects this)
    for rel in sorted(existing_files):
        suffix = rel.suffix.lower()
        if suffix and suffix not in (_IMAGE_EXTS | _AUDIO_EXTS | _VIDEO_EXTS):
            raise QuestionParseError(f"Unsupported media format: {rel.as_posix()}")

    unused = existing_files - used_rel_paths
    if unused:
        one = sorted(unused)[0].as_posix()
        raise QuestionParseError(f"Unused media file: {one}")


def _parse_one_question_folder(folder: Path) -> Question:
    qmd = folder / "question.md"
    if not qmd.exists():
        raise QuestionParseError(f"question.md not found in {folder}")

    md = _read_text_file(qmd)
    fm, body = _parse_frontmatter(md)

    title = fm.get("title")
    if not title:
        raise QuestionParseError("Missing required field: title")

    qtype_raw = fm.get("type", "normal").strip().lower()
    try:
        qtype = QuestionType(qtype_raw)
    except ValueError as e:
        raise QuestionParseError(f"Unknown question type: {qtype_raw}") from e

    author = fm.get("author")

    sections, order = _split_sections(body)
    _validate_section_order(order)

    if "Вопрос" not in sections:
        raise QuestionParseError("Missing section: Вопрос")

    used_rel_all: set[Path] = set()

    def _render_section(section_md: Optional[str]) -> tuple[Optional[str], list[Media], set[Path]]:
        if section_md is None:
            return None, [], set()
        md_with_ph, media, used_rel = _extract_media_and_replace(section_md, folder)
        return _simple_markdown_to_html(md_with_ph), media, used_rel

    question_html, q_media, used_rel_q = _render_section(sections.get("Вопрос"))
    if question_html is None:
        # Should be unreachable because we validate "Вопрос" presence above.
        raise QuestionParseError("Missing section: Вопрос")
    used_rel_all |= used_rel_q

    answer_html, a_media, used_rel_a = _render_section(sections.get("Ответ"))
    used_rel_all |= used_rel_a

    comment_html, _c_media, used_rel_c = _render_section(sections.get("Комментарий"))
    used_rel_all |= used_rel_c

    sources_html, _s_media, used_rel_s = _render_section(sections.get("Источник"))
    used_rel_all |= used_rel_s

    # Validate media folder contents vs references
    _validate_media_usage(folder, used_rel_all)

    return Question(
        title=title,
        question_html=question_html,
        answer_html=answer_html,
        author=author,
        comment_html=comment_html,
        sources_html=sources_html,
        question_media=q_media,
        answer_media=a_media,
        type=qtype,
        parts=[],
    )


def _part_dirs(folder: Path) -> list[Path]:
    return [folder / f"{i:02d}" for i in (1, 2, 3)]


def _existing_part_dirs(folder: Path) -> list[Path]:
    return [p for p in _part_dirs(folder) if p.exists() and p.is_dir()]


def parse_question(folder: Path) -> Question:
    """
    Parse a question from a folder.
    
    Args:
        folder: Path to question folder containing question.md and optional media/
        
    Returns:
        Parsed Question object
        
    Raises:
        QuestionParseError: If the question format is invalid
    """
    folder = Path(folder)
    if not folder.exists() or not folder.is_dir():
        raise QuestionParseError(f"Question folder does not exist: {folder}")

    q = _parse_one_question_folder(folder)
    existing_parts = _existing_part_dirs(folder)

    if q.type == QuestionType.NORMAL:
        if existing_parts:
            raise QuestionParseError("Normal question cannot have subfolders 01/02/03")
        if q.answer_html is None:
            raise QuestionParseError("Missing section: Ответ")
        return q

    # Blitz / superblitz
    if q.answer_html is not None:
        raise QuestionParseError("Blitz question must not have an answer at top level")
    if not existing_parts:
        raise QuestionParseError("Blitz question must have sub-questions in 01/02/03 folders")
    if len(existing_parts) != 3:
        raise QuestionParseError("Blitz question must have exactly 3 parts (01/02/03)")

    parts: list[Question] = []
    for p in _part_dirs(folder):
        if not p.exists() or not p.is_dir():
            raise QuestionParseError("Blitz question must have exactly 3 parts (01/02/03)")
        part_q = _parse_one_question_folder(p)
        if part_q.type != QuestionType.NORMAL:
            raise QuestionParseError("Blitz part has invalid type (must be normal)")
        if part_q.answer_html is None:
            raise QuestionParseError("Missing section: Ответ")
        if _existing_part_dirs(p):
            raise QuestionParseError("Nested parts are not allowed")
        parts.append(part_q)

    q.parts = parts
    return q


@dataclass
class QuestionPack:
    """
    A pack of 13 questions for a game.
    
    Questions are ordered by sector number (index 0 = sector 1).
    """
    questions: list[Question]
    path: Path  # path to the pack folder
    
    def get_by_sector(self, sector: int) -> Question:
        """Get question by sector number (1-13)."""
        if not 1 <= sector <= 13:
            raise ValueError(f"Sector must be 1-13, got {sector}")
        return self.questions[sector - 1]
    
    def __len__(self) -> int:
        return len(self.questions)


def parse_question_pack(pack_folder: Path) -> QuestionPack:
    """
    Parse a question pack from a folder containing 13 question subfolders: 01..13.

    Args:
        pack_folder: Path to pack folder

    Returns:
        QuestionPack with questions ordered by sector (index 0 = sector 1)

    Raises:
        QuestionParseError: If the pack structure is invalid or any question fails to parse.
    """
    pack_folder = Path(pack_folder)
    if not pack_folder.exists() or not pack_folder.is_dir():
        raise QuestionParseError(f"Pack folder does not exist: {pack_folder}")

    questions: list[Question] = []
    for sector in range(1, 14):
        qdir = pack_folder / f"{sector:02d}"
        if not qdir.exists() or not qdir.is_dir():
            raise QuestionParseError(f"Missing question folder for sector {sector}: {qdir}")
        try:
            questions.append(parse_question(qdir))
        except QuestionParseError as e:
            raise QuestionParseError(f"Failed to parse sector {sector} ({qdir}): {e}") from e

    return QuestionPack(questions=questions, path=pack_folder.resolve())

