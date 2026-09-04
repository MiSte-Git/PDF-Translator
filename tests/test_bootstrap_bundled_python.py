"""Tests for bootstrap/bundled_python.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from bootstrap import bundled_python


def test_bundled_python_dir_is_none_without_meipass(monkeypatch):
    monkeypatch.delattr(bundled_python.sys, "_MEIPASS", raising=False)
    assert bundled_python.bundled_python_dir() is None


def test_bundled_python_dir_under_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert bundled_python.bundled_python_dir() == tmp_path / "python_runtime"


def test_bundled_python_executable_none_when_not_frozen(monkeypatch):
    monkeypatch.delattr(bundled_python.sys, "_MEIPASS", raising=False)
    assert bundled_python.bundled_python_executable() is None


def test_bundled_python_executable_none_when_bundle_dir_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert bundled_python.bundled_python_executable() is None


def test_bundled_python_executable_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: "Windows")
    bundle = tmp_path / "python_runtime"
    bundle.mkdir()
    (bundle / "python.exe").touch()
    assert bundled_python.bundled_python_executable() == bundle / "python.exe"


def test_bundled_python_executable_windows_missing_exe(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: "Windows")
    (tmp_path / "python_runtime").mkdir()
    assert bundled_python.bundled_python_executable() is None


@pytest.mark.parametrize("system", ["Linux", "Darwin"])
def test_bundled_python_executable_unix_prefers_plain_python3(monkeypatch, tmp_path, system):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: system)
    bin_dir = tmp_path / "python_runtime" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python3.13").touch()
    (bin_dir / "python3").touch()
    assert bundled_python.bundled_python_executable() == bin_dir / "python3"


def test_bundled_python_executable_unix_falls_back_to_versioned_name(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: "Linux")
    bin_dir = tmp_path / "python_runtime" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python3.13").touch()
    assert bundled_python.bundled_python_executable() == bin_dir / "python3.13"


def test_bundled_python_executable_unix_none_when_bin_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: "Linux")
    (tmp_path / "python_runtime").mkdir()
    assert bundled_python.bundled_python_executable() is None
