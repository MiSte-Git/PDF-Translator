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


# --- "Aus JSON-Datei laden ..." (02.09.2026) --------------------------
# Michael: "Ich konnte eine json Datei mit den OAuth-Client Daten beim
# erstellen runterladen. Sollten wir das laden der json Datei beim
# anmelden unterstützen?" - fills the three fields from a real Google
# client-secrets JSON instead of the user copy-pasting each value.


@pytest.mark.parametrize(
    "module_name, dialog_attr",
    [
        ("ui.merge_search_dialog", "MergeSearchDialog"),
        ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
    ],
)
def test_load_from_file_fills_the_three_fields(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr, tmp_path
) -> None:
    import importlib
    import json

    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    json_path = tmp_path / "client_secret.json"
    json_path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "id-from-file",
                    "client_secret": "secret-from-file",
                    "project_id": "project-from-file",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dialog_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(json_path), "JSON (*.json)"))
    )

    from PySide6.QtCore import QSettings

    dialog = DialogClass(_language(), QSettings("PDF-Translator-Test", f"{dialog_attr}LoadFile"))
    try:
        dialog._load_drive_credentials_from_file()
        assert dialog.drive_client_id_edit.text() == "id-from-file"
        assert dialog.drive_client_secret_edit.text() == "secret-from-file"
        assert dialog.drive_project_id_edit.text() == "project-from-file"
    finally:
        dialog.close()


@pytest.mark.parametrize(
    "module_name, dialog_attr",
    [
        ("ui.merge_search_dialog", "MergeSearchDialog"),
        ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
    ],
)
def test_load_from_file_shows_warning_on_a_broken_file_and_leaves_fields_untouched(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr, tmp_path
) -> None:
    import importlib

    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    broken_path = tmp_path / "broken.json"
    broken_path.write_text("not valid json{{{", encoding="utf-8")
    monkeypatch.setattr(
        dialog_module.QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: (str(broken_path), "JSON (*.json)")),
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        dialog_module.QMessageBox,
        "warning",
        staticmethod(lambda parent, title, text: captured.update(title=title, text=text)),
    )

    from PySide6.QtCore import QSettings

    dialog = DialogClass(_language(), QSettings("PDF-Translator-Test", f"{dialog_attr}LoadFileBroken"))
    try:
        dialog._load_drive_credentials_from_file()
        assert captured  # a warning was shown
        assert dialog.drive_client_id_edit.text() == ""
        assert dialog.drive_client_secret_edit.text() == ""
        assert dialog.drive_project_id_edit.text() == ""
    finally:
        dialog.close()


@pytest.mark.parametrize(
    "module_name, dialog_attr",
    [
        ("ui.merge_search_dialog", "MergeSearchDialog"),
        ("ui.word_merge_search_dialog", "WordMergeSearchDialog"),
    ],
)
def test_load_from_file_does_nothing_when_dialog_is_cancelled(
    qapp, monkeypatch: pytest.MonkeyPatch, module_name, dialog_attr
) -> None:
    import importlib

    dialog_module = importlib.import_module(module_name)
    DialogClass = getattr(dialog_module, dialog_attr)

    monkeypatch.setattr(dialog_module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))

    from PySide6.QtCore import QSettings

    dialog = DialogClass(_language(), QSettings("PDF-Translator-Test", f"{dialog_attr}LoadFileCancel"))
    try:
        dialog._load_drive_credentials_from_file()
        assert dialog.drive_client_id_edit.text() == ""
    finally:
        dialog.close()
