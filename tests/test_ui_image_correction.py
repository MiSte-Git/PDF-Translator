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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QInputDialog

from pipeline.images.ocr import TesseractOcrEngine, tesseract_available
from pipeline.images.translate_image import build_corrected_replacements
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


# --- canvas: draggable/resizable boxes (real user request, 21.08.2026:
# "Boxen direkt im Bild verschieben/skalieren", after the OCR-placement
# fixes still left some cases the user wanted to correct by hand) --------
#
# Per this project's own "intercept the blocking primitive, not the
# business logic" testing philosophy (see tests/test_ui_pdf_correction.py
# and this file's own module docstring), these tests do not synthesize
# real QGraphicsScene mouse-drag pixel events - they call
# _ResizableRegionItem.set_geometry()/geometry() and the dialog's own
# _on_region_item_changed()/_on_region_item_selected() callbacks directly,
# exactly as the item's real mousePressEvent/mouseMoveEvent overrides do
# internally (see ui/image_correction_dialog.py).


def _make_two_row_dialog(tmp_path: Path):
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region_a = OcrTextRegion(text="First", x=10, y=10, width=50, height=20, confidence=90.0)
    region_b = OcrTextRegion(text="Second", x=10, y=40, width=60, height=25, confidence=90.0)
    replacements = [
        TextReplacement(region=region_a, translated_text="Erste"),
        TextReplacement(region=region_b, translated_text="Zweite"),
    ]
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", replacements,
    )
    return dialog, replacements


def test_canvas_creates_one_region_item_per_replacement_matching_geometry(
    qapp: QApplication, tmp_path: Path
) -> None:
    dialog, replacements = _make_two_row_dialog(tmp_path)
    try:
        assert len(dialog._region_items) == len(replacements)
        for item, replacement in zip(dialog._region_items, replacements):
            region = replacement.region
            assert item.geometry() == (region.x, region.y, region.width, region.height)
    finally:
        dialog.deleteLater()


def test_moving_canvas_box_records_edited_geometry(qapp: QApplication, tmp_path: Path) -> None:
    dialog, _ = _make_two_row_dialog(tmp_path)
    try:
        assert dialog._edited_geometry == {}
        # Mirrors what _ResizableRegionItem.mouseMoveEvent() does on a real
        # drag: update the item's geometry, then invoke on_changed(row).
        dialog._region_items[0].set_geometry(30, 45, 90, 28)
        dialog._on_region_item_changed(0)

        assert dialog._edited_geometry == {0: (30, 45, 90, 28)}
        # Untouched row 1 must stay absent, not implicitly recorded.
        assert 1 not in dialog._edited_geometry
    finally:
        dialog.deleteLater()


def test_clicking_canvas_box_selects_matching_table_row(qapp: QApplication, tmp_path: Path) -> None:
    dialog, _ = _make_two_row_dialog(tmp_path)
    try:
        assert dialog._active_row == 0  # __init__ preloads row 0
        # Mirrors what _ResizableRegionItem.mousePressEvent() does on a
        # real click: invoke on_selected(row).
        dialog._on_region_item_selected(1)

        assert dialog._active_row == 1
        assert dialog.table.currentRow() == 1
        # Only row 1's box should be the highlighted/active one now.
        assert dialog._region_items[0].pen().color() != dialog._region_items[1].pen().color()
    finally:
        dialog.deleteLater()


def test_reset_geometry_button_clears_override_and_restores_original_box(
    qapp: QApplication, tmp_path: Path
) -> None:
    dialog, replacements = _make_two_row_dialog(tmp_path)
    try:
        dialog._region_items[0].set_geometry(99, 99, 5, 5)
        dialog._on_region_item_changed(0)
        assert 0 in dialog._edited_geometry

        dialog._reset_active_geometry()  # active row is still 0

        assert 0 not in dialog._edited_geometry
        region = replacements[0].region
        assert dialog._region_items[0].geometry() == (region.x, region.y, region.width, region.height)
    finally:
        dialog.deleteLater()


