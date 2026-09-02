"""Covers MergeSearchDialog/WordMergeSearchDialog's Drive-credentials
"speichern" button - specifically the 02.09.2026 fix (Michael: "Es scheint
auch so das die Anmeldedaten nicht wirklich gespeichert werden.").

Root cause: _save_drive_credentials() called pipeline.drive_auth.
save_client_credentials() directly, with no try/except - unlike
SettingsDialog._save_key() (ui/app.py), which wraps the exact same kind of
call and shows a QMessageBox.critical on failure. A keyring failure (no OS
Secret Service running - the single most common real cause) therefore
raised silently out of the Qt slot: no error, no success, nothing visibly
happened. Both dialogs duplicate the same Drive-panel code (see their own
module docstrings), so both are covered here.

Relies on tests/conftest.py's autouse _isolated_qsettings fixture for
QSettings isolation.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from pipeline import drive_auth


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _fill_credentials_fields(dialog) -> None:
    dialog.drive_client_id_edit.setText("cid-1")
    dialog.drive_client_secret_edit.setText("secret-1")
    dialog.drive_project_id_edit.setText("proj-1")


@pytest.mark.parametrize(
    "module_name, dialog_attr",
    [
        ("ui.merge_search_dialog", "MergeSearchDialog"),
        ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
    ],
)
def test_save_drive_credentials_shows_error_and_keeps_fields_on_failure(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr
) -> None:
    import importlib

    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        dialog_module.QMessageBox,
        "critical",
        staticmethod(lambda parent, title, text: captured.update(title=title, text=text)),
    )

    def _boom(client_id, client_secret, project_id):
        raise RuntimeError("OS keyring is unavailable: no Secret Service running")

    monkeypatch.setattr(drive_auth, "save_client_credentials", _boom)

    from PySide6.QtCore import QSettings

    dialog = DialogClass(_language(), QSettings("PDF-Translator-Test", f"{dialog_attr}Smoke"))
    try:
        _fill_credentials_fields(dialog)
        dialog._save_drive_credentials()
        assert "keyring is unavailable" in captured["text"]
        # Unlike the success path, a failed save must NOT clear what the
        # user typed - they shouldn't have to retype everything to retry.
        assert dialog.drive_client_id_edit.text() == "cid-1"
        assert dialog.drive_client_secret_edit.text() == "secret-1"
        assert dialog.drive_project_id_edit.text() == "proj-1"
    finally:
        dialog.close()


@pytest.mark.parametrize(
    "module_name, dialog_attr",
    [
        ("ui.merge_search_dialog", "MergeSearchDialog"),
        ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
    ],
)
def test_save_drive_credentials_still_succeeds_and_clears_fields(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr
) -> None:
    """Regression guard: the try/except must not swallow the success path."""
    import importlib

    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    info_calls: list[tuple] = []
    monkeypatch.setattr(
        dialog_module.QMessageBox, "information", staticmethod(lambda *a: info_calls.append(a))
    )

    stored: dict[str, str] = {}
    monkeypatch.setattr(
        drive_auth,
        "save_client_credentials",
        lambda cid, secret, proj: stored.update(client_id=cid, client_secret=secret, project_id=proj),
    )

    from PySide6.QtCore import QSettings

    dialog = DialogClass(_language(), QSettings("PDF-Translator-Test", f"{dialog_attr}SmokeOk"))
    try:
        _fill_credentials_fields(dialog)
        dialog._save_drive_credentials()
        assert stored == {"client_id": "cid-1", "client_secret": "secret-1", "project_id": "proj-1"}
        assert dialog.drive_client_id_edit.text() == ""
        assert dialog.drive_client_secret_edit.text() == ""
        assert dialog.drive_project_id_edit.text() == ""
        assert len(info_calls) == 1
    finally:
        dialog.close()


def _language():
    from ui.i18n import LanguageManager

    return LanguageManager("de")
