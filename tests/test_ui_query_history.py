"""Covers the 02.09.2026 search-term history in MergeSearchDialog/
WordMergeSearchDialog (ui/merge_search_dialog.py, ui/word_merge_search_dialog.py)
- Michael: "Eine Historie im Suchbereich hätte ich noch gern." The field
used to persist only the single LAST query (see query_edit's constructor
comment, ui/merge_search_dialog.py) even though Michael's original request
that added it the same day already said "die letzten Suchbegriffe"
(plural) - this replaces that with an editable QComboBox backed by a real
history list.

Covers the two free functions this is built on (_load_query_history()/
_record_query_history(), both in ui/merge_search_dialog.py, imported
unchanged into ui/word_merge_search_dialog.py the same way
_configure_optional_date_edit() etc. already are - see that module's
docstring) directly, plus the dialog-level wiring via the established
`_DIALOGS`-parametrized-across-both-dialogs shape (see
tests/test_ui_date_filter.py) and the no_run_thread_pool pattern (see
tests/test_ui_search_scope_checkboxes.py) to drive a real _start_search()
without ever running the worker's actual scan.
"""
from __future__ import annotations

import importlib
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager
from ui.merge_search_dialog import _QUERY_HISTORY_MAX, _load_query_history, _record_query_history


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def no_run_thread_pool(monkeypatch: pytest.MonkeyPatch):
    started: list[object] = []
    monkeypatch.setattr(QThreadPool, "start", lambda self, worker: started.append(worker))
    return started


_DIALOGS = [
    ("ui.merge_search_dialog", "MergeSearchDialog"),
    ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
]


def _make_dialog(module_name: str, dialog_attr: str, settings_key: str):
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    return DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}{settings_key}"))


# --- _record_query_history() (pure logic) -----------------------------


def test_record_adds_a_new_term_to_the_front() -> None:
    assert _record_query_history([], "Acme") == ["Acme"]
    assert _record_query_history(["Acme"], "Zenith") == ["Zenith", "Acme"]


def test_record_promotes_an_existing_term_instead_of_duplicating_it() -> None:
    assert _record_query_history(["Zenith", "Acme"], "Acme") == ["Acme", "Zenith"]


def test_record_ignores_blank_or_whitespace_only_text() -> None:
    assert _record_query_history(["Acme"], "") == ["Acme"]
    assert _record_query_history(["Acme"], "   ") == ["Acme"]


def test_record_strips_surrounding_whitespace() -> None:
    assert _record_query_history([], "  Acme  ") == ["Acme"]


def test_record_caps_the_history_length() -> None:
    history = [f"term{i}" for i in range(_QUERY_HISTORY_MAX)]
    updated = _record_query_history(history, "brand new term")
    assert len(updated) == _QUERY_HISTORY_MAX
    assert updated[0] == "brand new term"
    assert updated[-1] == f"term{_QUERY_HISTORY_MAX - 2}"  # the oldest entry fell off


# --- _load_query_history() (pure logic) --------------------------------


def test_load_returns_empty_when_neither_key_was_ever_written() -> None:
    settings = QSettings("PDF-Translator-Test", "QueryHistoryLoadEmpty")
    assert _load_query_history(settings, "new_key", "old_key") == []


def test_load_reads_back_a_previously_saved_history() -> None:
    settings = QSettings("PDF-Translator-Test", "QueryHistoryLoadSaved")
    settings.setValue("new_key", json.dumps(["Zenith", "Acme"]))
    assert _load_query_history(settings, "new_key", "old_key") == ["Zenith", "Acme"]


def test_load_migrates_the_old_single_value_key_when_no_history_exists_yet() -> None:
    # 02.09.2026 - Michael's most recent search under the OLD "just the
    # last query" behavior must not simply vanish the first time this
    # runs after the history feature ships.
    settings = QSettings("PDF-Translator-Test", "QueryHistoryLoadMigrate")
    settings.setValue("old_key", "Acme UND Vertrag")
    assert _load_query_history(settings, "new_key", "old_key") == ["Acme UND Vertrag"]


