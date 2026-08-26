"""HTTP-independent glue between webapp/server.py's handlers and the
existing, already Qt-independent pipeline/ui.analysis/ui.settings/
pipeline.registry code - see webapp/__init__.py's docstring for why this
split exists at all (webapp/ must never import PySide6).

Kept separate from server.py on purpose: this module has no `http.server`
import and can be unit-tested (and read) without any HTTP machinery
involved - server.py's handlers stay thin (parse the request, call one
function here, serialize the result), all the actual logic lives here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.registry import (
    INPAINTING_BACKEND_FACTORIES,
    OCR_ENGINE_FACTORIES,
    PROVIDER_FACTORIES,
    inpainting_backend_available,
    ocr_engine_available,
)
from pipeline.translation.cost_control import DEFAULT_MAX_CHARS_PER_RUN
from ui.analysis import analyze_request
from ui.models import EmbeddedImageMode, TranslationMode, TranslationRequest
from ui.settings import credential_status
from webapp import settings_store


def build_config() -> dict[str, Any]:
    """Backs GET /api/config - everything the frontend's images-mode form
    needs to render itself: which providers/OCR-engines/inpainting-
    backends exist, whether each is actually usable right now (same
    availability checks ui/app.py's dropdown hints and fail-fast checks
    already use, see pipeline.registry's own docstring), and the
    last-saved form state to prefill with (webapp/settings_store.py, the
    QSettings replacement).
    """
    providers = sorted(PROVIDER_FACTORIES)
    ocr_engines = sorted(OCR_ENGINE_FACTORIES)
    inpainting_backends = sorted(INPAINTING_BACKEND_FACTORIES)
    saved = settings_store.load()
    return {
        "providers": providers,
        "provider_credential_status": {name: credential_status(name) for name in providers},
        "ocr_engines": ocr_engines,
        "ocr_engine_available": {name: ocr_engine_available(name) for name in ocr_engines},
        "inpainting_backends": inpainting_backends,
        "inpainting_backend_available": {
            name: inpainting_backend_available(name) for name in inpainting_backends
        },
        "max_chars_per_run": saved.get("max_chars", DEFAULT_MAX_CHARS_PER_RUN),
        "last_form_state": saved,
    }


class AnalyzeRequestError(ValueError):
    """Raised for a malformed analyze request body (wrong JSON shape, not
    a validation failure of the translation request itself) - analyze()
    catches this specifically to return a 400 with a clear message
    instead of letting a TypeError/AttributeError escape as a 500.
    """


def _request_from_json(body: dict[str, Any]) -> TranslationRequest:
    """Builds the images-mode TranslationRequest this pilot always uses -
    mode is hardcoded to IMAGES (webapp/ covers only the image-translation
    flow for now, see webapp/__init__.py's docstring); every other field
    comes from the request body with the same defaults ui/app.py's form
    fields have (target_lang "DE", ocr_engine "tesseract",
    inpainting_backend "box_overlay" - see webapp/settings_store.py's
    DEFAULTS, which uses the identical defaults).
    """
    source_paths = body.get("source_paths") or []
    if not isinstance(source_paths, list) or not all(isinstance(p, str) for p in source_paths):
        raise AnalyzeRequestError("source_paths muss eine Liste von Pfaden (Strings) sein.")
    protected_terms = body.get("protected_terms") or []
    if not isinstance(protected_terms, list) or not all(isinstance(t, str) for t in protected_terms):
        raise AnalyzeRequestError("protected_terms muss eine Liste von Begriffen (Strings) sein.")
    return TranslationRequest(
        mode=TranslationMode.IMAGES,
        source_paths=tuple(Path(p) for p in source_paths),
        provider=str(body.get("provider", "deepl")),
        source_language=(body.get("source_language") or None),
        target_language=str(body.get("target_language", "DE")),
        embedded_images=EmbeddedImageMode.NONE,
        protected_terms=tuple(protected_terms),
        ocr_engine=str(body.get("ocr_engine", "tesseract")),
        inpainting_backend=str(body.get("inpainting_backend", "box_overlay")),
    )


def analyze(body: dict[str, Any]) -> dict[str, Any]:
    """Backs POST /api/analyze - wraps ui.analysis.analyze_request()
    unchanged (RoadMap.md Leitprinzip: every paid run needs an analysis +
    cost estimate + explicit confirmation before execution - this is the
    ONLY function in webapp/ that produces that estimate, and it must stay
    the exact same estimate the Qt app already shows, not a re-derived
    approximation). Returns {"ok": True, ...AnalysisResult fields...} on
    success or {"ok": False, "errors": [...]} on any validation problem -
    never raises past this point, so server.py's handler can turn either
    shape directly into a JSON response.
    """
    try:
        request = _request_from_json(body)
    except AnalyzeRequestError as exc:
        return {"ok": False, "errors": [str(exc)]}
    max_chars = int(body.get("max_chars_per_run", DEFAULT_MAX_CHARS_PER_RUN))
    try:
        result = analyze_request(request, max_chars)
    except ValueError as exc:
        # TranslationRequest.validation_errors() is joined with "\n" by
        # analyze_request() itself - split back into a list so the
        # frontend can render one item per line instead of one blob.
        return {"ok": False, "errors": str(exc).split("\n")}
    cost = result.cost
    return {
        "ok": True,
        "mode": result.mode.value,
        "files": result.files,
        "units": result.units,
        "unit_label": result.unit_label,
        "text_characters": result.text_characters,
        "embedded_images": result.embedded_images,
        "selected_image_candidates": result.selected_image_candidates,
        "ocr_required": result.ocr_required,
        "warnings": list(result.warnings),
        "cost": {
            "provider": cost.provider,
            "characters": cost.characters,
            "month_usage": cost.month_usage,
            "free_tier": cost.free_tier,
            "estimated_cost_usd": cost.estimated_cost_usd,
            "max_chars_per_run": cost.max_chars_per_run,
            "within_run_limit": cost.within_run_limit,
            "live_usage_available": cost.live_usage_available,
            "live_characters_used": cost.live_characters_used,
            "live_character_limit": cost.live_character_limit,
        },
    }
