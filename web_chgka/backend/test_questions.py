"""Tests for question parser."""

import pytest
from pathlib import Path

from questions import (
    parse_question,
    parse_question_pack,
    Question,
    QuestionType,
    MediaType,
    QuestionParseError,
)

# Base paths for fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid_questions"
INVALID_DIR = FIXTURES_DIR / "invalid_questions"
SAMPLE_DIR = FIXTURES_DIR / "sample_questions"


class TestQuestionPackParsing:
    def test_parse_sample_pack_has_13_questions(self):
        pack = parse_question_pack(SAMPLE_DIR)
        assert len(pack) == 13
        assert len(pack.questions) == 13
        assert all(isinstance(q, Question) for q in pack.questions)


class TestValidQuestions:
    """Tests for valid question parsing."""
    
    def test_minimal(self):
        """Minimal question with only required fields."""
        q = parse_question(VALID_DIR / "valid_minimal")
        
        assert q.title == "Минимальный вопрос"
        assert q.type == QuestionType.NORMAL
        assert "2 + 2" in q.question_html
        assert "<strong>4</strong>" in q.answer_html
        assert q.author is None
        assert q.comment_html is None
        assert q.sources_html is None
        assert q.media == []
        assert q.parts == []
    
    def test_full(self):
        """Question with all fields present."""
        q = parse_question(VALID_DIR / "valid_full")
        
        assert q.title == "Полный вопрос со всеми полями"
        assert q.author == "Тестовый Автор"
        assert "столицей Франции" in q.question_html
        assert "<strong>Париж</strong>" in q.answer_html
        assert "реке Сене" in q.comment_html
        assert "Энциклопедия" in q.sources_html
    
    def test_all_media(self):
        """Question with all media types in question and answer."""
        q = parse_question(VALID_DIR / "valid_all_media")
        
        # Total media: question (4) + answer (3) = 7
        assert len(q.media) == 7
        assert q.media[0].type == MediaType.IMAGE
        assert q.media[1].type == MediaType.IMAGE
        assert q.media[2].type == MediaType.AUDIO
        assert q.media[3].type == MediaType.VIDEO
        assert q.media[4].type == MediaType.IMAGE
        assert q.media[5].type == MediaType.AUDIO
        assert q.media[6].type == MediaType.VIDEO
        
        # Check that paths are absolute and exist
        for media in q.media:
            assert media.path.is_absolute()
            assert media.path.exists()
        
        # Check placeholders in HTML
        assert "media-placeholder" in q.question_html
        assert "media-placeholder" in q.answer_html

    def test_shared_media_question_and_answer(self):
        """Same media file referenced in both question and answer."""
        q = parse_question(VALID_DIR / "valid_shared_media")

        assert q.type == QuestionType.NORMAL
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.IMAGE
        assert q.media[0].path.name == "shared.jpg"
        assert "media-placeholder" in q.question_html
        assert "media-placeholder" in q.answer_html
    
    def test_blitz(self):
        """Blitz question with 3 sub-questions."""
        q = parse_question(VALID_DIR / "valid_blitz")
        
        assert q.title == "Тестовый блиц"
        assert q.type == QuestionType.BLITZ
        assert q.answer_html is None  # No answer at top level
        assert len(q.parts) == 3
        
        # Check sub-questions
        assert q.parts[0].title == "Сложение"
        assert q.parts[0].author == "Математик"
        assert "<strong>4</strong>" in q.parts[0].answer_html
        
        assert q.parts[1].title == "Вычитание"
        assert q.parts[2].title == "Умножение"
    
    def test_superblitz(self):
        """Superblitz question with 3 sub-questions."""
        q = parse_question(VALID_DIR / "valid_superblitz")
        
        assert q.title == "Тестовый суперблиц"
        assert q.type == QuestionType.SUPERBLITZ
        assert q.answer_html is None
        assert len(q.parts) == 3
        assert q.sources_html is not None
        assert "Атлас мира" in q.sources_html


