"""First desktop UI slice for explicit document modes and cost analysis."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

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
from ui.models import AnalysisResult, EmbeddedImageMode, TranslationMode, TranslationRequest
from ui.pdf_job import PdfJobResult
from ui.pptx_job import PresentationJobResult
from ui.settings import credential_status, save_credential
from ui.theme import palette_colors
from ui.word_job import WordJobResult
from ui.workers import (
    AnalysisWorker,
    ImageTranslationWorker,
    PdfTranslationWorker,
    PresentationTranslationWorker,
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

        self.form = QFormLayout()
        self.form_labels = [QLabel() for _ in range(6)]
        for label, field in zip(self.form_labels, (self.locale, self.provider, self.status, self.secret, self.target, self.max_chars)):
            self.form.addRow(label, field)
        self.form.addRow("", self.save_key)
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
        self.note.setText(t("settings.session_note"))

    def _refresh_status(self) -> None:
        self.status.setText(self.language.text(credential_status(self.provider.currentText())))

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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(880, 760)
        self.settings = QSettings("PDF-Translator", "Document Translator")
        self.language = LanguageManager(str(self.settings.value("language", "de")))
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

        self.mode = QComboBox()
        for mode in MODE_KEYS:
            self.mode.addItem("", mode)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        self.choose = QPushButton()
        self.choose.clicked.connect(self._choose_sources)

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
        root = QVBoxLayout()
        root.addLayout(self.form)
        root.addWidget(self.cost_box)
        root.addWidget(self.job_box)
        root.addWidget(self.settings_button, alignment=Qt.AlignRight)
        root.addStretch()
        widget = QWidget(); widget.setLayout(root); self.setCentralWidget(widget)
        self.language.changed.connect(self.retranslate)
        self.retranslate()
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
        super().closeEvent(event)

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("app.title"))
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
        self.inpainting_backend_hint.setText(
            "" if available else self.language.text("inpainting_backend.unavailable")
        )
        self.inpainting_backend_hint.setVisible(is_images and not available)

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
        self.job_progress.setRange(0, 0)
        self.job_status.setText(self.language.text("job.running"))
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self._set_running(True)

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
        self._job_total_paragraphs = total
        self.job_progress.setRange(0, max(total, 1))
        self.job_progress.setValue(0)

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

        dialog = ImageCorrectionDialog(
            self.language,
            target.source_path,
            target.output_path,
            target.stats.replacements,
            inpainting_backend_name=self._job_inpainting_backend,
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
        self.job_progress.setVisible(False)
        self.cancel_button.setVisible(False)
        self.job_status.setText(self.language.text("job.idle"))
        QMessageBox.critical(self, self.language.text("job.failed_title"), message)

    def _set_running(self, running: bool) -> None:
        if not running:
            self._worker = None
        for widget in (
            self.mode, self.choose, self.analyze, self.confirm, self.settings_button, self.provider,
            self.ico_mode, self.ocr_engine, self.inpainting_backend,
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


def main() -> int:
    app = QApplication(sys.argv)
    apply_explicit_palette(app)
    window = MainWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
