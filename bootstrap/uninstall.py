"""Uninstall support: removes everything the installer created for the
current user (venv, downloaded app source, python_runtime copy, the
Start Menu/dock/launcher entry, language/GPU marker files, launch.log)
and, on Windows, the Add/Remove Programs registry entry that points here.

There is no separate uninstaller binary. bootstrap/installer.py::
register_windows_uninstall_entry() copies this *same* bootstrapper
executable into install_root() as Uninstall.exe at the end of a
successful Windows install, and registers ITS OWN path with
"--uninstall" appended as the registry UninstallString - the standard,
decades-old NSIS/Inno Setup trick of an installer doubling as its own
uninstaller via a command-line flag, rather than shipping and
maintaining a second PyInstaller build/CI matrix (see
.github/workflows/build-bootstrap.yml) just for this.
bootstrap/app.py::main() checks sys.argv for exactly that flag and
dispatches to run_uninstall_ui() below instead of opening the wizard.

07.09.2026 (Michael: "Haben wir auch an eine Deinstallation gedacht?
Oder geht das automatisch über Add/Remove Programs?") - it did not
happen automatically before this: a per-user install with no MSI/NSIS
package (see bootstrap/desktop_integration.py's module docstring for why
there is no .msi) has nothing that would make Windows show it in Add/
Remove Programs on its own. This module plus
register_windows_uninstall_entry() is what makes that listing appear.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

from bootstrap import desktop_integration, paths
from bootstrap.subprocess_utils import no_window_kwargs

REGISTRY_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Translator"
UNINSTALLER_EXE_NAME = "Uninstall.exe"
_SELF_DELETE_DELAY_SECONDS = 2


def remove_launcher_entry() -> None:
    """Best-effort removal of the Start Menu shortcut / .desktop file /
    .app bundle created by desktop_integration.create_desktop_entry().
    Never raises - a missing or already-removed entry (the user may have
    deleted it by hand already) is not an error worth stopping for."""
    system = platform.system()
    try:
        if system == "Windows":
            shortcut = desktop_integration.windows_start_menu_programs_dir() / f"{desktop_integration.APP_DISPLAY_NAME}.lnk"
            shortcut.unlink(missing_ok=True)
        elif system == "Darwin":
            bundle = desktop_integration.macos_applications_dir() / f"{desktop_integration.APP_DISPLAY_NAME}.app"
            if bundle.is_dir():
                shutil.rmtree(bundle, ignore_errors=True)
        elif system == "Linux":
            entry = desktop_integration.linux_applications_dir() / f"{desktop_integration.APP_ENTRY_SLUG}.desktop"
            entry.unlink(missing_ok=True)
    except OSError:
        pass


def remove_registry_entry() -> None:
    """Windows only - deletes the Add/Remove Programs entry written by
    bootstrap/installer.py::register_windows_uninstall_entry(). A no-op,
    never raising, on any other platform or if the key is already gone
    (winreg.DeleteKey raises FileNotFoundError, a subclass of OSError, in
    that case)."""
    if sys.platform != "win32":
        return
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY_PATH)
    except OSError:
        pass


def remove_install_root(keep: Path | None = None) -> None:
    """Deletes everything under install_root() (venv, app/, the copied
    python_runtime, marker files, launch.log) except `keep` (the running
    Uninstall.exe itself - see _schedule_self_delete(), which removes it
    separately after this process exits). Silently does nothing if
    install_root() does not exist (already removed, or never created).
    """
    root = paths.install_root()
    if not root.is_dir():
        return
    for child in root.iterdir():
        if keep is not None and child == keep:
            continue
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        except OSError:
            pass


def _schedule_self_delete(exe_path: Path) -> None:
    """Removes exe_path after this process exits.

    A running Windows .exe cannot always delete itself directly - Windows
    may keep the image file locked for the lifetime of the process. The
    standard workaround self-extracting/self-uninstalling Windows tools
    have used for decades is to hand the delete off to a short detached
    helper command that waits for this process to exit first; a plain
    `timeout` for a couple of seconds is simpler and more portable across
    Windows versions than trying to wait on this specific PID. Any
    failure here (the helper itself failing to start) is silently
    ignored - by this point everything else has already been removed,
    and a single leftover .exe in an otherwise-empty install_root() is a
    minor cosmetic issue, not a broken uninstall.
    """
    if sys.platform != "win32":
        try:
            exe_path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    try:
        subprocess.Popen(
            [
                "cmd",
                "/c",
                f'timeout /t {_SELF_DELETE_DELAY_SECONDS} /nobreak >nul & del /f /q "{exe_path}"',
            ],
            close_fds=True,
            **no_window_kwargs(),
        )
    except OSError:
        pass


def perform_uninstall() -> None:
    """Runs the full removal sequence. Order matters: the launcher entry
    and registry key first (so a half-finished uninstall at least stops
    the app showing up anywhere new if something later fails), the bulk
    of install_root() next, and this executable's own file last (and
    only via a detached helper on Windows - see _schedule_self_delete()).
    Never raises - every step above is already individually best-effort;
    this just sequences them.
    """
    remove_launcher_entry()
    remove_registry_entry()
    exe_path = Path(sys.executable).resolve() if paths.is_frozen() else None
    keep = exe_path if exe_path is not None and exe_path.parent == paths.install_root() else None
    remove_install_root(keep=keep)
    if keep is not None:
        _schedule_self_delete(keep)


def run_uninstall_ui() -> None:
    """Entry point for `<bootstrapper exe> --uninstall` (see
    bootstrap/app.py::main()) - a tiny confirm/result dialog, not the
    full wizard. Deliberately not built on BootstrapController: none of
    its install-time state (mode, GPU info, ...) applies to uninstalling,
    it would just be dead weight here. Language comes from
    bootstrap/system_lang.py's normal de/en-or-fallback-English
    detection (the same one BootstrapController itself uses for the
    wizard) - unlike bootstrap/app.py::_detect_wizard_language() for the
    elevated-admin warning, there is no reason to widen this one to all
    9 locales, since by the time someone is uninstalling they have
    already used - and very likely already set - the app's own language.
    """
    import tkinter as tk
    from tkinter import messagebox

    from bootstrap import system_lang
    from ui.i18n_data import CATALOGUES, DE

    catalogue = CATALOGUES.get(system_lang.detect_system_language(), DE)

    def text(key: str) -> str:
        return catalogue.get(key, DE.get(key, key))

    root = tk.Tk()
    root.withdraw()
    confirmed = messagebox.askyesno(text("bootstrap.uninstall_title"), text("bootstrap.uninstall_confirm"))
    if confirmed:
        perform_uninstall()
        messagebox.showinfo(text("bootstrap.uninstall_title"), text("bootstrap.uninstall_done"))
    root.destroy()
