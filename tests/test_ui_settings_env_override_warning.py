"""Covers the 07.09.2026 fix (Michael: DeepL-Kostenanalyse schlug mit 403
fehl, obwohl der Schluessel "nur Key-Ring" gespeichert war - app.log zeigte
"deepl_api_key: geladen aus Umgebungsvariable DEEPL_API_KEY"). Ursache: eine
auf dem Testrechner gesetzte DEEPL_API_KEY-Umgebungsvariable gewinnt laut
pipeline/credentials.py::get_api_key()s bewusstem env_first=True fuer
Uebersetzer-Provider (siehe dessen Docstring - noetig fuer TME's
dokumentiertes Env-Var-Override, image_translate_cli/CLI.md) immer vor dem
Schluesselbund, unabhaengig davon was in den Einstellungen als Speicherort
gewaehlt ist. credential_status() erkannte das bereits zuverlaessig, aber
als kleines Statuslabel neben einem Dropdown fiel das leicht nicht auf.
SettingsDialog.env_override_warning macht denselben Befund unuebersehbar.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_env_override_warning_hidden_when_source_is_keyring(qapp, monkeypatch) -> None:
    import ui.app as appmod

    monkeypatch.setattr(appmod, "credential_status", lambda provider: "credential.keyring")
    dialog = appmod.SettingsDialog(QSettings("PDF-Translator-Test", "EnvWarningKeyring"), LanguageManager("de"))
    try:
        dialog.show()
        qapp.processEvents()
        assert dialog.env_override_warning.isVisible() is False
    finally:
        dialog.close()


def test_env_override_warning_shown_when_source_is_environment(qapp, monkeypatch) -> None:
    import ui.app as appmod

    monkeypatch.setattr(appmod, "credential_status", lambda provider: "credential.environment")
    dialog = appmod.SettingsDialog(QSettings("PDF-Translator-Test", "EnvWarningEnv"), LanguageManager("de"))
    try:
        dialog.show()
        qapp.processEvents()
        assert dialog.env_override_warning.isVisible() is True
        assert dialog.env_override_warning.text()
    finally:
        dialog.close()


def test_env_override_warning_updates_when_provider_changes(qapp, monkeypatch) -> None:
    import ui.app as appmod

    def fake_status(provider: str) -> str:
        return "credential.environment" if provider == "deepl" else "credential.keyring"

    monkeypatch.setattr(appmod, "credential_status", fake_status)
    dialog = appmod.SettingsDialog(
        QSettings("PDF-Translator-Test", "EnvWarningSwitch"), LanguageManager("de"), initial_provider="deepl"
    )
    try:
        dialog.show()
        qapp.processEvents()
        assert dialog.env_override_warning.isVisible() is True

        dialog.provider.setCurrentText("google")
        qapp.processEvents()
        assert dialog.env_override_warning.isVisible() is False
    finally:
        dialog.close()


def test_env_override_warning_translated_for_all_locales() -> None:
    from ui.i18n_data import CATALOGUES

    for code, catalogue in CATALOGUES.items():
        assert "settings.env_override_warning" in catalogue, code
        assert catalogue["settings.env_override_warning"].strip()
