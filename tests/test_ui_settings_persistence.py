"""Regression coverage for ui/app.py's persisted-settings feature
(Backlog.md 21.08.2026): a real user reported having to retype the
source/target language, protected terms and every dropdown choice again on
every single run, and having to re-navigate to the same source/output
folders from scratch every time - even though "Original" and "Output" are
often two different folders.

MainWindow._restore_form_state()/_persist_form_state() (closeEvent()) cover
the form fields; _choose_sources()/_start() cover the two folder paths
(last_source_dir/last_output_dir) independently.

Every test here relies on tests/conftest.py's autouse _isolated_qsettings
fixture, which redirects QSettings("PDF-Translator", "Document Translator")
- the OS-native, really-on-disk store MainWindow persists into - to a fresh
per-test temp directory. Without it, this file's own window.close() calls
would write to the real, shared settings location and leak state into
every OTHER test file's MainWindow() (see that fixture's docstring for the
actual regression this caused during development).
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import ui.app as app_module
from ui.analysis import analyze_request
from ui.app import MainWindow
from ui.models import EmbeddedImageMode, TranslationMode, TranslationRequest

_REPRESENTATIVE_PDF = Path(__file__).parent / "fixtures" / "representative.pdf"


def _real_settings() -> QSettings:
    """The exact same QSettings(org, app) construction ui/app.py itself
    uses - redirected to this test's isolated temp directory by
    tests/conftest.py's autouse fixture, so this reads/writes the same
    file a MainWindow() built in the same test would."""
    return QSettings("PDF-Translator", "Document Translator")


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


def test_closing_and_reopening_restores_form_fields(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(window.mode.findData(TranslationMode.PDF))
        window.source_lang.setText("EN")
        window.target_lang.setText("FR")
        window.protected.setPlainText("Anthropic\nClaude")
        window.exclude_header.setChecked(True)
        window.exclude_footer.setChecked(True)
    finally:
        window.close()

    reopened = MainWindow()
    reopened.show()
    try:
        assert reopened.mode.currentData() == TranslationMode.PDF
        assert reopened.source_lang.text() == "EN"
        assert reopened.target_lang.text() == "FR"
        assert reopened.protected.toPlainText() == "Anthropic\nClaude"
        assert reopened.exclude_header.isChecked() is True
        assert reopened.exclude_footer.isChecked() is True
    finally:
        reopened.close()


def test_provider_choice_in_the_main_form_survives_a_restart(qapp: QApplication) -> None:
    """03.09.2026 regression (Michael: "Der Übersetzungsanbieter wird sich
    nicht gemerkt. Geht verloren nach Neustart."): self.provider read the
    "provider" settings key on construction, but a selection made directly
    in the main form's own dropdown was never written back anywhere -
    only going through the separate Settings dialog (which has its own
    save-on-accept for the same key) ever persisted it. Uses the exact
    same "provider" key both write and read from, independent of
    form.*-prefixed fields covered by the other tests in this file."""
    window = MainWindow()
    window.show()
    try:
        assert window.provider.currentText() == "deepl"  # the shipped default
        window.provider.setCurrentText("google")
    finally:
        window.close()

    reopened = MainWindow()
    reopened.show()
    try:
        assert reopened.provider.currentText() == "google"
    finally:
        reopened.close()


def test_restoring_an_old_mode_specific_flag_does_not_survive_a_mode_that_no_longer_supports_it(
    qapp: QApplication,
) -> None:
    """ico_mode is only valid for Word/PDF (see MainWindow._mode_changed())
    - persisting it while on PDF, then reopening with a persisted mode that
    doesn't support it (Presentation), must not resurrect a stale checked
    state ui/app.py's own reset logic would otherwise have cleared."""
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(window.mode.findData(TranslationMode.PDF))
        window.ico_mode.setChecked(True)
    finally:
        window.close()

    # Simulate having since switched (and closed again) on Presentation,
    # which _mode_changed() forces ico_mode back off for.
    settings = _real_settings()
    settings.setValue("form.mode", TranslationMode.PRESENTATION.value)
    settings.setValue("form.ico_mode", True)  # a stale value that must be ignored
    settings.sync()

    reopened = MainWindow()
    reopened.show()
    try:
        assert reopened.mode.currentData() == TranslationMode.PRESENTATION
        assert reopened.ico_mode.isChecked() is False
        assert not reopened.form.isRowVisible(reopened.ico_mode)
    finally:
        reopened.close()


def test_image_mode_and_engine_dropdowns_round_trip(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.image_mode.setCurrentIndex(window.image_mode.findData(EmbeddedImageMode.SELECTED))
        window.ocr_engine.setCurrentIndex(window.ocr_engine.count() - 1)
        window.inpainting_backend.setCurrentIndex(window.inpainting_backend.count() - 1)
        expected_ocr = window.ocr_engine.currentData()
        expected_inpainting = window.inpainting_backend.currentData()
    finally:
        window.close()

    reopened = MainWindow()
    reopened.show()
    try:
        assert reopened.image_mode.currentData() == EmbeddedImageMode.SELECTED
        assert reopened.ocr_engine.currentData() == expected_ocr
        assert reopened.inpainting_backend.currentData() == expected_inpainting
    finally:
        reopened.close()


def test_a_fresh_installation_with_no_persisted_settings_keeps_the_original_defaults(
    qapp: QApplication,
) -> None:
    """No settings file has been written yet - _restore_form_state() must
    leave every field at its normal hard-coded default, not blow up or
    silently blank something out."""
    window = MainWindow()
    window.show()
    try:
        assert window.target_lang.text() == "DE"
        assert window.source_lang.text() == ""
        assert window.protected.toPlainText() == ""
        assert window.ico_mode.isChecked() is False
    finally:
        window.close()


def test_choosing_a_source_remembers_its_folder_and_offers_it_next_time(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard for "Auch die Ordner Pfade für Original und Output
    separat. Es können ja zwei verschiedene sein.": last_source_dir must be
    persisted independently of last_output_dir (covered separately below),
    and offered back as the starting directory on the NEXT file dialog."""
    source_dir = tmp_path / "originals"
    source_dir.mkdir()
    source_file = source_dir / "input.pdf"
    source_file.write_bytes(_REPRESENTATIVE_PDF.read_bytes())

    seen_start_dirs: list[str] = []

    def fake_get_open_file_name(_parent, _title, start_dir, _filter):
        seen_start_dirs.append(start_dir)
        return str(source_file), ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_get_open_file_name)

    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(window.mode.findData(TranslationMode.PDF))
        window._choose_sources()
        assert seen_start_dirs == [""]  # nothing persisted yet on the very first call
        assert window.settings.value("last_source_dir", "", type=str) == str(source_dir)

        # A second selection must be offered the just-remembered folder as
        # its starting directory - proof it was actually READ back, not
        # just recorded.
        window._choose_sources()
        assert seen_start_dirs[-1] == str(source_dir)
    finally:
        window.close()


def test_start_output_dir_is_remembered_independently_of_source_dir(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counterpart to the source-dir test above - last_output_dir must be
    its own, separately tracked setting, offered as the starting directory
    for the output-folder picker in _start()."""
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    started: list[object] = []
    monkeypatch.setattr(QThreadPool, "start", lambda self, worker: started.append(worker))

    output_dir = tmp_path / "results"
    output_dir.mkdir()
    seen_start_dirs: list[str] = []

    def fake_get_existing_directory(_parent, _title, start_dir):
        seen_start_dirs.append(start_dir)
        return str(output_dir)

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake_get_existing_directory)

    fixture = tmp_path / "input.pdf"
    fixture.write_bytes(_REPRESENTATIVE_PDF.read_bytes())

    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(window.mode.findData(TranslationMode.PDF))
        window.paths = (fixture,)
        window.provider.setCurrentText("deepl")
        window.last_result = analyze_request(TranslationRequest(TranslationMode.PDF, (fixture,), provider="deepl"))
        window.confirm.setEnabled(True)
        window.confirm.setChecked(True)

        window._start()

        assert len(started) == 1
        assert seen_start_dirs == [""]  # nothing persisted yet on the first run
        assert window.settings.value("last_output_dir", "", type=str) == str(output_dir)
        # last_source_dir must be entirely untouched by an output-folder
        # pick - the two are independent settings.
        assert window.settings.value("last_source_dir", "", type=str) == ""
    finally:
        window.close()
