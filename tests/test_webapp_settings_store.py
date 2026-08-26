"""Regression coverage for webapp/settings_store.py - the QSettings
replacement for the local-server+pywebview pilot (see Backlog.md
26.08.2026 "lokaler Server + pywebview" and webapp/__init__.py's own
docstring).

Every test passes an explicit `path` into load()/save() (tmp_path-based)
so the real, per-machine settings file is never read or written by the
test suite - mirrors tests/conftest.py's own stated reasoning for why
QSettings isolation mattered there (a real hang/failure from one test's
persisted state leaking into another): the same class of bug is possible
here if a test ever touched the real config_dir() path by accident, so
config_dir()/settings_path() themselves are exercised separately, with
HOME/XDG_CONFIG_HOME/APPDATA monkeypatched to a tmp_path rather than left
pointing at the real environment.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from webapp import settings_store


def test_load_returns_defaults_when_no_file_exists(tmp_path: Path) -> None:
    result = settings_store.load(tmp_path / "does-not-exist.json")
    assert result == settings_store.DEFAULTS
    # Must be a copy, not the same object - a caller mutating the
    # returned dict must never corrupt the module-level DEFAULTS for
    # every future call in the same process.
    result["form"]["target_lang"] = "FR"
    assert settings_store.DEFAULTS["form"]["target_lang"] == "DE"


def test_load_returns_defaults_when_file_is_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not valid json", encoding="utf-8")
    # A corrupt file must never crash server startup (webapp/server.py
    # reads settings on every /api/config call) - fall back to DEFAULTS
    # exactly like a missing file does.
    assert settings_store.load(path) == settings_store.DEFAULTS


def test_save_then_load_round_trips_a_full_update(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings_store.save(
        {
            "provider": "google",
            "max_chars": 250_000,
            "form": {"target_lang": "FR", "ocr_engine": "paddleocr"},
        },
        path,
    )
    result = settings_store.load(path)
    assert result["provider"] == "google"
    assert result["max_chars"] == 250_000
    assert result["form"]["target_lang"] == "FR"
    assert result["form"]["ocr_engine"] == "paddleocr"
    # Fields not touched by this save() call keep their default - a
    # partial update must not silently reset the rest of the form, the
    # same "only the changed field moves" behavior
    # ui/app.py::_persist_form_state() has via individual setValue()
    # calls per field.
    assert result["form"]["inpainting_backend"] == "box_overlay"
    assert result["last_source_dir"] == ""


def test_save_is_a_partial_merge_not_an_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings_store.save({"form": {"target_lang": "FR"}}, path)
    # A second, unrelated save() must not undo the first one's change -
    # this is the read-modify-write contract the module's own docstring
    # promises, verified concretely rather than just asserted in prose.
    settings_store.save({"last_output_dir": "/tmp/out"}, path)
    result = settings_store.load(path)
    assert result["form"]["target_lang"] == "FR"
    assert result["last_output_dir"] == "/tmp/out"


def test_save_creates_missing_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "does" / "not" / "exist" / "settings.json"
    settings_store.save({"provider": "openai"}, path)
    assert path.exists()
    assert settings_store.load(path)["provider"] == "openai"


def test_config_dir_resolution_never_touches_the_real_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Linux/XDG path.
    monkeypatch.setattr(settings_store.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert settings_store.config_dir() == tmp_path / "xdg" / "pdf-translator"

    # Linux without XDG_CONFIG_HOME set - falls back to ~/.config, but
    # Path.home() itself is monkeypatched so this never resolves to the
    # real machine's home directory during a test run.
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(settings_store.Path, "home", staticmethod(lambda: tmp_path / "home"))
    assert settings_store.config_dir() == tmp_path / "home" / ".config" / "pdf-translator"

    # Windows.
    monkeypatch.setattr(settings_store.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert settings_store.config_dir() == tmp_path / "appdata" / settings_store.APP_NAME

    # macOS.
    monkeypatch.setattr(settings_store.sys, "platform", "darwin")
    assert settings_store.config_dir() == (
        tmp_path / "home" / "Library" / "Application Support" / settings_store.APP_NAME
    )
