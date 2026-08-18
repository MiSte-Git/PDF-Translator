"""Mirrors tests/test_pdf_job.py's coverage for the eigenständige
Bildübersetzung (ui/image_job.py, RoadMap.md Phase 3).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.ocr import tesseract_available
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.document_job_common import DestinationConflictError
from ui.image_job import run_image_job

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        self.calls += 1
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


def test_run_image_job_writes_output_and_qa_report(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    destination = tmp_path / "photo_DE.png"
    provider = FakeProvider()
    progress_messages: list[str] = []

    result = run_image_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000,
        progress_callback=progress_messages.append,
        provider=provider,
    )

    assert result.output_path == destination
    assert destination.exists()
    assert result.qa_report_path.exists()
    assert result.stats.translated == 2
    assert provider.calls == 2
    assert len(progress_messages) == 2

    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "Bildübersetzung - QA-Bericht" in report
    assert "Erkannte Textregionen: 2" in report
    assert "Regionen übersetzt: 2" in report
    assert "OCR-Engine: tesseract" in report
    assert "Box-Overlay" in report


def test_run_image_job_raises_for_identical_source_and_destination(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)

    with pytest.raises(DestinationConflictError):
        run_image_job(
            source, source, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=FakeProvider(),
        )


def test_run_image_job_raises_when_destination_already_exists(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    destination = tmp_path / "photo_DE.png"
    destination.write_bytes(b"already here")

    with pytest.raises(DestinationConflictError):
        run_image_job(
            source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=FakeProvider(),
        )


def test_run_image_job_uses_selected_inpainting_backend(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    destination = tmp_path / "photo_DE.png"

    result = run_image_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
        inpainting_backend_name="cv_inpainting",
    )

    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "Klassisches CPU-Inpainting" in report


def test_run_image_job_rejects_unknown_backend_name(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    destination = tmp_path / "photo_DE.png"

    with pytest.raises(ValueError, match="Rückschreibe-Backend"):
        run_image_job(
            source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=FakeProvider(),
            inpainting_backend_name="does-not-exist",
        )


def test_run_image_job_qa_report_notes_no_text_found(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    Image.new("RGB", (100, 50), "white").save(source)
    destination = tmp_path / "blank_DE.png"

    result = run_image_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )

    assert result.stats.translated == 0
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "kein Text im Bild erkannt" in report
