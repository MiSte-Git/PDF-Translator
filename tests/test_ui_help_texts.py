"""Covers the 07.09.2026 Feature (Michael: "zu jedem Button, Option usw.
auch ein richtiger Hilfetext existiert") - jedes Bedienelement im
Hauptfenster bekommt einen kurzen Tooltip (Hover) UND einen ausführlichen
WhatsThis-Text (abrufbar über Hilfe -> Direkthilfe bzw. Umschalt+F1), in
allen 9 Sprachen.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_every_help_widget_has_tooltip_and_whatsthis_in_every_language(qapp) -> None:
    from ui.app import MainWindow
    from ui.i18n_data import CATALOGUES

    window = MainWindow()
    try:
        assert len(window._help_widgets) >= 25
        for code in CATALOGUES:
            window.language.set_language(code)
            for widget, tooltip_key, whatsthis_key in window._help_widgets:
                assert widget.toolTip().strip(), (code, tooltip_key)
                assert widget.whatsThis().strip(), (code, whatsthis_key)
            for lang_code, button in window.flag_buttons.items():
                assert button.toolTip().strip(), (code, lang_code)
                assert button.whatsThis().strip(), (code, lang_code)
    finally:
        window.close()


def test_whats_this_menu_action_has_shortcut_and_triggers_mode(qapp) -> None:
    from ui.app import MainWindow

    window = MainWindow()
    try:
        labels = [action.text() for action in window.help_menu.actions()]
        assert "Direkthilfe" in labels
        action = window.help_menu.actions()[labels.index("Direkthilfe")]
        assert action.shortcut() == QKeySequence(QKeySequence.WhatsThis)
        action.trigger()  # must not raise
    finally:
        window.close()


def test_help_keys_translated_for_all_nine_locales() -> None:
    from ui.i18n_data import CATALOGUES

    new_keys = [
        "mode.tooltip", "mode.whatsthis", "source.tooltip", "source.whatsthis",
        "source_label.tooltip", "source_label.whatsthis", "image_mode.tooltip", "image_mode.whatsthis",
        "provider.tooltip", "provider.whatsthis", "source_lang.tooltip", "source_lang.whatsthis",
        "target_lang.tooltip", "target_lang.whatsthis", "protected.tooltip", "protected.whatsthis",
        "ocr_engine_field.tooltip", "ocr_engine_field.whatsthis",
        "inpainting_backend_field.tooltip", "inpainting_backend_field.whatsthis",
        "merge.tooltip", "merge.whatsthis", "word_merge.tooltip", "word_merge.whatsthis",
        "analysis.button.tooltip", "analysis.button.whatsthis",
        "analysis.checked.tooltip", "analysis.checked.whatsthis",
        "start.tooltip", "start.whatsthis", "job.cancel.tooltip", "job.cancel.whatsthis",
        "job.open_folder.tooltip", "job.open_folder.whatsthis",
        "job.open_report.tooltip", "job.open_report.whatsthis",
        "job.correct_translation.tooltip", "job.correct_translation.whatsthis",
        "settings.button.tooltip", "settings.button.whatsthis",
        "update_hint.tooltip", "update_hint.whatsthis",
        "flag_row.whatsthis", "menu.help.whats_this",
    ]
    assert len(new_keys) == 44
    for code, catalogue in CATALOGUES.items():
        for key in new_keys:
            assert key in catalogue, (code, key)
            assert catalogue[key].strip(), (code, key)


def test_no_duplicate_keys_in_any_catalogue() -> None:
    """A Python dict literal silently keeps the LAST of two duplicate
    keys instead of erroring - this guards against that class of mistake
    slipping into ui/i18n_data.py unnoticed (e.g. two help.* keys typed
    identically for two different widgets)."""
    import ast
    from pathlib import Path

    source = Path("ui/i18n_data.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    checked = 0
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ("DE", "EN", "FR", "ES", "IT", "NL", "FI", "HR", "RU")
        ):
            keys = [k.value for k in node.value.keys]
            assert len(keys) == len(set(keys)), (node.targets[0].id, "duplicate keys found")
            checked += 1
    assert checked == 9
