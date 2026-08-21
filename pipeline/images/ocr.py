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


# Ratio (horizontal gap between two adjacent words / the taller of their
# two heights) beyond which two words Tesseract grouped into the SAME
# (block, par, line) are nonetheless split into two separate OcrTextRegion
# - added after a real user-reported infographic (RoadMap.md/Backlog.md,
# 21.08.2026) with a two-column layout (main content + a right-hand
# sidebar box): Tesseract's page segmentation doesn't understand the
# columns, so on several rows it read straight across the gap between
# them, gluing two logically unrelated fragments - e.g. a left-column
# ledger label and the right sidebar's heading, dozens to hundreds of
# pixels apart - into one (block, par, line) group with a single giant
# bounding box spanning both. Translated as one string, that produced
# garbled, contextless nonsense far worse than either fragment translated
# on its own (see translate_image()'s docstring on garbage in tends to
# stay garbage out); drawn back as one oversized box, it also overlapped
# whatever sat between the two original fragments - a DIFFERENT root
# cause than pipeline.images.translate_image.DEFAULT_MAX_HEIGHT_RATIO's
# icon-inflated-height case, addressed here at the source instead of
# downstream.
#
# 2.5 was picked by inspecting this one real image's actual word gaps:
# every genuine single-column line's largest internal word gap stayed
# under 2.2x that gap's own text height (normal word/punctuation spacing,
# even in a wide letter-spaced headline), while every column-merged
# line's SMALLEST such gap was 3.4x or more - a clean separation with
# margin on both sides, not a broadly validated cutoff (same caveat as
# DEFAULT_MIN_OCR_CONFIDENCE/DEFAULT_MAX_HEIGHT_RATIO in translate_image.py).
_MAX_WORD_GAP_RATIO = 2.5


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

    Each group is further split wherever two adjacent words are further
    apart than _MAX_WORD_GAP_RATIO allows (see that constant's docstring)
    - Tesseract's (block, par, line) key alone is not a reliable "these
    words belong on one visual line" signal once a multi-column layout is
    involved, so a single key can still legitimately yield more than one
    OcrTextRegion here.

    Insertion order of the resulting dict already matches reading order:
    image_to_data() itself iterates block-by-block, then line-by-line
    within a block, so the FIRST time a given (block, par, line) key is
    seen is always in document reading order - no separate sort needed;
    a key's own gap-split sub-regions are emitted left-to-right.
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
        regions.extend(_split_by_horizontal_gap(data, indices))
    return regions


def _split_by_horizontal_gap(data: dict, indices: list[int]) -> list[OcrTextRegion]:
    """Split one Tesseract (block, par, line) word-index group into one or
    more left-to-right OcrTextRegion clusters, breaking wherever the
    horizontal gap between two adjacent words exceeds _MAX_WORD_GAP_RATIO
    times the taller of the two words' heights (see that constant's
    docstring). A group with no such gap returns exactly one region -
    identical to _group_words_into_lines()'s pre-split behaviour."""
    ordered = sorted(indices, key=lambda i: data["left"][i])
    clusters: list[list[int]] = [[ordered[0]]]
    for prev_index, index in zip(ordered, ordered[1:]):
        prev_right = data["left"][prev_index] + data["width"][prev_index]
        gap = data["left"][index] - prev_right
        local_height = max(data["height"][prev_index], data["height"][index], 1)
        if gap > _MAX_WORD_GAP_RATIO * local_height:
            clusters.append([])
        clusters[-1].append(index)
    return [_region_from_word_indices(data, cluster) for cluster in clusters]


def _region_from_word_indices(data: dict, indices: list[int]) -> OcrTextRegion:
    """Build one OcrTextRegion from a cluster of word indices already
    established to belong together (a whole gap-split group, or a group
    that never needed splitting) - the shared bounding-box/confidence
    computation _split_by_horizontal_gap() calls once per cluster."""
    words = [data["text"][i] for i in indices]
    x0 = min(data["left"][i] for i in indices)
    y0 = min(data["top"][i] for i in indices)
    x1 = max(data["left"][i] + data["width"][i] for i in indices)
    y1 = max(data["top"][i] + data["height"][i] for i in indices)
    # Tesseract reports -1 confidence for non-word rows; none should
    # remain after _group_words_into_lines()'s text.strip() filter, but
    # guard anyway rather than let a stray -1 drag the average down.
    confidences = [float(data["conf"][i]) for i in indices if float(data["conf"][i]) >= 0]
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return OcrTextRegion(
        text=" ".join(words), x=x0, y=y0, width=x1 - x0, height=y1 - y0,
        confidence=confidence,
    )
