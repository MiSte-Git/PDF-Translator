""""Ordner durchsuchen" sub-dialog for ui/word_merge_dialog.py (01.09.2026,
Michael: "Jetzt noch das ganze für *.docx."). Mirrors
ui/merge_search_dialog.py::MergeSearchDialog structurally (same source
toggle/QStackedWidget, same shared recursive/query/search/progress/results
section, same Google-Drive sub-panel and keyring-backed credentials flow -
see that module's docstring for the full reasoning behind each of those
choices, all unchanged here) - just swapping in the DOCX search engines
(WordIcoSearchWorker/WordDriveSearchWorker from ui/workers.py, which call
find_docx_files_matching()/find_drive_docx_matching()) and the handful of
i18n keys that differ in wording (word_merge_search.* - see
ui/i18n_data.py's comment on that block for exactly which keys are new vs.
reused from merge_search.*).

Not built as a parametrized "one dialog, pdf-or-docx flag" class: the two
dialogs' Python is close to identical, but the project's established
per-format convention (ui/word_job.py mirrors ui/pdf_job.py,
WordTranslationWorker mirrors PdfTranslationWorker, ...) keeps format-
specific UI classes separate and lets the *shared, pure-logic* engines
underneath do the actual deduplication (find_matching()/find_drive_matching()
in ui/merge_search.py/ui/drive_search.py) - consistent with that choice
rather than introducing a new, first-of-its-kind "if self.kind == 'docx'"
branch style into the dialog layer.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThreadPool
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pipeline import drive_auth
from ui.drive_search import DriveSearchResult, extract_folder_id
from ui.i18n import LanguageManager
from ui.merge_search import IcoSearchResult
from ui.merge_search_dialog import _match_path
from ui.workers import DriveConnectWorker, WordDriveSearchWorker, WordIcoSearchWorker

_SNIPPET_PREVIEW_LENGTH = 120


class WordMergeSearchDialog(QDialog):
    def __init__(self, language: LanguageManager, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language
        self.settings = settings
        self._worker: WordIcoSearchWorker | WordDriveSearchWorker | None = None
        self._connect_worker: DriveConnectWorker | None = None
        self._folder: Path | None = None
        self._drive_folder_id: str | None = None
        self._drive_cache_dir: Path | None = None

        # --- source toggle ---------------------------------------------
        self.source_local_radio = QRadioButton()
        self.source_local_radio.setChecked(True)
        self.source_drive_radio = QRadioButton()
        self.source_local_radio.toggled.connect(self._on_source_changed)
        source_row = QHBoxLayout()
        source_row.addWidget(self.source_local_radio)
        source_row.addWidget(self.source_drive_radio)
        source_row.addStretch(1)

        self.source_stack = QStackedWidget()
        self.source_stack.addWidget(self._build_local_panel())
        self.source_stack.addWidget(self._build_drive_panel())

        # --- shared: recursive/query/search/progress/results -----------
        self.recursive_checkbox = QCheckBox()
        self.recursive_checkbox.setChecked(True)

        self.query_label = QLabel()
        self.query_edit = QLineEdit()

        self.search_button = QPushButton()
        self.search_button.clicked.connect(self._start_search)
        self.search_button.setEnabled(False)
        self.cancel_button = QPushButton()
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.setVisible(False)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.cancel_button)
        search_row.addStretch(1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        self.results = QListWidget()
        self.select_all_button = QPushButton()
        self.select_all_button.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_button = QPushButton()
        self.select_none_button.clicked.connect(lambda: self._set_all_checked(False))
        select_row = QHBoxLayout()
        select_row.addWidget(self.select_all_button)
        select_row.addWidget(self.select_none_button)
        select_row.addStretch(1)

        self.take_selected_button = QPushButton()
        self.take_selected_button.clicked.connect(self.accept)
        self.take_selected_button.setEnabled(False)
        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.reject)
        button_row = QHBoxLayout()
        button_row.addWidget(self.take_selected_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(source_row)
        layout.addWidget(self.source_stack)
        layout.addWidget(self.recursive_checkbox)
        layout.addWidget(self.query_label)
        layout.addWidget(self.query_edit)
        layout.addLayout(search_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addLayout(select_row)
        layout.addWidget(self.results, 1)
        layout.addLayout(button_row)
        self.resize(680, 640)

        self.language.changed.connect(self.retranslate)
        self.retranslate()
        self._refresh_drive_status()
        self._restore_drive_state()

    def _restore_drive_state(self) -> None:
        """02.09.2026 - see MergeSearchDialog's identical method (this
        dialog duplicates the same Drive panel) for the full reasoning."""
        cache_dir = str(self.settings.value("word_merge_search_drive_cache_dir", "", type=str))
        if cache_dir:
            self._drive_cache_dir = Path(cache_dir)
            self.drive_cache_edit.setText(cache_dir)
        folder_link = str(self.settings.value("word_merge_search_drive_folder_link", "", type=str))
        if folder_link:
            self.drive_folder_edit.setText(folder_link)
        self._update_search_enabled()

    def done(self, result: int) -> None:
        # See MergeSearchDialog.done() - identical reasoning.
        text = self.drive_folder_edit.text().strip()
        if text:
            self.settings.setValue("word_merge_search_drive_folder_link", text)
        super().done(result)

    # --- panel construction ------------------------------------------------

    def _build_local_panel(self) -> QWidget:
        panel = QWidget()
        self.folder_label = QLabel()
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.choose_folder_button = QPushButton()
        self.choose_folder_button.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(self.choose_folder_button)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.folder_label)
        layout.addLayout(folder_row)
        return panel

    def _build_drive_panel(self) -> QWidget:
        panel = QWidget()

        self.drive_folder_label = QLabel()
        self.drive_folder_edit = QLineEdit()
        self.drive_folder_edit.textChanged.connect(self._on_drive_folder_text_changed)
        self.drive_resolve_button = QPushButton()
        self.drive_resolve_button.clicked.connect(self._resolve_drive_folder)
        drive_folder_row = QHBoxLayout()
        drive_folder_row.addWidget(self.drive_folder_edit, 1)
        drive_folder_row.addWidget(self.drive_resolve_button)
        self.drive_folder_status_label = QLabel()
        self.drive_folder_status_label.setWordWrap(True)
        # 02.09.2026 (Michael): Fehlermeldungen (z. B. HttpError-Details)
        # sollen sich markieren und kopieren lassen - QLabel ist dafür
        # standardmäßig NICHT selektierbar.
        self.drive_folder_status_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )

        self.drive_cache_label = QLabel()
        self.drive_cache_edit = QLineEdit()
        self.drive_cache_edit.setReadOnly(True)
        self.drive_choose_cache_button = QPushButton()
        self.drive_choose_cache_button.clicked.connect(self._choose_drive_cache)
        drive_cache_row = QHBoxLayout()
        drive_cache_row.addWidget(self.drive_cache_edit, 1)
        drive_cache_row.addWidget(self.drive_choose_cache_button)

        self.drive_credentials_label = QLabel()
        # 02.09.2026 - see MergeSearchDialog's identical comment above its
        # own drive_load_from_file_button (this dialog duplicates the same
        # Drive panel).
        self.drive_load_from_file_button = QPushButton()
        self.drive_load_from_file_button.clicked.connect(self._load_drive_credentials_from_file)
        load_from_file_row = QHBoxLayout()
        load_from_file_row.addWidget(self.drive_load_from_file_button)
        load_from_file_row.addStretch(1)
        self.drive_client_id_edit = QLineEdit()
        self.drive_client_secret_edit = QLineEdit()
        self.drive_client_secret_edit.setEchoMode(QLineEdit.Password)
        self.drive_project_id_edit = QLineEdit()
        self.drive_save_credentials_button = QPushButton()
        self.drive_save_credentials_button.clicked.connect(self._save_drive_credentials)
        credentials_row = QHBoxLayout()
        credentials_row.addWidget(self.drive_client_id_edit)
        credentials_row.addWidget(self.drive_client_secret_edit)
        credentials_row.addWidget(self.drive_project_id_edit)
        credentials_row.addWidget(self.drive_save_credentials_button)

        self.drive_connection_status_label = QLabel()
        self.drive_connection_status_label.setWordWrap(True)
        self.drive_connection_status_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.drive_connect_button = QPushButton()
        self.drive_connect_button.clicked.connect(self._connect_drive)
        self.drive_disconnect_button = QPushButton()
        self.drive_disconnect_button.clicked.connect(self._disconnect_drive)
        connect_row = QHBoxLayout()
        connect_row.addWidget(self.drive_connect_button)
        connect_row.addWidget(self.drive_disconnect_button)
        connect_row.addStretch(1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.drive_folder_label)
        layout.addLayout(drive_folder_row)
        layout.addWidget(self.drive_folder_status_label)
        layout.addWidget(self.drive_cache_label)
        layout.addLayout(drive_cache_row)
        layout.addWidget(self.drive_credentials_label)
        layout.addLayout(load_from_file_row)
        layout.addLayout(credentials_row)
        layout.addWidget(self.drive_connection_status_label)
        layout.addLayout(connect_row)
        return panel

    # --- i18n ------------------------------------------------------------
    # Every key below is either word_merge_search.* (wording genuinely
    # differs from the PDF dialog - see ui/i18n_data.py) or the shared,
    # format-agnostic merge_search.* key reused as-is (buttons, folder
    # picker, Drive panel - none of that text mentions PDF or DOCX).

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("word_merge_search.title"))
        self.source_local_radio.setText(t("merge_search.source_local"))
        self.source_drive_radio.setText(t("merge_search.source_drive"))
        self.folder_label.setText(t("merge_search.folder_label"))
        self.folder_edit.setPlaceholderText(t("merge_search.folder_placeholder"))
        self.choose_folder_button.setText(t("merge_search.choose_folder"))
        self.recursive_checkbox.setText(t("merge_search.recursive_checkbox"))
        self.query_label.setText(t("word_merge_search.query_label"))
        self.query_edit.setPlaceholderText(t("word_merge_search.query_placeholder"))
        self.search_button.setText(t("merge_search.search_button"))
        self.cancel_button.setText(t("merge_search.cancel_button"))
        self.select_all_button.setText(t("merge_search.select_all"))
        self.select_none_button.setText(t("merge_search.select_none"))
        self.take_selected_button.setText(t("merge_search.take_selected"))
        self.close_button.setText(t("merge_search.close_button"))

        self.drive_folder_label.setText(t("merge_search.drive_folder_label"))
        self.drive_folder_edit.setPlaceholderText(t("merge_search.drive_folder_placeholder"))
        self.drive_resolve_button.setText(t("merge_search.drive_resolve_button"))
        if self._drive_folder_id is None:
            self.drive_folder_status_label.setText(t("merge_search.drive_folder_unresolved"))
        self.drive_cache_label.setText(t("merge_search.drive_cache_label"))
        self.drive_choose_cache_button.setText(t("merge_search.drive_choose_cache"))
        self.drive_credentials_label.setText(t("merge_search.drive_credentials_label"))
        self.drive_load_from_file_button.setText(t("merge_search.drive_load_from_file"))
        self.drive_client_id_edit.setPlaceholderText(t("merge_search.drive_client_id_placeholder"))
        self.drive_client_secret_edit.setPlaceholderText(t("merge_search.drive_client_secret_placeholder"))
        self.drive_project_id_edit.setPlaceholderText(t("merge_search.drive_project_id_placeholder"))
        self.drive_save_credentials_button.setText(t("merge_search.drive_save_credentials"))
        self.drive_connect_button.setText(t("merge_search.drive_connect_button"))
        self.drive_disconnect_button.setText(t("merge_search.drive_disconnect_button"))
        self._refresh_drive_status()

    # --- source toggle -------------------------------------------------

    def _on_source_changed(self, local_checked: bool) -> None:
        self.source_stack.setCurrentIndex(0 if local_checked else 1)
        self._update_search_enabled()

    def _is_drive_source(self) -> bool:
        return self.source_drive_radio.isChecked()

    # --- local folder/query ------------------------------------------------

    def _choose_folder(self) -> None:
        start_dir = str(self.settings.value("word_merge_search_last_folder", "", type=str))
        chosen = QFileDialog.getExistingDirectory(
            self, self.language.text("merge_search.choose_folder_dialog_title"), start_dir
        )
        if not chosen:
            return
        self._folder = Path(chosen)
        self.folder_edit.setText(chosen)
        self.settings.setValue("word_merge_search_last_folder", chosen)
        self._update_search_enabled()

    # --- drive folder/cache/credentials/connection --------------------
    # Identical to MergeSearchDialog's - Drive auth/keyring state is shared
    # process-wide (pipeline/drive_auth.py), not per document format, so a
    # credential saved/connected from either dialog is immediately usable
    # in the other too.

    def _on_drive_folder_text_changed(self, _text: str) -> None:
        self._drive_folder_id = None
        self.drive_folder_status_label.setText(self.language.text("merge_search.drive_folder_unresolved"))
        self._update_search_enabled()

    def _resolve_drive_folder(self) -> None:
        try:
            folder_id = extract_folder_id(self.drive_folder_edit.text())
            client = drive_auth.DriveClient(drive_auth.build_service())
            entry = client.resolve_folder(folder_id)
        except Exception as exc:
            self._drive_folder_id = None
            self.drive_folder_status_label.setText(
                self.language.text("merge_search.drive_folder_resolve_failed", error=str(exc))
            )
            self._update_search_enabled()
            return
        self._drive_folder_id = entry.id
        self.drive_folder_status_label.setText(
            self.language.text("merge_search.drive_folder_resolved", name=entry.name)
        )
        self._update_search_enabled()

    def _choose_drive_cache(self) -> None:
        start_dir = str(self.settings.value("word_merge_search_drive_cache_dir", "", type=str))
        chosen = QFileDialog.getExistingDirectory(
            self, self.language.text("merge_search.drive_choose_cache_dialog_title"), start_dir
        )
        if not chosen:
            return
        self._drive_cache_dir = Path(chosen)
        self.drive_cache_edit.setText(chosen)
        self.settings.setValue("word_merge_search_drive_cache_dir", chosen)
        self._update_search_enabled()

    def _load_drive_credentials_from_file(self) -> None:
        """See MergeSearchDialog's identical method - same behaviour,
        shared Drive auth state (pipeline/drive_auth.py)."""
        chosen, _filter = QFileDialog.getOpenFileName(
            self,
            self.language.text("merge_search.drive_load_from_file_dialog_title"),
            "",
            "JSON (*.json)",
        )
        if not chosen:
            return
        try:
            client_id, client_secret, project_id = drive_auth.parse_client_secrets_file(Path(chosen))
        except Exception as exc:
            QMessageBox.warning(
                self, self.windowTitle(), self.language.text("merge_search.drive_load_from_file_failed", error=str(exc))
            )
            return
        self.drive_client_id_edit.setText(client_id)
        self.drive_client_secret_edit.setText(client_secret)
        self.drive_project_id_edit.setText(project_id)

    def _save_drive_credentials(self) -> None:
        client_id = self.drive_client_id_edit.text().strip()
        client_secret = self.drive_client_secret_edit.text().strip()
        project_id = self.drive_project_id_edit.text().strip()
        if not client_id or not client_secret or not project_id:
            QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.drive_not_configured"))
            return
        try:
            drive_auth.save_client_credentials(client_id, client_secret, project_id)
        except Exception as exc:
            # 02.09.2026 - see MergeSearchDialog._save_drive_credentials()'s
            # identical comment (this dialog duplicates that one's Drive
            # panel code): an unguarded save() call here used to fail
            # silently on a keyring error, which is exactly what got
            # reported as "credentials don't actually get saved". Fields
            # are deliberately left filled in so the user can retry without
            # retyping.
            QMessageBox.critical(
                self, self.windowTitle(), self.language.text("merge_search.drive_save_failed", error=str(exc))
            )
            return
        self.drive_client_id_edit.clear()
        self.drive_client_secret_edit.clear()
        self.drive_project_id_edit.clear()
        self._refresh_drive_status()
        QMessageBox.information(self, self.windowTitle(), self.language.text("merge_search.drive_credentials_saved"))

    def _connect_drive(self) -> None:
        self.drive_connect_button.setEnabled(False)
        self.drive_connection_status_label.setText(self.language.text("merge_search.drive_connecting"))
        self._connect_worker = DriveConnectWorker()
        self._connect_worker.signals.succeeded.connect(self._on_drive_connected)
        self._connect_worker.signals.failed.connect(self._on_drive_connect_failed)
        QThreadPool.globalInstance().start(self._connect_worker)

    def _on_drive_connected(self) -> None:
        self._connect_worker = None
        self._refresh_drive_status()

    def _on_drive_connect_failed(self, message: str) -> None:
        self._connect_worker = None
        self._refresh_drive_status()
        self.drive_connection_status_label.setText(
            self.language.text("merge_search.drive_connect_failed", error=message)
        )

    def _disconnect_drive(self) -> None:
        drive_auth.disconnect()
        self._refresh_drive_status()

    def _refresh_drive_status(self) -> None:
        t = self.language.text
        configured = drive_auth.is_configured()
        connected = drive_auth.is_connected()
        if connected:
            self.drive_connection_status_label.setText(t("merge_search.drive_connected", account=""))
        elif configured:
            self.drive_connection_status_label.setText(t("merge_search.drive_configured_not_connected"))
        else:
            self.drive_connection_status_label.setText(t("merge_search.drive_not_configured"))
        self.drive_connect_button.setEnabled(configured and self._connect_worker is None)
        self.drive_disconnect_button.setEnabled(connected)
        self._update_search_enabled()

    # --- search --------------------------------------------------------

    def _update_search_enabled(self) -> None:
        if self._worker is not None:
            return
        if self._is_drive_source():
            enabled = self._drive_folder_id is not None and self._drive_cache_dir is not None and drive_auth.is_connected()
        else:
            enabled = self._folder is not None
        self.search_button.setEnabled(enabled)

    def _start_search(self) -> None:
        self.results.clear()
        self.take_selected_button.setEnabled(False)
        self.status_label.setText("")

        if self._is_drive_source():
            if self._drive_folder_id is None:
                QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.drive_error_missing_folder"))
                return
            if self._drive_cache_dir is None:
                QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.drive_error_missing_cache"))
                return
            try:
                client = drive_auth.DriveClient(drive_auth.build_service())
            except drive_auth.DriveAuthError as exc:
                QMessageBox.critical(self, self.language.text("merge_search.failed_title"), str(exc))
                return
            self._worker = WordDriveSearchWorker(
                client, self._drive_folder_id, self.query_edit.text(), self.recursive_checkbox.isChecked(), self._drive_cache_dir
            )
        else:
            if self._folder is None:
                QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.error_missing_folder"))
                return
            self._worker = WordIcoSearchWorker(self._folder, self.query_edit.text(), self.recursive_checkbox.isChecked())

        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.cancel_button.setVisible(True)
        self.search_button.setEnabled(False)
        self.source_local_radio.setEnabled(False)
        self.source_drive_radio.setEnabled(False)
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.failed.connect(self._on_failed)
        QThreadPool.globalInstance().start(self._worker)

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()

    def _on_progress(self, done: int, total: int, current: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.status_label.setText(self.language.text("merge_search.status_running", current=current, done=done, total=total))

    def _finish_run(self) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self.cancel_button.setVisible(False)
        self.source_local_radio.setEnabled(True)
        self.source_drive_radio.setEnabled(True)
        self._update_search_enabled()

    def _on_finished(self, result: IcoSearchResult | DriveSearchResult) -> None:
        self._finish_run()
        for match in result.matches:
            path = _match_path(match)
            preview = match.snippet.replace("\n", " ").strip()
            if len(preview) > _SNIPPET_PREVIEW_LENGTH:
                preview = preview[:_SNIPPET_PREVIEW_LENGTH].rstrip() + "…"
            label = path.name if not preview else f"{path.name} — {preview}"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, path)
            item.setToolTip(str(path) + ("\n\n" + match.snippet if match.snippet else ""))
            self.results.addItem(item)
        self.take_selected_button.setEnabled(bool(result.matches))

        key = "word_merge_search.status_cancelled" if result.cancelled else (
            "word_merge_search.status_done_with_errors" if result.errors else "word_merge_search.status_done"
        )
        self.status_label.setText(
            self.language.text(key, matches=len(result.matches), scanned=result.scanned, errors=len(result.errors))
        )

    def _on_failed(self, message: str) -> None:
        self._finish_run()
        self.status_label.setText(self.language.text("merge_search.status_failed", error=message))
        QMessageBox.critical(self, self.language.text("merge_search.failed_title"), message)

    # --- results list ------------------------------------------------------

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.results.count()):
            self.results.item(row).setCheckState(state)

    def selected_paths(self) -> list[Path]:
        return [
            self.results.item(row).data(Qt.UserRole)
            for row in range(self.results.count())
            if self.results.item(row).checkState() == Qt.Checked
        ]
