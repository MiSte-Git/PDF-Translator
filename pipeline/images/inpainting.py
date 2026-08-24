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

Font-Auswahl (Familie/Fett/Kursiv) ist seit 22.08.2026 nach
pipeline/images/font_style.py ausgelagert (RoadMap.md Phase 3,
"...echte Schrifterkennung (Font-Matching) weiterhin offen" - siehe
dessen Moduldoc für die volle Begründung/Methodik). Diese Datei bleibt für
Layout/Rückschreibe-Mechanik zuständig (Zeilenumbruch, Schrumpf-zu-Passt-
Schleife, Kollisionsvermeidung, Hintergrund-Rekonstruktion) und importiert
Stil-Erkennung von dort, statt sie selbst zu duplizieren.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pipeline.images.font_style import classify_bold, estimate_font_style
from pipeline.images.font_style import load_font as _load_font
from pipeline.images.ocr import OcrTextRegion, region_line_height

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

# Breite des Rings außerhalb der Bounding-Box, aus dem die
# Hintergrundfarbe geschätzt wird (siehe _sample_background_color()).
_BACKGROUND_SAMPLE_MARGIN = 4

# Ab welcher euklidischen RGB-Distanz zwischen dem Rand-Mittel der Box-
# Ober-/Unterseite bzw. Links-/Rechtsseite ein Verlauf statt eines
# einfarbigen Hintergrunds angenommen wird (siehe _sample_background()) -
# 22.08.2026, Michael: "die sollten wir so wie auf das von Google bringen"
# (Google-Translate-Bildvergleich, Layout-Genauigkeit). Bewusst moderat
# gewählt: JPEG-Rauschen/Kompressionsartefakte in einer scheinbar
# einfarbigen Fläche liegen typischerweise deutlich darunter, ein
# tatsächlich gestalteter Farbverlauf (Infografik-Bänder, Farbverläufe in
# Icons/Grafiken) deutlich darüber - kein an echten Bildern kalibrierter
# Wert (anders als z. B. _INK_LUMINANCE_THRESHOLD in font_style.py),
# sondern eine bewusst konservative Schätzung, die im Zweifel eher zu
# einer flachen Füllung (dem bisherigen, bekannten Verhalten) als zu einem
# unnötigen/falschen Verlauf tendiert.
_GRADIENT_DETECTION_THRESHOLD = 18.0

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

    def apply(
        self,
        image_path: str,
        replacements: list[TextReplacement],
        output_path: str,
        obstacle_regions: list[OcrTextRegion] | None = None,
    ) -> None:
        """Write a copy of the image at `image_path` to `output_path`,
        with each replacement's region overwritten by its
        `translated_text`. Regions not covered by `replacements` (e.g.
        because the user only selected some of the recognized lines) are
        left byte-for-byte untouched.

        `obstacle_regions` (22.08.2026, closes the gap documented in
        _vertical_room_below()'s docstring until this date - real user,
        same real infographic that motivated _vertical_room_below() in
        the first place: "Boxen überlappen oder sind an falscher Stelle")
        - regions that are NOT drawn/translated here (typically OCR
        recognized them but translate_image() skipped or failed them, see
        pipeline.images.translate_image) but whose ORIGINAL pixels are
        still visible in the output, so they must still be treated as
        collision obstacles for `replacements`' own text placement. Pass
        `None` (the default) when there are no such regions to protect,
        e.g. run_image_correction_job()'s direct apply() call, whose
        `replacements` list is already the complete, user-approved final
        set - see that function's docstring for why it doesn't compute
        this itself.
        """
        ...


