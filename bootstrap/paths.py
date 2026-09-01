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


def is_frozen() -> bool:
    """True when running from a PyInstaller-built executable rather than
    from source - relevant for release_source.py's local dev-mode fallback,
    which should only ever activate for developers running from source.
    """
    return getattr(sys, "frozen", False)
