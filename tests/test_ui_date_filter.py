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
from PySide6.QtCore import QDate, QSettings, Qt, QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QStyle, QStyleOptionSpinBox

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
        # 02.09.2026 - the group must be checked (see
        # test_group_unchecked_hides_the_entire_date_filter_content below)
        # for isVisible() to reflect the source toggle at all - an
        # unchecked group hides date_filter_content itself, which makes
        # every descendant's isVisible() False regardless of its own
        # explicit visibility flag.
        dialog.date_filter_group.setChecked(True)
        assert dialog.date_document_options.isVisible() is False
        dialog.date_source_document_radio.setChecked(True)
        assert dialog.date_document_options.isVisible() is True
        dialog.date_source_file_radio.setChecked(True)
        assert dialog.date_document_options.isVisible() is False
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_group_unchecked_hides_the_entire_date_filter_content(qapp, module_name, dialog_attr) -> None:
    # 02.09.2026 (Michael: "Wenn 'Nach Datum filtern' deaktiviert ist
    # sollten die anderen Datums Optionen nicht sichtbar sein.") -
    # QGroupBox.setCheckable() alone only disables (greys out, keeps
    # visible) its children; date_filter_content's own visibility must be
    # tied to the group's checked state so an unchecked group actually
    # hides the panel instead of just greying it out.
    dialog = _make_dialog(module_name, dialog_attr, "DateGroupHidesContent")
    try:
        assert dialog.date_filter_group.isChecked() is False
        assert dialog.date_filter_content.isVisible() is False
        dialog.date_filter_group.setChecked(True)
        assert dialog.date_filter_content.isVisible() is True
        dialog.date_filter_group.setChecked(False)
        assert dialog.date_filter_content.isVisible() is False
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
def test_custom_format_field_has_a_label_placeholder_and_tooltip(qapp, module_name, dialog_attr) -> None:
    # 02.09.2026 (Michael: "Und für den Freitext sollten eben alle
    # gültigen Formate eingebar sein, mit Beispielen.") - the field must
    # actually explain its own token syntax, not just accept it.
    dialog = _make_dialog(module_name, dialog_attr, "DateCustomFormatLabels")
    try:
        assert dialog.date_custom_format_label.text()
        assert dialog.date_custom_format_edit.placeholderText()
        assert dialog.date_custom_format_edit.toolTip()
        assert "YYYY" in dialog.date_custom_format_edit.toolTip()
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_custom_format_alone_is_enough_without_any_preset_checked(
    qapp, module_name, dialog_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildCustomAlone")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_format_iso_checkbox.setChecked(False)  # the only default format
        dialog.date_custom_format_edit.setText("MMMM D, YYYY")
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert error_key is None
        assert date_filter is not None
        assert date_filter.formats == frozenset()
        assert date_filter.custom_format == "MMMM D, YYYY"
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_custom_format_combines_with_a_preset(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildCustomPlusPreset")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_custom_format_edit.setText("MMMM D, YYYY")
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert error_key is None
        assert date_filter is not None
        assert date_filter.formats == frozenset({FORMAT_ISO})
        assert date_filter.custom_format == "MMMM D, YYYY"
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_blank_custom_format_is_not_treated_as_set(qapp, module_name, dialog_attr) -> None:
    # Whitespace-only input must fall back to None, not become a
    # zero-token pattern the validator would have to reject instead.
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildCustomBlank")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_custom_format_edit.setText("   ")
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert error_key is None
        assert date_filter is not None
        assert date_filter.custom_format is None
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_no_preset_and_no_custom_format_is_the_missing_format_error(
    qapp, module_name, dialog_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildNeitherFormat")
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
def test_build_date_filter_invalid_custom_format_is_an_error_even_with_a_preset_checked(
    qapp, module_name, dialog_attr
) -> None:
    # A preset being checked must not silently hide a typo in the custom
    # field - Michael typed it on purpose, so an unusable pattern there
    # should always be flagged rather than quietly ignored.
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildCustomInvalid")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_custom_format_edit.setText("YYYY-YYYY")
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert date_filter is None
        assert error_key == "merge_search.error_invalid_custom_date_format"
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_build_date_filter_plain_text_with_no_tokens_is_an_invalid_custom_format(
    qapp, module_name, dialog_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DateBuildCustomNoTokens")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_custom_format_edit.setText("kein Platzhalter hier")
        dialog.date_from_edit.setDate(dialog.date_from_edit.date().fromString("2026-01-01", "yyyy-MM-dd"))

        date_filter, error_key = dialog._build_date_filter()

        assert date_filter is None
        assert error_key == "merge_search.error_invalid_custom_date_format"
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


# --- calendar popup opens on today, not the 1900 "unset" sentinel --------
# Michael, after trying the date filter out: "Beim Datum Filter sollte
# nicht der 1.1.1900 drin stehen eher das aktuelle Datum."


def _open_calendar_popup(edit) -> None:
    """Clicks the QDateEdit's own dropdown arrow, the same way a user
    would - NOT edit.calendarWidget().show() directly, since that
    bypasses the exact internal re-sync (QDateTimeEdit resetting the
    popup's page back to the edit's current value on every open) this
    test exists to guard against. Confirmed by hand that this actually
    reproduces the real symptom before the fix (calendar page snapping
    back to January 1900) and the fix (page staying on the current
    month).

    02.09.2026, second attempt (see _configure_optional_date_edit()'s
    docstring, ui/merge_search_dialog.py) - the correction is now
    deferred via QTimer.singleShot(0, ...) rather than applied
    synchronously/reentrantly, so a plain click no longer suffices here
    either: QTest.qWait(0) pumps the event loop once to let that queued
    callback actually run, the same way it would on the very next spin
    of a real application's event loop.
    """
    opt = QStyleOptionSpinBox()
    opt.initFrom(edit)
    rect = edit.style().subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, edit)
    QTest.mouseClick(edit, Qt.LeftButton, Qt.NoModifier, rect.center())
    QTest.qWait(0)


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
@pytest.mark.parametrize("edit_attr", ["date_from_edit", "date_to_edit", "date_exact_edit"])
def test_calendar_popup_opens_on_the_current_month_while_the_field_is_unset(
    qapp, module_name, dialog_attr, edit_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, f"CalendarToday{edit_attr}")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_exact_checkbox.setChecked(edit_attr == "date_exact_edit")
        edit = getattr(dialog, edit_attr)
        today = QDate.currentDate()

        _open_calendar_popup(edit)

        calendar = edit.calendarWidget()
        assert (calendar.yearShown(), calendar.monthShown()) == (today.year(), today.month())
        # Still genuinely unset - only the popup's displayed page moved,
        # not the field's own value (which would silently start filtering
        # by today's date if it had).
        assert edit.date() == QDate(1900, 1, 1)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_picking_a_date_from_the_calendar_still_works_normally(qapp, module_name, dialog_attr) -> None:
    # Regression guard: the currentPageChanged snap-back-to-today guard
    # must not interfere once the user actually navigates or picks a date.
    dialog = _make_dialog(module_name, dialog_attr, "CalendarPickStillWorks")
    try:
        dialog.date_filter_group.setChecked(True)
        edit = dialog.date_from_edit

        _open_calendar_popup(edit)
        edit.calendarWidget().setSelectedDate(QDate(2019, 6, 15))
        assert edit.date() == QDate(2019, 6, 15)

        # Reopening the popup afterwards must show June 2019 (the field's
        # real value now), NOT jump back to today - the guard only ever
        # applies while the field is still the 1900 sentinel.
        _open_calendar_popup(edit)
        calendar = edit.calendarWidget()
        assert (calendar.yearShown(), calendar.monthShown()) == (2019, 6)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_date_filter_state_is_persisted_and_restored_across_dialog_reopen(qapp, module_name, dialog_attr) -> None:
    """Regression guard for 03.09.2026 (Michael: "Wenn beim Filter Datums
    Optionen ausgewählt sind, werden sie nicht gespeichert und sind beim
    nächstem Mal nicht mehr da."): every other field in this dialog
    (folder, Drive link, recursive, scope checkboxes, query history) is
    written in done() and read back in a _restore_*_state() call from the
    constructor - the date filter, added the same day as this test file's
    other coverage, was never wired into either. See
    _persist_date_filter_state()/_restore_date_filter_state() in
    ui/merge_search_dialog.py (shared by both dialogs)."""
    dialog = _make_dialog(module_name, dialog_attr, "DateFilterPersistence")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_source_document_radio.setChecked(True)
        dialog.date_region_header_checkbox.setChecked(True)
        dialog.date_region_ico_format_checkbox.setChecked(False)
        dialog.date_format_de_checkbox.setChecked(True)
        dialog.date_format_iso_checkbox.setChecked(False)
        dialog.date_custom_format_edit.setText("MMMM D, YYYY")
        dialog.date_exact_checkbox.setChecked(False)
        dialog.date_from_edit.setDate(QDate(2025, 3, 1))
        dialog.date_to_edit.setDate(QDate(2025, 9, 30))
    finally:
        dialog.close()  # routes through done(), same as every other persisted field

    reopened = _make_dialog(module_name, dialog_attr, "DateFilterPersistence")
    try:
        assert reopened.date_filter_group.isChecked() is True
        assert reopened.date_source_document_radio.isChecked() is True
        assert reopened.date_region_header_checkbox.isChecked() is True
        assert reopened.date_region_ico_format_checkbox.isChecked() is False
        assert reopened.date_format_de_checkbox.isChecked() is True
        assert reopened.date_format_iso_checkbox.isChecked() is False
        assert reopened.date_custom_format_edit.text() == "MMMM D, YYYY"
        assert reopened.date_exact_checkbox.isChecked() is False
        assert reopened.date_from_edit.date() == QDate(2025, 3, 1)
        assert reopened.date_to_edit.date() == QDate(2025, 9, 30)
    finally:
        reopened.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_date_filter_off_by_default_is_not_forced_on_by_a_stale_persisted_state(qapp, module_name, dialog_attr) -> None:
    """A dialog that has never had its date filter touched must still open
    with the filter off, exactly like test_date_filter_group_is_unchecked_by_default()
    - i.e. persistence must not affect a settings scope nothing was ever
    written to."""
    dialog = _make_dialog(module_name, dialog_attr, "DateFilterNeverTouched")
    try:
        assert dialog.date_filter_group.isChecked() is False
        assert dialog.date_exact_edit.date() == QDate(1900, 1, 1)
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_date_filter_exact_mode_and_unset_dates_persist_too(qapp, module_name, dialog_attr) -> None:
    """The Von/Bis-vs-Exakt toggle and an UNSET field (still the 1900
    sentinel - see _configure_optional_date_edit()) must round-trip too,
    not just a filled-in range."""
    dialog = _make_dialog(module_name, dialog_attr, "DateFilterExactPersistence")
    try:
        dialog.date_filter_group.setChecked(True)
        dialog.date_exact_checkbox.setChecked(True)
        dialog.date_exact_edit.setDate(QDate(2025, 12, 24))
        # date_from_edit/date_to_edit are left at their unset sentinel.
    finally:
        dialog.close()

    reopened = _make_dialog(module_name, dialog_attr, "DateFilterExactPersistence")
    try:
        assert reopened.date_exact_checkbox.isChecked() is True
        assert reopened.date_exact_edit.date() == QDate(2025, 12, 24)
        assert reopened.date_from_edit.date() == QDate(1900, 1, 1)
        assert reopened.date_to_edit.date() == QDate(1900, 1, 1)
    finally:
        reopened.close()
