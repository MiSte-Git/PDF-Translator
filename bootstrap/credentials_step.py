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

import importlib.util
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


_loaded_settings_modules: dict[str, ModuleType] = {}


def load_settings_module(app_source_dir: Path) -> ModuleType:
    """Loads the downloaded app's ui/settings.py directly from its file,
    deliberately bypassing the "ui" *package* import machinery.

    05.09.2026: importlib.import_module("ui.settings") reliably failed
    here with "No module named 'ui.settings'" on a real Windows install.
    A bounded retry with importlib.invalidate_caches() (06.09.2026) made
    no difference across 5 attempts even though the file demonstrably
    existed on disk the whole time - which ruled out a timing/antivirus
    race and pointed at something structural instead.

    The actual cause: bootstrap/controller.py does
    `from ui.i18n_data import CATALOGUES, DE` at module load time (the
    wizard's own pre-download screens need their text before anything has
    been downloaded). PyInstaller's static analysis follows that import
    and bundles a partial "ui" package - just __init__.py and
    i18n_data.py - directly into the frozen executable. PyInstaller's own
    importer for that bundled code sits in sys.meta_path *ahead of* the
    regular filesystem-based finder, so once "ui" has been imported that
    way, any later "ui.settings" lookup resolves against the frozen
    package's own (non-filesystem) __path__ - never against
    app_source_dir, no matter what sys.path says or how many times the
    import is retried.

    Loading ui/settings.py by its exact file path sidesteps the "ui"
    package - and thus the frozen shadow copy - entirely. ui/settings.py
    only does absolute imports (`from pipeline.credentials import
    set_api_key`), never relative ones, and "pipeline" is never
    statically imported anywhere in bootstrap/, so it is never frozen
    into the executable and resolves normally via app_source_dir on
    sys.path.
    """
    cache_key = str(app_source_dir)
    cached = _loaded_settings_modules.get(cache_key)
    if cached is not None:
        return cached

    if cache_key not in sys.path:
        sys.path.insert(0, cache_key)

    settings_file = app_source_dir / "ui" / "settings.py"
    if not settings_file.is_file():
        raise ImportError(
            f"Expected ui/settings.py at {settings_file}, but it does not "
            f"exist (app_source_dir.is_dir(): {app_source_dir.is_dir()})"
        )

    spec = importlib.util.spec_from_file_location(
        "_pdftranslator_ui_settings", settings_file
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for {settings_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _loaded_settings_modules[cache_key] = module
    return module


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
