"""Add PDF-Translator to the desktop's application launcher, per platform.

Deliberately does NOT build a .deb/.rpm/.msi/.dmg package - see the
"Desktop-Integration" section of the 01.09.2026 project doc. None of those
formats can programmatically pin an app to the taskbar/dock either (an
OS-level restriction on Windows and macOS since Windows 7), so the only
thing any installer format actually delivers is "the app shows up in the
launcher, ready for the user to pin manually" - which the lightweight,
no-admin-rights mechanisms below achieve just as well:

- Linux: a .desktop file (freedesktop.org Desktop Entry spec) in the
  per-user ~/.local/share/applications/ - picked up by GNOME/KDE/etc.
  without root and without a system package.
- Windows: a .lnk shortcut in the per-user Start Menu Programs folder,
  created via PowerShell's WScript.Shell COM object (no pywin32 dependency
  needed just for this one shortcut).
- macOS: a minimal hand-built .app bundle (Contents/MacOS + Contents/
  Info.plist) in ~/Applications - the same structure PyInstaller's
  --windowed mode produces natively for the real app once that is built.
"""
from __future__ import annotations

import os
import platform
import stat
import subprocess
from pathlib import Path

APP_DISPLAY_NAME = "PDF-Translator"
APP_ENTRY_SLUG = "pdf-translator"
_WINDOWS_SHORTCUT_TIMEOUT_SECONDS = 30


class DesktopIntegrationError(RuntimeError):
    """Raised when the launcher entry could not be created."""


def linux_applications_dir() -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / "applications"


def windows_start_menu_programs_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def macos_applications_dir() -> Path:
    return Path.home() / "Applications"


def _linux_desktop_entry_content(app_source_dir: Path, venv_python: Path, icon_path: Path | None) -> str:
    icon_line = f"Icon={icon_path}" if icon_path else f"Icon={APP_ENTRY_SLUG}"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_DISPLAY_NAME}\n"
        "Comment=Translate documents while keeping their formatting\n"
        f'Exec="{venv_python}" -m ui.app\n'
        f"Path={app_source_dir}\n"
        f"{icon_line}\n"
        "Categories=Office;\n"
        "Terminal=false\n"
    )


def create_linux_desktop_entry(
    app_source_dir: Path, venv_python: Path, icon_path: Path | None = None
) -> Path:
    target_dir = linux_applications_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    entry_path = target_dir / f"{APP_ENTRY_SLUG}.desktop"
    entry_path.write_text(_linux_desktop_entry_content(app_source_dir, venv_python, icon_path))
    # Desktop files must be executable for some launchers to trust them.
    entry_path.chmod(entry_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return entry_path


def _windows_shortcut_script(shortcut_path: Path, venv_python: Path, app_source_dir: Path, icon_path: Path | None) -> str:
    icon_location = str(icon_path) if icon_path else str(venv_python)
    # WScript.Shell is a built-in Windows COM object; no extra package
    # (e.g. pywin32) needed just to create one .lnk file.
    return (
        "$WshShell = New-Object -ComObject WScript.Shell\n"
        f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")\n'
        f'$Shortcut.TargetPath = "{venv_python}"\n'
        '$Shortcut.Arguments = "-m ui.app"\n'
        f'$Shortcut.WorkingDirectory = "{app_source_dir}"\n'
        f'$Shortcut.IconLocation = "{icon_location}"\n'
        f'$Shortcut.Description = "{APP_DISPLAY_NAME}"\n'
        "$Shortcut.Save()\n"
    )


def create_windows_shortcut(
    app_source_dir: Path, venv_python: Path, icon_path: Path | None = None
) -> Path:
    target_dir = windows_start_menu_programs_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = target_dir / f"{APP_DISPLAY_NAME}.lnk"
    script = _windows_shortcut_script(shortcut_path, venv_python, app_source_dir, icon_path)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=_WINDOWS_SHORTCUT_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DesktopIntegrationError(f"Could not create the Start Menu shortcut: {exc}") from exc
    return shortcut_path


def _macos_launcher_script(venv_python: Path, app_source_dir: Path) -> str:
    return (
        "#!/bin/sh\n"
        f'cd "{app_source_dir}"\n'
        f'exec "{venv_python}" -m ui.app\n'
    )


def _macos_info_plist_content(bundle_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>CFBundleName</key>\n"
        f"    <string>{bundle_name}</string>\n"
        "    <key>CFBundleExecutable</key>\n"
        f"    <string>{bundle_name}</string>\n"
        "    <key>CFBundleIdentifier</key>\n"
        f"    <string>com.pdf-translator.{APP_ENTRY_SLUG}</string>\n"
        "    <key>CFBundlePackageType</key>\n"
        "    <string>APPL</string>\n"
        "    <key>CFBundleShortVersionString</key>\n"
        "    <string>1.0</string>\n"
        "    <key>LSMinimumSystemVersion</key>\n"
        "    <string>10.13</string>\n"
        "</dict>\n"
        "</plist>\n"
    )


def create_macos_app_bundle(
    app_source_dir: Path, venv_python: Path, icon_path: Path | None = None
) -> Path:
    bundle_path = macos_applications_dir() / f"{APP_DISPLAY_NAME}.app"
    macos_dir = bundle_path / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = macos_dir / APP_DISPLAY_NAME
    launcher_path.write_text(_macos_launcher_script(venv_python, app_source_dir))
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    info_plist_path = bundle_path / "Contents" / "Info.plist"
    info_plist_path.write_text(_macos_info_plist_content(APP_DISPLAY_NAME))

    if icon_path is not None and icon_path.is_file():
        resources_dir = bundle_path / "Contents" / "Resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        (resources_dir / icon_path.name).write_bytes(icon_path.read_bytes())

    return bundle_path


def create_desktop_entry(
    app_source_dir: Path, venv_python: Path, icon_path: Path | None = None
) -> Path:
    """Dispatches to the platform-appropriate launcher-entry creator."""
    system = platform.system()
    if system == "Windows":
        return create_windows_shortcut(app_source_dir, venv_python, icon_path)
    if system == "Darwin":
        return create_macos_app_bundle(app_source_dir, venv_python, icon_path)
    if system == "Linux":
        return create_linux_desktop_entry(app_source_dir, venv_python, icon_path)
    raise DesktopIntegrationError(f"Unsupported platform: {system!r}")
