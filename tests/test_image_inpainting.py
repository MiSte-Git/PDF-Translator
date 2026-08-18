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
    InpaintingError,
    TextReplacement,
    _contrasting_text_color,
    _fit_text,
    _sample_background_color,
    _wrap_text_to_width,
)
from pipeline.images.ocr import OcrTextRegion, TesseractOcrEngine, tesseract_available

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


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

    lines, font, line_height = _fit_text(draw, long_text, region)

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

    lines, font, line_height = _fit_text(draw, "Kurzer Text", region)

    assert font.size <= _MAX_FONT_SIZE


def test_fit_text_returns_single_line_for_short_text_that_already_fits() -> None:
    draw = _measure_draw()
    region = OcrTextRegion(text="Hi", x=0, y=0, width=200, height=24, confidence=95.0)

    lines, font, line_height = _fit_text(draw, "Hallo", region)

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
