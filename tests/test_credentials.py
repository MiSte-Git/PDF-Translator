from __future__ import annotations

import logging

from pipeline.credentials import get_api_key, get_deepl_api_key


def test_provider_environment_variable_is_used_without_keyring(monkeypatch) -> None:
    monkeypatch.setenv("DEEPL_API_KEY", "  env-secret  ")
    assert get_deepl_api_key() == "env-secret"


def test_explicit_environment_name_has_priority(monkeypatch) -> None:
    monkeypatch.setenv("CUSTOM_PROVIDER_TOKEN", "preferred")
    monkeypatch.setenv("SAMPLE_KEY", "derived")
    assert get_api_key("sample_key", ("CUSTOM_PROVIDER_TOKEN",)) == "preferred"


# --- 02.09.2026 (Michael: "Haben wir kein Log für genau solche Fälle?", ---
# nachdem ein im UI neu gespeicherter Wert scheinbar wirkungslos blieb - ein
# klassisches Symptom davon, dass eine Umgebungsvariable lautlos Vorrang vor
# dem Schlüsselbund hat, siehe get_api_key()'s Docstring) - get_api_key()
# loggt jetzt (nur) die Quelle, nie den Wert selbst.


def test_get_api_key_logs_that_the_environment_variable_was_used(monkeypatch, caplog) -> None:
    monkeypatch.setenv("SAMPLE_KEY", "some-value")
    with caplog.at_level(logging.DEBUG, logger="pipeline.credentials"):
        get_api_key("sample_key")
    assert "Umgebungsvariable SAMPLE_KEY" in caplog.text
    # The actual value must never appear in a log line.
    assert "some-value" not in caplog.text


def test_get_api_key_logs_that_the_keyring_was_used(monkeypatch, caplog) -> None:
    monkeypatch.delenv("SAMPLE_KEY", raising=False)
    monkeypatch.delenv("SAMPLE_KEY_ENV", raising=False)

    class _FakeKeyring:
        @staticmethod
        def get_password(service, key_name):
            return "keyring-value"

    import pipeline.credentials as credentials_module

    monkeypatch.setattr(credentials_module, "_keyring_module", lambda: _FakeKeyring)
    with caplog.at_level(logging.DEBUG, logger="pipeline.credentials"):
        assert get_api_key("sample_key", ("SAMPLE_KEY_ENV",)) == "keyring-value"
    assert "Schlüsselbund" in caplog.text
    assert "keyring-value" not in caplog.text


# --- env_first (02.09.2026, Michael: "Vielleicht sollten wir es umkehren ---
# und erst den Key-Ring nutzen und die env als Fallback nehmen.") - the
# translation-provider keys (get_deepl_api_key() and friends) keep the
# default env_first=True: TME relies on it to override a provider key for
# one subprocess call without touching PDF-Translator's own keyring (see
# image_translate_cli/CLI.md, "Zugangsdaten für den Provider"). The four
# Google-Drive-OAuth getters (pipeline/credentials.py, bottom section) pass
# env_first=False instead - Drive credentials are configured exclusively
# through this app's own dialog, so a leftover environment variable from an
# earlier debugging session should never be able to silently out-rank
# whatever the dialog just saved.


class _FakeKeyring:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_password(self, service, key_name) -> str:
        return self._value


def test_env_first_true_prefers_the_environment_variable_when_both_exist(monkeypatch) -> None:
    monkeypatch.setenv("SAMPLE_KEY", "from-env")
    import pipeline.credentials as credentials_module

    monkeypatch.setattr(credentials_module, "_keyring_module", lambda: _FakeKeyring("from-keyring"))
    assert get_api_key("sample_key", env_first=True) == "from-env"


def test_env_first_false_prefers_the_keyring_when_both_exist(monkeypatch) -> None:
    """The Drive-OAuth-getters' behaviour: a stored (keyring) value now
    wins over a same-named leftover environment variable, instead of being
    silently shadowed by it forever."""
    monkeypatch.setenv("SAMPLE_KEY", "from-env")
    import pipeline.credentials as credentials_module

    monkeypatch.setattr(credentials_module, "_keyring_module", lambda: _FakeKeyring("from-keyring"))
    assert get_api_key("sample_key", env_first=False) == "from-keyring"


def test_env_first_false_still_falls_back_to_the_environment_variable(monkeypatch) -> None:
    """When nothing is stored in the keyring, the environment variable is
    still used - env_first=False only changes which source wins when BOTH
    are present, it does not disable the environment fallback entirely."""
    monkeypatch.setenv("SAMPLE_KEY", "from-env")
    import pipeline.credentials as credentials_module

    monkeypatch.setattr(credentials_module, "_keyring_module", lambda: None)
    assert get_api_key("sample_key", env_first=False) == "from-env"


def test_drive_getters_use_env_first_false(monkeypatch) -> None:
    """Regression guard for the 02.09.2026 fix itself: pins down that all
    four Drive-OAuth getters actually pass env_first=False, not just that
    get_api_key() supports the parameter."""
    from pipeline import credentials as credentials_module

    calls: list[dict[str, object]] = []
    original = credentials_module.get_api_key

    def _spy(key_name, env_names=(), env_first=True):
        calls.append({"key_name": key_name, "env_first": env_first})
        return "dummy"

    monkeypatch.setattr(credentials_module, "get_api_key", _spy)
    credentials_module.get_google_drive_client_id()
    credentials_module.get_google_drive_client_secret()
    credentials_module.get_google_drive_project_id()
    credentials_module.get_google_drive_refresh_token()
    assert len(calls) == 4
    assert all(call["env_first"] is False for call in calls)
