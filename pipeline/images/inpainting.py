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

# Obere/untere Schranke für die beim Zurückschreiben verwendete
# Schriftgröße (siehe _fit_text() unten) - hinzugefügt nach einem
# realen Fund (RoadMap.md/Backlog.md, 18.08.2026): eine einzelne
# OCR-Zeile bekam durch einen fehlerhaft erkannten Bounding-Box eine
# absurd große Höhe (ein danebenliegendes Icon/Pfeil-Grafikelement
# wurde mit in die Zeile hineingerechnet), was ohne Obergrenze zu
# meterhohem Text geführt hätte. _MIN_FONT_SIZE ist die Grenze, ab der
# weiteres Schrumpfen (siehe _fit_text()) nicht mehr sinnvoll lesbar
# wäre - ab da wird lieber ein leichtes Überlaufen über die Box hinaus
# in Kauf genommen als unleserlich kleiner Text.
_MAX_FONT_SIZE = 48
_MIN_FONT_SIZE = 9
# Zeilenabstand als Vielfaches der Schriftgröße - ein gängiger Wert für
# gut lesbaren Fließtext (etwas mehr als reine Glyphenhöhe, damit sich
# Ober-/Unterlängen aufeinanderfolgender Zeilen nicht berühren).
_LINE_SPACING = 1.15

# Luminance-Differenz zum geschätzten Hintergrund, ab der ein Pixel als
# "Tinte" (Teil eines Glyphen-Strichs) statt Hintergrund zählt (siehe
# _ink_ratio() unten) - ein realer Nutzer-Fund (RoadMap.md/Backlog.md,
# 21.08.2026): jede zurückgeschriebene Übersetzung wurde bisher IMMER in
# DejaVuSans Regular gerendert, unabhängig davon, ob die Original-Zeile
# fett war - bei einem real getesteten Infografik-Design (durchgehend
# fette/halbfette Display-Schrift für Überschriften UND Fließtext) sah
# dadurch jede übersetzte Zeile im direkten Vergleich zu dünn/"anders"
# aus. 40 wurde gegen echte JPEG-Regionen dieses Bilds kalibriert:
# gemessene Ink-Ratios für fünf visuell bestätigt fette Original-Zeilen
# lagen bei diesem Schwellwert zwischen 0.37 und 0.55 und damit in jedem
# Fall klar näher an einer synthetisch fett gerenderten Vergleichszeile
# als an einer regulären (siehe _estimate_is_bold()) - kein absoluter
# Schwellwert für "ist fett", sondern nur die Pixel-Klassifikation, auf
# der der RELATIVE Vergleich in _estimate_is_bold() aufbaut.
_INK_LUMINANCE_THRESHOLD = 40


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


def _load_font(size: int, bold: bool = False):
    """Load a font at the given PIXEL SIZE directly (not a region height
    to derive a size from - see _fit_text() below for that step, done
    once by the caller instead of inside this function, so a caller
    trying several candidate sizes doesn't repeat the *0.8 conversion
    every time).

    `bold` (RoadMap.md/Backlog.md 21.08.2026, see _estimate_is_bold() for
    where it comes from) picks _FALLBACK_FONT_PATHS' Bold entry FIRST
    instead of Regular - previously EVERY call always tried Regular
    first, so Bold was effectively dead code (Regular is present on
    essentially every real system this runs on) and every rendered
    translation came out in the same weight regardless of the original
    line's actual weight. Still falls back to the OTHER weight (then
    Pillow's built-in default) if the preferred one's file is missing -
    same "never crash, always render something" fallback chain as
    before, just weight-aware now.
    """
    from PIL import ImageFont

    size = max(1, size)
    regular_path, bold_path = _FALLBACK_FONT_PATHS
    paths = (bold_path, regular_path) if bold else (regular_path, bold_path)
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text_to_width(draw, text: str, font, max_width: int) -> list[str]:
    """Greedy word-wrap: fits as many whitespace-separated words per line
    as stay within `max_width`, measured via draw.textlength() (stable
    across Pillow versions - see this project's own "don't rely on very
    new/uncommon Pillow APIs in test/rendering code" lesson, RoadMap.md/
    Backlog.md 18.08.2026). A single word wider than `max_width` on its
    own still gets its own line rather than being split mid-word -
    overflowing that one line is preferable to breaking a word apart.
    `max_width` <= 0 (a degenerate/zero-width OCR region) still returns
    at least one line rather than looping forever.
    """
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if max_width <= 0 or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _initial_font_size(region: OcrTextRegion) -> int:
    """Starting point for _fit_text()'s shrink-to-fit loop, derived from
    the region's own OCR height and capped at _MAX_FONT_SIZE (see that
    constant's docstring) - factored out of _fit_text() so
    _estimate_is_bold() below can pick a comparably-sized synthetic
    sample without duplicating the *0.8 conversion."""
    return min(max(_MIN_FONT_SIZE, int(region.height * 0.8)), _MAX_FONT_SIZE)


