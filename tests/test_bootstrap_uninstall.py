"""Tests for bootstrap/uninstall.py.

winreg only exists on Windows, so every registry-touching function here
guards itself with `if sys.platform != "win32": return` before ever
importing it - these tests exercise exactly that early-return path (this
suite runs on Linux/macOS in CI) plus the platform-independent
filesystem logic (remove_launcher_entry on Linux, remove_install_root,
perform_uninstall's overall sequencing via mocks).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from bootstrap import uninstall


def test_remove_registry_entry_is_noop_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    # Must not raise and must not even try to import winreg (which does
    # not exist here) - if it did, this call itself would already fail.
    uninstall.remove_registry_entry()


def test_remove_launcher_entry_removes_linux_desktop_file(monkeypatch, tmp_path):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    apps_dir = tmp_path / "applications"
    apps_dir.mkdir(parents=True)
    entry = apps_dir / "pdf-translator.desktop"
    entry.write_text("[Desktop Entry]\n")
    monkeypatch.setattr("bootstrap.desktop_integration.linux_applications_dir", lambda: apps_dir)

    uninstall.remove_launcher_entry()

    assert not entry.exists()


def test_remove_launcher_entry_missing_file_is_not_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("bootstrap.desktop_integration.linux_applications_dir", lambda: tmp_path / "nowhere")
    uninstall.remove_launcher_entry()  # must not raise


def test_remove_install_root_deletes_everything_by_default(monkeypatch, tmp_path):
    root = tmp_path / "install_root"
    (root / "venv" / "bin").mkdir(parents=True)
    (root / "app").mkdir(parents=True)
    (root / "language.json").write_text("{}")
    monkeypatch.setattr("bootstrap.paths.install_root", lambda: root)

    uninstall.remove_install_root()

    assert list(root.iterdir()) == []


def test_remove_install_root_keeps_named_file(monkeypatch, tmp_path):
    root = tmp_path / "install_root"
    root.mkdir()
    keep_me = root / "Uninstall.exe"
    keep_me.write_bytes(b"fake-exe")
    (root / "app").mkdir()
    monkeypatch.setattr("bootstrap.paths.install_root", lambda: root)

    uninstall.remove_install_root(keep=keep_me)

    assert list(root.iterdir()) == [keep_me]


def test_remove_install_root_missing_root_is_not_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr("bootstrap.paths.install_root", lambda: tmp_path / "nowhere")
    uninstall.remove_install_root()  # must not raise


def test_perform_uninstall_dev_run_removes_root_without_self_delete(monkeypatch, tmp_path):
    """Not frozen (running from source, like these tests) - there is no
    exe to keep/schedule for self-deletion, everything under
    install_root() is just removed outright."""
    root = tmp_path / "install_root"
    (root / "app").mkdir(parents=True)
    monkeypatch.setattr("bootstrap.paths.install_root", lambda: root)
    monkeypatch.setattr("bootstrap.paths.is_frozen", lambda: False)
    monkeypatch.setattr(uninstall, "remove_launcher_entry", MagicMock())
    monkeypatch.setattr(uninstall, "remove_registry_entry", MagicMock())
    schedule_mock = MagicMock()
    monkeypatch.setattr(uninstall, "_schedule_self_delete", schedule_mock)

    uninstall.perform_uninstall()

    assert not root.exists() or list(root.iterdir()) == []
    schedule_mock.assert_not_called()


def test_perform_uninstall_frozen_windows_keeps_and_schedules_exe(monkeypatch, tmp_path):
    root = tmp_path / "install_root"
    root.mkdir()
    exe = root / uninstall.UNINSTALLER_EXE_NAME
    exe.write_bytes(b"fake-exe")
    (root / "app").mkdir()

    monkeypatch.setattr("bootstrap.paths.install_root", lambda: root)
    monkeypatch.setattr("bootstrap.paths.is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(uninstall, "remove_launcher_entry", MagicMock())
    monkeypatch.setattr(uninstall, "remove_registry_entry", MagicMock())
    schedule_mock = MagicMock()
    monkeypatch.setattr(uninstall, "_schedule_self_delete", schedule_mock)

    uninstall.perform_uninstall()

    assert list(root.iterdir()) == [exe], "the exe itself must survive remove_install_root()"
    schedule_mock.assert_called_once_with(exe)


def test_schedule_self_delete_off_windows_deletes_immediately(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    target = tmp_path / "Uninstall.exe"
    target.write_bytes(b"x")

    uninstall._schedule_self_delete(target)

    assert not target.exists()


def test_schedule_self_delete_on_windows_spawns_detached_helper(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    # subprocess.CREATE_NO_WINDOW only exists on the subprocess module
    # when actually running on Windows (see bootstrap/subprocess_utils.py)
    # - not defined here, so it must be added for this cross-platform test.
    import subprocess as subprocess_module
    monkeypatch.setattr(subprocess_module, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    target = tmp_path / "Uninstall.exe"
    popen_mock = MagicMock()
    monkeypatch.setattr("subprocess.Popen", popen_mock)

    uninstall._schedule_self_delete(target)

    assert popen_mock.called
    args = popen_mock.call_args[0][0]
    assert str(target) in " ".join(args)
