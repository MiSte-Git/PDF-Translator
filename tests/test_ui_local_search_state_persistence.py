"""Covers the 02.09.2026 fix (Michael: "Dann sollte die Unterordner Option
nicht als Standard ausgewählt sein, zumindest nicht beim erneuten Suchen.
Der letzte Suchordner wird auch nicht im Textfeld angezeigt, aber wenn man
den Button klickt ist man direkt dort. Das sollte UI weit gleich
gehandhabt werden.").

Two related bugs in MergeSearchDialog/WordMergeSearchDialog's LOCAL
(non-Drive) search panel:

1. recursive_checkbox always started checked, with no memory of what was
   last used - unlike every other UI-visible search option in this
   dialog. Default is now unchecked, and the last value is restored on
   the next open (see _restore_local_folder_state()).
2. _choose_folder() already wrote the picked folder to QSettings (used
   only as getExistingDirectory()'s start_dir), but folder_edit/self._folder
   were never restored from it on reopen - the field looked empty even
   though a folder was already remembered underneath and the picker
   silently opened there. This mirrors the exact bug already fixed for
   the Drive cache folder in test_ui_drive_state_persistence.py; both
   local and Drive state are now handled the same way, in both dialogs.

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
def test_recursive_checkbox_defaults_to_unchecked_on_first_ever_open(
    qapp, module_name, dialog_attr, settings_prefix
) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}LocalStateEmpty")

    dialog = DialogClass(LanguageManager("de"), settings)
    try:
        assert dialog.recursive_checkbox.isChecked() is False
        assert dialog.folder_edit.text() == ""
        assert dialog._folder is None
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr, settings_prefix", _DIALOGS)
def test_recursive_checkbox_state_is_restored_on_reopen(qapp, module_name, dialog_attr, settings_prefix) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}LocalStateRecursive")

    first = DialogClass(LanguageManager("de"), settings)
    try:
        first.recursive_checkbox.setChecked(True)
    finally:
        first.done(0)  # simulate the window being closed (not accept()/reject())

    assert settings.value(f"{settings_prefix}_recursive", False, type=bool) is True

    second = DialogClass(LanguageManager("de"), settings)
    try:
        # A fresh dialog does NOT silently re-default to checked just
        # because it starts up - it picks up exactly what was last used.
        assert second.recursive_checkbox.isChecked() is True
    finally:
        second.done(0)

    # ... and switching it back off is remembered just as well - this
    # isn't a one-way "sticky true", it's a real persisted last value.
    third = DialogClass(LanguageManager("de"), settings)
    try:
        third.recursive_checkbox.setChecked(False)
    finally:
        third.done(0)

    fourth = DialogClass(LanguageManager("de"), settings)
    try:
        assert fourth.recursive_checkbox.isChecked() is False
    finally:
        fourth.close()


@pytest.mark.parametrize("module_name, dialog_attr, settings_prefix", _DIALOGS)
def test_last_local_folder_is_shown_in_the_field_on_reopen(qapp, module_name, dialog_attr, settings_prefix) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}LocalStateFolder")

    # _choose_folder() itself opens a real folder-picker dialog - not
    # exercised here (same isolation choice as
    # test_drive_cache_dir_is_restored_on_reopen); this test starts from
    # the QSettings value it would have written, to isolate what's
    # actually new here: reading that value back into the field/self._folder
    # on the next open.
    settings.setValue(f"{settings_prefix}_last_folder", "/tmp/some-search-folder")

    dialog = DialogClass(LanguageManager("de"), settings)
    try:
        assert dialog.folder_edit.text() == "/tmp/some-search-folder"
        assert str(dialog._folder) == "/tmp/some-search-folder"
        # Restoring the folder also means a search can start right away,
        # without the user having to click "Ordner wählen …" again just to
        # re-select the very folder that's already shown.
        assert dialog.search_button.isEnabled() is True
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr, settings_prefix", _DIALOGS)
def test_both_dialogs_persist_and_restore_local_state_identically(
    qapp, module_name, dialog_attr, settings_prefix
) -> None:
    # The reported inconsistency was exactly this - one dialog behaving
    # differently from the other (or from its own Drive panel). Both are
    # driven through the exact same settings-key naming convention
    # (f"{settings_prefix}_last_folder" / f"{settings_prefix}_recursive"),
    # so this is really a guard against the two dialogs drifting apart
    # again in a future change, not a new behavior of its own.
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}LocalStateBoth")

    first = DialogClass(LanguageManager("de"), settings)
    try:
        first._folder = None
        first.folder_edit.setText("")
        first.settings.setValue(f"{settings_prefix}_last_folder", "/tmp/shared-folder")
        first.recursive_checkbox.setChecked(True)
    finally:
        first.done(0)

    second = DialogClass(LanguageManager("de"), settings)
    try:
        assert second.folder_edit.text() == "/tmp/shared-folder"
        assert second.recursive_checkbox.isChecked() is True
    finally:
        second.close()
