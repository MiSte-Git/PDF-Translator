"""Regression coverage for pipeline/images/font_style.py (RoadMap.md
Phase 3, "...echte Schrifterkennung (Font-Matching) weiterhin offen" -
Michael, 22.08.2026, nach einem Google-Translate-Bildvergleich: "Unser
Ansatz hat eine Genauigkeit im Layout von vielleicht 60-70%... die sollten
wir so wie auf das von Google bringen").

Region boxes below are sized to closely match the ACTUAL rendered text
extent (via ImageDraw.textbbox(), plus a small margin) rather than an
arbitrary fixed box - mirrors how tests/test_image_inpainting.py's own
established bold-detection tests (test_estimate_is_bold_distinguishes_
regular_from_bold_in_the_same_image) size their regions close to the real
text width/height. A generously loose, arbitrary box dilutes the observed
ink-ratio/serif-score signal against the always-tightly-cropped synthetic
references (see font_style.py's own module docstring, "Bekannte Grenze"),
so an unrealistically loose test box would test that dilution artifact
rather than the classifiers themselves.

`size` is always passed as the SAME exact size the comparison text was
actually rendered at - the module docstring's own "Bekannte Grenze"
section documents that accuracy degrades once the caller's size ESTIMATE
(pipeline.images.inpainting._initial_font_size(), a rough region.height *
0.8 guess) drifts from the true size; that estimation-error sensitivity is
a separately documented, accepted limitation, not what these tests are
meant to catch.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from pipeline.images.font_style import (
    FontStyle,
    _binary_ink_mask,
    _ink_ratio,
    _resolve_sample_text,
    _serif_score,
    _slant_ratio,
    _trim_to_ink_bbox,
    classify_bold,
    classify_family,
    classify_italic,
    estimate_font_style,
    load_font,
)
from pipeline.images.ocr import OcrTextRegion

_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_SIZE = 20
_TEXT = "This is a sample line"
_BACKGROUND = (255, 255, 255)


def _build(bold: bool = False, family: str = "sans_serif", italic: bool = False, x: int = 10, y: int = 10):
    """Renders _TEXT in the given style at _SIZE, with an OcrTextRegion
    box tightly matching the actual glyph extent (see module docstring) -
    the shared fixture behind every classify_*()/estimate_font_style()
    test below."""
    font = load_font(_SIZE, bold=bold, family=family, italic=italic)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = probe.textbbox((x, y), _TEXT, font=font)
    width = (bbox[2] - bbox[0]) + 6
    height = (bbox[3] - bbox[1]) + 6
    image = Image.new("RGB", (x + width + 20, 60), "white")
    ImageDraw.Draw(image).text((x, y), _TEXT, fill="black", font=font)
    region = OcrTextRegion(text=_TEXT, x=x, y=y - 2, width=width, height=height, confidence=95.0)
    return image, region


# --- load_font() fallback cascade -------------------------------------------


def test_load_font_sans_regular_resolves_dejavu_sans() -> None:
    font = load_font(20)
    assert font.path == f"{_DEJAVU}/DejaVuSans.ttf"


def test_load_font_sans_bold_resolves_dejavu_sans_bold() -> None:
    font = load_font(20, bold=True)
    assert font.path == f"{_DEJAVU}/DejaVuSans-Bold.ttf"


def test_load_font_sans_italic_resolves_dejavu_sans_oblique() -> None:
    font = load_font(20, italic=True)
    assert font.path == f"{_DEJAVU}/DejaVuSans-Oblique.ttf"


def test_load_font_serif_regular_resolves_dejavu_serif() -> None:
    font = load_font(20, family="serif")
    assert font.path == f"{_DEJAVU}/DejaVuSerif.ttf"


def test_load_font_serif_bold_italic_resolves_dejavu_serif_bolditalic() -> None:
    font = load_font(20, family="serif", bold=True, italic=True)
    assert font.path == f"{_DEJAVU}/DejaVuSerif-BoldItalic.ttf"


def test_load_font_falls_back_to_default_when_no_candidate_path_exists(monkeypatch) -> None:
    """No DejaVu directory at all resolves on this system - the whole
    cascade must fall through to Pillow's own built-in default font
    rather than raising."""
    import pipeline.images.font_style as font_style_module

    monkeypatch.setattr(font_style_module, "_FONT_DIRS", ("/no/such/directory",))
    font = load_font(20, bold=True, family="serif", italic=True)
    assert font is not None


def test_load_font_never_returns_a_zero_or_negative_size() -> None:
    """size <= 0 (a degenerate caller value) must not crash ImageFont -
    load_font() clamps to at least 1."""
    font = load_font(0)
    assert font is not None


# --- _trim_to_ink_bbox() -----------------------------------------------------


def test_trim_to_ink_bbox_returns_empty_mask_unchanged() -> None:
    assert _trim_to_ink_bbox([]) == []


def test_trim_to_ink_bbox_returns_all_false_mask_unchanged() -> None:
    mask = [[False, False], [False, False]]
    assert _trim_to_ink_bbox(mask) == mask


def test_trim_to_ink_bbox_crops_padding_rows_and_columns() -> None:
    mask = [
        [False, False, False, False],
        [False, True, True, False],
        [False, True, True, False],
        [False, False, False, False],
    ]
    trimmed = _trim_to_ink_bbox(mask)
    assert trimmed == [[True, True], [True, True]]


def test_trim_to_ink_bbox_ignores_faint_noise_floor_rows() -> None:
    """A row/column with only a couple of ink pixels next to rows with
    dozens must not extend the trimmed bounding box - see this function's
    own docstring (22.08.2026 finding: anti-aliasing fringes a couple
    pixels wide skewed _serif_score()/_slant_ratio() before this)."""
    strong_row = [True] * 50
    faint_row = [True, True] + [False] * 48
    empty_row = [False] * 50
    mask = [empty_row, faint_row, strong_row, strong_row, strong_row, faint_row, empty_row]
    trimmed = _trim_to_ink_bbox(mask)
    # the two faint rows (2 ink pixels vs. 50 in the strong rows - well
    # under the 8% floor of 4) must be excluded from the trimmed box.
    assert len(trimmed) == 3


# --- _resolve_sample_text() --------------------------------------------------


def test_resolve_sample_text_prefers_region_text() -> None:
    region = OcrTextRegion(text="Original", x=0, y=0, width=10, height=10, confidence=90.0)
    assert _resolve_sample_text(region, "Translated") == "Original"


def test_resolve_sample_text_falls_back_to_candidate_when_region_text_blank() -> None:
    region = OcrTextRegion(text="   ", x=0, y=0, width=10, height=10, confidence=90.0)
    assert _resolve_sample_text(region, "Translated") == "Translated"


def test_resolve_sample_text_empty_when_both_blank() -> None:
    region = OcrTextRegion(text="", x=0, y=0, width=10, height=10, confidence=90.0)
    assert _resolve_sample_text(region, "   ") == ""


# --- classify_family() -------------------------------------------------------


def test_classify_family_detects_sans_serif() -> None:
    image, region = _build(family="sans_serif")
    assert classify_family(image, region, _BACKGROUND, _TEXT, _SIZE) == "sans_serif"


def test_classify_family_detects_serif() -> None:
    image, region = _build(family="serif")
    assert classify_family(image, region, _BACKGROUND, _TEXT, _SIZE) == "serif"


def test_classify_family_defaults_to_sans_serif_without_any_text() -> None:
    image, region = _build(family="serif")
    empty_region = OcrTextRegion(text="", x=region.x, y=region.y, width=region.width, height=region.height, confidence=95.0)
    assert classify_family(image, empty_region, _BACKGROUND, "", _SIZE) == "sans_serif"


# --- classify_bold() ---------------------------------------------------------


def test_classify_bold_detects_regular() -> None:
    image, region = _build(bold=False)
    assert classify_bold(image, region, _BACKGROUND, _TEXT, _SIZE) is False


def test_classify_bold_detects_bold() -> None:
    image, region = _build(bold=True)
    assert classify_bold(image, region, _BACKGROUND, _TEXT, _SIZE) is True


def test_classify_bold_uses_candidate_text_when_region_has_no_original_text() -> None:
    image, region = _build(bold=True)
    empty_region = OcrTextRegion(text="", x=region.x, y=region.y, width=region.width, height=region.height, confidence=95.0)
    assert classify_bold(image, empty_region, _BACKGROUND, _TEXT, _SIZE) is True


def test_classify_bold_returns_false_with_no_text_at_all() -> None:
    image, region = _build(bold=True)
    empty_region = OcrTextRegion(text="", x=region.x, y=region.y, width=region.width, height=region.height, confidence=95.0)
    assert classify_bold(image, empty_region, _BACKGROUND, "   ", _SIZE) is False


# --- classify_italic() -------------------------------------------------------


def test_classify_italic_detects_upright() -> None:
    image, region = _build(italic=False)
    assert classify_italic(image, region, _BACKGROUND, _TEXT, _SIZE) is False


def test_classify_italic_detects_slanted() -> None:
    image, region = _build(italic=True)
    assert classify_italic(image, region, _BACKGROUND, _TEXT, _SIZE) is True


def test_classify_italic_defaults_to_false_without_any_text() -> None:
    image, region = _build(italic=True)
    empty_region = OcrTextRegion(text="", x=region.x, y=region.y, width=region.width, height=region.height, confidence=95.0)
    assert classify_italic(image, empty_region, _BACKGROUND, "", _SIZE) is False


# --- estimate_font_style() ---------------------------------------------------


def test_estimate_font_style_plain_sans_serif_regular() -> None:
    image, region = _build(bold=False, family="sans_serif", italic=False)
    style = estimate_font_style(image, region, _BACKGROUND, _TEXT, _SIZE)
    assert style == FontStyle(family="sans_serif", bold=False, italic=False)


def test_estimate_font_style_bold_italic_serif() -> None:
    image, region = _build(bold=True, family="serif", italic=True)
    style = estimate_font_style(image, region, _BACKGROUND, _TEXT, _SIZE)
    assert style == FontStyle(family="serif", bold=True, italic=True)


def test_estimate_font_style_defaults_when_nothing_to_compare() -> None:
    image, region = _build()
    empty_region = OcrTextRegion(text="", x=region.x, y=region.y, width=region.width, height=region.height, confidence=95.0)
    style = estimate_font_style(image, empty_region, _BACKGROUND, "", _SIZE)
    assert style == FontStyle(family="sans_serif", bold=False, italic=False)


# --- low-level metrics: sanity checks (full behavioural coverage is via
# classify_*() above, which is what actually gets used) ----------------------


def test_ink_ratio_is_zero_for_blank_region() -> None:
    image = Image.new("RGB", (50, 50), "white")
    assert _ink_ratio(image, 0, 0, 50, 50, (255, 255, 255)) == 0.0


def test_binary_ink_mask_marks_a_drawn_black_square() -> None:
    image = Image.new("RGB", (10, 10), "white")
    ImageDraw.Draw(image).rectangle([2, 2, 6, 6], fill="black")
    mask = _binary_ink_mask(image, 0, 0, 10, 10, (255, 255, 255))
    assert mask[4][4] is True
    assert mask[0][0] is False


def test_serif_score_returns_zero_for_too_small_mask() -> None:
    assert _serif_score([[True]]) == 0.0


def test_slant_ratio_returns_zero_for_too_small_mask() -> None:
    assert _slant_ratio([[True]]) == 0.0
