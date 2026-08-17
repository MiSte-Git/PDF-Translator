"""UI-facing data model, deliberately independent from Qt."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TranslationMode(str, Enum):
    PDF = "pdf"
    PRESENTATION = "presentation"
    WORD = "word"
    IMAGES = "images"


class EmbeddedImageMode(str, Enum):
    NONE = "none"
    SELECTED = "selected"
    ALL = "all"


MODE_EXTENSIONS = {
    TranslationMode.PDF: {".pdf"},
    TranslationMode.PRESENTATION: {".pptx"},
    TranslationMode.WORD: {".docx"},
    TranslationMode.IMAGES: {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"},
}


@dataclass(frozen=True)
class TranslationRequest:
    mode: TranslationMode
    source_paths: tuple[Path, ...]
    provider: str = "deepl"
    source_language: str | None = None
    target_language: str = "DE"
    embedded_images: EmbeddedImageMode = EmbeddedImageMode.NONE
    protected_terms: tuple[str, ...] = ()

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        expected = MODE_EXTENSIONS[self.mode]
        if not self.source_paths:
            errors.append("Mindestens eine Quelldatei auswählen.")
        if self.mode is not TranslationMode.IMAGES and len(self.source_paths) > 1:
            errors.append("Für diesen Modus kann nur eine Quelldatei gewählt werden.")
        for path in self.source_paths:
            if not path.is_file():
                errors.append(f"Datei nicht gefunden: {path}")
            elif path.suffix.lower() not in expected:
                errors.append(
                    f"{path.name} passt nicht zum gewählten Modus "
                    f"({', '.join(sorted(expected))})."
                )
        if not self.target_language.strip():
            errors.append("Zielsprache fehlt.")
        return errors


@dataclass(frozen=True)
class CostSummary:
    provider: str
    characters: int
    month_usage: int
    free_tier: int
    estimated_cost_usd: float
    max_chars_per_run: int

    @property
    def within_run_limit(self) -> bool:
        return self.characters <= self.max_chars_per_run


@dataclass(frozen=True)
class AnalysisResult:
    mode: TranslationMode
    files: int
    units: int
    unit_label: str
    text_characters: int
    embedded_images: int
    selected_image_candidates: int
    ocr_required: bool
    cost: CostSummary
    warnings: tuple[str, ...] = field(default_factory=tuple)

