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

Developer variant (03.09.2026, Michael: "Ich als Entwickler möchte aber
auch nicht immer die App aus der Shell starten, sondern über die angeheftete
App in der Taskleiste"): the exact same mechanism, pointed at a source
checkout and the interpreter the developer normally runs it with (venv,
pyenv or system python) instead of the bootstrapper's hidden per-user
install, with its own entry name so both can coexist on one machine:

    python -m bootstrap.desktop_integration --dev

Icon: assets/icon.{png,ico,icns} in the app source (see
tools/build_icon.py) - default_icon_path() picks the right one per
platform, and every create_* function falls back to it when no explicit
icon_path is given. Linux entries additionally carry StartupWMClass, which
is what lets the desktop match the RUNNING window (Qt's WM_CLASS /
Wayland app_id, set via QApplication.setApplicationName in ui/app.py) to
the pinned launcher - without it the taskbar shows a second, generic
"python" icon next to the pinned one while the app is open.
"""
from __future__ import annotations

import argparse
import os
import platform
import stat
import subprocess
import sys
from pathlib import Path

APP_DISPLAY_NAME = "PDF-Translator"
APP_ENTRY_SLUG = "pdf-translator"
DEV_DISPLAY_NAME = "PDF-Translator (dev)"
DEV_ENTRY_SLUG = "pdf-translator-dev"
# Must equal QApplication.applicationName() in ui/app.py::main() - Qt derives
# the X11 WM_CLASS class name and the Wayland app_id from it.
APP_WM_CLASS = "PDF-Translator"
_WINDOWS_SHORTCUT_TIMEOUT_SECONDS = 30

_ICON_FILE_BY_PLATFORM = {
    "Windows": "icon.ico",
    "Darwin": "icon.icns",
    "Linux": "icon.png",
}


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


def default_icon_path(app_source_dir: Path, system: str | None = None) -> Path | None:
    """assets/icon.<ext> inside the app source for this platform, or None if
    the file is missing (older app-source release without assets/)."""
    system = system if system is not None else platform.system()
    filename = _ICON_FILE_BY_PLATFORM.get(system)
    if filename is None:
        return None
    candidate = app_source_dir / "assets" / filename
    return candidate if candidate.is_file() else None


def _resolve_icon(app_source_dir: Path, icon_path: Path | None, system: str) -> Path | None:
    return icon_path if icon_path is not None else default_icon_path(app_source_dir, system)


# --- Linux -----------------------------------------------------------------


def _linux_desktop_entry_content(
    app_source_dir: Path,
    venv_python: Path,
    icon_path: Path | None,
    display_name: str = APP_DISPLAY_NAME,
) -> str:
    icon_line = f"Icon={icon_path}" if icon_path else f"Icon={APP_ENTRY_SLUG}"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={display_name}\n"
        "Comment=Translate documents while keeping their formatting\n"
        f'Exec="{venv_python}" -m ui.app\n'
        f"Path={app_source_dir}\n"
        f"{icon_line}\n"
        f"StartupWMClass={APP_WM_CLASS}\n"
        "Categories=Office;\n"
        "Terminal=false\n"
    )


def create_linux_desktop_entry(
    app_source_dir: Path,
    venv_python: Path,
    icon_path: Path | None = None,
    *,
    display_name: str = APP_DISPLAY_NAME,
    entry_slug: str = APP_ENTRY_SLUG,
) -> Path:
    icon_path = _resolve_icon(app_source_dir, icon_path, "Linux")
    target_dir = linux_applications_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    entry_path = target_dir / f"{entry_slug}.desktop"
    entry_path.write_text(_linux_desktop_entry_content(app_source_dir, venv_python, icon_path, display_name))
    # Desktop files must be executable for some launchers to trust them.
    entry_path.chmod(entry_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return entry_path


# --- Windows ---------------------------------------------------------------


def _windows_shortcut_script(
    shortcut_path: Path,
    venv_python: Path,
    app_source_dir: Path,
    icon_path: Path | None,
    display_name: str = APP_DISPLAY_NAME,
) -> str:
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
        f'$Shortcut.Description = "{display_name}"\n'
        "$Shortcut.Save()\n"
    )


def create_windows_shortcut(
    app_source_dir: Path,
    venv_python: Path,
    icon_path: Path | None = None,
    *,
    display_name: str = APP_DISPLAY_NAME,
) -> Path:
    icon_path = _resolve_icon(app_source_dir, icon_path, "Windows")
    target_dir = windows_start_menu_programs_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = target_dir / f"{display_name}.lnk"
    script = _windows_shortcut_script(shortcut_path, venv_python, app_source_dir, icon_path, display_name)
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


# --- macOS -----------------------------------------------------------------


def _macos_launcher_script(venv_python: Path, app_source_dir: Path) -> str:
    return (
        "#!/bin/sh\n"
        f'cd "{app_source_dir}"\n'
        f'exec "{venv_python}" -m ui.app\n'
    )


def _macos_info_plist_content(bundle_name: str, icon_file: str | None = None) -> str:
    icon_entry = (
        f"    <key>CFBundleIconFile</key>\n    <string>{icon_file}</string>\n" if icon_file else ""
    )
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
        f"{icon_entry}"
        "    <key>CFBundleShortVersionString</key>\n"
        "    <string>1.0</string>\n"
        "    <key>LSMinimumSystemVersion</key>\n"
        "    <string>10.13</string>\n"
        "</dict>\n"
        "</plist>\n"
    )


def create_macos_app_bundle(
    app_source_dir: Path,
    venv_python: Path,
    icon_path: Path | None = None,
    *,
    display_name: str = APP_DISPLAY_NAME,
) -> Path:
    icon_path = _resolve_icon(app_source_dir, icon_path, "Darwin")
    bundle_path = macos_applications_dir() / f"{display_name}.app"
    macos_dir = bundle_path / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = macos_dir / display_name
    launcher_path.write_text(_macos_launcher_script(venv_python, app_source_dir))
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    icon_file: str | None = None
    if icon_path is not None and icon_path.is_file():
        resources_dir = bundle_path / "Contents" / "Resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        (resources_dir / icon_path.name).write_bytes(icon_path.read_bytes())
        icon_file = icon_path.name

    info_plist_path = bundle_path / "Contents" / "Info.plist"
    info_plist_path.write_text(_macos_info_plist_content(display_name, icon_file))

    return bundle_path


# --- dispatch --------------------------------------------------------------


def create_desktop_entry(
    app_source_dir: Path,
    venv_python: Path,
    icon_path: Path | None = None,
    *,
    dev: bool = False,
) -> Path:
    """Dispatches to the platform-appropriate launcher-entry creator.

    dev=True writes the separate developer entry ("PDF-Translator (dev)" /
    pdf-translator-dev.desktop) so it never overwrites a bootstrapper-made
    install on the same machine.
    """
    display_name = DEV_DISPLAY_NAME if dev else APP_DISPLAY_NAME
    system = platform.system()
    if system == "Windows":
        return create_windows_shortcut(app_source_dir, venv_python, icon_path, display_name=display_name)
    if system == "Darwin":
        return create_macos_app_bundle(app_source_dir, venv_python, icon_path, display_name=display_name)
    if system == "Linux":
        return create_linux_desktop_entry(
            app_source_dir,
            venv_python,
            icon_path,
            display_name=display_name,
            entry_slug=DEV_ENTRY_SLUG if dev else APP_ENTRY_SLUG,
        )
    raise DesktopIntegrationError(f"Unsupported platform: {system!r}")


# --- developer CLI ---------------------------------------------------------


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _can_import_app_deps(python: Path) -> bool:
    """True if `python -m ui.app` would at least get past its imports on
    this interpreter (PySide6 is the one heavy, easy-to-miss dependency)."""
    try:
        result = subprocess.run(
            [str(python), "-c", "import PySide6"],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def resolve_dev_python(python_override: str | None = None) -> Path:
    """Interpreter the developer entry should launch: --python if given,
    otherwise the interpreter running this command - i.e. whatever
    `python` resolves to in the shell you normally start the app from
    (an activated venv, a pyenv version, a system python: all fine, as
    long as the app's dependencies are installed there)."""
    python = Path(python_override).expanduser().resolve() if python_override else Path(sys.executable).resolve()
    if not python.is_file():
        raise DesktopIntegrationError(f"Python interpreter not found: {python}")
    if not _can_import_app_deps(python):
        print(
            f"Warning: {python} cannot import PySide6 - the entry will not start the app "
            "until the requirements are installed for this interpreter, or pass "
            "--python <path> to one that has them.",
            file=sys.stderr,
        )
    return python


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bootstrap.desktop_integration",
        description="Create an application-menu entry for a PDF-Translator source checkout.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="write the developer entry (separate name, points at this checkout and its venv)",
    )
    parser.add_argument("--python", help="interpreter to launch (default: the one running this command)")
    parser.add_argument("--icon", help="icon file to use (default: assets/icon.<ext> of this checkout)")
    args = parser.parse_args(argv)

    if not args.dev:
        parser.error("only --dev is supported from the command line; the installer path runs via bootstrap/installer.py")

    try:
        python = resolve_dev_python(args.python)
        icon = Path(args.icon).expanduser().resolve() if args.icon else None
        entry = create_desktop_entry(repo_root(), python, icon, dev=True)
    except DesktopIntegrationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Created {entry} (launches {python})")
    print("Open your application menu, find the entry and pin it to the taskbar/dock from there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
