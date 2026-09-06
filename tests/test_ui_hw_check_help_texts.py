"""Tooltip/WhatsThis-Abdeckung fuer HardwareCheckDialog.

07.09.2026 (Michael: "Ausserdem haette ich noch gerne zu jeder Option in
der App eine klare Nutzerfreundliche Tooltip und eine Hilfe."): gleiches
Muster wie tests/test_ui_help_texts.py (MainWindow) und
tests/test_ui_settings_help_texts.py (SettingsDialog), hier fuer die 2
Felder des Hardware-Test-Dialogs (Status, Erneut-pruefen-Button).
"""

from __future__ import annotations

import ast
import os
import pathlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager
from ui.i18n_data import CATALOGUES

NEW_KEYS = [
    "hw_check.status.tooltip",
    "hw_check.status.whatsthis",
    "hw_check.recheck_button.tooltip",
    "hw_check.recheck_button.whatsthis",
]


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_hardware_check_dialog_has_two_help_widgets(qapp) -> None:
    import ui.app as appmod

    dialog = appmod.HardwareCheckDialog(LanguageManager("de"))
    try:
        assert len(dialog._hw_check_help_widgets) == 2
    finally:
        dialog.close()


def test_every_hw_check_help_widget_has_tooltip_and_whatsthis_in_every_language(qapp) -> None:
    import ui.app as appmod

    dialog = appmod.HardwareCheckDialog(LanguageManager("de"))
    try:
        for code in CATALOGUES:
            dialog.language.set_language(code)
            for widget, tooltip_key, whatsthis_key in dialog._hw_check_help_widgets:
                assert widget.toolTip().strip(), f"{code}: missing tooltip for {tooltip_key}"
                assert widget.whatsThis().strip(), f"{code}: missing whatsthis for {whatsthis_key}"
    finally:
        dialog.close()


def test_hw_check_help_keys_translated_for_all_nine_locales() -> None:
    assert len(NEW_KEYS) == 4
    for code, catalogue in CATALOGUES.items():
        for key in NEW_KEYS:
            assert key in catalogue, f"{code}: missing key {key}"
            assert catalogue[key].strip(), f"{code}: empty value for {key}"


def test_no_duplicate_keys_in_any_catalogue_hw_check() -> None:
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
