"""Covers the 02.09.2026 fix (Michael: "Die App sollte sich die Google
Drive ID von der letzten Session merken. Auch den Cache Ordner und die
Anmelde Daten. Das alles bleibt bis jetzt leer.").

Root cause for the cache folder: _choose_drive_cache() already wrote it to
QSettings (used as getExistingDirectory()'s start_dir on the next pick),
but nothing ever read that value back into drive_cache_edit/_drive_cache_dir
when the dialog was reopened. The Drive folder link/ID had no persistence
at all. Both dialogs duplicate the same Drive panel (see their own module
docstrings), so both are covered here.

The stored Google sign-in state itself ("Anmeldedaten") needs no fix here:
_refresh_drive_status() (called in __init__ before this) already reads
is_configured()/is_connected() straight from the keyring on every open, so
it was never actually forgotten - see the module docstring of
MergeSearchDialog._restore_drive_state() for the full reasoning.

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


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


_DIALOGS = [
    ("ui.merge_search_dialog", "MergeSearchDialog", "merge_search"),
    ("ui.word_merge_search_dialog", "WordMergeSearchDialog", "word_merge_search"),
]


@pytest.mark.parametrize("module_name, dialog_attr, settings_prefix", _DIALOGS)
def test_drive_cache_dir_is_restored_on_reopen(qapp, module_name, dialog_attr, settings_prefix) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}DriveStateCache")

    # _choose_drive_cache() itself opens a real folder-picker dialog - not
    # exercised here (see test_choose_drive_cache_* tests for that); this
    # test starts from the QSettings value it would have written, to
    # isolate what's actually new here: reading that value back on the
    # next open.
    settings.setValue(f"{settings_prefix}_drive_cache_dir", "/tmp/some-cache-dir")

    second = DialogClass(LanguageManager("de"), settings)
    try:
        assert second.drive_cache_edit.text() == "/tmp/some-cache-dir"
        assert str(second._drive_cache_dir) == "/tmp/some-cache-dir"
    finally:
        second.close()


@pytest.mark.parametrize("module_name, dialog_attr, settings_prefix", _DIALOGS)
def test_drive_folder_link_is_restored_on_reopen(qapp, module_name, dialog_attr, settings_prefix) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}DriveStateFolder")

    first = DialogClass(LanguageManager("de"), settings)
    try:
        first.drive_folder_edit.setText("https://drive.google.com/drive/u/0/folders/1IGMZBUMVcTHj4z9wsDrSRb6xzdS0klPn")
    finally:
        first.done(0)  # simulate the window being closed (not accept()/reject())

    assert (
        settings.value(f"{settings_prefix}_drive_folder_link", "", type=str)
        == "https://drive.google.com/drive/u/0/folders/1IGMZBUMVcTHj4z9wsDrSRb6xzdS0klPn"
    )

    second = DialogClass(LanguageManager("de"), settings)
    try:
        assert second.drive_folder_edit.text() == (
            "https://drive.google.com/drive/u/0/folders/1IGMZBUMVcTHj4z9wsDrSRb6xzdS0klPn"
        )
        # A restored link is text-only, never a trusted resolve result - it
        # still needs a fresh "Prüfen" click (a live Drive API call) before
        # the search button can be enabled.
        assert second._drive_folder_id is None
    finally:
        second.close()


@pytest.mark.parametrize("module_name, dialog_attr, settings_prefix", _DIALOGS)
def test_nothing_restored_on_first_ever_open(qapp, module_name, dialog_attr, settings_prefix) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}DriveStateEmpty")

    dialog = DialogClass(LanguageManager("de"), settings)
    try:
        assert dialog.drive_cache_edit.text() == ""
        assert dialog.drive_folder_edit.text() == ""
        assert dialog._drive_cache_dir is None
        assert dialog._drive_folder_id is None
    finally:
        dialog.close()
