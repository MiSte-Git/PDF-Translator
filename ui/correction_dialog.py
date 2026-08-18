"""Manual-correction table for a finished PDF translation (RoadMap.md
Phase 2/PDF's "PDF-Übersetzung korrigieren" item) - added after a real
user found a genuine mistranslation (a proper name rendered as an
unrelated word) in a live run and asked for an in-app way to fix
individual blocks without leaving the tool or reinventing a full PDF
editor.

Reuses pipeline.pdf.translate_pdf.build_corrected_records_from_html()/
apply_pdf_corrections() (via ui.pdf_job.run_pdf_correction_job()) - the
same redact_block()/insert_text() machinery translate_pdf() itself uses,
just re-run against a fresh copy of the pristine source with the (edited)
translations already known, no provider/network call involved.

Per-row editing is a rich-text QTextEdit with Fett/Kursiv/Unterstrichen
toggle buttons (see ui/rich_text.py's qt_document_to_project_html()), not
a plain table cell. This replaced an earlier plain-text-only version
(directly editing a QTableWidgetItem) whose edited rows always lost
inline formatting on save - a real user explicitly asked for the
formatting to survive an edit instead.

Strg+B/Strg+I/Strg+U (QKeySequence.StandardKey.Bold/Italic/Underline -
the platform-appropriate binding, e.g. Cmd on macOS) mirror the three
toolbar buttons exactly - added after the toolbar-only version shipped,
on the same user's follow-up request for keyboard shortcuts, the same
"select a word, hit a key" muscle memory every other rich-text editor
already trained them on.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
)

from pipeline.pdf.pymupdf_engine import html_to_plain_text
from pipeline.pdf.translate_pdf import TranslatedBlockRecord, build_corrected_records_from_html
from ui.i18n import LanguageManager
from ui.pdf_job import PdfJobResult, run_pdf_correction_job
from ui.rich_text import qt_document_to_project_html

_PAGE_COLUMN = 0
_ORIGINAL_COLUMN = 1
_TRANSLATION_COLUMN = 2


class PdfCorrectionDialog(QDialog):
    """One row per TranslatedBlockRecord in the overview table (Seite/
    Original/Übersetzung-preview, all read-only); selecting a row loads
    its translation into the rich-text editor below (Fett/Kursiv/
    Unterstrichen toggle buttons + a QTextEdit) for actual editing.
    "Anwenden und speichern" re-renders the whole PDF from the pristine
    source with the (possibly edited) translations and overwrites
    `destination` in place - see run_pdf_correction_job()'s docstring for
    why overwriting is intentional here, unlike every other job in this
    app which refuses an existing destination.
    """

    def __init__(
        self,
        language: LanguageManager,
        source: Path,
        destination: Path,
        records: list[TranslatedBlockRecord],
        exclude_header: bool = False,
        exclude_footer: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.language = language
        self.source = Path(source)
        self.destination = Path(destination)
        self.records = records
        self.exclude_header = exclude_header
        self.exclude_footer = exclude_footer
        self.last_result: PdfJobResult | None = None
        self.last_corrected_records: list[TranslatedBlockRecord] | None = None
        """Set by _apply() to the exact records list a successful
        "Anwenden" just wrote out - lets the caller (ui/app.py's
        _open_correction_dialog()) use these, not the ORIGINAL
        pre-correction records, as the starting point if the dialog is
        reopened - otherwise a second correction round would silently
        discard the first one's edits and start over from the machine
        translation again."""

        self._row_html: list[str] = [record.translated_html for record in records]
        """Per-row CURRENT translated_html, index-aligned with `records`.
        Starts as each record's original, untouched html. Only ever
        overwritten by _flush_active_row() for a row _dirty actually
        contains (see below) - a row never visited, or visited but never
        genuinely edited, keeps its exact original string, byte for byte,
        rather than a re-serialized-but-visually-identical round-trip
        through Qt's rich text engine."""
        self._dirty: set[int] = set()
        """Row indices _on_editor_text_changed() saw a REAL edit happen in
        (never a programmatic _load_row() setHtml() call - see
        _loading). Drives both _flush_active_row()'s decision to
        overwrite _row_html[row] and _apply()'s decision to include that
        row in build_corrected_records_from_html()'s edited_html at all -
        a row merely selected/viewed but never changed is left out
        entirely, so it passes through with its pristine original html."""
        self._active_row: int | None = None
        self._loading = False

        t = self.language.text
        self.setWindowTitle(t("correction.title"))
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        hint = QLabel(t("correction.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(len(records), 3, self)
        self.table.setHorizontalHeaderLabels(
            [t("correction.column_page"), t("correction.column_original"), t("correction.column_translation")]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        for row, record in enumerate(records):
            page_item = QTableWidgetItem(str(record.page_index + 1))
            page_item.setFlags(page_item.flags() & ~Qt.ItemIsEditable)
            original_item = QTableWidgetItem(record.original_text)
            original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
            # Read-only PREVIEW of the translation (kept in sync by
            # _flush_active_row()) - actual editing happens in self.editor
            # below, not in this cell, so it never accepts direct input.
            translation_item = QTableWidgetItem(record.display_text)
            translation_item.setFlags(translation_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, _PAGE_COLUMN, page_item)
            self.table.setItem(row, _ORIGINAL_COLUMN, original_item)
            self.table.setItem(row, _TRANSLATION_COLUMN, translation_item)
        self.table.currentCellChanged.connect(self._on_row_changed)
        layout.addWidget(self.table)

        editor_label = QLabel(t("correction.editor_label"))
        layout.addWidget(editor_label)

        toolbar = QHBoxLayout()
        self.bold_button = QPushButton(t("correction.bold"))
        self.bold_button.setCheckable(True)
        self.bold_button.setToolTip(t("correction.bold_tooltip"))
        self.bold_button.clicked.connect(self._toggle_bold)
        toolbar.addWidget(self.bold_button)
        self.italic_button = QPushButton(t("correction.italic"))
        self.italic_button.setCheckable(True)
        self.italic_button.setToolTip(t("correction.italic_tooltip"))
        self.italic_button.clicked.connect(self._toggle_italic)
        toolbar.addWidget(self.italic_button)
        self.underline_button = QPushButton(t("correction.underline"))
        self.underline_button.setCheckable(True)
        self.underline_button.setToolTip(t("correction.underline_tooltip"))
        self.underline_button.clicked.connect(self._toggle_underline)
        toolbar.addWidget(self.underline_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(True)
        self.editor.setFixedHeight(140)
        self.editor.textChanged.connect(self._on_editor_text_changed)
        self.editor.currentCharFormatChanged.connect(self._sync_toolbar_state)
        layout.addWidget(self.editor)

        # Strg+B/Strg+I/Strg+U - see this class's docstring. WidgetShortcut
        # context: only fires while self.editor (or a descendant) has
        # focus, not globally across the whole dialog - e.g. typing "b" in
        # the table's (nonexistent) filter field, if one is ever added,
        # would never be mistaken for a bold toggle.
        self._bold_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Bold), self.editor)
        self._bold_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._bold_shortcut.activated.connect(self._shortcut_toggle_bold)
        self._italic_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Italic), self.editor)
        self._italic_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._italic_shortcut.activated.connect(self._shortcut_toggle_italic)
        self._underline_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Underline), self.editor)
        self._underline_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._underline_shortcut.activated.connect(self._shortcut_toggle_underline)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.apply_button = QPushButton(t("correction.apply"))
        self.apply_button.clicked.connect(self._apply)
        buttons.addWidget(self.apply_button)
        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        close_box.button(QDialogButtonBox.Close).setText(t("correction.close"))
        buttons.addWidget(close_box)
        layout.addLayout(buttons)

        if records:
            # Not left to the currentCellChanged signal from
            # setCurrentCell() below (Qt's "no previous current cell"
            # edge case is a poor fit to rely on for something this
            # dialog's usability depends on) - loaded directly, then the
            # table selection is just cosmetic follow-up.
            self._load_row(0)
            self.table.setCurrentCell(0, _TRANSLATION_COLUMN)

    def _on_row_changed(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        if current_row < 0 or current_row == self._active_row:
            return
        self._load_row(current_row)

    def _load_row(self, row: int) -> None:
        self._flush_active_row()
        self._active_row = row
        self._loading = True
        try:
            self.editor.setHtml(self._row_html[row])
        finally:
            self._loading = False
        self._sync_toolbar_state()

    def _flush_active_row(self) -> None:
        """Write the editor's CURRENT content back into _row_html for the
        row that was active until now - but only if that row is actually
        in _dirty (see its docstring for why an untouched row must keep
        its pristine original string instead of a Qt round-trip).
        """
        if self._active_row is None or self._active_row not in self._dirty:
            return
        row = self._active_row
        self._row_html[row] = qt_document_to_project_html(self.editor.document())
        preview_item = self.table.item(row, _TRANSLATION_COLUMN)
        if preview_item is not None:
            preview_item.setText(html_to_plain_text(self._row_html[row]))

    def _on_editor_text_changed(self) -> None:
        if self._loading or self._active_row is None:
            return
        self._dirty.add(self._active_row)

    def _sync_toolbar_state(self) -> None:
        char_format = self.editor.textCursor().charFormat()
        self.bold_button.setChecked(char_format.fontWeight() >= QFont.Weight.Bold)
        self.italic_button.setChecked(char_format.fontItalic())
        self.underline_button.setChecked(char_format.fontUnderline())

    def _apply_char_format(self, mutate) -> None:
        """Merge a QTextCharFormat built by `mutate` into the editor's
        current selection (or, with no selection, into the format new
        typing will use from here on) - QTextEdit.mergeCurrentCharFormat()
        already handles both cases itself, see its Qt docs.
        """
        char_format = QTextCharFormat()
        mutate(char_format)
        self.editor.mergeCurrentCharFormat(char_format)

    def _toggle_bold(self) -> None:
        weight = QFont.Weight.Bold if self.bold_button.isChecked() else QFont.Weight.Normal
        self._apply_char_format(lambda fmt: fmt.setFontWeight(weight))

    def _toggle_italic(self) -> None:
        checked = self.italic_button.isChecked()
        self._apply_char_format(lambda fmt: fmt.setFontItalic(checked))

    def _toggle_underline(self) -> None:
        checked = self.underline_button.isChecked()
        self._apply_char_format(lambda fmt: fmt.setFontUnderline(checked))

    def _shortcut_toggle_bold(self) -> None:
        """Strg+B handler - a checkable QPushButton flips its OWN checked
        state automatically before a mouse click reaches _toggle_bold()
        (see that method's isChecked() read); a QShortcut has no such
        button to flip, so this flips bold_button explicitly first, then
        reuses _toggle_bold() exactly as if the button had been clicked.
        """
        self.bold_button.setChecked(not self.bold_button.isChecked())
        self._toggle_bold()

    def _shortcut_toggle_italic(self) -> None:
        self.italic_button.setChecked(not self.italic_button.isChecked())
        self._toggle_italic()

    def _shortcut_toggle_underline(self) -> None:
        self.underline_button.setChecked(not self.underline_button.isChecked())
        self._toggle_underline()

    def _current_edits(self) -> dict[tuple[int, int], str]:
        self._flush_active_row()
        edits: dict[tuple[int, int], str] = {}
        for row, record in enumerate(self.records):
            if row in self._dirty:
                edits[(record.page_index, record.block_index)] = self._row_html[row]
        return edits

    def _apply(self) -> None:
        t = self.language.text
        self.apply_button.setEnabled(False)
        self.status_label.setText(t("correction.applying"))
        # No provider/network call is involved (see run_pdf_correction_job()'s
        # docstring) - fast and local enough to run directly on the UI
        # thread rather than wiring a background QThreadPool worker just
        # for this action.
        try:
            corrected_records = build_corrected_records_from_html(self.records, self._current_edits())
            result = run_pdf_correction_job(
                self.source, self.destination, corrected_records,
                exclude_header=self.exclude_header, exclude_footer=self.exclude_footer,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not silently swallowed
            self.status_label.setText(t("correction.failed", error=str(exc)))
            QMessageBox.warning(self, t("correction.title"), t("correction.failed", error=str(exc)))
            return
        finally:
            self.apply_button.setEnabled(True)

        self.last_result = result
        self.last_corrected_records = corrected_records
        self.status_label.setText(
            t("correction.success", count=result.stats.translated, output=str(result.output_path))
        )
