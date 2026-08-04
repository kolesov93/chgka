"""Command-line validation for CHGKA question packs."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

from questions import (
    MediaType,
    QuestionPack,
    QuestionParseError,
    QuestionType,
    parse_question_pack,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m validate_pack",
        description="Validate a CHGKA question pack before starting the backend.",
    )
    parser.add_argument("pack_path", type=Path, help="path to the pack directory")
    return parser


def _format_summary(pack: QuestionPack) -> str:
    question_counts = Counter(question.type for question in pack.questions)
    parts = [part for question in pack.questions for part in question.parts]
    media = [item for question in pack.questions for item in question.media]
    media.extend(item for part in parts for item in part.media)
    media_counts = Counter(item.type for item in media)

    return "\n".join(
        (
            f"VALID: {pack.path}",
            (
                f"Questions: {len(pack.questions)} "
                f"(normal: {question_counts[QuestionType.NORMAL]}, "
                f"blitz: {question_counts[QuestionType.BLITZ]}, "
                f"superblitz: {question_counts[QuestionType.SUPERBLITZ]})"
            ),
            f"Parts: {len(parts)}",
            (
                f"Media: {len(media)} "
                f"(image: {media_counts[MediaType.IMAGE]}, "
                f"audio: {media_counts[MediaType.AUDIO]}, "
                f"video: {media_counts[MediaType.VIDEO]})"
            ),
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pack_path = args.pack_path

    try:
        pack_path = pack_path.expanduser().resolve()
        pack = parse_question_pack(pack_path)
    except (QuestionParseError, OSError, RuntimeError) as error:
        print(f"INVALID: {pack_path}", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1

    print(_format_summary(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
