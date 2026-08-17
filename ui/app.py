"""First desktop UI slice for explicit document modes and cost analysis."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from pipeline.translation.cost_control import DEFAULT_MAX_CHARS_PER_RUN
from ui.i18n import LOCALES, LanguageManager
from ui.models import AnalysisResult, EmbeddedImageMode, TranslationMode, TranslationRequest
from ui.settings import credential_status, save_credential
from ui.workers import AnalysisWorker


MODE_KEYS = {
    TranslationMode.PDF: "mode.pdf",
    TranslationMode.PRESENTATION: "mode.presentation",
    TranslationMode.WORD: "mode.word",
    TranslationMode.IMAGES: "mode.images",
}


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, language: LanguageManager, parent: QWidget | None = None) -> None:
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
        self.provider.setCurrentText(str(settings.value("provider", "deepl")))
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
        self.resize(880, 680)
        self.settings = QSettings("PDF-Translator", "Document Translator")
        self.language = LanguageManager(str(self.settings.value("language", "de")))
        self.thread_pool = QThreadPool.globalInstance()
        self.paths: tuple[Path, ...] = ()
        self.last_result: AnalysisResult | None = None

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
        self.source_lang = QLineEdit()
        self.target_lang = QLineEdit("DE")
        self.protected = QTextEdit()
        self.protected.setMaximumHeight(90)

        self.form = QFormLayout()
        self.form_labels = [QLabel() for _ in range(7)]
        self.form.addRow(self.form_labels[0], self.mode)
        source_row = QHBoxLayout(); source_row.addWidget(self.source_label, 1); source_row.addWidget(self.choose)
        self.form.addRow(self.form_labels[1], source_row)
        for label, field in zip(self.form_labels[2:], (self.image_mode, self.provider, self.source_lang, self.target_lang, self.protected)):
            self.form.addRow(label, field)

        self.analyze = QPushButton()
        self.analyze.clicked.connect(self._analyze)
        self.confirm = QCheckBox()
        self.confirm.setEnabled(False)
        self.confirm.toggled.connect(self._update_start_state)
        self.start = QPushButton()
        self.start.setEnabled(False)
        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setStyleSheet("padding: 10px")

        self.cost_box = QGroupBox()
        cost_layout = QVBoxLayout(self.cost_box)
        cost_layout.addWidget(self.result)
        cost_layout.addWidget(self.confirm)
        actions = QHBoxLayout(); actions.addWidget(self.analyze); actions.addWidget(self.start)
        cost_layout.addLayout(actions)

        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self._open_settings)
        root = QVBoxLayout()
        root.addLayout(self.form)
        root.addWidget(self.cost_box)
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
        for label, key in zip(self.form_labels, ("field.mode", "field.source", "field.images", "field.provider", "field.source_language", "field.target_language", "field.protected_terms")):
            label.setText(t(key))
        if not self.paths: self.source_label.setText(t("source.none"))
        self.choose.setText(t("source.choose"))
        self.source_lang.setPlaceholderText(t("source_language.placeholder"))
        self.protected.setPlaceholderText(t("protected.placeholder"))
        self.cost_box.setTitle(t("analysis.group"))
        self.analyze.setText(t("analysis.button"))
        self.confirm.setText(t("analysis.checked"))
        self.start.setText(t("start.button")); self.start.setToolTip(t("start.pending"))
        self.settings_button.setText(t("settings.button"))
        if self.last_result is None: self.result.setText(t("analysis.required"))
        else: self._show_analysis(self.last_result)

    def _mode_changed(self) -> None:
        is_images = self.mode.currentData() is TranslationMode.IMAGES
        self.image_mode.setEnabled(not is_images)
        if is_images:
            self.image_mode.setCurrentIndex(2)
        self._invalidate_analysis()

    def _choose_sources(self) -> None:
        mode = self.mode.currentData()
        filters = {
            TranslationMode.PDF: "PDF (*.pdf)", TranslationMode.PRESENTATION: "PowerPoint (*.pptx)",
            TranslationMode.WORD: "Word (*.docx)", TranslationMode.IMAGES: "Bilder (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp)",
        }
        if mode is TranslationMode.IMAGES:
            names, _ = QFileDialog.getOpenFileNames(self, self.language.text("dialog.choose_images"), "", filters[mode])
        else:
            name, _ = QFileDialog.getOpenFileName(self, self.language.text("dialog.choose_document"), "", filters[mode]); names = [name] if name else []
        if names:
            self.paths = tuple(Path(name) for name in names)
            self.source_label.setText("\n".join(path.name for path in self.paths))
            self._invalidate_analysis()

    def _request(self) -> TranslationRequest:
        terms = tuple(line.strip() for line in self.protected.toPlainText().splitlines() if line.strip())
        return TranslationRequest(
            mode=self.mode.currentData(), source_paths=self.paths, provider=self.provider.currentText(),
            source_language=self.source_lang.text().strip() or None,
            target_language=self.target_lang.text().strip(), embedded_images=self.image_mode.currentData(),
            protected_terms=terms,
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
        self.result.setText(t(
            "analysis.summary", units=result.units, unit_label=t(result.unit_label),
            characters=result.text_characters, images=result.embedded_images,
            usage=result.cost.month_usage, free=result.cost.free_tier,
            cost=result.cost.estimated_cost_usd, limit=result.cost.max_chars_per_run,
            limit_state=t("analysis.within" if result.cost.within_run_limit else "analysis.exceeded"),
            warnings=warnings,
        ))

    def _analysis_failed(self, message: str) -> None:
        self.analyze.setEnabled(True); self.result.setText(self.language.text("analysis.failed"))
        QMessageBox.critical(self, self.language.text("dialog.analysis"), message)

    def _invalidate_analysis(self) -> None:
        if not hasattr(self, "confirm"): return
        self.last_result = None; self.confirm.setChecked(False); self.confirm.setEnabled(False); self.start.setEnabled(False)

    def _update_start_state(self) -> None:
        # Translation execution is intentionally not connected in this first UI slice.
        self.start.setEnabled(False)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.language, self)
        if dialog.exec(): self.provider.setCurrentText(str(self.settings.value("provider", "deepl"))); self._invalidate_analysis()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
