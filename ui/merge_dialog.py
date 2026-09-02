"""Standalone "PDFs zusammenführen / einfügen" dialog (01.09.2026, Backlog.md
26.08.2026).

A separate QDialog opened from a plain button in MainWindow's own form
(see ui/app.py's `self.merge_button`) rather than a new `self.mode`/
MODE_KEYS entry, even though the backlog entry that first floated this
feature considered the mode-combobox route. Reasons, both from real
inspection of ui/app.py before writing this: (1) MainWindow's mode combo,
_mode_changed(), _analyze()/_start()/_start_blocked_reason() and every
worker in ui/workers.py are built entirely around ONE
TranslationRequest-shaped flow (a single provider, a single cost estimate,
a single Start button gated on "analysis reviewed") - merge needs an
ordered, reorderable, N-item source list with a per-item page-range field,
which that form has no room or mechanism for without a much larger,
riskier rewrite of an already working, well-tested window; (2) merge has
no translation cost to analyze/confirm at all (see ui/merge_job.py's
module docstring), so half of that flow would need to be suppressed for
this "mode" anyway. A self-contained dialog needs none of that and keeps
every existing mode's code path completely untouched.

Mirrors SettingsDialog's shape (ui/app.py) for the Qt basics - a QFormLayout-
free but otherwise plain QDialog, LanguageManager wired via retranslate() -
and ui/pdf_job.py/ui/workers.py's Start/progress/cancel/result convention
for the actual run (QThreadPool + MergeWorker, see ui/workers.py).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pipeline.pdf.pymupdf_engine import MergeSourceSpec
from ui.i18n import LanguageManager
from ui.merge_job import MergeJobResult, validate_merge_sources
from ui.merge_search_dialog import MergeSearchDialog
from ui.natural_sort import natural_sort_key
from ui.workers import MergeWorker

_PATH_ROLE = Qt.UserRole  # QTableWidgetItem.setData/.data role for the file column's full Path


class MergeDialog(QDialog):
    def __init__(self, language: LanguageManager, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language
        self.settings = settings
        self._worker: MergeWorker | None = None
        self._output_path: Path | None = None

        self.intro = QLabel()
        self.intro.setWordWrap(True)

        self.table = QTableWidget(0, 2)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._update_button_states)

        self.add_button = QPushButton()
        self.add_button.clicked.connect(self._add_files)
        # 01.09.2026, Michael: "Wie sollten wir es machen wenn ich einen
        # Ordner mit 1000 oder mehr PDFs habe aber nur bestimmte von ihnen
        # zusammenführen möchte." - opens ui/merge_search_dialog.py's
        # MergeSearchDialog, a separate reviewable-results dialog (see its
        # own module docstring for why it's not just more controls bolted
        # onto this table).
        self.search_button = QPushButton()
        self.search_button.clicked.connect(self._open_search_dialog)
        self.remove_button = QPushButton()
        self.remove_button.clicked.connect(self._remove_selected)
        self.move_up_button = QPushButton()
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button = QPushButton()
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))

        # 02.09.2026 (Michael: "Was mir sonst noch fehlt ist eine
        # Sortierung wenn wir die PDFs zusammenführen wollen. Per
        # Dateiname, per Datum, auf und absteigend.") - two buttons next
        # to move_up/move_down rather than a dropdown or clickable column
        # header (confirmed via AskUserQuestion, 02.09.2026): each button
        # sorts the WHOLE table by its own key and toggles its own next
        # direction on every click (the button's label always shows which
        # direction the NEXT click will apply, via _sort_button_label()) -
        # independent of the other button and of any manual move_up/
        # move_down reordering done in between, so there's no separate
        # "currently sorted by X" state to keep in sync.
        self._name_sort_ascending = True
        self._date_sort_ascending = True
        self.sort_by_name_button = QPushButton()
        self.sort_by_name_button.clicked.connect(self._sort_by_name)
        self.sort_by_date_button = QPushButton()
        self.sort_by_date_button.clicked.connect(self._sort_by_date)

        row_buttons = QHBoxLayout()
        for button in (
            self.add_button, self.search_button, self.remove_button,
            self.move_up_button, self.move_down_button,
            self.sort_by_name_button, self.sort_by_date_button,
        ):
            row_buttons.addWidget(button)
        row_buttons.addStretch(1)

        self.output_label = QLabel()
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.choose_output_button = QPushButton()
        self.choose_output_button.clicked.connect(self._choose_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.choose_output_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        self.start_button = QPushButton()
        self.start_button.clicked.connect(self._start)
        self.cancel_button = QPushButton()
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setVisible(False)
        self.open_folder_button = QPushButton()
        self.open_folder_button.clicked.connect(self._open_output_folder)
        self.open_folder_button.setVisible(False)
        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.open_folder_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.intro)
        layout.addWidget(self.table, 1)
        layout.addLayout(row_buttons)
        layout.addWidget(self.output_label)
        layout.addLayout(output_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addLayout(button_row)
        self.resize(720, 480)

        self.language.changed.connect(self.retranslate)
        self.retranslate()
        self._update_button_states()

    # --- i18n ----------------------------------------------------------

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("merge.title"))
        self.intro.setText(t("merge.intro"))
        self.table.setHorizontalHeaderLabels([t("merge.column_file"), t("merge.column_pages")])
        for row in range(self.table.rowCount()):
            self.table.cellWidget(row, 1).setPlaceholderText(t("merge.pages_placeholder"))
            self.table.cellWidget(row, 1).setToolTip(t("merge.pages_tooltip"))
        self.add_button.setText(t("merge.add_files"))
        self.search_button.setText(t("merge_search.button"))
        self.remove_button.setText(t("merge.remove_selected"))
        self.move_up_button.setText(t("merge.move_up"))
        self.move_down_button.setText(t("merge.move_down"))
        self.sort_by_date_button.setToolTip(t("merge.sort_by_date_tooltip"))
        self._update_sort_button_labels()
        self.output_label.setText(t("merge.output_file_label"))
        self.output_edit.setPlaceholderText(t("merge.output_placeholder"))
        self.choose_output_button.setText(t("merge.choose_output_file"))
        self.start_button.setText(t("merge.start_button"))
        self.cancel_button.setText(t("merge.cancel_button"))
        self.open_folder_button.setText(t("job.open_folder"))
        self.close_button.setText(t("merge.close_button"))

    # --- source table ----------------------------------------------------

    def _add_files(self) -> None:
        start_dir = str(self.settings.value("merge_last_source_dir", "", type=str))
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.language.text("merge.error_dialog_choose_files"), start_dir, "PDF (*.pdf)"
        )
        if not paths:
            return
        self.settings.setValue("merge_last_source_dir", str(Path(paths[0]).parent))
        for raw_path in paths:
            self._append_row(Path(raw_path))
        self._update_button_states()

    def _append_row(self, path: Path) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        file_item = QTableWidgetItem(path.name)
        file_item.setData(_PATH_ROLE, path)
        file_item.setToolTip(str(path))
        file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, file_item)
        pages_edit = QLineEdit()
        pages_edit.setPlaceholderText(self.language.text("merge.pages_placeholder"))
        pages_edit.setToolTip(self.language.text("merge.pages_tooltip"))
        pages_edit.textChanged.connect(self._update_button_states)
        self.table.setCellWidget(row, 1, pages_edit)

    def _open_search_dialog(self) -> None:
        dialog = MergeSearchDialog(self.language, self.settings, self)
        if dialog.exec():
            # No de-duplication against the table's existing rows - same
            # reasoning as _add_files() above (which never de-duplicates
            # either): the SAME file appearing twice is a deliberate,
            # supported case (see the "Zwischeneinfügen" module comment),
            # so silently dropping a re-selected match here would be
            # surprising rather than helpful.
            for path in dialog.selected_paths():
                self._append_row(path)
            self._update_button_states()

    def _remove_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
        self._update_button_states()

    def _move_selected(self, delta: int) -> None:
        row = self.table.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < self.table.rowCount()):
            return
        path_a = self.table.item(row, 0).data(_PATH_ROLE)
        pages_a = self.table.cellWidget(row, 1).text()
        path_b = self.table.item(target, 0).data(_PATH_ROLE)
        pages_b = self.table.cellWidget(target, 1).text()
        self._set_row(row, path_b, pages_b)
        self._set_row(target, path_a, pages_a)
        self.table.setCurrentCell(target, 0)

    def _set_row(self, row: int, path: Path, pages: str) -> None:
        item = self.table.item(row, 0)
        item.setText(path.name)
        item.setData(_PATH_ROLE, path)
        item.setToolTip(str(path))
        self.table.cellWidget(row, 1).setText(pages)

    def _sources(self) -> list[MergeSourceSpec]:
        sources: list[MergeSourceSpec] = []
        for row in range(self.table.rowCount()):
            path = self.table.item(row, 0).data(_PATH_ROLE)
            pages = self.table.cellWidget(row, 1).text().strip()
            sources.append(MergeSourceSpec(path, pages))
        return sources

    # --- sorting (02.09.2026) -----------------------------------------

    def _sort_button_label(self, base_key: str, ascending_next: bool) -> str:
        # Arrow shows the direction the NEXT click will apply - see the
        # constructor comment above sort_by_name_button/sort_by_date_button.
        arrow = "▲" if ascending_next else "▼"
        return f"{self.language.text(base_key)} {arrow}"

    def _update_sort_button_labels(self) -> None:
        self.sort_by_name_button.setText(self._sort_button_label("merge.sort_by_name", self._name_sort_ascending))
        self.sort_by_date_button.setText(self._sort_button_label("merge.sort_by_date", self._date_sort_ascending))

    def _sort_rows(self, key, ascending: bool) -> None:
        rows = [
            (self.table.item(row, 0).data(_PATH_ROLE), self.table.cellWidget(row, 1).text())
            for row in range(self.table.rowCount())
        ]
        rows.sort(key=lambda entry: key(entry[0]), reverse=not ascending)
        for row, (path, pages) in enumerate(rows):
            self._set_row(row, path, pages)
        self.table.clearSelection()

    def _sort_by_name(self) -> None:
        # 02.09.2026 (Michael: ICO-numbered filenames need numeric-aware
        # sorting, not a plain string sort) - see ui/natural_sort.py.
        ascending = self._name_sort_ascending
        self._sort_rows(lambda path: natural_sort_key(path.name), ascending)
        self._name_sort_ascending = not ascending
        self._update_sort_button_labels()

    @staticmethod
    def _mtime(path: Path) -> float:
        # A file removed from disk between being added to the table and
        # clicking "sortieren" is an edge case, not an error this button
        # should crash on - sorts as if it were the oldest file.
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    def _sort_by_date(self) -> None:
        ascending = self._date_sort_ascending
        self._sort_rows(self._mtime, ascending)
        self._date_sort_ascending = not ascending
        self._update_sort_button_labels()

    # --- output file -------------------------------------------------------

    def _choose_output(self) -> None:
        start_dir = str(self.settings.value("merge_last_output_dir", "", type=str))
        path, _ = QFileDialog.getSaveFileName(
            self, self.language.text("merge.error_dialog_choose_output"), start_dir, "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self._output_path = Path(path)
        self.output_edit.setText(str(self._output_path))
        self.settings.setValue("merge_last_output_dir", str(self._output_path.parent))
        self._update_button_states()

    # --- run ---------------------------------------------------------------

    def _update_button_states(self) -> None:
        errors = validate_merge_sources(self._sources(), self._output_path)
        running = self._worker is not None
        self.start_button.setEnabled(not errors and not running)
        self.start_button.setToolTip("\n".join(errors))
        self.remove_button.setEnabled(not running and self.table.currentRow() >= 0)
        self.move_up_button.setEnabled(not running and self.table.currentRow() > 0)
        self.move_down_button.setEnabled(
            not running and 0 <= self.table.currentRow() < self.table.rowCount() - 1
        )
        self.sort_by_name_button.setEnabled(not running and self.table.rowCount() > 1)
        self.sort_by_date_button.setEnabled(not running and self.table.rowCount() > 1)
        self.add_button.setEnabled(not running)
        self.choose_output_button.setEnabled(not running)
        self.table.setEnabled(not running)

    def _start(self) -> None:
        assert self._output_path is not None
        self.open_folder_button.setVisible(False)
        self.progress.setVisible(True)
        self.cancel_button.setVisible(True)
        self.status_label.setText("")
        self._worker = MergeWorker(self._sources(), self._output_path)
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.failed.connect(self._on_failed)
        self._update_button_states()
        QThreadPool.globalInstance().start(self._worker)

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()

    def _on_progress(self, message: str) -> None:
        self.status_label.setText(self.language.text("merge.status_running", message=message))

    def _finish_run(self) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self.cancel_button.setVisible(False)
        self._update_button_states()

    def _on_finished(self, result: MergeJobResult) -> None:
        self._finish_run()
        key = "merge.status_cancelled" if result.stats.cancelled else "merge.status_done"
        self.status_label.setText(
            self.language.text(key, pages=result.stats.pages_written, files=result.stats.files_processed)
        )
        self.open_folder_button.setVisible(True)

    def _on_failed(self, message: str) -> None:
        self._finish_run()
        self.status_label.setText(self.language.text("merge.status_failed", error=message))
        QMessageBox.critical(self, self.language.text("merge.failed_title"), message)

    def _open_output_folder(self) -> None:
        if self._output_path is not None and self._output_path.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path.parent)))
