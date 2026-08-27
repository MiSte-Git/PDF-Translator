"""Regression coverage for the Box-Overlay-Rückschreibung (RoadMap.md
Phase 3), pipeline/images/inpainting.py.

Where practical, verification goes through the REAL Tesseract OCR engine
on the produced output image (not just pixel inspection) - the same
"verify against what actually happens, not just what the code claims to
do" discipline used throughout this project's PDF tests (e.g. checking
the actually-saved PDF's font names, not just the function's return
value).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.inpainting import (
    _MAX_FONT_SIZE,
    _MIN_FONT_SIZE,
    BoxOverlayBackend,
    GradientBackground,
    InpaintingError,
    TextReplacement,
    _color_distance,
    _contrasting_text_color,
    _draw_fitted_text,
    _estimate_is_bold,
    _fill_gradient_rect,
    _fit_text,
    _horizontal_room,
    _initial_font_size,
    _load_font,
    _representative_color,
    _sample_background,
    _sample_background_color,
    _wrap_text_to_width,
)
from pipeline.images.ocr import OcrTextRegion, TesseractOcrEngine, tesseract_available

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


def _build_dark_background_image(path: Path) -> None:
    """Dark background, light text - so _contrasting_text_color() must
    pick white, not the black default a naive implementation might use.
    """
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (300, 100), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    draw.text((20, 30), "Bright Text", fill=(230, 230, 230), font=font)
    image.save(path)


# --- _sample_background_color() / _contrasting_text_color() ---------------


def test_sample_background_color_matches_solid_surrounding() -> None:
    image = Image.new("RGB", (100, 100), (200, 50, 50))
    color = _sample_background_color(image, x=40, y=40, width=20, height=20)
    assert color == (200, 50, 50)


def test_sample_background_color_ignores_box_interior() -> None:
    """A box painted solid black in the middle of a white image must NOT
    pull the sampled color toward black - the sample ring sits OUTSIDE
    the box, not inside it.
    """
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([40, 40, 60, 60], fill="black")
    color = _sample_background_color(image, x=40, y=40, width=20, height=20)
    assert color == (255, 255, 255)


def test_contrasting_text_color_picks_black_on_light_background() -> None:
    assert _contrasting_text_color((255, 255, 255)) == (0, 0, 0)


def test_contrasting_text_color_picks_white_on_dark_background() -> None:
    assert _contrasting_text_color((20, 20, 20)) == (255, 255, 255)


# --- BoxOverlayBackend.apply() ---------------------------------------------


def test_apply_raises_inpainting_error_for_missing_source_image(tmp_path: Path) -> None:
    with pytest.raises(InpaintingError):
        BoxOverlayBackend().apply(
            str(tmp_path / "does_not_exist.png"), [], str(tmp_path / "out.png")
        )


def test_apply_leaves_untouched_regions_pixel_identical(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    # Only replace the FIRST line - the second ("Second Line") is not in
    # the replacements list at all.
    replacement = TextReplacement(
        region=OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=95.0),
        translated_text="Hallo Welt",
    )
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    # Crop a region well below the first line, covering the untouched
    # second line plus surrounding whitespace, and compare byte-for-byte.
    box = (0, 60, 400, 150)
    # .tobytes() (not .getdata()/.get_flattened_data() - see
    # tests/test_image_cv_inpainting.py's identical comment): stable raw-
    # pixel comparison across every Pillow version.
    assert original.crop(box).tobytes() == result.crop(box).tobytes()


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_apply_replaces_recognized_text_end_to_end(tmp_path: Path) -> None:
    """Full round-trip: OCR the source, replace one recognized line via
    BoxOverlayBackend, then OCR the OUTPUT again - the original text must
    be gone and the translated text must be recognizable in its place.
    """
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    engine = TesseractOcrEngine()
    regions = engine.recognize(str(source))
    first_line = next(r for r in regions if r.text == "Hello World")
    replacement = TextReplacement(region=first_line, translated_text="Hallo Welt")

    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result_regions = engine.recognize(str(output))
    result_texts = [r.text for r in result_regions]
    assert "Hello World" not in result_texts
    assert any("Hallo" in text for text in result_texts)
    # The untouched second line must still be there, unchanged.
    assert "Second Line" in result_texts


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_apply_with_render_box_erases_the_original_position_and_draws_at_the_new_one(
    tmp_path: Path,
) -> None:
    """26.08.2026 regression guard - real user report, Backlog.md 26.08.2026:
    "die Positionen, Grösse und Korrekturen werden nicht übernommen". A
    correction UI (image_translate_cli/review_server.py's browser page or
    ui/image_correction_dialog.py's canvas) moving a box used to overwrite
    `region` directly - which is also what `apply()` uses to erase the
    original source text, so the untranslated English stayed fully
    visible right where it always was, while a disconnected translated
    patch appeared wherever the box had been dragged to. `render_box`
    (see TextReplacement's own docstring) is the fix: `region` stays the
    TRUE original for erasure, `render_box` is only ever a NEW draw
    target. Verified via a real Tesseract round-trip, not just pixel
    inspection - the same "verify against what actually happens"
    discipline this file's own module docstring describes.
    """
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    engine = TesseractOcrEngine()
    regions = engine.recognize(str(source))
    first_line = next(r for r in regions if r.text == "Hello World")
    # Moved well clear of BOTH original lines and of the image edges -
    # into the empty lower-right area of the 400x150 canvas.
    moved_box = OcrTextRegion(
        text=first_line.text, x=250, y=110, width=130, height=30, confidence=first_line.confidence
    )
    replacement = TextReplacement(region=first_line, translated_text="Hallo Welt", render_box=moved_box)

    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result_regions = engine.recognize(str(output))
    result_texts = [r.text for r in result_regions]
    # The untranslated ORIGINAL text must actually be gone from its real
    # position - not just "no longer referenced by anything".
    assert "Hello World" not in result_texts
    # The translated text must appear at the NEW (moved) position.
    moved_hits = [
        r
        for r in result_regions
        if "Hallo" in r.text and r.x >= moved_box.x - 20 and r.y >= moved_box.y - 20
    ]
    assert moved_hits, f"expected translated text near the moved box, got: {result_regions}"
    # The untouched second line must still be there, unchanged.
    assert "Second Line" in result_texts


def test_apply_picks_white_text_on_dark_background(tmp_path: Path) -> None:
    """Regression guard for _contrasting_text_color() actually being used
    inside apply(): on a dark background, the box-overlay fill AND the
    inserted text must both end up in the same dark-background family -
    a naive always-black implementation would render invisible black-on-
    near-black text.
    """
    source = tmp_path / "dark.png"
    _build_dark_background_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Bright Text", x=20, y=30, width=150, height=24, confidence=90.0),
        translated_text="Heller Text",
    )
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result = Image.open(output).convert("RGB")
    # Sample a pixel where a glyph stroke is likely to be (well inside the
    # box, not just the fill) - at least one bright (text) pixel must
    # exist somewhere in the replaced region.
    pixels = result.load()
    region_pixels = [
        pixels[x, y]
        for x in range(20, 170)
        for y in range(30, 54)
    ]
    assert any(sum(p) > 600 for p in region_pixels), "expected at least one bright text pixel"


# --- _wrap_text_to_width() / _fit_text() (RoadMap.md/Backlog.md 18.08.2026:
# real user found translated text overflowing its box's width, since the
# old code always drew the whole translated string on ONE unwrapped line
# regardless of region.width - see this project's Backlog.md for the
# concrete before/after screenshots that motivated this fix) ---------------


def _measure_draw():
    return ImageDraw.Draw(Image.new("RGB", (1, 1)))


def test_wrap_text_to_width_splits_long_line_into_multiple_lines() -> None:
    draw = _measure_draw()
    font = ImageFont.truetype(_FONT_PATH, 20)
    text = "Dies ist ein deutlich längerer übersetzter Text als das Original"

    lines = _wrap_text_to_width(draw, text, font, max_width=150)

    assert len(lines) > 1
    # Every produced line must actually fit within max_width - the whole
    # point of wrapping - except a single word wider than max_width on
    # its own (not the case for any word in this sentence).
    for line in lines:
        assert draw.textlength(line, font=font) <= 150


def test_wrap_text_to_width_never_splits_a_single_word() -> None:
    """A single word wider than max_width by itself still gets its own,
    overflowing line rather than being cut mid-word - see
    _wrap_text_to_width()'s docstring for why."""
    draw = _measure_draw()
    font = ImageFont.truetype(_FONT_PATH, 40)
    word = "Donaudampfschifffahrtsgesellschaftskapitaen"

    lines = _wrap_text_to_width(draw, word, font, max_width=50)

    assert lines == [word]


def test_wrap_text_to_width_handles_empty_text() -> None:
    draw = _measure_draw()
    font = ImageFont.truetype(_FONT_PATH, 20)
    assert _wrap_text_to_width(draw, "", font, max_width=100) == [""]


def test_fit_text_shrinks_font_when_wrapped_block_exceeds_region_height() -> None:
    """A narrow, short region (little width, little height) combined with
    a long translated text must shrink below the naive
    region.height-derived starting size - otherwise the wrapped block
    would need far more vertical space than the region actually has.
    """
    draw = _measure_draw()
    region = OcrTextRegion(text="Hi", x=0, y=0, width=80, height=24, confidence=95.0)
    long_text = "Dies ist ein sehr viel längerer übersetzter Text als im Original vorhanden war"

    lines, font, line_height, x_offset = _fit_text(draw, long_text, region, region.height)

    naive_size = int(region.height * 0.8)
    assert font.size < naive_size
    assert font.size >= _MIN_FONT_SIZE


def test_fit_text_caps_start_size_regardless_of_region_height() -> None:
    """A region with an anomalously large height (e.g. an OCR bounding
    box that accidentally swallowed a neighboring icon/graphic - the
    real cause documented in Backlog.md 18.08.2026) must not translate
    into a giant, page-dominating font just because region.height says
    so - _MAX_FONT_SIZE caps the STARTING size independent of
    region.height.
    """
    draw = _measure_draw()
    region = OcrTextRegion(text="X", x=0, y=0, width=2000, height=500, confidence=95.0)

    lines, font, line_height, x_offset = _fit_text(draw, "Kurzer Text", region, region.height)

    assert font.size <= _MAX_FONT_SIZE


def test_fit_text_returns_single_line_for_short_text_that_already_fits() -> None:
    draw = _measure_draw()
    region = OcrTextRegion(text="Hi", x=0, y=0, width=200, height=24, confidence=95.0)

    lines, font, line_height, x_offset = _fit_text(draw, "Hallo", region, region.height)

    assert lines == ["Hallo"]


def test_apply_wraps_long_translation_instead_of_overflowing_box_width(tmp_path: Path) -> None:
    """End-to-end regression guard for the overflow bug itself: a narrow
    region translated into a much longer string must NOT draw any text
    pixels to the right of the box - a probe strip just past the box's
    right edge, at the same vertical span, must stay pure background.
    """
    image = Image.new("RGB", (500, 100), "white")
    image.save(tmp_path / "source.png")
    source = tmp_path / "source.png"
    output = tmp_path / "out.png"

    # Original box only 120px wide - the old code would have drawn the
    # much longer translated string on one line running far past x=120.
    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=120, height=24, confidence=95.0),
        translated_text="Ein sehr viel längerer übersetzter Text als das kurze Original",
    )
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result = Image.open(output).convert("RGB")
    pixels = result.load()
    # Probe strip well to the right of the box (x=160..480), spanning
    # generously beyond the box's own height too, in case wrapping needed
    # extra lines - must be pure white (background), no text pixel leaked
    # past the box's right edge.
    probe_pixels = [
        pixels[x, y]
        for x in range(160, 480)
        for y in range(20, 100)
    ]
    assert all(p == (255, 255, 255) for p in probe_pixels), (
        "expected no text pixels to the right of the box - translation overflowed its width"
    )


