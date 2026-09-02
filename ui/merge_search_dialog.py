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

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QSettings, Qt, QThreadPool
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
from ui.natural_sort import natural_sort_key
from ui.search_scopes import (
    DATE_REGION_FOOTER,
    DATE_REGION_HEADER,
    DATE_REGION_ICO_FORMAT,
    DEFAULT_SCOPES,
    SCOPE_FULL_TEXT,
    SCOPE_HEADER,
    SCOPE_ICO_FORMAT,
)
from ui.workers import DriveConnectWorker, DriveSearchWorker, IcoSearchWorker

_SNIPPET_PREVIEW_LENGTH = 120

# 02.09.2026 (Michael: "Das wir mit Google verbunden sind darf ruhig
# prominenter dargestellt werden. Vielleicht mit einem grünem Rahmen um
# die 'Verbunden' Meldung, oder grüner Hintergrund. Den sonst klickt man
# versehentlich wieder auf Verbinden...") - a self-contained
# background/text/border triple (not just a background color) so it reads
# correctly regardless of the app's own light/dark palette (see
# ui/theme.py's module docstring on why colors here are never left to
# inherit from the surrounding theme). Shared between MergeSearchDialog
# and WordMergeSearchDialog (imported there, see that module) rather than
# duplicated, since both apply it to the exact same label/condition.
_DRIVE_CONNECTED_STYLE = (
    "background-color: #d4edda; color: #155724; border: 1px solid #28a745; "
    "border-radius: 4px; padding: 6px;"
)


def _match_path(match) -> Path:
    """IcoSearchMatch calls its field `path`, DriveSearchMatch calls it
    `local_path` (see ui/merge_search.py vs. ui/drive_search.py) - both
    dataclasses were kept source-specific/self-documenting rather than
    forced into one shared shape, so the shared result-rendering code
    below normalizes through this one-line accessor instead.
    """
    return getattr(match, "local_path", None) or match.path


# 02.09.2026 (the date-range/exact-date search filter - see
# pipeline/date_extract.py) - QDateEdit has no built-in "empty" state, so
# an "unset" Von/Bis/Exakt field is represented as this sentinel date:
# setSpecialValueText() (in _configure_optional_date_edit() below) then
# displays a blank field whenever the widget's value equals its
# minimumDate, rather than a real - and misleading - date. 1900-01-01
# rather than QDate's own absolute minimum (year -4713) just so the
# calendar popup opens on a sensible page.
_DATE_UNSET = QDate(1900, 1, 1)


def _configure_optional_date_edit(edit: QDateEdit) -> None:
    """Shared setup for every Von/Bis/Exakt QDateEdit in the date filter -
    see _DATE_UNSET's comment above and _optional_date() below. Imported
    into ui/word_merge_search_dialog.py rather than duplicated, same as
    _DRIVE_CONNECTED_STYLE/_match_path above - purely format-agnostic Qt
    widget setup, nothing PDF- or DOCX-specific about it.
    """
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd.MM.yyyy")
    edit.setMinimumDate(_DATE_UNSET)
    edit.setMaximumDate(QDate(2999, 12, 31))
    edit.setSpecialValueText(" ")  # shown while the value == minimumDate ("not set")
    edit.setDate(_DATE_UNSET)


def _optional_date(edit: QDateEdit) -> date | None:
    """The edit's value as a plain date, or None if it's still at the
    "not set" sentinel (see _configure_optional_date_edit())."""
    value = edit.date()
    if value == _DATE_UNSET:
        return None
    return date(value.year(), value.month(), value.day())