def _fit_text(
    draw, text: str, region: OcrTextRegion, max_height: float, bold: bool = False
) -> tuple[list[str], object, int]:
    """Pick the largest font size - starting from _initial_font_size()'s
    region-height-derived size, in the requested weight (`bold` - see
    _estimate_is_bold()) - that, once `text` is word-wrapped to
    region.width, fits within `max_height` without shrinking past
    _MIN_FONT_SIZE.

    This is a SHRINK-to-fit strategy, deliberately never a GROW-the-box
    one: growing past `max_height` to fit more wrapped lines would risk
    the box encroaching on whatever sits just below it - which is exactly
    what `max_height` itself is computed to leave room for (see
    _vertical_room_below(), whose result every caller below passes here
    instead of region.height directly - a real risk in tightly line-
    spaced screenshots/infographics, see the Backlog.md 18.08.2026 and
    21.08.2026 finds that motivated this function and this parameter,
    respectively). At _MIN_FONT_SIZE the wrapped block may still exceed
    `max_height` - that overflow is accepted rather than shrinking
    further into illegibility, mirroring the PDF pipeline's own
    insert_text() "always make it fit somewhere" policy (see
    pipeline/pdf/pymupdf_engine.py).

    Returns (lines, font, line_height) - the caller draws each line at
    `region.y + i * line_height`, same x for every line.
    """
    size = _initial_font_size(region)
    while True:
        font = _load_font(size, bold=bold)
        lines = _wrap_text_to_width(draw, text, font, max(region.width, 1))
        line_height = max(1, int(size * _LINE_SPACING))
        total_height = line_height * len(lines)
        if total_height <= max_height or size <= _MIN_FONT_SIZE:
            return lines, font, line_height
        size = max(_MIN_FONT_SIZE, size - 2)


def _draw_fitted_text(
    draw,
    region: OcrTextRegion,
    text: str,
    color: tuple[int, int, int],
    image_height: int,
    max_height: float,
    bold: bool = False,
) -> None:
    """Shared final drawing step for all three InpaintingBackend
    implementations below - wraps and shrinks `text` to fit inside
    `max_height` (see _fit_text()) instead of the old single
    draw.text((region.x, region.y), text, ...) call, which drew the
    ENTIRE translated text on one unwrapped line regardless of
    region.width - the real cause (confirmed against actual user-
    reported output, see Backlog.md 18.08.2026) of translated text
    overflowing past its box into neighboring text once German (or any
    longer-than-English target language) no longer fit the original
    line's width.

    `max_height` - normally region.height's neighbour-aware replacement
    from _vertical_room_below(), NOT region.height itself (see that
    function's docstring for why the two differ and Backlog.md
    21.08.2026 for the real image that motivated the distinction) - is a
    separate parameter from region.height so a caller can pass the plain
    region.height back in specific cases (e.g. a test asserting the
    original single-region behaviour) without needing a second region in
    play.

    `image_height` clips line drawing at the image's own bottom edge -
    relevant only for the rare _MIN_FONT_SIZE-and-still-overflowing case
    described in _fit_text()'s docstring, so an extreme case can't draw
    lines past the image entirely.

    `bold` (RoadMap.md/Backlog.md 21.08.2026, see _estimate_is_bold())
    picks the Bold vs Regular DejaVu family for the WHOLE wrapped block -
    every InpaintingBackend.apply() below estimates this ONCE per region,
    from the original (pre-overwrite) pixels, before calling here.
    """
    lines, font, line_height = _fit_text(draw, text, region, max_height, bold=bold)
    y = region.y
    for line in lines:
        if y >= image_height:
            break
        draw.text((region.x, y), line, fill=color, font=font)
        y += line_height