class TestSampleQuestions:
    """Tests for sample questions from sample_questions folder."""
    
    def test_sample_01_no_media(self):
        """Sample question 01: no media."""
        q = parse_question(SAMPLE_DIR / "01")
        
        assert q.title == "Загадка Эйнштейна"
        assert q.author == "Михаил Савченко"
        assert "Скрипка" in q.answer_html
        assert q.media == []
    
    def test_sample_02_images(self):
        """Sample question 02: images in question and answer."""
        q = parse_question(SAMPLE_DIR / "02")
        
        assert q.title == "Картины и художник"
        assert len(q.media) == 3  # 2 paintings + 1 portrait
        assert all(m.type == MediaType.IMAGE for m in q.media)
    
    def test_sample_03_audio_in_question(self):
        """Sample question 03: audio in question."""
        q = parse_question(SAMPLE_DIR / "03")
        
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.AUDIO
    
    def test_sample_04_blitz(self):
        """Sample question 04: blitz."""
        q = parse_question(SAMPLE_DIR / "04")
        
        assert q.type == QuestionType.BLITZ
        assert len(q.parts) == 3
    
    def test_sample_05_audio_in_answer(self):
        """Sample question 05: audio in answer."""
        q = parse_question(SAMPLE_DIR / "05")
        
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.AUDIO
    
    def test_sample_06_video_in_question(self):
        """Sample question 06: video in question."""
        q = parse_question(SAMPLE_DIR / "06")
        
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.VIDEO
    
    def test_sample_07_superblitz(self):
        """Sample question 07: superblitz."""
        q = parse_question(SAMPLE_DIR / "07")
        
        assert q.type == QuestionType.SUPERBLITZ
        assert len(q.parts) == 3
    
    def test_sample_08_video_in_answer(self):
        """Sample question 08: video in answer."""
        q = parse_question(SAMPLE_DIR / "08")
        
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.VIDEO
    
    def test_sample_09_no_media(self):
        """Sample question 09: no media."""
        q = parse_question(SAMPLE_DIR / "09")
        
        assert q.title == "Литературный псевдоним"
        assert q.type == QuestionType.NORMAL
        assert q.media == []
    
    def test_sample_10_image_in_question(self):
        """Sample question 10: image in question."""
        q = parse_question(SAMPLE_DIR / "10")
        
        assert q.title == "Архитектурное чудо"
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.IMAGE
    
    def test_sample_11_no_media(self):
        """Sample question 11: no media."""
        q = parse_question(SAMPLE_DIR / "11")
        
        assert q.title == "Химический элемент"
        assert q.media == []
    
    def test_sample_12_image_in_question(self):
        """Sample question 12: image in question."""
        q = parse_question(SAMPLE_DIR / "12")
        
        assert q.title == "Спортивный рекорд"
        assert len(q.media) == 1
        assert q.media[0].type == MediaType.IMAGE
    
    def test_sample_13_no_media(self):
        """Sample question 13: special sector."""
        q = parse_question(SAMPLE_DIR / "13")
        
        assert q.title == "Тринадцатый сектор"
        assert q.type == QuestionType.NORMAL
        assert q.media == []


class TestInvalidFileStructure:
    """Tests for invalid file structure."""
    
    def test_no_question_md(self):
        """Folder without question.md."""
        with pytest.raises(QuestionParseError, match="question.md"):
            parse_question(INVALID_DIR / "no_question_md")
    
    def test_empty_file(self):
        """Empty question.md file."""
        with pytest.raises(QuestionParseError, match="empty|пуст"):
            parse_question(INVALID_DIR / "empty_file")
    
    def test_binary_file(self):
        """Binary file instead of markdown."""
        with pytest.raises(QuestionParseError):
            parse_question(INVALID_DIR / "binary_file")


class TestInvalidFrontmatter:
    """Tests for invalid frontmatter."""
    
    def test_no_frontmatter(self):
        """Missing frontmatter block."""
        with pytest.raises(QuestionParseError, match="frontmatter"):
            parse_question(INVALID_DIR / "no_frontmatter")
    
    def test_invalid_yaml(self):
        """Invalid YAML syntax in frontmatter."""
        with pytest.raises(QuestionParseError, match="YAML|yaml"):
            parse_question(INVALID_DIR / "invalid_yaml")
    
    def test_no_title(self):
        """Missing title field."""
        with pytest.raises(QuestionParseError, match="title"):
            parse_question(INVALID_DIR / "no_title")
    
    def test_duplicate_title(self):
        """Duplicate title field in frontmatter."""
        with pytest.raises(QuestionParseError, match="title"):
            parse_question(INVALID_DIR / "duplicate_title")
    
    def test_unknown_type(self):
        """Unknown question type."""
        with pytest.raises(QuestionParseError, match="type|unknown"):
            parse_question(INVALID_DIR / "unknown_type")
    
    def test_duplicate_author(self):
        """Duplicate author field in frontmatter."""
        with pytest.raises(QuestionParseError, match="author"):
            parse_question(INVALID_DIR / "duplicate_author")


