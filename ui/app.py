"""First desktop UI slice for explicit document modes and cost analysis."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from pipeline.pdf.translate_pdf import PdfTranslationStats
from pipeline.presentation.translate_presentation import PresentationTranslationStats
from pipeline.translation.cost_control import DEFAULT_MAX_CHARS_PER_RUN
from pipeline.word.translate_document import TranslationStats as WordTranslationStats
from ui.analysis import PRICING
from ui.i18n import LOCALES, LanguageManager
from ui.models import AnalysisResult, EmbeddedImageMode, TranslationMode, TranslationRequest
from ui.pdf_job import PdfJobResult
from ui.pptx_job import PresentationJobResult, safe_destination
from ui.settings import credential_status, save_credential
from ui.theme import palette_colors
from ui.word_job import WordJobResult
from ui.workers import (
    AnalysisWorker,
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

# PPTX (RoadMap.md Phase 1), DOCX (Phase 2/Word) and now the direct PDF path
# (Phase 2/PDF) are all connected to the start button. PDF's prerequisite
# quality issue (the redact/insert duplicate-text bug) is fixed and
# regression-tested (see tests/test_pdf_redact_insert_collision.py); a
# number of other, narrower PDF quality items remain open and are
# catalogued in every PDF job's QA report instead of being silently
# ignored - see ui/pdf_job.py.
_EXECUTABLE_MODES = {TranslationMode.PRESENTATION, TranslationMode.WORD, TranslationMode.PDF}


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
        # document type (see RoadMap.md): only enabled/visible for Word mode
        # today, wired through TranslationRequest.ico_mode -> ui/word_job.py
        # -> DocxEngine.open(). Never checked/inferred automatically -
        # see _mode_changed() and DocxEngine.open()'s docstring for why.
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

        self.form = QFormLayout()
        self.form_labels = [QLabel() for _ in range(10)]
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

        self.job_box = QGroupBox()
        job_layout = QVBoxLayout(self.job_box)
        job_layout.addWidget(self.job_status)
        job_layout.addWidget(self.job_progress)
        job_actions = QHBoxLayout()
        job_actions.addWidget(self.cancel_button)
        job_actions.addWidget(self.open_folder_button)
        job_actions.addWidget(self.open_report_button)
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
        self._mode_changed()

    def retranslate(self) -> None:
        t = self.language.text
        self.setWindowTitle(t("app.title"))
        for index, mode in enumerate(MODE_KEYS): self.mode.setItemText(index, t(MODE_KEYS[mode]))
        for index, key in enumerate(("image.none", "image.selected", "image.all")): self.image_mode.setItemText(index, t(key))
        for label, key in zip(self.form_labels, ("field.mode", "field.source", "field.images", "field.provider", "field.source_language", "field.target_language", "field.protected_terms", "field.ico_mode", "field.exclude_header", "field.exclude_footer")):
            label.setText(t(key))
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
        self.settings_button.setText(t("settings.button"))
        if self.last_result is None: self.result.setText(t("analysis.required"))
        else: self._show_analysis(self.last_result)
        if self._worker is None and self._job_result is None:
            self.job_status.setText(t("job.idle"))
        elif self._job_result is not None:
            self._show_job_result(self._job_result)
        self._update_provider_credential_hint()
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
        # ico_mode is a Word-only special case today (see RoadMap.md) - hide
        # the whole row rather than just disabling it, and force it back off
        # when leaving Word mode so a stale checked state can't silently
        # carry over into a request for a mode that doesn't support it.
        is_word = self.mode.currentData() == TranslationMode.WORD
        self.form.setRowVisible(self.ico_mode, is_word)
        if not is_word:
            self.ico_mode.setChecked(False)
        # exclude_header/exclude_footer are the PDF-mode equivalent special
        # case (see their construction above) - same hide-the-row-and-
        # reset-on-mode-change treatment as ico_mode, just for PDF instead
        # of Word.
        is_pdf = self.mode.currentData() == TranslationMode.PDF
        self.form.setRowVisible(self.exclude_header, is_pdf)
        self.form.setRowVisible(self.exclude_footer, is_pdf)
        if not is_pdf:
            self.exclude_header.setChecked(False)
            self.exclude_footer.setChecked(False)
        self._invalidate_analysis()

    def _choose_sources(self) -> None:
        mode = self.mode.currentData()
        filters = {
            TranslationMode.PDF: "PDF (*.pdf)", TranslationMode.PRESENTATION: "PowerPoint (*.pptx)",
            TranslationMode.WORD: "Word (*.docx)", TranslationMode.IMAGES: "Bilder (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp)",
        }
        if mode == TranslationMode.IMAGES:
            names, _ = QFileDialog.getOpenFileNames(self, self.language.text("dialog.choose_images"), "", filters[mode])
        else:
            name, _ = QFileDialog.getOpenFileName(self, self.language.text("dialog.choose_document"), "", filters[mode]); names = [name] if name else []
        if names:
            self.paths = tuple(Path(name) for name in names)
            self.source_label.setText("\n".join(path.name for path in self.paths))
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

        directory = QFileDialog.getExistingDirectory(self, self.language.text("dialog.choose_output_dir"))
        if not directory:
            return
        source = request.source_paths[0]
        destination = safe_destination(source, request.target_language, Path(directory))

        cost = self.last_result.cost
        proceed = QMessageBox.question(
            self, self.language.text("dialog.confirm_run"),
            self.language.text(
                "start.confirm_summary", characters=cost.characters, provider=request.provider,
                cost=cost.estimated_cost_usd, destination=str(destination),
            ),
        )
        if proceed != QMessageBox.Yes:
            return

        self._job_result = None
        self._job_total_paragraphs = 0
        self._job_last_location = ""
        self._job_last_stats = None
        self.open_folder_button.setVisible(False)
        self.open_report_button.setVisible(False)
        self.job_progress.setVisible(True)
        # Indeterminate only for the brief moment before total_paragraph_count()
        # reports in (see _job_total) - no API call has happened yet at this
        # point, so there is nothing to show real progress against.
        self.job_progress.setRange(0, 0)
        self.job_status.setText(self.language.text("job.running"))
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self._set_running(True)

        # All three worker classes share the exact same constructor
        # signature and TranslationSignals (see ui/workers.py) - only the
        # job function they call underneath differs (run_presentation_job()/
        # run_word_job()/run_pdf_job()), so the rest of this method (signal
        # wiring, progress/cancel/result handling below) is identical for
        # all three modes. A dict lookup (rather than an if/elif chain) so
        # adding a mode to _EXECUTABLE_MODES without adding it here raises a
        # clear KeyError instead of silently falling through to the wrong
        # worker, the way the old two-way "else" did before PDF was added.
        worker_cls = {
            TranslationMode.PRESENTATION: PresentationTranslationWorker,
            TranslationMode.WORD: WordTranslationWorker,
            TranslationMode.PDF: PdfTranslationWorker,
        }[request.mode]
        # ico_mode only exists on WordTranslationWorker, exclude_header/
        # exclude_footer only on PdfTranslationWorker (see their
        # docstrings) - each is passed as an extra kwarg only for its own
        # mode rather than added to every constructor just to keep the
        # call below uniform.
        if request.mode == TranslationMode.WORD:
            extra_kwargs = {"ico_mode": request.ico_mode}
        elif request.mode == TranslationMode.PDF:
            extra_kwargs = {"exclude_header": request.exclude_header, "exclude_footer": request.exclude_footer}
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
        self, stats: PresentationTranslationStats | WordTranslationStats | PdfTranslationStats
    ) -> None:
        # .processed/.translated/.skipped/.failed are format-agnostic
        # aliases/fields present on all three stats types (see
        # PresentationTranslationStats,
        # pipeline.word.translate_document.TranslationStats, and
        # pipeline.pdf.translate_pdf.PdfTranslationStats) - lets this
        # method (and _update_job_status()/_show_job_result() below) stay
        # identical for the PPTX, DOCX and PDF jobs instead of branching on type.
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
            lines.append(t("job.progress_count", processed=stats.processed, total=total))
            lines.append(t(
                "job.stats_summary", translated=stats.translated,
                skipped=stats.skipped, failed=stats.failed, chars=stats.chars_sent,
            ))
        if lines:
            self.job_status.setText("\n".join(lines))

    def _job_finished(self, result: PresentationJobResult | WordJobResult | PdfJobResult) -> None:
        self._job_result = result
        self._set_running(False)
        self._show_job_result(result)

    def _show_job_result(self, result: PresentationJobResult | WordJobResult | PdfJobResult) -> None:
        t = self.language.text
        stats = result.stats
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
        self.open_report_button.setVisible(True)

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
        for widget in (self.mode, self.choose, self.analyze, self.confirm, self.settings_button, self.provider, self.ico_mode):
            widget.setEnabled(not running)
        self._update_start_state()

    def _open_output_folder(self) -> None:
        if self._job_result is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._job_result.output_path.parent)))

    def _open_qa_report(self) -> None:
        if self._job_result is not None:
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
