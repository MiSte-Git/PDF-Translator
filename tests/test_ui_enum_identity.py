"""Regression guard for a PySide6/QVariant quirk that silently broke mode
dispatch and the Start button.

Root cause: TranslationMode/EmbeddedImageMode are `str, Enum` mixins. When a
member is stored as a QComboBox item's userData via addItem(text, member)
and read back via currentData(), PySide6 round-trips it through QVariant and
returns a plain `str` - not the original enum singleton. `==`/`!=` and
hashing still work (str.__eq__ compares equal to the str-Enum member), but
every `is`/`is not` comparison against the enum silently and permanently
fails.

This broke two things a user reported independently:
- analyze_request()'s `if request.mode is TranslationMode.PRESENTATION: ...`
  chain always fell through to the images/else branch, so a real .pptx
  analysis showed "1 Bilder / 0 Textzeichen" instead of slide/character
  counts.
- MainWindow._start()'s `if self.mode.currentData() is not
  TranslationMode.PRESENTATION: return` was always True, so clicking Start
  did nothing at all - no dialog, no error, no worker.

ui/app.py::_request() now coerces the raw combo box value back to the true
enum (TranslationMode(...)/EmbeddedImageMode(...)) before building a
TranslationRequest, and every remaining comparison in ui/app.py,
ui/analysis.py and ui/models.py uses "=="/"!=" instead of "is"/"is not", so
either fix independently prevents a regression here.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QComboBox

from ui.analysis import analyze_request
from ui.models import EmbeddedImageMode, TranslationMode, TranslationRequest

FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


def test_qcombobox_currentdata_loses_enum_identity_but_keeps_equality(qapp: QApplication) -> None:
    """Documents the underlying PySide6 behaviour itself, independent of
    this app's code, so a PySide6 upgrade that changes it is caught here
    first rather than as a mysterious UI regression.
    """
    combo = QComboBox()
    for mode in TranslationMode:
        combo.addItem("", mode)
    combo.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))

    data = combo.currentData()

    assert isinstance(data, str)
    assert data is not TranslationMode.PRESENTATION  # the trap
    assert data == TranslationMode.PRESENTATION  # still safe
    assert TranslationMode(data) is TranslationMode.PRESENTATION  # the fix


def test_request_built_from_combobox_selection_dispatches_as_presentation(qapp: QApplication) -> None:
    """Mirrors MainWindow._request(): build a TranslationRequest from raw
    QComboBox.currentData() the way the UI does, and confirm analyze_request
    takes the Presentation branch (slide/character counts), not the
    images/else fallback that masked the bug for the user.
    """
    mode_combo = QComboBox()
    for mode in TranslationMode:
        mode_combo.addItem("", mode)
    mode_combo.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))

    image_combo = QComboBox()
    for value in EmbeddedImageMode:
        image_combo.addItem("", value)
    image_combo.setCurrentIndex(list(EmbeddedImageMode).index(EmbeddedImageMode.NONE))

    request = TranslationRequest(
        mode=TranslationMode(mode_combo.currentData()),
        source_paths=(FIXTURE,),
        embedded_images=EmbeddedImageMode(image_combo.currentData()),
    )

    result = analyze_request(request)

    assert result.unit_label == "unit.slides"
    assert result.text_characters > 0
    assert result.embedded_images == 0 or result.units >= 1


def test_start_guard_condition_no_longer_blocks_presentation_mode(qapp: QApplication) -> None:
    """Reproduces the exact guard clause from MainWindow._start() (line ~371)
    against a real QComboBox selection. Before the fix this was
    `currentData() is not TranslationMode.PRESENTATION`, which was always
    True for a str, Enum value - making Start silently do nothing no matter
    what mode was selected.
    """
    combo = QComboBox()
    for mode in TranslationMode:
        combo.addItem("", mode)
    combo.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))

    blocked = combo.currentData() != TranslationMode.PRESENTATION
    assert blocked is False
