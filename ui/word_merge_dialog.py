"""Standalone "DOCX-Dateien zusammenführen / einfügen" dialog (01.09.2026,
Michael: "Jetzt noch das ganze für *.docx."). Mirrors ui/merge_dialog.py's
MergeDialog structurally and for the same reasons (see that module's
docstring: a self-contained QDialog rather than another TranslationRequest
`mode`, since merging has no translation cost to analyze/confirm and needs
an ordered, reorderable source list that TranslationRequest's form has no
room for).

Two differences from MergeDialog, both following from
pipeline/word/merge.py's design (see that module's docstring, and Michael's
confirmed choice, 01.09.2026):
1. The source table has only ONE column (file name) - no "Seiten"/pages
   column at all, since DOCX merge is whole-file only (confirmed: "Ja,
   ganze Dateien reichen").
2. The result status line reports segments/files/batches (and any
   soft-fail warnings - see pipeline/word/merge.py's _merge_sequential()
   docstring for what those are) instead of a page count, and shows the
   warnings list underneath when there are any - MergeDialog's PDF path
   has no warnings concept at all (merge_pdfs() hard-fails on every source
   problem, see that function's docstring), so this is new here, not
   carried over.
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
    QListWidget,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.i18n import LanguageManager
from ui.word_merge_job import WordMergeJobResult, validate_merge_word_sources
from ui.word_merge_search_dialog import WordMergeSearchDialog
from ui.workers import WordMergeWorker

_PATH_ROLE = Qt.UserRole  # QTableWidgetItem.setData/.data role for the file column's full Path


class WordMergeDialog(QDialog):
    def __init__(self, language: LanguageManager, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language
        self.settings = settings
        self._worker: WordMergeWorker | None = None
        self._output_path: Path | None = None

        self.intro = QLabel()
        self.intro.setWordWrap(True)

        self.table = QTableWidget(0, 1)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._update_button_states)

        self.add_button = QPushButton()
        self.add_button.clicked.connect(self._add_files)
        self.search_button = QPushButton()
        self.search_button.clicked.connect(self._open_search_dialog)
        self.remove_button = QPushButton()
        self.remove_button.clicked.connect(self._remove_selected)
        self.move_up_button = QPushButton()
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button = QPushButton()
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))

        # 02.09.2026 - see MergeDialog's identical block (this dialog
        # duplicates that one's source table/button row) for the full
        # reasoning.
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
        # Only populated/shown after a run with soft-fail warnings (see
        # module docstring) - MergeDialog has no counterpart to this.
        self.warnings_title_label = QLabel()
        self.warnings_title_label.setVisible(False)
        self.warnings_list = QListWidget()
        self.warnings_list.setVisible(False)
        self.warnings_list.setMaximumHeight(100)

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
        layout.addWidget(self.warnings_title_label)
        layout.addWidget(self.warnings_list)
        layout.addLayout(button_row)
        self.resize(720, 480)

        self.language.changed.connect(self.retranslate)
        self.retranslate()
        self._update_button_states()

    # --- i18n ----------------------------------------------------------
    # merge.*/merge_search.* keys reused wherever the text is format-
    # agnostic (buttons, output-file picker, ...) - see ui/i18n_data.py's
    # comment on the word_merge.* block for exactly which keys are new.

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("word_merge.title"))
        self.intro.setText(t("word_merge.intro"))
        self.table.setHorizontalHeaderLabels([t("merge.column_file")])
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
        self.warnings_title_label.setText(t("word_merge.warnings_title"))
        self.start_button.setText(t("merge.start_button"))
        self.cancel_button.setText(t("merge.cancel_button"))
        self.open_folder_button.setText(t("job.open_folder"))
        self.close_button.setText(t("merge.close_button"))

    # --- source table ----------------------------------------------------

    def _add_files(self) -> None:
        start_dir = str(self.settings.value("word_merge_last_source_dir", "", type=str))
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.language.text("word_merge.error_dialog_choose_files"), start_dir, "DOCX (*.docx)"
        )
        if not paths:
            return
        self.settings.setValue("word_merge_last_source_dir", str(Path(paths[0]).parent))
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

    def _open_search_dialog(self) -> None:
        dialog = WordMergeSearchDialog(self.language, self.settings, self)
        if dialog.exec():
            # No de-duplication against the table's existing rows - same
            # reasoning as _add_files() above and as MergeDialog's own
            # _open_search_dialog(): the SAME file appearing twice is a
            # deliberate, supported case (inserting it at more than one
            # place), so silently dropping a re-selected match would be
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
        path_b = self.table.item(target, 0).data(_PATH_ROLE)
        self._set_row(row, path_b)
        self._set_row(target, path_a)
        self.table.setCurrentCell(target, 0)

    def _set_row(self, row: int, path: Path) -> None:
        item = self.table.item(row, 0)
        item.setText(path.name)
        item.setData(_PATH_ROLE, path)
        item.setToolTip(str(path))

    def _sources(self) -> list[Path]:
        return [self.table.item(row, 0).data(_PATH_ROLE) for row in range(self.table.rowCount())]

    # --- sorting (02.09.2026) -----------------------------------------
    # See MergeDialog's identical block for the full reasoning - only
    # difference here is _set_row()'s signature (no "pages" column).

    def _sort_button_label(self, base_key: str, ascending_next: bool) -> str:
        arrow = "▲" if ascending_next else "▼"
        return f"{self.language.text(base_key)} {arrow}"

    def _update_sort_button_labels(self) -> None:
        self.sort_by_name_button.setText(self._sort_button_label("merge.sort_by_name", self._name_sort_ascending))
        self.sort_by_date_button.setText(self._sort_button_label("merge.sort_by_date", self._date_sort_ascending))

    def _sort_rows(self, key, ascending: bool) -> None:
        paths = [self.table.item(row, 0).data(_PATH_ROLE) for row in range(self.table.rowCount())]
        paths.sort(key=key, reverse=not ascending)
        for row, path in enumerate(paths):
            self._set_row(row, path)
        self.table.clearSelection()

    def _sort_by_name(self) -> None:
        ascending = self._name_sort_ascending
        self._sort_rows(lambda path: path.name.lower(), ascending)
        self._name_sort_ascending = not ascending
        self._update_sort_button_labels()

    @staticmethod
    def _mtime(path: Path) -> float:
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
        start_dir = str(self.settings.value("word_merge_last_output_dir", "", type=str))
        path, _ = QFileDialog.getSaveFileName(
            self, self.language.text("merge.error_dialog_choose_output"), start_dir, "DOCX (*.docx)"
        )
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        self._output_path = Path(path)
        self.output_edit.setText(str(self._output_path))
        self.settings.setValue("word_merge_last_output_dir", str(self._output_path.parent))
        self._update_button_states()

    # --- run ---------------------------------------------------------------

    def _update_button_states(self) -> None:
        errors = validate_merge_word_sources(self._sources(), self._output_path)
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
        self.warnings_title_label.setVisible(False)
        self.warnings_list.setVisible(False)
        self.warnings_list.clear()
        self.progress.setVisible(True)
        self.cancel_button.setVisible(True)
        self.status_label.setText("")
        self._worker = WordMergeWorker(self._sources(), self._output_path)
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

    def _on_finished(self, result: WordMergeJobResult) -> None:
        self._finish_run()
        stats = result.stats
        t = self.language.text
        batch_suffix = t("word_merge.status_batch_suffix", batches=stats.batches) if stats.batches else ""
        warning_suffix = (
            t("word_merge.status_warning_suffix", count=len(stats.warnings)) if stats.warnings else ""
        )
        key = "word_merge.status_cancelled" if stats.cancelled else "word_merge.status_done"
        self.status_label.setText(
            t(key, segments=stats.segments, files=stats.files_processed,
              batch_suffix=batch_suffix, warning_suffix=warning_suffix)
        )
        if stats.warnings:
            self.warnings_title_label.setVisible(True)
            self.warnings_list.setVisible(True)
            for warning in stats.warnings:
                self.warnings_list.addItem(warning)
        self.open_folder_button.setVisible(True)

    def _on_failed(self, message: str) -> None:
        self._finish_run()
        self.status_label.setText(self.language.text("merge.status_failed", error=message))
        QMessageBox.critical(self, self.language.text("merge.failed_title"), message)

    def _open_output_folder(self) -> None:
        if self._output_path is not None and self._output_path.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_path.parent)))
