"""OS-keyring-backed access to external API keys.

This is the only place API keys are read from/written to storage. Unlike
TME's credentials.py, there is deliberately no plaintext credentials.json
fallback - if the OS keyring has no value, callers get a clear error
instead of silently falling back to an unencrypted file.
"""
from __future__ import annotations

import keyring

# Service name under which all provider API keys are stored in the OS
# keyring (Windows Credential Locker / macOS Keychain / Secret Service on
# Linux).
_KEYRING_SERVICE = "pdf-translator"


def get_api_key(key_name: str) -> str:
    """Read an API key from the OS keyring under _KEYRING_SERVICE.

    Raises RuntimeError with a clear message (incl. a one-liner to set the
    value) if nothing is stored under `key_name`.
    """
    value = keyring.get_password(_KEYRING_SERVICE, key_name)
    if not value or not value.strip():
        raise RuntimeError(
            f"No value stored for {key_name!r} in the OS keyring "
            f"(service={_KEYRING_SERVICE!r}). Set it once via:\n"
            f"  python -c \"import keyring; keyring.set_password("
            f"'{_KEYRING_SERVICE}', '{key_name}', 'YOUR_KEY')\""
        )
    return value.strip()


def set_api_key(key_name: str, value: str) -> None:
    """Store an API key in the OS keyring under _KEYRING_SERVICE."""
    value = value.strip()
    if not value:
        raise ValueError("Cannot store an empty API key")
    keyring.set_password(_KEYRING_SERVICE, key_name, value)


def get_google_translate_api_key() -> str:
    """Google Cloud Translation API key from the OS keyring."""
    return get_api_key("google_translate_api_key")


def get_deepl_api_key() -> str:
    """DeepL API key from the OS keyring."""
    return get_api_key("deepl_api_key")


def get_openai_api_key() -> str:
    """OpenAI API key from the OS keyring."""
    return get_api_key("openai_api_key")


def get_grok_api_key() -> str:
    """xAI Grok API key from the OS keyring."""
    return get_api_key("grok_api_key")