def test_apply_uses_edited_geometry_alongside_untouched_rows(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Geometry and text edits are independent per row (mirrors
    build_corrected_replacements()'s own
    test_build_corrected_replacements_combines_text_and_geometry_edits_independently()
    in tests/test_translate_image.py) - moving row 0's box must not affect
    row 1's translated text or geometry, and vice versa.
    """
    dialog, replacements = _make_two_row_dialog(tmp_path)
    try:
        dialog._region_items[0].set_geometry(20, 15, 55, 22)
        dialog._on_region_item_changed(0)

        dialog._load_row(1)
        dialog.editor.selectAll()
        dialog.editor.insertPlainText("Von Hand korrigiert")

        corrected = build_corrected_replacements(
            dialog.replacements, dialog._current_edits(), edited_geometry=dialog._edited_geometry or None,
        )

        # 28.08.2026 - fixed a stale assertion here: this checked
        # corrected[0].region instead of .render_box, left over from
        # before render_box existed (26.08.2026 - see
        # TextReplacement.render_box's own docstring). `region` must
        # NEVER change (it's still the untranslated pixels' real
        # position, needed to erase/re-estimate style from) - only
        # render_box, the NEW target to draw at, reflects a geometry
        # edit. This test predates that split and was never updated, so
        # it silently asserted the wrong field for two days without a
        # full local `pytest tests/` run catching it (see Backlog.md
        # 28.08.2026 for why - test_ui_image_correction.py needed
        # PySide6/the full pipeline.pdf package, unavailable in every
        # sandbox this project's sessions ran in until now).
        original_region_0 = replacements[0].region
        assert (corrected[0].region.x, corrected[0].region.y, corrected[0].region.width, corrected[0].region.height) == (
            original_region_0.x, original_region_0.y, original_region_0.width, original_region_0.height,
        )
        assert corrected[0].render_box is not None
        assert (
            corrected[0].render_box.x,
            corrected[0].render_box.y,
            corrected[0].render_box.width,
            corrected[0].render_box.height,
        ) == (20, 15, 55, 22)
        assert corrected[0].translated_text == replacements[0].translated_text
        assert corrected[1].translated_text == "Von Hand korrigiert"
        original_region_1 = replacements[1].region
        assert (corrected[1].region.x, corrected[1].region.y) == (original_region_1.x, original_region_1.y)
    finally:
        dialog.deleteLater()


# --- font size/bold/alignment controls (28.08.2026, real user report,
# Backlog.md 28.08.2026: "Wenn ich etwas korrigiere, muss es auch genauso
# korrigiert werden wie ich es im Viewer sehe.") - mirrors the geometry
# tri-state tests directly above almost exactly, see
# ImageCorrectionDialog._row_font_size/_row_bold/_row_centered/
# _edited_font_size/_edited_bold/_edited_centered's own docstrings.


def test_canvas_box_preview_defaults_to_left_alignment_not_centered(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression test for the exact bug Backlog.md 28.08.2026 describes:
    _ResizableRegionItem.paint() used to draw every box's preview text
    unconditionally centered (Qt.AlignmentFlag.AlignCenter), regardless of
    any per-box state - there was none. A never-corrected row must now
    default to LEFT alignment/regular weight/no size override, matching
    what the real renderer has always done by default (see
    pipeline.images.inpainting.TextReplacement.render_centered's
    docstring), not the old always-centered preview."""
    dialog, _ = _make_two_row_dialog(tmp_path)
    try:
        assert dialog._region_items[0]._centered is False
        assert dialog._region_items[1]._centered is False
        assert dialog._region_items[0]._bold is False
        assert dialog._region_items[0]._font_size_override is None
        assert dialog.centered_button.isChecked() is False
        assert dialog.bold_button.isChecked() is False
    finally:
        dialog.deleteLater()


def test_changing_font_size_spinbox_records_edited_font_size(qapp: QApplication, tmp_path: Path) -> None:
    dialog, _ = _make_two_row_dialog(tmp_path)
    try:
        assert dialog._edited_font_size == {}
        new_size = dialog.font_size_spin.value() + 7
        dialog.font_size_spin.setValue(new_size)

        assert dialog._edited_font_size == {0: new_size}
        assert dialog._row_font_size[0] == new_size
        assert dialog._region_items[0]._font_size_override == new_size
        # Untouched row 1 must stay absent, not implicitly recorded.
        assert 1 not in dialog._edited_font_size
    finally:
        dialog.deleteLater()


def test_font_size_auto_button_clears_override_back_to_estimate(qapp: QApplication, tmp_path: Path) -> None:
    """Mirrors test_reset_geometry_button_clears_override_and_restores_original_box
    above, but the tri-state contract differs (see build_corrected_
    replacements()'s docstring): clearing a font-size override must record
    an EXPLICIT `None` in _edited_font_size, not merely remove the row's
    key - the only way build_corrected_replacements() can tell "clear a
    previous round's override" apart from "never touched this round" (row
    simply absent)."""
    from pipeline.images.inpainting import estimated_font_size

    dialog, replacements = _make_two_row_dialog(tmp_path)
    try:
        dialog.font_size_spin.setValue(dialog.font_size_spin.value() + 7)
        assert 0 in dialog._edited_font_size

        dialog._reset_active_font_size()  # active row is still 0

        assert dialog._edited_font_size == {0: None}
        assert dialog._row_font_size[0] is None
        assert dialog._region_items[0]._font_size_override is None
        assert dialog.font_size_spin.value() == estimated_font_size(replacements[0].region)
    finally:
        dialog.deleteLater()


def test_bold_and_centered_toggles_record_edits_and_update_canvas_preview(
    qapp: QApplication, tmp_path: Path
) -> None:
    dialog, _ = _make_two_row_dialog(tmp_path)
    try:
        assert dialog._edited_bold == {}
        assert dialog._edited_centered == {}

        dialog.bold_button.setChecked(True)
        dialog.centered_button.setChecked(True)

        assert dialog._edited_bold == {0: True}
        assert dialog._edited_centered == {0: True}
        assert dialog._row_bold[0] is True
        assert dialog._row_centered[0] is True
        assert dialog._region_items[0]._bold is True
        assert dialog._region_items[0]._centered is True
        # Untouched row 1 must stay absent, not implicitly recorded.
        assert 1 not in dialog._edited_bold
        assert 1 not in dialog._edited_centered
    finally:
        dialog.deleteLater()


def test_switching_rows_restores_each_rows_own_format_controls(qapp: QApplication, tmp_path: Path) -> None:
    """Mirrors test_switching_rows_without_editing_keeps_original_text's
    reasoning, for the new controls: switching to row 1 and back to row 0
    must not leak row 0's bold/centered/font-size choice onto row 1, and
    must restore row 0's own choice when switching back -
    ImageCorrectionDialog._load_row()'s self._loading guard (see that
    method's docstring) is exactly what this test protects."""
    dialog, _ = _make_two_row_dialog(tmp_path)
    try:
        dialog.bold_button.setChecked(True)
        dialog.centered_button.setChecked(True)
        new_size = dialog.font_size_spin.value() + 11
        dialog.font_size_spin.setValue(new_size)

        dialog._load_row(1)
        assert dialog.bold_button.isChecked() is False
        assert dialog.centered_button.isChecked() is False
        assert 1 not in dialog._edited_bold
        assert 1 not in dialog._edited_font_size

        dialog._load_row(0)
        assert dialog.bold_button.isChecked() is True
        assert dialog.centered_button.isChecked() is True
        assert dialog.font_size_spin.value() == new_size
    finally:
        dialog.deleteLater()


def test_apply_uses_edited_font_size_bold_centered_alongside_untouched_rows(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Format overrides are independent per row, mirrors
    test_apply_uses_edited_geometry_alongside_untouched_rows immediately
    above exactly, just for font size/bold/centered instead of geometry."""
    dialog, replacements = _make_two_row_dialog(tmp_path)
    try:
        new_size = dialog.font_size_spin.value() + 9
        dialog.font_size_spin.setValue(new_size)
        dialog.bold_button.setChecked(True)
        dialog.centered_button.setChecked(True)

        corrected = build_corrected_replacements(
            dialog.replacements, dialog._current_edits(), edited_geometry=dialog._edited_geometry or None,
            edited_font_size=dialog._edited_font_size or None,
            edited_bold=dialog._edited_bold or None,
            edited_centered=dialog._edited_centered or None,
        )

        assert corrected[0].render_font_size == new_size
        assert corrected[0].render_bold is True
        assert corrected[0].render_centered is True
        # Untouched row 1 must keep its original (unset) render_* values.
        assert corrected[1].render_font_size == replacements[1].render_font_size
        assert corrected[1].render_bold == replacements[1].render_bold
        assert corrected[1].render_centered == replacements[1].render_centered
    finally:
        dialog.deleteLater()


def test_open_correction_dialog_applies_moved_box_end_to_end(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Full round trip through _apply(): a box dragged on the canvas must
    end up as the region actually used to re-render the output image, not
    just recorded in self._edited_geometry - reuses
    test_open_correction_dialog_applies_edit_and_refreshes_result()'s
    real-OCR setup, but moves a box instead of editing text.
    """
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
        stats=ImageBatchStats(files_processed=1, files_total=1, translated=2, results=[original_result]),
    )

    def fake_exec(self: ImageCorrectionDialog) -> int:
        # Drag row 0's box down and to the right by 5px, mirroring a real
        # user's corner-handle/body drag - see this test module's header
        # comment for why set_geometry()+the callback stands in for an
        # actual synthesized mouse drag.
        original = self.replacements[0].region
        self._region_items[0].set_geometry(
            original.x + 5, original.y + 5, original.width, original.height
        )
        self._on_region_item_changed(0)
        self._apply()
        return 0

    monkeypatch.setattr(ImageCorrectionDialog, "exec", fake_exec)

    window = MainWindow()
    window.show()
    try:
        window._job_result = batch_result
        _prepare_job_context(window)
        window._show_job_result(batch_result)
        window._open_correction_dialog()

        corrected_file_result = window._job_result.stats.results[0]
        moved_replacement = corrected_file_result.stats.replacements[0]
        original_region = original_result.stats.replacements[0].region
        # 28.08.2026 - same stale-assertion fix as
        # test_apply_uses_edited_geometry_alongside_untouched_rows above:
        # a moved box lands on render_box, `region` itself must stay put
        # (see TextReplacement.render_box's docstring, 26.08.2026).
        assert moved_replacement.region.x == original_region.x
        assert moved_replacement.region.y == original_region.y
        assert moved_replacement.render_box is not None
        assert moved_replacement.render_box.x == original_region.x + 5
        assert moved_replacement.render_box.y == original_region.y + 5
    finally:
        window.close()


# --- canvas follow-ups (real user, 21.08.2026: after trying the feature
# above, reported two concrete bugs - resizing a box did nothing, and a
# moved box showed no text at all, only the selected row's text in the
# table alongside it) ------------------------------------------------------


def _count_near_color_pixels(scene, color, x0: int, y0: int, x1: int, y1: int) -> int:
    """Render `scene` to an RGB32 QImage and count pixels close to `color`
    within [x0, x1) x [y0, y1) - used to tell "a box's translucent fill
    only" apart from "actual text strokes drawn on top of it" (the fill is
    the same hue at low alpha, blended much paler against the white
    background; real text strokes are painted at full opacity)."""
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import QRectF

    width = int(scene.sceneRect().width()) or x1
    height = int(scene.sceneRect().height()) or y1
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(0xFFFFFFFF)
    painter = QPainter(image)
    try:
        scene.render(painter, QRectF(0, 0, width, height), QRectF(0, 0, width, height))
    finally:
        painter.end()
    target_r, target_g, target_b = color
    count = 0
    for x in range(x0, x1):
        for y in range(y0, y1):
            pixel = image.pixelColor(x, y)
            if abs(pixel.red() - target_r) < 40 and abs(pixel.green() - target_g) < 40 and abs(pixel.blue() - target_b) < 40:
                count += 1
    return count


def test_canvas_box_renders_visible_text_and_follows_it_when_moved(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression guard for "wenn ich die Textbox verschiebe sehe ich
    keinen Text in der Box" - a box must show its translated text at its
    CURRENT position, not just an empty colored outline, both before and
    after a drag."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    source = tmp_path / "photo.png"
    _build_two_line_image(source)
    region = OcrTextRegion(text="First", x=20, y=20, width=200, height=60, confidence=90.0)
    replacements = [TextReplacement(region=region, translated_text="Hallo Welt, das ist ein Test")]
    dialog = ImageCorrectionDialog(LanguageManager("de"), source, tmp_path / "photo_DE.png", replacements)
    try:
        dialog.resize(900, 600)
        dialog.show()
        qapp.processEvents()
        # Text is drawn in the box's OWN current pen color (see
        # _ResizableRegionItem.paint()) - row 0 is auto-loaded/active on
        # construction, so its pen is _ACTIVE_PEN_COLOR (blue), not the
        # default _INACTIVE_PEN_COLOR (red) a lone box might suggest.
        pen_color = dialog._region_items[0].pen().color()
        text_color = (pen_color.red(), pen_color.green(), pen_color.blue())

        before = _count_near_color_pixels(dialog.scene, text_color, 20, 20, 220, 80)
        assert before > 20, "expected visible text strokes inside the box before any move"

        # _build_two_line_image() produces a 400x150 image - moved well
        # clear of the original (20,20)-(220,80) box so the two probed
        # regions never overlap, but still fully within the 400x150 canvas.
        dialog._region_items[0].set_geometry(250, 20, 140, 60)
        dialog._on_region_item_changed(0)
        qapp.processEvents()

        after = _count_near_color_pixels(dialog.scene, text_color, 250, 20, 390, 80)
        assert after > 20, "expected visible text strokes inside the box AFTER the move"
        stale = _count_near_color_pixels(dialog.scene, text_color, 20, 20, 220, 80)
        assert stale == 0, "the OLD position must be empty again once the box has moved away"
    finally:
        dialog.deleteLater()


def test_canvas_box_preview_text_updates_live_while_typing(qapp: QApplication, tmp_path: Path) -> None:
    """The canvas preview must track what the user is CURRENTLY typing in
    the editor, not just the original machine translation - _row_text[row]
    itself is only written back by _flush_active_row() on row switch/apply,
    so this exercises the separate live wiring in _on_editor_text_changed()."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=0, y=0, width=100, height=30, confidence=90.0)
    replacements = [TextReplacement(region=region, translated_text="Alt")]
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", replacements,
    )
    try:
        assert dialog._region_items[0]._text == "Alt"
        dialog.editor.selectAll()
        dialog.editor.insertPlainText("Neu getippt")
        assert dialog._region_items[0]._text == "Neu getippt"
        # _row_text itself is untouched until flush - the two are deliberately independent.
        assert dialog._row_text[0] == "Alt"
    finally:
        dialog.deleteLater()


def test_canvas_box_preview_font_size_matches_the_real_estimate(qapp: QApplication, tmp_path: Path) -> None:
    """Real user report, Backlog.md 27.08.2026 (round 4/5, "Der Font ist
    noch sehr schlecht, wenn man mal den Titel anschaut"): the canvas
    preview used to pick its own font size from half the box's height,
    hard-capped at _MAX_PREVIEW_FONT_SIZE (18pt), with no relation
    whatsoever to pipeline.images.inpainting.estimated_font_size() - the
    same OCR-line-height-based estimate the real PIL renderer AND (since
    26.08.2026) review_server.py's WebViewer both start from. A tall
    title region therefore always looked capped-small here, disconnected
    from what the real output would show. Each row's _ResizableRegionItem
    must now carry the real per-region estimate instead.
    """
    from pipeline.images.inpainting import TextReplacement, estimated_font_size
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    # A tall region whose real estimate is well above the OLD hardcoded
    # 18pt cap - if this ever regresses back to the box-height heuristic,
    # the assertion below catches it.
    region = OcrTextRegion(text="Titel", x=10, y=10, width=400, height=100, confidence=95.0)
    replacements = [TextReplacement(region=region, translated_text="Ein Titel")]
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", replacements,
    )
    try:
        expected = estimated_font_size(region)
        assert expected > 18.0, "fixture region must reproduce the old cap being too low to test anything"
        assert dialog._region_items[0]._font_size_px == expected
    finally:
        dialog.deleteLater()


def test_manually_added_box_still_uses_the_box_height_fallback(qapp: QApplication, tmp_path: Path) -> None:
    """A manually added box (RoadMap.md's "manuelles Hinzufügen einer Box
    für nicht erkannten Text") has no underlying OcrTextRegion to estimate
    a real font size from - must keep using the old box-height-derived
    guess (font_size_px=None), not crash or silently invent a region.
    """
    from ui.i18n import LanguageManager

    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", [],
    )
    try:
        dialog._on_new_box_drawn(30, 30, 120, 40)
        assert dialog._region_items[-1]._font_size_px is None
    finally:
        dialog.deleteLater()


def test_resize_handle_scales_with_view_zoom(qapp: QApplication, tmp_path: Path) -> None:
    """Regression guard for "kann jetzt die Boxen verschieben aber nicht
    in der Grösse verändern": the corner resize handle used to be a fixed
    10-SCENE-unit square, which shrank to a near-unclickable few SCREEN
    pixels once the canvas auto-fits a large source image at less than
    100% zoom (see _ImageCanvasView.resizeEvent()). It must now stay a
    roughly constant SCREEN size regardless of the current zoom level.
    """
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=0, y=0, width=200, height=100, confidence=90.0)
    replacements = [TextReplacement(region=region, translated_text="Text")]
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", replacements,
    )
    try:
        item = dialog._region_items[0]

        dialog.view.resetTransform()
        dialog.view.scale(0.25, 0.25)  # zoomed OUT - handle must GROW in scene units
        zoomed_out_handle = item._handle_rect()

        dialog.view.resetTransform()
        dialog.view.scale(2.0, 2.0)  # zoomed IN - handle must SHRINK in scene units
        zoomed_in_handle = item._handle_rect()

        assert zoomed_out_handle.width() > zoomed_in_handle.width()
        # Roughly proportional to 1/scale (0.25 -> 2.0 is an 8x scale jump).
        assert zoomed_out_handle.width() / zoomed_in_handle.width() == pytest.approx(8.0, rel=0.3)
    finally:
        dialog.deleteLater()


# --- "Neue Box hinzufügen" (real user, 21.08.2026: text Tesseract never
# recognized at all had no box/row to correct at all) ----------------------


def _simulate_drag(view, start, end) -> None:
    """Send real QMouseEvent press/move/release through the view's own
    overridden mouse handlers - mirrors a genuine click-drag-release,
    unlike calling on_box_drawn()/set_geometry() directly, specifically to
    exercise _ImageCanvasView's OWN add-mode state machine end to end (see
    that class's docstring)."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    # The (type, localPos, button, buttons, modifiers) 5-arg constructor is
    # deprecated in this PySide6 version in favour of the localPos+globalPos
    # one below - globalPos's exact value doesn't matter for these tests
    # (only view-local coordinates drive _ImageCanvasView's own handlers).
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress, QPointF(*start), QPointF(*start), Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(press)
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove, QPointF(*end), QPointF(*end), Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    view.mouseMoveEvent(move)
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease, QPointF(*end), QPointF(*end), Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
    )
    view.mouseReleaseEvent(release)


def test_dragging_a_new_box_adds_row_and_focuses_editor(qapp: QApplication, tmp_path: Path) -> None:
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager
    from PIL import Image

    source = tmp_path / "photo.png"
    Image.new("RGB", (400, 300), "white").save(source)
    region = OcrTextRegion(text="First", x=10, y=10, width=50, height=20, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), source, tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Erste")],
    )
    try:
        dialog.resize(900, 600)
        dialog.show()
        qapp.processEvents()

        dialog.add_region_button.setChecked(True)
        assert dialog.view._add_mode is True

        _simulate_drag(dialog.view, (50, 50), (150, 120))

        assert dialog.table.rowCount() == 2
        assert len(dialog.replacements) == 2
        assert len(dialog._region_items) == 2
        # add mode is a one-shot - both the view's internal flag AND the
        # toolbar button's checked state must reset once a box is drawn.
        assert dialog.view._add_mode is False
        assert dialog.add_region_button.isChecked() is False
        assert dialog._active_row == 1
        assert dialog.replacements[1].region.text == ""
        assert dialog.replacements[1].region.width >= 8 and dialog.replacements[1].region.height >= 8
    finally:
        dialog.deleteLater()


def test_new_box_translation_reaches_build_corrected_replacements(qapp: QApplication, tmp_path: Path) -> None:
    """The manually drawn box's geometry AND its typed-in translation must
    both flow through to build_corrected_replacements() exactly like an
    OCR-found row's edits do - the whole point of the feature."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=10, y=10, width=50, height=20, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Erste")],
    )
    try:
        dialog.add_region_button.setChecked(True)
        dialog.view.on_box_drawn(100, 120, 80, 40)
        assert dialog._active_row == 1

        dialog.editor.insertPlainText("Handschriftlich hinzugefügt")

        corrected = build_corrected_replacements(
            dialog.replacements, dialog._current_edits(), edited_geometry=dialog._edited_geometry or None,
        )
        assert len(corrected) == 2
        new_replacement = corrected[1]
        assert new_replacement.translated_text == "Handschriftlich hinzugefügt"
        assert (new_replacement.region.x, new_replacement.region.y, new_replacement.region.width, new_replacement.region.height) == (
            100, 120, 80, 40,
        )
        # The pre-existing OCR row must be completely untouched.
        assert corrected[0].translated_text == "Erste"
    finally:
        dialog.deleteLater()


def test_toggling_add_mode_off_without_drawing_leaves_no_stray_preview(qapp: QApplication, tmp_path: Path) -> None:
    """Turning "Neue Box hinzufügen" off again WITHOUT drawing anything
    (the user changed their mind) must not leave a half-drawn preview
    rectangle behind on the canvas, and must not add a row."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=10, y=10, width=50, height=20, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Erste")],
    )
    try:
        dialog.add_region_button.setChecked(True)
        # A press without a matching release (e.g. the user started
        # dragging, then clicked the toolbar button to cancel mid-drag).
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent

        press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress, QPointF(20, 20), QPointF(20, 20), Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        dialog.view.mousePressEvent(press)
        assert dialog.view._draw_preview is not None

        dialog.add_region_button.setChecked(False)

        assert dialog.view._draw_preview is None
        assert dialog.table.rowCount() == 1
        assert len(dialog.replacements) == 1
    finally:
        dialog.deleteLater()


