"""Tests for bootstrap/installer.py."""
from __future__ import annotations

import subprocess

import pytest

from bootstrap import installer
from bootstrap.installer import InstallError, InstallMode, InstallProgress, InstallStep


def test_requirements_files_for_mode_online_skips_gpu(tmp_path):
    (tmp_path / "requirements.txt").write_text("PyMuPDF\n")
    (tmp_path / "requirements-ocr.txt").write_text("Pillow\n")
    (tmp_path / "requirements-gpu.txt").write_text("torch\n")
    result = installer.requirements_files_for_mode(InstallMode.ONLINE, tmp_path)
    names = [p.name for p in result]
    assert names == ["requirements.txt", "requirements-ocr.txt"]


def test_requirements_files_for_mode_local_includes_gpu_if_present(tmp_path):
    (tmp_path / "requirements.txt").write_text("PyMuPDF\n")
    (tmp_path / "requirements-gpu.txt").write_text("torch\n")
    result = installer.requirements_files_for_mode(InstallMode.LOCAL, tmp_path)
    names = [p.name for p in result]
    assert names == ["requirements.txt", "requirements-gpu.txt"]


def test_requirements_files_for_mode_skips_missing_optional_files(tmp_path):
    (tmp_path / "requirements.txt").write_text("PyMuPDF\n")
    result = installer.requirements_files_for_mode(InstallMode.LOCAL, tmp_path)
    assert [p.name for p in result] == ["requirements.txt"]


def test_create_venv_wraps_errors(monkeypatch, tmp_path):
    class _FailingBuilder:
        def __init__(self, *a, **k):
            pass

        def create(self, venv_dir):
            raise OSError("disk full")

    monkeypatch.setattr(installer.venv_module, "EnvBuilder", _FailingBuilder)
    with pytest.raises(InstallError):
        installer.create_venv(tmp_path / "venv")


def test_pip_install_wraps_called_process_error(monkeypatch, tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("PyMuPDF\n")

    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="boom")

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    with pytest.raises(InstallError, match="boom"):
        installer.pip_install(tmp_path / "python", req_file)


def test_pip_install_success_does_not_raise(monkeypatch, tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("PyMuPDF\n")

    class _Result:
        returncode = 0

    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: _Result())
    installer.pip_install(tmp_path / "python", req_file)  # should not raise


def test_run_install_full_sequence_reports_progress_in_order(monkeypatch, tmp_path):
    venv_dir = tmp_path / "venv"
    app_source_dir = tmp_path / "app"
    dev_source = tmp_path / "dev-source"
    dev_source.mkdir()
    (dev_source / "requirements.txt").write_text("PyMuPDF\n")

    calls: list[InstallProgress] = []

    def fake_create_venv(vdir):
        assert vdir == venv_dir
        vdir.mkdir(parents=True, exist_ok=True)

    installed_reqs = []

    def fake_pip_install(venv_python, requirements_file):
        installed_reqs.append(requirements_file.name)

    def fake_create_desktop_entry(app_dir, venv_python, icon_path=None):
        assert app_dir == app_source_dir
        return tmp_path / "shortcut"

    monkeypatch.setattr(installer, "create_venv", fake_create_venv)
    monkeypatch.setattr(installer, "pip_install", fake_pip_install)
    monkeypatch.setattr(installer.desktop_integration, "create_desktop_entry", fake_create_desktop_entry)

    result = installer.run_install(
        venv_dir,
        app_source_dir,
        InstallMode.ONLINE,
        dev_source_override=str(dev_source),
        progress_cb=calls.append,
    )

    assert result == installer.paths.venv_python(venv_dir)
    assert (app_source_dir / "requirements.txt").is_file()
    assert installed_reqs == ["requirements.txt"]
    steps = [c.step for c in calls]
    assert steps == [InstallStep.SOURCE, InstallStep.VENV, InstallStep.DEPS, InstallStep.SHORTCUT]


def test_run_install_wraps_release_source_error(monkeypatch, tmp_path):
    def fake_download(*a, **k):
        raise installer.release_source.ReleaseSourceError("no network")

    monkeypatch.setattr(installer.release_source, "download_app_source", fake_download)
    with pytest.raises(InstallError):
        installer.run_install(tmp_path / "venv", tmp_path / "app", InstallMode.ONLINE)