# --- Single-word (unbreakable) translations must also respect box width,
# not just region height (27.08.2026 - real user report, Backlog.md
# 27.08.2026, Michael: "Spirit - Soul - Meatsuit.jpg", "LEDGER"->
# "HAUPTBUCH" rendered far wider than its box, manually corrected or not).
# _wrap_text_to_width() never splits a single word (see its own test
# above), so a one-word translation is always exactly ONE line -
# total_height was therefore always trivially within max_height and
# _fit_text()'s shrink loop broke on its very first iteration, at the
# height-derived starting size, regardless of how narrow region.width
# was. The fix folds a widest-line-fits-region.width check into that same
# loop. --------------------------------------------------------------


def test_fit_text_shrinks_a_single_unbreakable_word_that_overflows_region_width() -> None:
    """A narrow box (width=60) with a generous max_height (mirrors a
    region with no vertical neighbour to constrain it - exactly Michael's
    real case, "LEDGER" sitting alone in open graphic space) and a single
    word that would render far wider than 60px at the height-derived
    starting size. Before this fix, font.size stayed at the naive
    height-derived value and the word overflowed region.width
    unconstrained; the shrink loop must now keep reducing size until the
    word actually fits width-wise too."""
    draw = _measure_draw()
    region = OcrTextRegion(text="x", x=0, y=0, width=60, height=40, confidence=90.0)

    lines, font, line_height, x_offset = _fit_text(draw, "HAUPTBUCH", region, max_height=1000)

    naive_size = int(region.height * 0.8)
    assert font.size < naive_size, "expected the width check to shrink below the naive height-derived size"
    assert lines == ["HAUPTBUCH"]  # never split mid-word, unchanged
    assert draw.textlength("HAUPTBUCH", font=font) <= region.width
    assert x_offset == 0.0  # fit by shrinking alone, no widening needed


