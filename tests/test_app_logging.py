"""Covers pipeline/app_logging.py (02.09.2026, Michael: "Haben wir kein
Log für genau solche Fälle?", nach einem Google-Drive-Fehler, den er
zweimal per Screenshot durchgeben musste). configure_logging() is called
once from ui/app.py::main() - here it is exercised directly against a
patched LOG_DIR/LOG_FILE so the test never touches the real
~/.pdf-translator/ directory.
"""
from __future__ import annotations

import logging
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtWidgets import QApplication

from pipeline import app_logging


@pytest.fixture(autouse=True)
def _isolated_log_location(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Point LOG_DIR/LOG_FILE at a throwaway directory and reset the
    module's "already configured" flag, so each test gets a clean handler
    - configure_logging() is otherwise idempotent by design (see its own
    docstring) and would silently no-op on the second test.
    """
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(app_logging, "LOG_DIR", log_dir)
    monkeypatch.setattr(app_logging, "LOG_FILE", log_dir / "app.log")
    monkeypatch.setattr(app_logging, "_configured", False)
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    for handler in list(root.handlers):
        if handler not in original_handlers:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(original_level)


def test_configure_logging_creates_the_log_file() -> None:
    log_file = app_logging.configure_logging()
    assert log_file == app_logging.LOG_FILE
    logging.getLogger("pipeline.drive_auth").info("Testeintrag")
    assert log_file.exists()
    assert "Testeintrag" in log_file.read_text(encoding="utf-8")


def test_configure_logging_is_idempotent() -> None:
    """A second call (e.g. if some future code path invoked it twice) must
    not register a second handler - otherwise every line would be written
    twice."""
    app_logging.configure_logging()
    handlers_after_first = len(logging.getLogger().handlers)
    app_logging.configure_logging()
    assert len(logging.getLogger().handlers) == handlers_after_first


# --- SettingsDialog's "Log-Datei öffnen" button -----------------------


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_open_log_button_opens_the_log_file(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    from ui.app import SettingsDialog
    from ui.i18n import LanguageManager

    opened: list[QUrl] = []
    import ui.app as app_module

    monkeypatch.setattr(app_module.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url)))

    dialog = SettingsDialog(QSettings("PDF-Translator-Test", "SettingsDialogLogButton"), LanguageManager("de"))
    try:
        dialog.open_log_button.click()
        assert len(opened) == 1
        assert opened[0].toLocalFile() == str(app_module.LOG_FILE)
    finally:
        dialog.close()
