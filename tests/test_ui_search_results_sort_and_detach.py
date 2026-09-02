"""Covers three 02.09.2026 additions to the results section of
MergeSearchDialog/WordMergeSearchDialog (ui/merge_search_dialog.py,
ui/word_merge_search_dialog.py), all from the same round of feedback:

- "Die Sortierung nach Dateinamen [...] sortiert scheinbar nicht strikt
  nach Dateinamen [...] Es würde reichen die Sortierung im Anzeigefenster
  gemacht werden könnte." - Name/Datum sort buttons for the results list,
  mirroring MergeDialog's existing sort_by_name_button/sort_by_date_button
  (ui/merge_dialog.py, Fortsetzung 12) but adapted to a checkable
  QListWidget: sorting must not reset which matches the user already
  (un)checked.
- "Vielleicht das Ergebnis Fenster rausnehmbar machen." (confirmed via
  AskUserQuestion: a separate, freely movable/resizable window) - the
  detach/reattach toggle, both via the dialog's own button and via the
  floating window's own close button/X.
- The `_CurrentWidgetSizedStack` fix for "...nur ein Label 'Ordner' aber
  das scheint 1/3 des Dialogs einzunehmen" (source_stack sizing to its
  LARGEST page by default, per Qt's own QStackedWidget behavior, instead
  of the currently shown one).

Follows the established `_DIALOGS`-parametrized-across-both-dialogs shape
(see tests/test_ui_date_filter.py) since every one of these is duplicated
identically into both dialogs.

02.09.2026 addendum (Michael, second round: "Das Fenster erscheint nicht
[...] es geht keine neues Fenster auf.") - _DetachedResultsWindow's
`parent` was the root cause (was `None`, must be the owning dialog - see
that class's docstring in ui/merge_search_dialog.py). Confirmed by hand
under QT_QPA_PLATFORM=offscreen that this specific on-screen symptom does
NOT reproduce as a difference in `isVisible()` here - Qt's real modal-
window blocking is largely native-platform behavior (e.g. Windows'
EnableWindow() on sibling top-levels), which the offscreen QPA plugin
doesn't simulate; both a `parent=None` and a `parent=dialog` window report
`isVisible() is True` under offscreen. So `parent() is dialog` (the actual
fix) is what's asserted below, not visibility - that's the one invariant
that's both correct and reliably testable outside a real display.
"""
from __future__ import annotations

import importlib
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem

from ui.merge_search import IcoSearchMatch, IcoSearchResult


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


_DIALOGS = [
    ("ui.merge_search_dialog", "MergeSearchDialog"),
    ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
]


def _make_dialog(module_name: str, dialog_attr: str, settings_key: str):
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    from ui.i18n import LanguageManager

    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}{settings_key}"))
    dialog.show()  # isVisible()/sizeHint() need an actually-shown top-level
    return dialog


def _add_result(dialog, path: Path, checked: bool = True) -> None:
    item = QListWidgetItem(path.name)
    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    item.setData(Qt.UserRole, path)
    dialog.results.addItem(item)


# --- scope checkbox tooltips (Michael: "Bedeutet jetzt 'ICO Format ---


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_scope_checkboxes_have_distinct_clarifying_tooltips(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "ScopeTooltips")
    try:
        ico_tip = dialog.scope_ico_format_checkbox.toolTip()
        header_tip = dialog.scope_header_checkbox.toolTip()
        full_text_tip = dialog.scope_full_text_checkbox.toolTip()
        assert ico_tip and header_tip and full_text_tip
        assert len({ico_tip, header_tip, full_text_tip}) == 3  # all different
    finally:
        dialog.close()


