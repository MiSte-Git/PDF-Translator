"""Regression guard: picking a provider with no API key configured used to
give no indication anywhere in the UI - the only place it ever showed up
was a wall of per-paragraph failures in the QA report after a full run
already happened. Two things are checked here:

- Switching the provider combo box immediately shows/hides a warning next
  to it (ui/app.py::MainWindow._update_provider_credential_hint()).
- Clicking Start with a provider that has no key configured shows a warning
  dialog and aborts BEFORE the output-folder dialog or any API call - not
  after wasting a full (doomed) run.
- Switching the provider also invalidates the current analysis/cost
  estimate (ui/app.py::MainWindow._provider_changed()), the same way
  changing the mode or source file already did - the estimate (pricing,
  free tier, live-quota line) is provider-specific, so leaving a previous
  provider's numbers on screen (and confirmable via the checkbox) after
  switching would be showing stale, wrong figures for the new selection.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import ui.app as app_module
from ui.analysis import analyze_request
from ui.app import MainWindow
from ui.models import TranslationMode, TranslationRequest

FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


def _fake_credential_status(missing_providers: set[str]):
    def status(provider: str) -> str:
        return "credential.missing" if provider in missing_providers else "credential.keyring"
    return status


def test_provider_hint_reflects_credential_status(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "credential_status", _fake_credential_status({"openai"}))

    window = MainWindow()
    window.show()
    try:
        window.provider.setCurrentText("deepl")
        assert window.provider_hint.text() == ""
        assert not window.provider_hint.isVisible()

        window.provider.setCurrentText("openai")
        assert "openai" in window.provider_hint.text()
        assert window.provider_hint.isVisible()

        window.provider.setCurrentText("deepl")
        assert window.provider_hint.text() == ""
        assert not window.provider_hint.isVisible()
    finally:
        window.close()


def test_start_warns_and_aborts_before_folder_dialog_when_key_missing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "credential_status", _fake_credential_status({"deepl"}))

    warning_shown: list[QMessageBox] = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: warning_shown.append(self) or 0)

    def fail_if_called(*args, **kwargs):
        pytest.fail("output-folder dialog must not open when credentials are missing")

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fail_if_called)

    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))
        window.paths = (FIXTURE,)
        window.provider.setCurrentText("deepl")
        window.last_result = analyze_request(TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,)))
        window.confirm.setChecked(True)

        window._start()

        assert warning_shown  # the missing-credential dialog was shown
        assert window._worker is None  # and no job was actually started
    finally:
        window.close()


def test_switching_provider_invalidates_current_analysis(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "credential_status", _fake_credential_status(set()))

    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))
        window.paths = (FIXTURE,)
        window.provider.setCurrentText("deepl")
        window.last_result = analyze_request(TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), provider="deepl"))
        window.confirm.setEnabled(True)
        window.confirm.setChecked(True)
        window.result.setText("some stale analysis text from the deepl estimate")

        window.provider.setCurrentText("google")

        assert window.last_result is None
        assert not window.confirm.isChecked()
        assert not window.confirm.isEnabled()
        assert window.result.text() == window.language.text("analysis.required")
        # The completed-run panel is a different, deliberately untouched
        # concern (see _start()/_invalidate_analysis() docs) - not asserted
        # here since this test never starts a run in the first place.
    finally:
        window.close()
