from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from pipeline.translation.base import TranslationError
from pipeline.translation.deepl_provider import DeepLProvider


def test_get_usage_returns_live_character_count_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
    provider = DeepLProvider()
    response = Mock()
    response.json.return_value = {"character_count": 123456, "character_limit": 500000}
    response.raise_for_status.return_value = None

    with patch("pipeline.translation.deepl_provider.requests.get", return_value=response) as mocked_get:
        usage = provider.get_usage()

    assert usage == {"character_count": 123456, "character_limit": 500000}
    called_url = mocked_get.call_args.args[0]
    assert called_url == "https://api-free.deepl.com/v2/usage"
    assert mocked_get.call_args.kwargs["headers"]["Authorization"] == "DeepL-Auth-Key test-key:fx"


def test_get_usage_handles_no_limit_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")  # no :fx suffix -> Pro endpoint
    provider = DeepLProvider()
    response = Mock()
    response.json.return_value = {"character_count": 42, "character_limit": None}
    response.raise_for_status.return_value = None

    with patch("pipeline.translation.deepl_provider.requests.get", return_value=response) as mocked_get:
        usage = provider.get_usage()

    assert usage == {"character_count": 42, "character_limit": None}
    assert mocked_get.call_args.args[0] == "https://api.deepl.com/v2/usage"


def test_get_usage_raises_translation_error_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    monkeypatch.setattr("pipeline.credentials._keyring_module", lambda: None)
    provider = DeepLProvider()

    with pytest.raises(TranslationError):
        provider.get_usage()
