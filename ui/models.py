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
    ico_mode: bool = False
    """Explicit, user-controlled override (the "ICO-Dokument" checkbox in
    ui/app.py, currently WORD mode only - see RoadMap.md): when True, the
    page-1 metadata block of a document of that specific internal type is
    excluded from translation. Never inferred automatically - see
    DocxEngine.open()'s docstring for why the underlying detection used to
    run unconditionally and no longer does."""
    exclude_header: bool = False
    exclude_footer: bool = False
    """PDF-only checkboxes (ui/app.py, mirroring ico_mode's Word-only
    pattern): when True, PyMuPdfEngine.open()'s document-specific template
    file was never used by the direct PDF path (see ui/pdf_job.py's
    docstring); instead run_pdf_job() runs
    pipeline.pdf.template.detect_header_footer_zones() and excludes
    whatever repeating header/footer it finds - a real user's live run
    against a real document had its header translated along with the
    body before this existed."""
    ocr_engine: str = "tesseract"
    inpainting_backend: str = "box_overlay"
    """IMAGES-only dropdowns (ui/app.py, RoadMap.md Phase 3): which
    pipeline.images.ocr.OcrEngine/pipeline.images.inpainting.InpaintingBackend
    ui/image_job.py::run_image_batch_job() should use - see
    ui/document_job_common.py's OCR_ENGINE_FACTORIES/
    INPAINTING_BACKEND_FACTORIES for the valid keys. Kept as plain strings
    here (not the class/Protocol itself) so TranslationRequest stays a
    Qt-independent, trivially comparable/hashable dataclass, exactly like
    every other field on it."""

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        expected = MODE_EXTENSIONS[self.mode]
        if not self.source_paths:
            errors.append("Mindestens eine Quelldatei auswählen.")
        if self.mode != TranslationMode.IMAGES and len(self.source_paths) > 1:
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
    # Live, account-level quota (currently only available for DeepL via
    # DeepLProvider.get_usage()) - authoritative where month_usage/free_tier
    # above are only this app's own local, provider-agnostic approximation.
    # live_character_limit is None both when no live check was possible
    # (live_usage_available False) and when the provider reports no limit
    # for the account (live_usage_available True) - check the flag first.
    live_usage_available: bool = False
    live_characters_used: int | None = None
    live_character_limit: int | None = None

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