class TestInvalidSections:
    """Tests for missing/duplicate sections."""
    
    def test_no_question_section(self):
        """Missing # Вопрос section."""
        with pytest.raises(QuestionParseError, match="Вопрос"):
            parse_question(INVALID_DIR / "no_question_section")
    
    def test_no_answer_section(self):
        """Missing # Ответ section."""
        with pytest.raises(QuestionParseError, match="Ответ"):
            parse_question(INVALID_DIR / "no_answer_section")
    
    def test_duplicate_question(self):
        """Duplicate # Вопрос section."""
        with pytest.raises(QuestionParseError, match="Вопрос"):
            parse_question(INVALID_DIR / "duplicate_question")
    
    def test_duplicate_answer(self):
        """Duplicate # Ответ section."""
        with pytest.raises(QuestionParseError, match="Ответ"):
            parse_question(INVALID_DIR / "duplicate_answer")
    
    def test_duplicate_comment(self):
        """Duplicate # Комментарий section."""
        with pytest.raises(QuestionParseError, match="Комментарий"):
            parse_question(INVALID_DIR / "duplicate_comment")
    
    def test_duplicate_sources(self):
        """Duplicate # Источник section."""
        with pytest.raises(QuestionParseError, match="Источник"):
            parse_question(INVALID_DIR / "duplicate_sources")


class TestInvalidSectionOrder:
    """Tests for wrong section order."""
    
    def test_answer_before_question(self):
        """# Ответ before # Вопрос."""
        with pytest.raises(QuestionParseError, match="порядок|order"):
            parse_question(INVALID_DIR / "wrong_order_answer_before_question")
    
    def test_comment_before_answer(self):
        """# Комментарий before # Ответ."""
        with pytest.raises(QuestionParseError, match="порядок|order"):
            parse_question(INVALID_DIR / "wrong_order_comment_before_answer")
    
    def test_sources_before_comment(self):
        """# Источник before # Комментарий."""
        with pytest.raises(QuestionParseError, match="порядок|order"):
            parse_question(INVALID_DIR / "wrong_order_sources_before_comment")


class TestInvalidMedia:
    """Tests for media validation errors."""
    
    def test_missing_media(self):
        """Reference to non-existent media file."""
        with pytest.raises(QuestionParseError, match="nonexistent|не найден"):
            parse_question(INVALID_DIR / "missing_media")
    
    def test_unused_media(self):
        """Media file exists but not referenced."""
        with pytest.raises(QuestionParseError, match="unused|не использ"):
            parse_question(INVALID_DIR / "unused_media")
    
    def test_unsupported_media_format(self):
        """Unsupported media format (.gif, .txt)."""
        with pytest.raises(QuestionParseError, match="формат|format|поддерж"):
            parse_question(INVALID_DIR / "unsupported_media_format")


class TestInvalidBlitz:
    """Tests for blitz/superblitz validation errors."""
    
    def test_blitz_no_parts(self):
        """Blitz without sub-question folders."""
        with pytest.raises(QuestionParseError, match="01|02|03|подвопрос|part"):
            parse_question(INVALID_DIR / "blitz_no_parts")
    
    def test_blitz_wrong_part_count(self):
        """Blitz with wrong number of parts (not 3)."""
        with pytest.raises(QuestionParseError, match="3|три|three"):
            parse_question(INVALID_DIR / "blitz_wrong_part_count")
    
    def test_blitz_with_answer(self):
        """Blitz with # Ответ at top level."""
        with pytest.raises(QuestionParseError, match="Ответ|answer"):
            parse_question(INVALID_DIR / "blitz_with_answer")
    
    def test_blitz_nested(self):
        """Blitz sub-question has its own parts."""
        with pytest.raises(QuestionParseError, match="вложен|nested|part"):
            parse_question(INVALID_DIR / "blitz_nested")
    
    def test_blitz_part_wrong_type(self):
        """Blitz sub-question has type: blitz."""
        with pytest.raises(QuestionParseError, match="type|тип"):
            parse_question(INVALID_DIR / "blitz_part_wrong_type")
    
    def test_normal_with_parts(self):
        """Normal question with sub-question folders."""
        with pytest.raises(QuestionParseError, match="01|02|03|подпапк|subfolder"):
            parse_question(INVALID_DIR / "normal_with_parts")

