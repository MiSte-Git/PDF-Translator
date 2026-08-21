"""Regression coverage for the OCR-Backend-Abstraktion (RoadMap.md Phase 3
- Bildübersetzung und OCR), pipeline/images/ocr.py.

Fixture images are rendered with a real TrueType font (DejaVuSans, present
on this system's fonts) rather than Pillow's tiny built-in bitmap default
font: confirmed by direct experimentation that the default font merges
"Hello World" into a single "Helloworld" word under Tesseract (too small/
tight for real character spacing), while DejaVuSans at a normal text size
recognizes each word separately with high confidence - the same class of
"reproduce the real shape, not a convenient shortcut" fixture-construction
care used throughout this project's PDF tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.ocr import OcrError, TesseractOcrEngine, tesseract_available

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


def _build_blank_image(path: Path) -> None:
    Image.new("RGB", (200, 100), "white").save(path)


def _build_two_column_image(path: Path) -> None:
    """Two single words on the SAME visual row, far enough apart to
    simulate a two-column layout (a main content area + a right-hand
    sidebar box) - the shape that motivated _MAX_WORD_GAP_RATIO (see
    pipeline/images/ocr.py, RoadMap.md/Backlog.md 21.08.2026): without the
    gap-split, Tesseract's (block, par, line) grouping alone would glue
    "Left" and "Right" into one nonsensical "Left Right" region spanning
    the whole gap between them.
    """
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (600, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Left", fill="black", font=font)
    draw.text((420, 20), "Right", fill="black", font=font)
    image.save(path)


def test_tesseract_available_reflects_shutil_which(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipeline.images.ocr.shutil.which", lambda name: "/usr/bin/tesseract")
    assert tesseract_available() is True

    monkeypatch.setattr("pipeline.images.ocr.shutil.which", lambda name: None)
    assert tesseract_available() is False


def test_recognize_raises_ocr_error_when_tesseract_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The availability check must be consulted BEFORE ever touching
    pytesseract/the binary - a caller that skipped the UI-level
    availability gate still gets a clean OcrError, not a raw subprocess
    failure from pytesseract.
    """
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.tesseract_available", lambda: False)

    with pytest.raises(OcrError, match="Tesseract-Binary"):
        TesseractOcrEngine().recognize(str(source))


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_groups_words_into_reading_order_lines(tmp_path: Path) -> None:
    source = tmp_path / "two_lines.png"
    _build_two_line_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 2
    first, second = regions
    assert first.text == "Hello World"
    assert second.text == "Second Line"
    # Reading order: the "Hello World" line sits above "Second Line" in
    # the fixture (y=20 vs y=70) and must be returned first.
    assert first.y < second.y
    # Bounding boxes must be the union of both words on that line, not
    # just the first word's box.
    assert first.width > 50
    assert first.confidence > 0


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_returns_empty_list_for_blank_image(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    _build_blank_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert regions == []


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_splits_words_far_apart_on_the_same_line(tmp_path: Path) -> None:
    """A wide horizontal gap between two words Tesseract put on the same
    (block, par, line) - the two-column-layout case - must yield TWO
    regions, not one giant one spanning the gap (see
    _build_two_column_image()'s docstring and _MAX_WORD_GAP_RATIO)."""
    source = tmp_path / "two_columns.png"
    _build_two_column_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 2
    first, second = regions
    assert first.text == "Left"
    assert second.text == "Right"
    # Left-to-right within the row, same as reading order elsewhere.
    assert first.x < second.x


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_accepts_language_hint(tmp_path: Path) -> None:
    """language=None must fall back to "eng" rather than raising - a
    caller-supplied language (e.g. "deu") is passed through to
    pytesseract unchanged.
    """
    source = tmp_path / "two_lines.png"
    _build_two_line_image(source)

    regions_default = TesseractOcrEngine().recognize(str(source))
    regions_explicit = TesseractOcrEngine().recognize(str(source), language="eng")

    assert [r.text for r in regions_default] == [r.text for r in regions_explicit]
