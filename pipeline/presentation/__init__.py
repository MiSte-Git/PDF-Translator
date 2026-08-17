"""Loss-minimising OOXML support for PowerPoint presentations."""

from pipeline.presentation.base import (
    OverflowFinding,
    OverflowRegression,
    PresentationParagraph,
    PresentationRun,
    PresentationTextContainer,
    RunFormatting,
)
from pipeline.presentation.pptx_engine import PptxEngine
from pipeline.presentation.translate_presentation import (
    PresentationTranslationStats,
    collect_translatable_html,
    translate_presentation,
)

__all__ = [
    "OverflowFinding",
    "OverflowRegression",
    "PptxEngine",
    "PresentationParagraph",
    "PresentationRun",
    "PresentationTextContainer",
    "RunFormatting",
    "PresentationTranslationStats",
    "collect_translatable_html",
    "translate_presentation",
]