def _ink_ratio(image, x: int, y: int, width: int, height: int, background: tuple[int, int, int]) -> float:
    """Fraction of pixels within [x, x+width) x [y, y+height) (clamped to
    the image bounds) whose luminance differs from `background`'s by more
    than _INK_LUMINANCE_THRESHOLD - a crude proxy for "how much stroke/
    glyph area this region occupies", used ONLY as one half of the
    RELATIVE comparison in _estimate_is_bold() below, never as an
    absolute measurement anything else depends on (real photographed/
    scanned/compressed text is far too noisy for an absolute ink-ratio
    threshold to mean the same thing across different images, fonts and
    sizes - see that function's docstring)."""
    img_w, img_h = image.size
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img_w, x + width), min(img_h, y + height)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    pixels = image.load()
    bg_luminance = 0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2]
    ink = 0
    total = 0
    for px in range(x0, x1):
        for py in range(y0, y1):
            r, g, b = pixels[px, py]
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            total += 1
            if abs(luminance - bg_luminance) > _INK_LUMINANCE_THRESHOLD:
                ink += 1
    return ink / total if total else 0.0


def _synthetic_ink_ratio(text: str, font) -> float:
    """_ink_ratio() of a freshly black-on-white-rendered sample of `text`
    in `font` - the "known weight" reference point _estimate_is_bold()
    compares the REAL region's observed ink ratio against."""
    from PIL import Image, ImageDraw

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = probe.textbbox((0, 0), text, font=font)
    width = max(1, bbox[2] - bbox[0] + 4)
    height = max(1, bbox[3] - bbox[1] + 4)
    sample = Image.new("RGB", (width, height), "white")
    ImageDraw.Draw(sample).text((2, 2), text, fill="black", font=font)
    return _ink_ratio(sample, 0, 0, width, height, (255, 255, 255))


def _estimate_is_bold(image, region: OcrTextRegion, background: tuple[int, int, int], candidate_text: str) -> bool:
    """Guess whether `region`'s ORIGINAL text (still present in `image` -
    the caller must pass an image where this region hasn't been
    overwritten/inpainted yet) was set in a bold weight, so the
    translated replacement can be drawn in the same weight instead of
    _load_font()'s old always-Regular default.

    Real regions (JPEG noise, anti-aliasing, colored/patterned
    backgrounds, decorative surrounding graphics) never look like a clean
    synthetic render - an ABSOLUTE ink-ratio threshold ("bold if ink
    ratio > X") calibrated on one image would not transfer to another.
    Instead this renders a comparison string once in Regular and once in
    Bold at a comparable size (_initial_font_size()) and picks whichever
    synthetic ink ratio the real region's OWN observed ink ratio sits
    closer to.

    That comparison string is `region.text` - the ORIGINAL recognized
    text - whenever OCR actually found one, NOT `candidate_text` (the
    TRANSLATED text) despite that being what will actually get drawn.
    This matters: `observed` is measured from the ORIGINAL glyphs still
    sitting in `image`, so the fairest possible comparison renders the
    SAME string synthetically, isolating font weight as the only
    remaining variable. An early version of this function used
    `candidate_text` instead and was measurably less reliable in
    practice (RoadMap.md/Backlog.md 21.08.2026): a real region confirmed
    bold by eye flipped between correctly- and incorrectly-classified
    across otherwise-equivalent German candidate strings ("Das ist
    fetter Text" correctly -> bold, "Fetter Beispieltext" incorrectly ->
    regular, same region, same image) purely because different letters
    carry different natural ink density, a confound `region.text` avoids
    entirely. `candidate_text` is still the fallback for a region with no
    original text at all - a manually-drawn box from the correction UI
    (ui/image_correction_dialog.py's "Neue Box hinzufügen") - where there
    is no original glyph content to compare against in the first place.

    Exploratory heuristic, not a guarantee (RoadMap.md/Backlog.md
    21.08.2026: the user explicitly asked for this knowing "Aufwand
    unklar, kein Fidelity-Garant") - an unusual original font or a very
    noisy/textured background can still produce the wrong guess.
    Defaults to False (Regular) whenever the comparison can't
    discriminate at all (no text at all to compare against, or
    _load_font() silently fell back to the same file for both weights
    because Bold isn't installed on this system).
    """
    sample_text = region.text if region.text.strip() else candidate_text
    if not sample_text.strip():
        return False
    size = _initial_font_size(region)
    regular_font = _load_font(size, bold=False)
    bold_font = _load_font(size, bold=True)
    regular_ratio = _synthetic_ink_ratio(sample_text, regular_font)
    bold_ratio = _synthetic_ink_ratio(sample_text, bold_font)
    if regular_ratio == bold_ratio:
        return False
    observed = _ink_ratio(image, region.x, region.y, region.width, region.height, background)
    return abs(observed - bold_ratio) < abs(observed - regular_ratio)


