""""Ordner durchsuchen" sub-dialog for ui/merge_dialog.py (01.09.2026,
erweitert um Google Drive am selben Tag).

Michael: "Wie sollten wir es machen wenn ich einen Ordner mit 1000 oder
mehr PDFs habe aber nur bestimmte von ihnen zusammenführen möchte." A
separate modal dialog (opened from a button in MergeDialog, mirrors how
MergeDialog itself is opened from MainWindow) rather than folding folder-
scan controls directly into MergeDialog's own layout: the scan produces a
whole extra state machine (folder/recursive/query -> background scan with
its own progress/cancel -> a reviewable match list with checkboxes) that
has nothing to do with MergeDialog's own source table once the user is
done reviewing - keeping it separate keeps both dialogs' state simple.
Confirmed with Michael (01.09.2026): filter text matches ONLY the ICO
metadata region (see pipeline/pdf/pymupdf_engine.py's
extract_ico_header_text()), and recursive-subfolder scanning is a
UI-visible checkbox, not a fixed choice - see ui/merge_search.py's own
module docstring for both.

On accept() (the "Ausgewählte übernehmen" button), the caller reads
selected_paths() for the checked matches - MergeDialog appends each as a
whole-file MergeSourceSpec (pages="") into its own source table. This is
unaffected by the Drive addition below: by the time a Drive match appears
in the results list it has ALREADY been downloaded to a real local file
(see ui/drive_search.py's module docstring for why), so selected_paths()
returns plain local Path objects for both sources without the caller ever
needing to know which source a given match came from.

Google-Drive-Ordnersuche (01.09.2026): Michael, direkt im Anschluss an das
lokale Feature: "Können wir eine Google Drive Ordner durchsuchen?" Auf
Rückfrage bestätigt: fest als App-Feature (nicht nur einmalig hier im
Chat), im SELBEN Dialog über einen Umschalter statt einem eigenen Fenster
(unten: source_local_radio/source_drive_radio + ein QStackedWidget mit den
quellenspezifischen Feldern; Suchtext, Rekursiv-Checkbox, Fortschritt,
Ergebnisliste und die Übernehmen/Schließen-Knöpfe bleiben gemeinsam, da ihr
Verhalten quellenunabhängig identisch ist), und heruntergeladene Treffer
bleiben in einem vom Nutzer gewählten Cache-Ordner liegen statt gelöscht zu
werden (siehe ui/drive_search.py).

Der Drive-Bereich trägt zusätzlich seine eigene, sehr kleine
Zugangsdaten-UI (Client-ID/Client-Secret einfügen + "Mit Google
verbinden") statt die bestehende SettingsDialog-Zugangsdaten-Maske
(ui/app.py) mitzubenutzen: die dort verwaltete PROVIDER_CREDENTIALS-Liste
sind ausschließlich Übersetzungs-Provider und ihr `provider`-Auswahlfeld
ist an TranslationRequest.provider gekoppelt - Google Drive ist kein
Übersetzungs-Provider und hätte dort nur verwirrt. Die eigentliche
Speicherung nutzt trotzdem denselben Keyring-Mechanismus
(pipeline.drive_auth.save_client_credentials() -> pipeline.credentials,
siehe dort).
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
from ui.workers import DriveConnectWorker, DriveSearchWorker, IcoSearchWorker

_SNIPPET_PREVIEW_LENGTH = 120


def _match_path(match) -> Path:
    """IcoSearchMatch calls its field `path`, DriveSearchMatch calls it
    `local_path` (see ui/merge_search.py vs. ui/drive_search.py) - both
    dataclasses were kept source-specific/self-documenting rather than
    forced into one shared shape, so the shared result-rendering code
    below normalizes through this one-line accessor instead.
    """
    return getattr(match, "local_path", None) or match.path


class MergeSearchDialog(QDialog):
    def __init__(self, language: LanguageManager, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language
        self.settings = settings
        self._worker: IcoSearchWorker | DriveSearchWorker | None = None
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

        self.drive_cache_label = QLabel()
        self.drive_cache_edit = QLineEdit()
        self.drive_cache_edit.setReadOnly(True)
        self.drive_choose_cache_button = QPushButton()
        self.drive_choose_cache_button.clicked.connect(self._choose_drive_cache)
        drive_cache_row = QHBoxLayout()
        drive_cache_row.addWidget(self.drive_cache_edit, 1)
        drive_cache_row.addWidget(self.drive_choose_cache_button)

        self.drive_credentials_label = QLabel()
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
        layout.addLayout(credentials_row)
        layout.addWidget(self.drive_connection_status_label)
        layout.addLayout(connect_row)
        return panel

    # --- i18n ------------------------------------------------------------

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("merge_search.title"))
        self.source_local_radio.setText(t("merge_search.source_local"))
        self.source_drive_radio.setText(t("merge_search.source_drive"))
        self.folder_label.setText(t("merge_search.folder_label"))
        self.folder_edit.setPlaceholderText(t("merge_search.folder_placeholder"))
        self.choose_folder_button.setText(t("merge_search.choose_folder"))
        self.recursive_checkbox.setText(t("merge_search.recursive_checkbox"))
        self.query_label.setText(t("merge_search.query_label"))
        self.query_edit.setPlaceholderText(t("merge_search.query_placeholder"))
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
        start_dir = str(self.settings.value("merge_search_last_folder", "", type=str))
        chosen = QFileDialog.getExistingDirectory(
            self, self.language.text("merge_search.choose_folder_dialog_title"), start_dir
        )
        if not chosen:
            return
        self._folder = Path(chosen)
        self.folder_edit.setText(chosen)
        self.settings.setValue("merge_search_last_folder", chosen)
        self._update_search_enabled()

    # --- drive folder/cache/credentials/connection --------------------

    def _on_drive_folder_text_changed(self, _text: str) -> None:
        # Any edit invalidates a previous resolve - stops the user from
        # searching a folder that no longer matches what's in the field.
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
        start_dir = str(self.settings.value("merge_search_drive_cache_dir", "", type=str))
        chosen = QFileDialog.getExistingDirectory(
            self, self.language.text("merge_search.drive_choose_cache_dialog_title"), start_dir
        )
        if not chosen:
            return
        self._drive_cache_dir = Path(chosen)
        self.drive_cache_edit.setText(chosen)
        self.settings.setValue("merge_search_drive_cache_dir", chosen)
        self._update_search_enabled()

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
            # 02.09.2026 (Michael: "Es scheint auch so das die Anmeldedaten
            # nicht wirklich gespeichert werden.") - this call used to be
            # unguarded, unlike SettingsDialog._save_key()'s identical
            # save-then-report pattern for the translation-provider API
            # keys. Without a try/except, a keyring failure (no OS Secret
            # Service running - the single most common real-world cause,
            # see pipeline/credentials.py::set_api_key()) raised silently
            # out of this Qt slot: no error dialog, no success dialog,
            # nothing visibly happened, which is exactly what got reported.
            # The fields are deliberately NOT cleared here (unlike the
            # success path below) so the user doesn't have to retype
            # everything after a failed save.
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
        """Keyring-only status check (no network call) - see this module's
        docstring: a Drive folder resolve or search is the deliberate first
        point a token refresh is attempted, not just opening this dialog.
        """
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
            return  # a scan is already running - _finish_run() re-enables afterwards
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
            self._worker = DriveSearchWorker(
                client, self._drive_folder_id, self.query_edit.text(), self.recursive_checkbox.isChecked(), self._drive_cache_dir
            )
        else:
            if self._folder is None:
                QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.error_missing_folder"))
                return
            self._worker = IcoSearchWorker(self._folder, self.query_edit.text(), self.recursive_checkbox.isChecked())

        self.progress.setRange(0, 0)  # indeterminate until the first progress signal reports a real total
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

        key = "merge_search.status_cancelled" if result.cancelled else (
            "merge_search.status_done_with_errors" if result.errors else "merge_search.status_done"
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