def test_fit_text_widens_a_single_word_that_still_overflows_at_min_font_size() -> None:
    """When even _MIN_FONT_SIZE still doesn't make the word fit
    region.width, the existing widen-using-available-room fallback must
    still engage for a single word exactly like it already does for
    wrapped multi-word text (test_fit_text_widens_to_the_right_first_
    without_shifting_x above) - rewrapping a fixed-size unbreakable word
    to a wider box never shrinks it, so this exhausts the available room
    rather than finding an exact fit, but must still use it rather than
    silently accepting an avoidable overflow when room exists."""
    draw = _measure_draw()
    region = OcrTextRegion(text="x", x=100, y=50, width=20, height=12, confidence=90.0)
    word = "Donaudampfschifffahrtsgesellschaft"

    no_room_lines, no_room_font, _, no_room_offset = _fit_text(draw, word, region, max_height=1000)
    assert draw.textlength(word, font=no_room_font) > region.width, (
        "control fixture did not actually reproduce the still-too-wide-at-min-size case - "
        "adjust the fixture, not the assertion"
    )
    assert no_room_offset == 0.0

    lines, font, line_height, x_offset = _fit_text(
        draw, word, region, max_height=1000, right_room=800
    )
    assert lines == [word]
    assert x_offset == 0.0  # right_room alone is enough, no left shift needed


def test_apply_shrinks_a_single_unbreakable_word_to_fit_a_manually_corrected_boxs_width(
    tmp_path: Path,
) -> None:
    """End-to-end regression guard for the exact real-world scenario:
    a `render_box` set by a correction UI (image_translate_cli/
    review_server.py's browser page, or ui/image_correction_dialog.py) -
    NOT the wide-open, never-corrected default - translated into a
    single long word. Before this fix, the rendered text ignored
    render_box's width entirely (only its height mattered) and could
    draw far outside it; now it must stay within render_box, mirroring
    test_apply_wraps_long_translation_instead_of_overflowing_box_width's
    probe-strip technique."""
    image = Image.new("RGB", (500, 200), "white")
    image.save(tmp_path / "source.png")
    source = tmp_path / "source.png"
    output = tmp_path / "out.png"

    original_region = OcrTextRegion(text="Short", x=20, y=20, width=60, height=30, confidence=95.0)
    # A correction UI moved/resized this to a modest box elsewhere on the
    # canvas - deliberately NOT tiny (a human dragging a resize handle a
    # little, not down to the absolute minimum) so this also proves the
    # fix isn't merely "always shrink to the floor".
    corrected_box = OcrTextRegion(text="Short", x=200, y=100, width=110, height=40, confidence=95.0)
    replacement = TextReplacement(
        region=original_region, translated_text="HAUPTBUCH", render_box=corrected_box
    )

    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result = Image.open(output).convert("RGB")
    pixels = result.load()
    # Probe strip well to the right of the CORRECTED box (not the
    # original) - must stay pure background, no text leaking past the
    # box the user actually set.
    probe_pixels = [
        pixels[x, y]
        for x in range(corrected_box.x + corrected_box.width + 20, 480)
        for y in range(corrected_box.y, corrected_box.y + corrected_box.height)
    ]
    assert all(p == (255, 255, 255) for p in probe_pixels), (
        "expected no text pixels to the right of the manually corrected box - "
        "a single-word translation overflowed its width"
    )


# --- _load_font(bold=) / _estimate_is_bold() (real user, 21.08.2026: a
# real infographic uses a uniformly bold/semi-bold display typeface for
# EVERY line - headline, section headers, even small body captions - but
# every rendered translation always came out in plain DejaVuSans Regular,
# regardless of the original line's weight. Calibrated and verified
# against the user's actual source image, not just synthetic samples -
# see this module's own header comment on verifying against reality.) ----


