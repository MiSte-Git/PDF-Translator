"""Benutzerhandbuch (14.10.2026): every UI language has a manual source and
a built PDF, Hilfe -> Benutzerhandbuch opens the PDF for the current
language (falling back to English, then German), and the OCR/inpainting
field hints link to it - see ui/app.py's manual_path()/_open_manual() and
tools/build_manual.py.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

import ui.app as app_module
from ui.app import MainWindow, manual_path
from ui.i18n import LOCALES

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("code", [locale.code for locale in LOCALES])
def test_every_ui_language_has_manual_source_and_pdf(code):
    assert (ROOT / "docs" / code / "manual.md").is_file()
    assert (ROOT / "docs" / "pdf" / f"manual-{code}.pdf").is_file()


def test_manual_path_falls_back_to_english_then_german(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "MANUAL_DIR", tmp_path)
    assert manual_path("fr") is None
    (tmp_path / "manual-de.pdf").write_bytes(b"%PDF")
    assert manual_path("fr") == tmp_path / "manual-de.pdf"
    (tmp_path / "manual-en.pdf").write_bytes(b"%PDF")
    assert manual_path("fr") == tmp_path / "manual-en.pdf"
    (tmp_path / "manual-fr.pdf").write_bytes(b"%PDF")
    assert manual_path("fr") == tmp_path / "manual-fr.pdf"


def test_help_menu_manual_opens_pdf_for_current_language(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: tmp_path / "language.json")
    opened = []
    monkeypatch.setattr(app_module.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()))
    window = MainWindow()
    try:
        assert window.help_menu.actions()[0].text() == window.language.text("menu.help.manual")
        window._open_manual()
        assert opened == [str(manual_path(window.language.language))]
    finally:
        window.close()


def test_field_hint_links_to_manual(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.language_marker_file", lambda: tmp_path / "language.json")
    window = MainWindow()
    try:
        text = window._hint_with_manual_link("PaddleOCR <fehlt>")
        assert "&lt;fehlt&gt;" in text
        assert '<a href="manual">' in text
        assert window._hint_with_manual_link("") == ""
    finally:
        window.close()