# --- Canvas zoom (real user, 21.08.2026: "die Boxen ... nicht in der
# Grösse verändern" / "Das Quadrat zum aufziehen der Box ist sehr gross" -
# no way to zoom in on small text/boxes at all, and every box drew its own
# always-visible resize handle) -------------------------------------------


def test_zoom_in_and_out_change_view_scale_and_clamp(qapp: QApplication, tmp_path: Path) -> None:
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager
    from ui.image_correction_dialog import _MAX_VIEW_SCALE, _MIN_VIEW_SCALE, _ZOOM_STEP

    region = OcrTextRegion(text="First", x=0, y=0, width=200, height=100, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Text")],
    )
    try:
        dialog.view.resetTransform()
        before = dialog.view.transform().m11()

        dialog.view.zoom_in()
        after_in = dialog.view.transform().m11()
        assert after_in == pytest.approx(before * _ZOOM_STEP)

        dialog.view.zoom_out()
        dialog.view.zoom_out()
        after_out = dialog.view.transform().m11()
        assert after_out < after_in

        # Clamped, not unbounded - repeated zoom-out must never cross
        # _MIN_VIEW_SCALE, and repeated zoom-in must never cross
        # _MAX_VIEW_SCALE.
        for _ in range(60):
            dialog.view.zoom_out()
        assert dialog.view.transform().m11() >= _MIN_VIEW_SCALE * 0.99

        for _ in range(80):
            dialog.view.zoom_in()
        assert dialog.view.transform().m11() <= _MAX_VIEW_SCALE * 1.01
    finally:
        dialog.deleteLater()


