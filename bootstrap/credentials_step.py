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


def _import_from_app_source(app_source_dir: Path, module_name: str) -> ModuleType:
    app_source_str = str(app_source_dir)
    if app_source_str not in sys.path:
        sys.path.insert(0, app_source_str)
    return importlib.import_module(module_name)


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
