"""Regression coverage for the "PDF-Übersetzung korrigieren" UI wiring
(RoadMap.md Phase 2/PDF): MainWindow._show_job_result() must show
correct_translation_button only for a PDF result that actually produced
correctable blocks, and _open_correction_dialog()/PdfCorrectionDialog
(ui/correction_dialog.py) must apply a rich-text editor edit through to
the saved PDF, exactly the workflow a real user asked for after finding a
genuine mistranslation ("Manuel" -> "Handbuch") in a live run - and, once
plain-text-only editing turned out to lose formatting on every edited
row, asked specifically for a Fett/Kursiv/Unterstrichen-capable editor
instead (see ui/rich_text.py).

Mirrors tests/test_ui_word_mode.py's QApplication/offscreen-platform
setup. PdfCorrectionDialog.exec() is monkeypatched to synchronously
simulate a user editing the rich-text editor and clicking "Anwenden"
instead of opening a real (blocking) modal dialog loop - the same
"intercept the blocking primitive, not the business logic" pattern
test_ui_word_mode.py's QThreadPool.start() monkeypatch uses.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz
import pytest
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import QApplication

from pipeline.pdf.translate_pdf import PdfTranslationStats, TranslatedBlockRecord
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.app import MainWindow
from ui.correction_dialog import PdfCorrectionDialog
from ui.pdf_job import PdfJobResult, run_pdf_job
from ui.word_job import WordJobResult

PDF_FIXTURE = Path(__file__).parent / "fixtures" / "representative.pdf"


class FakeHtmlProvider:
    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{html} [DE]", source_lang or "", target_lang, "fake")

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _prepare_job_context(window: MainWindow, source: Path) -> None:
    """Sets exactly the state _start() would have set before a real run,
    without actually running one - see this module's docstring.
    """
    window._job_source_path = source
    window._job_exclude_header = False
    window._job_exclude_footer = False


def test_correct_translation_button_visible_for_pdf_result_with_blocks(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        result = PdfJobResult(
            output_path=Path("out.pdf"), qa_report_path=Path("out_qa_report.txt"),
            stats=PdfTranslationStats(
                translated=1,
                blocks=[TranslatedBlockRecord(0, 0, "Original", "<p>Original [DE]</p>")],
            ),
        )
        window._job_result = result
        window._show_job_result(result)
        assert window.correct_translation_button.isVisible()
    finally:
        window.close()


def test_correct_translation_button_hidden_when_no_blocks(qapp: QApplication) -> None:
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


def test_correct_translation_button_hidden_for_non_pdf_result(qapp: QApplication) -> None:
    from pipeline.word.translate_document import TranslationStats

    window = MainWindow()
    window.show()
    try:
        result = WordJobResult(
            output_path=Path("out.docx"), qa_report_path=Path("out_qa_report.txt"),
            stats=TranslationStats(body_translated=1),
        )
        window._job_result = result
        window._show_job_result(result)
        assert not window.correct_translation_button.isVisible()
    finally:
        window.close()


def test_open_correction_dialog_applies_edit_and_refreshes_result(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(PDF_FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"

    original_result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
    )
    assert len(original_result.stats.blocks) == 1

    def fake_exec(self: PdfCorrectionDialog) -> int:
        # Simulate the user editing row 0's rich-text editor (already
        # loaded by __init__'s initial _load_row(0)), then clicking
        # "Anwenden" - see this module's docstring for why exec() itself
        # (which would otherwise block on a real modal event loop) is
        # replaced rather than the actual apply logic.
        self.editor.selectAll()
        self.editor.insertPlainText("Handkorrigierter Text")
        self._apply()
        return 0

    monkeypatch.setattr(PdfCorrectionDialog, "exec", fake_exec)

    window = MainWindow()
    window.show()
    try:
        window._job_result = original_result
        _prepare_job_context(window, source)
        window._show_job_result(original_result)
        assert window.correct_translation_button.isVisible()

        window._open_correction_dialog()

        assert window._job_result is not None
        assert window._job_result.output_path == destination
        # Reopening again must start from THIS round's edit, not silently
        # discard it back to the original machine translation - see
        # ui/app.py's _open_correction_dialog() docstring/comment.
        assert window._job_result.stats.blocks[0].display_text == "Handkorrigierter Text"
    finally:
        window.close()

    doc = fitz.open(str(destination))
    text = " ".join(doc[0].get_text().split())
    assert "Handkorrigierter Text" in text
    doc.close()


def test_correction_dialog_unedited_row_keeps_original_html(tmp_path: Path, qapp: QApplication) -> None:
    """Direct dialog-level check (no MainWindow involved) that a row the
    user never touches is passed straight through unchanged - see
    build_corrected_records_from_html()'s docstring for why this matters
    (formatting preservation). The real gate for THIS end-to-end
    guarantee is _current_edits()'s own `if row in self._dirty` filter
    (an untouched row is never even added to build_corrected_records_from_html()'s
    edited_html dict, regardless of what _row_html holds) - see
    test_switching_rows_without_editing_keeps_original_html_object() below
    for a narrower check of _flush_active_row()'s OWN _dirty guard, which
    only matters for what a LATER edit on the same row would start from,
    not for this test's outcome.
    """
    source = tmp_path / "Doc.pdf"
    source.write_bytes(PDF_FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
    )
    original_html = result.stats.blocks[0].translated_html

    from ui.i18n import LanguageManager

    dialog = PdfCorrectionDialog(
        LanguageManager("de"), source, destination, result.stats.blocks,
    )
    try:
        dialog._apply()
        assert dialog.last_corrected_records is not None
        assert dialog.last_corrected_records[0].translated_html == original_html
        assert dialog.last_corrected_records[0].translated_html is original_html
    finally:
        dialog.deleteLater()


def test_switching_rows_without_editing_keeps_original_html_object(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Narrower counterpart to test_correction_dialog_unedited_row_keeps_original_html()
    above: directly exercises PdfCorrectionDialog._flush_active_row()'s OWN
    _dirty guard (switching away from a row the user never edited), rather
    than the FINAL applied-output guarantee - which stays correct either
    way thanks to _current_edits()'s separate _dirty filter (confirmed by
    deliberately reverting _flush_active_row()'s guard alone: the
    unconditional-== version of the test above still passed, since
    _current_edits() never even looks at a round-tripped-but-clean
    _row_html entry - only THIS test's `is` check on _row_html itself
    actually caught that regression). Matters because a later genuine
    edit on the SAME row would otherwise start from a silently
    round-tripped base instead of the row's true original html.
    """
    from ui.i18n import LanguageManager

    records = [
        TranslatedBlockRecord(0, 0, "First original", "<p>First translated</p>"),
        TranslatedBlockRecord(0, 1, "Second original", "<p>Second translated</p>"),
    ]
    dialog = PdfCorrectionDialog(
        LanguageManager("de"), tmp_path / "Doc.pdf", tmp_path / "Doc_DE.pdf", records,
    )
    try:
        original_html_0 = records[0].translated_html
        dialog._load_row(1)  # switch away from row 0 without ever editing it
        assert dialog._row_html[0] is original_html_0
    finally:
        dialog.deleteLater()


