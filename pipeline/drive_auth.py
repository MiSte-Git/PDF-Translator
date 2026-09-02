"""Google Drive OAuth + a minimal, testable Drive-API wrapper (01.09.2026).

This is the only file in the project allowed to import google-auth /
google-auth-oauthlib / google-api-python-client - exactly the same
exclusivity rule pymupdf_engine.py already applies to PyMuPDF, for the same
reason: every other module (ui/drive_search.py, its tests, the merge search
dialog) talks only to the small, hand-rolled DriveClient/DriveEntry shapes
defined below, never to the Google SDK objects directly. That keeps the
recursive-folder-walk/download logic in ui/drive_search.py unit-testable
with a plain in-memory fake instead of a real Google account, and keeps a
future SDK version bump or backend swap confined to this one file.

Auth model - three states the UI (MergeSearchDialog) needs to distinguish:
  1. "not configured": no Client-ID/Client-Secret/project ID stored yet. The
     user must create an OAuth "Desktop app" client in Google Cloud Console
     first (this app cannot provision a Google Cloud project on its own) -
     see docs/google_drive_setup.md - and paste all three values into the
     dialog's Drive panel.
  2. "configured, not connected": Client-ID/Secret/project ID are present
     but there is no stored refresh token yet, or the user disconnected.
  3. "connected": a refresh token is stored; build_service() can mint a
     usable access token from it without further user interaction.
is_configured()/is_connected() answer these without raising, so the dialog
can just branch on them rather than catching credential errors as control
flow (see pipeline.credentials.has_api_key()'s docstring for why that helper
exists at all).

**Project ID (02.09.2026, Michael: "Mit Google verbinden" schlug fehl -
"die Google Projekt-ID fehlt"):** the OAuth Client-ID/Secret alone are not
enough - the resulting user credentials also need a `quota_project_id` (see
build_service() below) or Google-side calls fail with a project-related
error. Every "Desktop app" OAuth client belongs to exactly one Google Cloud
project; that project's ID is now a required third field, alongside
Client-ID/Secret, stored the same way (see
pipeline.credentials.get_google_drive_project_id()).

Scope: drive.readonly (broad read access to the user's whole Drive, but
never write/delete). The alternative, the narrower drive.file scope, only
grants access to files/folders the user picks through Google's own Picker
UI - which would mean building a Picker integration instead of letting the
user simply paste a folder link, a materially bigger feature. Documented
here as a conscious trade-off, not an oversight; see Backlog.md 01.09.2026.

connect_interactively() opens a real system browser and a local loopback
HTTP server to catch the OAuth redirect (google_auth_oauthlib's
InstalledAppFlow.run_local_server()) - it can only be exercised against a
real Google account on the user's own machine, never in this sandbox. Kept
deliberately thin (a handful of lines, no branching to speak of) so the
untestable surface is as small as possible; DriveClient below, which
contains all the actual logic (pagination, recursive listing, retries), is
fully unit-tested against a fake service object.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from pipeline.credentials import (
    get_google_drive_client_id,
    get_google_drive_client_secret,
    get_google_drive_project_id,
    get_google_drive_refresh_token,
    has_api_key,
    set_api_key,
    delete_api_key,
)

SCOPES = ("https://www.googleapis.com/auth/drive.readonly",)

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# Public (no leading underscore - unlike _FOLDER_MIME_TYPE above, which is
# purely this module's own implementation detail): the per-format mime
# types callers pass to DriveClient.list_children()'s file_mime_type
# parameter - ui/drive_search.py (PDF) and ui/word_drive_search.py (DOCX,
# 01.09.2026) both import these rather than hardcoding the strings.
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PDF_MIME_TYPE = PDF_MIME_TYPE  # noqa: kept as an alias - see list_children()'s default below

# Drive API calls occasionally fail with a transient 403/429/5xx under load
# (documented Google guidance: retry with exponential backoff). Scanning a
# folder with 1000+ PDFs makes enough calls that hitting this at least once
# per run is realistic, so DriveClient retries internally instead of
# surfacing a transient error as a hard scan failure.
_MAX_RETRIES = 5
_RETRY_BASE_DELAY_SECONDS = 1.0


class DriveAuthError(RuntimeError):
    """Raised when Drive access is not configured/connected yet."""


@dataclass(frozen=True)
class DriveEntry:
    id: str
    name: str
    is_folder: bool


def is_configured() -> bool:
    """True once a Client-ID, Client-Secret, and project ID have been saved."""
    return (
        has_api_key("google_drive_client_id", ("GOOGLE_DRIVE_CLIENT_ID",))
        and has_api_key("google_drive_client_secret", ("GOOGLE_DRIVE_CLIENT_SECRET",))
        and has_api_key("google_drive_project_id", ("GOOGLE_DRIVE_PROJECT_ID",))
    )


def is_connected() -> bool:
    """True once a refresh token from a completed sign-in is stored."""
    return has_api_key("google_drive_refresh_token", ("GOOGLE_DRIVE_REFRESH_TOKEN",))


def save_client_credentials(client_id: str, client_secret: str, project_id: str) -> None:
    set_api_key("google_drive_client_id", client_id)
    set_api_key("google_drive_client_secret", client_secret)
    set_api_key("google_drive_project_id", project_id)


def disconnect() -> None:
    """Drop the stored refresh token. Client-ID/Secret are kept."""
    delete_api_key("google_drive_refresh_token")


# How long connect_interactively() waits for the user to complete the
# browser consent screen before giving up (02.09.2026, Michael: the app's
# process didn't terminate cleanly after closing all windows - see
# Backlog.md). google_auth_oauthlib's run_local_server() blocks on its local
# loopback server with NO timeout by default (timeout_seconds=None) - if the
# user starts "Mit Google verbinden" and then abandons the browser tab (or
# closes the whole app) without finishing sign-in, the background
# QThreadPool worker running this function (ui/workers.py::DriveConnectWorker)
# would otherwise block forever, which in turn blocks Qt's global
# QThreadPool from ever finishing its own cleanup - exactly what looked like
# the process "hanging" instead of exiting. 5 minutes is generous enough for
# a real sign-in (including picking an account, 2FA, etc.) while still
# guaranteeing this can never hang indefinitely.
_OAUTH_CONSENT_TIMEOUT_SECONDS = 300


def connect_interactively() -> None:
    """Run the OAuth consent flow in the system browser and store the result.

    Blocks until the user completes the browser consent screen, or up to
    _OAUTH_CONSENT_TIMEOUT_SECONDS if they abandon it - callers run this off
    the UI thread (see ui/workers.py::DriveConnectWorker). Raises
    DriveAuthError if Client-ID/Secret/project ID are not configured yet, if
    the user did not complete sign-in within the timeout, or if Google did
    not return a refresh token (happens if this exact client already has a
    live grant for this account with no offline-access request pending -
    vanishingly unlikely here since InstalledAppFlow always requests offline
    access, but guarded rather than storing an unusable empty value).
    """
    if not is_configured():
        raise DriveAuthError(
            "Keine Google-Client-ID/Client-Secret/Projekt-ID hinterlegt. Bitte zuerst im "
            "Drive-Bereich der Ordnersuche speichern."
        )
    from google_auth_oauthlib.flow import InstalledAppFlow, WSGITimeoutError  # local import: see module docstring

    client_config = {
        "installed": {
            "client_id": get_google_drive_client_id(),
            "client_secret": get_google_drive_client_secret(),
            "project_id": get_google_drive_project_id(),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, list(SCOPES))
    try:
        credentials = flow.run_local_server(port=0, timeout_seconds=_OAUTH_CONSENT_TIMEOUT_SECONDS)
    except WSGITimeoutError as exc:
        raise DriveAuthError(
            "Die Google-Anmeldung wurde nicht innerhalb von 5 Minuten abgeschlossen. "
            "Bitte 'Mit Google verbinden' erneut klicken."
        ) from exc
    if not credentials.refresh_token:
        raise DriveAuthError(
            "Google hat keinen Refresh-Token zurückgegeben. Bitte den Zugriff dieser "
            "App unter https://myaccount.google.com/permissions entfernen und erneut "
            "verbinden."
        )
    set_api_key("google_drive_refresh_token", credentials.refresh_token)


def build_service():
    """Return an authorized googleapiclient Drive v3 service resource.

    Raises DriveAuthError if not configured/connected yet, or if the stored
    refresh token was revoked (e.g. the user removed this app's access on
    myaccount.google.com) - in that case the caller should point the user
    back at "Mit Google verbinden".
    """
    if not is_configured():
        raise DriveAuthError(
            "Keine Google-Client-ID/Client-Secret/Projekt-ID hinterlegt. Bitte zuerst im "
            "Drive-Bereich der Ordnersuche speichern."
        )
    if not is_connected():
        raise DriveAuthError("Noch nicht mit Google verbunden. Bitte zuerst 'Mit Google verbinden' klicken.")

    from google.auth.exceptions import RefreshError  # local import: see module docstring
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(
        token=None,
        refresh_token=get_google_drive_refresh_token(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=get_google_drive_client_id(),
        client_secret=get_google_drive_client_secret(),
        scopes=list(SCOPES),
        # Without a quota project, Google bills/attributes API calls to no
        # project at all - this is exactly what surfaced to Michael as a
        # "Google project ID is missing" failure (02.09.2026). The OAuth
        # client's own project (the one entered alongside Client-ID/Secret,
        # see docs/google_drive_setup.md) is the correct value here.
        quota_project_id=get_google_drive_project_id(),
    )
    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        raise DriveAuthError(
            f"Google-Zugriff wurde offenbar widerrufen, bitte erneut verbinden ({exc})."
        ) from exc
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _execute_with_retry(request):
    """Run a googleapiclient request, retrying transient failures.

    Kept as a free function (rather than a DriveClient method) so it can be
    unit-tested in isolation against a request stub that fails N times
    before succeeding, without needing a full fake service.
    """
    import time

    from googleapiclient.errors import HttpError

    attempt = 0
    while True:
        try:
            return request.execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            attempt += 1
            if status not in (403, 429, 500, 502, 503, 504) or attempt >= _MAX_RETRIES:
                raise
            time.sleep(_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))


class DriveClient:
    """Thin, unit-testable wrapper around an authorized Drive v3 service.

    Every method here takes/returns only DriveEntry/str/bytes - never a raw
    googleapiclient object - so ui/drive_search.py's tests can hand in a
    hand-written fake with the same three methods instead of the real
    Google SDK. See tests/test_drive_client.py for both the retry behaviour
    (against a request stub) and the fake-service-based tests of this class
    itself.
    """

    def __init__(self, service) -> None:
        self._service = service

    def resolve_folder(self, folder_id: str) -> DriveEntry:
        """Look up a folder by id, raising ValueError if it isn't one.

        Used by the dialog's "Prüfen" button so the user gets an immediate,
        readable confirmation ("Ordner 'Developer XY' gefunden") before a
        potentially long scan starts, instead of only finding out the
        pasted link/id was wrong once the search comes back empty.
        """
        request = self._service.files().get(
            fileId=folder_id,
            fields="id, name, mimeType, trashed",
            supportsAllDrives=True,
        )
        data = _execute_with_retry(request)
        if data.get("trashed"):
            raise ValueError(f"'{data.get('name', folder_id)}' liegt im Papierkorb.")
        if data.get("mimeType") != _FOLDER_MIME_TYPE:
            raise ValueError(f"'{data.get('name', folder_id)}' ist kein Ordner.")
        return DriveEntry(id=data["id"], name=data["name"], is_folder=True)

    def list_children(self, folder_id: str, file_mime_type: str = _PDF_MIME_TYPE) -> Iterator[DriveEntry]:
        """Yield direct child folders and `file_mime_type` files of
        folder_id (paginated). Defaults to PDF; DOCX search
        (ui/word_drive_search.py, 01.09.2026) passes _DOCX_MIME_TYPE.

        Anything that is neither a folder nor `file_mime_type` (other file
        types) is silently skipped - this feature only ever merges one
        document type per scan, mirroring the local Ordnersuche's single-
        extension file-system scan.
        """
        page_token = None
        query = (
            f"'{folder_id}' in parents and trashed = false and "
            f"(mimeType = '{_FOLDER_MIME_TYPE}' or mimeType = '{file_mime_type}')"
        )
        while True:
            request = self._service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            data = _execute_with_retry(request)
            for entry in data.get("files", []):
                yield DriveEntry(
                    id=entry["id"],
                    name=entry["name"],
                    is_folder=entry.get("mimeType") == _FOLDER_MIME_TYPE,
                )
            page_token = data.get("nextPageToken")
            if not page_token:
                return

    def download(self, file_id: str, destination: Path) -> None:
        """Download a file's full content to destination (overwritten if present).

        Deliberately a single files().get_media(...).execute() call that
        returns the whole payload in memory rather than
        googleapiclient.http.MediaIoBaseDownload's chunked/resumable path:
        PDFs here are at most a few tens of MB (see representative fixtures
        elsewhere in this project), and per-file (not per-chunk) progress
        is already reported by the caller - see ui/drive_search.py. Trading
        away resumability for this much simpler, much easier to unit-test
        shape (a fake service just returns bytes) was a deliberate call,
        not an oversight; large-file resumable download would be the first
        thing to add if this ever needs to handle multi-hundred-MB PDFs.
        """
        request = self._service.files().get_media(fileId=file_id, supportsAllDrives=True)
        content = _execute_with_retry(request)
        destination.write_bytes(content)

    def whoami(self) -> str | None:
        """Best-effort signed-in account email for the dialog's status line.

        Returns None rather than raising on failure - this is a nice-to-have
        label, never something a scan should fail over.
        """
        try:
            request = self._service.about().get(fields="user(emailAddress)")
            data = _execute_with_retry(request)
            return data.get("user", {}).get("emailAddress")
        except Exception:
            return None
