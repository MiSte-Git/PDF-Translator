"""Covers the 02.09.2026 fix (Michael, after pasting a full Google
HttpError into the chat): "Es wäre gut wenn man solche Meldungen im UI
auch direkt selektieren und kopieren könnte."

QLabel is not selectable by default, so a status/error message shown in
one could not be marked and copied (e.g. into a bug report). Fixed by
setting Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard on every
status/error label in the app: SettingsDialog.status,
HardwareCheckDialog.status and MainWindow.job_status (ui/app.py), plus
drive_folder_status_label and drive_connection_status_label in both
MergeSearchDialog and WordMergeSearchDialog (which duplicate the same
Drive panel - see their own module docstrings).

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import importlib

import pytest
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager

_SELECTABLE = Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _is_selectable(label) -> bool:
    return (label.textInteractionFlags() & _SELECTABLE) == _SELECTABLE


def test_settings_dialog_status_label_is_selectable(qapp) -> None:
    from ui.app import SettingsDialog

    dialog = SettingsDialog(QSettings("PDF-Translator-Test", "SettingsDialogSelectable"), LanguageManager("de"))
    try:
        assert _is_selectable(dialog.status)
    finally:
        dialog.close()


def test_hardware_check_dialog_status_label_is_selectable(qapp) -> None:
    from ui.app import HardwareCheckDialog

    dialog = HardwareCheckDialog(LanguageManager("de"))
    try:
        assert _is_selectable(dialog.status)
    finally:
        dialog.close()


def test_main_window_job_status_label_is_selectable(qapp) -> None:
    from ui.app import MainWindow

    window = MainWindow()
    try:
        assert _is_selectable(window.job_status)
    finally:
        window.close()


@pytest.mark.parametrize(
    "module_name, dialog_attr",
    [
        ("ui.merge_search_dialog", "MergeSearchDialog"),
        ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
    ],
)
def test_drive_status_labels_are_selectable(qapp, module_name, dialog_attr) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}Selectable"))
    try:
        assert _is_selectable(dialog.drive_folder_status_label)
        assert _is_selectable(dialog.drive_connection_status_label)
    finally:
        dialog.close()
