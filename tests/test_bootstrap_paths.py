"""Tests for bootstrap/paths.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from bootstrap import paths


@pytest.mark.parametrize(
    "system, env, expected_contains",
    [
        ("Linux", {}, ".local/share/pdf-translator"),
        ("Linux", {"XDG_DATA_HOME": "/custom/xdg"}, "/custom/xdg/pdf-translator"),
        ("Darwin", {}, "Library/Application Support/pdf-translator"),
        ("Windows", {"LOCALAPPDATA": r"C:\Users\test\AppData\Local"}, "PDF-Translator"),
    ],
)
def test_install_root_per_platform(monkeypatch, system, env, expected_contains):
    monkeypatch.setattr(paths.platform, "system", lambda: system)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False) if "XDG_DATA_HOME" not in env else None
    root = paths.install_root()
    assert expected_contains in str(root).replace("\\", "/")


def test_derived_paths_are_children_of_install_root(monkeypatch):
    monkeypatch.setattr(paths.platform, "system", lambda: "Linux")
    root = paths.install_root()
    assert paths.venv_dir() == root / "venv"
    assert paths.app_source_dir() == root / "app"
    assert paths.language_marker_file() == root / "language.json"
    assert paths.gpu_check_marker_file() == root / "gpu_check.json"


def test_venv_python_platform_specific(monkeypatch, tmp_path):
    venv = tmp_path / "venv"
    monkeypatch.setattr(paths.platform, "system", lambda: "Windows")
    assert paths.venv_python(venv) == venv / "Scripts" / "python.exe"
    monkeypatch.setattr(paths.platform, "system", lambda: "Linux")
    assert paths.venv_python(venv) == venv / "bin" / "python"


def test_ensure_install_root_creates_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    root = paths.ensure_install_root()
    assert root.is_dir()
    assert root == Path(tmp_path / "xdg" / "pdf-translator")


def test_is_frozen_reflects_sys_frozen(monkeypatch):
    monkeypatch.delattr(paths.sys, "frozen", raising=False)
    assert paths.is_frozen() is False
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    assert paths.is_frozen() is True
