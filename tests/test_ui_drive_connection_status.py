"""Covers the 02.09.2026 fix (Michael: "Das wir mit Google verbunden sind
darf ruhig prominenter dargestellt werden. Vielleicht mit einem grünem
Rahmen um die 'Verbunden' Meldung, oder grüner Hintergrund. Den sonst
klickt man versehentlich wieder auf Verbinden, das der 'Verbinden' Button
ja aktiv ist.").

Two related changes to _refresh_drive_status() in both
MergeSearchDialog/WordMergeSearchDialog (duplicated Drive panel, see their
own module docstrings): the connection-status label gets a green
background/border (_DRIVE_CONNECTED_STYLE) only while connected, and "Mit
Google verbinden" is now disabled while already connected (it used to stay
enabled the whole time credentials were configured, connected or not).

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation.
"""
from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager
from ui.merge_search_dialog import _DRIVE_CONNECTED_STYLE


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


_DIALOGS = [
    ("ui.merge_search_dialog", "MergeSearchDialog"),
    ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
]


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_connected_status_gets_the_green_highlight_and_disables_connect(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr
) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    monkeypatch.setattr(dialog_module.drive_auth, "is_configured", lambda: True)
    monkeypatch.setattr(dialog_module.drive_auth, "is_connected", lambda: True)

    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ConnStatusGreen"))
    try:
        assert dialog.drive_connection_status_label.styleSheet() == _DRIVE_CONNECTED_STYLE
        assert dialog.drive_connect_button.isEnabled() is False
        assert dialog.drive_disconnect_button.isEnabled() is True
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_configured_but_not_connected_has_no_highlight_and_enables_connect(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr
) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    monkeypatch.setattr(dialog_module.drive_auth, "is_configured", lambda: True)
    monkeypatch.setattr(dialog_module.drive_auth, "is_connected", lambda: False)

    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ConnStatusIdle"))
    try:
        assert dialog.drive_connection_status_label.styleSheet() == ""
        assert dialog.drive_connect_button.isEnabled() is True
        assert dialog.drive_disconnect_button.isEnabled() is False
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_not_configured_has_no_highlight_and_disables_connect(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr
) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    monkeypatch.setattr(dialog_module.drive_auth, "is_configured", lambda: False)
    monkeypatch.setattr(dialog_module.drive_auth, "is_connected", lambda: False)

    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ConnStatusNone"))
    try:
        assert dialog.drive_connection_status_label.styleSheet() == ""
        assert dialog.drive_connect_button.isEnabled() is False
        assert dialog.drive_disconnect_button.isEnabled() is False
    finally:
        dialog.close()