def test_load_font_bold_true_prefers_the_bold_family() -> None:
    font = _load_font(20, bold=True)
    assert _FONT_BOLD_PATH in getattr(font, "path", "")


def test_load_font_bold_false_prefers_the_regular_family() -> None:
    font = _load_font(20, bold=False)
    assert _FONT_BOLD_PATH not in getattr(font, "path", "")


def _build_mixed_weight_image(path: Path) -> None:
    """One clearly Regular-weight and one clearly Bold-weight line, same
    size, same text length - the minimum needed to verify
    _estimate_is_bold() discriminates BOTH ways, not just "always bold"
    or "always regular"."""
    image = Image.new("RGB", (400, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "This is regular weight text", fill="black", font=ImageFont.truetype(_FONT_PATH, 20))
    draw.text((10, 60), "This is bold weight text", fill="black", font=ImageFont.truetype(_FONT_BOLD_PATH, 20))
    image.save(path)


def test_estimate_is_bold_distinguishes_regular_from_bold_in_the_same_image(tmp_path: Path) -> None:
    """Primary path: `region.text` (the ORIGINAL recognized text) drives
    the comparison, not the translated candidate text - see
    _estimate_is_bold()'s docstring for why comparing the SAME string
    (original vs. synthetic) is what makes this reliable. The translated
    candidate text passed here is deliberately quite different in length/
    letters from the original, to prove it is NOT what the comparison
    actually keys off of.
    """
    source = tmp_path / "mixed.png"
    _build_mixed_weight_image(source)
    image = Image.open(source).convert("RGB")

    regular_region = OcrTextRegion(text="This is regular weight text", x=10, y=10, width=300, height=24, confidence=95.0)
    bold_region = OcrTextRegion(text="This is bold weight text", x=10, y=60, width=280, height=24, confidence=95.0)
    background = _sample_background_color(
        image, regular_region.x, regular_region.y, regular_region.width, regular_region.height
    )

    assert _estimate_is_bold(image, regular_region, background, "Regulaerer Beispieltext") is False
    assert _estimate_is_bold(image, bold_region, background, "Fetter Beispieltext") is True


def test_estimate_is_bold_falls_back_to_candidate_text_when_region_has_no_original_text(tmp_path: Path) -> None:
    """A manually-drawn box (ui/image_correction_dialog.py's "Neue Box
    hinzufügen") has region.text == "" - no original OCR text exists to
    compare against, so the comparison must fall back to candidate_text
    (the translated text about to be drawn) rather than returning False
    outright just because region.text happens to be empty."""
    source = tmp_path / "mixed.png"
    _build_mixed_weight_image(source)
    image = Image.open(source).convert("RGB")

    bold_region = OcrTextRegion(text="", x=10, y=60, width=280, height=24, confidence=95.0)
    background = _sample_background_color(image, bold_region.x, bold_region.y, bold_region.width, bold_region.height)

    assert _estimate_is_bold(image, bold_region, background, "Das ist fetter Text") is True


def test_estimate_is_bold_returns_false_when_no_text_at_all_is_available() -> None:
    """Neither region.text NOR candidate_text has anything to compare
    against - the one case with truly nothing to go on, must default to
    Regular rather than raising or guessing."""
    image = Image.new("RGB", (100, 50), "white")
    region = OcrTextRegion(text="", x=0, y=0, width=100, height=24, confidence=95.0)
    assert _estimate_is_bold(image, region, (255, 255, 255), "") is False
    assert _estimate_is_bold(image, region, (255, 255, 255), "   ") is False


def test_estimate_is_bold_ignores_empty_candidate_text_when_region_has_original_text() -> None:
    """A blank/whitespace-only candidate_text must NOT short-circuit the
    whole function to False when region.text itself has real content to
    compare against - only the FINAL fallback (candidate_text) needs to
    be non-empty, not every parameter."""
    image = Image.new("RGB", (100, 50), "white")
    region = OcrTextRegion(text="Some original text", x=0, y=0, width=100, height=24, confidence=95.0)
    # Doesn't raise, and reaches the real comparison logic instead of the
    # early "nothing to compare" return - the actual bool value depends
    # on the (blank) synthetic image content, which isn't the point here.
    _estimate_is_bold(image, region, (255, 255, 255), "")


def test_apply_renders_bold_original_text_in_bold_and_regular_in_regular(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end regression guard, through the full BoxOverlayBackend.apply()
    path (not just _estimate_is_bold() in isolation): a mixed-weight
    source image must produce a mixed-weight OUTPUT.

    Verified by spying on _load_font() itself rather than re-deriving
    boldness from the OUTPUT's pixels: the translated replacement text is
    a DIFFERENT (German, differently-shaped) string than the original
    English text the region's width was measured against, so re-running
    the synthetic-ink-ratio comparison against the rendered output would
    compare a tightly-cropped synthetic sample against a real box padded
    with extra background - an apples-to-oranges mismatch that belongs to
    THIS test's own verification approach, not to _estimate_is_bold()
    itself (see the module-level real-image and mixed-weight tests above,
    which call it exactly as apply() does - on the pristine, pre-overwrite
    image, region matched to the ORIGINAL text). Spying on the actual
    bold= argument _draw_fitted_text()/_fit_text() pass down to
    _load_font() checks the real wiring without that mismatch.
    """
    import pipeline.images.inpainting as inpainting_module

    source = tmp_path / "mixed.png"
    _build_mixed_weight_image(source)
    output = tmp_path / "out.png"

    replacements = [
        TextReplacement(
            region=OcrTextRegion(text="This is regular weight text", x=10, y=10, width=300, height=24, confidence=95.0),
            translated_text="Regulaerer Beispieltext",
        ),
        TextReplacement(
            region=OcrTextRegion(text="This is bold weight text", x=10, y=60, width=280, height=24, confidence=95.0),
            translated_text="Fetter Beispieltext",
        ),
    ]

    calls: list[bool] = []
    real_load_font = inpainting_module._load_font

    def spy_load_font(size: int, bold: bool = False, family: str = "sans_serif", italic: bool = False):
        calls.append(bold)
        return real_load_font(size, bold=bold, family=family, italic=italic)

    monkeypatch.setattr(inpainting_module, "_load_font", spy_load_font)

    BoxOverlayBackend().apply(str(source), replacements, str(output))

    # _load_font() is also called many more times now (22.08.2026,
    # font_style.py's family/bold/italic classification each render their
    # own synthetic comparison samples per region, not just the two
    # bold-estimation samples from before) - so the actually-drawn weight
    # is whichever value _fit_text() passed down LAST for each region, not
    # simply "every bold=True call".
    assert calls[-1] is True, f"expected the final (drawing) _load_font() call for the BOLD region to use bold=True, got {calls}"


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_apply_bold_output_still_recognizable_by_ocr(tmp_path: Path) -> None:
    """A bold-rendered replacement must still be genuine, OCR-readable
    text - not, say, an accidentally-doubled/smeared render - mirrors
    test_apply_replaces_recognized_text_end_to_end()'s own round-trip
    discipline for the plain (non-bold) case."""
    source = tmp_path / "mixed.png"
    _build_mixed_weight_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="This is bold weight text", x=10, y=60, width=280, height=24, confidence=95.0),
        translated_text="Fetter erkennbarer Text",
    )
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(output))]
    assert any("Fetter" in text for text in result_texts)


# --- _sample_background()/GradientBackground/_fill_gradient_rect (real
# user, 22.08.2026: nach einem Google-Translate-Bildvergleich mit einer
# eigenen Test-Infografik, "die sollten wir so wie auf das von Google
# bringen" - BoxOverlayBackend füllte bislang JEDE Box einfarbig, auch
# wenn die Umgebung sichtbar einen Farbverlauf zeigte, siehe
# pipeline/images/inpainting.py's GradientBackground-Docstring.) ---------


def _build_vertical_gradient_image(path: Path, region: OcrTextRegion) -> None:
    """A 400x150 image whose background fades from a light color at the
    top to a clearly darker one at the bottom - well past
    _GRADIENT_DETECTION_THRESHOLD - with `region`'s own original text
    drawn on top in black, exactly like a real gradient-backed infographic
    banner."""
    image = Image.new("RGB", (400, 150), "white")
    pixels = image.load()
    top_color = (250, 250, 250)
    bottom_color = (40, 40, 120)
    for y in range(150):
        t = y / 149
        color = tuple(round(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        for x in range(400):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(_FONT_PATH, 24)
    draw.text((region.x, region.y), region.text, fill="black", font=font)
    image.save(path)


def _build_horizontal_gradient_image(path: Path, region: OcrTextRegion) -> None:
    """Same idea as _build_vertical_gradient_image(), but the fade runs
    left->right instead of top->bottom."""
    image = Image.new("RGB", (400, 150), "white")
    pixels = image.load()
    left_color = (250, 250, 250)
    right_color = (120, 40, 40)
    for x in range(400):
        t = x / 399
        color = tuple(round(left_color[i] + (right_color[i] - left_color[i]) * t) for i in range(3))
        for y in range(150):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(_FONT_PATH, 24)
    draw.text((region.x, region.y), region.text, fill="black", font=font)
    image.save(path)


def test_sample_background_returns_flat_color_for_uniform_background(tmp_path: Path) -> None:
    """The common case (a genuinely flat, uniform surrounding) must still
    return a plain (r, g, b) tuple, not a GradientBackground - backward
    compatible with every existing flat-background test above."""
    source = tmp_path / "flat.png"
    _build_two_line_image(source)
    image = Image.open(source).convert("RGB")

    region = OcrTextRegion(text="Hello World", x=20, y=20, width=200, height=28, confidence=95.0)
    background = _sample_background(image, region.x, region.y, region.width, region.height)

    assert isinstance(background, tuple)


def test_sample_background_detects_vertical_gradient(tmp_path: Path) -> None:
    region = OcrTextRegion(text="Hello World", x=20, y=60, width=200, height=28, confidence=95.0)
    source = tmp_path / "vgrad.png"
    _build_vertical_gradient_image(source, region)
    image = Image.open(source).convert("RGB")

    background = _sample_background(image, region.x, region.y, region.width, region.height)

    assert isinstance(background, GradientBackground)
    assert background.axis == "vertical"
    # top->bottom fade goes from light to dark - start must be the
    # lighter stop, matching the real image, not swapped.
    assert sum(background.start) > sum(background.end)


def test_sample_background_detects_horizontal_gradient(tmp_path: Path) -> None:
    region = OcrTextRegion(text="Hello World", x=20, y=60, width=200, height=28, confidence=95.0)
    source = tmp_path / "hgrad.png"
    _build_horizontal_gradient_image(source, region)
    image = Image.open(source).convert("RGB")

    background = _sample_background(image, region.x, region.y, region.width, region.height)

    assert isinstance(background, GradientBackground)
    assert background.axis == "horizontal"
    assert sum(background.start) > sum(background.end)


def test_representative_color_returns_flat_tuple_unchanged() -> None:
    assert _representative_color((10, 20, 30)) == (10, 20, 30)


def test_representative_color_is_midpoint_of_gradient_stops() -> None:
    gradient = GradientBackground(axis="vertical", start=(0, 0, 0), end=(100, 200, 40))
    assert _representative_color(gradient) == (50, 100, 20)


def test_fill_gradient_rect_interpolates_from_start_to_end() -> None:
    """Direct pixel check on _fill_gradient_rect() itself, independent of
    detection/BoxOverlayBackend - the first row must match `start`, the
    last row `end`, and rows in between must move monotonically from one
    to the other (no banding/discontinuity)."""
    image = Image.new("RGB", (20, 50), "white")
    draw = ImageDraw.Draw(image)
    gradient = GradientBackground(axis="vertical", start=(255, 0, 0), end=(0, 0, 255))

    _fill_gradient_rect(draw, 0, 0, 20, 50, gradient)

    pixels = image.load()
    assert pixels[5, 0] == (255, 0, 0)
    assert pixels[5, 49] == (0, 0, 255)
    # monotonic: red channel decreases, blue channel increases, top to bottom
    reds = [pixels[5, y][0] for y in range(50)]
    blues = [pixels[5, y][2] for y in range(50)]
    assert all(reds[i] >= reds[i + 1] for i in range(len(reds) - 1))
    assert all(blues[i] <= blues[i + 1] for i in range(len(blues) - 1))


def test_apply_fills_gradient_background_with_a_visible_gradient_not_flat(tmp_path: Path) -> None:
    """End-to-end through BoxOverlayBackend.apply(): a region sitting on a
    genuine vertical gradient must come back out with a gradient fill
    (top of the box visibly different from the bottom of the box), not
    today's single flat draw.rectangle() color."""
    region = OcrTextRegion(text="Hello World", x=20, y=60, width=200, height=28, confidence=95.0)
    source = tmp_path / "vgrad.png"
    _build_vertical_gradient_image(source, region)
    output = tmp_path / "out.png"

    replacement = TextReplacement(region=region, translated_text="Hallo Welt")
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result = Image.open(output).convert("RGB")
    pixels = result.load()
    # Sample the fill just inside the box's left edge (away from the drawn
    # text itself), near the top vs. near the bottom of the box.
    top_fill = pixels[region.x + 2, region.y + 2]
    bottom_fill = pixels[region.x + 2, region.y + region.height - 2]
    assert _color_distance(top_fill, bottom_fill) > 10.0


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_apply_gradient_background_output_still_recognizable_by_ocr(tmp_path: Path) -> None:
    """The gradient fill must not come at the cost of text legibility -
    same round-trip discipline as test_apply_bold_output_still_recognizable_by_ocr().

    Region deliberately sits near the LIGHT end of the gradient (y=15, not
    the y=60 mid-fade position the other gradient tests above use) rather
    than straddling the exact light/dark 50%-luminance crossover of a
    400x150, near-white-to-dark-blue fade: found empirically (22.08.2026)
    that Tesseract's own binarization simply fails outright (empty
    result, not just a wrong reading) right at that crossover, even
    though the rendered text is genuinely legible to a human eye there
    too (visually confirmed) - a low-contrast-position artifact of this
    specific synthetic test image, not a defect in the gradient fill or
    text-drawing code itself (confirmed by moving only the region's y and
    getting a clean OCR read - see git history of this test if that
    edge case needs revisiting, e.g. sampling text-color contrast locally
    under the text instead of _representative_color()'s single midpoint).
    """
    region = OcrTextRegion(text="Hello World", x=20, y=15, width=200, height=28, confidence=95.0)
    source = tmp_path / "vgrad.png"
    _build_vertical_gradient_image(source, region)
    output = tmp_path / "out.png"

    replacement = TextReplacement(region=region, translated_text="Erkennbarer Text")
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(output))]
    assert any("Erkennbarer" in text for text in result_texts)


