"""Tests for ui/app.py's "Hilfe" -> Hardware-Test feature (01.09.2026,
Michael: "Ist es möglich den HW Check beim Installieren zu speichern und in
einem Hilfe Menü in der App eine Möglichkeit den HW Test anzeigen zu lassen
und auch noch mal zu wiederholen. Dort sollte auch angezeigt werden ob die
HW die Mindestanforderung erfüllt.") - HardwareCheckDialog, _format_checked_at(),
and MainWindow's "Hilfe" menu wiring.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation; bootstrap.gpu_check.paths.gpu_check_marker_file() is
separately redirected per test below, so this file never touches a real
per-machine bootstrapper install either - same pattern as
tests/test_ui_bootstrap_language_handoff.py.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import ui.app as app_module
from bootstrap.gpu_check import GpuInfo, save_gpu_check_result
from ui.app import HardwareCheckDialog, MainWindow, _format_checked_at
from ui.i18n import LanguageManager


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _patch_marker_path(monkeypatch, tmp_path):
    marker_path = tmp_path / "gpu_check.json"
    monkeypatch.setattr("bootstrap.gpu_check.paths.gpu_check_marker_file", lambda: marker_path)
    return marker_path


# --- _format_checked_at() ------------------------------------------------


def test_format_checked_at_formats_iso_timestamp():
    formatted = _format_checked_at("2026-09-01T14:32:07.123456+00:00")
    # Exact clock digits depend on the test machine's local time zone, but
    # the shape (and the date component, timezone offsets are all well
    # under 24h) must always come out as "YYYY-MM-DD HH:MM".
    assert len(formatted) == 16
    assert formatted[:7] == "2026-09"
    assert formatted[10] == " "
    assert formatted[13] == ":"


def test_format_checked_at_falls_back_to_raw_string_on_garbage():
    assert _format_checked_at("not-a-timestamp") == "not-a-timestamp"


# --- HardwareCheckDialog ---------------------------------------------------


def test_dialog_shows_never_checked_when_no_marker(qapp, monkeypatch, tmp_path):
    _patch_marker_path(monkeypatch, tmp_path)
    dialog = HardwareCheckDialog(LanguageManager("de"))
    try:
        assert "Noch keine Hardware-Prüfung" in dialog.status.text()
    finally:
        dialog.close()


def test_dialog_shows_found_and_meets_recommendation(qapp, monkeypatch, tmp_path):
    marker = _patch_marker_path(monkeypatch, tmp_path)
    save_gpu_check_result(GpuInfo(name="RTX 4090", vram_gb=24.0), marker_path=marker)
    dialog = HardwareCheckDialog(LanguageManager("de"))
    try:
        assert "RTX 4090" in dialog.status.text()
        assert "24" in dialog.status.text()
        assert "Erfüllt die Empfehlung" in dialog.status.text()
    finally:
        dialog.close()


def test_dialog_shows_found_below_recommendation(qapp, monkeypatch, tmp_path):
    marker = _patch_marker_path(monkeypatch, tmp_path)
    save_gpu_check_result(GpuInfo(name="GTX 1650", vram_gb=4.0), marker_path=marker)
    dialog = HardwareCheckDialog(LanguageManager("de"))
    try:
        assert "GTX 1650" in dialog.status.text()
        assert "Liegt unter der Empfehlung" in dialog.status.text()
    finally:
        dialog.close()


def test_dialog_shows_not_found(qapp, monkeypatch, tmp_path):
    marker = _patch_marker_path(monkeypatch, tmp_path)
    save_gpu_check_result(None, marker_path=marker)
    dialog = HardwareCheckDialog(LanguageManager("de"))
    try:
        assert "Keine CUDA-GPU gefunden" in dialog.status.text()
    finally:
        dialog.close()


def test_dialog_recheck_persists_and_updates_display(qapp, monkeypatch, tmp_path):
    marker = _patch_marker_path(monkeypatch, tmp_path)
    # Starts with nothing on record.
    dialog = HardwareCheckDialog(LanguageManager("de"))
    try:
        assert "Noch keine Hardware-Prüfung" in dialog.status.text()

        fresh_gpu = GpuInfo(name="RTX 4070", vram_gb=12.0)
        monkeypatch.setattr("bootstrap.gpu_check.detect_nvidia_gpu", lambda: fresh_gpu)

        dialog._recheck()

        assert "RTX 4070" in dialog.status.text()
        assert marker.is_file()  # detect_and_save_gpu_check() persisted it
        assert dialog.recheck_button.isEnabled()
    finally:
        dialog.close()


def test_dialog_retranslates_status_on_language_change(qapp, monkeypatch, tmp_path):
    marker = _patch_marker_path(monkeypatch, tmp_path)
    save_gpu_check_result(GpuInfo(name="RTX 4090", vram_gb=24.0), marker_path=marker)
    language = LanguageManager("de")
    dialog = HardwareCheckDialog(language)
    try:
        assert "Erfüllt die Empfehlung" in dialog.status.text()
        language.set_language("en")
        dialog.retranslate()
        assert "Meets the recommendation" in dialog.status.text()
        assert dialog.windowTitle() == "Hardware test"
    finally:
        dialog.close()


# --- MainWindow's "Hilfe" menu --------------------------------------------


def test_help_menu_has_three_actions_in_german(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: tmp_path / "language.json")
    window = MainWindow()
    try:
        assert window.help_menu.title() == "Hilfe"
        labels = [action.text() for action in window.help_menu.actions()]
        assert labels == [
            "Hardware-Test anzeigen/wiederholen …",
            "Nach Updates suchen …",
            "Über …",
        ]
    finally:
        window.close()


def test_help_menu_retranslates_on_language_change(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: tmp_path / "language.json")
    window = MainWindow()
    try:
        window.language.set_language("en")
        assert window.help_menu.title() == "Help"
        labels = [action.text() for action in window.help_menu.actions()]
        assert labels == [
            "Show/repeat hardware test …",
            "Check for updates …",
            "About …",
        ]
    finally:
        window.close()


def test_open_hardware_check_constructs_dialog_with_window_language(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: tmp_path / "language.json")
    _patch_marker_path(monkeypatch, tmp_path)
    window = MainWindow()
    try:
        captured = {}
        real_init = app_module.HardwareCheckDialog.__init__

        def spy_init(self, language, parent=None):
            captured["language"] = language
            real_init(self, language, parent)

        monkeypatch.setattr(app_module.HardwareCheckDialog, "__init__", spy_init)
        monkeypatch.setattr(app_module.HardwareCheckDialog, "exec", lambda self: 0)

        window._open_hardware_check()

        assert captured["language"] is window.language
    finally:
        window.close()


def test_about_uses_current_language_and_version(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: tmp_path / "language.json")
    window = MainWindow()
    try:
        captured = {}
        monkeypatch.setattr(
            app_module.QMessageBox,
            "about",
            lambda parent, title, text: captured.update(title=title, text=text),
        )
        window._about()
        assert captured["title"] == "Über …"
        assert "Document Translator" in captured["text"]
        assert app_module.__version__ in captured["text"]
    finally:
        window.close()
