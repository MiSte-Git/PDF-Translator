"""Regression coverage for the "Bildübersetzung korrigieren" UI wiring
(RoadMap.md Phase 3's "Korrektur-Möglichkeit ... analog zur PDF-Variante"
item): MainWindow._show_job_result() must show correct_translation_button
only for an ImageBatchJobResult with at least one correctable file, and
_open_correction_dialog()/ImageCorrectionDialog (ui/image_correction_dialog.py)
must apply a plain-text edit through to the saved image - mirrors
tests/test_ui_pdf_correction.py's structure and "intercept the blocking
exec(), not the business logic" pattern.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog

from pipeline.images.ocr import TesseractOcrEngine, tesseract_available
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.app import MainWindow
from ui.image_correction_dialog import ImageCorrectionDialog
from ui.image_job import ImageBatchStats, run_image_job
from ui.pdf_job import PdfJobResult

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class FakeProvider:
    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def _build_two_line_image(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _prepare_job_context(window: MainWindow) -> None:
    window._job_inpainting_backend = "box_overlay"


def test_correct_translation_button_visible_for_image_batch_with_replacements(
    qapp: QApplication, tmp_path: Path
) -> None:
    from ui.image_job import ImageBatchJobResult, ImageJobResult
    from pipeline.images.translate_image import ImageTranslationStats
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion

    window = MainWindow()
    window.show()
    try:
        region = OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=95.0)
        replacement = TextReplacement(region=region, translated_text="Hallo Welt")
        file_result = ImageJobResult(
            source_path=tmp_path / "photo.png",
            output_path=tmp_path / "photo_DE.png",
            qa_report_path=tmp_path / "photo_DE_qa_report.txt",
            stats=ImageTranslationStats(translated=1, replacements=[replacement]),
        )
        result = ImageBatchJobResult(
            output_dir=tmp_path,
            stats=ImageBatchStats(files_processed=1, files_total=1, translated=1, results=[file_result]),
        )
        window._job_result = result
        window._show_job_result(result)
        assert window.correct_translation_button.isVisible()
    finally:
        window.close()


def test_correct_translation_button_hidden_when_no_replacements(qapp: QApplication, tmp_path: Path) -> None:
    from ui.image_job import ImageBatchJobResult, ImageJobResult
    from pipeline.images.translate_image import ImageTranslationStats

    window = MainWindow()
    window.show()
    try:
        file_result = ImageJobResult(
            source_path=tmp_path / "photo.png",
            output_path=tmp_path / "photo_DE.png",
            qa_report_path=tmp_path / "photo_DE_qa_report.txt",
            stats=ImageTranslationStats(translated=0, failed=1),
        )
        result = ImageBatchJobResult(
            output_dir=tmp_path,
            stats=ImageBatchStats(files_processed=1, files_total=1, failed=1, results=[file_result]),
        )
        window._job_result = result
        window._show_job_result(result)
        assert not window.correct_translation_button.isVisible()
    finally:
        window.close()


def test_correct_translation_button_hidden_for_non_image_batch_result(qapp: QApplication) -> None:
    from pipeline.pdf.translate_pdf import PdfTranslationStats

    window = MainWindow()
    window.show()
    try:
        result = PdfJobResult(
            output_path=Path("out.pdf"), qa_report_path=Path("out_qa_report.txt"),
            stats=PdfTranslationStats(translated=0, skipped=1),
        )
        window._job_result = result
        window._show_job_result(result)
        assert not window.correct_translation_button.isVisible()
    finally:
        window.close()


def test_open_correction_dialog_applies_edit_and_refreshes_result(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ui.image_job import ImageBatchJobResult

    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    destination = tmp_path / "photo_DE.png"

    original_result = run_image_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )
    assert len(original_result.stats.replacements) == 2
    batch_result = ImageBatchJobResult(
        output_dir=tmp_path,
        stats=ImageBatchStats(
            files_processed=1, files_total=1, translated=2, results=[original_result],
        ),
    )

    def fake_exec(self: ImageCorrectionDialog) -> int:
        # Simulate the user editing row 0's plain-text editor (already
        # loaded by __init__'s initial _load_row(0)), then clicking
        # "Anwenden" - mirrors test_ui_pdf_correction.py's fake_exec().
        self.editor.selectAll()
        self.editor.insertPlainText("Handkorrigierter Text")
        self._apply()
        return 0

    monkeypatch.setattr(ImageCorrectionDialog, "exec", fake_exec)

    window = MainWindow()
    window.show()
    try:
        window._job_result = batch_result
        _prepare_job_context(window)
        window._show_job_result(batch_result)
        assert window.correct_translation_button.isVisible()

        window._open_correction_dialog()

        assert window._job_result is not None
        corrected_file_result = window._job_result.stats.results[0]
        assert corrected_file_result.output_path == destination
        # Reopening again must start from THIS round's edit, not silently
        # discard it back to the original machine translation.
        assert corrected_file_result.stats.replacements[0].translated_text == "Handkorrigierter Text"
    finally:
        window.close()

    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(destination))]
    assert any("Handkorrigierter" in text for text in result_texts)


def test_open_correction_dialog_asks_which_file_when_batch_has_several(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ui.image_job import ImageBatchJobResult

    source_a = tmp_path / "a.png"
    source_b = tmp_path / "b.png"
    _build_two_line_image(source_a)
    _build_two_line_image(source_b)
    dest_a = tmp_path / "a_DE.png"
    dest_b = tmp_path / "b_DE.png"

    result_a = run_image_job(
        source_a, dest_a, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )
    result_b = run_image_job(
        source_b, dest_b, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )
    batch_result = ImageBatchJobResult(
        output_dir=tmp_path,
        stats=ImageBatchStats(
            files_processed=2, files_total=2, translated=4, results=[result_a, result_b],
        ),
    )

    # Simulate the user picking the SECOND file ("b_DE.png") in the picker.
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *args, **kwargs: ("b_DE.png", True))
    )

    def fake_exec(self: ImageCorrectionDialog) -> int:
        assert self.destination == dest_b
        return 0

    monkeypatch.setattr(ImageCorrectionDialog, "exec", fake_exec)

    window = MainWindow()
    window.show()
    try:
        window._job_result = batch_result
        _prepare_job_context(window)
        window._show_job_result(batch_result)

        window._open_correction_dialog()
        # fake_exec()'s own assertion is the real check here (that the
        # picked file's destination reached the dialog) - reaching this
        # point without an AssertionError from fake_exec() confirms it.
    finally:
        window.close()


def test_switching_rows_without_editing_keeps_original_text(qapp: QApplication, tmp_path: Path) -> None:
    """Mirrors tests/test_ui_pdf_correction.py's
    test_switching_rows_without_editing_keeps_original_html_object():
    exercises ImageCorrectionDialog._flush_active_row()'s OWN _dirty
    guard directly (switching away from a row the user never edited)
    rather than the final applied-output guarantee, which stays correct
    either way thanks to _current_edits()'s separate _dirty filter.
    """
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region_a = OcrTextRegion(text="First", x=0, y=0, width=50, height=20, confidence=90.0)
    region_b = OcrTextRegion(text="Second", x=0, y=30, width=50, height=20, confidence=90.0)
    replacements = [
        TextReplacement(region=region_a, translated_text="Erste"),
        TextReplacement(region=region_b, translated_text="Zweite"),
    ]
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", replacements,
    )
    try:
        original_text_0 = replacements[0].translated_text
        dialog._load_row(1)  # switch away from row 0 without ever editing it
        assert dialog._row_text[0] is original_text_0
    finally:
        dialog.deleteLater()