# --- obstacle_regions (22.08.2026, real user - same real infographic +
# GPU-Inpainting qa_report.txt that motivated the qa_report.txt settings
# fix: "Boxen überlappen oder sind an falscher Stelle". Until this date,
# _vertical_room_below() only ever saw the CURRENT run's successfully
# translated regions - a region OCR recognized but translate_image()
# skipped/failed still shows its ORIGINAL pixels in the output, but was
# invisible to collision avoidance, so a neighbouring translated region's
# text could still grow straight into it. apply()'s new obstacle_regions
# parameter closes that gap - these tests build the exact failure shape
# (two tightly-spaced lines, only the first translated, the second passed
# as an obstacle) and assert the translated text's growth actually stops
# short of it now.) ----------------------------------------------------


_OBSTACLE_TRANSLATED_TEXT = (
    "Ein deutlich laengerer Text der garantiert mehrere Zeilen braucht dies und jenes"
)


def _build_two_tight_lines_image(path: Path) -> OcrTextRegion:
    """A short first line (wide 200px box, so _OBSTACLE_TRANSLATED_TEXT
    only needs to wrap, not shrink to the font floor) and a second line
    60px below it (y=80, first line's own box ends at y=44) - close
    enough that _fit_text()'s GENEROUS no-neighbour fallback
    (_NO_NEIGHBOR_HEIGHT_ALLOWANCE * region.height = 96px of vertical
    room) lets the wrapped translation grow right through it, but far
    enough that the REAL gap-based room (still comfortably above what
    the text needs even at the smallest font size) lets it fit without
    touching the second line at all - see the two tests below, whose
    exact pixel-level behaviour at these coordinates was verified by
    directly running BoxOverlayBackend.apply() before being written down
    here (not just hand-computed), since _fit_text()'s discrete font-size
    steps make the exact chosen size/line count non-obvious in advance.
    Returns the SECOND line's region (the one that must survive as an
    obstacle - never itself translated in these tests, mirroring a
    skipped/failed region that translate_image() left untouched).
    """
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Short", fill="black", font=font)
    draw.text((20, 80), "Untouched Neighbour", fill="black", font=font)
    image.save(path)
    return OcrTextRegion(text="Untouched Neighbour", x=20, y=80, width=220, height=24, confidence=95.0)


