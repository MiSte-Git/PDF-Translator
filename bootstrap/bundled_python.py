"""Locates the CPython runtime bundled into the frozen bootstrapper
executable (see .github/workflows/build-bootstrap.yml's "Download bundled
Python runtime" step and the --add-data python_runtime flag on the
PyInstaller build step).

Why this exists (04.09.2026 - first real Windows test run, see project doc
"windows-testlauf-04-09-2026.md"): a PyInstaller --onefile build's own
sys.executable points at the bootstrapper .exe itself, not at a real Python
interpreter. bootstrap/installer.py::create_venv() used to build the venv
via venv.EnvBuilder() running inside the frozen process, which looks for
python.exe/pythonw.exe next to sys.executable to copy into the new venv -
on the test machine (no system Python installed, which is the *expected*
case for this project's "no shell contact, no prerequisites" target
audience, not an edge case) this failed with
"[WinError 2] Das System kann die angegebene Datei nicht finden".

Fix: bundle a redistributable CPython build (python-build-standalone -
https://github.com/astral-sh/python-build-standalone, the same project
uv/rye use for this exact purpose) into the installer executable itself,
and always create the venv by invoking THAT interpreter's own `-m venv`
as a subprocess (bootstrap/installer.py::create_venv()) instead of
EnvBuilder() inside the frozen process. This fixes both root causes at
once: no system Python is ever required, and the frozen-exe
sys.executable trap no longer matters because the running process is
never asked to infer a base interpreter for itself.

Size (01.09.2026 project doc + 04.09.2026 follow-up, approved by Michael
"da kann man noch größer werden", budget "unter 100 MB"): a python-build-
standalone "install_only" archive is roughly 25-35 MB compressed per
platform, taking the ~11 MB unsigned installer to roughly 35-50 MB - well
within budget.
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

# Must match the --add-data destination name in
# .github/workflows/build-bootstrap.yml's PyInstaller build step.
_BUNDLE_DIR_NAME = "python_runtime"


def bundled_python_dir() -> Path | None:
    """Root of the bundled CPython install (PyInstaller onefile extracts
    --add-data content under sys._MEIPASS at runtime), or None when not
    running from a frozen build - see bootstrap.paths.is_frozen()."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    return Path(meipass) / _BUNDLE_DIR_NAME


def bundled_python_executable() -> Path | None:
    """Path to the bundled python executable, or None if this is not a
    frozen build or the bundle is missing/incomplete (e.g. a dev build of
    the bootstrapper .exe that skipped the "Download bundled Python
    runtime" CI step - see bootstrap/installer.py::_base_python(), which
    turns None into a clear InstallError rather than a confusing crash).

    python-build-standalone's "install_only" archives use the platform's
    normal install layout: python.exe directly under the install root on
    Windows, bin/python3.<minor> (usually also symlinked as bin/python3)
    on Linux/macOS - see docs/distributions.rst in that project.
    """
    root = bundled_python_dir()
    if root is None or not root.is_dir():
        return None

    if platform.system() == "Windows":
        candidate = root / "python.exe"
        return candidate if candidate.is_file() else None

    bin_dir = root / "bin"
    if not bin_dir.is_dir():
        return None
    plain = bin_dir / "python3"
    if plain.is_file():
        return plain
    # Fall back to the versioned name (python3.13, ...) in case a future
    # python-build-standalone release ever ships without the python3
    # convenience symlink.
    versioned = sorted(bin_dir.glob("python3.*"))
    return versioned[0] if versioned else None
