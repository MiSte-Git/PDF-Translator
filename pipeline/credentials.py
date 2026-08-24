"""Environment-variable and optional OS-keyring access to API keys.

Environment variables are checked first for machines that have not yet been
migrated to an OS keyring.  There is deliberately no plaintext credentials
file fallback.
"""
from __future__ import annotations

import os

# Service name under which all provider API keys are stored in the OS
# keyring (Windows Credential Locker / macOS Keychain / Secret Service on
# Linux).
_KEYRING_SERVICE = "pdf-translator"


def _keyring_module():
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def get_api_key(key_name: str, env_names: tuple[str, ...] = ()) -> str:
    """Read an API key from environment first, then the optional keyring.

    ``env_names`` are checked in order, followed by the uppercase key name.
    Keyring import/backend errors are treated as an unavailable fallback and
    reported without exposing any credential value.
    """
    # dict.fromkeys() dedupes while preserving order - without it, a
    # get_*_api_key() helper whose env_names already equals key_name.upper()
    # (e.g. get_deepl_api_key(): env_names=("DEEPL_API_KEY",),
    # key_name="deepl_api_key") listed that same variable twice in the
    # error message below (found 22.08.2026 while building
    # image_translate_cli's `check` command, which surfaces this message
    # to a caller like TME - see CLI.md).
    candidates = tuple(dict.fromkeys((*env_names, key_name.upper())))
    for env_name in candidates:
        value = os.environ.get(env_name)
        if value and value.strip():
            return value.strip()

    keyring = _keyring_module()
    if keyring is not None:
        try:
            value = keyring.get_password(_KEYRING_SERVICE, key_name)
        except Exception:  # backend not installed/configured
            value = None
        if value and value.strip():
            return value.strip()

    raise RuntimeError(
        f"No credential available for {key_name!r}. Set one of the environment "
        f"variables {', '.join(candidates)} or configure OS keyring service "
        f"{_KEYRING_SERVICE!r}."
    )


def set_api_key(key_name: str, value: str) -> None:
    """Store an API key in the OS keyring under _KEYRING_SERVICE."""
    value = value.strip()
    if not value:
        raise ValueError("Cannot store an empty API key")
    keyring = _keyring_module()
    if keyring is None:
        raise RuntimeError("The optional 'keyring' package is not installed")
    try:
        keyring.set_password(_KEYRING_SERVICE, key_name, value)
    except Exception as exc:
        raise RuntimeError(f"OS keyring is unavailable: {exc}") from exc


def get_google_translate_api_key() -> str:
    """Google Cloud Translation API key from the OS keyring."""
    return get_api_key("google_translate_api_key", ("GOOGLE_TRANSLATE_API_KEY",))


def get_deepl_api_key() -> str:
    """DeepL API key from the OS keyring."""
    return get_api_key("deepl_api_key", ("DEEPL_API_KEY",))


def get_openai_api_key() -> str:
    """OpenAI API key from the OS keyring."""
    return get_api_key("openai_api_key", ("OPENAI_API_KEY",))


def get_grok_api_key() -> str:
    """xAI Grok API key from the OS keyring."""
    return get_api_key("grok_api_key", ("GROK_API_KEY", "XAI_API_KEY"))
