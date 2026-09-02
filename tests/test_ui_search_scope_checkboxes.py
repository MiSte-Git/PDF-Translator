"""Covers the 02.09.2026 search-scope checkboxes in MergeSearchDialog/
WordMergeSearchDialog (ui/merge_search_dialog.py, ui/word_merge_search_dialog.py)
- Michael's confirmed design: three independently-combinable checkboxes
("ICO Format"/"Header"/"Volltext"), default state unchanged from before
this feature (only "ICO Format" checked), at least one must be selected
to search, and whichever are checked at "Suchen" time get passed straight
through to the worker (ui/workers.py).

Follows the established no_run_thread_pool pattern (see
tests/test_ui_word_mode.py) to intercept QThreadPool.start() without ever
running the worker's actual scan.
"""
from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.i18n import LanguageManager
from ui.search_scopes import SCOPE_FULL_TEXT, SCOPE_HEADER, SCOPE_ICO_FORMAT


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


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_default_state_is_ico_format_only(qapp, module_name, dialog_attr) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ScopeDefault"))
    try:
        assert dialog.scope_ico_format_checkbox.isChecked() is True
        assert dialog.scope_header_checkbox.isChecked() is False
        assert dialog.scope_full_text_checkbox.isChecked() is False
        assert dialog._selected_scopes() == {SCOPE_ICO_FORMAT}
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_selected_scopes_reflects_arbitrary_checkbox_combinations(qapp, module_name, dialog_attr) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ScopeCombo"))
    try:
        dialog.scope_ico_format_checkbox.setChecked(False)
        dialog.scope_header_checkbox.setChecked(True)
        dialog.scope_full_text_checkbox.setChecked(True)
        assert dialog._selected_scopes() == {SCOPE_HEADER, SCOPE_FULL_TEXT}

        dialog.scope_header_checkbox.setChecked(False)
        dialog.scope_full_text_checkbox.setChecked(False)
        assert dialog._selected_scopes() == set()
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_warns_and_does_not_start_a_worker_with_no_scope_selected(
    qapp, monkeypatch: pytest.MonkeyPatch, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    # 02.09.2026 (Michael, real-world large-folder merge: "Wenn ich alle
    # PDFs in einem Ordner haben möchte, ohne einen Suchbereich, gibt es
    # einen Fehler.") - a scope is only ever consulted when there's an
    # actual text query to check it against (find_matching()'s docstring,
    # ui/merge_search.py); this warning is about "you typed something to
    # search for but didn't say WHERE to look", so it must only fire with
    # a non-empty query - see the empty-query counterpart test below.
    warnings: list[tuple] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))

    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ScopeMissing"))
    try:
        dialog.scope_ico_format_checkbox.setChecked(False)  # uncheck the only default scope
        dialog.query_edit.setText("Acme")
        dialog._folder = tmp_path  # a folder IS set - the scope check must still fire first

        dialog._start_search()

        assert len(no_run_thread_pool) == 0
        assert len(warnings) == 1
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_with_an_empty_query_needs_no_scope_at_all(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    # 02.09.2026 (Michael: "Wenn ich alle PDFs in einem Ordner haben
    # möchte, ohne einen Suchbereich, gibt es einen Fehler.") - "list
    # every file in this folder" (empty search field) never opens a file
    # to check any scope against (find_matching()'s docstring), so
    # requiring one here used to block a deliberately-supported case for
    # no reason. See test_start_search_warns_and_does_not_start_a_worker_
    # with_no_scope_selected above for the still-enforced non-empty-query
    # case.
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ScopeEmptyQuery"))
    try:
        dialog.scope_ico_format_checkbox.setChecked(False)  # uncheck the only default scope
        assert dialog.query_edit.text().strip() == ""  # the "list everything" case
        dialog._folder = tmp_path

        dialog._start_search()

        assert len(no_run_thread_pool) == 1
        worker = no_run_thread_pool[0]
        assert worker.scopes == set()
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_passes_the_selected_scopes_to_the_worker(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}ScopeWiring"))
    try:
        dialog.scope_header_checkbox.setChecked(True)
        dialog.scope_full_text_checkbox.setChecked(True)
        dialog._folder = tmp_path

        dialog._start_search()

        assert len(no_run_thread_pool) == 1
        worker = no_run_thread_pool[0]
        assert worker.scopes == {SCOPE_ICO_FORMAT, SCOPE_HEADER, SCOPE_FULL_TEXT}
    finally:
        dialog.close()
