"""Covers the 02.09.2026 "Dateien zusammenführen" card in MainWindow
(ui/app.py) - Michael: "Sollten die beiden Optionen [...] mit in die
'Vorgang' Auswahlbox? Oder sollten wir Rahmen für Übersetzung und für
'PDF/DOCX' Zusammenführen machen. So ist es ein unangenehmer Mix." -
merge_button/word_merge_button used to sit as two unlabeled rows inside
self.form/config_box, sandwiched between the mode combo and the source-
file row. They now live in their own QGroupBox (self.merge_box), placed
ABOVE config_box (confirmed with Michael via AskUserQuestion), reusing
the config_box/cost_box/job_box "stack of cards" pattern already
established in this window.

Relies on tests/conftest.py's autouse `_isolated_qsettings` fixture for
QSettings isolation (see tests/test_ui_hardware_check_dialog.py for the
same pattern).
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFormLayout

from ui.app import MainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_merge_buttons_live_in_their_own_card_not_in_the_config_form(qapp) -> None:
    window = MainWindow()
    try:
        # Not rows of self.form/config_box any more.
        for row in range(window.form.rowCount()):
            field = window.form.itemAt(row, QFormLayout.FieldRole)
            widget = field.widget() if field is not None else None
            assert widget is not window.merge_button
            assert widget is not window.word_merge_button

        assert window.merge_button.parent() is window.merge_box
        assert window.word_merge_button.parent() is window.merge_box
    finally:
        window.close()


def test_merge_box_is_titled_and_placed_above_config_box(qapp) -> None:
    window = MainWindow()
    try:
        assert window.merge_box.title() == window.language.text("merge_box.group")

        root = window.centralWidget().layout()
        positions = {}
        for i in range(root.count()):
            widget = root.itemAt(i).widget()
            if widget is window.merge_box:
                positions["merge_box"] = i
            elif widget is window.config_box:
                positions["config_box"] = i
        assert positions["merge_box"] < positions["config_box"]
    finally:
        window.close()


def test_merge_buttons_still_disabled_while_a_job_is_running(qapp) -> None:
    # Relocating the buttons must not break _set_running()'s existing
    # enable/disable bookkeeping (ui/app.py:_set_running()).
    window = MainWindow()
    try:
        window._set_running(True)
        assert window.merge_button.isEnabled() is False
        assert window.word_merge_button.isEnabled() is False

        window._set_running(False)
        assert window.merge_button.isEnabled() is True
        assert window.word_merge_button.isEnabled() is True
    finally:
        window.close()


def test_merge_button_labels_survive_retranslation(qapp) -> None:
    window = MainWindow()
    try:
        window.language.set_language("en")
        assert window.merge_box.title() == window.language.text("merge_box.group")
        assert window.merge_button.text() == window.language.text("merge.button")
        assert window.word_merge_button.text() == window.language.text("word_merge.button")
    finally:
        window.close()
