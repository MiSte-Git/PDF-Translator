"""Tests for bootstrap/credentials_step.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bootstrap import credentials_step

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_load_settings_module_from_real_repo():
    module = credentials_step.load_settings_module(REPO_ROOT)
    assert hasattr(module, "PROVIDER_CREDENTIALS")
    assert hasattr(module, "credential_status")
    assert hasattr(module, "save_credential")


def test_list_providers_uses_fixed_order_then_extras():
    providers = credentials_step.list_providers(REPO_ROOT)
    assert providers[:4] == ["deepl", "google", "openai", "grok"]


def test_provider_status_delegates_to_settings_module(monkeypatch, tmp_path):
    calls = []

    class _FakeSettings:
        PROVIDER_CREDENTIALS = {"deepl": ("deepl_api_key", ("DEEPL_API_KEY",))}

        @staticmethod
        def credential_status(provider):
            calls.append(provider)
            return "credential.missing"

        @staticmethod
        def save_credential(provider, value, target):
            calls.append((provider, value, target))

    monkeypatch.setattr(credentials_step, "load_settings_module", lambda app_dir: _FakeSettings)
    assert credentials_step.provider_status(tmp_path, "deepl") == "credential.missing"
    assert calls == ["deepl"]


def test_save_provider_credential_defaults_to_keyring_target(monkeypatch, tmp_path):
    calls = []

    class _FakeSettings:
        @staticmethod
        def save_credential(provider, value, target):
            calls.append((provider, value, target))

    monkeypatch.setattr(credentials_step, "load_settings_module", lambda app_dir: _FakeSettings)
    credentials_step.save_provider_credential(tmp_path, "openai", "sk-test")
    assert calls == [("openai", "sk-test", "keyring")]


def test_signup_url_known_and_unknown_provider():
    assert credentials_step.signup_url("deepl").startswith("https://")
    assert credentials_step.signup_url("does-not-exist") is None


def test_open_signup_page_returns_false_for_unknown_provider():
    assert credentials_step.open_signup_page("does-not-exist") is False


def test_open_signup_page_uses_webbrowser(monkeypatch):
    opened = {}

    def fake_open(url):
        opened["url"] = url
        return True

    monkeypatch.setattr(credentials_step.webbrowser, "open", fake_open)
    assert credentials_step.open_signup_page("openai") is True
    assert opened["url"] == credentials_step.PROVIDER_SIGNUP_URLS["openai"]


def test_open_signup_page_swallows_browser_errors(monkeypatch):
    def fake_open(url):
        raise RuntimeError("no display")

    monkeypatch.setattr(credentials_step.webbrowser, "open", fake_open)
    assert credentials_step.open_signup_page("openai") is False


def test_import_from_app_source_inserts_arbitrary_directory(tmp_path, monkeypatch):
    # Proves the dynamic-import mechanism itself works against a directory
    # that is not this repo, not just against the real ui/settings.py -
    # relevant because in production app_source_dir is a freshly downloaded
    # release, unrelated to wherever the bootstrapper executable lives.
    #
    # sys.modules["ui"]/["ui.settings"] are removed via monkeypatch.delitem
    # rather than a plain sys.modules.pop(): a plain pop deletes the entry
    # for good, so the fake "ui" package this test creates (found earlier
    # on sys.path than the real one) permanently shadows the real one for
    # every test that runs afterwards in the same pytest process - this
    # broke tests/test_ui_models.py when first written here.
    # monkeypatch.delitem restores whatever was cached before this test on
    # teardown, exactly like every other monkeypatch call.
    package_dir = tmp_path / "fake_app" / "ui"
    package_dir.mkdir(parents=True)
    (tmp_path / "fake_app" / "ui" / "__init__.py").write_text("")
    (package_dir / "settings.py").write_text(
        "PROVIDER_CREDENTIALS = {'stub': ('stub_key', ())}\n"
        "def credential_status(provider):\n    return 'credential.missing'\n"
        "def save_credential(provider, value, target):\n    pass\n"
    )
    monkeypatch.delitem(sys.modules, "ui.settings", raising=False)
    monkeypatch.delitem(sys.modules, "ui", raising=False)
    try:
        module = credentials_step.load_settings_module(tmp_path / "fake_app")
        assert module.PROVIDER_CREDENTIALS == {"stub": ("stub_key", ())}
    finally:
        if str(tmp_path / "fake_app") in sys.path:
            sys.path.remove(str(tmp_path / "fake_app"))
