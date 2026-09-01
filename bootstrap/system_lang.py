"""Detect the system UI language and normalize it to a supported catalogue.

Only "de" and "en" are marked available=True in ui/i18n_data.py::LOCALES
right now. Per the project doc decision ("Fallback Englisch (nicht
Deutsch) bei nicht unterstützter Systemsprache"), any system language other
than German falls back to English - unlike ui/i18n.py::LanguageManager,
which still hardcodes a German fallback (see that module's docstring; a
harmonization is listed as an open follow-up in the project doc and
deliberately left alone here to avoid changing existing app-startup
behaviour as a side effect of this feature).
"""
from __future__ import annotations

import locale
import os
import platform
import subprocess

_FALLBACK_LANGUAGE = "en"
_SUPPORTED_LANGUAGES = ("de", "en")

_MACOS_LOCALE_TIMEOUT_SECONDS = 5


def raw_system_locale() -> str | None:
    """Best-effort raw locale/language code for the current OS, e.g.
    "de_DE", "en_US", "de-CH". None if it could not be determined.
    """
    system = platform.system()
    if system == "Windows":
        return _raw_windows_locale()
    if system == "Darwin":
        return _raw_macos_locale()
    return _raw_posix_locale()


def _raw_windows_locale() -> str | None:
    try:
        import ctypes

        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
        if not lang_id:
            return None
        code = locale.windows_locale.get(lang_id)
        return code
    except Exception:
        # ctypes.windll only exists on Windows; any failure here (missing
        # attribute, unknown lang_id, ...) just means "could not determine".
        return None


def _raw_macos_locale() -> str | None:
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleLocale"],
            capture_output=True,
            text=True,
            timeout=_MACOS_LOCALE_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def _raw_posix_locale() -> str | None:
    for env_name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(env_name)
        if value:
            # LANGUAGE may list several colon-separated preferences; the
            # first one is the user's top choice.
            return value.split(":", 1)[0]
    try:
        code, _encoding = locale.getlocale()
    except (ValueError, TypeError):
        return None
    return code


def normalize_locale(raw: str | None, fallback: str = _FALLBACK_LANGUAGE) -> str:
    """Map a raw locale code to one of the supported catalogues (currently
    "de"/"en"), falling back to `fallback` (English by default) for
    anything unsupported or undetectable.
    """
    if not raw:
        return fallback
    primary = raw.strip().lower().replace("_", "-").split("-", 1)[0]
    if primary in _SUPPORTED_LANGUAGES:
        return primary
    return fallback


def detect_system_language() -> str:
    """Convenience wrapper: raw_system_locale() normalized in one call."""
    return normalize_locale(raw_system_locale())
