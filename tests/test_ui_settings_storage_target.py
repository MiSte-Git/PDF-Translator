"""Covers the 07.09.2026 fix (Michael, nach der DeepL env-var/Keyring-
Verwechslung: "Der Punkt mit der Umgebungsvariable, im Keyring oder in
beiden speichern, ist doch eigentlich nicht nötig, oder?"). Die
Umgebungsvariable-Option bleibt bestehen - sie ist kein Bug, sondern
deckt TMEs dokumentiertes Env-Var-Override beim image_translate_cli-
Subprozessaufruf ab (image_translate_cli/CLI.md), unabhängig vom
Desktop-Dialog. Für den Normalfall im Desktop-Dialog wird "OS-Keyring"
aber deutlicher als DIE Standardauswahl positioniert: zuerst in der
Dropdown-Liste (nicht mehr "Umgebungsvariable"), und der
Sitzungs-Hinweis (settings.session_note) erscheint jetzt auch bei
"Beides" - das schreibt laut ui/settings.py::save_credential() ebenfalls
eine nicht dauerhafte Umgebungsvariable, nicht nur "Umgebungsvariable"
allein.

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


def test_keyring_is_first_and_default(qapp) -> None:
    from ui.app import SettingsDialog

    dialog = SettingsDialog(QSettings("PDF-Translator-Test", "StorageTargetOrder"), LanguageManager("de"))
    try:
        order = [dialog.target.itemData(i) for i in range(dialog.target.count())]
        assert order == ["keyring", "environment", "both"]
        assert dialog.target.currentData() == "keyring"
        assert dialog.note.isVisible() is False
    finally:
        dialog.close()


def test_session_note_shown_for_environment_and_both(qapp) -> None:
    from ui.app import SettingsDialog

    dialog = SettingsDialog(QSettings("PDF-Translator-Test", "StorageTargetNote"), LanguageManager("de"))
    try:
        dialog.show()
        qapp.processEvents()
        for target in ("environment", "both"):
            dialog.target.setCurrentIndex(dialog.target.findData(target))
            qapp.processEvents()
            assert dialog.note.isVisible() is True, target
        dialog.target.setCurrentIndex(dialog.target.findData("keyring"))
        qapp.processEvents()
        assert dialog.note.isVisible() is False
    finally:
        dialog.close()