# Multiple of region.height used as the vertical-growth ceiling when
# _vertical_room_below() finds no OTHER translated region below this one
# in the same horizontal band (last line in a box, or nothing else
# recognized/translated further down that column) - generous, since
# there is no real neighbour to protect against, but still bounded so a
# short lone region near the image's bottom edge doesn't effectively
# claim unlimited height. Same value as
# pipeline.images.translate_image.DEFAULT_MAX_HEIGHT_RATIO by
# coincidence of both being "how far past one line is still plausible",
# not because the two are the same computation.
_NO_NEIGHBOR_HEIGHT_ALLOWANCE = 4.0

# Pixels of breathing room _vertical_room_below() subtracts from the raw
# gap to the nearest region below - so wrapped/shrunk text stops just
# short of touching that region's own top edge rather than landing
# exactly on it.
_VERTICAL_SAFETY_MARGIN = 3


def _vertical_room_below(region: OcrTextRegion, other_regions: list[OcrTextRegion]) -> float:
    """How far `region`'s drawn text may extend downward (from
    `region.y`) before reaching the nearest OTHER region below it in the
    same horizontal band, minus _VERTICAL_SAFETY_MARGIN - the `max_height`
    every InpaintingBackend.apply() below passes to _draw_fitted_text()
    instead of region.height directly.

    Added after a real user-reported infographic (RoadMap.md/Backlog.md,
    21.08.2026) with very tight line spacing (a multi-tier bullet list
    with only a few pixels between one recognized line and the next):
    region.height alone is this project's ORIGINAL, single-line English
    text's height - frequently far too little room once a translated
    (typically longer) text needs to wrap to a second line, and
    _fit_text()'s shrink-to-fit accepted that overflow rather than
    shrinking into illegibility (see that function's own docstring). But
    accepting it blindly meant overflowing text collided with whatever
    real, still-visible content - translated or original - sat in the
    very next line, a few pixels below.

    "Same horizontal band" (their x-ranges actually overlap) matters so a
    sidebar box's constraining neighbour is the next line INSIDE that
    same sidebar box, never some unrelated line in the main column merely
    sitting at a similar height. Falls back to a generous multiple of
    `region.height` (_NO_NEIGHBOR_HEIGHT_ALLOWANCE) when no such neighbour
    exists at all.

    Known remaining gap: `other_regions` is only ever the CURRENT run's
    successfully TRANSLATED regions (every InpaintingBackend.apply()
    passes `[r.region for r in replacements]`) - a region OCR recognized
    but skipped (low confidence or an outlier height, see
    pipeline.images.translate_image), or text OCR never detected at all,
    still occupies real space in the image but isn't counted here, so a
    translated region can still overflow into either of those. Left as a
    known limitation rather than threading the full skipped-region list
    through InpaintingBackend.apply()'s existing signature.
    """
    region_bottom = region.y + region.height
    best_gap: float | None = None
    for other in other_regions:
        if other is region:
            continue
        if other.x + other.width <= region.x or other.x >= region.x + region.width:
            continue  # no horizontal overlap - a different column/box
        if other.y < region_bottom:
            continue  # not actually below (overlaps or sits above)
        gap = other.y - region_bottom
        if best_gap is None or gap < best_gap:
            best_gap = gap
    if best_gap is None:
        return region.height * _NO_NEIGHBOR_HEIGHT_ALLOWANCE
    return max(best_gap - _VERTICAL_SAFETY_MARGIN, 1)


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
        all_regions = [r.region for r in replacements]
        for replacement in replacements:
            region = replacement.region
            background = _sample_background_color(image, region.x, region.y, region.width, region.height)
            # Bold estimation reads `image`'s CURRENT pixels at this
            # region - must happen before draw.rectangle() below
            # overwrites them, or there is nothing left to estimate from.
            is_bold = _estimate_is_bold(image, region, background, replacement.translated_text)
            draw.rectangle(
                [region.x, region.y, region.x + region.width, region.y + region.height],
                fill=background,
            )
            text_color = _contrasting_text_color(background)
            max_height = _vertical_room_below(region, all_regions)
            _draw_fitted_text(
                draw, region, replacement.translated_text, text_color, image.height, max_height, bold=is_bold
            )

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
        all_regions = [r.region for r in replacements]
        for replacement in replacements:
            region = replacement.region
            # The interior itself is now a valid background estimate
            # (cv2.inpaint() already reconstructed it) - sampling the
            # RECONSTRUCTED interior directly for text-color contrast,
            # rather than BoxOverlayBackend's outside-ring sample, which
            # would still be correct here too but is a needless detour
            # now that the interior itself is meaningful.
            background = _average_region_color(result, region.x, region.y, region.width, region.height)
            # `pil_image` (unlike `result`) was never touched by
            # cv2.inpaint() - still holds the ORIGINAL, un-reconstructed
            # glyph pixels this region's boldness has to be estimated
            # from; `background` still comes from the RECONSTRUCTED
            # `result` (the best available background-color estimate).
            is_bold = _estimate_is_bold(pil_image, region, background, replacement.translated_text)
            text_color = _contrasting_text_color(background)
            max_height = _vertical_room_below(region, all_regions)
            _draw_fitted_text(
                draw, region, replacement.translated_text, text_color, result.height, max_height, bold=is_bold
            )

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

        # Kept around ONLY for _estimate_is_bold() below, which needs the
        # ORIGINAL, not-yet-reconstructed glyph pixels - `image` itself
        # gets REASSIGNED to the model's output a few lines down (not
        # mutated in place), so this reference has to be captured first or
        # it would be lost once that reassignment happens.
        original_image = image
        if replacements:
            mask = _build_inpainting_mask(image.size, replacements)
            model = _get_lama_model(torch, SimpleLama)
            try:
                image = model(image, mask).convert("RGB")
            except Exception as exc:
                raise InpaintingError(f"KI-Inpainting fehlgeschlagen: {exc}") from exc

        draw = ImageDraw.Draw(image)
        all_regions = [r.region for r in replacements]
        for replacement in replacements:
            region = replacement.region
            # The model's own reconstructed interior is now a valid
            # background estimate (same reasoning as CvInpaintingBackend
            # above) - sampled directly rather than BoxOverlayBackend's
            # outside-ring approach.
            background = _average_region_color(image, region.x, region.y, region.width, region.height)
            is_bold = _estimate_is_bold(original_image, region, background, replacement.translated_text)
            text_color = _contrasting_text_color(background)
            max_height = _vertical_room_below(region, all_regions)
            _draw_fitted_text(
                draw, region, replacement.translated_text, text_color, image.height, max_height, bold=is_bold
            )

        try:
            image.save(output_path)
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht gespeichert werden: {exc}") from exc
