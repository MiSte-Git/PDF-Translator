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
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from bootstrap import bundled_python, desktop_integration, gpu_check, paths, release_source
from bootstrap.subprocess_utils import no_window_kwargs

_PIP_INSTALL_TIMEOUT_SECONDS = 60 * 30  # large ML wheels (torch, etc.) are slow to fetch
_VENV_CREATE_TIMEOUT_SECONDS = 60 * 5  # venv + ensurepip is normally seconds, not minutes


class InstallMode(str, Enum):
    ONLINE = "online"
    LOCAL = "local"


class InstallStep(str, Enum):
    """Matches the "bootstrap.install_step_*" i18n key suffixes."""

    SOURCE = "source"
    VENV = "venv"
    DEPS = "deps"
    SHORTCUT = "shortcut"


# requirements files that must be installed with `pip install --no-deps`
# (03.09.2026): simple-lama-inpainting's own pins (pillow<10, numpy<2) would
# otherwise force pip into a doomed source build of an ancient Pillow on
# Python 3.13+ - see the header comments of requirements-gpu.txt.
NO_DEPS_REQUIREMENTS = frozenset({"requirements-gpu-nodeps.txt"})


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
        # Must come AFTER requirements-gpu.txt: installed with --no-deps,
        # so torch etc. have to be there already (NO_DEPS_REQUIREMENTS).
        candidates.append(app_source_dir / "requirements-gpu-nodeps.txt")
    return [path for path in candidates if path.is_file()]


def _base_python() -> Path:
    """Interpreter used to create the Stage-2 venv.

    04.09.2026 (first real Windows test run): a frozen build's own
    sys.executable is the bootstrapper .exe, not a real interpreter - see
    bootstrap/bundled_python.py's module docstring for the full story. Use
    the bundled CPython there. Running from source (dev/tests),
    sys.executable already IS a real interpreter, same as before this fix.
    """
    if paths.is_frozen():
        python = bundled_python.bundled_python_executable()
        if python is None:
            raise InstallError(
                "This build is missing its bundled Python runtime "
                "(python_runtime) - it was not built correctly."
            )
        return python
    return Path(sys.executable)


def create_venv(venv_dir: Path, base_python: Path | None = None) -> None:
    """Creates the Stage-2 venv by running `<python> -m venv <venv_dir>` in
    a subprocess, rather than venv.EnvBuilder() in-process (as this used to
    do): EnvBuilder derives its base interpreter from the running process,
    which is wrong for a frozen bootstrapper (see _base_python()). Running
    the target interpreter's own venv module as a subprocess sidesteps that
    entirely - `-m venv` always builds a venv based on itself, exactly like
    running it from a normal command line would. `-m venv` installs pip by
    default (same as EnvBuilder(with_pip=True) before it), so behaviour for
    callers is unchanged.
    """
    python = base_python if base_python is not None else _base_python()
    try:
        subprocess.run(
            [str(python), "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
            timeout=_VENV_CREATE_TIMEOUT_SECONDS,
            check=True,
            **no_window_kwargs(),
        )
    except subprocess.CalledProcessError as exc:
        raise InstallError(
            f"Could not create the virtual environment: {exc.stderr.strip() if exc.stderr else exc}"
        ) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallError(f"Could not create the virtual environment: {exc}") from exc


def pip_install(venv_python: Path, requirements_file: Path, no_deps: bool = False) -> None:
    command = [str(venv_python), "-m", "pip", "install"]
    if no_deps:
        command.append("--no-deps")
    command += ["-r", str(requirements_file)]
    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_PIP_INSTALL_TIMEOUT_SECONDS,
            check=True,
            **no_window_kwargs(),
        )
    except subprocess.CalledProcessError as exc:
        raise InstallError(
            f"Installing {requirements_file.name} failed: {exc.stderr.strip() if exc.stderr else exc}"
        ) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallError(f"Installing {requirements_file.name} failed: {exc}") from exc


_TORCH_PACKAGES = ["torch", "torchvision"]


def torch_install_command(venv_python: Path, cuda_version: str | None) -> list[str]:
    """pip command installing torch/torchvision from the wheel index that
    matches the driver's CUDA generation (see gpu_check.torch_index_url());
    plain PyPI when no specific index applies."""
    command = [str(venv_python), "-m", "pip", "install", *_TORCH_PACKAGES]
    index_url = gpu_check.torch_index_url(cuda_version)
    if index_url:
        command += ["--index-url", index_url]
    return command


def install_torch(venv_python: Path, cuda_version: str | None) -> None:
    """LOCAL mode only. Runs BEFORE requirements-gpu.txt so that its bare
    `torch`/`torchvision` lines are already satisfied and pip does not
    replace the driver-matched wheels with PyPI's newest-CUDA default
    (03.09.2026 - see gpu_check.TORCH_INDEX_BY_CUDA_MAJOR)."""
    try:
        subprocess.run(
            torch_install_command(venv_python, cuda_version),
            capture_output=True,
            text=True,
            timeout=_PIP_INSTALL_TIMEOUT_SECONDS,
            check=True,
            **no_window_kwargs(),
        )
    except subprocess.CalledProcessError as exc:
        raise InstallError(f"Installing torch failed: {exc.stderr.strip() if exc.stderr else exc}") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallError(f"Installing torch failed: {exc}") from exc


def run_install(
    venv_dir: Path,
    app_source_dir: Path,
    mode: InstallMode,
    dev_source_override: str | None = None,
    progress_cb: Optional[ProgressCallback] = None,
    cuda_version: str | None = None,
) -> Path:
    """Runs the full Stage 2 sequence and returns the venv's python path.

    `cuda_version` (LOCAL mode, from the GPU-check step's GpuInfo) selects
    the torch wheel index - see install_torch().
    """
    _report(progress_cb, InstallStep.SOURCE)
    try:
        release_source.download_app_source(app_source_dir, dev_source_override=dev_source_override)
    except release_source.ReleaseSourceError as exc:
        raise InstallError(str(exc)) from exc

    _report(progress_cb, InstallStep.VENV)
    create_venv(venv_dir)
    venv_python = paths.venv_python(venv_dir)

    if mode is InstallMode.LOCAL:
        index_url = gpu_check.torch_index_url(cuda_version)
        _report(progress_cb, InstallStep.DEPS, detail=f"torch ({index_url.rsplit('/', 1)[-1] if index_url else 'PyPI'})")
        install_torch(venv_python, cuda_version)

    for requirements_file in requirements_files_for_mode(mode, app_source_dir):
        _report(progress_cb, InstallStep.DEPS, detail=requirements_file.name)
        pip_install(venv_python, requirements_file, no_deps=requirements_file.name in NO_DEPS_REQUIREMENTS)

    _report(progress_cb, InstallStep.SHORTCUT)
    try:
        # Icon is resolved inside create_desktop_entry() from the downloaded
        # app source's assets/ (03.09.2026) - nothing to pass explicitly.
        desktop_integration.create_desktop_entry(app_source_dir, venv_python)
    except desktop_integration.DesktopIntegrationError as exc:
        raise InstallError(str(exc)) from exc

    return venv_python
