import shutil
from pathlib import Path

import pytest

from questions import QuestionParseError, parse_question, parse_question_pack
from validate_pack import main


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
SAMPLE_DIR = FIXTURES_DIR / "sample_questions"


def _copy_sample_pack(tmp_path: Path) -> Path:
    pack_path = tmp_path / "pack"
    shutil.copytree(SAMPLE_DIR, pack_path)
    return pack_path


def _write_question(folder: Path, media_reference: str) -> None:
    folder.mkdir(parents=True)
    (folder / "media").mkdir()
    (folder / "question.md").write_text(
        "\n".join(
            (
                "---",
                "title: Media path test",
                "---",
                "",
                "# Вопрос",
                f"![image]({media_reference})",
                "",
                "# Ответ",
                "Answer",
            )
        ),
        encoding="utf-8",
    )


def test_cli_prints_sample_pack_summary(capsys):
    assert main([str(SAMPLE_DIR)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        f"VALID: {SAMPLE_DIR.resolve()}\n"
        "Questions: 13 (normal: 11, blitz: 1, superblitz: 1)\n"
        "Parts: 6\n"
        "Media: 9 (image: 5, audio: 2, video: 2)\n"
    )


def test_cli_returns_one_for_missing_pack(tmp_path, capsys):
    missing = tmp_path / "missing"

    assert main([str(missing)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"INVALID: {missing.resolve()}" in captured.err
    assert "does not exist" in captured.err
    assert "Traceback" not in captured.err


def test_cli_returns_two_for_invalid_usage(capsys):
    with pytest.raises(SystemExit) as error:
        main([])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: python -m validate_pack" in captured.err


def test_cli_preserves_sector_context_for_invalid_question(tmp_path, capsys):
    pack_path = _copy_sample_pack(tmp_path)
    (pack_path / "01" / "question.md").unlink()

    assert main([str(pack_path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Failed to parse sector 1" in captured.err
    assert "question.md" in captured.err
    assert "Traceback" not in captured.err


def test_pack_rejects_extra_numeric_sector(tmp_path):
    pack_path = _copy_sample_pack(tmp_path)
    (pack_path / "14").mkdir()

    with pytest.raises(QuestionParseError, match="14|01..13"):
        parse_question_pack(pack_path)


def test_pack_allows_named_auxiliary_directory(tmp_path):
    pack_path = _copy_sample_pack(tmp_path)
    (pack_path / "intro").mkdir()

    assert len(parse_question_pack(pack_path)) == 13


def test_pack_allows_missing_intro_speech(tmp_path):
    pack_path = _copy_sample_pack(tmp_path)
    (pack_path / "intro.md").unlink()

    assert parse_question_pack(pack_path).intro_html is None


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty"),
        (b"\xff\xfe", "UTF-8|binary"),
        (b"![image](intro/photo.jpg)", "Media in intro.md"),
    ],
)
def test_pack_rejects_invalid_intro_speech(tmp_path, content, message):
    pack_path = _copy_sample_pack(tmp_path)
    (pack_path / "intro.md").write_bytes(content)

    with pytest.raises(QuestionParseError, match=message):
        parse_question_pack(pack_path)


def test_pack_rejects_intro_symlink_escape(tmp_path):
    pack_path = _copy_sample_pack(tmp_path)
    outside_intro = tmp_path / "outside.md"
    outside_intro.write_text("Private speech", encoding="utf-8")
    (pack_path / "intro.md").unlink()
    (pack_path / "intro.md").symlink_to(outside_intro)

    with pytest.raises(QuestionParseError, match="inside the pack"):
        parse_question_pack(pack_path)


def test_question_rejects_absolute_media_path(tmp_path):
    external_media = tmp_path / "external.jpg"
    external_media.write_bytes(b"image")
    question_path = tmp_path / "question"
    _write_question(question_path, str(external_media))

    with pytest.raises(QuestionParseError, match="relative|media"):
        parse_question(question_path)


def test_question_rejects_media_path_traversal(tmp_path):
    external_media = tmp_path / "external.jpg"
    external_media.write_bytes(b"image")
    question_path = tmp_path / "question"
    _write_question(question_path, "media/../../external.jpg")

    with pytest.raises(QuestionParseError, match="escapes"):
        parse_question(question_path)


def test_question_rejects_media_symlink_escape(tmp_path):
    external_media = tmp_path / "external.jpg"
    external_media.write_bytes(b"image")
    question_path = tmp_path / "question"
    _write_question(question_path, "media/linked.jpg")
    (question_path / "media" / "linked.jpg").symlink_to(external_media)

    with pytest.raises(QuestionParseError, match="escapes"):
        parse_question(question_path)
