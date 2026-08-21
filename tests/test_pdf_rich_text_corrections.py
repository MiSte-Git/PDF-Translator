"""Regression coverage for ui/rich_text.py's qt_document_to_project_html()
and pipeline.pdf.translate_pdf.build_corrected_records_from_html() -
together the rich-text half of RoadMap.md Phase 2/PDF's "PDF-Übersetzung
korrigieren" item (see ui/correction_dialog.py's docstring for why
plain-text-only editing wasn't enough: a real user explicitly asked for
Fett/Kursiv/Unterstrichen to survive an edited row instead of being
silently dropped).

Uses a real QTextEdit (offscreen platform, same setup as
tests/test_ui_pdf_correction.py) to build QTextDocument fixtures via
setHtml()/mergeCurrentCharFormat()/QTextCursor, rather than hand-building
a QTextDocument through its lower-level block API directly - closer to
how PdfCorrectionDialog's own editor is actually driven by a real user.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymupdf as fitz
import pytest
from PySide6.QtGui import QFont, QTextCharFormat
from PySide6.QtWidgets import QApplication, QTextEdit

from pipeline.pdf.base import TextSpan
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html
from pipeline.pdf.translate_pdf import TranslatedBlockRecord, build_corrected_records_from_html
from ui.correction_dialog import PdfCorrectionDialog
from ui.i18n import LanguageManager
from ui.rich_text import qt_document_to_project_html


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _editor_html(source_html: str, edit=None) -> str:
    """Build a QTextEdit, load `source_html` (skipped if empty - some
    cases build content purely via `edit`'s cursor calls instead), apply
    `edit` (a callable receiving the editor), and return
    qt_document_to_project_html() of the result - the same
    load -> mutate -> flush sequence PdfCorrectionDialog's
    _load_row()/_flush_active_row() drive for a real user edit.
    """
    editor = QTextEdit()
    if source_html:
        editor.setHtml(source_html)
    if edit is not None:
        edit(editor)
    return qt_document_to_project_html(editor.document())


def test_plain_text_round_trip(qapp: QApplication) -> None:
    assert _editor_html("<p>Hello world</p>") == "<p>Hello world</p>"


def test_bold_applied_via_merge_current_char_format(qapp: QApplication) -> None:
    def make_bold(editor: QTextEdit) -> None:
        editor.selectAll()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        editor.mergeCurrentCharFormat(fmt)

    assert _editor_html("<p>Hello world</p>", make_bold) == "<p><b>Hello world</b></p>"


def test_italic_and_underline_combine(qapp: QApplication) -> None:
    def make_italic_underline(editor: QTextEdit) -> None:
        editor.selectAll()
        fmt = QTextCharFormat()
        fmt.setFontItalic(True)
        fmt.setFontUnderline(True)
        editor.mergeCurrentCharFormat(fmt)

    # Tag nesting order matches spans_to_html()'s own convention: <u>
    # innermost, then <i> wraps it, then <b> would wrap that.
    assert _editor_html("<p>Quote</p>", make_italic_underline) == "<p><i><u>Quote</u></i></p>"


def test_partial_selection_bold_keeps_rest_plain(qapp: QApplication) -> None:
    """Exactly the real-world case that motivated this whole feature: a
    single word (a proper name like "Manuel") gets bolded/corrected
    within an otherwise-plain line, not the whole block.
    """
    def bold_first_word(editor: QTextEdit) -> None:
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor, len("Manuel"))
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)

    result = _editor_html("<p>Manuel to PQ</p>", bold_first_word)
    assert result == "<p><b>Manuel</b> to PQ</p>"


def test_multi_paragraph_round_trip(qapp: QApplication) -> None:
    assert _editor_html("<p>First</p><p>Second</p>") == "<p>First</p><p>Second</p>"


def test_soft_line_break_becomes_br(qapp: QApplication) -> None:
    def insert_with_soft_break(editor: QTextEdit) -> None:
        cursor = editor.textCursor()
        cursor.insertText("Line one")
        cursor.insertText(" ")
        cursor.insertText("Line two")

    assert _editor_html("", insert_with_soft_break) == "<p>Line one<br/>Line two</p>"


def test_html_special_characters_are_escaped(qapp: QApplication) -> None:
    def replace_with_special_chars(editor: QTextEdit) -> None:
        editor.selectAll()
        editor.insertPlainText("A & B < C")

    assert _editor_html("<p>Original text</p>", replace_with_special_chars) == "<p>A &amp; B &lt; C</p>"


def test_empty_editor_returns_empty_string(qapp: QApplication) -> None:
    assert _editor_html("") == ""


def _record(page=0, block=0, original="Original", html="<p>Original [DE]</p>") -> TranslatedBlockRecord:
    return TranslatedBlockRecord(page_index=page, block_index=block, original_text=original, translated_html=html)


def test_build_corrected_records_from_html_missing_key_passes_through_unchanged() -> None:
    record = _record()
    result = build_corrected_records_from_html([record], {})
    assert result == [record]
    assert result[0] is record  # exact original object - see that function's docstring


def test_build_corrected_records_from_html_present_key_replaces_translated_html() -> None:
    record = _record()
    edited_html = {(0, 0): "<p><b>Manuel</b> to PQ</p>"}
    result = build_corrected_records_from_html([record], edited_html)
    assert result[0] is not record
    assert result[0].translated_html == "<p><b>Manuel</b> to PQ</p>"
    assert result[0].page_index == record.page_index
    assert result[0].block_index == record.block_index
    assert result[0].original_text == record.original_text


def test_build_corrected_records_from_html_only_matching_key_is_replaced() -> None:
    record_a = _record(page=0, block=0, html="<p>A</p>")
    record_b = _record(page=0, block=1, html="<p>B</p>")
    edited_html = {(0, 1): "<p><i>B edited</i></p>"}
    result = build_corrected_records_from_html([record_a, record_b], edited_html)
    assert result[0] is record_a
    assert result[1] is not record_b
    assert result[1].translated_html == "<p><i>B edited</i></p>"


def _build_two_block_source(path: Path) -> None:
    """Mirrors tests/test_pdf_translation_corrections.py's helper of the
    same name: two ordinary, well-separated single-line blocks - block 0
    gets the real "Manuel" -> "Handbuch" mistranslation fixed (and made
    bold, this time, via the dialog's rich-text editor); block 1 stays an
    untouched bold control.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    page.insert_textbox(fitz.Rect(50, 50, 350, 70), "Manuel to PQ", fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(50, 150, 350, 170), "Second block text", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_dialog_bold_correction_survives_into_saved_pdf_alongside_untouched_bold_block(
    qapp: QApplication, tmp_path: Path
) -> None:
    """End-to-end through the ACTUAL PdfCorrectionDialog (not just
    qt_document_to_project_html() in isolation): the real "Manuel" ->
    "Handbuch" scenario, fixed AND bolded via the rich-text editor, while
    an untouched bold block keeps its own bold formatting - the exact
    workflow a real user asked for once plain-text-only editing turned
    out to lose formatting on every edited row.
    """
    source = tmp_path / "source.pdf"
    _build_two_block_source(source)
    destination = tmp_path / "corrected.pdf"

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block0 = engine.extract_blocks(0)[0]
    block1 = engine.extract_blocks(0)[1]
    block0.spans = [TextSpan(text="- Handbuch to PQ", font_name="helv", font_size=11.0,
                              color=(0, 0, 0), bold=False, italic=False, underline=False)]
    block1.spans = [TextSpan(text="Second block translated", font_name="helv", font_size=11.0,
                              color=(0, 0, 0), bold=True, italic=False, underline=False)]

    records = [
        TranslatedBlockRecord(
            page_index=0, block_index=0, original_text="Manuel to PQ",
            translated_html=spans_to_html(block0.spans),
        ),
        TranslatedBlockRecord(
            page_index=0, block_index=1, original_text="Second block text",
            translated_html=spans_to_html(block1.spans),
        ),
    ]

    dialog = PdfCorrectionDialog(LanguageManager("de"), source, destination, records)
    try:
        # Row 0 is loaded by __init__ - fix the wrong word AND bold it,
        # exactly like a user correcting a mistranslated proper name and
        # wanting it to stand out.
        dialog.editor.selectAll()
        dialog.editor.insertPlainText("- Manuel to PQ")
        dialog.editor.selectAll()
        dialog.bold_button.setChecked(True)
        dialog._toggle_bold()
        dialog._apply()
        assert dialog.last_result is not None
    finally:
        dialog.deleteLater()

    result = fitz.open(str(destination))
    page = result[0]
    extracted = " ".join(page.get_text().split())
    assert "Handbuch" not in extracted
    assert "Manuel" in extracted

    raw = page.get_text("dict")
    matching_spans = [
        span
        for b in raw["blocks"] if b.get("type") == 0
        for line in b["lines"]
        for span in line["spans"]
        if span["text"].strip() and span["text"].strip() in "- Manuel to PQ"
    ]
    assert matching_spans, "expected to find spans making up the corrected first block"
    assert all("bold" in span["font"].lower() for span in matching_spans), (
        "the user's own bold correction did not survive into the saved PDF"
    )

    second_block_spans = [
        span
        for b in raw["blocks"] if b.get("type") == 0
        for line in b["lines"]
        for span in line["spans"]
        if span["text"].strip() and span["text"].strip() in "Second block translated"
    ]
    assert second_block_spans, "expected to find spans making up the untouched second block"
    assert all("bold" in span["font"].lower() for span in second_block_spans), (
        "the untouched block's original bold formatting was lost"
    )
    result.close()
