"""Regression coverage for the klassische CPU-Inpainting-Rückschreibung
(RoadMap.md Phase 3), pipeline/images/inpainting.py::CvInpaintingBackend.

Skipped entirely if opencv is not installed (optional dependency, see
requirements-ocr.txt) - mirrors how tests/test_image_ocr.py's Tesseract-
dependent tests skip when the Tesseract binary is missing.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2  # noqa: F401
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

from pipeline.images.inpainting import CvInpaintingBackend, InpaintingError, TextReplacement, _average_region_color
from pipeline.images.ocr import OcrTextRegion, TesseractOcrEngine, tesseract_available

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pytestmark = pytest.mark.skipif(not _CV2_AVAILABLE, reason="opencv not installed")


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


def _build_gradient_image(path: Path) -> None:
    """A horizontal gradient background with a text line drawn across
    it - the case classic inpainting is meant to handle better than a
    flat box-overlay fill (a gradient, unlike a photo, is exactly the
    kind of simple/continuable structure cv2.inpaint() is good at)."""
    image = Image.new("RGB", (300, 100))
    pixels = image.load()
    for x in range(300):
        shade = int(255 * x / 300)
        for y in range(100):
            pixels[x, y] = (shade, shade, shade)
    font = ImageFont.truetype(_FONT_PATH, 24)
    draw = ImageDraw.Draw(image)
    draw.text((20, 35), "Gradient Text", fill="red", font=font)
    image.save(path)


def test_average_region_color_matches_solid_interior() -> None:
    image = Image.new("RGB", (100, 100), (10, 20, 30))
    color = _average_region_color(image, x=10, y=10, width=20, height=20)
    assert color == (10, 20, 30)


def test_apply_raises_inpainting_error_for_missing_source_image(tmp_path: Path) -> None:
    with pytest.raises(InpaintingError):
        CvInpaintingBackend().apply(
            str(tmp_path / "does_not_exist.png"), [], str(tmp_path / "out.png")
        )


def test_apply_with_no_replacements_leaves_image_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    CvInpaintingBackend().apply(str(source), [], str(output))

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    # .tobytes() (not .getdata()/.get_flattened_data()): the former is
    # deprecated as of newer Pillow releases, the latter only exists on
    # very recent ones - .tobytes() is the one raw-pixel-comparison API
    # that's been stable across every Pillow version, including older
    # ones some environments are still pinned to (see requirements-gpu.txt's
    # note on simple-lama-inpainting forcing an older Pillow).
    assert original.tobytes() == result.tobytes()


def test_apply_leaves_untouched_regions_pixel_identical(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=95.0),
        translated_text="Hallo Welt",
    )
    CvInpaintingBackend().apply(str(source), [replacement], str(output))

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    box = (0, 60, 400, 150)
    assert original.crop(box).tobytes() == result.crop(box).tobytes()


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_apply_replaces_recognized_text_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    engine = TesseractOcrEngine()
    regions = engine.recognize(str(source))
    first_line = next(r for r in regions if r.text == "Hello World")
    replacement = TextReplacement(region=first_line, translated_text="Hallo Welt")

    CvInpaintingBackend().apply(str(source), [replacement], str(output))

    result_texts = [r.text for r in engine.recognize(str(output))]
    assert "Hello World" not in result_texts
    assert any("Hallo" in text for text in result_texts)
    assert "Second Line" in result_texts


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_apply_with_render_box_erases_the_original_position_and_draws_at_the_new_one(
    tmp_path: Path,
) -> None:
    """26.08.2026 regression guard - same real user report and same fix
    as test_image_inpainting.py's identically-named test for
    BoxOverlayBackend (Backlog.md 26.08.2026: "die Positionen, Grösse und
    Korrekturen werden nicht übernommen"). Here the inpainting MASK must
    cover both `region` (erase the real original) and `render_box` (clean
    background for the new draw target) - see _build_inpainting_mask()'s
    CvInpaintingBackend counterpart in inpainting.py for the exact
    reasoning."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    output = tmp_path / "out.png"

    engine = TesseractOcrEngine()
    regions = engine.recognize(str(source))
    first_line = next(r for r in regions if r.text == "Hello World")
    moved_box = OcrTextRegion(
        text=first_line.text, x=250, y=110, width=130, height=30, confidence=first_line.confidence
    )
    replacement = TextReplacement(region=first_line, translated_text="Hallo Welt", render_box=moved_box)

    CvInpaintingBackend().apply(str(source), [replacement], str(output))

    result_regions = engine.recognize(str(output))
    result_texts = [r.text for r in result_regions]
    assert "Hello World" not in result_texts
    moved_hits = [
        r
        for r in result_regions
        if "Hallo" in r.text and r.x >= moved_box.x - 20 and r.y >= moved_box.y - 20
    ]
    assert moved_hits, f"expected translated text near the moved box, got: {result_regions}"
    assert "Second Line" in result_texts


def test_apply_reconstructs_gradient_more_closely_than_flat_fill(tmp_path: Path) -> None:
    """The concrete reason to prefer CvInpaintingBackend over
    BoxOverlayBackend for this kind of background: after inpainting, the
    left and right edges of the replaced region should still roughly
    match the surrounding gradient values, not both collapse to one flat
    color the way a box-overlay fill would.
    """
    source = tmp_path / "gradient.png"
    _build_gradient_image(source)
    output = tmp_path / "out.png"

    region = OcrTextRegion(text="Gradient Text", x=20, y=35, width=180, height=24, confidence=90.0)
    replacement = TextReplacement(region=region, translated_text="Verlaufstext")
    CvInpaintingBackend().apply(str(source), [replacement], str(output))

    result = Image.open(output).convert("RGB")
    pixels = result.load()
    # Just inside the left edge vs. just inside the right edge of the
    # replaced region - a flat single-color fill would make these equal;
    # a gradient-aware reconstruction keeps them different, continuing
    # the same left-to-right shade progression as the surroundings.
    left_edge = pixels[region.x + 2, region.y + region.height - 1]
    right_edge = pixels[region.x + region.width - 2, region.y + region.height - 1]
    assert left_edge != right_edge
    assert left_edge[0] < right_edge[0]  # darker on the left, matching the gradient's direction


# --- obstacle_regions (22.08.2026 - see tests/test_image_inpainting.py's
# identical section for the full real-user motivation; same verified
# fixture coordinates reused here since _fit_text()/_vertical_room_below()
# are shared by every backend, not re-derived per backend). --------------


def _build_two_tight_lines_image(path: Path) -> OcrTextRegion:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Short", fill="black", font=font)
    draw.text((20, 80), "Untouched Neighbour", fill="black", font=font)
    image.save(path)
    return OcrTextRegion(text="Untouched Neighbour", x=20, y=80, width=220, height=24, confidence=95.0)


_OBSTACLE_TRANSLATED_TEXT = (
    "Ein deutlich laengerer Text der garantiert mehrere Zeilen braucht dies und jenes"
)


def test_apply_with_obstacle_regions_leaves_the_skipped_neighbour_untouched(tmp_path: Path) -> None:
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text=_OBSTACLE_TRANSLATED_TEXT,
    )
    CvInpaintingBackend().apply(
        str(source), [replacement], str(output), obstacle_regions=[neighbour_region]
    )

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    box = (0, neighbour_region.y, 400, neighbour_region.y + neighbour_region.height)
    assert original.crop(box).tobytes() == result.crop(box).tobytes()


def test_apply_obstacle_regions_are_never_added_to_the_inpainting_mask(tmp_path: Path) -> None:
    """obstacle_regions must only affect TEXT PLACEMENT (via
    _vertical_room_below()), never the cv2.inpaint() mask itself - an
    obstacle region's ORIGINAL pixels (not a reconstructed background)
    are exactly what must stay visible, so passing it as an obstacle must
    NOT cause its interior to be erased/reconstructed the way a real
    `replacements` region's interior is.
    """
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    output = tmp_path / "out.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text="Kurz",
    )
    CvInpaintingBackend().apply(
        str(source), [replacement], str(output), obstacle_regions=[neighbour_region]
    )

    original = Image.open(source).convert("RGB")
    result = Image.open(output).convert("RGB")
    box = (
        neighbour_region.x,
        neighbour_region.y,
        neighbour_region.x + neighbour_region.width,
        neighbour_region.y + neighbour_region.height,
    )
    assert original.crop(box).tobytes() == result.crop(box).tobytes()
