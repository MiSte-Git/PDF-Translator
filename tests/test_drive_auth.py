"""Covers pipeline/drive_auth.py - the Google-Drive-Ordnersuche feature's
OAuth/API isolation layer (01.09.2026, Michael: "Können wir eine Google
Drive Ordner durchsuchen?").

What is and isn't tested here, and why: connect_interactively() itself
opens a real system browser and blocks on a local loopback server for the
OAuth redirect (InstalledAppFlow.run_local_server()) - that can only be
exercised against a real Google account on a real machine, never in this
sandbox (see the module's own docstring). What IS fully testable without
any real Google account, and is tested below: the three-state
is_configured()/is_connected() logic, _execute_with_retry()'s backoff
behaviour against a request stub, and every DriveClient method against a
hand-written fake "service" object that mimics just the small slice of the
googleapiclient chained-call shape (.files().list()/.get()/.get_media(),
.about().get()) DriveClient actually calls - never the real SDK.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline import drive_auth
from pipeline.drive_auth import DriveAuthError, DriveClient, DriveEntry, _execute_with_retry


# --- is_configured() / is_connected() --------------------------------------


def test_not_configured_when_no_credentials_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    assert drive_auth.is_configured() is False


def test_configured_once_both_client_id_and_secret_are_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "id-123")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "secret-456")
    assert drive_auth.is_configured() is True


def test_not_configured_with_only_one_of_the_two_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "id-123")
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    assert drive_auth.is_configured() is False


def test_not_connected_without_a_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_DRIVE_REFRESH_TOKEN", raising=False)
    assert drive_auth.is_connected() is False


def test_connected_once_a_refresh_token_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-789")
    assert drive_auth.is_connected() is True


# --- save_client_credentials() / disconnect() -------------------------------
# Both go through pipeline.credentials.set_api_key()/delete_api_key(), which
# hit the OS keyring - unavailable in this sandbox (see Backlog.md), so
# these are monkeypatched at drive_auth's own import site rather than
# exercising a real keyring backend, the same way test_ui_provider_credentials.py
# monkeypatches ui.app.credential_status instead of a real provider.


def test_save_client_credentials_stores_both_values_under_their_key_names(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, str] = {}
    monkeypatch.setattr(drive_auth, "set_api_key", lambda name, value: stored.__setitem__(name, value))
    drive_auth.save_client_credentials("my-id", "my-secret")
    assert stored == {"google_drive_client_id": "my-id", "google_drive_client_secret": "my-secret"}


def test_disconnect_deletes_only_the_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []
    monkeypatch.setattr(drive_auth, "delete_api_key", deleted.append)
    drive_auth.disconnect()
    assert deleted == ["google_drive_refresh_token"]


# --- connect_interactively() / build_service(): the configured/connected guards ---


def test_connect_interactively_refuses_without_client_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    with pytest.raises(DriveAuthError):
        drive_auth.connect_interactively()


def test_connect_interactively_raises_if_google_returns_no_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "id-123")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "secret-456")

    class _FakeCredentials:
        refresh_token = None

    class _FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            assert config["installed"]["client_id"] == "id-123"
            return cls()

        def run_local_server(self, port):
            return _FakeCredentials()

    import google_auth_oauthlib.flow as flow_module

    monkeypatch.setattr(flow_module, "InstalledAppFlow", _FakeFlow)
    with pytest.raises(DriveAuthError):
        drive_auth.connect_interactively()


def test_connect_interactively_stores_the_returned_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "id-123")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "secret-456")

    class _FakeCredentials:
        refresh_token = "brand-new-refresh-token"

    class _FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            return cls()

        def run_local_server(self, port):
            return _FakeCredentials()

    import google_auth_oauthlib.flow as flow_module

    monkeypatch.setattr(flow_module, "InstalledAppFlow", _FakeFlow)
    stored: dict[str, str] = {}
    monkeypatch.setattr(drive_auth, "set_api_key", lambda name, value: stored.__setitem__(name, value))
    drive_auth.connect_interactively()
    assert stored["google_drive_refresh_token"] == "brand-new-refresh-token"


def test_build_service_refuses_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    with pytest.raises(DriveAuthError):
        drive_auth.build_service()


def test_build_service_refuses_when_configured_but_not_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "id-123")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "secret-456")
    monkeypatch.delenv("GOOGLE_DRIVE_REFRESH_TOKEN", raising=False)
    with pytest.raises(DriveAuthError):
        drive_auth.build_service()


def test_build_service_wraps_a_revoked_refresh_token_as_drive_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "id-123")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "secret-456")
    monkeypatch.setenv("GOOGLE_DRIVE_REFRESH_TOKEN", "revoked-token")

    from google.auth.exceptions import RefreshError

    def _raise_refresh_error(self, request):
        raise RefreshError("token has been revoked")

    import google.oauth2.credentials as credentials_module

    monkeypatch.setattr(credentials_module.Credentials, "refresh", _raise_refresh_error)
    with pytest.raises(DriveAuthError):
        drive_auth.build_service()


# --- _execute_with_retry() ---------------------------------------------


class _FakeHttpResponse:
    def __init__(self, status: int) -> None:
        self.status = status
        self.reason = "Fake reason"


def _http_error(status: int):
    from googleapiclient.errors import HttpError

    return HttpError(_FakeHttpResponse(status), b"{}")


class _FlakyRequest:
    """Fails `fail_times` times with the given status, then returns `result`."""

    def __init__(self, fail_times: int, status: int, result) -> None:
        self.fail_times = fail_times
        self.status = status
        self.result = result
        self.calls = 0

    def execute(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise _http_error(self.status)
        return self.result


def test_execute_with_retry_succeeds_after_transient_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(drive_auth, "_RETRY_BASE_DELAY_SECONDS", 0.0)
    request = _FlakyRequest(fail_times=2, status=503, result={"ok": True})
    assert _execute_with_retry(request) == {"ok": True}
    assert request.calls == 3


def test_execute_with_retry_does_not_retry_non_transient_errors() -> None:
    request = _FlakyRequest(fail_times=1, status=404, result={"ok": True})
    with pytest.raises(Exception):
        _execute_with_retry(request)
    assert request.calls == 1


def test_execute_with_retry_gives_up_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(drive_auth, "_RETRY_BASE_DELAY_SECONDS", 0.0)
    request = _FlakyRequest(fail_times=999, status=429, result={"ok": True})
    with pytest.raises(Exception):
        _execute_with_retry(request)
    assert request.calls == drive_auth._MAX_RETRIES


# --- DriveClient against a fake service ------------------------------------


class _FakeRequest:
    def __init__(self, result) -> None:
        self._result = result

    def execute(self):
        return self._result


class _FakeFilesResource:
    def __init__(self, get_result=None, list_pages=None, media_bytes: dict[str, bytes] | None = None) -> None:
        self._get_result = get_result
        self._list_pages = list_pages or []
        self._media_bytes = media_bytes or {}
        self.list_calls: list[dict] = []

    def get(self, **kwargs):
        return _FakeRequest(self._get_result)

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        # One fixed page per call, in call order - enough to exercise
        # pageToken-driven pagination without a real stateful fake server.
        page = self._list_pages[len(self.list_calls) - 1]
        return _FakeRequest(page)

    def get_media(self, fileId: str, **kwargs):
        return _FakeRequest(self._media_bytes[fileId])


class _FakeAboutResource:
    def __init__(self, email: str | None) -> None:
        self._email = email

    def get(self, **kwargs):
        if self._email is None:
            raise RuntimeError("boom")
        return _FakeRequest({"user": {"emailAddress": self._email}})


class _FakeService:
    def __init__(self, files_resource: _FakeFilesResource, about_resource: _FakeAboutResource | None = None) -> None:
        self._files = files_resource
        self._about = about_resource or _FakeAboutResource(None)

    def files(self):
        return self._files

    def about(self):
        return self._about


def test_resolve_folder_returns_a_drive_entry_for_a_real_folder() -> None:
    files = _FakeFilesResource(get_result={"id": "f1", "name": "Developer XY", "mimeType": drive_auth._FOLDER_MIME_TYPE, "trashed": False})
    client = DriveClient(_FakeService(files))
    entry = client.resolve_folder("f1")
    assert entry == DriveEntry(id="f1", name="Developer XY", is_folder=True)


def test_resolve_folder_rejects_a_file_id() -> None:
    files = _FakeFilesResource(get_result={"id": "x1", "name": "not_a_folder.pdf", "mimeType": drive_auth._PDF_MIME_TYPE, "trashed": False})
    client = DriveClient(_FakeService(files))
    with pytest.raises(ValueError):
        client.resolve_folder("x1")


def test_resolve_folder_rejects_a_trashed_folder() -> None:
    files = _FakeFilesResource(get_result={"id": "f1", "name": "Old", "mimeType": drive_auth._FOLDER_MIME_TYPE, "trashed": True})
    client = DriveClient(_FakeService(files))
    with pytest.raises(ValueError):
        client.resolve_folder("f1")


def test_list_children_paginates_across_multiple_pages() -> None:
    page1 = {
        "files": [{"id": "a", "name": "a.pdf", "mimeType": drive_auth._PDF_MIME_TYPE}],
        "nextPageToken": "TOKEN2",
    }
    page2 = {
        "files": [
            {"id": "sub", "name": "Subfolder", "mimeType": drive_auth._FOLDER_MIME_TYPE},
            {"id": "b", "name": "b.pdf", "mimeType": drive_auth._PDF_MIME_TYPE},
        ],
    }
    files = _FakeFilesResource(list_pages=[page1, page2])
    client = DriveClient(_FakeService(files))
    entries = list(client.list_children("root"))
    assert entries == [
        DriveEntry(id="a", name="a.pdf", is_folder=False),
        DriveEntry(id="sub", name="Subfolder", is_folder=True),
        DriveEntry(id="b", name="b.pdf", is_folder=False),
    ]
    # second call must have carried the pageToken from the first page's response
    assert files.list_calls[1]["pageToken"] == "TOKEN2"


def test_download_writes_the_files_bytes_to_destination(tmp_path: Path) -> None:
    files = _FakeFilesResource(media_bytes={"f1": b"%PDF-1.4 fake content"})
    client = DriveClient(_FakeService(files))
    destination = tmp_path / "out.pdf"
    client.download("f1", destination)
    assert destination.read_bytes() == b"%PDF-1.4 fake content"


def test_whoami_returns_the_signed_in_email() -> None:
    client = DriveClient(_FakeService(_FakeFilesResource(), _FakeAboutResource("dev@example.com")))
    assert client.whoami() == "dev@example.com"


def test_whoami_returns_none_on_failure_rather_than_raising() -> None:
    client = DriveClient(_FakeService(_FakeFilesResource(), _FakeAboutResource(None)))
    assert client.whoami() is None
