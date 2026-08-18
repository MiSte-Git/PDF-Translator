"""Rückschreibe-Backends für übersetzte Bildtexte (RoadMap.md Phase 3).

Analog zu pipeline/images/ocr.py::OcrEngine: ein Protocol
(`InpaintingBackend`), gegen das mehrere austauschbare Implementierungen
laufen. Diese Datei enthält das erste, sofort lauffähige Backend
(BoxOverlayBackend - keine neue Abhängigkeit über das im Projekt bereits
vorhandene Pillow hinaus, das PDF-Redact/Insert-Prinzip von
pipeline/pdf/pymupdf_engine.py auf Rasterbilder übertragen: Originalfläche
überdecken, übersetzten Text einfügen). Weitere Backends (klassisches
CPU-Inpainting über OpenCV, KI-Inpainting lokal/Cloud) folgen als eigene
Klassen in eigenen Commits - siehe RoadMap.md Phase 3 für die komplette
Backend-Liste und die Gründe für die Reihenfolge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pipeline.images.ocr import OcrTextRegion

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
