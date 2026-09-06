"""API-key setup step, reusing ui/settings.py rather than re-implementing
credential storage a second time.

This deliberately imports ui.settings (and, transitively, only
pipeline.credentials.set_api_key) from the just-downloaded app_source_dir
at runtime, not a copy statically bundled into the bootstrapper executable.
The credentials step therefore always runs after
bootstrap/installer.py::run_install() has finished (see the "API-Schlüssel"
section of the 01.09.2026 project doc) - this guarantees the exact same
credential-storage code path the freshly-installed app itself will use at
first launch, with no risk of the bootstrapper's own (possibly older,
frozen-at-build-time) copy drifting from it.

Both ui/settings.py and pipeline/credentials.py are Qt-free by design (see
their own docstrings), so importing them here does not pull in PySide6.
"""
from __future__ import annotations

import importlib
import sys
import time
import webbrowser
from pathlib import Path
from types import ModuleType

# Order mirrors the "bootstrap.credentials_provider_*" i18n keys and the
# checklist-first UX decision (project doc: "Checkliste zuerst ... dann
# nacheinander") - Google listed after DeepL despite alphabetical order
# would put it first, because DeepL is the quicker, simpler sign-up and
# should be what a user sees first.
PROVIDER_ORDER = ("deepl", "google", "openai", "grok")

# Sign-up/API-console URLs opened by the "Schlüssel besorgen" button.
# UI-only concern (which page to send a browser to) - deliberately kept out
# of ui/settings.py, which only knows about *storing* an already-obtained
# key.
PROVIDER_SIGNUP_URLS = {
    "deepl": "https://www.deepl.com/pro-api",
    "google": "https://console.cloud.google.com/apis/library/translate.googleapis.com",
    "openai": "https://platform.openai.com/api-keys",
    "grok": "https://console.x.ai/",
}


# 05.09.2026: on a real Windows machine, this import failed with "No
# module named 'ui.settings'" immediately after extraction, even though
# the file demonstrably existed on disk with the right content moments
# later (a manual PowerShell listing confirmed it: correct size, correct
# timestamp). A recursive directory listing taken around the same time
# showed the identical symptom one level up: it came back completely
# empty for every freshly-extracted app/* subdirectory (ui, bootstrap,
# pipeline, ...) while a much larger, already-settled sibling tree
# (venv/, populated by pip over the previous ~70 seconds) enumerated
# perfectly, deeply and correctly. That points at antivirus real-time
# scanning racing the installer: files this fresh can briefly appear
# missing or locked to any process that tries to read the directory,
# including Python's own import machinery. The fix is a short, bounded
# retry - and critically, importlib.invalidate_caches() before each
# retry, because once FileFinder sees a package directory as empty it
# caches that verdict in sys.path_importer_cache, so a bare retry alone
# would keep failing even after the antivirus scan releases the files.
_IMPORT_RETRY_ATTEMPTS = 5
_IMPORT_RETRY_DELAY_SECONDS = 0.4


def _import_from_app_source(app_source_dir: Path, module_name: str) -> ModuleType:
    app_source_str = str(app_source_dir)
    if app_source_str not in sys.path:
        sys.path.insert(0, app_source_str)

    last_exc: ImportError | None = None
    for attempt in range(1, _IMPORT_RETRY_ATTEMPTS + 1):
        if attempt > 1:
            importlib.invalidate_caches()
            time.sleep(_IMPORT_RETRY_DELAY_SECONDS)
        try:
            return importlib.import_module(module_name)
        except ImportError as exc:
            last_exc = exc

    # All attempts exhausted - gather diagnostics and raise. Whatever the
    # crash log captures next time should already have the answer: does
    # app_source_dir actually exist on disk at this point, what is in it,
    # does the specific expected .py file exist, and what does sys.path
    # (which PyInstaller's frozen import machinery treats specially) look
    # like when this failed.
    assert last_exc is not None
    expected_file = app_source_dir.joinpath(*module_name.split(".")).with_suffix(".py")
    parent_init = app_source_dir / module_name.split(".")[0] / "__init__.py"
    try:
        top_level = sorted(p.name for p in app_source_dir.iterdir()) if app_source_dir.is_dir() else None
    except OSError as list_exc:
        top_level = f"<listdir failed: {list_exc}>"
    diagnostic = (
        f"Could not import {module_name!r} from {app_source_dir} after "
        f"{_IMPORT_RETRY_ATTEMPTS} attempts: {last_exc}\n"
        f"  app_source_dir.is_dir(): {app_source_dir.is_dir()}\n"
        f"  app_source_dir top-level entries: {top_level}\n"
        f"  expected file {expected_file}: exists={expected_file.is_file()}\n"
        f"  parent package init {parent_init}: exists={parent_init.is_file()}\n"
        f"  sys.path[:5]: {sys.path[:5]}\n"
        f"  sys.frozen: {getattr(sys, 'frozen', False)}, _MEIPASS: {getattr(sys, '_MEIPASS', None)}"
    )
    raise ImportError(diagnostic) from last_exc


def load_settings_module(app_source_dir: Path) -> ModuleType:
    """The downloaded app's ui.settings module (PROVIDER_CREDENTIALS,
    credential_status(), save_credential())."""
    return _import_from_app_source(app_source_dir, "ui.settings")


def list_providers(app_source_dir: Path) -> list[str]:
    settings = load_settings_module(app_source_dir)
    known = set(settings.PROVIDER_CREDENTIALS)
    # PROVIDER_ORDER first (fixed, deliberate display order), then anything
    # ui/settings.py added later that this module does not know about yet -
    # so a new provider never silently disappears from the bootstrapper.
    ordered = [p for p in PROVIDER_ORDER if p in known]
    ordered.extend(sorted(known - set(ordered)))
    return ordered


def provider_status(app_source_dir: Path, provider: str) -> str:
    """One of "credential.environment" / "credential.keyring" /
    "credential.missing" - see ui/settings.py::credential_status()."""
    settings = load_settings_module(app_source_dir)
    return settings.credential_status(provider)


def save_provider_credential(
    app_source_dir: Path, provider: str, value: str, target: str = "keyring"
) -> None:
    """Stores `value` for `provider` via ui/settings.py::save_credential().

    `target` defaults to "keyring" (not "environment") because a bootstrap-
    time environment variable would only live for the bootstrapper's own
    process and be gone by the time the real app starts - the OS keyring is
    the only target that actually persists across the app's later launches.
    """
    settings = load_settings_module(app_source_dir)
    settings.save_credential(provider, value, target)


def signup_url(provider: str) -> str | None:
    return PROVIDER_SIGNUP_URLS.get(provider)


def open_signup_page(provider: str) -> bool:
    """Opens the provider's sign-up page in the system's default browser.

    Returns False (instead of raising) if there is no known URL or the
    browser could not be launched - a failed browser open should never
    block the rest of the credentials step, the user can still paste an
    already-obtained key or copy the URL manually.
    """
    url = signup_url(provider)
    if not url:
        return False
    try:
        return webbrowser.open(url)
    except Exception:
        return False
