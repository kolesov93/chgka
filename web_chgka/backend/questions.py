"""
Question models and parser for ЧГК game.

Question format: Markdown files with YAML frontmatter.
See fixtures/sample_questions for examples.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


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