def test_load_prefers_the_new_key_over_the_legacy_one_once_both_exist() -> None:
    settings = QSettings("PDF-Translator-Test", "QueryHistoryLoadPrefersNew")
    settings.setValue("old_key", "stale")
    settings.setValue("new_key", json.dumps(["fresh"]))
    assert _load_query_history(settings, "new_key", "old_key") == ["fresh"]


def test_load_treats_corrupt_json_the_same_as_no_history() -> None:
    settings = QSettings("PDF-Translator-Test", "QueryHistoryLoadCorrupt")
    settings.setValue("new_key", "{not valid json")
    assert _load_query_history(settings, "new_key", "old_key") == []


# --- dialog-level wiring ------------------------------------------------


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_query_field_starts_empty_with_no_history(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "QueryHistoryDefault")
    try:
        assert dialog.query_edit.currentText() == ""
        assert dialog._query_history == []
        assert dialog.query_edit.count() == 0
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_typing_without_searching_does_not_join_the_history(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    # Only an actually-run search counts (see _record_query_history()'s
    # docstring) - typing into the field alone must never pollute the
    # dropdown with things that were never searched.
    dialog = _make_dialog(module_name, dialog_attr, "QueryHistoryTypeOnly")
    try:
        dialog.query_edit.setCurrentText("Acme")
        assert dialog._query_history == []
        assert dialog.query_edit.count() == 0
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_records_the_query_and_repopulates_the_dropdown(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "QueryHistoryRecord")
    try:
        dialog._folder = tmp_path
        dialog.query_edit.setCurrentText("Acme")

        dialog._start_search()

        assert dialog._query_history == ["Acme"]
        assert [dialog.query_edit.itemText(i) for i in range(dialog.query_edit.count())] == ["Acme"]
        assert dialog.query_edit.currentText() == "Acme"  # unchanged by the repopulation
        assert len(no_run_thread_pool) == 1
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_with_an_empty_query_records_nothing(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "QueryHistoryEmptySearch")
    try:
        dialog._folder = tmp_path
        dialog.scope_ico_format_checkbox.setChecked(False)  # scope is irrelevant to an empty query

        dialog._start_search()

        assert dialog._query_history == []
        assert dialog.query_edit.count() == 0
        assert len(no_run_thread_pool) == 1
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_re_running_an_earlier_query_promotes_it_without_duplicating(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "QueryHistoryPromote")
    try:
        dialog._folder = tmp_path

        dialog.query_edit.setCurrentText("Acme")
        dialog._start_search()
        dialog.query_edit.setCurrentText("Zenith")
        dialog._start_search()
        dialog.query_edit.setCurrentText("Acme")
        dialog._start_search()

        assert dialog._query_history == ["Acme", "Zenith"]
        assert [dialog.query_edit.itemText(i) for i in range(dialog.query_edit.count())] == ["Acme", "Zenith"]
        assert len(no_run_thread_pool) == 3
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_history_is_persisted_on_close_and_restored_on_the_next_open(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}QueryHistoryPersist")
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    first = DialogClass(LanguageManager("de"), settings)
    try:
        first._folder = tmp_path
        first.query_edit.setCurrentText("Acme")
        first._start_search()
        first.query_edit.setCurrentText("Zenith")
        first._start_search()
        first.done(0)  # QDialog.reject()/accept() both route through done()
    finally:
        first.close()

    second = DialogClass(LanguageManager("de"), settings)
    try:
        assert second._query_history == ["Zenith", "Acme"]
        assert second.query_edit.currentText() == "Zenith"  # most recent shown by default
        assert [second.query_edit.itemText(i) for i in range(second.query_edit.count())] == ["Zenith", "Acme"]
    finally:
        second.close()