def _mtime_or_zero(path: Path) -> float:
    """Same defensive pattern as MergeDialog._mtime() (ui/merge_dialog.py)
    - a result whose file vanished between the scan and a "Nach Datum
    sortieren" click (02.09.2026, see _sort_results() below) is an edge
    case, not a crash; sorts as if it were the oldest file."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


class _CurrentWidgetSizedStack(QStackedWidget):
    """A QStackedWidget that sizes itself to whichever page is CURRENTLY
    shown, not to the largest of all its pages (Qt's own default).

    02.09.2026 (Michael: "...zwischen dem Suchordner Feld und den Auswahl
    Optionen 'Lokaler Ordner' und 'Google Drive' ist nur ein Label
    'Ordner' aber das scheint 1/3 des Dialogs einzunehmen.") -
    source_stack's Google-Drive panel (folder link/status, cache folder,
    credentials fields, connection status - see _build_drive_panel())
    is far taller than its local-folder panel (just a label + one text
    field), and QStackedWidget.sizeHint()/minimumSizeHint() default to
    the MAX over every page it holds - so the local panel used to be
    padded with a lot of dead vertical space to match the Drive panel's
    height even while the Drive panel itself was never shown. Also used
    for date_range_stack below for the same reason, even though its two
    pages (Von/Bis vs. Exaktes Datum) are closer in size already.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A page switch changes what OUR OWN sizeHint()/minimumSizeHint()
        # report below - updateGeometry() tells the enclosing layout to
        # recompute from those, so the freed/needed space actually
        # reflows (e.g. into self.results_stack's stretch=1 slot) instead
        # of sitting there as dead space until the window is resized by
        # hand.
        self.currentChanged.connect(lambda _index: self.updateGeometry())

    def sizeHint(self):  # noqa: D102 (Qt override, see class docstring)
        current = self.currentWidget()
        return current.sizeHint() if current is not None else super().sizeHint()

    def minimumSizeHint(self):  # noqa: D102 (Qt override, see class docstring)
        current = self.currentWidget()
        return current.minimumSizeHint() if current is not None else super().minimumSizeHint()


class _DetachedResultsWindow(QWidget):
    """Standalone, non-modal top-level window for the "in eigenem Fenster
    öffnen" button (02.09.2026, Michael: "Vielleicht das Ergebnis Fenster
    rausnehmbar machen. Wäre auch besser handhabbar bei vielen Dateien.",
    confirmed via AskUserQuestion: a separate, freely movable/resizable
    window rather than a bigger dialog or an in-dialog splitter) - just
    reparents the SAME QListWidget (self.results) into its own layout for
    as long as it's open, no copy/sync needed, since selected_paths()
    keeps working regardless of which widget currently parents the list.
    Calls back into the owning dialog when closed via THIS window's own
    close button/X (not only via the dialog's "Andocken" toggle, which
    calls window.close() itself - see _on_detached_results_closed()) so
    the list always finds its way back into the dialog rather than being
    stranded in a closed window.

    02.09.2026 (Michael: "Das Fenster erscheint nicht wenn ich auf
    'Ergebnisliste in eigenem Fenster öffnen' anklicke. Die Liste
    verschwindet aber es geht keine neues Fenster auf.") - this dialog is
    normally opened via exec() (application-modal, both directly from
    MainWindow and, one level deeper, from MergeDialog/WordMergeDialog -
    see their own _open_search_dialog()), and Qt blocks/never surfaces
    top-level windows that are not descendants of the modal widget while
    a modal exec() loop is running. `parent` MUST therefore be the owning
    MergeSearchDialog/WordMergeSearchDialog itself (still shown as a real
    top-level window on screen, thanks to the Qt.Window flag below) -
    NOT None, which is what silently produced an unshowable window.
    """

    def __init__(self, parent: QWidget, on_close) -> None:
        super().__init__(parent, Qt.Window)
        self._on_close = on_close

    def closeEvent(self, event) -> None:
        self._on_close()
        super().closeEvent(event)


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

        self.source_stack = _CurrentWidgetSizedStack()
        self.source_stack.addWidget(self._build_local_panel())
        self.source_stack.addWidget(self._build_drive_panel())

        # --- shared: recursive/scope/query/search/progress/results -----
        # 02.09.2026 (Michael: "Dann sollte die Unterordner Option nicht
        # als Standard ausgewählt sein, zumindest nicht beim erneuten
        # Suchen.") - used to always start checked, with no memory of what
        # the user picked last time. Default is now unchecked, and
        # _restore_local_folder_state() below overrides that with whatever
        # was last used (persisted in done(), same "remember across
        # dialog opens" contract as the folder path itself).
        self.recursive_checkbox = QCheckBox()
        self.recursive_checkbox.setChecked(False)

        # 02.09.2026 (Michael: "Wir haben ja nur 'Suchtext (nur
        # ICO-Kopfbereich auf Seite 1)' als Suchbereich statisch zur
        # Verfügung. Allerdings sollte das eine Option sein... Auch die
        # Kombination, entweder alle Optionen, oder nur eine von Dreien")
        # - three independently-combinable checkboxes replacing the
        # former fixed "ICO-Kopfbereich auf Seite 1"-only behavior; see
        # ui/search_scopes.py for what each scope actually searches and
        # this dialog's _selected_scopes()/_start_search(). Default
        # matches Michael's confirmed answer (AskUserQuestion,
        # 02.09.2026): only "ICO Format" checked, same as before this
        # feature.
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
        # 02.09.2026 (Michael: "Es sollte noch die letzten Suchbegriffe im
        # Suchfeld angezeigt werden.") - restored the same way as the last
        # folder/recursive-checkbox state (_restore_local_folder_state()),
        # persisted in done() below.
        self.query_edit.setText(str(self.settings.value("merge_search_last_query", "", type=str)))

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
        # 02.09.2026 - see _DetachedResultsWindow's docstring: results_stack
        # swaps between the real list (index 0) and a placeholder label
        # (index 1) while the list itself is reparented into a separate
        # window, so the main dialog never shows an empty gap in its place.
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
        # 02.09.2026 (Michael: "Die Sortierung nach Dateinamen [...] Es
        # würde reichen die Sortierung im Anzeigefenster gemacht werden
        # könnte.") - mirrors MergeDialog's own sort_by_name_button/
        # sort_by_date_button (ui/merge_dialog.py, Fortsetzung 12)
        # adapted for this dialog's checkable QListWidget instead of a
        # QTableWidget; see _sort_results() below.
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
        """02.09.2026 (Michael: "Der letzte Suchordner wird auch nicht im
        Textfeld angezeigt, aber wenn man den Button klickt ist man direkt
        dort. Das sollte UI weit gleich gehandhabt werden.") - the last
        local folder was already written to QSettings by _choose_folder()
        and used as getExistingDirectory()'s start_dir, exactly like the
        Drive cache folder was before _restore_drive_state() above learned
        to also show it in its own field - but unlike the Drive side, it
        was never read back into folder_edit/self._folder on the next
        open, so the field looked empty even though a folder was already
        remembered underneath. Restored here the same way, plus the
        recursive-subfolder checkbox (persisted in done(), see there).
        """
        folder = str(self.settings.value("merge_search_last_folder", "", type=str))
        if folder:
            self._folder = Path(folder)
            self.folder_edit.setText(folder)
        self.recursive_checkbox.setChecked(
            bool(self.settings.value("merge_search_recursive", False, type=bool))
        )
        self._update_search_enabled()

    def _restore_drive_state(self) -> None:
        """02.09.2026 (Michael: "Die App sollte sich die Google Drive ID
        von der letzten Session merken. Auch den Cache Ordner...") - the
        cache-folder value was already written to QSettings by
        _choose_drive_cache() but never read back into the UI on the next
        open (only used as getExistingDirectory()'s start_dir); the Drive
        folder link/ID had no persistence at all. Both are restored here,
        deliberately without re-resolving the folder against the Drive API
        (that needs a live, authorized connection and would either block
        dialog startup on a network call or need its own async worker) -
        the user still clicks "Prüfen" once, but no longer has to go find
        and re-paste the link every time. The connection/credentials
        status itself needs no restoring here - _refresh_drive_status()
        above already reads it straight from the keyring on every open.
        """
        cache_dir = str(self.settings.value("merge_search_drive_cache_dir", "", type=str))
        if cache_dir:
            self._drive_cache_dir = Path(cache_dir)
            self.drive_cache_edit.setText(cache_dir)
        folder_link = str(self.settings.value("merge_search_drive_folder_link", "", type=str))
        if folder_link:
            # Setting the text fires _on_drive_folder_text_changed(), which
            # (correctly) resets _drive_folder_id to None and the status
            # label to "unresolved" - exactly the state a not-yet-verified
            # restored link should start in.
            self.drive_folder_edit.setText(folder_link)
        self._update_search_enabled()

    def done(self, result: int) -> None:
        # Persists whatever is currently in the Drive-folder field - not
        # only a successfully resolved one - on every way this dialog can
        # close (accept/"Ausgewählte übernehmen", reject/"Schließen", or
        # the window's own close button, which QDialog routes through
        # reject() -> done() same as the others).
        text = self.drive_folder_edit.text().strip()
        if text:
            self.settings.setValue("merge_search_drive_folder_link", text)
        # 02.09.2026 - see _restore_local_folder_state()'s docstring: the
        # recursive checkbox is remembered the same way the Drive folder
        # link above already was, on every path that closes this dialog.
        self.settings.setValue("merge_search_recursive", self.recursive_checkbox.isChecked())
        # 02.09.2026 (Michael: "Es sollte noch die letzten Suchbegriffe im
        # Suchfeld angezeigt werden.") - see query_edit's constructor
        # comment above.
        self.settings.setValue("merge_search_last_query", self.query_edit.text())
        # 02.09.2026 - a still-open detached results window (see
        # _DetachedResultsWindow) must not outlive this dialog: closing it
        # here reparents self.results back before this dialog itself is
        # possibly torn down.
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
        # 02.09.2026 (Michael: "Ich konnte eine json Datei mit den
        # OAuth-Client Daten beim erstellen runterladen. Sollten wir das
        # laden der json Datei beim anmelden unterstützen?") - yes, this is
        # the standard Google-documented way (see
        # pipeline/drive_auth.py::parse_client_secrets_file()'s docstring):
        # picking the file Google Cloud Console already offers avoids
        # retyping/copy-pasting three separate values by hand, which is
        # exactly what caused the last two bugs Michael hit. Fills the
        # three fields below rather than saving directly, so the existing,
        # already-tested "speichern" button/error handling stays the one
        # single save path.
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
        """02.09.2026 (Michael: "Können wir noch eine nach Datumsbereich,
        von, bis, exakt einbauen.") - a checkable QGroupBox: Qt disables
        (greys out, but keeps visible) every child widget automatically
        when unchecked, so "date filter switched off" needs no manual
        enable/disable bookkeeping beyond the checkbox itself.

        Confirmed design (AskUserQuestion, 02.09.2026): a Von/Bis range by
        default, an "Exaktes Datum" toggle swapping in a single date field
        instead (see _on_date_exact_toggled() - date_range_stack's two
        pages), one source per search - file date (SOURCE_FILE) or a date
        found IN the document text (SOURCE_DOCUMENT, restricted to ICO
        Feld/Header/Footer - Michael: "Das aber nur entweder im Header, im
        Footer oder im ICO Feld auf der ersten Seite") never both combined
        (Michael: "Eine Quelle pro Suche wählen") - and individually
        selectable recognized text formats (default ISO only - Michael:
        "Standard ist ISO", see FORMAT_*/DEFAULT_DATE_FORMATS in
        pipeline/date_extract.py).
        """
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

        # 02.09.2026 (Michael: "Wenn 'Nach Datum filtern' deaktiviert ist
        # sollten die anderen Datums Optionen nicht sichtbar sein.") -
        # QGroupBox.setCheckable() alone only DISABLES (greys out, keeps
        # visible) its children when unchecked; everything below is now
        # wrapped in one content widget whose visibility is tied directly
        # to the group's checked state, so an unchecked group collapses
        # to just its title bar instead of a greyed-out, still full-size
        # panel.
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

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("merge_search.title"))
        self.source_local_radio.setText(t("merge_search.source_local"))
        self.source_drive_radio.setText(t("merge_search.source_drive"))
        self.folder_label.setText(t("merge_search.folder_label"))
        self.folder_edit.setPlaceholderText(t("merge_search.folder_placeholder"))
        self.choose_folder_button.setText(t("merge_search.choose_folder"))
        self.recursive_checkbox.setText(t("merge_search.recursive_checkbox"))
        self.scope_ico_format_checkbox.setText(t("merge_search.scope_ico_format"))
        self.scope_header_checkbox.setText(t("merge_search.scope_header"))
        self.scope_full_text_checkbox.setText(t("merge_search.scope_full_text"))
        # 02.09.2026 (Michael: "Bedeutet jetzt 'ICO Format (Kopfbereich
        # Seite 1)' das auch der Header mit durchsucht wird, oder nur der
        # Kopfbereich?") - the three scopes were already independent and
        # non-overlapping in the underlying code; these tooltips just make
        # that explicit in the UI (see ui/i18n_data.py's comment there).
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

        self.query_label.setText(t("merge_search.query_label"))
        self.query_edit.setPlaceholderText(t("merge_search.query_placeholder"))
        # 02.09.2026 (Michael: "einen Tooltip mit etwas mehr Text und
        # Beispiel wäre schon schön") - the label/placeholder text alone
        # only hints at UND/ODER, no room there for a worked example. Set
        # on both the field and its label so hovering either one shows it.
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

    def _load_drive_credentials_from_file(self) -> None:
        """Fills the three fields below from a Google-downloaded client-
        secrets JSON, instead of the user copy-pasting each value by hand -
        see the module-level comment above drive_load_from_file_button for
        why (02.09.2026). Does NOT save anything itself - the user still
        clicks "Zugangsdaten speichern" afterwards, same as after typing
        the fields manually.
        """
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
            self.drive_connection_status_label.setStyleSheet(_DRIVE_CONNECTED_STYLE)
        elif configured:
            self.drive_connection_status_label.setText(t("merge_search.drive_configured_not_connected"))
            self.drive_connection_status_label.setStyleSheet("")
        else:
            self.drive_connection_status_label.setText(t("merge_search.drive_not_configured"))
            self.drive_connection_status_label.setStyleSheet("")
        # 02.09.2026 (Michael, s.o.) - previously enabled whenever
        # `configured`, i.e. even while already connected, making it easy
        # to click "Mit Google verbinden" again by accident (harmless, but
        # confusing/unnecessary - it just re-runs the whole browser
        # consent flow for a connection that already exists).
        self.drive_connect_button.setEnabled(configured and not connected and self._connect_worker is None)
        self.drive_disconnect_button.setEnabled(connected)
        self._update_search_enabled()

    # --- search --------------------------------------------------------

    def _selected_scopes(self) -> set[str]:
        """Which of the three scope checkboxes are checked right now - see
        ui/search_scopes.py for what each scope key means. Read fresh on
        every "Suchen" click rather than cached, same as query_edit.text().
        """
        scopes: set[str] = set()
        if self.scope_ico_format_checkbox.isChecked():
            scopes.add(SCOPE_ICO_FORMAT)
        if self.scope_header_checkbox.isChecked():
            scopes.add(SCOPE_HEADER)
        if self.scope_full_text_checkbox.isChecked():
            scopes.add(SCOPE_FULL_TEXT)
        return scopes

    # --- date filter -----------------------------------------------------

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
        """Returns (filter_or_None, error_translation_key_or_None) - see
        _start_search() for how a non-None error key becomes a
        QMessageBox. The filter is None (with no error) both when the
        group box is unchecked AND when it's checked but no date was
        actually entered - an enabled-but-still-empty filter is a
        plausible "just turned it on, haven't filled it in yet" state,
        not a mistake worth interrupting the search over, so it's treated
        exactly like an empty text query: no filtering at all.
        """
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
    # 02.09.2026 - see this dialog's comments above sort_results_by_name_
    # button/detach_results_button (constructor) for both features' origin.

    def _sort_button_label(self, base_key: str, ascending_next: bool) -> str:
        # Arrow shows the direction the NEXT click will apply - mirrors
        # MergeDialog._sort_button_label() (ui/merge_dialog.py).
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
        """Re-orders the results list in place by `key(path)` - reads
        every item's current path/check-state/label/tooltip first so a
        sort never resets which matches the user already (un)checked,
        then repopulates in the new order. See MergeDialog._sort_rows()
        (ui/merge_dialog.py) for the same pattern applied to a
        QTableWidget instead of a checkable QListWidget.
        """
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
        # 02.09.2026 (Michael: "Die Dateinamen fangen hier aktuell alle
        # mit Nummern an [...] Ich dachte das nach Namen sortieren
        # Standardmässig immer erst die Nummern ausliest [...]") - see
        # ui/natural_sort.py for why a plain string sort gets this wrong
        # for ICO-numbered filenames.
        ascending = self._results_name_sort_ascending
        self._sort_results(lambda path: natural_sort_key(path.name), ascending)
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
            # Reuses the exact same path as the window's own close button/X
            # - see _DetachedResultsWindow.closeEvent() and
            # _on_detached_results_closed() below - so there is only ONE
            # place that actually reparents self.results back.
            self._detached_results_window.close()

    def _detach_results(self) -> None:
        # Switch to the placeholder page WHILE self.results is still one of
        # results_stack's two pages - reparenting it into the new window's
        # own layout below implicitly removes it from results_stack (a
        # QWidget can only have one parent), which would otherwise shift
        # the placeholder down to index 0 first and make a subsequent
        # setCurrentIndex(1) target nothing.
        self.results_stack.setCurrentWidget(self.results_placeholder_label)
        # `self` (not None) as parent - see _DetachedResultsWindow's
        # docstring: required for the window to actually show up at all
        # while this application-modal dialog's exec() loop is running.
        window = _DetachedResultsWindow(self, self._on_detached_results_closed)
        window.setWindowTitle(
            f"{self.windowTitle()} – {self.language.text('merge_search.detached_results_title_suffix')}"
        )
        window_layout = QVBoxLayout(window)
        window_layout.addWidget(self.results)
        # 02.09.2026 (Michael, after the parent=self fix above: "Jetzt geht
        # zwar ein Fenster auf, es wird aber keine Liste angezeigt.") -
        # results_stack.setCurrentWidget() a few lines up hides the widget
        # it switches AWAY from via an explicit widget.hide() (that's how
        # QStackedWidget/QStackedLayout work internally), which sets Qt's
        # "explicitly hidden" state - reparenting a widget into a new,
        # visible layout does NOT clear that state or implicitly re-show
        # it, so self.results stayed invisible inside the otherwise-correct
        # new window. Confirmed by hand: without this show(), a freshly
        # reparented, explicitly-hidden widget's isVisible() stays False
        # even after its new top-level window.show(). _on_detached_results_
        # closed() below never had this problem the other way round,
        # because QStackedWidget.setCurrentIndex() DOES explicitly show()
        # whichever widget becomes the new current page.
        self.results.show()
        window.resize(420, 480)
        self._detached_results_window = window
        self.detach_results_button.setText(self.language.text("merge_search.reattach_results_button"))
        window.show()
        window.raise_()
        window.activateWindow()

    def _on_detached_results_closed(self) -> None:
        if self._detached_results_window is None:
            return
        self._detached_results_window = None
        self.results_stack.insertWidget(0, self.results)
        self.results_stack.setCurrentIndex(0)
        self.detach_results_button.setText(self.language.text("merge_search.detach_results_button"))

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
            self._worker = DriveSearchWorker(
                client, self._drive_folder_id, self.query_edit.text(), self.recursive_checkbox.isChecked(),
                self._drive_cache_dir, scopes, date_filter,
            )
        else:
            if self._folder is None:
                QMessageBox.warning(self, self.windowTitle(), self.language.text("merge_search.error_missing_folder"))
                return
            self._worker = IcoSearchWorker(
                self._folder, self.query_edit.text(), self.recursive_checkbox.isChecked(), scopes, date_filter
            )

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
        self._update_results_button_states()

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
