"""Read-only document analysis used by the cost confirmation UI."""
from __future__ import annotations

import zipfile
from pathlib import Path

from pipeline.presentation.pptx_engine import PptxEngine
from pipeline.presentation.translate_presentation import collect_translatable_html
from pipeline.translation.base import TranslationError
from pipeline.translation.cost_control import (
    DEEPL_PRICING,
    DEFAULT_MAX_CHARS_PER_RUN,
    GOOGLE_PRICING,
    GROK_PRICING,
    OPENAI_PRICING,
    PricingModel,
    get_month_usage,
)
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import paragraph_to_html
from ui.models import AnalysisResult, CostSummary, EmbeddedImageMode, TranslationMode, TranslationRequest


PRICING: dict[str, PricingModel] = {
    item.provider_name: item
    for item in (DEEPL_PRICING, GOOGLE_PRICING, OPENAI_PRICING, GROK_PRICING)
}


def _zip_media_count(path: Path, prefix: str) -> int:
    with zipfile.ZipFile(path) as archive:
        return sum(1 for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/"))


def _pptx_slide_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        return sum(
            1 for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )


def _live_deepl_usage() -> tuple[int, int | None] | None:
    """Query DeepL's own live quota (GET /v2/usage) for the account behind
    the currently configured key. Returns None - never raises - if no key
    is configured or the request fails for any reason (offline, revoked
    key, DeepL outage); callers fall back to the local estimate and surface
    a warning instead of failing the whole analysis over an optional extra.
    """
    try:
        usage = DeepLProvider().get_usage()
    except TranslationError:
        return None
    character_count = usage.get("character_count")
    if character_count is None:
        return None
    return character_count, usage.get("character_limit")


def _cost(provider: str, characters: int, max_chars: int, warnings: list[str]) -> CostSummary:
    pricing = PRICING[provider]
    usage = get_month_usage(provider)

    live_used: int | None = None
    live_limit: int | None = None
    live_available = False
    if provider == "deepl":
        live = _live_deepl_usage()
        if live is not None:
            live_used, live_limit = live
            live_available = True
        else:
            warnings.append("warning.live_quota_unavailable")

    if live_available and live_limit is not None:
        remaining_free = max(live_limit - live_used, 0)
    elif live_available:
        # Account reports no limit (some Pro contracts) - nothing is billed
        # as "over the free tier" from this app's perspective.
        remaining_free = characters
    else:
        remaining_free = max(pricing.free_tier_chars_per_month - usage, 0)
    billable = max(characters - remaining_free, 0)
    estimate = billable / 1_000_000 * pricing.cost_per_million_chars
    return CostSummary(
        provider, characters, usage, pricing.free_tier_chars_per_month, estimate, max_chars,
        live_available, live_used, live_limit,
    )


def analyze_request(
    request: TranslationRequest,
    max_chars_per_run: int = DEFAULT_MAX_CHARS_PER_RUN,
) -> AnalysisResult:
    errors = request.validation_errors()
    if errors:
        raise ValueError("\n".join(errors))

    text_chars = images = units = 0
    warnings: list[str] = []
    # "==" (not "is"): request.mode may arrive as a plain str here rather
    # than the TranslationMode singleton if a caller skipped the
    # TranslationRequest coercion (see ui/app.py::_request) - str/Enum
    # equality still holds either way, identity does not.
    ocr_required = request.mode == TranslationMode.IMAGES
    label = "unit.images"

    if request.mode == TranslationMode.PDF:
        # Keep the other UI modes usable when the optional PDF runtime is not
        # installed; requirements.txt still installs PyMuPDF for full use.
        from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html

        engine = PyMuPdfEngine()
        engine.open(str(request.source_paths[0]))
        pages = engine.get_pages()
        units, label = len(pages), "unit.pages"
        for page in pages:
            blocks = engine.extract_blocks(page.index)
            text_chars += sum(len(spans_to_html(block.spans)) for block in blocks if block.translatable)
            images += len(engine.extract_images(page.index))
        if text_chars == 0:
            ocr_required = True
            warnings.append("warning.scan_pdf")
    elif request.mode == TranslationMode.PRESENTATION:
        engine = PptxEngine()
        engine.open(request.source_paths[0])
        payloads = collect_translatable_html(engine)
        text_chars = sum(map(len, payloads))
        units = _pptx_slide_count(request.source_paths[0])
        label = "unit.slides"
        images = _zip_media_count(request.source_paths[0], "ppt/media/")
    elif request.mode == TranslationMode.WORD:
        engine = DocxEngine()
        # ico_mode must match what the actual run will use (see
        # DocxEngine.open()'s docstring / ui/word_job.py) - otherwise this
        # cost estimate would count paragraphs the run then skips (or vice
        # versa), and the estimate the user confirms wouldn't match what
        # actually happens.
        engine.open(str(request.source_paths[0]), ico_mode=request.ico_mode)
        paragraphs = engine.get_paragraphs()
        payloads = [paragraph_to_html(p).html for p in paragraphs if p.translatable]
        text_chars = sum(map(len, payloads))
        units, label = len(paragraphs), "unit.paragraphs"
        images = _zip_media_count(request.source_paths[0], "word/media/")
    else:
        units, label = len(request.source_paths), "unit.images"
        images = units
        warnings.append("warning.image_cost_unknown")

    selected = images if request.embedded_images == EmbeddedImageMode.ALL else 0
    if request.embedded_images == EmbeddedImageMode.SELECTED:
        warnings.append("warning.image_selection_later")
    cost = _cost(request.provider, text_chars, max_chars_per_run, warnings)
    return AnalysisResult(
        request.mode, len(request.source_paths), units, label, text_chars, images, selected,
        ocr_required, cost, tuple(warnings)
    )
