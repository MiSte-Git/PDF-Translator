"""Fetch the real app's source code (pipeline/, ui/, requirements*.txt, ...)
for Stage 2 of the installer, AND (01.09.2026) the same GitHub Release API
plumbing reused by ui/app.py's self-update check.

Downloads a versioned GitHub Release ZIP asset rather than embedding the
code in the bootstrapper itself or cloning via git (which would need git
installed and reachable, and would pull the full repo history) - see the
"App-Code-Quelle" decision in the 01.09.2026 project doc. Uses only
urllib.request from the standard library, not `requests`, keeping this
module usable before anything from requirements.txt is installed (module
docstring in bootstrap/__init__.py).

Local dev-mode fallback: no real GitHub release exists yet at the time this
module was written, so setting the PDF_TRANSLATOR_BOOTSTRAP_SOURCE
environment variable to a local directory or a local .zip file makes
download_app_source() use that instead of contacting GitHub at all. This is
for testing the bootstrapper itself, not an end-user-facing feature.

**Self-update (01.09.2026, Michael: "Update sollte die App selbst
prüfen."):** check_for_update() below reuses fetch_latest_release_metadata()/
resolve_zip_asset_url() - the exact same GitHub API call and .zip-asset
lookup Stage 2 already used to find the app source for a FRESH install -
to answer the same question for an ALREADY-installed app: "is there a newer
release than the one I'm running?" ui/app.py (via ui/workers.py's
UpdateCheckWorker/UpdateApplyWorker, both QRunnable so this network I/O
never blocks the Qt event loop) is the only caller outside bootstrap/ - see
that package's __init__.py docstring for why this is safe (bootstrap/ itself
still imports nothing from ui/ or pipeline/, this module is simply also
importable BY ui/app.py, not the other way around) and this module's own
"Tk-free" property (stdlib only) is exactly what makes that safe: importing
it from the Qt app pulls in nothing tkinter needs, and importing it from the
tkinter bootstrapper pulls in nothing Qt needs.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# See project doc "deployment-strategie-27-08-2026.md" - confirmed GitHub
# repository for this project.
REPO_OWNER = "MiSte-Git"
REPO_NAME = "TranslatePDF"

GITHUB_API_LATEST_RELEASE = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
)

DEV_SOURCE_ENV_VAR = "PDF_TRANSLATOR_BOOTSTRAP_SOURCE"

_REQUEST_TIMEOUT_SECONDS = 30
_DOWNLOAD_CHUNK_SIZE = 1 << 16  # 64 KiB

# GitHub API requires a User-Agent header on every request or it responds
# 403; any non-empty value is accepted.
_USER_AGENT = "pdf-translator-bootstrapper"

ProgressCallback = Callable[[int, Optional[int]], None]


class ReleaseSourceError(RuntimeError):
    """Raised when the app source could not be resolved or downloaded."""


def fetch_latest_release_metadata() -> dict:
    """GitHub API JSON for the repository's latest release."""
    request = urllib.request.Request(
        GITHUB_API_LATEST_RELEASE, headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ReleaseSourceError(f"Could not reach GitHub: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseSourceError(f"GitHub returned an unexpected response: {exc}") from exc


def resolve_zip_asset_url(release_metadata: dict) -> str:
    """browser_download_url of the first .zip asset in a release's assets."""
    for asset in release_metadata.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url")
        if url and name.lower().endswith(".zip"):
            return url
    raise ReleaseSourceError(
        "The latest GitHub release has no .zip asset attached."
    )


def _download_to_file(url: str, dest: Path, progress_cb: ProgressCallback | None = None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            total = response.length  # None if the server did not send Content-Length
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb is not None:
                        progress_cb(downloaded, total)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ReleaseSourceError(f"Download failed: {exc}") from exc


def _extract_zip_flattened(zip_path: Path, dest_dir: Path) -> None:
    """Extract `zip_path` into `dest_dir`, unwrapping a single top-level
    directory if the archive has one - GitHub's auto-generated release/
    source ZIPs always wrap everything in a single "<repo>-<ref>/" folder,
    which callers of app_source_dir() should not have to know about.
    """
    with tempfile.TemporaryDirectory(prefix="pdf-translator-extract-") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        entries = list(tmp_path.iterdir())
        source_root = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in source_root.iterdir():
            target = dest_dir / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(item), str(target))


def _copy_dev_source(source: Path, dest_dir: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, dest_dir, dirs_exist_ok=True)
    elif source.is_file() and source.suffix.lower() == ".zip":
        _extract_zip_flattened(source, dest_dir)
    else:
        raise ReleaseSourceError(
            f"{DEV_SOURCE_ENV_VAR}={source} is neither a directory nor a .zip file."
        )


def download_app_source(
    dest_dir: Path,
    dev_source_override: str | None = None,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Populate `dest_dir` with the app source and return it.

    `dev_source_override` defaults to the PDF_TRANSLATOR_BOOTSTRAP_SOURCE
    environment variable when None, matching the module docstring's local
    dev-mode fallback; pass an explicit value (or "") in tests to avoid
    depending on the calling environment.
    """
    override = dev_source_override if dev_source_override is not None else os.environ.get(DEV_SOURCE_ENV_VAR)
    if override:
        _copy_dev_source(Path(override).expanduser(), dest_dir)
        return dest_dir

    metadata = fetch_latest_release_metadata()
    zip_url = resolve_zip_asset_url(metadata)
    with tempfile.TemporaryDirectory(prefix="pdf-translator-download-") as tmp:
        zip_path = Path(tmp) / "release.zip"
        _download_to_file(zip_url, zip_path, progress_cb)
        _extract_zip_flattened(zip_path, dest_dir)
    return dest_dir


@dataclass(frozen=True)
class UpdateInfo:
    """A newer release than the one currently running - check_for_update()'s
    return value. `zip_url` is passed straight through to
    download_app_source()'s underlying _download_to_file() by
    ui/workers.py::UpdateApplyWorker, exactly like a fresh Stage 2 install
    uses it, just pointed at bootstrap.paths.app_source_dir() (the already-
    installed app's own source directory) instead of a brand new one.
    """

    version: str
    zip_url: str
    release_notes: str = ""


def parse_version(version: str) -> tuple[int, ...]:
    """"v1.2.3" or "1.2.3" -> (1, 2, 3). Raises ValueError if `version` has
    any non-numeric component - the caller decides what "I can't tell"
    means (see is_newer_version()/check_for_update() below), this function
    itself does not guess.
    """
    stripped = version.strip()
    if stripped.lower().startswith("v"):
        stripped = stripped[1:]
    parts = stripped.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        raise ValueError(f"Not a plain dotted-numeric version: {version!r}")
    return tuple(int(part) for part in parts)


def is_newer_version(candidate: str, current: str) -> bool:
    """Whether `candidate` (e.g. a release tag) is a newer version than
    `current` (e.g. _version.py's __version__).

    Numeric semver-style comparison via parse_version() when both parse
    cleanly - (1, 10, 0) > (1, 9, 0) the way plain string comparison would
    get wrong. If EITHER side fails to parse (an unexpected tag format on
    the release, or this project ever moves off plain dotted-numeric
    versions), falls back to "different string = newer" rather than raising
    or silently saying "no update": a self-update check would otherwise go
    permanently silent the moment one release used a tag this function
    can't parse, which is a worse failure than an occasional over-eager
    prompt. Equal strings are never "newer" either way.
    """
    if candidate.strip() == current.strip():
        return False
    try:
        return parse_version(candidate) > parse_version(current)
    except ValueError:
        return True


def check_for_update(current_version: str) -> Optional[UpdateInfo]:
    """None if `current_version` is already the latest GitHub release (or
    newer - e.g. a local dev build), otherwise an UpdateInfo describing the
    release to install.

    Raises ReleaseSourceError exactly like fetch_latest_release_metadata()/
    resolve_zip_asset_url() do (network failure, malformed API response, no
    .zip asset attached) - deliberately NOT swallowed here, so a caller can
    tell "checked, no update" (None) apart from "could not check at all"
    (exception) if it ever needs to. ui/workers.py::UpdateCheckWorker is the
    one place that currently does swallow it, into its own `failed` signal,
    since ui/app.py's startup check must never interrupt the user over a
    machine that happens to be offline right now.
    """
    metadata = fetch_latest_release_metadata()
    latest_version = str(metadata.get("tag_name", "")).strip()
    if not latest_version or not is_newer_version(latest_version, current_version):
        return None
    zip_url = resolve_zip_asset_url(metadata)
    release_notes = str(metadata.get("body") or "")
    return UpdateInfo(version=latest_version, zip_url=zip_url, release_notes=release_notes)


def download_release(info: UpdateInfo, dest_dir: Path, progress_cb: ProgressCallback | None = None) -> Path:
    """Populate `dest_dir` with the exact release described by `info` (see
    check_for_update()) and return it - the self-update counterpart to
    download_app_source() above, used by ui/workers.py::UpdateApplyWorker.

    Downloads the SPECIFIC `info.zip_url` the user was already shown and
    confirmed, rather than calling download_app_source() and letting it
    re-resolve "whatever is latest right now" a second time - avoids
    installing a different release than the one the confirmation dialog
    named, in the (unlikely, but possible) case a newer release appears in
    the few seconds between the check and the user clicking "install".
    """
    with tempfile.TemporaryDirectory(prefix="pdf-translator-download-") as tmp:
        zip_path = Path(tmp) / "release.zip"
        _download_to_file(info.zip_url, zip_path, progress_cb)
        _extract_zip_flattened(zip_path, dest_dir)
    return dest_dir
