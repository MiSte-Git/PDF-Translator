"""UI coverage for the "Aus Datei laden …" button next to the protected-terms
box (03.09.2026, see tests/test_protected_terms_file.py for the pure
reader). MainWindow._load_protected_terms_file() must APPEND to what is
already typed, skip duplicates, remember the file's folder independently of
last_source_dir, and report unreadable files without crashing.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture like the
other UI tests.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from ui.app import MainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _pick(monkeypatch: pytest.MonkeyPatch, chosen: str, seen_start_dirs: list[str] | None = None) -> None:
    def fake_get_open_file_name(_parent, _title, start_dir, _filter):
        if seen_start_dirs is not None:
            seen_start_dirs.append(start_dir)
        return chosen, ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_get_open_file_name)


def test_loading_a_csv_appends_new_terms_and_keeps_typed_ones(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    terms_dir = tmp_path / "listen"
    terms_dir.mkdir()
    csv_file = terms_dir / "begriffe.csv"
    csv_file.write_text("Begriff;Kommentar\nVIRELICON;Produkt\nclaude;doppelt\nAcme;Kunde\n", encoding="utf-8")

    seen_start_dirs: list[str] = []
    _pick(monkeypatch, str(csv_file), seen_start_dirs)

    window = MainWindow()
    window.show()
    try:
        window.protected.setPlainText("Anthropic\nClaude")
        window.protected_load.click()

        assert window.protected.toPlainText() == "Anthropic\nClaude\nVIRELICON\nAcme"
        assert window.protected_hint.isVisible()
        assert "begriffe.csv" in window.protected_hint.text()
        assert window.settings.value("last_protected_terms_dir", "", type=str) == str(terms_dir)
        # Not the document folder - term lists live elsewhere.
        assert window.settings.value("last_source_dir", "", type=str) == ""

        # Loading the same file twice must not duplicate anything, and the
        # remembered folder is offered back as the dialog's start dir.
        window.protected_load.click()
        assert window.protected.toPlainText() == "Anthropic\nClaude\nVIRELICON\nAcme"
        assert seen_start_dirs == ["", str(terms_dir)]
    finally:
        window.close()


def test_cancelling_the_dialog_changes_nothing(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    _pick(monkeypatch, "")
    window = MainWindow()
    window.show()
    try:
        window.protected.setPlainText("Anthropic")
        window.protected_load.click()
        assert window.protected.toPlainText() == "Anthropic"
        assert not window.protected_hint.isVisible()
    finally:
        window.close()


def test_unreadable_file_shows_a_warning_instead_of_crashing(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pick(monkeypatch, str(tmp_path / "fehlt.csv"))
    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda _parent, title, text, *a, **k: warnings.append((title, text)))

    window = MainWindow()
    window.show()
    try:
        window.protected.setPlainText("Anthropic")
        window.protected_load.click()
        assert window.protected.toPlainText() == "Anthropic"
        assert len(warnings) == 1
        assert "fehlt.csv" in warnings[0][1]
    finally:
        window.close()
