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


# --- 06.09.2026: stable copy of the bundled runtime (real-install fix) ------


def test_ensure_stable_python_runtime_none_when_meipass_missing(monkeypatch, tmp_path):
    monkeypatch.delattr(bundled_python.sys, "_MEIPASS", raising=False)
    assert bundled_python.ensure_stable_python_runtime(tmp_path / "install-root") is None


def test_ensure_stable_python_runtime_copies_and_returns_executable(monkeypatch, tmp_path):
    meipass = tmp_path / "meipass"
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: "Linux")
    bin_dir = meipass / "python_runtime" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python3").write_text("fake interpreter")

    install_root = tmp_path / "install-root"
    result = bundled_python.ensure_stable_python_runtime(install_root)

    assert result == install_root / "python_runtime" / "bin" / "python3"
    assert result.is_file()
    assert result.read_text() == "fake interpreter"
    # the transient source is untouched - only copied, not moved
    assert (bin_dir / "python3").is_file()


def test_ensure_stable_python_runtime_overwrites_stale_copy(monkeypatch, tmp_path):
    meipass = tmp_path / "meipass"
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(bundled_python.platform, "system", lambda: "Linux")
    bin_dir = meipass / "python_runtime" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python3").write_text("new interpreter")

    install_root = tmp_path / "install-root"
    stale_dir = install_root / "python_runtime"
    stale_dir.mkdir(parents=True)
    (stale_dir / "leftover-from-old-version.txt").write_text("stale")

    result = bundled_python.ensure_stable_python_runtime(install_root)

    assert result.read_text() == "new interpreter"
    assert not (stale_dir / "leftover-from-old-version.txt").exists()


def test_ensure_stable_python_runtime_none_when_source_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(bundled_python.sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)
    assert bundled_python.ensure_stable_python_runtime(tmp_path / "install-root") is None
