"""Central, single-registration extension points for this project:
translation providers, OCR engines, and inpainting backends.

Moved here (22.08.2026) from ui/document_job_common.py, which originally
introduced the provider/OCR/inpainting mapping with the rationale "a
UI-layer concern (which options the dropdown/checkbox offers), not
something pipeline/images/ocr.py or pipeline/images/inpainting.py
themselves need to know about". That rationale held as long as the only
consumer was the desktop UI - it stopped holding once a second, non-UI
consumer appeared: image_translate_cli (Backlog.md "Geplant", 22.08.2026),
the standalone CLI/subprocess interface for the image-translation module
that TME (a separate project) is meant to call without depending on
anything UI-specific.

**Provider registration (22.08.2026, Michael: "für die Zukunft offen und
dynamisch behalten"):** originally a provider's name/factory lived in one
dict here, its PricingModel in pipeline/translation/cost_control.py, and
(once image_translate_cli existed) its credential-check callable in a
THIRD dict in image_translate_cli/cli.py - adding a provider meant editing
three separate files' separate mappings, an easy step to miss and an
awkward shape for "we don't know yet what providers we'll want to support
in the future". ProviderSpec/register_provider()/PROVIDER_REGISTRY below
consolidate all three into ONE registration call in ONE place: a new
provider still needs actual code (a TranslationProvider implementation -
there is no way around writing SOME code to speak a new API, no config
file can invent that), but once that class and its PricingModel exist,
wiring it in is exactly one register_provider(ProviderSpec(...)) call
here, and everything downstream (image_translate_cli's config validation,
its `check`/`translate` commands, the desktop UI's provider dropdown, cost
estimation) picks it up automatically - no other file needs to change.
PROVIDER_FACTORIES (this module's pre-existing public name, still used by
ui/app.py, ui/pptx_job.py, etc.) is now DERIVED from PROVIDER_REGISTRY
rather than being its own separate literal, so it can't drift out of sync
with the registry the way three independent dicts could.

OCR_ENGINE_FACTORIES/INPAINTING_BACKEND_FACTORIES keep the simpler
"one dict, name -> factory" shape for now (no per-entry pricing/credential
metadata to consolidate the way providers had) - see this module's
ocr_engine_available()/inpainting_backend_available() for their
availability checks. Worth revisiting the same ProviderSpec-style
consolidation for these two if/when a second real entry appears for
either (a cloud OCR backend, a cloud inpainting backend - both already
anticipated in RoadMap.md Phase 3) and brings its own credential-check
concern the way a translation provider does.

ui/document_job_common.py imports the public names from here rather than
defining them - see that module for what's still genuinely UI/job-specific
(DestinationConflictError, safe_destination()).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pipeline import credentials
from pipeline.images.inpainting import (
    BoxOverlayBackend,
    CvInpaintingBackend,
    GpuInpaintingBackend,
    InpaintingBackend,
)
from pipeline.images.ocr import GoogleVisionOcrEngine, OcrEngine, PaddleOcrEngine, TesseractOcrEngine
from pipeline.translation.base import TranslationProvider
from pipeline.translation.cost_control import (
    DEEPL_PRICING,
    GOOGLE_PRICING,
    GROK_PRICING,
    OPENAI_PRICING,
    PricingModel,
)
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from pipeline.translation.openai_provider import OpenAIProvider


@dataclass(frozen=True)
class ProviderSpec:
    """Everything needed to offer one translation provider, in one place.

    `credential_check` is a zero-argument callable that raises
    RuntimeError with a human-readable message when the provider's
    credentials are NOT configured (the exact shape
    pipeline.credentials.get_*_api_key() already has - passed directly,
    not wrapped) - used by image_translate_cli's `check` command and
    ui/settings.py-style availability checks alike, without either of
    them needing to know which specific credential function belongs to
    which provider.
    """

    name: str
    factory: Callable[[], TranslationProvider]
    pricing: PricingModel
    credential_check: Callable[[], str]


PROVIDER_REGISTRY: dict[str, ProviderSpec] = {}

# Kept as the pre-existing public name every current caller (ui/app.py,
# ui/pptx_job.py, image_translate_cli/config.py, ...) already imports -
# but populated by register_provider() below IN PLACE (mutated, never
# reassigned) rather than computed once from PROVIDER_REGISTRY, so a
# provider registered AFTER this module was first imported (e.g. by a
# future entry_points-based auto-loader, or a test) still shows up here:
# every earlier `from pipeline.registry import PROVIDER_FACTORIES` holds a
# reference to this SAME dict object, and only sees a new key because the
# object itself was mutated, not replaced. A comprehension recomputed once
# at registration time would have silently missed any registration that
# happens later - which is exactly the "we don't know yet what providers
# we'll want to support in the future" case this whole registry exists
# for (22.08.2026, Michael).
PROVIDER_FACTORIES: dict[str, Callable[[], TranslationProvider]] = {}


def register_provider(spec: ProviderSpec) -> None:
    """Add (or replace) one provider in PROVIDER_REGISTRY (and, derived
    from it, PROVIDER_FACTORIES - see that dict's comment above).
    Registering the same `spec.name` twice replaces the earlier entry
    rather than raising - deliberately permissive, since the only
    realistic double-registration case is a test or a REPL re-running this
    module's registrations, not a real naming collision worth failing
    loudly over.
    """
    PROVIDER_REGISTRY[spec.name] = spec
    PROVIDER_FACTORIES[spec.name] = spec.factory


register_provider(
    ProviderSpec("deepl", DeepLProvider, DEEPL_PRICING, credentials.get_deepl_api_key)
)
register_provider(
    ProviderSpec(
        "google", GoogleTranslateProvider, GOOGLE_PRICING, credentials.get_google_translate_api_key
    )
)
register_provider(
    ProviderSpec("openai", OpenAIProvider, OPENAI_PRICING, credentials.get_openai_api_key)
)
register_provider(
    ProviderSpec("grok", GrokProvider, GROK_PRICING, credentials.get_grok_api_key)
)

OCR_ENGINE_FACTORIES: dict[str, Callable[[], OcrEngine]] = {
    "tesseract": TesseractOcrEngine,
    # google_vision/paddleocr (23.08.2026): die zwei "Cloud-OCR-Backend"-
    # Eintraege, die hier seit 22.08.2026 als offen angekuendigt waren -
    # Michael fragte nach dem Vergleich mit Googles eigener Bild-
    # Uebersetzung ("Was fuer eine Loesung gibt es dafuer?"), beide
    # Kandidaten wurden gegen das echte Infografik-Bild geprueft
    # (tools/probe_google_vision.py/tools/probe_paddleocr.py - siehe
    # Backlog.md) und dann "Ich wuerde beide zur Auswahl einbauen." Siehe
    # pipeline.images.ocr.GoogleVisionOcrEngine/PaddleOcrEngine fuer die
    # Implementierung, ocr_engine_available() unten fuer ihre
    # Verfuegbarkeitspruefung.
    "google_vision": GoogleVisionOcrEngine,
    "paddleocr": PaddleOcrEngine,
}

INPAINTING_BACKEND_FACTORIES: dict[str, Callable[[], InpaintingBackend]] = {
    "box_overlay": BoxOverlayBackend,
    "cv_inpainting": CvInpaintingBackend,
    "gpu_inpainting": GpuInpaintingBackend,
    # Cloud-Inpainting (OpenAI) folgt als weiterer Eintrag - siehe
    # RoadMap.md Phase 3.
}


def get_provider_spec(name: str) -> ProviderSpec:
    try:
        return PROVIDER_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Unbekannter Übersetzungsanbieter: {name!r} (bekannt: {', '.join(sorted(PROVIDER_REGISTRY))})"
        ) from exc


def build_provider(name: str) -> TranslationProvider:
    return get_provider_spec(name).factory()


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


def provider_credential_status(name: str) -> tuple[bool, str | None]:
    """Whether `name`'s credentials are configured right now - (True, None)
    if so, (False, <message from the RuntimeError>) if not. Used by
    image_translate_cli's `check` command; ui/settings.py-style callers can
    use this too instead of importing a provider's get_*_api_key()
    directly.
    """
    spec = get_provider_spec(name)
    try:
        spec.credential_check()
    except RuntimeError as exc:
        return False, str(exc)
    return True, None


def ocr_engine_available(name: str) -> bool:
    """Whether the OCR engine `name` can actually be used right now -
    checked BEFORE a job starts (ui/analysis.py, image_translate_cli's
    `check` command), mirroring provider_credential_status() for
    translation providers. "tesseract" needs its binary on PATH (see
    pipeline.images.ocr.tesseract_available()), "google_vision" needs a
    configured Google API key (pipeline.images.ocr.
    google_vision_available() - reuses the SAME key as the Google
    translation provider, see that function's own docstring for why),
    "paddleocr" needs the optional paddleocr package installed
    (pipeline.images.ocr.paddleocr_available()) - each check is a plain
    delegate to that engine's own module-level function rather than
    consolidated into a ProviderSpec-style registry entry (see this
    module's docstring on OCR_ENGINE_FACTORIES/INPAINTING_BACKEND_FACTORIES
    "worth revisiting" note): with two real cloud entries now, that
    consolidation is worth doing once a THIRD needs genuinely different
    per-entry metadata (pricing, say) - both current checks are a single
    no-argument bool function, no more complex than tesseract's own, so
    the simple if/elif below still isn't pulling its weight to replace.
    """
    if name == "tesseract":
        from pipeline.images.ocr import tesseract_available

        return tesseract_available()
    if name == "google_vision":
        from pipeline.images.ocr import google_vision_available

        return google_vision_available()
    if name == "paddleocr":
        from pipeline.images.ocr import paddleocr_available

        return paddleocr_available()
    return name in OCR_ENGINE_FACTORIES


def inpainting_backend_available(name: str) -> bool:
    """Whether the rückschreibe-backend `name` can actually be used right
    now - checked BEFORE a job starts (ui/app.py's IMAGES-mode dropdown
    hint and fail-fast check, image_translate_cli's `check` command,
    mirrors ocr_engine_available() above). Box-Overlay/CvInpaintingBackend
    have no real availability question (both only need Pillow, resp.
    Pillow+OpenCV, which are hard dependencies of running IMAGES mode at
    all - see requirements-ocr.txt) so they're always reported available;
    only "gpu_inpainting" has a real check today (CUDA GPU with enough
    VRAM, see pipeline.images.inpainting.gpu_inpainting_available()) - a
    future Cloud-Inpainting backend would check for a configured API key
    instead, the same way build_provider()'s providers do lazily on first
    use.
    """
    if name == "gpu_inpainting":
        from pipeline.images.inpainting import gpu_inpainting_available

        return gpu_inpainting_available()
    return name in INPAINTING_BACKEND_FACTORIES
