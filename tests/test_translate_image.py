"""Regression coverage for pipeline/images/translate_image.py (RoadMap.md
Phase 3 - Bildübersetzung und OCR): the OCR -> Übersetzung -> Rückschreibung
loop, independent of ui/image_job.py's file-handling/QA-report layer around
it (mirrors how tests/test_pdf_ico_mode.py separates engine-level from
job-level coverage).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.inpainting import BoxOverlayBackend
from pipeline.images.ocr import OcrError, OcrTextRegion, TesseractOcrEngine, tesseract_available
from pipeline.images.translate_image import translate_image
from pipeline.translation.base import TranslationError, TranslationResult

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


class _FakeProvider:
    """Minimal TranslationProvider: appends " [DE]" to every translated
    text - mirrors FakeHtmlProvider in tests/test_pdf_ico_mode.py, just
    the plain-text translate() half (translate_image() never calls
    translate_html())."""

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


class _SelectiveFailProvider:
    """Raises TranslationError for one specific input text, succeeds for
    everything else - lets a test assert that one bad region doesn't
    abort translation of the rest, mirroring translate_pdf()'s own
    per-block try/except test coverage."""

    def __init__(self, fail_text: str) -> None:
        self._fail_text = fail_text

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        if text == self._fail_text:
            raise TranslationError("simulierter Anbieterfehler")
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


class _StubFailingOcrEngine:
    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        raise OcrError("Tesseract-Binary wurde nicht gefunden")


def test_translate_image_translates_all_regions_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de",
    )

    assert stats.translated == 2
    assert stats.failed == 0
    assert len(stats.regions) == 2
    assert destination.exists()

    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(destination))]
    assert "Hello World" not in result_texts
    assert "Second Line" not in result_texts
    assert any("[DE]" in text for text in result_texts)


def test_translate_image_counts_failed_region_without_aborting_others(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _SelectiveFailProvider(fail_text="Hello World"), [], target_lang="de",
    )

    assert stats.translated == 1
    assert stats.failed == 1
    assert len(stats.errors) == 1
    assert "region" in stats.errors[0]
    assert destination.exists()


def test_translate_image_cancellation_stops_further_translation(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # cancel right after the first region is processed

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de", should_cancel=should_cancel,
    )

    assert stats.cancelled is True
    assert stats.translated == 1
    # Output is still written (inpainting_backend.apply() always runs at
    # the end, see translate_image()'s docstring) even though the run
    # was cancelled partway through.
    assert destination.exists()


def test_translate_image_propagates_ocr_error(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    with pytest.raises(OcrError):
        translate_image(
            str(source), str(destination), _StubFailingOcrEngine(), BoxOverlayBackend(),
            _FakeProvider(), [], target_lang="de",
        )
    assert not destination.exists()


def test_translate_image_invokes_progress_and_stats_callbacks(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    progress_messages: list[str] = []
    stats_snapshots: list[int] = []

    translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de",
        progress_callback=progress_messages.append,
        stats_callback=lambda stats: stats_snapshots.append(stats.translated),
    )

    assert len(progress_messages) == 2
    assert stats_snapshots == [1, 2]


def test_translate_image_respects_protected_terms(tmp_path: Path) -> None:
    """protect_terms()/restore_terms() must actually be wired in - a
    protected term must survive untranslated inside the (otherwise
    translated) region, mirroring translate_pdf()'s equivalent handling.
    """
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), ["World"], target_lang="de",
    )

    assert stats.translated == 2
    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(destination))]
    assert any("World" in text for text in result_texts)