def test_apply_without_obstacle_regions_can_overwrite_a_skipped_neighbour(tmp_path: Path) -> None:
    """Baseline/control: reproduces the pre-fix behaviour on purpose, so
    the next test's improvement is demonstrably real and not just an
    artifact of the fixture. A long enough translation, wrapped to the
    first line's narrow width, needs more than the ~26px gap to the
    second line - without obstacle_regions, _vertical_room_below() has no
    neighbour to see (the second line was never in `replacements`) and
    falls back to its generous _NO_NEIGHBOR_HEIGHT_ALLOWANCE, so the
    wrapped block is free to grow down across the second line's own
    pixels.
    """
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text=_OBSTACLE_TRANSLATED_TEXT,
    )
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    box = (0, neighbour_region.y, 400, neighbour_region.y + neighbour_region.height)
    assert original.crop(box).tobytes() != result.crop(box).tobytes(), (
        "control fixture did not actually reproduce the overlap - adjust the fixture, "
        "not the assertion"
    )


def test_apply_with_obstacle_regions_leaves_the_skipped_neighbour_untouched(tmp_path: Path) -> None:
    """The fix itself: passing the second line's region as obstacle_regions
    (never in `replacements`, exactly mirroring how translate_image() now
    passes every skipped/failed region) must make _vertical_room_below()
    see it as a real neighbour and constrain the first region's growth so
    its pixels stay untouched - same translated text, same tight fixture
    as the control test above, only obstacle_regions differs.
    """
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text=_OBSTACLE_TRANSLATED_TEXT,
    )
    BoxOverlayBackend().apply(
        str(source), [replacement], str(output), obstacle_regions=[neighbour_region]
    )

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    box = (0, neighbour_region.y, 400, neighbour_region.y + neighbour_region.height)
    assert original.crop(box).tobytes() == result.crop(box).tobytes()


