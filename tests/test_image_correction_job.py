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

from pipeline.images.ocr import TesseractOcrEngine, tesseract_available
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


def test_correction_job_does_not_require_provider_or_ocr_engine(tmp_path: Path) -> None:
    """Sanity check on the "no OCR/provider re-run" contract mentioned in
    run_image_correction_job()'s docstring - it has no such parameters to
    even pass one to.
    """
    params = inspect.signature(run_image_correction_job).parameters
    assert "provider" not in params
    assert "provider_name" not in params
    assert "ocr_engine_name" not in params
