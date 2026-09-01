"""Tests for ui/app.py's bootstrapper language-marker handoff (01.09.2026,
project doc "deployment-strategie-bootstrapper-01-09-2026.md", decision "Ja,
übernehmen"): a first run with no QSettings "language" value yet should
pick up the language the guided bootstrapper installer left behind in
bootstrap/paths.py::language_marker_file(), but a previously saved
QSettings value always wins over it.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation; the marker file's location is separately redirected
per test below via monkeypatching bootstrap.paths.language_marker_file(),
so this file never touches a real per-machine bootstrapper install either.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import ui.app as app_module
from ui.app import MainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _patch_marker_path(monkeypatch, tmp_path):
    marker_path = tmp_path / "language.json"
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: marker_path)
    return marker_path


def test_bootstrap_language_marker_none_when_file_missing(monkeypatch, tmp_path):
    _patch_marker_path(monkeypatch, tmp_path)
    assert app_module._bootstrap_language_marker() is None


def test_bootstrap_language_marker_reads_valid_json(monkeypatch, tmp_path):
    marker_path = _patch_marker_path(monkeypatch, tmp_path)
    marker_path.write_text(json.dumps({"language": "en"}))
    assert app_module._bootstrap_language_marker() == "en"


def test_bootstrap_language_marker_none_on_corrupt_json(monkeypatch, tmp_path):
    marker_path = _patch_marker_path(monkeypatch, tmp_path)
    marker_path.write_text("not valid json{{{")
    assert app_module._bootstrap_language_marker() is None


def test_bootstrap_language_marker_none_when_key_not_a_string(monkeypatch, tmp_path):
    marker_path = _patch_marker_path(monkeypatch, tmp_path)
    marker_path.write_text(json.dumps({"language": 5}))
    assert app_module._bootstrap_language_marker() is None


def test_mainwindow_uses_marker_language_on_first_run(qapp, monkeypatch, tmp_path):
    marker_path = _patch_marker_path(monkeypatch, tmp_path)
    marker_path.write_text(json.dumps({"language": "en"}))

    window = MainWindow()
    try:
        assert window.language.language == "en"
    finally:
        window.close()


def test_mainwindow_ignores_marker_without_saved_settings_key(qapp, monkeypatch, tmp_path):
    # No marker file at all: falls back to the existing hardcoded default.
    _patch_marker_path(monkeypatch, tmp_path)
    window = MainWindow()
    try:
        assert window.language.language == "de"
    finally:
        window.close()


def test_mainwindow_prefers_saved_settings_over_marker(qapp, monkeypatch, tmp_path):
    marker_path = _patch_marker_path(monkeypatch, tmp_path)
    marker_path.write_text(json.dumps({"language": "en"}))

    # Simulate a previous run that already saved an explicit choice.
    pre_existing = QSettings("PDF-Translator", "Document Translator")
    pre_existing.setValue("language", "de")
    pre_existing.sync()

    window = MainWindow()
    try:
        assert window.language.language == "de"
    finally:
        window.close()
