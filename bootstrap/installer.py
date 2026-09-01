"""Orchestrates Stage 2: venv creation, dependency installation, app-source
download, and the desktop launcher entry.

Execution order is source -> venv -> deps -> shortcut: the app source has to
be on disk before its requirements*.txt files can be read, the venv has to
exist before anything can be installed into it, and the launcher entry is
only meaningful once everything it points at (venv_python, app_source_dir)
is in place.

Dependencies come exclusively from PyPI via the project's own
requirements*.txt files (see module docstring of bootstrap/__init__.py and
the "Bestätigt" section of the 01.09.2026 project doc: this was already the
case before the bootstrapper existed - `pip install -r requirements.txt`
here is the same command a developer runs by hand, just driven from the
GUI). requirements-gpu.txt (documented in Backlog.md 18.08.2026, pointing
pip at pytorch.org's own CUDA wheel index) is optional and only installed
for InstallMode.LOCAL, and only if the downloaded app source actually
contains it - it does not exist in this sandbox's requirements-ocr.txt yet.
"""
from __future__ import annotations

import subprocess
import venv as venv_module
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from bootstrap import desktop_integration, paths, release_source

_PIP_INSTALL_TIMEOUT_SECONDS = 60 * 30  # large ML wheels (torch, etc.) are slow to fetch


class InstallMode(str, Enum):
    ONLINE = "online"
    LOCAL = "local"


class InstallStep(str, Enum):
    """Matches the "bootstrap.install_step_*" i18n key suffixes."""

    SOURCE = "source"
    VENV = "venv"
    DEPS = "deps"
    SHORTCUT = "shortcut"


class InstallError(RuntimeError):
    """Raised when any part of Stage 2 installation fails."""


@dataclass(frozen=True)
class InstallProgress:
    step: InstallStep
    detail: str = ""


ProgressCallback = Callable[[InstallProgress], None]


def _report(progress_cb: Optional[ProgressCallback], step: InstallStep, detail: str = "") -> None:
    if progress_cb is not None:
        progress_cb(InstallProgress(step=step, detail=detail))


def requirements_files_for_mode(mode: InstallMode, app_source_dir: Path) -> list[Path]:
    """requirements*.txt files to install, in order, for the chosen mode.

    Missing optional files (requirements-ocr.txt, requirements-gpu.txt) are
    silently skipped rather than raising - both are optional extras (see
    their own header comments in this repo), and a bootstrapper built
    against an older app-source release may simply not have them yet.
    """
    candidates = [app_source_dir / "requirements.txt", app_source_dir / "requirements-ocr.txt"]
    if mode is InstallMode.LOCAL:
        candidates.append(app_source_dir / "requirements-gpu.txt")
    return [path for path in candidates if path.is_file()]


def create_venv(venv_dir: Path) -> None:
    try:
        venv_module.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
    except Exception as exc:  # venv/ensurepip can raise several error types
        raise InstallError(f"Could not create the virtual environment: {exc}") from exc


def pip_install(venv_python: Path, requirements_file: Path) -> None:
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=_PIP_INSTALL_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise InstallError(
            f"Installing {requirements_file.name} failed: {exc.stderr.strip() if exc.stderr else exc}"
        ) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallError(f"Installing {requirements_file.name} failed: {exc}") from exc


def run_install(
    venv_dir: Path,
    app_source_dir: Path,
    mode: InstallMode,
    dev_source_override: str | None = None,
    progress_cb: Optional[ProgressCallback] = None,
) -> Path:
    """Runs the full Stage 2 sequence and returns the venv's python path."""
    _report(progress_cb, InstallStep.SOURCE)
    try:
        release_source.download_app_source(app_source_dir, dev_source_override=dev_source_override)
    except release_source.ReleaseSourceError as exc:
        raise InstallError(str(exc)) from exc

    _report(progress_cb, InstallStep.VENV)
    create_venv(venv_dir)
    venv_python = paths.venv_python(venv_dir)

    for requirements_file in requirements_files_for_mode(mode, app_source_dir):
        _report(progress_cb, InstallStep.DEPS, detail=requirements_file.name)
        pip_install(venv_python, requirements_file)

    _report(progress_cb, InstallStep.SHORTCUT)
    try:
        desktop_integration.create_desktop_entry(app_source_dir, venv_python)
    except desktop_integration.DesktopIntegrationError as exc:
        raise InstallError(str(exc)) from exc

    return venv_python
