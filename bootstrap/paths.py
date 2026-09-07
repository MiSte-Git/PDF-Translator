"""Per-user install locations for the bootstrapper's Stage 2 payload.

Stage 1 (this package) never needs admin/root rights, which is the actual
reason a classic system-wide installer (.deb/.rpm/.msi) is unnecessary -
see the "Desktop-Integration" section of the 01.09.2026 project doc. Stage 2
(the venv + downloaded app source) therefore always lives under a per-user
data directory, one per platform's convention.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

# Matches pipeline/credentials.py::_KEYRING_SERVICE - not imported directly
# from there to keep this module dependency-free (no risk of ever pulling
# in pipeline/'s heavier siblings via a package-level import), but the two
# must stay in sync since both name the same on-disk/keyring identity.
APP_SLUG = "pdf-translator"


def install_root() -> Path:
    """Per-user directory holding the venv, the downloaded app source, and
    the language marker file. Created on first use by ensure_install_root().
    """
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / "PDF-Translator"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_SLUG
    # Linux and other POSIX systems: XDG Base Directory spec.
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / APP_SLUG


def ensure_install_root() -> Path:
    """install_root(), creating it (and parents) if it does not exist yet."""
    root = install_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def venv_dir() -> Path:
    """Directory of the per-user virtual environment created by the
    installer (bootstrap/installer.py). Kept separate from app_source_dir()
    so re-downloading the app source (an update) never has to touch, and
    therefore never risks breaking, the already-working environment.
    """
    return install_root() / "venv"


def venv_python(venv: Path | None = None) -> Path:
    """Path to the venv's own python executable, cross-platform."""
    venv = venv if venv is not None else venv_dir()
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def venv_pythonw(venv: Path | None = None) -> Path:
    """Path to the venv's *windowed* interpreter (Windows only - pythonw.exe,
    no console window) for launching the GUI app itself.

    06.09.2026: bootstrap/controller.py::launch_app() used venv_python()
    (python.exe, the console interpreter) to start the finished PySide6
    app. Since bootstrap.exe itself is a --windowed build with no console
    of its own, spawning python.exe as its child makes Windows allocate a
    brand new console window for it - the "kurz kommt wieder eine Shell
    hoch" a real user saw right after clicking "Jetzt starten". pythonw.exe
    is the same interpreter built without a console subsystem, so no
    window is created at all, on success or failure.

    On any platform other than Windows this is identical to venv_python()
    - pythonw.exe/console-vs-windowed is a Windows-only distinction, every
    other OS has one interpreter binary.
    """
    venv = venv if venv is not None else venv_dir()
    if platform.system() == "Windows":
        candidate = venv / "Scripts" / "pythonw.exe"
        if candidate.is_file():
            return candidate
        # Extremely defensive: every CPython Windows install ships
        # pythonw.exe next to python.exe, but if some future/stripped
        # runtime doesn't, falling back to the console interpreter is
        # still a working app (just with the console-flash back) rather
        # than a launch that can never succeed.
        return venv_python(venv)
    return venv_python(venv)


def app_source_dir() -> Path:
    """Directory the downloaded/extracted app source (pipeline/, ui/,
    requirements*.txt, ...) is installed into - see bootstrap/release_source.py.
    """
    return install_root() / "app"


def language_marker_file() -> Path:
    """JSON file the bootstrapper writes with the language chosen during
    setup, so the real app's first run can pre-select it (see project doc,
    decision "Ja, übernehmen"). A plain JSON file rather than writing into
    QSettings' native storage directly: QSettings uses different physical
    formats per platform (INI file vs. Windows Registry), which this
    dependency-free package (see module docstring above; no PySide6 import
    allowed here) cannot manipulate reliably or portably. ui/app.py reads
    this file itself, once, before constructing its own QSettings-backed
    LanguageManager.
    """
    return install_root() / "language.json"


def gpu_check_marker_file() -> Path:
    """JSON file persisting the last GPU capability check result - see
    bootstrap/gpu_check.py::save_gpu_check_result()/read_gpu_check_marker().

    01.09.2026 (Michael: "Ist es möglich den HW Check beim Installieren zu
    speichern und in einem Hilfe Menü in der App eine Möglichkeit den HW
    Test anzeigen zu lassen und auch noch mal zu wiederholen."): written
    once during a LOCAL-mode install's Stage 1 GPU-check step
    (bootstrap/controller.py::check_gpu()), and again any time the user
    re-runs the check from the real app's "Hilfe" -> Hardware-Test dialog
    (ui/app.py::HardwareCheckDialog). Same plain-JSON-file reasoning as
    language_marker_file() above (no direct QSettings access from this
    Qt-free package) - and the same file whether the check that produced it
    ran from inside the bootstrapper or from inside the already-installed
    app, so the dialog shows an install-time result until the user
    explicitly re-checks, not two separate histories.
    """
    return install_root() / "gpu_check.json"


def is_frozen() -> bool:
    """True when running from a PyInstaller-built executable rather than
    from source - relevant for release_source.py's local dev-mode fallback,
    which should only ever activate for developers running from source.
    """
    return getattr(sys, "frozen", False)


def bootstrap_icon_path() -> Path | None:
    """Path to the bootstrapper's own window icon (assets/icon.png),
    resolved for both a frozen PyInstaller build and a dev run from source.

    07.09.2026 (Michael: "lass uns unser Icon einbauen"): Stage 1's tkinter
    window had no icon set at all (default Tk feather icon) - unrelated to
    the already-working app/taskbar icon (ui/app.py's APP_ICON_PATH,
    desktop_integration.py's per-platform .desktop/.lnk/.app entries),
    which only exist once Stage 2's app source is on disk - something
    Stage 1's own window can't wait for, since it is visible from the very
    first screen. A frozen build therefore needs its own copy of
    assets/icon.png bundled directly into the onefile executable (see the
    "--add-data assets/icon.png...assets" step in
    .github/workflows/build-bootstrap.yml, same mechanism as
    bootstrap/bundled_python.py's python_runtime bundle), extracted by
    PyInstaller under sys._MEIPASS at runtime. Returns None if the file
    genuinely cannot be found (e.g. a future build forgets the --add-data
    flag) rather than raising - a missing window icon is cosmetic, not
    worth crashing the installer over.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / "assets" / "icon.png"
    else:
        # Dev run from source: repo_root/assets/icon.png - same layout
        # ui/app.py's APP_ICON_PATH already relies on.
        candidate = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    return candidate if candidate.is_file() else None
