"""Credential status and non-secret UI settings."""
from __future__ import annotations

import os

from pipeline.credentials import set_api_key

PROVIDER_CREDENTIALS = {
    "deepl": ("deepl_api_key", ("DEEPL_API_KEY",)),
    "google": ("google_translate_api_key", ("GOOGLE_TRANSLATE_API_KEY",)),
    "openai": ("openai_api_key", ("OPENAI_API_KEY",)),
    "grok": ("grok_api_key", ("GROK_API_KEY", "XAI_API_KEY")),
}


def credential_status(provider: str) -> str:
    key_name, env_names = PROVIDER_CREDENTIALS[provider]
    if any(os.environ.get(name, "").strip() for name in env_names):
        return "credential.environment"
    try:
        import keyring
        if keyring.get_password("pdf-translator", key_name):
            return "credential.keyring"
    except Exception:
        pass
    return "credential.missing"


def save_credential(provider: str, value: str, target: str) -> None:
    value = value.strip()
    if not value:
        raise ValueError("API-Schlüssel darf nicht leer sein.")
    key_name, env_names = PROVIDER_CREDENTIALS[provider]
    if target in {"environment", "both"}:
        os.environ[env_names[0]] = value
    if target in {"keyring", "both"}:
        set_api_key(key_name, value)
