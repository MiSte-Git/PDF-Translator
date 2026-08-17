from __future__ import annotations

from pipeline.credentials import get_api_key, get_deepl_api_key


def test_provider_environment_variable_is_used_without_keyring(monkeypatch) -> None:
    monkeypatch.setenv("DEEPL_API_KEY", "  env-secret  ")
    assert get_deepl_api_key() == "env-secret"


def test_explicit_environment_name_has_priority(monkeypatch) -> None:
    monkeypatch.setenv("CUSTOM_PROVIDER_TOKEN", "preferred")
    monkeypatch.setenv("SAMPLE_KEY", "derived")
    assert get_api_key("sample_key", ("CUSTOM_PROVIDER_TOKEN",)) == "preferred"
