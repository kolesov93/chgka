"""Assign explicit UUIDs to every question file in an existing valid pack."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import uuid
from typing import Callable

from questions import QuestionParseError, parse_question_pack


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m assign_question_ids",
        description="Assign missing UUIDs to every question.md in a CHGKA pack.",
    )
    parser.add_argument("pack_path", type=Path, help="path to the pack directory")
    return parser


def _question_files(pack_path: Path) -> list[Path]:
    files: list[Path] = []
    for sector in range(1, 14):
        sector_path = pack_path / f"{sector:02d}"
        files.append(sector_path / "question.md")
        for part in range(1, 4):
            part_file = sector_path / f"{part:02d}" / "question.md"
            if part_file.is_file():
                files.append(part_file)
    return files


def _frontmatter_lines(content: str, path: Path) -> tuple[list[str], int]:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise QuestionParseError(f"Missing YAML frontmatter in {path}")
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        raise QuestionParseError(f"Invalid YAML frontmatter in {path}: missing closing ---")
    return lines, closing_index


def assign_question_ids(
    pack_path: Path,
    *,
    id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
) -> int:
    pack_path = Path(pack_path).expanduser().resolve()
    # Validate the complete pack before modifying any file. Existing IDs are
    # still checked for canonical UUID format and duplicates.
    parse_question_pack(pack_path, require_ids=False)

    changes: dict[Path, str] = {}
    known_ids: set[str] = set()
    missing: list[tuple[Path, list[str], int | None]] = []

    for path in _question_files(pack_path):
        content = path.read_text(encoding="utf-8")
        lines, closing_index = _frontmatter_lines(content, path)
        id_line_index = next(
            (
                index
                for index, line in enumerate(lines[1:closing_index], start=1)
                if ":" in line and line.split(":", 1)[0].strip() == "id"
            ),
            None,
        )
        raw_id = (
            lines[id_line_index].split(":", 1)[1].strip()
            if id_line_index is not None
            else None
        )
        if raw_id:
            canonical = str(uuid.UUID(raw_id))
            if raw_id != canonical:
                raise QuestionParseError(
                    f"Question id in {path} must use canonical format: {canonical}"
                )
            if canonical in known_ids:
                raise QuestionParseError(f"Duplicate question id: {canonical}")
            known_ids.add(canonical)
            continue
        missing.append((path, lines, id_line_index))

    for path, lines, id_line_index in missing:
        try:
            question_id = str(uuid.UUID(str(id_factory())))
        except (AttributeError, TypeError, ValueError) as error:
            raise QuestionParseError("ID generator returned an invalid UUID") from error
        while question_id in known_ids:
            try:
                question_id = str(uuid.UUID(str(id_factory())))
            except (AttributeError, TypeError, ValueError) as error:
                raise QuestionParseError("ID generator returned an invalid UUID") from error
        known_ids.add(question_id)
        newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
        if id_line_index is None:
            lines.insert(1, f"id: {question_id}{newline}")
        else:
            lines[id_line_index] = f"id: {question_id}{newline}"
        changes[path] = "".join(lines)

    for path, content in changes.items():
        path.write_text(content, encoding="utf-8", newline="")

    if changes:
        parse_question_pack(pack_path)
    return len(changes)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pack_path = args.pack_path
    try:
        assigned = assign_question_ids(pack_path)
    except (QuestionParseError, OSError, ValueError) as error:
        print(f"INVALID: {pack_path.expanduser().resolve()}", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1
    print(f"ASSIGNED: {assigned}")
    print(f"PACK: {pack_path.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