def test_zoom_reset_button_restores_fit_and_re_enables_auto_fit(qapp: QApplication, tmp_path: Path) -> None:
    """"Ansicht anpassen" must both restore the fitted view AND turn
    _manual_zoom back off - otherwise a later window resize (see
    _ImageCanvasView.resizeEvent()) would stay frozen at whatever zoom the
    user had before clicking reset."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=0, y=0, width=200, height=100, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Text")],
    )
    try:
        dialog.view.zoom_in()
        dialog.view.zoom_in()
        assert dialog.view._manual_zoom is True

        dialog.zoom_reset_button.click()

        assert dialog.view._manual_zoom is False
    finally:
        dialog.deleteLater()


def test_ctrl_wheel_zooms_plain_wheel_does_not(qapp: QApplication, tmp_path: Path) -> None:
    """Strg+Mausrad zooms the canvas; a plain wheel notch is left to Qt's
    own scroll handling instead (see _ImageCanvasView.wheelEvent()'s
    docstring for why losing plain-scroll panning would have made a
    zoomed-in image harder to navigate, not easier)."""
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=0, y=0, width=200, height=100, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Text")],
    )
    try:
        dialog.view.resetTransform()
        before = dialog.view.transform().m11()

        pos = QPointF(50, 50)
        plain_event = QWheelEvent(
            pos, pos, QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False,
        )
        dialog.view.wheelEvent(plain_event)
        assert dialog.view.transform().m11() == pytest.approx(before)
        assert dialog.view._manual_zoom is False

        ctrl_event = QWheelEvent(
            pos, pos, QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier, Qt.ScrollPhase.NoScrollPhase, False,
        )
        dialog.view.wheelEvent(ctrl_event)
        assert dialog.view.transform().m11() > before
        assert dialog.view._manual_zoom is True
    finally:
        dialog.deleteLater()


def test_only_active_box_shows_and_hit_tests_the_resize_handle(qapp: QApplication, tmp_path: Path) -> None:
    """Regression guard for "Das Quadrat zum aufziehen der Box ist sehr
    gross": with one handle drawn per box, a dense infographic with many
    small boxes was cluttered by handles regardless of the handle's own
    size. Only the currently active (selected) box's handle should be
    drawn at all, or respond to a click inside its corner - an inactive
    box's corner must behave like the rest of the box (a plain move), not
    like a resize handle."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region_a = OcrTextRegion(text="First", x=0, y=0, width=100, height=60, confidence=90.0)
    region_b = OcrTextRegion(text="Second", x=150, y=0, width=100, height=60, confidence=90.0)
    replacements = [
        TextReplacement(region=region_a, translated_text="Eins"),
        TextReplacement(region=region_b, translated_text="Zwei"),
    ]
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png", replacements,
    )
    try:
        from PySide6.QtWidgets import QGraphicsSceneMouseEvent

        def _press_at_handle_center(item: "_ResizableRegionItem") -> None:
            local_pos = item._handle_rect().center()
            event = QGraphicsSceneMouseEvent(QGraphicsSceneMouseEvent.Type.GraphicsSceneMousePress)
            event.setPos(local_pos)
            event.setScenePos(item.mapToScene(local_pos))
            event.setButton(Qt.MouseButton.LeftButton)
            event.setButtons(Qt.MouseButton.LeftButton)
            item.mousePressEvent(event)

        active_item = dialog._region_items[0]
        inactive_item = dialog._region_items[1]
        assert active_item._active is True
        assert inactive_item._active is False

        # Pressing inside the inactive box's own corner (where a handle
        # WOULD be if it were active) must start a plain move, never a
        # resize - _resizing stays False. Every _ResizableRegionItem press
        # also selects its row (see mousePressEvent()'s on_selected() call,
        # mirroring a real click), so this same press makes inactive_item
        # the new active row as a side effect - exactly like clicking
        # anywhere else on an inactive box in the real app would.
        _press_at_handle_center(inactive_item)
        assert inactive_item._resizing is False
        inactive_item.mouseReleaseEvent(
            QGraphicsSceneMouseEvent(QGraphicsSceneMouseEvent.Type.GraphicsSceneMouseRelease)
        )
        assert inactive_item._active is True
        assert active_item._active is False

        # NOW that this box is the active one, pressing the SAME corner
        # again must start a real resize - "select, then drag the handle"
        # is exactly the intended two-step workflow.
        _press_at_handle_center(inactive_item)
        assert inactive_item._resizing is True
    finally:
        dialog.deleteLater()


def test_dialog_window_can_be_maximized(qapp: QApplication, tmp_path: Path) -> None:
    """Regression guard for "Der Koorektur Dialog kann auch nicht auf
    Vollbild gesetzt werden" - a plain QDialog gets no maximize button on
    most platforms/window managers by default, which matters here
    specifically because the canvas needs all the screen space it can get
    for precise box editing."""
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager

    region = OcrTextRegion(text="First", x=0, y=0, width=100, height=60, confidence=90.0)
    dialog = ImageCorrectionDialog(
        LanguageManager("de"), tmp_path / "photo.png", tmp_path / "photo_DE.png",
        [TextReplacement(region=region, translated_text="Eins")],
    )
    try:
        assert bool(dialog.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint)
    finally:
        dialog.deleteLater()
