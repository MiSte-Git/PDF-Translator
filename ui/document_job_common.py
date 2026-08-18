"""Format-agnostic pieces shared by every per-format UI job module
(ui/pptx_job.py, ui/word_job.py, ui/pdf_job.py, ui/image_job.py).

Deliberately small: provider construction, destination safety, and the
conflict-error type are the only parts that don't depend on which document
format is being translated. Everything format-specific (which engine to
open, which translate_*() function to call, what a QA report should say)
stays in that format's own job module rather than being folded into one
generic "document job" abstraction here - PPTX's overflow-risk comparison
and Word's header/footer/break-marker concerns don't map onto each other
cleanly enough to be worth forcing into a shared code path.

OCR_ENGINE_FACTORIES/INPAINTING_BACKEND_FACTORIES (RoadMap.md Phase 3) live
here rather than in pipeline/images/ - mirrors PROVIDER_FACTORIES: the
mapping from a UI-facing string key to a concrete backend class is a UI-
layer concern (which options the dropdown/checkbox offers), not something
pipeline/images/ocr.py or pipeline/images/inpainting.py themselves need to
know about. Placed here (not in ui/image_job.py) specifically so the
planned embedding of the same OCR/Inpainting selection into PDF/Word/PPTX
jobs (RoadMap.md Phase 3, still open) can import from this already-shared
module instead of reaching into ui/image_job.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pipeline.images.inpainting import BoxOverlayBackend, CvInpaintingBackend, InpaintingBackend
from pipeline.images.ocr import OcrEngine, TesseractOcrEngine
from pipeline.translation.base import TranslationProvider
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from pipeline.translation.openai_provider import OpenAIProvider

PROVIDER_FACTORIES: dict[str, Callable[[], TranslationProvider]] = {
    "deepl": DeepLProvider,
    "google": GoogleTranslateProvider,
    "openai": OpenAIProvider,
    "grok": GrokProvider,
}

OCR_ENGINE_FACTORIES: dict[str, Callable[[], OcrEngine]] = {
    "tesseract": TesseractOcrEngine,
    # Cloud-OCR-Backend folgt als zweiter Eintrag (RoadMap.md Phase 3,
    # konkreter Anbieter noch offen) - siehe ocr_engine_available() unten
    # für die Verfügbarkeitsprüfung, die dann auch für diesen Eintrag
    # gilt.
}

INPAINTING_BACKEND_FACTORIES: dict[str, Callable[[], InpaintingBackend]] = {
    "box_overlay": BoxOverlayBackend,
    "cv_inpainting": CvInpaintingBackend,
    # GPU-Inpainting (lokal, LaMa) und Cloud-Inpainting (OpenAI) folgen als
    # weitere Einträge - siehe RoadMap.md Phase 3.
}


class DestinationConflictError(ValueError):
    """The chosen output path is unsafe: same as the source, or already
    exists. Raised before any translation API call is made.
    """


def build_provider(name: str) -> TranslationProvider:
    try:
        factory = PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ValueError(f"Unbekannter Übersetzungsanbieter: {name!r}") from exc
    return factory()


def build_ocr_engine(name: str) -> OcrEngine:
    try:
        factory = OCR_ENGINE_FACTORIES[name]
    except KeyError as exc:
        raise ValueError(f"Unbekannte OCR-Engine: {name!r}") from exc
    return factory()


def build_inpainting_backend(name: str) -> InpaintingBackend:
    try:
        factory = INPAINTING_BACKEND_FACTORIES[name]
    except KeyError as exc:
        raise ValueError(f"Unbekanntes Rückschreibe-Backend: {name!r}") from exc
    return factory()


def ocr_engine_available(name: str) -> bool:
    """Whether the OCR engine `name` can actually be used right now -
    checked BEFORE a job starts (ui/analysis.py), mirroring
    ui/settings.py::credential_status() for translation providers. Only
    "tesseract" has a real availability check today (its binary must be
    on PATH, see pipeline.images.ocr.tesseract_available()) - a future
    cloud backend would check for a configured API key instead, the same
    way build_provider()'s providers do lazily on first use.
    """
    if name == "tesseract":
        from pipeline.images.ocr import tesseract_available

        return tesseract_available()
    return name in OCR_ENGINE_FACTORIES


def safe_destination(source: Path, target_lang: str, output_dir: Path | None = None) -> Path:
    """Propose a destination filename that can never collide with the
    source: the target language is always appended, and a numeric suffix is
    added if that name is already taken in the chosen directory. Source and
    destination identity is still re-checked technically in each job
    module's run_*_job()/*.save() before anything is written. Format-
    agnostic (only uses source.suffix), so it's shared as-is rather than
    duplicated per format.
    """
    source = Path(source)
    directory = Path(output_dir) if output_dir is not None else source.parent
    tag = "".join(char for char in target_lang.strip().upper() if char.isalnum()) or "TRANSLATED"
    base_name = f"{source.stem}_{tag}"
    resolved_source = source.resolve()
    candidate = directory / f"{base_name}{source.suffix}"
    counter = 2
    while candidate.exists() or candidate.resolve() == resolved_source:
        candidate = directory / f"{base_name} ({counter}){source.suffix}"
        counter += 1
    return candidate
