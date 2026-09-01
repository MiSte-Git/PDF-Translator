"""Tests for bootstrap/desktop_integration.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from bootstrap import desktop_integration as di


def test_linux_applications_dir_uses_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert di.linux_applications_dir() == tmp_path / "xdg" / "applications"


def test_linux_applications_dir_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert di.linux_applications_dir() == Path.home() / ".local" / "share" / "applications"


def test_windows_start_menu_programs_dir_uses_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    result = di.windows_start_menu_programs_dir()
    assert str(result).replace("\\", "/").endswith(
        "Users/test/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"
    )


def test_macos_applications_dir():
    assert di.macos_applications_dir() == Path.home() / "Applications"


def test_linux_desktop_entry_content_has_required_keys(tmp_path):
    content = di._linux_desktop_entry_content(
        tmp_path / "app", tmp_path / "venv" / "bin" / "python", None
    )
    assert "[Desktop Entry]" in content
    assert "Type=Application" in content
    assert f'Exec="{tmp_path / "venv" / "bin" / "python"}" -m ui.app' in content
    assert f"Path={tmp_path / 'app'}" in content
    assert "Icon=pdf-translator" in content


def test_create_linux_desktop_entry_writes_executable_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    entry = di.create_linux_desktop_entry(tmp_path / "app", tmp_path / "venv" / "bin" / "python")
    assert entry.is_file()
    assert entry.name == "pdf-translator.desktop"
    mode = entry.stat().st_mode
    assert mode & 0o100  # owner-executable bit set


def test_windows_shortcut_script_contains_target_and_workdir(tmp_path):
    script = di._windows_shortcut_script(
        tmp_path / "shortcut.lnk", tmp_path / "venv" / "python.exe", tmp_path / "app", None
    )
    assert "WScript.Shell" in script
    assert str(tmp_path / "venv" / "python.exe") in script
    assert str(tmp_path / "app") in script
    assert "-m ui.app" in script


def test_create_windows_shortcut_invokes_powershell(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr(di.subprocess, "run", fake_run)
    shortcut = di.create_windows_shortcut(tmp_path / "app", tmp_path / "venv" / "python.exe")
    assert shortcut.name == f"{di.APP_DISPLAY_NAME}.lnk"
    assert captured["cmd"][0] == "powershell"


def test_create_windows_shortcut_wraps_subprocess_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("powershell not found")

    monkeypatch.setattr(di.subprocess, "run", fake_run)
    with pytest.raises(di.DesktopIntegrationError):
        di.create_windows_shortcut(tmp_path / "app", tmp_path / "venv" / "python.exe")


def test_macos_launcher_script_cds_and_execs():
    script = di._macos_launcher_script(Path("/tmp/venv/bin/python"), Path("/tmp/app"))
    assert 'cd "/tmp/app"' in script
    assert 'exec "/tmp/venv/bin/python" -m ui.app' in script


def test_macos_info_plist_content_has_bundle_keys():
    plist = di._macos_info_plist_content("PDF-Translator")
    assert "<key>CFBundleExecutable</key>" in plist
    assert "<string>PDF-Translator</string>" in plist
    assert "<string>APPL</string>" in plist


def test_create_macos_app_bundle_writes_expected_structure(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    bundle = di.create_macos_app_bundle(tmp_path / "app", tmp_path / "venv" / "bin" / "python")
    assert bundle == tmp_path / "Applications" / f"{di.APP_DISPLAY_NAME}.app"
    launcher = bundle / "Contents" / "MacOS" / di.APP_DISPLAY_NAME
    assert launcher.is_file()
    assert launcher.stat().st_mode & 0o100
    assert (bundle / "Contents" / "Info.plist").is_file()


def test_create_desktop_entry_dispatches_by_platform(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(di.platform, "system", lambda: "Linux")
    entry = di.create_desktop_entry(tmp_path / "app", tmp_path / "venv" / "bin" / "python")
    assert entry.suffix == ".desktop"


def test_create_desktop_entry_raises_for_unsupported_platform(tmp_path):
    import bootstrap.desktop_integration as di_module

    original = di_module.platform.system
    di_module.platform.system = lambda: "BeOS"
    try:
        with pytest.raises(di.DesktopIntegrationError):
            di.create_desktop_entry(tmp_path / "app", tmp_path / "venv" / "python")
    finally:
        di_module.platform.system = original