def _new_dialog(qapp: QApplication, tmp_path: Path) -> PdfCorrectionDialog:
    from ui.i18n import LanguageManager

    records = [TranslatedBlockRecord(0, 0, "Manuel to PQ", "<p>Handbuch to PQ</p>")]
    return PdfCorrectionDialog(
        LanguageManager("de"), tmp_path / "Doc.pdf", tmp_path / "Doc_DE.pdf", records,
    )


def test_bold_keyboard_shortcut_is_bound_to_the_standard_key(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Wiring check, not a behavior check (see the next three tests for
    that): the shortcut is bound to Qt's own StandardKey.Bold, the
    platform-appropriate binding (Strg+B on this Linux desktop, Cmd+B on
    macOS) - not a hand-picked key sequence that could silently drift
    from what every other rich-text editor already trained the user to
    expect.
    """
    dialog = _new_dialog(qapp, tmp_path)
    try:
        assert dialog._bold_shortcut.key() == QKeySequence(QKeySequence.StandardKey.Bold)
        assert dialog._italic_shortcut.key() == QKeySequence(QKeySequence.StandardKey.Italic)
        assert dialog._underline_shortcut.key() == QKeySequence(QKeySequence.StandardKey.Underline)
    finally:
        dialog.deleteLater()


def test_bold_shortcut_handler_toggles_button_and_selection_format(
    qapp: QApplication, tmp_path: Path
) -> None:
    """_shortcut_toggle_bold() (what Strg+B's activated signal actually
    calls - see this module's docstring for why the signal itself isn't
    triggered via a simulated key press: QShortcut delivery on an
    offscreen platform is Qt-internal plumbing, not this dialog's own
    logic) must both flip bold_button's checked state AND apply bold to
    the current selection, exactly like clicking the toolbar button would.
    """
    dialog = _new_dialog(qapp, tmp_path)
    try:
        dialog.editor.selectAll()
        assert not dialog.bold_button.isChecked()

        dialog._shortcut_toggle_bold()
        assert dialog.bold_button.isChecked()
        assert dialog.editor.textCursor().charFormat().fontWeight() >= QFont.Weight.Bold

        dialog._shortcut_toggle_bold()  # pressing it again toggles back off
        assert not dialog.bold_button.isChecked()
    finally:
        dialog.deleteLater()


def test_italic_and_underline_shortcut_handlers_toggle_their_own_button(
    qapp: QApplication, tmp_path: Path
) -> None:
    dialog = _new_dialog(qapp, tmp_path)
    try:
        dialog.editor.selectAll()

        dialog._shortcut_toggle_italic()
        assert dialog.italic_button.isChecked()
        assert dialog.editor.textCursor().charFormat().fontItalic()

        dialog._shortcut_toggle_underline()
        assert dialog.underline_button.isChecked()
        assert dialog.editor.textCursor().charFormat().fontUnderline()

        # Bold's own state is untouched by the other two shortcuts.
        assert not dialog.bold_button.isChecked()
    finally:
        dialog.deleteLater()


def test_bold_shortcut_marks_row_dirty_and_survives_apply(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End-to-end: the keyboard shortcut, not the toolbar button, is what
    marks the row dirty (via the same textChanged signal - see
    PdfCorrectionDialog._on_editor_text_changed()) and what a saved
    correction actually contains.
    """
    source = tmp_path / "Doc.pdf"
    source.write_bytes(PDF_FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
    )

    from ui.i18n import LanguageManager

    dialog = PdfCorrectionDialog(LanguageManager("de"), source, destination, result.stats.blocks)
    try:
        dialog.editor.selectAll()
        dialog._shortcut_toggle_bold()
        assert dialog._active_row in dialog._dirty

        dialog._apply()
        assert dialog.last_corrected_records is not None
        assert "<b>" in dialog.last_corrected_records[0].translated_html
    finally:
        dialog.deleteLater()