def test_apply_obstacle_regions_defaults_to_none_without_error(tmp_path: Path) -> None:
    """Every existing caller (e.g. run_image_correction_job(), which never
    computes obstacle regions - see InpaintingBackend.apply()'s docstring
    for why) omits the new parameter entirely - must keep working exactly
    as before, not raise a TypeError for a missing argument."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"
    replacement = TextReplacement(
        region=OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=95.0),
        translated_text="Hallo Welt",
    )
    BoxOverlayBackend().apply(str(source), [replacement], str(output))  # no obstacle_regions kwarg
    assert output.exists()


# --- _horizontal_room() / _fit_text() horizontal widening (23.08.2026 -
# real user, QA-Bericht "(12)", "Spirit - Soul - Meatsuit.jpg": a footer
# text got cut off at the image's own bottom edge even though the box's
# left/right neighbours were both far enough away to leave real, unused
# margin - "Der Text könnte ohne weiteres nach links... und... nach
# rechts erweitert werden. Links und Rechts davon ist nichts." Mirrors
# the _vertical_room_below()/obstacle_regions section above almost
# exactly, just the other axis - see _horizontal_room()'s own docstring
# for why there is no "generous no-neighbour multiplier" here unlike the
# vertical case.) ------------------------------------------------------


def test_horizontal_room_with_no_neighbours_is_bounded_by_image_edges() -> None:
    region = OcrTextRegion(text="x", x=100, y=0, width=50, height=20, confidence=90.0)
    left_room, right_room = _horizontal_room(region, [region], image_width=400)
    # left edge at x=100 minus the 3px safety margin; right edge at
    # x=150, image ends at 400, so 250px minus the margin.
    assert left_room == 97.0
    assert right_room == 247.0


def test_horizontal_room_finds_nearest_left_and_right_neighbours_in_same_row() -> None:
    region = OcrTextRegion(text="x", x=100, y=50, width=50, height=20, confidence=90.0)
    left_neighbour = OcrTextRegion(text="L", x=20, y=50, width=50, height=20, confidence=90.0)
    right_neighbour = OcrTextRegion(text="R", x=200, y=55, width=30, height=10, confidence=90.0)
    left_room, right_room = _horizontal_room(
        region, [region, left_neighbour, right_neighbour], image_width=1000
    )
    # left_neighbour's right edge is at x=70; gap to region.x=100 is 30,
    # minus the 3px margin. right_neighbour's left edge is at x=200; gap
    # from region's right edge (150) is 50, minus the margin.
    assert left_room == 27.0
    assert right_room == 47.0


def test_horizontal_room_ignores_a_neighbour_in_a_different_row() -> None:
    """A region sitting well to the left but in a completely different
    row (no y-overlap at all) must not constrain this region's room -
    same "same horizontal/vertical band" reasoning as
    _vertical_room_below()'s own docstring, just the other axis."""
    region = OcrTextRegion(text="x", x=100, y=50, width=50, height=20, confidence=90.0)
    unrelated_row = OcrTextRegion(text="U", x=20, y=500, width=50, height=20, confidence=90.0)
    left_room, right_room = _horizontal_room(region, [region, unrelated_row], image_width=400)
    assert left_room == 97.0  # same as the no-neighbours case above
    assert right_room == 247.0


def test_horizontal_room_never_negative_when_a_neighbour_is_touching_or_overlapping() -> None:
    region = OcrTextRegion(text="x", x=100, y=0, width=50, height=20, confidence=90.0)
    touching_left = OcrTextRegion(text="L", x=98, y=0, width=2, height=20, confidence=90.0)
    left_room, _ = _horizontal_room(region, [region, touching_left], image_width=400)
    assert left_room == 0.0


def test_fit_text_returns_zero_x_offset_when_shrink_alone_already_fits() -> None:
    """Room being available must not change anything for the common case
    where the existing shrink-to-fit loop already succeeds - widening is
    a FALLBACK only (see _fit_text()'s own docstring)."""
    draw = _measure_draw()
    region = OcrTextRegion(text="Hi", x=0, y=0, width=200, height=24, confidence=95.0)
    lines, font, line_height, x_offset = _fit_text(
        draw, "Hallo", region, region.height, left_room=500, right_room=500
    )
    assert x_offset == 0.0


