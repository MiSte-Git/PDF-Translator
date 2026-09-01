"""Tests for bootstrap/system_lang.py."""
from __future__ import annotations

import subprocess

import pytest

from bootstrap import system_lang


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("de_DE", "de"),
        ("de-CH", "de"),
        ("DE_AT", "de"),
        ("en_US", "en"),
        ("en-GB", "en"),
        ("fr_FR", "en"),
        ("ja_JP", "en"),
        (None, "en"),
        ("", "en"),
    ],
)
def test_normalize_locale(raw, expected):
    assert system_lang.normalize_locale(raw) == expected


def test_normalize_locale_custom_fallback():
    assert system_lang.normalize_locale("fr_FR", fallback="de") == "de"


def test_raw_posix_locale_prefers_language_env(monkeypatch):
    monkeypatch.setenv("LANGUAGE", "de_DE:en_US")
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    assert system_lang._raw_posix_locale() == "de_DE"


def test_raw_posix_locale_falls_back_to_lang(monkeypatch):
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANG", "de_DE.UTF-8")
    assert system_lang._raw_posix_locale() == "de_DE.UTF-8"


def test_raw_posix_locale_none_when_undetectable(monkeypatch):
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(system_lang.locale, "getlocale", lambda: (None, None))
    assert system_lang._raw_posix_locale() is None


def test_raw_macos_locale_parses_defaults_output(monkeypatch):
    class _FakeCompletedProcess:
        stdout = "de_CH\n"

    monkeypatch.setattr(
        system_lang.subprocess, "run", lambda *a, **k: _FakeCompletedProcess()
    )
    assert system_lang._raw_macos_locale() == "de_CH"


def test_raw_macos_locale_none_on_error(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="defaults")

    monkeypatch.setattr(system_lang.subprocess, "run", fake_run)
    assert system_lang._raw_macos_locale() is None


def test_raw_windows_locale_none_off_windows(monkeypatch):
    # ctypes.windll does not exist on non-Windows platforms; the function
    # must catch that and return None rather than raising.
    assert system_lang._raw_windows_locale() is None


def test_detect_system_language_dispatches_by_platform(monkeypatch):
    monkeypatch.setattr(system_lang.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(system_lang, "_raw_macos_locale", lambda: "de_DE")
    assert system_lang.detect_system_language() == "de"

    monkeypatch.setattr(system_lang.platform, "system", lambda: "Linux")
    monkeypatch.setattr(system_lang, "_raw_posix_locale", lambda: "fr_FR")
    assert system_lang.detect_system_language() == "en"
