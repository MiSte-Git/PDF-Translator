"""Manual-correction table for a finished Bildübersetzung (RoadMap.md
Phase 3's "Korrektur-Möglichkeit ... analog zur PDF-Variante" item) -
built directly after ui/correction_dialog.py's PdfCorrectionDialog, on the
explicit reasoning that the correction pattern is needed everywhere
(images, and later PDF/Word/PPTX embedded image translation too), so it
should be built once, well, rather than reinvented per format.

Reuses pipeline.images.translate_image.build_corrected_replacements() (via
ui.image_job.run_image_correction_job()) - the same InpaintingBackend.apply()
machinery translate_image() itself uses, just re-run against a fresh copy
of the pristine source image with the (edited) translations already known,
no OCR/provider/network call involved.

Deliberately SIMPLER than PdfCorrectionDialog: plain-text editing only (a
QPlainTextEdit, no rich-text toolbar/shortcuts) - raster-drawn image text
via PIL's ImageDraw.text() has no bold/italic/underline concept the way a
PDF's rich-text box does, so there is no formatting to preserve or toggle
here (see pipeline.images.translate_image.build_corrected_replacements()'s
docstring). Also no page column - a single image has no page concept, so
the table is just Original/Übersetzung.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)
from PySide6.QtCore import Qt

from pipeline.images.inpainting import TextReplacement
from pipeline.images.translate_image import build_corrected_replacements
from ui.i18n import LanguageManager
from ui.image_job import ImageJobResult, run_image_correction_job

_ORIGINAL_COLUMN = 0
_TRANSLATION_COLUMN = 1


class ImageCorrectionDialog(QDialog):
    """One row per TextReplacement in the overview table (Original/
    Übersetzung-preview, both read-only); selecting a row loads its
    translation into the plain-text editor below for actual editing.
    "Anwenden und speichern" re-renders the image from the pristine
    source with the (possibly edited) translations and overwrites
    `destination` in place - see run_image_correction_job()'s docstring
    for why overwriting is intentional here, unlike run_image_job()
    itself, which refuses an existing destination.
    """

    def __init__(
        self,
        language: LanguageManager,
        source: Path,
        destination: Path,
        replacements: list[TextReplacement],
        inpainting_backend_name: str = "box_overlay",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.language = language
        self.source = Path(source)
        self.destination = Path(destination)
        self.replacements = replacements
        self.inpainting_backend_name = inpainting_backend_name
        self.last_result: ImageJobResult | None = None
        self.last_corrected_replacements: list[TextReplacement] | None = None
        """Set by _apply() to the exact replacements list a successful
        "Anwenden" just wrote out - lets the caller (ui/app.py's
        _open_image_correction_dialog()) use these, not the ORIGINAL
        pre-correction replacements, as the starting point if the dialog
        is reopened - otherwise a second correction round would silently
        discard the first one's edits and start over from the machine
        translation again. Mirrors PdfCorrectionDialog.last_corrected_records."""

        self._row_text: list[str] = [replacement.translated_text for replacement in replacements]
        """Per-row CURRENT translated_text, index-aligned with
        `replacements`. Starts as each replacement's original, untouched
        text. Only ever overwritten by _flush_active_row() for a row
        _dirty actually contains - mirrors PdfCorrectionDialog._row_html."""
        self._dirty: set[int] = set()
        self._active_row: int | None = None
        self._loading = False

        t = self.language.text
        self.setWindowTitle(t("image_correction.title"))
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        hint = QLabel(t("image_correction.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(len(replacements), 2, self)
        self.table.setHorizontalHeaderLabels(
            [t("image_correction.column_original"), t("image_correction.column_translation")]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        for row, replacement in enumerate(replacements):
            original_item = QTableWidgetItem(replacement.region.text)
            original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
            # Read-only PREVIEW of the translation (kept in sync by
            # _flush_active_row()) - actual editing happens in self.editor
            # below, not in this cell, so it never accepts direct input.
            translation_item = QTableWidgetItem(replacement.translated_text)
            translation_item.setFlags(translation_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, _ORIGINAL_COLUMN, original_item)
            self.table.setItem(row, _TRANSLATION_COLUMN, translation_item)
        self.table.currentCellChanged.connect(self._on_row_changed)
        layout.addWidget(self.table)

        editor_label = QLabel(t("image_correction.editor_label"))
        layout.addWidget(editor_label)

        self.editor = QPlainTextEdit(self)
        self.editor.setFixedHeight(100)
        self.editor.textChanged.connect(self._on_editor_text_changed)
        layout.addWidget(self.editor)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.apply_button = QPushButton(t("image_correction.apply"))
        self.apply_button.clicked.connect(self._apply)
        buttons.addWidget(self.apply_button)
        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        close_box.button(QDialogButtonBox.Close).setText(t("image_correction.close"))
        buttons.addWidget(close_box)
        layout.addLayout(buttons)

        if replacements:
            # Not left to the currentCellChanged signal from
            # setCurrentCell() below - mirrors PdfCorrectionDialog's
            # identical reasoning.
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
            self.editor.setPlainText(self._row_text[row])
        finally:
            self._loading = False

    def _flush_active_row(self) -> None:
        """Write the editor's CURRENT content back into _row_text for the
        row that was active until now - but only if that row is actually
        in _dirty (see its docstring for why an untouched row must keep
        its pristine original string).
        """
        if self._active_row is None or self._active_row not in self._dirty:
            return
        row = self._active_row
        self._row_text[row] = self.editor.toPlainText()
        preview_item = self.table.item(row, _TRANSLATION_COLUMN)
        if preview_item is not None:
            preview_item.setText(self._row_text[row])

    def _on_editor_text_changed(self) -> None:
        if self._loading or self._active_row is None:
            return
        self._dirty.add(self._active_row)

    def _current_edits(self) -> dict[int, str]:
        self._flush_active_row()
        edits: dict[int, str] = {}
        for row in self._dirty:
            edits[row] = self._row_text[row]
        return edits

    def _apply(self) -> None:
        t = self.language.text
        self.apply_button.setEnabled(False)
        self.status_label.setText(t("image_correction.applying"))
        # No OCR/provider/network call is involved (see
        # run_image_correction_job()'s docstring) - fast and local enough
        # to run directly on the UI thread rather than wiring a
        # background QThreadPool worker just for this action.
        try:
            corrected_replacements = build_corrected_replacements(self.replacements, self._current_edits())
            result = run_image_correction_job(
                self.source, self.destination, corrected_replacements,
                inpainting_backend_name=self.inpainting_backend_name,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not silently swallowed
            self.status_label.setText(t("image_correction.failed", error=str(exc)))
            QMessageBox.warning(self, t("image_correction.title"), t("image_correction.failed", error=str(exc)))
            return
        finally:
            self.apply_button.setEnabled(True)

        self.last_result = result
        self.last_corrected_replacements = corrected_replacements
        self.status_label.setText(
            t("image_correction.success", count=result.stats.translated, output=str(result.output_path))
        )
