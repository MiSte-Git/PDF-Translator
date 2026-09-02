"""Covers the 02.09.2026 sort-by-name/sort-by-date feature in MergeDialog/
WordMergeDialog (ui/merge_dialog.py, ui/word_merge_dialog.py) - Michael:
"Was mir sonst noch fehlt ist eine Sortierung wenn wir die PDFs
zusammenführen wollen. Per Dateiname, per Datum, auf und absteigend."
Confirmed design (AskUserQuestion, 02.09.2026): two buttons next to the
existing move-up/move-down buttons, each toggling its own next sort
direction on every click (shown as a ▲/▼ arrow in the button's label).

Both dialogs duplicate the same source table/button-row code (see their
own module docstrings), so every scenario below is parametrized across
both.
"""
from __future__ import annotations

import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ui.i18n import LanguageManager


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


_DIALOGS = [
    ("ui.merge_dialog", "MergeDialog"),
    ("ui.word_merge_dialog", "WordMergeDialog"),
]


def _make_dialog(module_name: str, dialog_attr: str, settings_suffix: str):
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    return DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}{settings_suffix}"))


def _row_names(dialog) -> list[str]:
    return [dialog.table.item(row, 0).text() for row in range(dialog.table.rowCount())]


def _populate_with_distinct_mtimes(tmp_path: Path, names: list[str]) -> list[Path]:
    """Creates one file per name under tmp_path with strictly increasing
    modification times (names[0] oldest) - real file timestamps rather
    than relying on creation order/sleeps, so the date-sort assertions
    are exact and fast.
    """
    paths = []
    base = time.time() - 1000
    for i, name in enumerate(names):
        path = tmp_path / name
        path.write_bytes(b"stub")
        mtime = base + i * 10
        os.utime(path, (mtime, mtime))
        paths.append(path)
    return paths


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_name_ascending_then_descending(qapp, module_name, dialog_attr, tmp_path: Path) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortName")
    try:
        for path in _populate_with_distinct_mtimes(tmp_path, ["charlie.pdf", "alpha.pdf", "bravo.pdf"]):
            dialog._append_row(path)
        assert _row_names(dialog) == ["charlie.pdf", "alpha.pdf", "bravo.pdf"]

        dialog._sort_by_name()
        assert _row_names(dialog) == ["alpha.pdf", "bravo.pdf", "charlie.pdf"]

        dialog._sort_by_name()  # second click reverses direction
        assert _row_names(dialog) == ["charlie.pdf", "bravo.pdf", "alpha.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_name_sorts_ico_numbered_filenames_numerically(qapp, module_name, dialog_attr, tmp_path: Path) -> None:
    # 02.09.2026 (Michael: "Die Dateinamen fangen hier aktuell alle mit
    # Nummern an [...] Ich dachte das nach Namen sortieren Standardmässig
    # immer erst die Nummern ausliest [...]") - a plain string sort put
    # "176 ChinaAMC.pdf" AFTER "1747 ABSENCE.pdf" (see
    # tests/test_natural_sort.py for the underlying key's own tests).
    dialog = _make_dialog(module_name, dialog_attr, "SortNameIco")
    try:
        names = ["1747 ABSENCE.pdf", "176 ChinaAMC.pdf", "1750 ANEMNESIS.pdf"]
        for path in _populate_with_distinct_mtimes(tmp_path, names):
            dialog._append_row(path)

        dialog._sort_by_name()
        assert _row_names(dialog) == ["176 ChinaAMC.pdf", "1747 ABSENCE.pdf", "1750 ANEMNESIS.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_name_is_case_insensitive(qapp, module_name, dialog_attr, tmp_path: Path) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortNameCase")
    try:
        for path in _populate_with_distinct_mtimes(tmp_path, ["Bravo.pdf", "alpha.pdf"]):
            dialog._append_row(path)
        dialog._sort_by_name()
        assert _row_names(dialog) == ["alpha.pdf", "Bravo.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_date_ascending_then_descending(qapp, module_name, dialog_attr, tmp_path: Path) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortDate")
    try:
        # oldest -> newest: alpha, bravo, charlie - added in an unrelated order
        paths = _populate_with_distinct_mtimes(tmp_path, ["alpha.pdf", "bravo.pdf", "charlie.pdf"])
        for path in [paths[2], paths[0], paths[1]]:  # charlie, alpha, bravo
            dialog._append_row(path)
        assert _row_names(dialog) == ["charlie.pdf", "alpha.pdf", "bravo.pdf"]

        dialog._sort_by_date()  # oldest first
        assert _row_names(dialog) == ["alpha.pdf", "bravo.pdf", "charlie.pdf"]

        dialog._sort_by_date()  # newest first
        assert _row_names(dialog) == ["charlie.pdf", "bravo.pdf", "alpha.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_direction_arrow_reflects_the_next_click(qapp, module_name, dialog_attr, tmp_path: Path) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortArrow")
    try:
        for path in _populate_with_distinct_mtimes(tmp_path, ["a.pdf", "b.pdf"]):
            dialog._append_row(path)

        assert dialog.sort_by_name_button.text().endswith("▲")
        dialog._sort_by_name()
        assert dialog.sort_by_name_button.text().endswith("▼")
        dialog._sort_by_name()
        assert dialog.sort_by_name_button.text().endswith("▲")

        # the date button's own direction is independent of the name button's
        assert dialog.sort_by_date_button.text().endswith("▲")
        dialog._sort_by_date()
        assert dialog.sort_by_date_button.text().endswith("▼")
        assert dialog.sort_by_name_button.text().endswith("▲")  # unaffected by the date click
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_buttons_disabled_with_fewer_than_two_rows(qapp, module_name, dialog_attr, tmp_path: Path) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortDisabled")
    try:
        assert dialog.sort_by_name_button.isEnabled() is False
        assert dialog.sort_by_date_button.isEnabled() is False

        [path] = _populate_with_distinct_mtimes(tmp_path, ["only.pdf"])
        dialog._append_row(path)
        dialog._update_button_states()
        assert dialog.sort_by_name_button.isEnabled() is False

        dialog._append_row(_populate_with_distinct_mtimes(tmp_path, ["second.pdf"])[0])
        dialog._update_button_states()
        assert dialog.sort_by_name_button.isEnabled() is True
        assert dialog.sort_by_date_button.isEnabled() is True
    finally:
        dialog.close()


def test_pdf_dialog_sort_keeps_the_pages_field_attached_to_its_file(qapp, tmp_path: Path) -> None:
    # MergeDialog-only: the "pages" column must travel with its row during
    # a sort, not stay pinned to the row index (regression guard for the
    # 2-column table - WordMergeDialog has no pages column to lose).
    from ui.merge_dialog import MergeDialog

    dialog = MergeDialog(LanguageManager("de"), QSettings("PDF-Translator-Test", "MergeDialogSortPagesTravel"))
    try:
        paths = _populate_with_distinct_mtimes(tmp_path, ["bravo.pdf", "alpha.pdf"])
        for path in paths:
            dialog._append_row(path)
        dialog.table.cellWidget(0, 1).setText("1-3")  # bravo.pdf's pages
        dialog.table.cellWidget(1, 1).setText("5")  # alpha.pdf's pages

        dialog._sort_by_name()  # alpha.pdf, bravo.pdf afterwards

        assert _row_names(dialog) == ["alpha.pdf", "bravo.pdf"]
        assert dialog.table.cellWidget(0, 1).text() == "5"  # travels with alpha.pdf
        assert dialog.table.cellWidget(1, 1).text() == "1-3"  # travels with bravo.pdf
    finally:
        dialog.close()
