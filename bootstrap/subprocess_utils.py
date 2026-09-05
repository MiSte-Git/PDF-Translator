"""Shared helper so every subprocess this package spawns (venv creation,
pip installs, the Windows Start Menu shortcut's powershell call, the
PySide6 import probe, nvidia-smi) stays invisible - added 04.09.2026 after
a real installer run showed several empty python.exe console windows and
a flashing PowerShell window during a normal install.

bootstrap/app.py runs as a PyInstaller --windowed build, so it has no
console of its own; without this, each subprocess.run() call still makes
Windows allocate a brand new console window for the child process (the
default CreateProcess behaviour, independent of whether the *parent* has
one), which briefly flashes on screen even though these calls only care
about return code / captured stdout-stderr, never an interactive window.
subprocess.CREATE_NO_WINDOW tells CreateProcess not to allocate one at
all. Windows-only flag - everywhere else this is simply an empty dict, so
call sites can pass `**no_window_kwargs()` unconditionally.
"""
from __future__ import annotations

import subprocess
import sys


def no_window_kwargs() -> dict:
    if sys.platform != "win32":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}
