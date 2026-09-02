"""Covers the 02.09.2026 date filter ("Nach Datum filtern": Von/Bis or
"Exaktes Datum", file date vs. date-in-document) in MergeSearchDialog/
WordMergeSearchDialog (ui/merge_search_dialog.py,
ui/word_merge_search_dialog.py) - Michael: "Können wir noch eine nach
Datumsbereich, von, bis, exakt einbauen." Confirmed design (two rounds of
AskUserQuestion, 02.09.2026): a checkable group box (off by default), a
Von/Bis range with an "Exaktes Datum" toggle swapping in a single field,
one source per search (file date XOR a date found in the document, scoped
to ICO Feld/Header/Footer), and individually selectable recognized text
formats (default ISO only) - see pipeline/date_extract.py's module
docstring for the full design.

Follows the established no_run_thread_pool pattern (see
tests/test_ui_search_scope_checkboxes.py) to intercept QThreadPool.start()
without ever running the worker's actual scan, and the same
`_DIALOGS`-parametrized-across-both-dialogs shape since this feature is
duplicated identically into both dialogs (see the project's per-format UI
convention, ui/merge_search_dialog.py's module docstring).

dialog.show() is required before asserting on child widget isVisible() -
Qt's isVisible() reflects actual on-screen visibility (false for every
child of a never-shown top-level widget, regardless of an explicit
setVisible(True) call further down the hierarchy), not just the widget's
own explicit-visibility flag.
"""
from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date

import pytest
from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from pipeline.date_extract import SOURCE_DOCUMENT, SOURCE_FILE, FORMAT_ISO
from ui.search_scopes import DATE_REGION_FOOTER, DATE_REGION_ICO_FORMAT


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
    from ui.i18n import LanguageManager

    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}{settings_key}"))
    dialog.show()  # see module docstring: isVisible() needs an actually-shown top-level
    return dialog


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_date_filter_group_is_unchecked_by_default(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateDefault")
    try:
        assert dialog.date_filter_group.isChecked() is False
        assert dialog.date_document_options.isVisible() is False
        assert dialog.date_source_file_radio.isChecked() is True
        assert dialog.date_region_ico_format_checkbox.isChecked() is True
        assert dialog.date_format_iso_checkbox.isChecked() is True
        assert dialog.date_format_de_checkbox.isChecked() is False
        assert dialog._build_date_filter() == (None, None)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_source_toggle_shows_and_hides_the_document_options(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateSourceToggle")
    try:
        assert dialog.date_document_options.isVisible() is False
        dialog.date_source_document_radio.setChecked(True)
        assert dialog.date_document_options.isVisible() is True
        dialog.date_source_file_radio.setChecked(True)
        assert dialog.date_document_options.isVisible() is False
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_exact_toggle_switches_the_stacked_panel(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateExactToggle")
    try:
        assert dialog.date_range_stack.currentIndex() == 0
        dialog.date_exact_checkbox.setChecked(True)
        assert dialog.date_range_stack.currentIndex() == 1
        dialog.date_exact_checkbox.setChecked(False)
        assert dialog.date_range_stack.currentIndex() == 0
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_file_source_range(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildFileRange")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))
        dialog.date_to_edit.setDate(dialog.date_to_edit.date().fromString("2026-12-31", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert error_key is None
        assert date_filter is not None
        assert date_filter.source == SOURCE_FILE
        assert date_filter.date_range.start == date(2026, 1, 1)
        assert date_filter.date_range.end == date(2026, 12, 31)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_exact_date_sets_start_equal_to_end(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildExact")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_exact_checkbox.setChecked(True)
        dialog.date_exact_edit.setDate(dialog.date_exact_edit.date().fromString("2026-09-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert error_key is None
        assert date_filter is not None
        assert date_filter.date_range.start == date(2026, 9, 1)
        assert date_filter.date_range.end == date(2026, 9, 1)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_document_source_with_regions_and_formats(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildDocument")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_region_ico_format_checkbox.setChecked(False)
        dialog.date_region_footer_checkbox.setChecked(True)
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert error_key is None
        assert date_filter is not None
        assert date_filter.source == SOURCE_DOCUMENT
        assert date_filter.regions == frozenset({DATE_REGION_FOOTER})
        assert date_filter.formats == frozenset({FORMAT_ISO})
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_checked_but_empty_is_treated_as_no_filter(qapp, module_name, dialog_attr) -> None:
    # See MergeSearchDialog._build_date_filter()'s docstring: a checked-but-
    # still-empty group is the "just turned it on, haven't filled it in
    # yet" state, not an error.
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildEmpty")
    try:
        dialog.date_filter_group.setChecked(True)
        assert dialog._build_date_filter() == (None, None)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_reversed_range_is_an_error(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildReversed")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-12-31", "yyyy-MM-dd"))
        dialog.date_to_edit.setDate(dialog.date_to_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert date_filter is None
        assert error_key == "merge_search.error_date_range_reversed"
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_document_source_without_region_is_an_error(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildMissingRegion")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_region_ico_format_checkbox.setChecked(False)  # the only default region
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert date_filter is None
        assert error_key == "merge_search.error_missing_date_region"
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_document_source_without_format_is_an_error(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildMissingFormat")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_format_iso_checkbox.setChecked(False)  # the only default format
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert date_filter is None
        assert error_key == "merge_search.error_missing_date_format"
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_warns_and_does_not_start_a_worker_on_reversed_range(
    qapp, monkeypatch: pytest.MonkeyPatch, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    warnings: list[tuple] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))

    dialog = _make_dialog(module_name, dialog_attr, "DateStartReversed")
    try:
        dialog._folder = tmp_path
        dialog.date_filter_group.setChecked(True)
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-12-31", "yyyy-MM-dd"))
        dialog.date_to_edit.setDate(dialog.date_to_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        dialog._start_search()

        assert len(no_run_thread_pool) == 0
        assert len(warnings) == 1
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_passes_the_date_filter_to_the_worker(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateStartWiring")
    try:
        dialog._folder = tmp_path
        dialog.date_filter_group.setChecked(True)
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        dialog._start_search()

        assert len(no_run_thread_pool) == 1
        worker = no_run_thread_pool[0]
        assert worker.date_filter is not None
        assert worker.date_filter.source == SOURCE_FILE
        assert worker.date_filter.date_range.start == date(2026, 1, 1)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_start_search_passes_none_date_filter_when_group_unchecked(
    qapp, no_run_thread_pool: list[object], module_name, dialog_attr, tmp_path
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateStartUnchecked")
    try:
        dialog._folder = tmp_path

        dialog._start_search()

        assert len(no_run_thread_pool) == 1
        worker = no_run_thread_pool[0]
        assert worker.date_filter is None
    finally:
        dialog.close()