def test_fit_text_widens_to_the_right_first_without_shifting_x(tmp_path: Path) -> None:
    """A narrow, short region with a translation long enough that even
    _MIN_FONT_SIZE still overflows max_height - verified directly here
    (not just hand-computed, same discipline as _build_two_tight_lines_
    image()'s docstring above) rather than assumed. With enough room on
    the RIGHT alone, the block must fit without any left shift."""
    draw = _measure_draw()
    region = OcrTextRegion(text="x", x=100, y=50, width=60, height=20, confidence=90.0)
    long_text = (
        "Dies ist ein deutlich laengerer deutscher Uebersetzungstext "
        "der garantiert nicht in eine kleine Box passt"
    )
    no_room_lines, _, no_room_lh, no_room_offset = _fit_text(draw, long_text, region, max_height=20)
    assert no_room_lh * len(no_room_lines) > 20, (
        "control fixture did not actually reproduce the overflow-at-min-size case - "
        "adjust the fixture, not the assertion"
    )
    assert no_room_offset == 0.0

    lines, _, line_height, x_offset = _fit_text(
        draw, long_text, region, max_height=20, right_room=400
    )
    assert line_height * len(lines) <= 20
    assert x_offset == 0.0


def test_fit_text_uses_left_room_only_once_right_room_is_exhausted() -> None:
    """Same overflowing fixture as above, but this time the RIGHT side
    alone (small room) is not enough - the remainder must come from the
    LEFT (negative x_offset), never more than left_room itself."""
    draw = _measure_draw()
    region = OcrTextRegion(text="x", x=100, y=50, width=60, height=20, confidence=90.0)
    long_text = (
        "Dies ist ein deutlich laengerer deutscher Uebersetzungstext "
        "der garantiert nicht in eine kleine Box passt"
    )
    lines, _, line_height, x_offset = _fit_text(
        draw, long_text, region, max_height=20, right_room=50, left_room=400
    )
    assert line_height * len(lines) <= 20
    assert x_offset < 0.0
    assert x_offset >= -400.0


def test_fit_text_still_accepts_overflow_when_no_horizontal_room_exists() -> None:
    """Unchanged pre-23.08.2026 behaviour: explicit left_room=right_room=0
    (e.g. a region with real neighbours pressed right up against it on
    both sides) must produce the exact same result as calling without
    the parameters at all."""
    draw = _measure_draw()
    region = OcrTextRegion(text="x", x=100, y=50, width=60, height=20, confidence=90.0)
    long_text = (
        "Dies ist ein deutlich laengerer deutscher Uebersetzungstext "
        "der garantiert nicht in eine kleine Box passt"
    )
    default_lines, default_font, default_lh, default_offset = _fit_text(draw, long_text, region, max_height=20)
    zero_lines, zero_font, zero_lh, zero_offset = _fit_text(
        draw, long_text, region, max_height=20, left_room=0.0, right_room=0.0
    )
    # Font objects from two separate _load_font() calls never compare
    # equal by identity even for the same size/family - compare the
    # size actually used instead, alongside everything else.
    assert default_lines == zero_lines
    assert default_font.size == zero_font.size
    assert default_lh == zero_lh
    assert default_offset == zero_offset == 0.0


def test_apply_wires_horizontal_room_into_fit_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Integration check for BoxOverlayBackend.apply()'s own new
    `_horizontal_room(region, all_regions, image.width)` call (added
    23.08.2026) - patches _fit_text() to record the left_room/right_room
    it was actually called with, so a copy-paste slip in apply() itself
    (as opposed to _horizontal_room()/_fit_text() individually, both
    already covered above) would be caught here."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"
    region = OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=95.0)
    replacement = TextReplacement(region=region, translated_text="Hallo Welt")

    calls = []
    import pipeline.images.inpainting as inpainting_module

    real_fit_text = inpainting_module._fit_text

    def _spy_fit_text(*args, **kwargs):
        calls.append((kwargs.get("left_room"), kwargs.get("right_room")))
        return real_fit_text(*args, **kwargs)

    monkeypatch.setattr(inpainting_module, "_fit_text", _spy_fit_text)
    BoxOverlayBackend().apply(str(source), [replacement], str(output))

    assert len(calls) == 1
    left_room, right_room = calls[0]
    expected_left, expected_right = _horizontal_room(region, [region], image_width=400)
    assert left_room == expected_left
    assert right_room == expected_right


# --- _initial_font_size() respecting OcrTextRegion.line_height (22.08.2026
# - see that field's docstring: a region built by pipeline.images.ocr.
# merge_region_group() has a `height` spanning several merged original
# lines together, which must NOT drive the seeded font size the way a
# genuine single-line region's `height` does.) ---------------------------


def test_initial_font_size_uses_height_when_line_height_is_none() -> None:
    """Every OcrTextRegion anywhere else in the codebase (line_height
    defaults to None) - unchanged behaviour."""
    region = OcrTextRegion(text="x", x=0, y=0, width=10, height=30, confidence=90.0)
    assert _initial_font_size(region) == min(max(_MIN_FONT_SIZE, int(30 * 0.8)), _MAX_FONT_SIZE)


def test_initial_font_size_uses_line_height_not_the_merged_span_when_set() -> None:
    """A merged multi-line region: `height` (90, spanning 3 merged lines)
    must NOT seed the font size - `line_height` (one line's real height,
    14) must, or the whole paragraph would render several times too
    large."""
    region = OcrTextRegion(text="a b c", x=0, y=0, width=200, height=90, confidence=90.0, line_height=14)
    assert _initial_font_size(region) == min(max(_MIN_FONT_SIZE, int(14 * 0.8)), _MAX_FONT_SIZE)
    # Sanity: using the merged span directly would have given a very
    # different (much larger) result - confirms the test fixture actually
    # exercises the distinction, not a coincidence where both paths agree.
    assert _initial_font_size(region) != min(max(_MIN_FONT_SIZE, int(90 * 0.8)), _MAX_FONT_SIZE)
