"""First desktop UI slice for explicit document modes and cost analysis."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, QTimer, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from _version import __version__
from bootstrap.release_source import UpdateInfo
from pipeline.app_logging import LOG_FILE, configure_logging
from pipeline.images.inpainting import GPU_MIN_VRAM_GB, gpu_vram_gb
from pipeline.pdf.translate_pdf import PdfTranslationStats
from pipeline.presentation.translate_presentation import PresentationTranslationStats
from pipeline.translation.cost_control import DEFAULT_MAX_CHARS_PER_RUN
from pipeline.word.translate_document import TranslationStats as WordTranslationStats
from ui.analysis import PRICING
from ui.document_job_common import (
    INPAINTING_BACKEND_FACTORIES,
    OCR_ENGINE_FACTORIES,
    inpainting_backend_available,
    ocr_engine_available,
    safe_destination,
)
from ui.i18n import LOCALES, LanguageManager
from ui.image_job import ImageBatchJobResult, ImageBatchStats, ImageJobResult
from ui.merge_dialog import MergeDialog
from ui.word_merge_dialog import WordMergeDialog
from ui.models import AnalysisResult, EmbeddedImageMode, TranslationMode, TranslationRequest
from ui.pdf_job import PdfJobResult
from ui.pptx_job import PresentationJobResult
from ui.settings import credential_status, save_credential
from ui.theme import build_stylesheet, palette_colors
from ui.word_job import WordJobResult
from ui.workers import (
    AnalysisWorker,
    ImageTranslationWorker,
    PdfTranslationWorker,
    PresentationTranslationWorker,
    UpdateApplyWorker,
    UpdateCheckWorker,
    WordTranslationWorker,
)

log = logging.getLogger(__name__)

MODE_KEYS = {
    TranslationMode.PDF: "mode.pdf",
    TranslationMode.PRESENTATION: "mode.presentation",
    TranslationMode.WORD: "mode.word",
    TranslationMode.IMAGES: "mode.images",
}

# PPTX (RoadMap.md Phase 1), DOCX (Phase 2/Word), the direct PDF path
# (Phase 2/PDF) and now the eigenständige Bildübersetzung (Phase 3/
# TranslationMode.IMAGES, RoadMap.md) are all connected to the start
# button. PDF's prerequisite quality issue (the redact/insert
# duplicate-text bug) is fixed and regression-tested (see
# tests/test_pdf_redact_insert_collision.py); a number of other, narrower
# PDF quality items remain open and are catalogued in every PDF job's QA
# report instead of being silently ignored - see ui/pdf_job.py. IMAGES
# mode's own open items (no embedding into PDF/Word/PPTX yet, no manual
# correction dialog, only Tesseract/Box-Overlay/CPU-Inpainting so far) are
# catalogued the same way in ui/image_job.py's QA report and in
# RoadMap.md Phase 3.
_EXECUTABLE_MODES = {
    TranslationMode.PRESENTATION, TranslationMode.WORD, TranslationMode.PDF, TranslationMode.IMAGES,
}

# 28.08.2026 - real user report, Backlog.md 28.08.2026, Michael: "Am
# Anfang geht es gut 30 Sekunden bevor sich etwas tut ... Erst da sieht
# man das etwas vorwärts geht." job_progress's indeterminate phase (see
# _start(), before _job_total() reports in) used to rely purely on
# QProgressBar's native busy/marquee animation (the usual effect of
# setRange(0, 0)) - which, on Michael's actual desktop/Qt style, simply
# did not visibly animate, so the whole OCR/analysis phase before the
# first per-region count looked completely frozen. _BUSY_SWEEP_MAX/
# _BUSY_SWEEP_STEP drive a manual left-to-right sweep instead (see
# _tick_busy_progress()) - independent of whatever a given platform's
# style does with an indeterminate range, so it is visibly moving
# everywhere, not just on styles that happen to animate it. Values
# picked purely for a smooth-looking ~1s sweep at the 30ms timer
# interval (100 / 3 ≈ 33 ticks ≈ 1s per left-to-right pass); no
# significance beyond that.
_BUSY_SWEEP_MAX = 100
_BUSY_SWEEP_STEP = 3


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: QSettings,
        language: LanguageManager,
        parent: QWidget | None = None,
        initial_provider: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.language = language
        self.locale = QComboBox()
        for info in LOCALES:
            suffix = "" if info.available else f" ({self.language.text('settings.prepared')})"
            self.locale.addItem(info.native_name + suffix, info.code)
            if not info.available:
                self.locale.model().item(self.locale.count() - 1).setEnabled(False)
        self.locale.setCurrentIndex(max(self.locale.findData(language.language), 0))
        self.provider = QComboBox()
        self.provider.addItems(["deepl", "google", "openai", "grok"])
        # initial_provider lets a caller jump straight to the provider that
        # actually needs attention (e.g. the one just selected in the main
        # window with no key configured) instead of always reopening on the
        # last globally-saved default provider.
        self.provider.setCurrentText(initial_provider or str(settings.value("provider", "deepl")))
        self.status = QLabel()
        # 02.09.2026 (Michael): Fehler-/Statusmeldungen sollen sich im UI
        # markieren und kopieren lassen (z. B. für einen Bugreport) - QLabel
        # ist dafür standardmäßig NICHT selektierbar.
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.secret = QLineEdit()
        self.secret.setEchoMode(QLineEdit.Password)
        self.target = QComboBox()
        for target in ("environment", "keyring", "both"):
            self.target.addItem("", target)
        self.max_chars = QSpinBox()
        self.max_chars.setRange(1_000, 10_000_000)
        self.max_chars.setSingleStep(10_000)
        self.max_chars.setValue(int(settings.value("max_chars", DEFAULT_MAX_CHARS_PER_RUN)))
        self.save_key = QPushButton()
        self.save_key.clicked.connect(self._save_key)
        self.provider.currentTextChanged.connect(self._refresh_status)
        self.locale.currentIndexChanged.connect(self._language_changed)
        # 02.09.2026 (Michael: "Haben wir kein Log für genau solche
        # Fälle?") - macht die neue Log-Datei (pipeline/app_logging.py)
        # ohne Dateibrowser-Umweg erreichbar, z. B. um sie hier
        # anzuhängen statt einen Screenshot zu machen.
        self.open_log_button = QPushButton()
        self.open_log_button.clicked.connect(self._open_log_file)

        self.form = QFormLayout()
        self.form_labels = [QLabel() for _ in range(6)]
        for label, field in zip(self.form_labels, (self.locale, self.provider, self.status, self.secret, self.target, self.max_chars)):
            self.form.addRow(label, field)
        self.form.addRow("", self.save_key)
        self.form.addRow("", self.open_log_button)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        self.note = QLabel()
        layout = QVBoxLayout(self)
        layout.addLayout(self.form)
        layout.addWidget(self.note)
        layout.addWidget(self.buttons)
        self.language.changed.connect(self.retranslate)
        self.retranslate()
        self._refresh_status()

    def _language_changed(self) -> None:
        code = self.locale.currentData()
        if code:
            self.language.set_language(code)

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("settings.title"))
        keys = ("settings.language", "settings.provider", "settings.credentials", "settings.new_key", "settings.storage", "settings.run_limit")
        for label, key in zip(self.form_labels, keys): label.setText(t(key))
        self.secret.setPlaceholderText(t("settings.key_placeholder"))
        for index, key in enumerate(("settings.environment", "settings.keyring", "settings.both")):
            self.target.setItemText(index, t(key))
        self.save_key.setText(t("settings.save_key"))
        self.open_log_button.setText(t("settings.open_log"))
        self.note.setText(t("settings.session_note"))

    def _refresh_status(self) -> None:
        self.status.setText(self.language.text(credential_status(self.provider.currentText())))

    def _open_log_file(self) -> None:
        # configure_logging() (aufgerufen aus main(), bevor irgendein
        # Fenster erscheint) hat die Datei zu diesem Zeitpunkt immer schon
        # angelegt - kein Existenz-Check nötig, aber ein leeres Verzeichnis
        # würde openUrl schlicht ignorieren, falls main() doch mal nicht
        # durchlaufen wurde (z. B. ein Test, der SettingsDialog isoliert
        # instanziiert).
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE)))

    def _save_key(self) -> None:
        try:
            save_credential(self.provider.currentText(), self.secret.text(), self.target.currentData())
        except Exception as exc:
            QMessageBox.critical(self, self.language.text("credentials.title"), str(exc))
            return
        self.secret.clear()
        self._refresh_status()
        QMessageBox.information(self, self.language.text("credentials.title"), self.language.text("credentials.saved"))

    def _accept(self) -> None:
        self.settings.setValue("provider", self.provider.currentText())
        self.settings.setValue("max_chars", self.max_chars.value())
        self.settings.setValue("language", self.language.language)
        self.accept()


def _format_checked_at(iso_timestamp: str) -> str:
    """"2026-09-01T14:32:07.123456+00:00" -> "2026-09-01 16:32" in the
    machine's own local time zone - HardwareCheckDialog's only use of this,
    since GpuCheckResult.checked_at is stored as UTC (see
    bootstrap/gpu_check.py::save_gpu_check_result()) but a "zuletzt
    geprüft"/"last checked" line is far more readable in local time.
    Falls back to the raw string on any parse failure (e.g. a marker file
    from a future format this version doesn't understand) rather than
    raising - this is a display nicety, never worth breaking the whole
    dialog over.
    """
    try:
        from datetime import datetime

        return datetime.fromisoformat(iso_timestamp).astimezone().strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_timestamp


class HardwareCheckDialog(QDialog):
    """"Hilfe" -> Hardware-Test: shows the last persisted GPU check result
    and lets the user re-run it without reinstalling anything.

    01.09.2026 (Michael: "Ist es möglich den HW Check beim Installieren zu
    speichern und in einem Hilfe Menü in der App eine Möglichkeit den HW
    Test anzeigen zu lassen und auch noch mal zu wiederholen. Dort sollte
    auch angezeigt werden ob die HW die Mindestanforderung erfüllt.") - the
    installer's own GPU check (bootstrap/app.py::_show_gpu_check(), LOCAL
    mode only) never had anywhere durable to put its result, so a user who
    installed in ONLINE mode, or upgraded a driver/GPU since installing, or
    just wants to double-check why local GPU-Inpainting isn't behaving as
    expected, had no way to see or repeat that check short of
    reinstalling. Reuses bootstrap.gpu_check directly rather than
    duplicating the nvidia-smi logic - same "safe to import from ui/"
    reasoning as bootstrap.release_source (see that module's own
    docstring): bootstrap.gpu_check pulls in nothing beyond the standard
    library.

    Deliberately synchronous (no QThreadPool worker the way the self-update
    check is) - nvidia-smi answers in well under a second in practice, and
    _NVIDIA_SMI_TIMEOUT_SECONDS (10s) caps the absolute worst case; a modal
    dialog briefly not responding to a button click it just received is a
    reasonable trade against the extra signal/worker plumbing for
    something the user only ever triggers by hand.
    """

    def __init__(self, language: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language
        self._result = None
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.recheck_button = QPushButton()
        self.recheck_button.clicked.connect(self._recheck)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.note)
        layout.addWidget(self.recheck_button)
        layout.addWidget(self.buttons)
        self.language.changed.connect(self.retranslate)
        self._load_last_result()
        self.retranslate()

    def _load_last_result(self) -> None:
        from bootstrap.gpu_check import read_gpu_check_marker

        self._result = read_gpu_check_marker()

    def _recheck(self) -> None:
        from bootstrap.gpu_check import detect_and_save_gpu_check

        self.recheck_button.setEnabled(False)
        self.status.setText(self.language.text("hw_check.checking"))
        try:
            _gpu, self._result = detect_and_save_gpu_check()
        finally:
            self.recheck_button.setEnabled(True)
        self._render_status()

    def retranslate(self) -> None:
        self.setWindowTitle(self.language.text("hw_check.title"))
        self.note.setText(self.language.text("hw_check.note"))
        self.recheck_button.setText(self.language.text("hw_check.recheck_button"))
        self._render_status()

    def _render_status(self) -> None:
        result = self._result
        t = self.language.text
        if result is None:
            self.status.setText(t("hw_check.never_checked"))
            return
        checked_at = _format_checked_at(result.checked_at)
        if not result.found:
            self.status.setText(t("hw_check.not_found", checked_at=checked_at))
            return
        key = "hw_check.found_ok" if result.meets_recommendation else "hw_check.found_below_recommended"
        self.status.setText(
            t(key, name=result.name, vram_gb=result.vram_gb, min_gb=result.min_vram_gb, checked_at=checked_at)
        )


def _bootstrap_language_marker() -> str | None:
    """Language chosen during a guided bootstrapper install, if any - see
    bootstrap/paths.py::language_marker_file() and
    bootstrap/controller.py::write_language_marker() (project doc
    "deployment-strategie-bootstrapper-01-09-2026.md", decision "Ja,
    übernehmen": the bootstrapper's language choice should carry over into
    the real app's first launch). Only ever consulted once, before
    QSettings has its own "language" value yet - see MainWindow.__init__()
    below.

    Any failure (marker file missing - the normal case for a developer-path
    install that never went through the bootstrapper - or corrupt JSON) is
    treated the same as "no marker": this is a convenience pre-selection
    only, never a hard requirement, and LanguageManager already falls back
    to German for anything it does not recognise.
    """
    try:
        from bootstrap.paths import language_marker_file

        marker = language_marker_file()
        if not marker.is_file():
            return None
        data = json.loads(marker.read_text(encoding="utf-8"))
        language = data.get("language")
        return language if isinstance(language, str) else None
    except Exception:
        return None


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(880, 760)
        self.settings = QSettings("PDF-Translator", "Document Translator")
        if self.settings.contains("language"):
            start_language = str(self.settings.value("language", "de"))
        else:
            # First run (no explicit choice saved yet, neither via the app's
            # own SettingsDialog nor a previous run of it): prefer the
            # bootstrapper's language marker over the hardcoded "de"
            # default, if one was left behind.
            start_language = _bootstrap_language_marker() or "de"
        self.language = LanguageManager(start_language)
        self.thread_pool = QThreadPool.globalInstance()
        self.paths: tuple[Path, ...] = ()
        self.last_result: AnalysisResult | None = None
        self._worker: PresentationTranslationWorker | None = None
        self._job_result: PresentationJobResult | None = None
        # Live status of the run in progress, so job_status can show both the
        # currently processed location AND how far the run has actually
        # gotten - a bare "Verarbeite: ..." line looked identical whether the
        # app was busy or stuck, which was reported as "no idea if anything
        # is happening in the background".
        self._job_total_paragraphs = 0
        self._job_last_location = ""
        self._job_last_stats: PresentationTranslationStats | None = None
        # Which i18n key _update_job_status() uses for the "X von Y ..."
        # line - "job.progress_count" (paragraphs/pages/slides) for every
        # mode except IMAGES, which counts whole files instead (see
        # _start()'s is_images branch, which overwrites this before each
        # run).
        self._job_progress_unit_key = "job.progress_count"
        # 28.08.2026 - see _BUSY_SWEEP_MAX/_BUSY_SWEEP_STEP's own comment
        # above - drives job_progress's indeterminate-phase sweep
        # manually via _tick_busy_progress(), started in _start() and
        # stopped the moment a real count is known (_job_total()) or the
        # run ends without ever reaching that point (_show_job_result(),
        # _job_failed()).
        self._busy_timer = QTimer(self)
        self._busy_timer.setInterval(30)
        self._busy_timer.timeout.connect(self._tick_busy_progress)

        # "Hilfe" menu (01.09.2026, Michael: "in einem Hilfe Menü in der
        # App eine Möglichkeit den HW Test anzeigen zu lassen und auch noch
        # mal zu wiederholen") - the app's first menu bar; only ever needed
        # this one entry point before now (everything else lives on
        # settings_button/inline hints, see settings_row further below).
        # Built once here and retranslated by name via _rebuild_help_menu()
        # (called from retranslate()) rather than tracked action-by-action,
        # since QMenu has no equivalent of a plain QLabel.setText() and
        # rebuilding three short-lived QAction objects is simpler than
        # keeping references to each just to retranslate them in place.
        self.help_menu = self.menuBar().addMenu("")
        self._rebuild_help_menu()

        self.mode = QComboBox()
        for mode in MODE_KEYS:
            self.mode.addItem("", mode)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        self.choose = QPushButton()
        self.choose.clicked.connect(self._choose_sources)
        # PDFs zusammenführen/zwischeneinfügen (01.09.2026, Backlog.md
        # 26.08.2026) - a plain button opening ui/merge_dialog.py's
        # MergeDialog, deliberately NOT wired through self.mode/MODE_KEYS -
        # see that dialog's module docstring for why. Always visible/
        # enabled regardless of the mode combo above: it starts its own,
        # completely independent flow (no provider, no cost analysis, no
        # interaction with self.paths/self.last_result at all).
        #
        # 02.09.2026 (Michael: "Sollten die beiden Optionen [...] mit in
        # die 'Vorgang' Auswahlbox? Oder sollten wir Rahmen für Übersetzung
        # und für 'PDF/DOCX' Zusammenführen machen. So ist es ein
        # unangenehmer Mix.") - used to sit as two unlabeled rows inside
        # self.form/config_box, sandwiched between the mode combo and the
        # source-file row, visually indistinguishable from the translation-
        # specific fields around them even though merging shares none of
        # their state (no provider/languages/protected terms, its own
        # modal dialog with its own file table). Folding them INTO the
        # mode combo was considered and rejected: mode selection only
        # toggles which rows of THIS SAME form are visible
        # (_mode_changed()) - merging doesn't belong to that form at all,
        # so it would need the whole form hidden behind a mode that
        # otherwise does nothing "Start" can act on. Given their own card
        # instead (self.merge_box below), reusing the config_box/cost_box/
        # job_box "stack of cards" pattern already established in this
        # window rather than introducing a new UI concept.
        self.merge_button = QPushButton()
        self.merge_button.clicked.connect(self._open_merge_dialog)
        # DOCX-Gegenstück (01.09.2026, Michael: "Jetzt noch das ganze für
        # *.docx.") - ui/word_merge_dialog.py's WordMergeDialog, gleiche
        # Behandlung wie merge_button oben (eigener, unabhängiger Ablauf,
        # nicht über self.mode/MODE_KEYS geführt).
        self.word_merge_button = QPushButton()
        self.word_merge_button.clicked.connect(self._open_word_merge_dialog)

        self.image_mode = QComboBox()
        for value in EmbeddedImageMode:
            self.image_mode.addItem("", value)
        self.provider = QComboBox()
        self.provider.addItems(["deepl", "google", "openai", "grok"])
        self.provider.setCurrentText(str(self.settings.value("provider", "deepl")))
        self.provider.currentTextChanged.connect(self._provider_changed)
        # Reported bug: picking a provider with no API key configured gave
        # no indication of that anywhere in the UI - the only place it ever
        # showed up was buried in the QA report after a full, already-failed
        # run. This label appears immediately next to the provider field
        # instead, with an inline link straight into Settings on the right
        # provider.
        self.provider_hint = QLabel()
        self.provider_hint.setWordWrap(True)
        self.provider_hint.setTextFormat(Qt.RichText)
        self.provider_hint.setStyleSheet("font-weight: bold; padding-left: 2px;")
        self.provider_hint.linkActivated.connect(lambda _href: self._open_settings(self.provider.currentText()))
        self.source_lang = QLineEdit()
        self.target_lang = QLineEdit("DE")
        self.protected = QTextEdit()
        self.protected.setMaximumHeight(90)
        # Explicit, user-controlled special case for the internal "ICO"
        # document type (see RoadMap.md): visible for Word AND PDF mode
        # (see _mode_changed()), wired through TranslationRequest.ico_mode
        # -> ui/word_job.py -> DocxEngine.open() resp. ui/pdf_job.py ->
        # PyMuPdfEngine.open(). Never checked/inferred automatically - see
        # _mode_changed() and DocxEngine.open()'s/PyMuPdfEngine.open()'s
        # docstrings for why.
        self.ico_mode = QCheckBox()
        # PDF-only pair (see _mode_changed()): a real user's live run
        # against a real document had its repeating header translated
        # along with the body, because the direct PDF path never applied
        # any header/footer exclusion (see ui/pdf_job.py's docstring).
        # Wired through TranslationRequest.exclude_header/exclude_footer ->
        # ui/pdf_job.py::run_pdf_job() ->
        # pipeline.pdf.template.detect_header_footer_zones().
        self.exclude_header = QCheckBox()
        self.exclude_footer = QCheckBox()
        # IMAGES-only pair (RoadMap.md Phase 3): which OCR engine/
        # inpainting backend run_image_batch_job() should use for this run -
        # see ui/document_job_common.py's OCR_ENGINE_FACTORIES/
        # INPAINTING_BACKEND_FACTORIES for the keys these combo boxes carry
        # as itemData. ocr_engine_hint mirrors provider_hint's pattern: an
        # availability check (ocr_engine_available()) surfaced right next to
        # the field instead of only failing deep inside a run - see
        # _update_ocr_engine_hint().
        self.ocr_engine = QComboBox()
        for key in OCR_ENGINE_FACTORIES:
            self.ocr_engine.addItem("", key)
        self.ocr_engine.currentIndexChanged.connect(self._ocr_engine_changed)
        self.ocr_engine_hint = QLabel()
        self.ocr_engine_hint.setWordWrap(True)
        self.ocr_engine_hint.setStyleSheet("font-weight: bold; padding-left: 2px;")
        self.inpainting_backend = QComboBox()
        for key in INPAINTING_BACKEND_FACTORIES:
            self.inpainting_backend.addItem("", key)
        self.inpainting_backend.currentIndexChanged.connect(self._inpainting_backend_changed)
        self.inpainting_backend_hint = QLabel()
        self.inpainting_backend_hint.setWordWrap(True)
        self.inpainting_backend_hint.setStyleSheet("font-weight: bold; padding-left: 2px;")

        self.form = QFormLayout()
        self.form_labels = [QLabel() for _ in range(12)]
        self.form.addRow(self.form_labels[0], self.mode)
        source_row = QHBoxLayout(); source_row.addWidget(self.source_label, 1); source_row.addWidget(self.choose)
        self.form.addRow(self.form_labels[1], source_row)
        self.form.addRow(self.form_labels[2], self.image_mode)
        self.form.addRow(self.form_labels[3], self.provider)
        self.form.addRow("", self.provider_hint)
        for label, field in zip(self.form_labels[4:], (self.source_lang, self.target_lang, self.protected)):
            self.form.addRow(label, field)
        self.form.addRow(self.form_labels[7], self.ico_mode)
        self.form.addRow(self.form_labels[8], self.exclude_header)
        self.form.addRow(self.form_labels[9], self.exclude_footer)
        self.form.addRow(self.form_labels[10], self.ocr_engine)
        self.form.addRow("", self.ocr_engine_hint)
        self.form.addRow(self.form_labels[11], self.inpainting_backend)
        self.form.addRow("", self.inpainting_backend_hint)

        self.analyze = QPushButton()
        self.analyze.clicked.connect(self._analyze)
        self.confirm = QCheckBox()
        self.confirm.setEnabled(False)
        self.confirm.toggled.connect(self._update_start_state)
        self.start = QPushButton()
        self.start.setEnabled(False)
        self.start.clicked.connect(self._start)
        # 26.08.2026 - the app's one primary call-to-action gets the solid
        # green "primary" button treatment (see ui/theme.py's
        # build_stylesheet() docstring) - every other button keeps the
        # neutral secondary look, same split as the reference project.
        self.start.setProperty("cssClass", "primary")
        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setStyleSheet("padding: 10px")

        self.start_hint = QLabel()
        self.start_hint.setWordWrap(True)
        # Bold only - no hardcoded color: this label must stay legible under
        # whatever palette is active (see ui/theme.py / apply_explicit_palette()),
        # not assume a specific light or dark background.
        self.start_hint.setStyleSheet("font-weight: bold; padding-left: 2px;")

        self.cost_box = QGroupBox()
        cost_layout = QVBoxLayout(self.cost_box)
        cost_layout.addWidget(self.result)
        cost_layout.addWidget(self.confirm)
        actions = QHBoxLayout(); actions.addWidget(self.analyze); actions.addWidget(self.start)
        cost_layout.addLayout(actions)
        cost_layout.addWidget(self.start_hint)

        # Run/result panel: live progress while a job is running, then the
        # output file, short stats, overflow hints and QA report afterwards.
        self.job_status = QLabel()
        self.job_status.setWordWrap(True)
        self.job_status.setStyleSheet("padding: 10px")
        self.job_status.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.job_progress = QProgressBar()
        self.job_progress.setVisible(False)
        self.cancel_button = QPushButton()
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.open_folder_button = QPushButton()
        self.open_folder_button.setVisible(False)
        self.open_folder_button.clicked.connect(self._open_output_folder)
        self.open_report_button = QPushButton()
        self.open_report_button.setVisible(False)
        self.open_report_button.clicked.connect(self._open_qa_report)
        # PDF-only, only shown once a run actually produced correctable
        # blocks (see _show_job_result()) - opens PdfCorrectionDialog
        # (ui/correction_dialog.py), RoadMap.md Phase 2/PDF's "PDF-
        # Übersetzung korrigieren" item.
        self.correct_translation_button = QPushButton()
        self.correct_translation_button.setVisible(False)
        self.correct_translation_button.clicked.connect(self._open_correction_dialog)

        self.job_box = QGroupBox()
        job_layout = QVBoxLayout(self.job_box)
        job_layout.addWidget(self.job_status)
        job_layout.addWidget(self.job_progress)
        job_actions = QHBoxLayout()
        job_actions.addWidget(self.cancel_button)
        job_actions.addWidget(self.open_folder_button)
        job_actions.addWidget(self.open_report_button)
        job_actions.addWidget(self.correct_translation_button)
        job_layout.addLayout(job_actions)

        self.settings_button = QPushButton()
        # Not a direct connect: _open_settings() now takes an optional
        # preselect_provider argument, and QPushButton.clicked emits a bool
        # ("checked") - a direct connection would let PySide feed that bool
        # into preselect_provider instead of the intended default. The
        # lambda pins the call to zero arguments.
        self.settings_button.clicked.connect(lambda: self._open_settings())
        # Self-update (01.09.2026, Michael: "Update sollte die App selbst
        # prüfen.") - a plain link-style label next to settings_button,
        # hidden until _check_for_update()'s background check actually
        # finds something (see _update_check_finished()). RichText +
        # linkActivated mirrors provider_hint's own inline-link pattern
        # above rather than introducing a whole menu bar for this one
        # entry point.
        self.update_hint = QLabel()
        self.update_hint.setTextFormat(Qt.RichText)
        self.update_hint.setVisible(False)
        self.update_hint.linkActivated.connect(self._offer_update)
        self._pending_update: UpdateInfo | None = None
        # 26.08.2026 - the form used to sit directly in `root`, the only
        # section of the window WITHOUT a card around it (cost_box/job_box
        # already were QGroupBoxes). Wrapped in its own card so the whole
        # window reads as a stack of cards, matching the reference
        # project's "Modus"/"Dateien"/... sections rather than one card-
        # less form followed by two cards.
        self.config_box = QGroupBox()
        config_layout = QVBoxLayout(self.config_box)
        config_layout.addLayout(self.form)
        # 02.09.2026 - see the comment above merge_button/word_merge_button
        # (constructor) for why these two moved out of self.form/
        # config_box into their own card: merging is an independent action,
        # not a translation mode, so it gets its own "Dateien
        # zusammenführen" card instead of two undifferentiated rows inside
        # the translation config form. Placed ABOVE config_box (confirmed
        # with Michael) so it reads as an equally-weighted, independent
        # first choice rather than a translation-config afterthought.
        self.merge_box = QGroupBox()
        merge_box_row = QHBoxLayout()
        merge_box_row.addWidget(self.merge_button)
        merge_box_row.addWidget(self.word_merge_button)
        merge_box_row.addStretch(1)
        merge_box_layout = QVBoxLayout(self.merge_box)
        merge_box_layout.addLayout(merge_box_row)
        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        root.addWidget(self.merge_box)
        root.addWidget(self.config_box)
        root.addWidget(self.cost_box)
        root.addWidget(self.job_box)
        settings_row = QHBoxLayout()
        settings_row.addStretch()
        settings_row.addWidget(self.update_hint)
        settings_row.addWidget(self.settings_button)
        root.addLayout(settings_row)
        root.addStretch()
        widget = QWidget(); widget.setLayout(root); self.setCentralWidget(widget)
        self.language.changed.connect(self.retranslate)
        self.retranslate()
        # Self-update: fired once, shortly after the window is up rather
        # than from inside __init__ directly - QThreadPool.start() below
        # would work either way, but a short delay means this network call
        # never competes with the window actually becoming visible/
        # responsive on a slow machine. 3s, not immediately: not urgent
        # enough to be the very first thing competing for I/O on startup.
        QTimer.singleShot(3000, self._check_for_update)
        # Restored BEFORE _mode_changed(): that call re-derives which
        # rows/checkboxes are actually valid for the (just-restored) mode -
        # e.g. it resets ico_mode if the restored mode is neither Word nor
        # PDF - so a stale combination from an old, no-longer-applicable
        # mode can never survive the restore.
        self._restore_form_state()
        self._mode_changed()

    def _restore_form_state(self) -> None:
        """Refill the form with whatever was on screen the last time the
        app was closed (see closeEvent()) - a real user reported having to
        retype the source/target language, protected terms and every
        dropdown choice again on every single run."""
        settings = self.settings
        mode_value = settings.value("form.mode", "", type=str)
        if mode_value:
            try:
                index = self.mode.findData(TranslationMode(mode_value))
            except ValueError:
                index = -1
            if index >= 0:
                self.mode.setCurrentIndex(index)
        image_mode_value = settings.value("form.image_mode", "", type=str)
        if image_mode_value:
            try:
                index = self.image_mode.findData(EmbeddedImageMode(image_mode_value))
            except ValueError:
                index = -1
            if index >= 0:
                self.image_mode.setCurrentIndex(index)
        self.source_lang.setText(settings.value("form.source_lang", "", type=str))
        self.target_lang.setText(settings.value("form.target_lang", "DE", type=str))
        self.protected.setPlainText(settings.value("form.protected_terms", "", type=str))
        self.ico_mode.setChecked(settings.value("form.ico_mode", False, type=bool))
        self.exclude_header.setChecked(settings.value("form.exclude_header", False, type=bool))
        self.exclude_footer.setChecked(settings.value("form.exclude_footer", False, type=bool))
        ocr_engine_value = settings.value("form.ocr_engine", "", type=str)
        if ocr_engine_value:
            index = self.ocr_engine.findData(ocr_engine_value)
            if index >= 0:
                self.ocr_engine.setCurrentIndex(index)
        inpainting_value = settings.value("form.inpainting_backend", "", type=str)
        if inpainting_value:
            index = self.inpainting_backend.findData(inpainting_value)
            if index >= 0:
                self.inpainting_backend.setCurrentIndex(index)

    def _persist_form_state(self) -> None:
        """Counterpart to _restore_form_state() - called from closeEvent()
        so the next run starts where this one left off instead of blank."""
        settings = self.settings
        mode = self.mode.currentData()
        if mode is not None:
            settings.setValue("form.mode", TranslationMode(mode).value)
        image_mode = self.image_mode.currentData()
        if image_mode is not None:
            settings.setValue("form.image_mode", EmbeddedImageMode(image_mode).value)
        settings.setValue("form.source_lang", self.source_lang.text())
        settings.setValue("form.target_lang", self.target_lang.text())
        settings.setValue("form.protected_terms", self.protected.toPlainText())
        settings.setValue("form.ico_mode", self.ico_mode.isChecked())
        settings.setValue("form.exclude_header", self.exclude_header.isChecked())
        settings.setValue("form.exclude_footer", self.exclude_footer.isChecked())
        if self.ocr_engine.currentData():
            settings.setValue("form.ocr_engine", self.ocr_engine.currentData())
        if self.inpainting_backend.currentData():
            settings.setValue("form.inpainting_backend", self.inpainting_backend.currentData())

    def closeEvent(self, event) -> None:
        self._persist_form_state()
        # 02.09.2026 (Michael: Prozess beendet sich nach Fensterschliessen
        # nicht sauber) - explizit hier flushen statt uns auf Qt/QSettings'
        # eigenen, unbestimmten Zeitpunkt fuers Schreiben auf die Platte zu
        # verlassen: main() unten beendet den Prozess gleich per os._exit()
        # (siehe dortiger Kommentar), das ueberspringt jede normale
        # Python-/Qt-Aufraeumroutine.
        self.settings.sync()
        super().closeEvent(event)

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("app.title"))
        self.merge_box.setTitle(t("merge_box.group"))
        self.config_box.setTitle(t("config.group"))
        for index, mode in enumerate(MODE_KEYS): self.mode.setItemText(index, t(MODE_KEYS[mode]))
        for index, key in enumerate(("image.none", "image.selected", "image.all")): self.image_mode.setItemText(index, t(key))
        for label, key in zip(self.form_labels, ("field.mode", "field.source", "field.images", "field.provider", "field.source_language", "field.target_language", "field.protected_terms", "field.ico_mode", "field.exclude_header", "field.exclude_footer", "field.ocr_engine", "field.inpainting_backend")):
            label.setText(t(key))
        for index, key in enumerate(OCR_ENGINE_FACTORIES):
            self.ocr_engine.setItemText(index, t(f"ocr_engine.{key}"))
        for index, key in enumerate(INPAINTING_BACKEND_FACTORIES):
            self.inpainting_backend.setItemText(index, t(f"inpainting_backend.{key}"))
        if not self.paths: self.source_label.setText(t("source.none"))
        self.choose.setText(t("source.choose"))
        self.merge_button.setText(t("merge.button"))
        self.word_merge_button.setText(t("word_merge.button"))
        self.source_lang.setPlaceholderText(t("source_language.placeholder"))
        self.protected.setPlaceholderText(t("protected.placeholder"))
        self.cost_box.setTitle(t("analysis.group"))
        self.analyze.setText(t("analysis.button"))
        self.confirm.setText(t("analysis.checked"))
        self.ico_mode.setText(t("ico_mode.checkbox"))
        self.ico_mode.setToolTip(t("ico_mode.tooltip"))
        self.exclude_header.setText(t("exclude_header.checkbox"))
        self.exclude_header.setToolTip(t("exclude_header.tooltip"))
        self.exclude_footer.setText(t("exclude_footer.checkbox"))
        self.exclude_footer.setToolTip(t("exclude_footer.tooltip"))
        self.start.setText(t("start.button"))
        self.job_box.setTitle(t("job.group"))
        self.cancel_button.setText(t("job.cancel"))
        self.open_folder_button.setText(t("job.open_folder"))
        self.open_report_button.setText(t("job.open_report"))
        self.correct_translation_button.setText(t("job.correct_translation"))
        self.settings_button.setText(t("settings.button"))
        self._render_update_hint()
        self._rebuild_help_menu()
        if self.last_result is None: self.result.setText(t("analysis.required"))
        else: self._show_analysis(self.last_result)
        if self._worker is None and self._job_result is None:
            self.job_status.setText(t("job.idle"))
        elif self._job_result is not None:
            self._show_job_result(self._job_result)
        self._update_provider_credential_hint()
        self._update_ocr_engine_hint()
        self._update_inpainting_backend_hint()
        self._update_start_state()

    # --- self-update (01.09.2026, Michael: "Update sollte die App selbst
    # prüfen.") --------------------------------------------------------

    def _render_update_hint(self) -> None:
        """(Re-)renders update_hint from self._pending_update - the current
        language's wording for whichever state it's in (nothing pending,
        an update found, installing). Split out from _update_check_finished()
        so retranslate() can re-run it on a language change without
        re-running the network check itself.
        """
        if self._pending_update is None:
            self.update_hint.setVisible(False)
            return
        text = self.language.text("update.available", version=self._pending_update.version)
        self.update_hint.setText(f'<a href="update">{text}</a>')
        self.update_hint.setVisible(True)

    def _check_for_update(self) -> None:
        worker = UpdateCheckWorker(__version__)
        worker.signals.finished.connect(self._update_check_finished)
        worker.signals.failed.connect(self._update_check_failed)
        self.thread_pool.start(worker)

    def _update_check_finished(self, info: UpdateInfo | None) -> None:
        self._pending_update = info
        self._render_update_hint()

    def _update_check_failed(self, message: str) -> None:
        # Deliberately silent (see UpdateCheckWorker's own docstring) - an
        # unattended startup check going offline/unreachable must never
        # interrupt someone who never asked for it. Logged for anyone
        # actually debugging a "why doesn't it ever find an update" report.
        log.debug("Update check failed: %s", message)

    def _offer_update(self, _href: str = "") -> None:
        info = self._pending_update
        if info is None:
            return
        reply = QMessageBox.question(
            self,
            self.language.text("update.confirm_title"),
            self.language.text("update.confirm_body", version=info.version),
        )
        if reply != QMessageBox.Yes:
            return
        self.update_hint.setText(self.language.text("update.installing"))
        self.update_hint.setVisible(True)
        worker = UpdateApplyWorker(info)
        worker.signals.finished.connect(self._update_apply_finished)
        worker.signals.failed.connect(self._update_apply_failed)
        self.thread_pool.start(worker)

    def _update_apply_finished(self) -> None:
        # No auto-restart - see UpdateApplyWorker's own docstring for why.
        self._pending_update = None
        self.update_hint.setVisible(False)
        QMessageBox.information(
            self, self.language.text("update.success_title"), self.language.text("update.success_body")
        )

    def _update_apply_failed(self, message: str) -> None:
        # The update attempt failed, but the OLD source/venv were never
        # touched until download_release()/pip_install() each fully
        # succeeded (see UpdateApplyWorker) - the app keeps running exactly
        # as before, so this is a plain error dialog, not a "please
        # restart"/recovery flow. self._pending_update is deliberately kept
        # (not cleared) so the hint goes back to offering the same update
        # rather than disappearing on a failure the user may want to retry.
        self._render_update_hint()
        QMessageBox.warning(
            self, self.language.text("update.failed_title"), self.language.text("update.failed_body", error=message)
        )

    # --- "Hilfe" menu (01.09.2026) --------------------------------------

    def _rebuild_help_menu(self) -> None:
        """Rebuilds help_menu's actions from scratch in the current
        language - see help_menu's own setup comment in __init__ for why a
        rebuild rather than retranslating three tracked QAction objects in
        place.
        """
        t = self.language.text
        self.help_menu.setTitle(t("menu.help"))
        self.help_menu.clear()
        hw_check_action = self.help_menu.addAction(t("menu.help.hw_check"))
        hw_check_action.triggered.connect(self._open_hardware_check)
        update_action = self.help_menu.addAction(t("menu.help.check_updates"))
        update_action.triggered.connect(self._check_for_update_manual)
        about_action = self.help_menu.addAction(t("menu.help.about"))
        about_action.triggered.connect(self._about)

    def _open_hardware_check(self) -> None:
        dialog = HardwareCheckDialog(self.language, self)
        dialog.exec()

    def _check_for_update_manual(self) -> None:
        """"Hilfe" -> "Nach Updates suchen …" - unlike the silent startup
        check (_check_for_update()), a check the user explicitly asked for
        always gets a visible outcome, success or failure (see
        _update_check_manual_finished()/_update_check_manual_failed()
        below) - a manual click that visibly does nothing when there is no
        update reads as broken, not as "already up to date".
        """
        worker = UpdateCheckWorker(__version__)
        worker.signals.finished.connect(self._update_check_manual_finished)
        worker.signals.failed.connect(self._update_check_manual_failed)
        self.thread_pool.start(worker)

    def _update_check_manual_finished(self, info: UpdateInfo | None) -> None:
        self._pending_update = info
        self._render_update_hint()
        if info is None:
            QMessageBox.information(
                self,
                self.language.text("update.check.no_update_title"),
                self.language.text("update.check.no_update_body", version=__version__),
            )
            return
        self._offer_update()

    def _update_check_manual_failed(self, message: str) -> None:
        QMessageBox.warning(
            self,
            self.language.text("update.check.failed_title"),
            self.language.text("update.check.failed_body", error=message),
        )

    def _about(self) -> None:
        QMessageBox.about(
            self,
            self.language.text("menu.help.about"),
            self.language.text("about.body", app_name=self.language.text("app.title"), version=__version__),
        )

    def _update_provider_credential_hint(self) -> None:
        provider = self.provider.currentText()
        missing = credential_status(provider) == "credential.missing"
        self.provider_hint.setText(
            self.language.text("provider.missing_key", provider=provider) if missing else ""
        )
        self.provider_hint.setVisible(missing)

    def _provider_changed(self) -> None:
        self._update_provider_credential_hint()
        # The cost estimate (pricing, free tier, live-quota line) is
        # provider-specific - a previous analysis's numbers would otherwise
        # stay on screen (and stay confirmable via the checkbox) after
        # switching to a provider they don't apply to, e.g. still showing
        # DeepL's live quota line after switching to Google. Matches the
        # existing behaviour for a mode/source change (_mode_changed()/
        # _choose_sources()) - only the analysis/cost panel resets here, the
        # "Lauf und Ergebnis" panel from a previously completed run is left
        # alone until a new run is actually started (see _start()), since
        # it documents a completed action rather than a live preview.
        self._invalidate_analysis()

    def _mode_changed(self) -> None:
        is_images = self.mode.currentData() == TranslationMode.IMAGES
        self.image_mode.setEnabled(not is_images)
        if is_images:
            self.image_mode.setCurrentIndex(2)
        # ico_mode applies to Word AND PDF mode (see RoadMap.md) - hide the
        # whole row rather than just disabling it, and force it back off
        # when leaving BOTH modes so a stale checked state can't silently
        # carry over into a request for a mode (PPTX/images) that doesn't
        # support it.
        is_word = self.mode.currentData() == TranslationMode.WORD
        is_pdf = self.mode.currentData() == TranslationMode.PDF
        self.form.setRowVisible(self.ico_mode, is_word or is_pdf)
        if not (is_word or is_pdf):
            self.ico_mode.setChecked(False)
        # exclude_header/exclude_footer are PDF's own additional special
        # case (see their construction above) - same hide-the-row-and-
        # reset-on-mode-change treatment as ico_mode, just PDF-only.
        self.form.setRowVisible(self.exclude_header, is_pdf)
        self.form.setRowVisible(self.exclude_footer, is_pdf)
        if not is_pdf:
            self.exclude_header.setChecked(False)
            self.exclude_footer.setChecked(False)
        # ocr_engine/inpainting_backend are IMAGES-only (see their
        # construction above) - same hide-the-row treatment, no reset needed
        # since both combo boxes keep a harmless default (index 0) that is
        # simply unused for every other mode.
        self.form.setRowVisible(self.ocr_engine, is_images)
        self.form.setRowVisible(self.inpainting_backend, is_images)
        self._update_ocr_engine_hint()
        self._update_inpainting_backend_hint()
        self._invalidate_analysis()

    def _ocr_engine_changed(self) -> None:
        self._update_ocr_engine_hint()
        self._invalidate_analysis()

    def _update_ocr_engine_hint(self) -> None:
        # Mirrors _update_provider_credential_hint(): checked proactively so
        # an unavailable engine (e.g. Tesseract not installed) shows up here
        # instead of only as a wall of per-file failures at the end of a run
        # - see ui/document_job_common.py::ocr_engine_available() and the
        # matching fail-fast check in _start().
        #
        # Hint text is looked up PER ENGINE ("ocr_engine.{key}.unavailable",
        # 23.08.2026, added alongside google_vision/paddleocr) rather than
        # one shared "ocr_engine.unavailable" string - a single generic
        # message was fine while Tesseract was the only engine that could
        # ever BE unavailable, but "Tesseract wurde nicht gefunden..." is
        # actively wrong/confusing shown for an unavailable Google-Vision-
        # or PaddleOCR-selection. ui/i18n.py keeps "ocr_engine.unavailable"
        # itself only as the generic fallback Language.text() already falls
        # back to for any key with no dedicated translation.
        is_images = self.mode.currentData() == TranslationMode.IMAGES
        engine = self.ocr_engine.currentData()
        available = engine is None or ocr_engine_available(engine)
        self.ocr_engine_hint.setText(
            "" if available else self.language.text(f"ocr_engine.{engine}.unavailable")
        )
        self.ocr_engine_hint.setVisible(is_images and not available)

    def _inpainting_backend_changed(self) -> None:
        self._update_inpainting_backend_hint()
        self._invalidate_analysis()

    def _update_inpainting_backend_hint(self) -> None:
        # Same pattern as _update_ocr_engine_hint() (checked proactively,
        # never only failing deep inside a run) - relevant in practice
        # only for "gpu_inpainting" today: Box-Overlay/CvInpaintingBackend
        # are always available (see
        # ui/document_job_common.py::inpainting_backend_available()'s
        # docstring), so this hint stays empty/hidden for them.
        is_images = self.mode.currentData() == TranslationMode.IMAGES
        backend = self.inpainting_backend.currentData()
        available = backend is None or inpainting_backend_available(backend)
        hint_text = "" if available else self.language.text("inpainting_backend.unavailable")
        # 01.09.2026 (Michael: "GPU Schwelle auf den realistischen Wert
        # anheben. Mit dem Hinweis, dass es auch mit geringerem Wert
        # laufen kann, aber ohne Gewähr."): GPU_MIN_VRAM_GB no longer
        # hard-blocks gpu_inpainting_available() - a GPU below it still
        # counts as "available" above, so it needs its own, separate,
        # non-blocking warning here instead of the "unavailable" text.
        if available and backend == "gpu_inpainting":
            vram = gpu_vram_gb()
            if vram is not None and vram < GPU_MIN_VRAM_GB:
                hint_text = self.language.text(
                    "inpainting_backend.below_recommended_vram", vram_gb=vram, min_gb=GPU_MIN_VRAM_GB
                )
        self.inpainting_backend_hint.setText(hint_text)
        self.inpainting_backend_hint.setVisible(is_images and bool(hint_text))

    def _choose_sources(self) -> None:
        mode = self.mode.currentData()
        filters = {
            TranslationMode.PDF: "PDF (*.pdf)", TranslationMode.PRESENTATION: "PowerPoint (*.pptx)",
            TranslationMode.WORD: "Word (*.docx)", TranslationMode.IMAGES: "Bilder (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp)",
        }
        # Remembers the folder the LAST source selection was made from
        # (separate from "last_output_dir" below - a real user pointed out
        # these are often two different folders and both had to be
        # re-navigated to from scratch, every single run) as the starting
        # directory for the next file dialog.
        start_dir = str(self.settings.value("last_source_dir", "", type=str))
        if mode == TranslationMode.IMAGES:
            names, _ = QFileDialog.getOpenFileNames(self, self.language.text("dialog.choose_images"), start_dir, filters[mode])
        else:
            name, _ = QFileDialog.getOpenFileName(self, self.language.text("dialog.choose_document"), start_dir, filters[mode]); names = [name] if name else []
        if names:
            self.paths = tuple(Path(name) for name in names)
            self.source_label.setText("\n".join(path.name for path in self.paths))
            self.settings.setValue("last_source_dir", str(self.paths[0].parent))
            self._invalidate_analysis()

    def _request(self) -> TranslationRequest:
        terms = tuple(line.strip() for line in self.protected.toPlainText().splitlines() if line.strip())
        # currentData() round-trips a str/Enum through QVariant and comes
        # back as a plain str, not the original enum singleton - breaking
        # every "is"/"is not" comparison against TranslationMode/
        # EmbeddedImageMode downstream (this was the root cause of both a
        # mis-analyzed mode and the Start button silently no-op'ing).
        # Coerce back to the real enum here, at the UI boundary, so every
        # consumer of TranslationRequest can rely on true enum identity.
        return TranslationRequest(
            mode=TranslationMode(self.mode.currentData()), source_paths=self.paths, provider=self.provider.currentText(),
            source_language=self.source_lang.text().strip() or None,
            target_language=self.target_lang.text().strip(), embedded_images=EmbeddedImageMode(self.image_mode.currentData()),
            protected_terms=terms, ico_mode=self.ico_mode.isChecked(),
            exclude_header=self.exclude_header.isChecked(), exclude_footer=self.exclude_footer.isChecked(),
            ocr_engine=self.ocr_engine.currentData() or "tesseract",
            inpainting_backend=self.inpainting_backend.currentData() or "box_overlay",
        )

    def _analyze(self) -> None:
        request = self._request()
        errors = request.validation_errors()
        if errors:
            QMessageBox.warning(self, self.language.text("dialog.check_input"), "\n".join(errors)); return
        self.analyze.setEnabled(False); self.result.setText(self.language.text("analysis.running"))
        worker = AnalysisWorker(request, int(self.settings.value("max_chars", DEFAULT_MAX_CHARS_PER_RUN)))
        worker.signals.finished.connect(self._analysis_finished)
        worker.signals.failed.connect(self._analysis_failed)
        self.thread_pool.start(worker)

    def _analysis_finished(self, result: AnalysisResult) -> None:
        self.last_result = result; self.analyze.setEnabled(True); self.confirm.setEnabled(result.cost.within_run_limit)
        self._show_analysis(result)
        self._update_start_state()

    def _show_analysis(self, result: AnalysisResult) -> None:
        t = self.language.text
        warnings = "<br>".join(t(key) for key in result.warnings) or t("analysis.no_warnings")
        text = t(
            "analysis.summary", units=result.units, unit_label=t(result.unit_label),
            characters=result.text_characters, images=result.embedded_images,
            provider=result.cost.provider, usage=result.cost.month_usage, free=result.cost.free_tier,
            cost=result.cost.estimated_cost_usd, limit=result.cost.max_chars_per_run,
            limit_state=t("analysis.within" if result.cost.within_run_limit else "analysis.exceeded"),
            warnings=warnings,
        )
        cost = result.cost
        if cost.live_usage_available:
            if cost.live_character_limit is not None:
                remaining = max(cost.live_character_limit - cost.live_characters_used, 0)
                text += "<br>" + t(
                    "analysis.live_quota", used=cost.live_characters_used,
                    limit=cost.live_character_limit, remaining=remaining,
                )
            else:
                text += "<br>" + t("analysis.live_quota_unlimited", used=cost.live_characters_used)
        self.result.setText(text)

    def _analysis_failed(self, message: str) -> None:
        self.analyze.setEnabled(True); self.result.setText(self.language.text("analysis.failed"))
        QMessageBox.critical(self, self.language.text("dialog.analysis"), message)

    def _invalidate_analysis(self) -> None:
        if not hasattr(self, "confirm"): return
        self.last_result = None; self.confirm.setChecked(False); self.confirm.setEnabled(False)
        # Bug fixed here: this used to leave the previous analysis's numbers
        # (e.g. from a different mode or an earlier source file) visible on
        # screen even though last_result was already cleared - the cost
        # panel and the actual state could disagree. Always show
        # "analysis required" the moment the analysis is invalidated.
        self.result.setText(self.language.text("analysis.required"))
        self._update_start_state()

    def _start_blocked_reason(self) -> str | None:
        """Which single condition is currently keeping the start button
        disabled - None means it's ready. Shown to the user as visible text
        (not just a tooltip), so "why is it greyed out" is always answered
        on screen instead of requiring a hover or a guess.
        """
        if self._worker is not None:
            return "start.blocked_running"
        if self.mode.currentData() not in _EXECUTABLE_MODES:
            return "start.blocked_mode"
        if self.last_result is None:
            return "start.blocked_no_analysis"
        if not self.confirm.isChecked():
            return "start.blocked_not_confirmed"
        return None

    def _update_start_state(self) -> None:
        reason_key = self._start_blocked_reason()
        ready = reason_key is None
        self.start.setEnabled(ready)
        self.start.setToolTip(self.language.text("start.ready" if ready else reason_key))
        self.start_hint.setText("" if ready else self.language.text(reason_key))
        self.start_hint.setVisible(not ready)

    # -- Translation job (PPTX and DOCX share this flow) -------------------

    def _start(self) -> None:
        if self.mode.currentData() not in _EXECUTABLE_MODES or self.last_result is None:
            return
        request = self._request()
        errors = request.validation_errors()
        if errors:
            QMessageBox.warning(self, self.language.text("dialog.check_input"), "\n".join(errors)); return
        if credential_status(request.provider) == "credential.missing":
            # Fail fast, before asking for an output folder or spending any
            # API budget: without this check, a missing key only ever
            # surfaced as a wall of per-paragraph failures at the end of a
            # full run (and in the QA report), with no upfront warning.
            self._warn_missing_credential(request.provider)
            return

        is_images = request.mode == TranslationMode.IMAGES
        if is_images and not ocr_engine_available(request.ocr_engine):
            # Same fail-fast principle as the missing-credential check above
            # (and the same check _update_ocr_engine_hint() already shows
            # proactively next to the dropdown) - without this, an
            # unavailable OCR engine (e.g. Tesseract not installed) would
            # only ever surface as a wall of per-file failures at the end of
            # a full run.
            QMessageBox.warning(
                self,
                self.language.text("dialog.check_input"),
                self.language.text(f"ocr_engine.{request.ocr_engine}.unavailable"),
            )
            return
        if is_images and not inpainting_backend_available(request.inpainting_backend):
            # Same fail-fast principle, for the rewrite-backend choice (e.g.
            # "gpu_inpainting" selected without a qualifying CUDA GPU - see
            # ui/document_job_common.py::inpainting_backend_available()) -
            # relevant in practice only for GPU-Inpainting today, since
            # Box-Overlay/CvInpaintingBackend are always available.
            QMessageBox.warning(
                self, self.language.text("dialog.check_input"),
                self.language.text("inpainting_backend.unavailable"),
            )
            return

        # Own, separate remembered folder from "last_source_dir" above - see
        # that field's comment for why a real user asked for these two to
        # be tracked independently.
        directory = QFileDialog.getExistingDirectory(
            self, self.language.text("dialog.choose_output_dir"),
            str(self.settings.value("last_output_dir", "", type=str)),
        )
        if not directory:
            return
        self.settings.setValue("last_output_dir", directory)
        source = request.source_paths[0]
        output_dir = Path(directory)
        # IMAGES mode treats the chosen directory as the output directory
        # itself (one destination file per source, computed later inside
        # run_image_batch_job() via safe_destination() - see its docstring);
        # every other mode still computes one single destination file here.
        destination = output_dir if is_images else safe_destination(source, request.target_language, output_dir)

        cost = self.last_result.cost
        if is_images:
            summary = self.language.text(
                "start.confirm_summary_images", characters=cost.characters, provider=request.provider,
                cost=cost.estimated_cost_usd, count=len(request.source_paths), folder=str(output_dir),
            )
        else:
            summary = self.language.text(
                "start.confirm_summary", characters=cost.characters, provider=request.provider,
                cost=cost.estimated_cost_usd, destination=str(destination),
            )
        proceed = QMessageBox.question(self, self.language.text("dialog.confirm_run"), summary)
        if proceed != QMessageBox.Yes:
            return

        self._job_result = None
        self._job_total_paragraphs = 0
        self._job_last_location = ""
        self._job_last_stats = None
        # Needed later by _open_correction_dialog(), PDF-only: the source
        # path (never touched by the run itself - see run_pdf_job()'s
        # docstring) and the exact same header/footer exclusion the run
        # used, so a correction re-render reproduces the identical
        # DocumentTemplate/block list (see run_pdf_correction_job()'s
        # docstring for why this matters). Harmlessly set (but never read)
        # for IMAGES mode too, since _open_correction_dialog() only acts on
        # a PdfJobResult.
        self._job_source_path = source
        self._job_exclude_header = request.exclude_header
        self._job_exclude_footer = request.exclude_footer
        # IMAGES-only, mirrors the PDF-only fields above: needed by
        # _open_image_correction_dialog() to re-run the SAME
        # InpaintingBackend the original run used (see
        # run_image_correction_job()'s docstring). Harmlessly set (but
        # never read) for every other mode too, same as the PDF fields
        # above are for IMAGES.
        self._job_inpainting_backend = request.inpainting_backend
        # Mode-aware progress wording (see _update_job_status()): every
        # other mode counts paragraphs/pages/slides, IMAGES counts whole
        # files instead - "X von Y Absätzen" would be nonsensical for a
        # batch of image files.
        self._job_progress_unit_key = "job.progress_count_files" if is_images else "job.progress_count"
        self.open_folder_button.setVisible(False)
        self.open_report_button.setVisible(False)
        self.correct_translation_button.setVisible(False)
        self.job_progress.setVisible(True)
        # Indeterminate only for the brief moment before total_paragraph_count()
        # reports in (see _job_total) - no API call has happened yet at this
        # point, so there is nothing to show real progress against.
        # 28.08.2026 - a manually-driven sweep (_tick_busy_progress()), not
        # QProgressBar's native busy/marquee animation - see
        # _BUSY_SWEEP_MAX's own comment for why.
        self.job_progress.setTextVisible(False)
        self.job_progress.setRange(0, _BUSY_SWEEP_MAX)
        self.job_progress.setValue(0)
        self._busy_timer.start()
        self.job_status.setText(self.language.text("job.running"))
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)

        if is_images:
            # ImageTranslationWorker's shape differs deliberately from the
            # other three worker classes (multiple `sources` + one
            # `output_dir` rather than one `source`/`destination` pair - see
            # its own docstring in ui/workers.py), so it's built directly
            # here rather than folded into the worker_cls dict lookup below.
            worker = ImageTranslationWorker(
                list(request.source_paths), output_dir, request.provider, PRICING[request.provider],
                request.target_language, request.source_language, list(request.protected_terms),
                int(self.settings.value("max_chars", DEFAULT_MAX_CHARS_PER_RUN)),
                ocr_engine_name=request.ocr_engine, inpainting_backend_name=request.inpainting_backend,
            )
        else:
            # The other three worker classes share the exact same
            # constructor signature and TranslationSignals (see
            # ui/workers.py) - only the job function they call underneath
            # differs (run_presentation_job()/run_word_job()/run_pdf_job()),
            # so the rest of this method (signal wiring, progress/cancel/
            # result handling below) is identical for all of them. A dict
            # lookup (rather than an if/elif chain) so adding a mode to
            # _EXECUTABLE_MODES without adding it here raises a clear
            # KeyError instead of silently falling through to the wrong
            # worker, the way the old two-way "else" did before PDF was added.
            worker_cls = {
                TranslationMode.PRESENTATION: PresentationTranslationWorker,
                TranslationMode.WORD: WordTranslationWorker,
                TranslationMode.PDF: PdfTranslationWorker,
            }[request.mode]
            # ico_mode exists on both WordTranslationWorker and
            # PdfTranslationWorker (see their docstrings); exclude_header/
            # exclude_footer only on PdfTranslationWorker. Each is passed as
            # an extra kwarg only for the mode(s) that support it rather
            # than added to every constructor just to keep the call below
            # uniform.
            if request.mode == TranslationMode.WORD:
                extra_kwargs = {"ico_mode": request.ico_mode}
            elif request.mode == TranslationMode.PDF:
                extra_kwargs = {
                    "exclude_header": request.exclude_header, "exclude_footer": request.exclude_footer,
                    "ico_mode": request.ico_mode,
                }
            else:
                extra_kwargs = {}
            worker = worker_cls(
                source, destination, request.provider, PRICING[request.provider],
                request.target_language, request.source_language, list(request.protected_terms),
                int(self.settings.value("max_chars", DEFAULT_MAX_CHARS_PER_RUN)),
                **extra_kwargs,
            )
        worker.signals.progress.connect(self._job_progress)
        worker.signals.stats.connect(self._job_stats)
        worker.signals.total.connect(self._job_total)
        worker.signals.finished.connect(self._job_finished)
        worker.signals.failed.connect(self._job_failed)
        self._worker = worker
        # 27.08.2026 - real user report, Backlog.md 27.08.2026: "Während der
        # Verarbeitung ist in der App der Start Button weiterhin aktiv."
        # Root cause: _set_running(True) used to run BEFORE self._worker was
        # assigned above (right after the confirm dialog, long before the
        # worker itself was even constructed). _set_running() ends with
        # _update_start_state(), which re-enables/disables the Start button
        # via _start_blocked_reason()'s `self._worker is not None` check -
        # called while self._worker was still None (or a stale reference
        # from a PREVIOUS run already cleared to None), it never saw a
        # reason to block, so Start stayed enabled for the whole run. Moving
        # this call to AFTER self._worker is set (and right before the
        # worker actually starts, so nothing above can early-return without
        # having enabled the running state) fixes that at its actual cause.
        self._set_running(True)
        self.thread_pool.start(worker)

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()
            self.cancel_button.setEnabled(False)
            self.job_status.setText(self.language.text("job.cancel_requested"))

    def _job_total(self, total: int) -> None:
        # Switches the bar from indeterminate to determinate the moment the
        # real paragraph count is known (before the first API call) - fixes
        # a bug where the range's max was set to the CURRENT processed count
        # on every update, so the bar always showed 100% no matter how much
        # of the run actually remained.
        # 28.08.2026 - stop the manual busy-sweep (_tick_busy_progress(),
        # see _BUSY_SWEEP_MAX's own comment) and restore the percentage
        # text _start() hid for that phase - a real count is now known, so
        # there is real progress to show instead of the sweep.
        self._busy_timer.stop()
        self.job_progress.setTextVisible(True)
        self._job_total_paragraphs = total
        self.job_progress.setRange(0, max(total, 1))
        self.job_progress.setValue(0)

    def _tick_busy_progress(self) -> None:
        """Advances job_progress's value by _BUSY_SWEEP_STEP, wrapping back
        to 0 at the top - see _BUSY_SWEEP_MAX's own comment (__init__) for
        why this drives the indeterminate-phase sweep manually instead of
        relying on QProgressBar's native busy/marquee animation. Only ever
        ticking while _busy_timer is running, i.e. between _start() and
        whichever of _job_total()/_show_job_result()/_job_failed() stops it
        first."""
        value = self.job_progress.value() + _BUSY_SWEEP_STEP
        if value > self.job_progress.maximum():
            value = 0
        self.job_progress.setValue(value)

    def _job_progress(self, location: str) -> None:
        self._job_last_location = location
        self._update_job_status()

    def _job_stats(
        self,
        stats: PresentationTranslationStats | WordTranslationStats | PdfTranslationStats | ImageBatchStats,
    ) -> None:
        # .processed/.translated/.skipped/.failed are format-agnostic
        # aliases/fields present on all four stats types (see
        # PresentationTranslationStats,
        # pipeline.word.translate_document.TranslationStats,
        # pipeline.pdf.translate_pdf.PdfTranslationStats, and
        # ui.image_job.ImageBatchStats) - lets this method (and
        # _update_job_status()/_show_job_result() below) stay identical for
        # the PPTX, DOCX, PDF and IMAGES jobs instead of branching on type.
        self._job_last_stats = stats
        self.job_progress.setValue(min(stats.processed, self.job_progress.maximum()))
        self._update_job_status()

    def _update_job_status(self) -> None:
        t = self.language.text
        lines = []
        if self._job_last_location:
            lines.append(t("job.progress_prefix", location=self._job_last_location))
        stats = self._job_last_stats
        if stats is not None:
            total = max(self._job_total_paragraphs, stats.processed, 1)
            # _job_progress_unit_key is set in _start() per run - "job.
            # progress_count" (paragraphs/pages/slides) for every mode
            # except IMAGES ("job.progress_count_files", whole files).
            lines.append(t(self._job_progress_unit_key, processed=stats.processed, total=total))
            lines.append(t(
                "job.stats_summary", translated=stats.translated,
                skipped=stats.skipped, failed=stats.failed, chars=stats.chars_sent,
            ))
        if lines:
            self.job_status.setText("\n".join(lines))

    def _job_finished(
        self, result: PresentationJobResult | WordJobResult | PdfJobResult | ImageBatchJobResult
    ) -> None:
        self._job_result = result
        self._set_running(False)
        self._show_job_result(result)

    def _show_job_result(
        self, result: PresentationJobResult | WordJobResult | PdfJobResult | ImageBatchJobResult
    ) -> None:
        t = self.language.text
        stats = result.stats
        if isinstance(result, ImageBatchJobResult):
            # ImageBatchJobResult has no single output_path/qa_report_path
            # (one output file + one QA report PER image, all inside
            # output_dir - see run_image_batch_job()'s docstring), so it
            # gets its own summary string instead of "job.result_summary".
            text = t(
                "job.result_summary_images", files=stats.files_processed, translated=stats.translated,
                failed=stats.failed, chars=stats.chars_sent, output_dir=str(result.output_dir),
            )
        else:
            text = t(
                "job.result_summary", translated=stats.translated, skipped=stats.skipped,
                failed=stats.failed, chars=stats.chars_sent, output=str(result.output_path),
                report=str(result.qa_report_path),
            )
        if stats.cancelled:
            text += t("job.result_cancelled_suffix")
        if isinstance(result, PresentationJobResult):
            # Overflow-risk comparison only exists for PPTX (fixed-size text
            # boxes) - DOCX reflows automatically, so there is no equivalent
            # check to report here yet (see ui/word_job.py's docstring); the
            # DOCX QA report covers its own known risk (break-marker
            # anomalies) instead.
            text += "\n" + (
                t("job.overflow_none") if not result.overflow_regressions
                else t("job.overflow_count", count=len(result.overflow_regressions))
            )
        elif isinstance(result, PdfJobResult):
            # PDF's own risk profile (see ui/pdf_job.py's docstring):
            # insert_text() always makes text fit somewhere, but "fit" isn't
            # the same as "fit cleanly at the original size" - overflow_blocks
            # flags the ones worth a manual look, surfaced here the same way
            # PPTX surfaces its overflow-risk count.
            text += "\n" + (
                t("job.pdf_overflow_none") if not stats.overflow_blocks
                else t("job.pdf_overflow_count", count=stats.overflow_blocks)
            )
        self.job_status.setText(text)
        # 28.08.2026 - safety net: a run that fails/cancels before
        # _job_total() ever reports in (e.g. an error during the initial
        # OCR/analysis phase) would otherwise leave _busy_timer running
        # forever, silently ticking job_progress's value after the bar
        # itself is already hidden below.
        self._busy_timer.stop()
        self.job_progress.setVisible(False)
        self.cancel_button.setVisible(False)
        self.open_folder_button.setVisible(True)
        # ImageBatchJobResult has no single QA report file to open (one per
        # image, inside output_dir instead - see run_image_batch_job()'s
        # docstring) - "open folder" already gets the user there, so the
        # button that would open one specific report file is hidden for
        # this type.
        self.open_report_button.setVisible(not isinstance(result, ImageBatchJobResult))
        # PDF: only for runs that actually produced correctable blocks
        # (empty for e.g. an all-skipped or fully-cancelled run) - see
        # PdfTranslationStats.blocks' docstring. IMAGES: only if at least
        # ONE file in the batch produced correctable replacements - see
        # ImageTranslationStats.replacements' docstring; the dialog itself
        # (_open_image_correction_dialog()) is what lets the user pick
        # WHICH file, if there's more than one candidate.
        if isinstance(result, PdfJobResult):
            self.correct_translation_button.setVisible(bool(stats.blocks))
        elif isinstance(result, ImageBatchJobResult):
            self.correct_translation_button.setVisible(
                any(file_result.stats.replacements for file_result in stats.results)
            )
        else:
            self.correct_translation_button.setVisible(False)

    def _open_correction_dialog(self) -> None:
        if isinstance(self._job_result, PdfJobResult):
            self._open_pdf_correction_dialog(self._job_result)
        elif isinstance(self._job_result, ImageBatchJobResult):
            self._open_image_correction_dialog(self._job_result)

    def _open_pdf_correction_dialog(self, job_result: PdfJobResult) -> None:
        from ui.correction_dialog import PdfCorrectionDialog

        dialog = PdfCorrectionDialog(
            self.language,
            self._job_source_path,
            job_result.output_path,
            job_result.stats.blocks,
            exclude_header=self._job_exclude_header,
            exclude_footer=self._job_exclude_footer,
            parent=self,
        )
        dialog.exec()
        if dialog.last_result is not None and dialog.last_corrected_records is not None:
            # A correction run overwrote the same output/QA-report paths
            # (see run_pdf_correction_job()'s docstring) - refresh the job
            # panel's result so open_report_button reflects the corrected
            # file, not the stale pre-correction one. Deliberately reuse
            # last_corrected_records (NOT dialog.last_result.stats.blocks,
            # which apply_pdf_corrections() always leaves empty - see its
            # docstring) as the new baseline for `blocks`, so reopening the
            # correction dialog again starts from this round's edits
            # instead of silently discarding them back to the original
            # machine translation.
            corrected_result = dialog.last_result
            corrected_result.stats.blocks = dialog.last_corrected_records
            self._job_result = corrected_result
            self._show_job_result(corrected_result)

    def _open_image_correction_dialog(self, batch_result: ImageBatchJobResult) -> None:
        t = self.language.text
        candidates = [
            file_result for file_result in batch_result.stats.results if file_result.stats.replacements
        ]
        if not candidates:
            return
        if len(candidates) == 1:
            target = candidates[0]
        else:
            # More than one file in the batch has correctable regions -
            # ask which one, by output filename (unambiguous even if two
            # sources shared a stem, since safe_destination() already
            # made every output filename in the batch unique).
            names = [candidate.output_path.name for candidate in candidates]
            chosen_name, confirmed = QInputDialog.getItem(
                self, t("image_correction.choose_file_title"),
                t("image_correction.choose_file_label"), names, 0, False,
            )
            if not confirmed:
                return
            target = candidates[names.index(chosen_name)]

        from ui.image_correction_dialog import ImageCorrectionDialog

        # 26.08.2026 - see run_image_correction_job()'s matching
        # docstring: regions the original job recognized but never
        # translated (skipped, or a translatable=False layout obstacle)
        # must still be protected as collision obstacles when this dialog
        # re-renders, exactly like translate_image() itself protects them
        # on the FIRST run - identity-based (`is`), same style
        # translate_image.py's own obstacle_regions computation uses.
        translated_region_ids = {id(replacement.region) for replacement in target.stats.replacements}
        obstacle_regions = [
            region for region in target.stats.regions if id(region) not in translated_region_ids
        ]

        dialog = ImageCorrectionDialog(
            self.language,
            target.source_path,
            target.output_path,
            target.stats.replacements,
            inpainting_backend_name=self._job_inpainting_backend,
            obstacle_regions=obstacle_regions,
            parent=self,
        )
        dialog.exec()
        if dialog.last_result is not None and dialog.last_corrected_replacements is not None:
            # Mirrors _open_pdf_correction_dialog()'s identical reasoning:
            # a correction run overwrote this one file's output/QA-report
            # paths in place, so splice the corrected ImageJobResult back
            # into the batch result at the same position, keeping every
            # OTHER file's result untouched, then refresh the job panel.
            corrected_file_result = dialog.last_result
            corrected_file_result.stats.replacements = dialog.last_corrected_replacements
            # Identity (is), not equality: two ImageJobResult entries could
            # otherwise compare equal by field values, which .index() would
            # match against the wrong (e.g. first) one.
            index = next(i for i, r in enumerate(batch_result.stats.results) if r is target)
            batch_result.stats.results[index] = corrected_file_result
            self._job_result = batch_result
            self._show_job_result(batch_result)

    def _job_failed(self, message: str) -> None:
        log.error("Übersetzungslauf fehlgeschlagen: %s", message)
        self._set_running(False)
        # 28.08.2026 - same safety net as _show_job_result()'s: a failure
        # during the initial OCR/analysis phase (before _job_total() ever
        # reports in) would otherwise leave _busy_timer ticking forever.
        self._busy_timer.stop()
        self.job_progress.setVisible(False)
        self.cancel_button.setVisible(False)
        self.job_status.setText(self.language.text("job.idle"))
        QMessageBox.critical(self, self.language.text("job.failed_title"), message)

    def _set_running(self, running: bool) -> None:
        if not running:
            self._worker = None
        for widget in (
            self.mode, self.choose, self.analyze, self.confirm, self.settings_button, self.provider,
            self.ico_mode, self.ocr_engine, self.inpainting_backend, self.merge_button, self.word_merge_button,
        ):
            widget.setEnabled(not running)
        self._update_start_state()

    def _open_output_folder(self) -> None:
        if self._job_result is not None:
            # ImageBatchJobResult has an output_dir directly (no single
            # output_path to take .parent of - see its docstring in
            # ui/image_job.py); every other result type still has one
            # output_path whose parent folder is opened.
            path = (
                self._job_result.output_dir if isinstance(self._job_result, ImageBatchJobResult)
                else self._job_result.output_path.parent
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_qa_report(self) -> None:
        # ImageBatchJobResult has no single qa_report_path (one per image
        # instead - see run_image_batch_job()'s docstring); the button that
        # calls this is already hidden for that type in _show_job_result(),
        # this guard just avoids an AttributeError if it's ever invoked
        # anyway (e.g. a stray keyboard shortcut).
        if self._job_result is not None and not isinstance(self._job_result, ImageBatchJobResult):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._job_result.qa_report_path)))

    def _warn_missing_credential(self, provider: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(self.language.text("credentials.title"))
        box.setText(self.language.text("provider.missing_key_dialog", provider=provider))
        open_button = box.addButton(self.language.text("settings.button"), QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()
        if box.clickedButton() is open_button:
            self._open_settings(provider)

    def _open_settings(self, preselect_provider: str | None = None) -> None:
        dialog = SettingsDialog(self.settings, self.language, self, initial_provider=preselect_provider)
        if dialog.exec(): self.provider.setCurrentText(str(self.settings.value("provider", "deepl"))); self._invalidate_analysis()
        # A key may have been saved even if the dialog was cancelled
        # afterwards (Save key/Cancel are independent), so always refresh.
        self._update_provider_credential_hint()

    def _open_merge_dialog(self) -> None:
        # Modal (exec(), like SettingsDialog above) - simplest choice for a
        # v1 that runs no more than one merge job at a time anyway (see
        # ui/merge_dialog.py); nothing stops this window's own translation
        # flow from being made to run alongside it later if that turns out
        # to matter to Michael in practice.
        dialog = MergeDialog(self.language, self.settings, self)
        dialog.exec()

    def _open_word_merge_dialog(self) -> None:
        # DOCX-Gegenstück zu _open_merge_dialog() oben (01.09.2026) - siehe
        # dort für die Begründung (modal, ein Lauf zur Zeit).
        dialog = WordMergeDialog(self.language, self.settings, self)
        dialog.exec()


def apply_explicit_palette(app: QApplication) -> None:
    """Force an explicit, contrast-tested palette (see ui/theme.py) instead
    of trusting the desktop environment's own Qt style integration for
    every color. Reported bug: with a Linux dark-mode desktop active,
    QLineEdit/QTextEdit/QCheckBox text and a disabled Start button were all
    effectively unreadable/indistinguishable - that desktop's Qt palette
    integration left too little contrast for this app's widgets. Detects
    dark-vs-light from the *inherited* palette before overriding it, so a
    light-mode desktop is left alone rather than being forced dark.
    """
    app.setStyle("Fusion")
    is_dark = app.palette().color(QPalette.Window).lightness() < 128
    colors = palette_colors(is_dark)

    def rgb(name: str) -> QColor:
        return QColor(*colors[name])

    palette = QPalette()
    palette.setColor(QPalette.Window, rgb("window"))
    palette.setColor(QPalette.WindowText, rgb("window_text"))
    palette.setColor(QPalette.Base, rgb("base"))
    palette.setColor(QPalette.AlternateBase, rgb("window"))
    palette.setColor(QPalette.Text, rgb("text"))
    palette.setColor(QPalette.Button, rgb("button"))
    palette.setColor(QPalette.ButtonText, rgb("button_text"))
    palette.setColor(QPalette.ToolTipBase, rgb("base"))
    palette.setColor(QPalette.ToolTipText, rgb("text"))
    palette.setColor(QPalette.Highlight, rgb("highlight"))
    palette.setColor(QPalette.HighlightedText, rgb("highlighted_text"))
    palette.setColor(QPalette.PlaceholderText, rgb("placeholder_text"))
    # The Disabled group is the one that actually matters for "why did
    # clicking Start seem to do nothing": without it, a disabled button can
    # render almost identically to an enabled one on some themes.
    palette.setColor(QPalette.Disabled, QPalette.Text, rgb("disabled_text"))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, rgb("disabled_text"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, rgb("disabled_text"))
    palette.setColor(QPalette.Disabled, QPalette.Button, rgb("disabled_button"))
    palette.setColor(QPalette.Disabled, QPalette.Base, rgb("disabled_button"))
    app.setPalette(palette)
    # 26.08.2026 (Michael: "Das UI gefällt mir so gar nicht [...] Unseres
    # schaut so staubig, technisch und trocken aus.") - QSS layered ON TOP
    # of the QPalette above, not instead of it (see ui/theme.py's
    # build_stylesheet() docstring for why both still coexist). is_dark was
    # already computed above from the INHERITED palette, before this
    # function overwrote it - build_stylesheet() must use that same
    # light-vs-dark decision, not re-derive it from the now-overwritten
    # app.palette().
    app.setStyleSheet(build_stylesheet(is_dark))


def main() -> int:
    # 02.09.2026 (Michael: "Haben wir kein Log für genau solche Fälle?",
    # nach einem Google-Drive-Fehler, der sich per Screenshot nur mühsam
    # mitteilen ließ) - vor allem anderen aufrufen, damit auch ein Fehler
    # ganz am Anfang von MainWindow.__init__() noch in der Datei landet.
    configure_logging()
    app = QApplication(sys.argv)
    apply_explicit_palette(app)
    window = MainWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    _exit_code = main()
    # 02.09.2026 (Michael: "Es scheint das die App nach Schliessen aller
    # offener Fenster den Prozess in der Shell nicht sauber beendet.") -
    # app.exec() above has already returned, meaning every window is closed
    # and MainWindow.closeEvent() has already run (settings persisted,
    # see there) - but a background QThreadPool task started earlier
    # (translation job, Drive-Ordnersuche connect/search, update check/
    # apply - see the various QThreadPool.globalInstance().start(...)
    # call sites across ui/) can still be running or, worse, permanently
    # blocked in a native call with no timeout (the "Mit Google
    # verbinden" bug fixed the same day in pipeline/drive_auth.py -
    # unbounded before that fix, still theoretically possible for a
    # future worker). A normal `raise SystemExit(...)` waits for Qt's
    # global QThreadPool to finish every such task before the process can
    # actually exit (Qt's own documented QThreadPool destructor
    # behaviour) - exactly the "process doesn't terminate cleanly"
    # symptom. os._exit() terminates the process immediately at the OS
    # level, without waiting for any thread - safe here because nothing
    # this app cares about is deferred to normal interpreter shutdown:
    # form state and every credential are already written synchronously
    # at the moment they change (QSettings.setValue()/self.settings.sync()
    # in closeEvent(), OS keyring writes in pipeline/credentials.py's
    # set_api_key() at the moment "speichern" is clicked), not batched up
    # for process exit.
    os._exit(_exit_code)
