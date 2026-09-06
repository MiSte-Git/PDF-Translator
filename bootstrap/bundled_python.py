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
import shutil
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


def _python_executable_in(root: Path) -> Path | None:
    """python.exe / bin/python3(.<minor>) under a python-build-standalone
    "install_only" archive's root - shared by bundled_python_executable()
    (looking inside the transient sys._MEIPASS copy) and
    ensure_stable_python_runtime() (looking inside the persistent copy),
    since both are the exact same on-disk layout."""
    if not root.is_dir():
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


def bundled_python_executable() -> Path | None:
    """Path to the bundled python executable *inside sys._MEIPASS*, or
    None if this is not a frozen build or the bundle is missing/incomplete
    (e.g. a dev build of the bootstrapper .exe that skipped the "Download
    bundled Python runtime" CI step).

    06.09.2026: do not use this to create the Stage-2 venv directly - see
    ensure_stable_python_runtime()'s docstring for why a real end-to-end
    Windows test showed the app could never start when this was used for
    that. It is still correct for anything that only needs the bundled
    interpreter for the lifetime of the current bootstrapper process
    (there is nothing like that today, but the distinction matters enough
    to keep both functions and not quietly merge them).
    """
    root = bundled_python_dir()
    if root is None:
        return None
    return _python_executable_in(root)


def ensure_stable_python_runtime(install_root: Path) -> Path | None:
    """Copies the bundled CPython runtime out of sys._MEIPASS into
    install_root/python_runtime - a location that outlives this process -
    and returns *that* copy's python executable. Use this (not
    bundled_python_executable()) for anything that must still work after
    the bootstrapper has exited, i.e. building the Stage-2 venv.

    06.09.2026 (first real end-to-end Windows test - install finished,
    but the installed app then refused to start, and so did the bundled
    "Jetzt starten" button): bootstrap/installer.py::create_venv() used to
    run `<bundled_python_executable()> -m venv <venv_dir>` directly. `-m
    venv` bakes the exact interpreter path it was invoked with into the
    new venv's own pyvenv.cfg ("home = ..."), so the venv permanently
    pointed at sys._MEIPASS/python_runtime - PyInstaller's own onefile
    extraction directory for that one run, which PyInstaller deletes the
    moment the bootstrapper process exits. Every later attempt to run the
    venv's python(w).exe - a fresh "Jetzt starten" click, a Start Menu
    shortcut, the app trying to relaunch itself - hit that venv's
    python(w).exe launcher stub, which failed with "Python venv launcher
    is sorry to say ... did not find executable at ...backslash-MEIxxxxx
    backslash python_runtime backslash pythonw.exe": the path was real
    for the few seconds the installer ran, and gone forever after.

    Always re-copies (removing any previous copy first) rather than
    reusing one that happens to already exist, so an update/reinstall
    that ships a newer bundled runtime can never end up mixing an old
    runtime copy with a freshly rebuilt venv.
    """
    source_dir = bundled_python_dir()
    if source_dir is None or not source_dir.is_dir():
        return None
    target_dir = install_root / _BUNDLE_DIR_NAME
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    return _python_executable_in(target_dir)
