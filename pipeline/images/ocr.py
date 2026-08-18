"""OCR-Backend-Abstraktion für die Bildübersetzung (RoadMap.md Phase 3).

Spiegelt pipeline/translation/base.py::TranslationProvider bewusst 1:1:
ein Protocol (`OcrEngine`), gegen das mehrere austauschbare
Implementierungen laufen - analog zu DeepL/Google/OpenAI/Grok bei der
Übersetzung. Verfügbarkeit wird jeweils VOR dem eigentlichen Lauf geprüft
(siehe `tesseract_available()` unten und ui/settings.py::
credential_status() für das Übersetzungs-Pendant), damit ein Nutzer ohne
installiertes Tesseract das im UI als ausgegraute/deaktivierte Option
sieht statt mitten im Lauf eine kryptische Exception zu bekommen.

Aktuell ein Backend (TesseractOcrEngine, lokal). Ein Cloud-OCR-Backend
ist als zweite OcrEngine-Implementierung vorgesehen (siehe RoadMap.md),
konkreter Anbieter noch offen - der Grund für die Protocol-Abstraktion
hier statt eines direkten Tesseract-Aufrufs ist genau, dass ein
zusätzliches Backend später ergänzt werden kann, ohne dass Aufrufer
(ui/image_job.py) sich ändern müssen.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class OcrError(Exception):
    """Raised when an OCR engine fails: missing binary, unreadable image,
    or an unexpected recognizer error. Mirrors
    pipeline.translation.base.TranslationError - callers handle OCR
    failures uniformly regardless of which engine is in use.
    """


@dataclass(frozen=True)
class OcrTextRegion:
    """One recognized text line within an image, in pixel coordinates of
    the ORIGINAL image (top-left origin - the convention Pillow, OpenCV
    and PyMuPDF's pixel-space all share).

    `confidence` is the engine's own average word-confidence for this
    line (0-100, Tesseract's scale - not normalized further since there
    is currently only one engine; a future second backend may need its
    own normalization, not this dataclass's job). Not used for filtering
    yet, kept for a future QA report column - mirrors how
    PyMuPdfEngine's TextBlock keeps span-level detail around even before
    every consumer needs it.
    """

    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float


@runtime_checkable
class OcrEngine(Protocol):
    """Minimal interface every OCR engine (Tesseract/future cloud
    backends) must implement - mirrors TranslationProvider.translate()'s
    role for the translation side."""

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        """Return recognized text lines for the image at `image_path`, in
        reading order (top-to-bottom, matching Tesseract's own block/
        paragraph/line traversal order).

        `language` is an engine-specific hint (Tesseract expects its
        3-letter code, e.g. "eng" or "deu") - None lets the engine fall
        back to its own default.
        """
        ...


def tesseract_available() -> bool:
    """Whether the local Tesseract binary can be found on PATH.

    Checked BEFORE a job starts (ui/analysis.py, mirrors
    ui/settings.py::credential_status() for the translation providers) so
    a missing installation surfaces as a disabled/greyed UI option
    instead of a mid-run crash - relevant in particular for a possible
    future standalone build, where Tesseract may not be present at all
    (see RoadMap.md Phase 3).
    """
    return shutil.which("tesseract") is not None


class TesseractOcrEngine:
    """OcrEngine backed by the local Tesseract binary via pytesseract.

    pytesseract is imported lazily inside recognize(), not at module
    level - mirrors how ui/analysis.py imports PyMuPDF lazily inside the
    PDF branch, so the other UI modes stay usable even in an environment
    where the (optional, listed in requirements-ocr.txt) pytesseract
    package is not installed.
    """

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        if not tesseract_available():
            raise OcrError(
                "Tesseract-Binary wurde nicht gefunden (PATH). Installation "
                "prüfen oder eine Cloud-OCR-Engine wählen."
            )
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise OcrError(
                f"OCR-Abhängigkeit fehlt: {exc}. Siehe requirements-ocr.txt."
            ) from exc

        try:
            with Image.open(image_path) as image:
                data = pytesseract.image_to_data(
                    image,
                    lang=language or "eng",
                    output_type=pytesseract.Output.DICT,
                )
        except Exception as exc:  # tesseract binary/runtime failure, corrupt image, ...
            raise OcrError(f"Tesseract-Erkennung fehlgeschlagen: {exc}") from exc

        return _group_words_into_lines(data)


def _group_words_into_lines(data: dict) -> list[OcrTextRegion]:
    """pytesseract.image_to_data() (Output.DICT) returns ONE ROW PER WORD,
    each tagged with its (block_num, par_num, line_num) position in
    Tesseract's own hierarchical page/block/paragraph/line/word scan.
    Grouping consecutive words that share the same (block, par, line) key
    reconstructs a single reading-order text LINE per group - the same
    granularity PyMuPdfEngine's TextBlock lines represent for PDFs,
    rather than exposing one OcrTextRegion per single word (which would
    make e.g. inpainting box merging or QA display far noisier than
    necessary).

    Insertion order of the resulting dict already matches reading order:
    image_to_data() itself iterates block-by-block, then line-by-line
    within a block, so the FIRST time a given (block, par, line) key is
    seen is always in document reading order - no separate sort needed.
    """
    lines: dict[tuple[int, int, int], list[int]] = {}
    word_count = len(data["text"])
    for i in range(word_count):
        text = data["text"][i]
        if not text or not text.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(i)

    regions: list[OcrTextRegion] = []
    for indices in lines.values():
        words = [data["text"][i] for i in indices]
        x0 = min(data["left"][i] for i in indices)
        y0 = min(data["top"][i] for i in indices)
        x1 = max(data["left"][i] + data["width"][i] for i in indices)
        y1 = max(data["top"][i] + data["height"][i] for i in indices)
        # Tesseract reports -1 confidence for non-word rows; none should
        # remain after the text.strip() filter above, but guard anyway
        # rather than let a stray -1 drag the average down.
        confidences = [float(data["conf"][i]) for i in indices if float(data["conf"][i]) >= 0]
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        regions.append(
            OcrTextRegion(
                text=" ".join(words), x=x0, y=y0, width=x1 - x0, height=y1 - y0,
                confidence=confidence,
            )
        )
    return regions
