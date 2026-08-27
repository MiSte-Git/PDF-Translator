"""Coverage for run_image_correction_job() (ui/image_job.py) - the UI-job
layer wrapping pipeline.images.inpainting.InpaintingBackend.apply() for the
"Bildübersetzung korrigieren" workflow (RoadMap.md Phase 3's "Korrektur-
Möglichkeit ... analog zur PDF-Variante" item). Mirrors
tests/test_pdf_correction_job.py's structure so the two stay easy to
compare (run_image_job() produces the replacements this file's tests
apply corrections to).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.inpainting import TextReplacement
from pipeline.images.ocr import OcrTextRegion, TesseractOcrEngine, tesseract_available
from pipeline.images.translate_image import build_corrected_replacements
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.document_job_common import DestinationConflictError
from ui.image_job import run_image_correction_job, run_image_job

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")


class FakeProvider:
    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


def test_correction_job_overwrites_existing_output_with_edited_text(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    destination = tmp_path / "photo_DE.png"

    original_result = run_image_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )
    assert original_result.stats.translated == 2
    assert len(original_result.stats.replacements) == 2
    original_mtime = destination.stat().st_mtime_ns

    corrected_replacements = build_corrected_replacements(
        original_result.stats.replacements, {0: "Handkorrigierter Text"}
    )

    corrected_result = run_image_correction_job(source, destination, corrected_replacements)

    assert corrected_result.output_path == destination
    assert destination.exists()
    assert destination.stat().st_mtime_ns >= original_mtime  # actually rewritten
    assert corrected_result.stats.translated == 2

    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(destination))]
    assert any("Handkorrigierter" in text for text in result_texts)

    report = corrected_result.qa_report_path.read_text(encoding="utf-8")
    assert "manuelle Korrektur" in report
    assert "Regionen neu eingefügt: 2" in report


def test_correction_job_refuses_source_as_destination(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)

    with pytest.raises(DestinationConflictError):
        run_image_correction_job(source, source, [])


def _build_two_tight_lines_image(path: Path) -> OcrTextRegion:
    """Same fixture shape as tests/test_image_inpainting.py's identically
    named helper - a short region whose translation will need to grow,
    directly above a second, untouched line close enough that growing
    without a collision obstacle would overwrite it."""
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Short", fill="black", font=font)
    draw.text((20, 80), "Untouched Neighbour", fill="black", font=font)
    image.save(path)
    return OcrTextRegion(text="Untouched Neighbour", x=20, y=80, width=220, height=24, confidence=95.0)


_LONG_TRANSLATION = "Ein deutlich laengerer Text der garantiert mehrere Zeilen braucht dies und jenes"


def test_correction_job_without_obstacle_regions_can_overwrite_a_real_neighbour(tmp_path: Path) -> None:
    """26.08.2026 regression guard - real user report, Backlog.md
    26.08.2026, "Spirit - Soul - Meatsuit.jpg": a correction round
    rendered a badly oversized, overlapping "HAUPTBUCH" where the
    original translation run had rendered cleanly. Root cause: this
    function NEVER forwarded `obstacle_regions` to
    InpaintingBackend.apply() until today - documents the OLD, buggy
    behaviour this fixture reproduces (obstacle_regions omitted): a
    region whose translation needs to grow has NO neighbour to respect,
    so it CAN grow straight over real, still-visible content. The
    companion test below proves passing `obstacle_regions` now prevents
    exactly this."""
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    destination = tmp_path / "tight_DE.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text=_LONG_TRANSLATION,
    )
    run_image_correction_job(source, destination, [replacement])  # obstacle_regions omitted, as before today

    original = Image.open(source).convert("RGB")
    result = Image.open(destination).convert("RGB")
    box = (0, neighbour_region.y, 400, neighbour_region.y + neighbour_region.height)
    assert original.crop(box).tobytes() != result.crop(box).tobytes(), (
        "expected the old, obstacle-blind behaviour to overwrite the neighbour - "
        "if this now fails, the underlying renderer's growth behaviour changed "
        "and this test's premise needs revisiting, not just this assertion"
    )


def test_correction_job_passes_obstacle_regions_through_and_protects_a_real_neighbour(tmp_path: Path) -> None:
    """The actual fix for the bug documented above: `obstacle_regions`
    (26.08.2026, new parameter) reaches InpaintingBackend.apply() - a
    real neighbour passed this way survives a correction round
    untouched, exactly like it already did on the ORIGINAL translation
    run (see tests/test_image_inpainting.py's identically-motivated
    obstacle_regions coverage)."""
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    destination = tmp_path / "tight_DE.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text=_LONG_TRANSLATION,
    )
    run_image_correction_job(
        source, destination, [replacement], obstacle_regions=[neighbour_region]
    )

    original = Image.open(source).convert("RGB")
    result = Image.open(destination).convert("RGB")
    box = (0, neighbour_region.y, 400, neighbour_region.y + neighbour_region.height)
    assert original.crop(box).tobytes() == result.crop(box).tobytes()


def test_correction_job_folds_obstacle_regions_into_the_returned_stats_regions(tmp_path: Path) -> None:
    """26.08.2026 - obstacle_regions must also survive into the returned
    ImageJobResult.stats.regions, not just this ONE apply() call - a
    SECOND correction round (webapp/job_bridge.py::apply_correction_
    result()'s splice, or reopening ui/image_correction_dialog.py) reads
    ITS starting obstacle set from the PREVIOUS result's stats.regions
    (see ui/app.py::_open_image_correction_dialog()'s matching
    identity-based computation) - if this result dropped them, that
    second round would silently lose protection again."""
    source = tmp_path / "tight.png"
    neighbour_region = _build_two_tight_lines_image(source)
    destination = tmp_path / "tight_DE.png"

    replacement = TextReplacement(
        region=OcrTextRegion(text="Short", x=20, y=20, width=200, height=24, confidence=95.0),
        translated_text="Kurz",
    )
    result = run_image_correction_job(
        source, destination, [replacement], obstacle_regions=[neighbour_region]
    )

    assert neighbour_region in result.stats.regions
    assert replacement.region in result.stats.regions


def test_correction_job_does_not_require_provider_or_ocr_engine(tmp_path: Path) -> None:
    """Sanity check on the "no OCR/provider re-run" contract mentioned in
    run_image_correction_job()'s docstring - it has no such parameters to
    even pass one to.
    """
    params = inspect.signature(run_image_correction_job).parameters
    assert "provider" not in params
    assert "provider_name" not in params
    assert "ocr_engine_name" not in params