# --- sort buttons ----------------------------------------------------------


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_buttons_disabled_with_zero_or_one_result(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortDisabledFew")
    try:
        dialog._update_results_button_states()
        assert dialog.sort_results_by_name_button.isEnabled() is False
        assert dialog.sort_results_by_date_button.isEnabled() is False

        _add_result(dialog, Path("/tmp/only-one.pdf"))
        dialog._update_results_button_states()
        assert dialog.sort_results_by_name_button.isEnabled() is False
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_name_orders_alphabetically_and_toggles_direction(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortByName")
    try:
        for name in ("Zeta.pdf", "Alpha.pdf", "Mitte.pdf"):
            _add_result(dialog, Path(f"/tmp/{name}"))
        dialog._update_results_button_states()
        assert dialog.sort_results_by_name_button.isEnabled() is True

        dialog._sort_results_by_name()
        names = [dialog.results.item(i).data(Qt.UserRole).name for i in range(dialog.results.count())]
        assert names == ["Alpha.pdf", "Mitte.pdf", "Zeta.pdf"]

        dialog._sort_results_by_name()  # second click reverses
        names = [dialog.results.item(i).data(Qt.UserRole).name for i in range(dialog.results.count())]
        assert names == ["Zeta.pdf", "Mitte.pdf", "Alpha.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_name_sorts_ico_numbered_filenames_numerically(qapp, module_name, dialog_attr) -> None:
    # 02.09.2026 (Michael: "Die Dateinamen fangen hier aktuell alle mit
    # Nummern an [...] Ich dachte das nach Namen sortieren Standardmässig
    # immer erst die Nummern ausliest [...]") - see tests/test_natural_sort.py
    # for the underlying key's own tests, and MergeDialog's identical case
    # in tests/test_ui_merge_sort.py.
    dialog = _make_dialog(module_name, dialog_attr, "SortByNameIco")
    try:
        for name in ("1747 ABSENCE.pdf", "176 ChinaAMC.pdf", "1750 ANEMNESIS.pdf"):
            _add_result(dialog, Path(f"/tmp/{name}"))

        dialog._sort_results_by_name()
        names = [dialog.results.item(i).data(Qt.UserRole).name for i in range(dialog.results.count())]
        assert names == ["176 ChinaAMC.pdf", "1747 ABSENCE.pdf", "1750 ANEMNESIS.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_by_date_uses_file_mtime_and_toggles_direction(qapp, module_name, dialog_attr, tmp_path) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortByDate")
    try:
        older = tmp_path / "older.pdf"
        newer = tmp_path / "newer.pdf"
        older.write_bytes(b"x")
        newer.write_bytes(b"x")
        now = time.time()
        os.utime(older, (now - 1000, now - 1000))
        os.utime(newer, (now, now))
        _add_result(dialog, newer)
        _add_result(dialog, older)

        dialog._sort_results_by_date()  # ascending: oldest first
        names = [dialog.results.item(i).data(Qt.UserRole).name for i in range(dialog.results.count())]
        assert names == ["older.pdf", "newer.pdf"]

        dialog._sort_results_by_date()  # descending: newest first
        names = [dialog.results.item(i).data(Qt.UserRole).name for i in range(dialog.results.count())]
        assert names == ["newer.pdf", "older.pdf"]
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sorting_preserves_each_items_check_state(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortPreservesChecks")
    try:
        _add_result(dialog, Path("/tmp/Zeta.pdf"), checked=True)
        _add_result(dialog, Path("/tmp/Alpha.pdf"), checked=False)

        dialog._sort_results_by_name()

        by_name = {
            dialog.results.item(i).data(Qt.UserRole).name: dialog.results.item(i).checkState()
            for i in range(dialog.results.count())
        }
        assert by_name["Zeta.pdf"] == Qt.Checked
        assert by_name["Alpha.pdf"] == Qt.Unchecked
    finally:
        dialog.close()


# --- detach/reattach ---------------------------------------------------


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_detach_shows_placeholder_and_moves_the_list_into_its_own_window(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DetachBasic")
    try:
        _add_result(dialog, Path("/tmp/a.pdf"))
        assert dialog._detached_results_window is None
        assert dialog.results_stack.currentWidget() is dialog.results

        dialog._toggle_detach_results()

        assert dialog._detached_results_window is not None
        assert dialog.results_stack.currentWidget() is dialog.results_placeholder_label
        assert dialog.results.parent() is dialog._detached_results_window
        assert dialog.detach_results_button.text() == dialog.language.text("merge_search.reattach_results_button")
        assert dialog.results.count() == 1  # the list itself, and its content, are untouched
        # 02.09.2026 (Michael, after the parent=self fix: "Jetzt geht zwar
        # ein Fenster auf, es wird aber keine Liste angezeigt.") -
        # results_stack.setCurrentWidget() a few lines up in _detach_results()
        # explicitly hide()s self.results as part of switching away from it;
        # reparenting it into the new window's layout does NOT implicitly
        # re-show it. Regression guard for the explicit self.results.show()
        # call added there.
        assert dialog.results.isVisible() is True
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_detached_window_is_parented_to_the_dialog_not_none(qapp, module_name, dialog_attr) -> None:
    # 02.09.2026 (Michael: "Das Fenster erscheint nicht wenn ich auf
    # 'Ergebnisliste in eigenem Fenster öffnen' anklicke. Die Liste
    # verschwindet aber es geht keine neues Fenster auf.") - this dialog is
    # normally opened via exec() (application-modal), and Qt never surfaces
    # a top-level window that isn't a descendant of the active modal widget
    # while that exec() loop is running. `parent=None` (the original bug)
    # produced exactly that: a window that silently never appears. This is
    # a regression guard for the fix (parent=self, see
    # _DetachedResultsWindow's docstring) - QT_QPA_PLATFORM=offscreen
    # doesn't reproduce the actual on-screen symptom (see this module's own
    # docstring), so `parent()` is the one invariant that's both correct
    # and reliably testable here.
    dialog = _make_dialog(module_name, dialog_attr, "DetachParent")
    try:
        _add_result(dialog, Path("/tmp/a.pdf"))
        dialog._toggle_detach_results()
        window = dialog._detached_results_window
        assert window.parent() is dialog
        assert window.parent() is not None
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_reattach_via_toggle_button_restores_the_list_into_the_dialog(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "ReattachButton")
    try:
        _add_result(dialog, Path("/tmp/a.pdf"))
        dialog._toggle_detach_results()
        dialog._toggle_detach_results()

        assert dialog._detached_results_window is None
        assert dialog.results_stack.currentWidget() is dialog.results
        assert dialog.results.parent() is dialog.results_stack
        assert dialog.results.count() == 1
        assert dialog.detach_results_button.text() == dialog.language.text("merge_search.detach_results_button")
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_reattach_via_the_floating_windows_own_close_button(qapp, module_name, dialog_attr) -> None:
    # The dialog's "Andocken" toggle is not the only way to close the
    # floating window - the user can also just close it directly (the
    # window's own X). Both paths must reattach the list the same way.
    dialog = _make_dialog(module_name, dialog_attr, "ReattachViaX")
    try:
        _add_result(dialog, Path("/tmp/a.pdf"))
        dialog._toggle_detach_results()
        window = dialog._detached_results_window

        window.close()

        assert dialog._detached_results_window is None
        assert dialog.results_stack.currentWidget() is dialog.results
        assert dialog.results.count() == 1
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_closing_the_dialog_while_detached_reattaches_first(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "DoneReattaches")
    try:
        _add_result(dialog, Path("/tmp/a.pdf"))
        dialog._toggle_detach_results()
        assert dialog._detached_results_window is not None

        dialog.done(0)

        assert dialog._detached_results_window is None
    finally:
        dialog.close()


# --- source_stack sizes to the currently shown page, not the largest ------


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_source_stack_size_hint_tracks_the_current_page_not_the_largest(qapp, module_name, dialog_attr) -> None:
    # 02.09.2026 (Michael: "...zwischen dem Suchordner Feld und den
    # Auswahl Optionen 'Lokaler Ordner' und 'Google Drive' [...] nur ein
    # Label 'Ordner' aber das scheint 1/3 des Dialogs einzunehmen.") - the
    # Drive panel (credentials fields, connection status, ...) is much
    # taller than the local-folder panel; source_stack must report the
    # CURRENT page's height, not Qt's own QStackedWidget default (the max
    # over every page).
    dialog = _make_dialog(module_name, dialog_attr, "SourceStackSizing")
    try:
        local_hint = dialog.source_stack.sizeHint().height()
        assert local_hint == dialog.source_stack.widget(0).sizeHint().height()

        dialog.source_drive_radio.setChecked(True)
        drive_hint = dialog.source_stack.sizeHint().height()
        assert drive_hint == dialog.source_stack.widget(1).sizeHint().height()

        # The Drive panel is meaningfully taller - this is the actual
        # symptom Michael reported (a huge gap around the short local
        # panel to match the tall Drive panel's height).
        assert drive_hint > local_hint
    finally:
        dialog.close()


# --- query field: last-used text remembered, label wording (02.09.2026) ---
# Michael, third round of feedback on this same search dialog: "Es sollte
# noch die letzten Suchbegriffe im Suchfeld angezeigt werden. Ausserdem
# wird in der Überschrift über dem Suchfeld nicht die Operatoren mit
# angezeigt. Die Aussage 'leer = alle Dateien' ist eher verwirrend und
# sollte dort raus."


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_last_query_text_is_restored_on_the_next_open(qapp, module_name, dialog_attr) -> None:
    settings = QSettings("PDF-Translator-Test", f"{dialog_attr}LastQuery")
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    from ui.i18n import LanguageManager

    first = DialogClass(LanguageManager("de"), settings)
    try:
        assert first.query_edit.text() == ""  # nothing remembered yet
        first.query_edit.setText("Acme UND Vertrag")
        first.done(0)  # QDialog.reject()/accept() both route through done()
    finally:
        first.close()

    second = DialogClass(LanguageManager("de"), settings)
    try:
        assert second.query_edit.text() == "Acme UND Vertrag"
    finally:
        second.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_query_label_mentions_symbol_operators_and_drops_the_confusing_empty_hint(
    qapp, module_name, dialog_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "QueryLabelWording")
    try:
        label_text = dialog.query_label.text()
        assert "&&" in label_text and "||" in label_text
        # "leer = alle Dateien" / "empty = every file" - Michael: confusing,
        # remove from the label above the field (the placeholder text
        # inside the empty field itself still explains this, unchanged).
        assert "leer" not in label_text.lower()
        assert "empty" not in label_text.lower()
    finally:
        dialog.close()


# --- results list label shows only the Developer value (02.09.2026) ------
# Michael, after the detach-window fixes above: "Noch zur Liste. Es
# reicht wenn hinter dem Namen nur der Teil mit Developer erscheint und
# nicht die ganze 1. Seite. Wenn kein Developer gefunden wird, darf es
# leer bleiben."


def _finish_with_snippet(dialog, path: Path, snippet: str) -> None:
    result = IcoSearchResult(matches=[IcoSearchMatch(path=path, snippet=snippet)], scanned=1)
    dialog._on_finished(result)


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_result_label_shows_only_the_developer_value_not_the_whole_snippet(
    qapp, module_name, dialog_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "ResultLabelDeveloper")
    try:
        snippet = (
            "Developer: StellarRussia\nQSI ICO: AUREXIS\n"
            "Issuer Address: 123 Main St\nAsset Matrix: a long block of "
            "unrelated first-page text that used to spill into the label"
        )
        _finish_with_snippet(dialog, Path("/tmp/a.pdf"), snippet)

        label = dialog.results.item(0).text()
        assert label == "a.pdf — StellarRussia"
        # The full snippet is still available on hover, unchanged.
        assert "Asset Matrix" in dialog.results.item(0).toolTip()
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_result_label_is_just_the_filename_when_no_developer_is_found(
    qapp, module_name, dialog_attr
) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "ResultLabelNoDeveloper")
    try:
        _finish_with_snippet(dialog, Path("/tmp/plain.pdf"), "Issuer Address: 123 Main St")

        assert dialog.results.item(0).text() == "plain.pdf"
    finally:
        dialog.close()


# --- detached window keeps the sort buttons usable (02.09.2026) ----------
# Michael, same round: "Dann sollten beim eigenen Fenster die gleichen
# Sortierbuttons angezeigt werde wie im Original Fenster sonst ist das
# Fenster recht nutzlos."


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_sort_buttons_move_into_the_detached_window_and_back(qapp, module_name, dialog_attr) -> None:
    dialog = _make_dialog(module_name, dialog_attr, "SortButtonsFollowWindow")
    try:
        _add_result(dialog, Path("/tmp/a.pdf"))
        assert dialog.sort_results_by_name_button.parent() is dialog  # not detached yet

        dialog._toggle_detach_results()
        window = dialog._detached_results_window
        assert dialog.sort_results_by_name_button.parent() is window
        assert dialog.sort_results_by_date_button.parent() is window
        # Still fully functional while detached - operates on self.results
        # directly, regardless of which widget currently parents the button.
        _add_result(dialog, Path("/tmp/z.pdf"))
        dialog._sort_results_by_name()
        names = [dialog.results.item(i).data(Qt.UserRole).name for i in range(dialog.results.count())]
        assert names == ["a.pdf", "z.pdf"]

        dialog._toggle_detach_results()  # reattach

        assert dialog.sort_results_by_name_button.parent() is dialog
        assert dialog.sort_results_by_date_button.parent() is dialog
        # Back in their original slot in select_row - not just anywhere.
        row_widgets = [dialog.select_row.itemAt(i).widget() for i in range(dialog.select_row.count())]
        assert row_widgets[:5] == [
            dialog.select_all_button,
            dialog.select_none_button,
            dialog.sort_results_by_name_button,
            dialog.sort_results_by_date_button,
            dialog.detach_results_button,
        ]
    finally:
        dialog.close()
