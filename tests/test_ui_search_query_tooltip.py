"""Covers the 02.09.2026 query-field tooltip in MergeSearchDialog/
WordMergeSearchDialog - Michael: "Ja, einen Tooltip mit etwas mehr Text
und Beispiel wäre schon schön." (in response to being told the AND/OR
syntax was only hinted at in the field's label/placeholder).
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
    ("ui.merge_search_dialog", "MergeSearchDialog"),
    ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
]


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_query_field_has_a_tooltip_explaining_and_or_with_an_example(qapp, module_name, dialog_attr) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("de"), QSettings("PDF-Translator-Test", f"{dialog_attr}QueryTooltip"))
    try:
        tooltip = dialog.query_edit.toolTip()
        assert "UND" in tooltip
        assert "ODER" in tooltip
        assert "Acme" in tooltip  # a worked example, not just the bare keywords
        assert dialog.query_label.toolTip() == tooltip
    finally:
        dialog.close()


@pytest.mark.parametrize("module_name, dialog_attr", _DIALOGS)
def test_tooltip_is_translated_in_english(qapp, module_name, dialog_attr) -> None:
    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)
    dialog = DialogClass(LanguageManager("en"), QSettings("PDF-Translator-Test", f"{dialog_attr}QueryTooltipEn"))
    try:
        tooltip = dialog.query_edit.toolTip()
        assert "AND" in tooltip
        assert "OR" in tooltip
        assert "Acme" in tooltip
    finally:
        dialog.close()