# _load_font() (bold=/family=/italic=) ist seit 22.08.2026 pipeline.
# images.font_style.load_font() - hier oben als _load_font importiert, so
# dass bestehende Aufrufer/Tests (die den Namen `_load_font` in diesem
# Modul erwarten, u. a. tests/test_image_inpainting.py's monkeypatch-Spy)
# unverändert funktionieren. Mit nur `bold=` aufgerufen (family=/italic=
# auf Default belassen) verhält es sich exakt wie die alte, hier vorher
# lokal definierte Fassung (18.08.2026: nur DejaVu Sans Regular/Bold).


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
    sample without duplicating the *0.8 conversion.

    Uses pipeline.images.ocr.region_line_height() instead of
    `region.height` directly (22.08.2026, see OcrTextRegion.line_height's
    docstring; centralized into that shared helper 23.08.2026 once
    GoogleVisionOcrEngine/PaddleOcrEngine became a second source of
    multi-line regions - see its own docstring) - a region whose `height`
    spans EVERY merged/grouped original line together, not one line's
    glyph height, would otherwise seed a font sized for the whole block,
    several times too large. Every other region (line_height is None)
    behaves exactly as before.
    """
    return min(max(_MIN_FONT_SIZE, int(region_line_height(region) * 0.8)), _MAX_FONT_SIZE)


def _fit_text(
    draw,
    text: str,
    region: OcrTextRegion,
    max_height: float,
    bold: bool = False,
    family: str = "sans_serif",
    italic: bool = False,
    left_room: float = 0.0,
    right_room: float = 0.0,
) -> tuple[list[str], object, int, float]:
    """Pick the largest font size - starting from _initial_font_size()'s
    region-height-derived size, in the requested weight/family/slant
    (`bold`/`family`/`italic` - see pipeline.images.font_style.
    estimate_font_style()) - that, once `text` is word-wrapped to
    region.width, fits within `max_height` without shrinking past
    _MIN_FONT_SIZE.

    This is primarily a SHRINK-to-fit strategy, deliberately never a
    GROW-the-box-DOWNWARD one: growing past `max_height` to fit more
    wrapped lines would risk the box encroaching on whatever sits just
    below it - which is exactly what `max_height` itself is computed to
    leave room for (see _vertical_room_below(), whose result every
    caller below passes here instead of region.height directly - a real
    risk in tightly line-spaced screenshots/infographics, see the
    Backlog.md 18.08.2026 and 21.08.2026 finds that motivated this
    function and this parameter, respectively).

    23.08.2026: if even _MIN_FONT_SIZE still doesn't fit `max_height`,
    this now tries ONE more thing before accepting the overflow - widen
    the wrap width using `left_room`/`right_room` (see
    _horizontal_room(), whose result every caller below passes here),
    the pixel room genuinely free to the region's left/right (real user
    report, QA-Bericht "(12)": a footer text got cut off at the image's
    bottom edge, exactly the case this used to just accept - "Der Text
    könnte ohne weiteres nach links... und... nach rechts erweitert
    werden. Links und Rechts davon ist nichts."). RIGHT room is tried
    first (needs no change to where the box's left edge is drawn), LEFT
    room only for whatever RIGHT room alone couldn't cover - see the
    x_offset return value. If even the full available width (region.width
    + left_room + right_room) still doesn't fit, or there simply is no
    room on either side, the old behaviour is unchanged: the overflow is
    accepted rather than shrinking font further into illegibility,
    mirroring the PDF pipeline's own insert_text() "always make it fit
    somewhere" policy (see pipeline/pdf/pymupdf_engine.py).

    Returns (lines, font, line_height, x_offset) - the caller draws each
    line at `(region.x + x_offset, region.y + i * line_height)`.
    `x_offset` is always <= 0 (this never shifts the box rightward - a
    wider wrap width used entirely from `right_room` needs no shift at
    all) and is exactly 0.0 whenever the shrink loop alone already fit,
    i.e. for every region this behaved the same for before 23.08.2026.
    """
    size = _initial_font_size(region)
    while True:
        font = _load_font(size, bold=bold, family=family, italic=italic)
        lines = _wrap_text_to_width(draw, text, font, max(region.width, 1))
        line_height = max(1, int(size * _LINE_SPACING))
        total_height = line_height * len(lines)
        if total_height <= max_height or size <= _MIN_FONT_SIZE:
            break
        size = max(_MIN_FONT_SIZE, size - 2)

    if total_height <= max_height:
        return lines, font, line_height, 0.0

    extra_total = left_room + right_room
    if extra_total <= 0:
        return lines, font, line_height, 0.0

    # Coarse search: grow the wrap width in _HORIZONTAL_FIT_STEPS steps
    # from region.width up to region.width + extra_total, stopping at the
    # first (narrowest) step that fits - or falling through to the
    # widest attempt as a best-effort if none do.
    step = max(extra_total / _HORIZONTAL_FIT_STEPS, 1.0)
    extra = 0.0
    while True:
        extra = min(extra + step, extra_total)
        width = max(region.width + extra, 1)
        candidate_lines = _wrap_text_to_width(draw, text, font, width)
        candidate_height = line_height * len(candidate_lines)
        if candidate_height <= max_height or extra >= extra_total:
            lines = candidate_lines
            break

    extra_right = min(extra, right_room)
    extra_left = extra - extra_right
    return lines, font, line_height, -extra_left


def _draw_fitted_text(
    draw,
    region: OcrTextRegion,
    text: str,
    color: tuple[int, int, int],
    image_height: int,
    max_height: float,
    bold: bool = False,
    family: str = "sans_serif",
    italic: bool = False,
    left_room: float = 0.0,
    right_room: float = 0.0,
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

    `bold`/`family`/`italic` (see pipeline.images.font_style.
    estimate_font_style(), 22.08.2026) pick the font variant for the WHOLE
    wrapped block - every InpaintingBackend.apply() below estimates this
    ONCE per region, from the original (pre-overwrite) pixels, before
    calling here.

    `left_room`/`right_room` (23.08.2026, see _horizontal_room()) are the
    pixel room genuinely free to `region`'s left/right - passed straight
    through to _fit_text(), whose x_offset return value shifts where
    drawing starts. Both default to 0.0 (no widening, identical to the
    pre-23.08.2026 behaviour) for any caller that doesn't pass them.
    Note this widened margin is NOT covered by whatever background
    reconstruction (mask-based inpainting or the outside-ring color fill)
    happened before this call - only ever built from `region`'s own
    original box - so this is safe/invisible specifically when that
    margin genuinely has nothing else drawn in it already, exactly the
    real case that motivated this (a real user confirmed the two
    directions used here were empty margin, not unknown content).
    """
    lines, font, line_height, x_offset = _fit_text(
        draw, text, region, max_height, bold=bold, family=family, italic=italic,
        left_room=left_room, right_room=right_room,
    )
    x = region.x + x_offset
    y = region.y
    for line in lines:
        if y >= image_height:
            break
        draw.text((x, y), line, fill=color, font=font)
        y += line_height


def _estimate_is_bold(image, region: OcrTextRegion, background: tuple[int, int, int], candidate_text: str) -> bool:
    """Guess whether `region`'s ORIGINAL text (still present in `image` -
    the caller must pass an image where this region hasn't been
    overwritten/inpainted yet) was set in a bold weight.

    Thin, sans-serif-fixed wrapper around pipeline.images.font_style.
    classify_bold() (22.08.2026) - kept here, under its original name and
    4-argument signature, for backward compatibility (this module's own
    tests, and any other existing caller, import/call it exactly as
    before). The three InpaintingBackend.apply() implementations below no
    longer call this directly since 22.08.2026 - they call
    pipeline.images.font_style.estimate_font_style() instead, which
    additionally classifies FAMILY (serif/sans-serif) and ITALIC, using
    this same bold-classification method but against the correct family's
    synthetic references rather than always DejaVu Sans. See that
    module's docstring for the full methodology (RoadMap.md Phase 3,
    Font-Matching) - this function's own original 21.08.2026 docstring
    (RELATIVE ink-ratio comparison against synthetic Regular/Bold
    references, `region.text` over `candidate_text` when available,
    exploratory heuristic not a guarantee) still applies unchanged, since
    the underlying algorithm is untouched, just relocated and
    family-parameterized.
    """
    return classify_bold(image, region, background, candidate_text, _initial_font_size(region), family="sans_serif")


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

    Until 22.08.2026, `other_regions` was only ever the CURRENT run's
    successfully TRANSLATED regions (every InpaintingBackend.apply()
    passed just `[r.region for r in replacements]`) - a region OCR
    recognized but skipped (low confidence or an outlier height, see
    pipeline.images.translate_image) or failed (the provider call itself
    raised) still occupies real space in the image, since neither is
    drawn over, but wasn't counted here, so a translated region could
    still overflow into either of those - confirmed as a real
    contributor to a user-reported garbled/overlapping output (Backlog.md
    22.08.2026: real infographic, GPU-Inpainting backend, "Boxen
    überlappen"). Every InpaintingBackend.apply() implementation below
    now also folds its `obstacle_regions` parameter into the list passed
    here (see that parameter's docstring on the Protocol), so this
    function itself never needed to change - only what its callers pass
    it. Text OCR never detected at all (no OcrTextRegion exists for it)
    remains outside what this function can possibly know about - not a
    gap this fix (or any purely OCR-region-based one) can close.
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


# Same idea as _VERTICAL_SAFETY_MARGIN, for _horizontal_room() below.
_HORIZONTAL_SAFETY_MARGIN = 3

# Coarse-search step count _fit_text() uses when widening a box
# horizontally (see its own docstring for when this triggers) - not a
# real-image-calibrated constant, just a resolution/speed tradeoff for
# the wrap-and-measure search: fine enough that the found width doesn't
# noticeably overshoot what was actually needed, coarse enough that a
# very wide available room (a mostly-empty row) doesn't cost more than
# a handful of _wrap_text_to_width() calls.
_HORIZONTAL_FIT_STEPS = 8


def _horizontal_room(
    region: OcrTextRegion, other_regions: list[OcrTextRegion], image_width: int
) -> tuple[float, float]:
    """How far `region`'s box may extend LEFT and RIGHT (independently)
    before reaching the nearest OTHER region in the same VERTICAL band
    (their y-ranges actually overlap - mirrors _vertical_room_below()'s
    "same horizontal band" check, just the other axis) or the image's
    own left/right edge, minus _HORIZONTAL_SAFETY_MARGIN each.

    Added 23.08.2026 after Michael's real report (QA-Bericht "(12)",
    "Spirit - Soul - Meatsuit.jpg"): the two footer text boxes each sit
    alone in their own row with nothing beside them but the chalice icon
    between them and empty margin outside - "Der Text könnte ohne
    weiteres nach links auf der einen Seite und auf der anderen Seite
    des Kelches nach rechts erweitert werden. Links und Rechts davon ist
    nichts." `_fit_text()` uses this as a FALLBACK, only once its
    existing shrink-to-_MIN_FONT_SIZE loop still doesn't fit
    `max_height` - widening is a last resort, same "don't change
    behaviour for the common case" reasoning as _vertical_room_below()'s
    own docstring.

    Unlike _vertical_room_below(), there is no "generous multiple of
    region.<axis>" fallback for "no neighbour found": the image's own
    edge is ALWAYS a real, hard constraint on this axis (nothing
    equivalent to _draw_fitted_text()'s image_height safety-clip exists
    for the horizontal direction), so both returned values are capped by
    the image bounds from the start rather than only checked separately.

    Same known gap as _vertical_room_below(): a non-translated block
    (e.g. a PaddleOCR "image"-labeled layout block, discarded before
    ever becoming an OcrTextRegion - see pipeline/images/ocr.py::
    PaddleOcrEngine) is invisible here too - this can only ever protect
    against OTHER TEXT regions, not arbitrary graphic content sitting to
    either side.
    """
    region_left = region.x
    region_right = region.x + region.width
    left_room = float(region_left)
    right_room = float(image_width - region_right)
    for other in other_regions:
        if other is region:
            continue
        if other.y + other.height <= region.y or other.y >= region.y + region.height:
            continue  # no vertical overlap - a different row
        if other.x + other.width <= region_left:
            left_room = min(left_room, region_left - (other.x + other.width))
        elif other.x >= region_right:
            right_room = min(right_room, other.x - region_right)
        # else: overlaps this region's own column too - already colliding
        # on this axis regardless of width, not this function's problem.
    return (
        max(left_room - _HORIZONTAL_SAFETY_MARGIN, 0.0),
        max(right_room - _HORIZONTAL_SAFETY_MARGIN, 0.0),
    )


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


@dataclass(frozen=True)
class GradientBackground:
    """A simple two-stop linear gradient along one axis - what
    _sample_background() (below) returns instead of a flat color when the
    box's surroundings clearly aren't uniform (RoadMap.md Phase 3,
    22.08.2026: "Textregionen, Leserichtung, Schrift, Farbe und
    Hintergrund erfassen" - Michael, after a Google-Translate-Bildvergleich:
    "die sollten wir so wie auf das von Google bringen"). Deliberately
    only horizontal/vertical two-stop gradients, not diagonal or radial
    ones - covers the common case (color bars, simple accent fades in
    infographics/UI design) without the substantially more sampling a
    general 2D gradient fit would need; a diagonal/radial gradient still
    gets SOME improvement (an approximated H/V gradient beats a flat
    average) but not a faithful reconstruction. `BoxOverlayBackend` is the
    only consumer - `CvInpaintingBackend`/`GpuInpaintingBackend` already
    reconstruct gradients (and far more complex backgrounds) via real
    inpainting, so they have no use for this simpler approximation.
    """

    axis: str  # "vertical" (top->bottom) or "horizontal" (left->right)
    start: tuple[int, int, int]
    end: tuple[int, int, int]


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Plain Euclidean RGB distance - used only to decide "flat enough to
    treat as one color" vs "visibly a gradient" (see
    _GRADIENT_DETECTION_THRESHOLD's docstring), not for anything requiring
    perceptual color-space accuracy."""
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def _sample_background(
    image, x: int, y: int, width: int, height: int
) -> tuple[int, int, int] | GradientBackground:
    """Like _sample_background_color() (unchanged, still used for its own
    sake - see that function's docstring for the ring-sampling rationale
    shared here), but samples the TOP/BOTTOM/LEFT/RIGHT ring strips
    SEPARATELY instead of averaging all of them into one color, and
    returns a GradientBackground along whichever axis shows the larger
    color difference once that difference clears
    _GRADIENT_DETECTION_THRESHOLD - otherwise the plain flat average
    (backward-compatible with the common, uniform-background case).
    """
    img_w, img_h = image.size
    x0 = max(0, x - _BACKGROUND_SAMPLE_MARGIN)
    y0 = max(0, y - _BACKGROUND_SAMPLE_MARGIN)
    x1 = min(img_w, x + width + _BACKGROUND_SAMPLE_MARGIN)
    y1 = min(img_h, y + height + _BACKGROUND_SAMPLE_MARGIN)
    pixels = image.load()

    def _average(samples: list[tuple[int, int, int]]) -> tuple[int, int, int] | None:
        if not samples:
            return None
        r = sum(s[0] for s in samples) // len(samples)
        g = sum(s[1] for s in samples) // len(samples)
        b = sum(s[2] for s in samples) // len(samples)
        return (r, g, b)

    top = _average([pixels[px, y0] for px in range(x0, x1) if y0 < y])
    bottom = _average([pixels[px, y1 - 1] for px in range(x0, x1) if y1 - 1 >= y + height and y1 - 1 < img_h])
    left = _average([pixels[x0, py] for py in range(max(y0, y), min(y1, y + height)) if x0 < x])
    right = _average(
        [pixels[x1 - 1, py] for py in range(max(y0, y), min(y1, y + height)) if x1 - 1 >= x + width and x1 - 1 < img_w]
    )

    vertical_delta = _color_distance(top, bottom) if top and bottom else 0.0
    horizontal_delta = _color_distance(left, right) if left and right else 0.0

    if max(vertical_delta, horizontal_delta) >= _GRADIENT_DETECTION_THRESHOLD:
        if vertical_delta >= horizontal_delta:
            return GradientBackground(axis="vertical", start=top, end=bottom)
        return GradientBackground(axis="horizontal", start=left, end=right)

    return _sample_background_color(image, x, y, width, height)


def _representative_color(background: tuple[int, int, int] | GradientBackground) -> tuple[int, int, int]:
    """A single flat color standing in for `background` - the midpoint of
    its two stops for a GradientBackground, itself unchanged for a flat
    tuple. Used wherever a single reference color is genuinely needed
    (text-color contrast, font-style classification's background
    baseline) even though the actual FILL may be a gradient."""
    if isinstance(background, tuple):
        return background
    return tuple(round((background.start[i] + background.end[i]) / 2) for i in range(3))


def _lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _fill_gradient_rect(draw, x0: int, y0: int, x1: int, y1: int, gradient: GradientBackground) -> None:
    """Fills [x0, x1) x [y0, y1) with a linear interpolation between
    `gradient.start` and `gradient.end` along `gradient.axis` - one
    draw.line() per row (vertical axis) or column (horizontal axis), the
    simplest way to approximate a gradient fill with plain PIL (no native
    gradient-fill primitive, no new dependency)."""
    if gradient.axis == "vertical":
        span = max(1, y1 - y0)
        for i in range(y1 - y0):
            t = i / max(1, span - 1)
            draw.line([(x0, y0 + i), (x1, y0 + i)], fill=_lerp_color(gradient.start, gradient.end, t))
    else:
        span = max(1, x1 - x0)
        for i in range(x1 - x0):
            t = i / max(1, span - 1)
            draw.line([(x0 + i, y0), (x0 + i, y1)], fill=_lerp_color(gradient.start, gradient.end, t))


class BoxOverlayBackend:
    """InpaintingBackend that overwrites each region with a sampled
    background (a flat color, or - since 22.08.2026, RoadMap.md Phase 3 -
    a simple linear gradient when the surroundings clearly call for one,
    see _sample_background()), then draws the translated text on top -
    the box-overlay approach documented in RoadMap.md Phase 3 as the
    always-available default (no new dependency, works everywhere), with
    the known remaining limitation that it reads as a visible "patch"
    over genuinely photographic or texture-rich backgrounds (a simple
    two-stop gradient fill narrows, but does not eliminate, that gap).
    """

    def apply(
        self,
        image_path: str,
        replacements: list[TextReplacement],
        output_path: str,
        obstacle_regions: list[OcrTextRegion] | None = None,
    ) -> None:
        from PIL import Image, ImageDraw

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht geöffnet werden: {exc}") from exc

        draw = ImageDraw.Draw(image)
        all_regions = [r.region for r in replacements] + list(obstacle_regions or [])
        for replacement in replacements:
            region = replacement.region
            background = _sample_background(image, region.x, region.y, region.width, region.height)
            background_color = _representative_color(background)
            # Style estimation reads `image`'s CURRENT pixels at this
            # region - must happen before the fill below overwrites them,
            # or there is nothing left to estimate from.
            style = estimate_font_style(
                image, region, background_color, replacement.translated_text, _initial_font_size(region)
            )
            box = [region.x, region.y, region.x + region.width, region.y + region.height]
            if isinstance(background, GradientBackground):
                _fill_gradient_rect(draw, box[0], box[1], box[2], box[3], background)
            else:
                draw.rectangle(box, fill=background)
            text_color = _contrasting_text_color(background_color)
            max_height = _vertical_room_below(region, all_regions)
            left_room, right_room = _horizontal_room(region, all_regions, image.width)
            _draw_fitted_text(
                draw,
                region,
                replacement.translated_text,
                text_color,
                image.height,
                max_height,
                bold=style.bold,
                family=style.family,
                italic=style.italic,
                left_room=left_room,
                right_room=right_room,
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

    def apply(
        self,
        image_path: str,
        replacements: list[TextReplacement],
        output_path: str,
        obstacle_regions: list[OcrTextRegion] | None = None,
    ) -> None:
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
        all_regions = [r.region for r in replacements] + list(obstacle_regions or [])
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
            # glyph pixels this region's style has to be estimated from;
            # `background` still comes from the RECONSTRUCTED `result`
            # (the best available background-color estimate).
            style = estimate_font_style(
                pil_image, region, background, replacement.translated_text, _initial_font_size(region)
            )
            text_color = _contrasting_text_color(background)
            max_height = _vertical_room_below(region, all_regions)
            left_room, right_room = _horizontal_room(region, all_regions, result.width)
            _draw_fitted_text(
                draw,
                region,
                replacement.translated_text,
                text_color,
                result.height,
                max_height,
                bold=style.bold,
                family=style.family,
                italic=style.italic,
                left_room=left_room,
                right_room=right_room,
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

    def apply(
        self,
        image_path: str,
        replacements: list[TextReplacement],
        output_path: str,
        obstacle_regions: list[OcrTextRegion] | None = None,
    ) -> None:
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

        # Kept around ONLY for estimate_font_style() below, which needs
        # the ORIGINAL, not-yet-reconstructed glyph pixels - `image`
        # itself gets REASSIGNED to the model's output a few lines down
        # (not mutated in place), so this reference has to be captured
        # first or it would be lost once that reassignment happens.
        original_image = image
        if replacements:
            mask = _build_inpainting_mask(image.size, replacements)
            model = _get_lama_model(torch, SimpleLama)
            try:
                image = model(image, mask).convert("RGB")
            except Exception as exc:
                raise InpaintingError(f"KI-Inpainting fehlgeschlagen: {exc}") from exc

        draw = ImageDraw.Draw(image)
        all_regions = [r.region for r in replacements] + list(obstacle_regions or [])
        for replacement in replacements:
            region = replacement.region
            # The model's own reconstructed interior is now a valid
            # background estimate (same reasoning as CvInpaintingBackend
            # above) - sampled directly rather than BoxOverlayBackend's
            # outside-ring approach.
            background = _average_region_color(image, region.x, region.y, region.width, region.height)
            style = estimate_font_style(
                original_image, region, background, replacement.translated_text, _initial_font_size(region)
            )
            text_color = _contrasting_text_color(background)
            max_height = _vertical_room_below(region, all_regions)
            left_room, right_room = _horizontal_room(region, all_regions, image.width)
            _draw_fitted_text(
                draw,
                region,
                replacement.translated_text,
                text_color,
                image.height,
                max_height,
                bold=style.bold,
                family=style.family,
                italic=style.italic,
                left_room=left_room,
                right_room=right_room,
            )

        try:
            image.save(output_path)
        except Exception as exc:
            raise InpaintingError(f"Bild konnte nicht gespeichert werden: {exc}") from exc
