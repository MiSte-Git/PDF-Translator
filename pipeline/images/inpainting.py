"""Rückschreibe-Backends für übersetzte Bildtexte (RoadMap.md Phase 3).

Analog zu pipeline/images/ocr.py::OcrEngine: ein Protocol
(`InpaintingBackend`), gegen das mehrere austauschbare Implementierungen
laufen. Diese Datei enthält Box-Overlay (keine neue Abhängigkeit über das
im Projekt bereits vorhandene Pillow hinaus, das PDF-Redact/Insert-Prinzip
von pipeline/pdf/pymupdf_engine.py auf Rasterbilder übertragen:
Originalfläche überdecken, übersetzten Text einfügen), klassisches
CPU-Inpainting (OpenCV, kein trainiertes Modell) sowie lokales
KI-Inpainting (GpuInpaintingBackend, LaMa via PyTorch/CUDA) - Cloud-
Inpainting folgt als eigene Klasse in einem eigenen Commit. Siehe
RoadMap.md Phase 3 für die komplette Backend-Liste und die Gründe für die
Reihenfolge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pipeline.images.ocr import OcrTextRegion

# Mindest-VRAM für GpuInpaintingBackend (siehe gpu_inpainting_available()
# unten) - LaMa (big-lama-Gewichte) läuft auch mit weniger, aber mit
# spürbarem Risiko für CUDA-Out-of-Memory bei größeren Bildern/vielen
# Regionen gleichzeitig; 4 GB ist ein konservativer, dokumentierter
# Schwellwert, kein hart validierter Benchmark-Wert.
GPU_MIN_VRAM_GB = 4.0

# Modul-weiter Cache für das geladene LaMa-Modell (siehe
# _get_lama_model()) - überlebt über mehrere GpuInpaintingBackend()-
# Instanzen hinweg (eine neue Instanz pro run_image_job()-Aufruf, siehe
# ui/document_job_common.py::build_inpainting_backend()), damit ein
# Mehrdatei-Batch (run_image_batch_job()) die mehrere-hundert-MB-Gewichte
# nicht pro Datei neu lädt/herunterlädt.
_LAMA_MODEL_CACHE: dict[str, object] = {}

# Bewusst derselbe Font-Pfad wie in tests/test_image_ocr.py - auf diesem
# System vorhanden, aber NICHT garantiert auf jeder Zielmaschine (siehe
# RoadMap.md/Backlog.md: eine mögliche Standalone-Version soll auch ohne
# bestimmte vorinstallierte Fonts laufen). _load_font() fällt deshalb auf
# Pillows eingebauten Default-Font zurück statt eine Exception zu werfen,
# wenn keiner der Pfade existiert.
_FALLBACK_FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

# Breite des Rings außerhalb der Bounding-Box, aus dem die
# Hintergrundfarbe geschätzt wird (siehe _sample_background_color()).
_BACKGROUND_SAMPLE_MARGIN = 4


class InpaintingError(Exception):
    """Raised when a backend fails to produce the replacement image -
    mirrors pipeline.images.ocr.OcrError's role for the recognition
    stage."""


@dataclass(frozen=True)
class TextReplacement:
    """One OCR-recognized region together with its translated text - the
    unit of work an InpaintingBackend consumes. `region` keeps the
    ORIGINAL recognized OcrTextRegion (not just a bare bounding box)
    around, so a backend can use its size/original text if useful (e.g.
    for font-size sizing below)."""

    region: OcrTextRegion
    translated_text: str


@runtime_checkable
class InpaintingBackend(Protocol):
    """Minimal interface every rückschreibe-backend (Box-Overlay/CPU-
    Inpainting/KI-Inpainting lokal/Cloud) must implement."""

    def apply(self, image_path: str, replacements: list[TextReplacement], output_path: str) -> None:
        """Write a copy of the image at `image_path` to `output_path`,
        with each replacement's region overwritten by its
        `translated_text`. Regions not covered by `replacements` (e.g.
        because the user only selected some of the recognized lines) are
        left byte-for-byte untouched.
        """
        ...


def _load_font(pixel_height: int):
    from PIL import ImageFont

    size = max(8, int(pixel_height * 0.8))
    for path in _FALLBACK_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _sample_background_color(image, x: int, y: int, width: int, height: int) -> tuple[int, int, int]:
    """Approximates the region's surrounding color by averaging a thin
    ring of pixels just OUTSIDE the bounding box (clamped to image
    bounds).

    Deliberately not a single corner pixel: that risks landing on a
    stray dark pixel right at the box edge (part of the very glyph
    being replaced, e.g. a descender or serif poking out). Averaging a
    ring around the box is more robust against that, at the cost of
    blurring genuinely multi-colored surroundings - acceptable for the
    box-overlay backend's target use case (business documents, diagrams,
    screenshots - see RoadMap.md), not a claim of photographic realism.
    """
    img_w, img_h = image.size
    x0 = max(0, x - _BACKGROUND_SAMPLE_MARGIN)
    y0 = max(0, y - _BACKGROUND_SAMPLE_MARGIN)
    x1 = min(img_w, x + width + _BACKGROUND_SAMPLE_MARGIN)
    y1 = min(img_h, y + height + _BACKGROUND_SAMPLE_MARGIN)

    pixels = image.load()
    samples: list[tuple[int, int, int]] = []
    # Top and bottom strips (full sampled width), left and right strips
    # (only the vertical span of the box itself, to avoid re-sampling the
    # corners already covered by the top/bottom strips - harmless if it
    # happened, just redundant).
    for px in range(x0, x1):
        if y0 < y:
            samples.append(pixels[px, y0])
        if y1 - 1 >= y + height and y1 - 1 < img_h:
            samples.append(pixels[px, y1 - 1])
    for py in range(max(y0, y), min(y1, y + height)):
        if x0 < x:
            samples.append(pixels[x0, py])
        if x1 - 1 >= x + width and x1 - 1 < img_w:
            samples.append(pixels[x1 - 1, py])

    if not samples:
        return (255, 255, 255)  # fully clamped away (tiny image) - safe white default
    r = sum(s[0] for s in samples) // len(samples)
    g = sum(s[1] for s in samples) // len(samples)
    b = sum(s[2] for s in samples) // len(samples)
    return (r, g, b)


def _contrasting_text_color(background: tuple[int, int, int]) -> tuple[int, int, int]:
    """Standard relative-luminance formula (ITU-R BT.601) to pick black
    or white text - whichever contrasts against the sampled background,
    mirroring how a real document's original dark-on-light or
    light-on-dark text would have been chosen."""
    r, g, b = background
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return (0, 0, 0) if luminance > 128 else (255, 255, 255)


class BoxOverlayBackend:
    """InpaintingBackend that overwrites each region with a sampled
    background color, then draws the translated text on top - the
    box-overlay approach documented in RoadMap.md Phase 3 as the always-
    available default (no new dependency, works everywhere), with the
    known limitation that it reads as a visible "patch" over photographic
    or otherwise structured backgrounds.
    """

    def apply(self, image_path: str, replacements: list[TextReplacement], output_path: str) -> None:
        from PIL import Image, ImageDraw

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht geöffnet werden: {exc}") from exc

        draw = ImageDraw.Draw(image)
        for replacement in replacements:
            region = replacement.region
            background = _sample_background_color(image, region.x, region.y, region.width, region.height)
            draw.rectangle(
                [region.x, region.y, region.x + region.width, region.y + region.height],
                fill=background,
            )
            font = _load_font(region.height)
            text_color = _contrasting_text_color(background)
            draw.text((region.x, region.y), replacement.translated_text, fill=text_color, font=font)

        try:
            image.save(output_path)
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht gespeichert werden: {exc}") from exc


class CvInpaintingBackend:
    """InpaintingBackend using classic (non-AI) OpenCV inpainting
    (cv2.inpaint, Telea algorithm - fast marching method, no trained
    model involved) to reconstruct the background under each replaced
    region before drawing the translated text on top.

    Unlike BoxOverlayBackend's flat single-color fill, this can plausibly
    continue simple textures or gradients right up to (and slightly
    into) the box edge, instead of leaving a visibly flat rectangle - see
    RoadMap.md Phase 3 for where this sits relative to the other three
    backends (Box-Overlay/this one need no GPU or trained model; KI-
    Inpainting lokal/Cloud follow separately). Needs opencv-python(-
    headless), listed as an optional dependency in requirements-ocr.txt
    (imported lazily below, same lazy-import discipline as
    BoxOverlayBackend/TesseractOcrEngine) - classic (not AI-based)
    inpainting quality is bounded by the algorithm itself: it works well
    for simple/repetitive surroundings, but - like BoxOverlayBackend -
    is not a substitute for the KI-Inpainting backends on genuinely
    complex photographic backgrounds.
    """

    def apply(self, image_path: str, replacements: list[TextReplacement], output_path: str) -> None:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise InpaintingError(
                f"Inpainting-Abhängigkeit fehlt: {exc}. Siehe requirements-ocr.txt."
            ) from exc
        from PIL import Image

        try:
            pil_image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht geöffnet werden: {exc}") from exc

        # PIL is RGB, OpenCV expects BGR - converted once here and back
        # once at the very end, so every intermediate step (mask,
        # cv2.inpaint()) stays entirely inside OpenCV's own convention.
        image_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        mask = np.zeros(image_bgr.shape[:2], dtype=np.uint8)
        for replacement in replacements:
            region = replacement.region
            mask[region.y : region.y + region.height, region.x : region.x + region.width] = 255

        if replacements:
            image_bgr = cv2.inpaint(image_bgr, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        result = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        from PIL import ImageDraw

        draw = ImageDraw.Draw(result)
        for replacement in replacements:
            region = replacement.region
            # The interior itself is now a valid background estimate
            # (cv2.inpaint() already reconstructed it) - sampling the
            # RECONSTRUCTED interior directly for text-color contrast,
            # rather than BoxOverlayBackend's outside-ring sample, which
            # would still be correct here too but is a needless detour
            # now that the interior itself is meaningful.
            background = _average_region_color(result, region.x, region.y, region.width, region.height)
            font = _load_font(region.height)
            text_color = _contrasting_text_color(background)
            draw.text((region.x, region.y), replacement.translated_text, fill=text_color, font=font)

        try:
            result.save(output_path)
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht gespeichert werden: {exc}") from exc


def _average_region_color(image, x: int, y: int, width: int, height: int) -> tuple[int, int, int]:
    """Plain average color of the region's OWN interior pixels - valid
    once that interior has already been reconstructed (CvInpaintingBackend
    after cv2.inpaint()), unlike _sample_background_color() above which
    deliberately avoids the interior because it still holds the original,
    not-yet-replaced text."""
    pixels = image.load()
    samples = [pixels[px, py] for px in range(x, x + width) for py in range(y, y + height)]
    if not samples:
        return (255, 255, 255)
    r = sum(s[0] for s in samples) // len(samples)
    g = sum(s[1] for s in samples) // len(samples)
    b = sum(s[2] for s in samples) // len(samples)
    return (r, g, b)


def gpu_inpainting_available(min_vram_gb: float = GPU_MIN_VRAM_GB) -> bool:
    """Whether GpuInpaintingBackend can actually run right now: PyTorch
    must be importable, a CUDA device must be visible, and that device's
    total memory must be at least `min_vram_gb` (see GPU_MIN_VRAM_GB).
    Mirrors pipeline.images.ocr.tesseract_available() - never raises,
    always returns a plain bool, checked BEFORE a job starts (see
    ui/document_job_common.py::inpainting_backend_available()) rather
    than failing deep inside a run.

    Deliberately no CPU fallback here (see RoadMap.md Phase 3): CPU-only
    LaMa inference would be dramatically slower than the point of
    offering a GPU backend in the first place - a GPU that doesn't
    qualify (or isn't present at all) is reported as unavailable so the
    UI can steer the user toward Cloud-Inpainting instead (see
    ui/app.py's inpainting-backend hint, mirrors
    _update_ocr_engine_hint()'s pattern), not silently downgraded to a
    slow local run the user never asked for.
    """
    try:
        import torch
    except ImportError:
        return False
    try:
        if not torch.cuda.is_available():
            return False
        total_memory = torch.cuda.get_device_properties(0).total_memory
    except Exception:
        # Any other failure while probing the device (driver mismatch, no
        # device index 0, ...) is treated the same as "not available" -
        # this check must never itself crash the analysis/start flow.
        return False
    return total_memory >= min_vram_gb * (1024 ** 3)


def _build_inpainting_mask(size: tuple[int, int], replacements: list[TextReplacement], padding: int = 4):
    """Binary mask for the GPU model in the standard LaMa/simple-lama-
    inpainting convention: white (255) marks the area to remove and
    reconstruct, black (0) is left untouched. Each region is padded by
    `padding` pixels on every side (clamped to the image bounds) so
    anti-aliased glyph edges the OCR bounding box just barely missed are
    still covered - an uncovered sliver of the original glyph would
    otherwise show through underneath the new translated text.
    """
    from PIL import Image, ImageDraw

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    width, height = size
    for replacement in replacements:
        region = replacement.region
        left = max(region.x - padding, 0)
        top = max(region.y - padding, 0)
        right = min(region.x + region.width + padding, width)
        bottom = min(region.y + region.height + padding, height)
        draw.rectangle([left, top, right, bottom], fill=255)
    return mask


def _get_lama_model(torch_module, simple_lama_cls):
    """Lazily construct (and cache - see _LAMA_MODEL_CACHE above) the
    SimpleLama wrapper around the pretrained LaMa weights. `device` is
    always explicitly "cuda" here (never simple-lama-inpainting's own
    default of "cuda if available else cpu") because GpuInpaintingBackend.
    apply() only ever reaches this point after gpu_inpainting_available()
    already confirmed a qualifying CUDA device exists - see that
    function's docstring for why there is no CPU fallback path to select
    instead.
    """
    if "model" not in _LAMA_MODEL_CACHE:
        _LAMA_MODEL_CACHE["model"] = simple_lama_cls(device=torch_module.device("cuda"))
    return _LAMA_MODEL_CACHE["model"]


class GpuInpaintingBackend:
    """InpaintingBackend using the local GPU to run LaMa (Large Mask
    inpainting - https://github.com/advimman/lama), a model purpose-built
    for object/text removal with background reconstruction, via the
    lightweight `simple-lama-inpainting` wrapper (lazy import, listed as
    an optional dependency in requirements-gpu.txt - separate from
    requirements-ocr.txt because it pulls in PyTorch, a much larger and
    GPU-specific installation not every user needs).

    Unlike BoxOverlayBackend/CvInpaintingBackend, this can plausibly
    reconstruct genuinely complex/photographic backgrounds instead of
    being bounded by a flat fill or a non-AI algorithm - the tradeoff is
    the GPU/VRAM requirement checked by gpu_inpainting_available() (no
    CPU fallback - see that function's docstring) and, on first use, a
    multi-hundred-MB model download (cached afterwards - see
    _LAMA_MODEL_CACHE and _get_lama_model(); `simple-lama-inpainting`
    also honours a LAMA_MODEL environment variable pointing at a local
    weights file, useful for a standalone deployment without runtime
    internet access - see requirements-gpu.txt).

    Text is drawn back on top exactly like CvInpaintingBackend does
    (contrast color sampled from the model's own reconstructed interior,
    not an outside ring - see _average_region_color()'s docstring for
    why that's correct once the interior has actually been
    reconstructed).

    Real model inference needs an actual CUDA GPU, which this
    development sandbox does not have (see RoadMap.md Phase 3) - the
    fail-fast guard below and the mask-building helper are covered by
    tests here; the model call itself must be verified through a real
    run on the user's own machine, the same pattern used for every other
    "needs real hardware/a live account" feature in this project.
    """

    def apply(self, image_path: str, replacements: list[TextReplacement], output_path: str) -> None:
        if not gpu_inpainting_available():
            raise InpaintingError(
                "GPU-Inpainting ist auf diesem System nicht verfügbar (keine "
                "ausreichend starke CUDA-GPU gefunden) - bitte ein anderes "
                "Rückschreibe-Backend wählen (z. B. Cloud-Inpainting)."
            )
        try:
            import torch
            from simple_lama_inpainting import SimpleLama
        except ImportError as exc:
            raise InpaintingError(
                f"GPU-Inpainting-Abhängigkeit fehlt: {exc}. Siehe requirements-gpu.txt."
            ) from exc
        from PIL import Image, ImageDraw

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht geöffnet werden: {exc}") from exc

        if replacements:
            mask = _build_inpainting_mask(image.size, replacements)
            model = _get_lama_model(torch, SimpleLama)
            try:
                image = model(image, mask).convert("RGB")
            except Exception as exc:
                raise InpaintingError(f"KI-Inpainting fehlgeschlagen: {exc}") from exc

        draw = ImageDraw.Draw(image)
        for replacement in replacements:
            region = replacement.region
            # The model's own reconstructed interior is now a valid
            # background estimate (same reasoning as CvInpaintingBackend
            # above) - sampled directly rather than BoxOverlayBackend's
            # outside-ring approach.
            background = _average_region_color(image, region.x, region.y, region.width, region.height)
            font = _load_font(region.height)
            text_color = _contrasting_text_color(background)
            draw.text((region.x, region.y), replacement.translated_text, fill=text_color, font=font)

        try:
            image.save(output_path)
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht gespeichert werden: {exc}") from exc
