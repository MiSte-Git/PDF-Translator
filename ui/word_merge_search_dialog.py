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
    QDateEdit,
    QDialog,
    QFileDialog,
    QGroupBox,
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
from pipeline.date_extract import (
    DEFAULT_DATE_FORMATS,
    FORMAT_DE,
    FORMAT_EN_MONTH,
    FORMAT_ISO,
    FORMAT_SLASH,
    SOURCE_DOCUMENT,
    SOURCE_FILE,
    DateRange,
    DateSearchFilter,
)
from ui.drive_search import DriveSearchResult, extract_folder_id
from ui.i18n import LanguageManager
from ui.merge_search import IcoSearchResult
from ui.merge_search_dialog import (
    _DRIVE_CONNECTED_STYLE,
    _CurrentWidgetSizedStack,
    _DetachedResultsWindow,
    _configure_optional_date_edit,
    _match_path,
    _mtime_or_zero,
    _optional_date,
)
from ui.search_scopes import (
    DATE_REGION_FOOTER,
    DATE_REGION_HEADER,
    DATE_REGION_ICO_FORMAT,
    DEFAULT_SCOPES,
    SCOPE_FULL_TEXT,
    SCOPE_HEADER,
    SCOPE_ICO_FORMAT,
)
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

        self.source_stack = _CurrentWidgetSizedStack()
        self.source_stack.addWidget(self._build_local_panel())
        self.source_stack.addWidget(self._build_drive_panel())

        # --- shared: recursive/scope/query/search/progress/results -----
        # 02.09.2026 - see MergeSearchDialog's identical block (this
        # dialog duplicates that one's recursive checkbox) for Michael's
        # request behind the change of default + the restore/persist below.
        self.recursive_checkbox = QCheckBox()
        self.recursive_checkbox.setChecked(False)

        # 02.09.2026 - see MergeSearchDialog's identical block (this
        # dialog duplicates that one's search-scope checkboxes; see
        # ui/search_scopes.py).
        self.scope_ico_format_checkbox = QCheckBox()
        self.scope_ico_format_checkbox.setChecked(SCOPE_ICO_FORMAT in DEFAULT_SCOPES)
        self.scope_header_checkbox = QCheckBox()
        self.scope_header_checkbox.setChecked(SCOPE_HEADER in DEFAULT_SCOPES)
        self.scope_full_text_checkbox = QCheckBox()
        self.scope_full_text_checkbox.setChecked(SCOPE_FULL_TEXT in DEFAULT_SCOPES)
        scope_row = QHBoxLayout()
        scope_row.addWidget(self.scope_ico_format_checkbox)
        scope_row.addWidget(self.scope_header_checkbox)
        scope_row.addWidget(self.scope_full_text_checkbox)
        scope_row.addStretch(1)

        self.date_filter_group = self._build_date_filter_group()

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
        # 02.09.2026 - see MergeSearchDialog's identical block (this
        # dialog duplicates that one's results section) for the full
        # reasoning behind results_stack/the sort buttons/detach button.
        self.results_placeholder_label = QLabel()
        self.results_placeholder_label.setAlignment(Qt.AlignCenter)
        self.results_placeholder_label.setWordWrap(True)
        self.results_stack = QStackedWidget()
        self.results_stack.addWidget(self.results)
        self.results_stack.addWidget(self.results_placeholder_label)
        self._detached_results_window: _DetachedResultsWindow | None = None

        self.select_all_button = QPushButton()
        self.select_all_button.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_button = QPushButton()
        self.select_none_button.clicked.connect(lambda: self._set_all_checked(False))
        self._results_name_sort_ascending = True
        self._results_date_sort_ascending = True
        self.sort_results_by_name_button = QPushButton()
        self.sort_results_by_name_button.clicked.connect(self._sort_results_by_name)
        self.sort_results_by_date_button = QPushButton()
        self.sort_results_by_date_button.clicked.connect(self._sort_results_by_date)
        self.detach_results_button = QPushButton()
        self.detach_results_button.clicked.connect(self._toggle_detach_results)
        select_row = QHBoxLayout()
        select_row.addWidget(self.select_all_button)
        select_row.addWidget(self.select_none_button)
        select_row.addWidget(self.sort_results_by_name_button)
        select_row.addWidget(self.sort_results_by_date_button)
        select_row.addWidget(self.detach_results_button)
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
        layout.addLayout(scope_row)
        layout.addWidget(self.date_filter_group)
        layout.addWidget(self.query_label)
        layout.addWidget(self.query_edit)
        layout.addLayout(search_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addLayout(select_row)
        layout.addWidget(self.results_stack, 1)
        layout.addLayout(button_row)
        self.resize(680, 640)

        self.language.changed.connect(self.retranslate)
        self.retranslate()
        self._refresh_drive_status()
        self._restore_drive_state()
        self._restore_local_folder_state()

    def _restore_local_folder_state(self) -> None:
        """02.09.2026 - see MergeSearchDialog's identical method (this
        dialog duplicates the same local-folder field/recursive checkbox)
        for the full reasoning."""
        folder = str(self.settings.value("word_merge_search_last_folder", "", type=str))
        if folder:
            self._folder = Path(folder)
            self.folder_edit.setText(folder)
        self.recursive_checkbox.setChecked(
            bool(self.settings.value("word_merge_search_recursive", False, type=bool))
        )
        self._update_search_enabled()

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
        self.settings.setValue("word_merge_search_recursive", self.recursive_checkbox.isChecked())
        # 02.09.2026 - see MergeSearchDialog.done()'s identical comment
        # (this dialog duplicates that one's detach-results feature).
        if self._detached_results_window is not None:
            self._detached_results_window.close()
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

    def _build_date_filter_group(self) -> QGroupBox:
        """02.09.2026 - see MergeSearchDialog._build_date_filter_group()'s
        identical method (this dialog duplicates that one's date-filter
        panel) for the full reasoning behind the design."""
        group = QGroupBox()
        group.setCheckable(True)
        group.setChecked(False)

        self.date_source_file_radio = QRadioButton()
        self.date_source_file_radio.setChecked(True)
        self.date_source_document_radio = QRadioButton()
        self.date_source_file_radio.toggled.connect(self._on_date_source_changed)
        date_source_row = QHBoxLayout()
        date_source_row.addWidget(self.date_source_file_radio)
        date_source_row.addWidget(self.date_source_document_radio)
        date_source_row.addStretch(1)

        self.date_region_ico_format_checkbox = QCheckBox()
        self.date_region_ico_format_checkbox.setChecked(True)
        self.date_region_header_checkbox = QCheckBox()
        self.date_region_footer_checkbox = QCheckBox()
        date_region_row = QHBoxLayout()
        date_region_row.addWidget(self.date_region_ico_format_checkbox)
        date_region_row.addWidget(self.date_region_header_checkbox)
        date_region_row.addWidget(self.date_region_footer_checkbox)
        date_region_row.addStretch(1)

        self.date_format_iso_checkbox = QCheckBox()
        self.date_format_iso_checkbox.setChecked(FORMAT_ISO in DEFAULT_DATE_FORMATS)
        self.date_format_de_checkbox = QCheckBox()
        self.date_format_de_checkbox.setChecked(FORMAT_DE in DEFAULT_DATE_FORMATS)
        self.date_format_en_month_checkbox = QCheckBox()
        self.date_format_en_month_checkbox.setChecked(FORMAT_EN_MONTH in DEFAULT_DATE_FORMATS)
        self.date_format_slash_checkbox = QCheckBox()
        self.date_format_slash_checkbox.setChecked(FORMAT_SLASH in DEFAULT_DATE_FORMATS)
        date_format_row = QHBoxLayout()
        date_format_row.addWidget(self.date_format_iso_checkbox)
        date_format_row.addWidget(self.date_format_de_checkbox)
        date_format_row.addWidget(self.date_format_en_month_checkbox)
        date_format_row.addWidget(self.date_format_slash_checkbox)
        date_format_row.addStretch(1)

        self.date_document_options = QWidget()
        date_document_layout = QVBoxLayout(self.date_document_options)
        date_document_layout.setContentsMargins(0, 0, 0, 0)
        date_document_layout.addLayout(date_region_row)
        date_document_layout.addLayout(date_format_row)
        self.date_document_options.setVisible(False)  # source starts on "Dateidatum"

        self.date_exact_checkbox = QCheckBox()
        self.date_exact_checkbox.toggled.connect(self._on_date_exact_toggled)

        self.date_from_label = QLabel()
        self.date_from_edit = QDateEdit()
        _configure_optional_date_edit(self.date_from_edit)
        self.date_to_label = QLabel()
        self.date_to_edit = QDateEdit()
        _configure_optional_date_edit(self.date_to_edit)
        range_panel = QWidget()
        range_layout = QHBoxLayout(range_panel)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(self.date_from_label)
        range_layout.addWidget(self.date_from_edit)
        range_layout.addWidget(self.date_to_label)
        range_layout.addWidget(self.date_to_edit)
        range_layout.addStretch(1)

        self.date_exact_label = QLabel()
        self.date_exact_edit = QDateEdit()
        _configure_optional_date_edit(self.date_exact_edit)
        exact_panel = QWidget()
        exact_layout = QHBoxLayout(exact_panel)
        exact_layout.setContentsMargins(0, 0, 0, 0)
        exact_layout.addWidget(self.date_exact_label)
        exact_layout.addWidget(self.date_exact_edit)
        exact_layout.addStretch(1)

        self.date_range_stack = _CurrentWidgetSizedStack()
        self.date_range_stack.addWidget(range_panel)  # index 0: Von/Bis
        self.date_range_stack.addWidget(exact_panel)  # index 1: Exaktes Datum

        # 02.09.2026 - see MergeSearchDialog._build_date_filter_group()'s
        # identical comment (this dialog duplicates that one's date-filter
        # panel) for why the group's content is wrapped like this.
        self.date_filter_content = QWidget()
        content_layout = QVBoxLayout(self.date_filter_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addLayout(date_source_row)
        content_layout.addWidget(self.date_document_options)
        content_layout.addWidget(self.date_exact_checkbox)
        content_layout.addWidget(self.date_range_stack)
        self.date_filter_content.setVisible(False)  # group starts unchecked
        group.toggled.connect(self.date_filter_content.setVisible)

        layout = QVBoxLayout(group)
        layout.addWidget(self.date_filter_content)
        return group

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
        self.scope_ico_format_checkbox.setText(t("merge_search.scope_ico_format"))
        self.scope_header_checkbox.setText(t("merge_search.scope_header"))
        self.scope_full_text_checkbox.setText(t("merge_search.scope_full_text"))
        self.scope_ico_format_checkbox.setToolTip(t("merge_search.scope_ico_format_tooltip"))
        self.scope_header_checkbox.setToolTip(t("merge_search.scope_header_tooltip"))
        self.scope_full_text_checkbox.setToolTip(t("merge_search.scope_full_text_tooltip"))

        self.date_filter_group.setTitle(t("merge_search.date_filter_group"))
        self.date_source_file_radio.setText(t("merge_search.date_source_file"))
        self.date_source_document_radio.setText(t("merge_search.date_source_document"))
        self.date_region_ico_format_checkbox.setText(t("merge_search.date_region_ico_format"))
        self.date_region_header_checkbox.setText(t("merge_search.date_region_header"))
        self.date_region_footer_checkbox.setText(t("merge_search.date_region_footer"))
        self.date_format_iso_checkbox.setText(t("merge_search.date_format_iso"))
        self.date_format_de_checkbox.setText(t("merge_search.date_format_de"))
        self.date_format_en_month_checkbox.setText(t("merge_search.date_format_en_month"))
        self.date_format_slash_checkbox.setText(t("merge_search.date_format_slash"))
        self.date_exact_checkbox.setText(t("merge_search.date_exact_checkbox"))
        self.date_from_label.setText(t("merge_search.date_from_label"))
        self.date_to_label.setText(t("merge_search.date_to_label"))
        self.date_exact_label.setText(t("merge_search.date_exact_label"))
        # 02.09.2026: query_label/query_placeholder used to be
        # word_merge_search.*-specific ("... am Dokumentanfang" vs. the
        # PDF dialog's "... auf Seite 1") back when the search scope was a
        # fixed part of the label text - now that scope is chosen via the
        # checkboxes above (format-agnostic wording either way), both
        # dialogs share the same merge_search.* key, like every other
        # reused key below.
        self.query_label.setText(t("merge_search.query_label"))
        self.query_edit.setPlaceholderText(t("merge_search.query_placeholder"))
        # 02.09.2026 - see MergeSearchDialog's identical comment (this
        # dialog duplicates that one's query field).
        self.query_edit.setToolTip(t("merge_search.query_tooltip"))
        self.query_label.setToolTip(t("merge_search.query_tooltip"))
        self.search_button.setText(t("merge_search.search_button"))
        self.cancel_button.setText(t("merge_search.cancel_button"))
        self.select_all_button.setText(t("merge_search.select_all"))
        self.select_none_button.setText(t("merge_search.select_none"))
        self.sort_results_by_date_button.setToolTip(t("merge.sort_by_date_tooltip"))
        self._update_results_sort_button_labels()
        detach_key = (
            "merge_search.reattach_results_button" if self._detached_results_window is not None
            else "merge_search.detach_results_button"
        )
        self.detach_results_button.setText(t(detach_key))
        self.results_placeholder_label.setText(t("merge_search.results_detached_placeholder"))
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
            self.drive_connection_status_label.setStyleSheet(_DRIVE_CONNECTED_STYLE)
        elif configured:
            self.drive_connection_status_label.setText(t("merge_search.drive_configured_not_connected"))
            self.drive_connection_status_label.setStyleSheet("")
        else:
            self.drive_connection_status_label.setText(t("merge_search.drive_not_configured"))
            self.drive_connection_status_label.setStyleSheet("")
        # 02.09.2026 - see MergeSearchDialog._refresh_drive_status()'s
        # identical comment.
        self.drive_connect_button.setEnabled(configured and not connected and self._connect_worker is None)
        self.drive_disconnect_button.setEnabled(connected)
        self._update_search_enabled()

    # --- search --------------------------------------------------------

    def _selected_scopes(self) -> set[str]:
        """See MergeSearchDialog._selected_scopes() - identical reasoning
        (this dialog duplicates that one's search-scope checkboxes)."""
        scopes: set[str] = set()
        if self.scope_ico_format_checkbox.isChecked():
            scopes.add(SCOPE_ICO_FORMAT)
        if self.scope_header_checkbox.isChecked():
            scopes.add(SCOPE_HEADER)
        if self.scope_full_text_checkbox.isChecked():
            scopes.add(SCOPE_FULL_TEXT)
        return scopes

    # --- date filter -----------------------------------------------------
    # 02.09.2026 - see MergeSearchDialog's identical methods (this dialog
    # duplicates that one's date-filter panel) for the full reasoning.

    def _on_date_source_changed(self, file_checked: bool) -> None:
        self.date_document_options.setVisible(not file_checked)

    def _on_date_exact_toggled(self, checked: bool) -> None:
        self.date_range_stack.setCurrentIndex(1 if checked else 0)

    def _selected_date_regions(self) -> frozenset[str]:
        regions: set[str] = set()
        if self.date_region_ico_format_checkbox.isChecked():
            regions.add(DATE_REGION_ICO_FORMAT)
        if self.date_region_header_checkbox.isChecked():
            regions.add(DATE_REGION_HEADER)
        if self.date_region_footer_checkbox.isChecked():
            regions.add(DATE_REGION_FOOTER)
        return frozenset(regions)

    def _selected_date_formats(self) -> frozenset[str]:
        formats: set[str] = set()
        if self.date_format_iso_checkbox.isChecked():
            formats.add(FORMAT_ISO)
        if self.date_format_de_checkbox.isChecked():
            formats.add(FORMAT_DE)
        if self.date_format_en_month_checkbox.isChecked():
            formats.add(FORMAT_EN_MONTH)
        if self.date_format_slash_checkbox.isChecked():
            formats.add(FORMAT_SLASH)
        return frozenset(formats)

    def _build_date_filter(self) -> tuple[DateSearchFilter | None, str | None]:
        """See MergeSearchDialog._build_date_filter() - identical logic."""
        if not self.date_filter_group.isChecked():
            return None, None

        if self.date_exact_checkbox.isChecked():
            exact = _optional_date(self.date_exact_edit)
            date_range = DateRange(start=exact, end=exact)
        else:
            start = _optional_date(self.date_from_edit)
            end = _optional_date(self.date_to_edit)
            if start is not None and end is not None and start > end:
                return None, "merge_search.error_date_range_reversed"
            date_range = DateRange(start=start, end=end)

        if date_range.is_unbounded:
            return None, None

        if self.date_source_file_radio.isChecked():
            return DateSearchFilter(source=SOURCE_FILE, date_range=date_range), None

        regions = self._selected_date_regions()
        if not regions:
            return None, "merge_search.error_missing_date_region"
        formats = self._selected_date_formats()
        if not formats:
            return None, "merge_search.error_missing_date_format"
        return (
            DateSearchFilter(source=SOURCE_DOCUMENT, date_range=date_range, regions=regions, formats=formats),
            None,
        )

    # --- results: sorting/detaching ---------------------------------------
    # 02.09.2026 - see MergeSearchDialog's identical methods (this dialog
    # duplicates that one's results section) for the full reasoning.

    def _sort_button_label(self, base_key: str, ascending_next: bool) -> str:
        arrow = "▲" if ascending_next else "▼"
        return f"{self.language.text(base_key)} {arrow}"

    def _update_results_sort_button_labels(self) -> None:
        self.sort_results_by_name_button.setText(
            self._sort_button_label("merge.sort_by_name", self._results_name_sort_ascending)
        )
        self.sort_results_by_date_button.setText(
            self._sort_button_label("merge.sort_by_date", self._results_date_sort_ascending)
        )

    def _sort_results(self, key, ascending: bool) -> None:
        entries = [
            (item.data(Qt.UserRole), item.checkState(), item.text(), item.toolTip())
            for item in (self.results.item(row) for row in range(self.results.count()))
        ]
        entries.sort(key=lambda entry: key(entry[0]), reverse=not ascending)
        self.results.clear()
        for path, check_state, label, tooltip in entries:
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(check_state)
            item.setData(Qt.UserRole, path)
            item.setToolTip(tooltip)
            self.results.addItem(item)

    def _sort_results_by_name(self) -> None:
        ascending = self._results_name_sort_ascending
        self._sort_results(lambda path: path.name.lower(), ascending)
        self._results_name_sort_ascending = not ascending
        self._update_results_sort_button_labels()

    def _sort_results_by_date(self) -> None:
        ascending = self._results_date_sort_ascending
        self._sort_results(_mtime_or_zero, ascending)
        self._results_date_sort_ascending = not ascending
        self._update_results_sort_button_labels()

    def _update_results_button_states(self) -> None:
        enabled = self.results.count() > 1
        self.sort_results_by_name_button.setEnabled(enabled)
        self.sort_results_by_date_button.setEnabled(enabled)

    def _toggle_detach_results(self) -> None:
        if self._detached_results_window is None:
            self._detach_results()
        else:
            self._detached_results_window.close()

    def _detach_results(self) -> None:
        self.results_stack.setCurrentWidget(self.results_placeholder_label)
        window = _DetachedResultsWindow(self._on_detached_results_closed)
        window.setWindowTitle(
            f"{self.windowTitle()} – {self.language.text('merge_search.detached_results_title_suffix')}"
        )
        window_layout = QVBoxLayout(window)
        window_layout.addWidget(self.results)
        window.resize(420, 480)
        self._detached_results_window = window
        self.detach_results_button.setText(self.language.text("merge_search.reattach_results_button"))
        window.show()

    def _on_detached_results_closed(self) -> None:
        if self._detached_results_window is None:
            return
        self._detached_results_window = None
        self.results_stack.insertWidget(0, self.results)
        self.results_stack.setCurrentIndex(0)
        self.detach_results_button.setText(self.language.text("merge_search.detach_results_button"))

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
        self._update_results_button_states()
        self.take_selected_button.setEnabled(False)
        self.status_label.setText("")

        scopes = self._selected_scopes()
        if not scopes:
            QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.error_missing_scope"))
            return

        date_filter, date_error_key = self._build_date_filter()
        if date_error_key is not None:
            QMessageBox.warning(self, self.windowTitle(), self.language.text(date_error_key))
            return

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
                client, self._drive_folder_id, self.query_edit.text(), self.recursive_checkbox.isChecked(),
                self._drive_cache_dir, scopes, date_filter,
            )
        else:
            if self._folder is None:
                QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.error_missing_folder"))
                return
            self._worker = WordIcoSearchWorker(
                self._folder, self.query_edit.text(), self.recursive_checkbox.isChecked(), scopes, date_filter
            )

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
        self._update_results_button_states()

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
