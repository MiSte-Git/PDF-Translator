"""Covers the 03.09.2026 fix (Michael: "das UI [geht] über die Höhe des
Bildschirms leicht hinaus und [ist] nur in der Breite einstellbar und nicht
in der Höhe. Der Button unten rechts ist dadurch nicht sichtbar.").

Root cause: MainWindow stacked its cards directly as the central widget,
so the window's minimum height was the sum of all card minimums - after
the 02.09. "Dateien zusammenführen" card that exceeded a 768/800px screen,
Qt refused to shrink the window vertically and the settings row fell off
the bottom. Fix: the card stack lives inside a frameless QScrollArea (so
the window's minimum height is decoupled from the content's) and the
880x760 default size is clamped to the available screen area on first
show.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QScrollArea


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_central_widget_is_a_resizable_frameless_scroll_area(qapp) -> None:
    from ui.app import MainWindow

    window = MainWindow()
    try:
        scroll = window.centralWidget()
        assert isinstance(scroll, QScrollArea)
        assert scroll.widgetResizable()
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
        # the card stack must still be reachable for everything that used
        # to be the central widget
        assert scroll.widget() is not None
        assert scroll.widget().isAncestorOf(window.settings_button)
    finally:
        window.close()


def test_window_minimum_height_is_decoupled_from_card_stack(qapp) -> None:
    from ui.app import MainWindow

    window = MainWindow()
    try:
        content_min = window.centralWidget().widget().minimumSizeHint().height()
        window_min = window.minimumSizeHint().height()
        # Without the scroll area these two were equal (and both > 760).
        assert window_min < content_min
        assert window_min < 400
    finally:
        window.close()


def test_initial_size_never_exceeds_available_screen(qapp) -> None:
    from ui.app import MainWindow

    window = MainWindow()
    try:
        available = QApplication.primaryScreen().availableGeometry()
        assert window.width() <= available.width()
        assert window.height() <= available.height()
    finally:
        window.close()
