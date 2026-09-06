"""Tooltip/WhatsThis-Abdeckung fuer SettingsDialog.

07.09.2026 (Michael: "Ausserdem haette ich noch gerne zu jeder Option in
der App eine klare Nutzerfreundliche Tooltip und eine Hilfe."): gleiches
Muster wie tests/test_ui_help_texts.py fuer MainWindow, hier fuer die 7
Felder des Einstellungsdialogs (Anbieter, Status, neuer Schluessel,
Speicherort, Zeichen-Obergrenze, Speichern-Button, Log-oeffnen-Button).

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation.
"""

from __future__ import annotations

import ast
import os
import pathlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager
from ui.i18n_data import CATALOGUES

NEW_KEYS = [
    "settings.provider.tooltip",
    "settings.provider.whatsthis",
    "settings.status.tooltip",
    "settings.status.whatsthis",
    "settings.secret.tooltip",
    "settings.secret.whatsthis",
    "settings.target_field.tooltip",
    "settings.target_field.whatsthis",
    "settings.max_chars.tooltip",
    "settings.max_chars.whatsthis",
    "settings.save_key.tooltip",
    "settings.save_key.whatsthis",
    "settings.open_log.tooltip",
    "settings.open_log.whatsthis",
]


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_settings_dialog_has_seven_help_widgets(qapp) -> None:
    import ui.app as appmod

    dialog = appmod.SettingsDialog(QSettings("PDF-Translator-Test", "SettingsHelpCount"), LanguageManager("de"))
    try:
        assert len(dialog._settings_help_widgets) == 7
    finally:
        dialog.close()


def test_every_settings_help_widget_has_tooltip_and_whatsthis_in_every_language(qapp) -> None:
    import ui.app as appmod

    dialog = appmod.SettingsDialog(QSettings("PDF-Translator-Test", "SettingsHelpAllLangs"), LanguageManager("de"))
    try:
        for code in CATALOGUES:
            dialog.language.set_language(code)
            for widget, tooltip_key, whatsthis_key in dialog._settings_help_widgets:
                assert widget.toolTip().strip(), f"{code}: missing tooltip for {tooltip_key}"
                assert widget.whatsThis().strip(), f"{code}: missing whatsthis for {whatsthis_key}"
    finally:
        dialog.close()


def test_settings_help_keys_translated_for_all_nine_locales() -> None:
    assert len(NEW_KEYS) == 14
    for code, catalogue in CATALOGUES.items():
        for key in NEW_KEYS:
            assert key in catalogue, f"{code}: missing key {key}"
            assert catalogue[key].strip(), f"{code}: empty value for {key}"


def test_no_duplicate_keys_in_any_catalogue_settings() -> None:
    path = pathlib.Path(__file__).resolve().parents[1] / "ui" / "i18n_data.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    expected_locales = {"DE", "EN", "FR", "ES", "IT", "NL", "FI", "HR", "RU"}
    checked = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in expected_locales and isinstance(node.value, ast.Dict):
                checked += 1
                keys = [k.value for k in node.value.keys]
                assert len(keys) == len(set(keys)), f"{name}: duplicate keys found"
    assert checked == 9
