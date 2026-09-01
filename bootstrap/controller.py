"""Tkinter-independent state and orchestration for the bootstrapper wizard.

Split out of bootstrap/app.py so all of this logic - language selection,
the GPU check, driving bootstrap/installer.py, the credentials step,
launching the finished app - can be unit-tested without an actual display.
tkinter/Tk needs one, and neither this project's CI runners nor every dev
machine reliably has one available; bootstrap/app.py is a thin widget layer
built on top of this class and is not itself unit-tested for that reason
(covered instead by the per-OS PyInstaller build in CI - see
.github/workflows/build-bootstrap.yml - which at least proves it imports
and freezes cleanly on all three platforms).

Text lookup here uses ui/i18n_data.py's CATALOGUES/DE directly (statically
bundled into the bootstrapper executable, unlike ui/settings.py in
credentials_step.py which is deliberately loaded at runtime from the
downloaded app source - see that module's docstring for why the two differ):
the wizard's own screens (language choice, mode choice, ...) must render
before anything has been downloaded yet, so their strings cannot come from
anywhere but a copy shipped with the bootstrapper itself.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from ui.i18n_data import CATALOGUES, DE

from bootstrap import credentials_step, gpu_check, installer, paths, system_lang


class BootstrapController:
    def __init__(self, venv_dir: Path | None = None, app_source_dir: Path | None = None) -> None:
        self.venv_dir = venv_dir if venv_dir is not None else paths.venv_dir()
        self.app_source_dir = app_source_dir if app_source_dir is not None else paths.app_source_dir()
        self.language: str = system_lang.detect_system_language()
        self.mode: Optional[installer.InstallMode] = None
        self.gpu_info: Optional[gpu_check.GpuInfo] = None
        self.install_error: Optional[str] = None
        self.venv_python: Optional[Path] = None

    # --- language --------------------------------------------------------

    def set_language(self, language: str) -> None:
        if language in CATALOGUES:
            self.language = language

    def text(self, key: str, **values: object) -> str:
        catalogue = CATALOGUES.get(self.language, DE)
        template = catalogue.get(key, DE.get(key, key))
        return template.format(**values) if values else template

    def write_language_marker(self) -> Path:
        """Writes the JSON marker file ui/app.py reads on the real app's
        first launch to pre-select this same language (project doc
        decision "Ja, übernehmen")."""
        marker = paths.language_marker_file()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"language": self.language}))
        return marker

    # --- mode / GPU --------------------------------------------------------

    def set_mode(self, mode: installer.InstallMode) -> None:
        self.mode = mode

    def check_gpu(self) -> gpu_check.GpuInfo | None:
        self.gpu_info = gpu_check.detect_nvidia_gpu()
        # 01.09.2026 (Michael: "Ist es möglich den HW Check beim
        # Installieren zu speichern...") - persists through to
        # bootstrap.paths.gpu_check_marker_file() so ui/app.py's "Hilfe" ->
        # Hardware-Test dialog can show this install-time result later.
        # save_gpu_check_result() takes the already-detected self.gpu_info
        # rather than re-probing (see that function's own docstring) - one
        # nvidia-smi call per check_gpu() call, not two.
        gpu_check.save_gpu_check_result(self.gpu_info)
        return self.gpu_info

    def gpu_meets_recommendation(self) -> bool:
        return gpu_check.meets_recommendation(self.gpu_info)

    # --- install -----------------------------------------------------------

    def run_install(
        self,
        dev_source_override: str | None = None,
        progress_cb: installer.ProgressCallback | None = None,
    ) -> Path:
        if self.mode is None:
            raise RuntimeError("set_mode() must be called before run_install()")
        self.install_error = None
        try:
            self.venv_python = installer.run_install(
                self.venv_dir,
                self.app_source_dir,
                self.mode,
                dev_source_override=dev_source_override,
                progress_cb=progress_cb,
            )
        except installer.InstallError as exc:
            self.install_error = str(exc)
            raise
        return self.venv_python

    # --- credentials ---------------------------------------------------

    def list_providers(self) -> list[str]:
        return credentials_step.list_providers(self.app_source_dir)

    def provider_status(self, provider: str) -> str:
        return credentials_step.provider_status(self.app_source_dir, provider)

    def save_provider_credential(self, provider: str, value: str) -> None:
        credentials_step.save_provider_credential(self.app_source_dir, provider, value)

    def open_signup_page(self, provider: str) -> bool:
        return credentials_step.open_signup_page(provider)

    # --- finish ----------------------------------------------------------

    def launch_app(self) -> subprocess.Popen:
        venv_python = self.venv_python if self.venv_python is not None else paths.venv_python(self.venv_dir)
        return subprocess.Popen(
            [str(venv_python), "-m", "ui.app"], cwd=str(self.app_source_dir)
        )
