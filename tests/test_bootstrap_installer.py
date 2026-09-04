"""Tests for bootstrap/installer.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def test_requirements_files_for_mode_local_puts_nodeps_file_after_gpu(tmp_path):
    (tmp_path / "requirements.txt").write_text("PyMuPDF\n")
    (tmp_path / "requirements-gpu.txt").write_text("torch\n")
    (tmp_path / "requirements-gpu-nodeps.txt").write_text("simple-lama-inpainting\n")
    names = [p.name for p in installer.requirements_files_for_mode(InstallMode.LOCAL, tmp_path)]
    assert names == ["requirements.txt", "requirements-gpu.txt", "requirements-gpu-nodeps.txt"]


def test_pip_install_adds_no_deps_flag(monkeypatch, tmp_path):
    req_file = tmp_path / "requirements-gpu-nodeps.txt"
    req_file.write_text("simple-lama-inpainting\n")
    captured = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    installer.pip_install(tmp_path / "python", req_file, no_deps=True)
    assert "--no-deps" in captured["cmd"]
    installer.pip_install(tmp_path / "python", req_file)
    assert "--no-deps" not in captured["cmd"]


def test_run_install_uses_no_deps_for_nodeps_file(monkeypatch, tmp_path):
    dev_source = tmp_path / "dev-source"
    dev_source.mkdir()
    (dev_source / "requirements.txt").write_text("PyMuPDF\n")
    (dev_source / "requirements-gpu-nodeps.txt").write_text("simple-lama-inpainting\n")
    seen = []
    monkeypatch.setattr(installer, "create_venv", lambda vdir: vdir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(installer, "install_torch", lambda *a: None)  # 03.09.2026: LOCAL installs torch first
    monkeypatch.setattr(installer, "pip_install", lambda py, req, no_deps=False: seen.append((req.name, no_deps)))
    monkeypatch.setattr(installer.desktop_integration, "create_desktop_entry", lambda *a, **k: tmp_path / "s")
    installer.run_install(tmp_path / "venv", tmp_path / "app", InstallMode.LOCAL, dev_source_override=str(dev_source))
    assert seen == [("requirements.txt", False), ("requirements-gpu-nodeps.txt", True)]


def test_requirements_files_for_mode_skips_missing_optional_files(tmp_path):
    (tmp_path / "requirements.txt").write_text("PyMuPDF\n")
    result = installer.requirements_files_for_mode(InstallMode.LOCAL, tmp_path)
    assert [p.name for p in result] == ["requirements.txt"]


def test_create_venv_wraps_errors(monkeypatch, tmp_path):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="disk full")

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    with pytest.raises(InstallError, match="disk full"):
        installer.create_venv(tmp_path / "venv", base_python=tmp_path / "python")


def test_create_venv_invokes_base_python_module_venv(monkeypatch, tmp_path):
    captured = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    venv_dir = tmp_path / "venv"
    installer.create_venv(venv_dir, base_python=tmp_path / "python")
    assert captured["cmd"] == [str(tmp_path / "python"), "-m", "venv", str(venv_dir)]


def test_create_venv_defaults_to_base_python(monkeypatch, tmp_path):
    monkeypatch.setattr(installer, "_base_python", lambda: tmp_path / "resolved-python")
    captured = {}

    class _Result:
        returncode = 0

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    installer.create_venv(tmp_path / "venv")
    assert captured["cmd"][0] == str(tmp_path / "resolved-python")


# --- 04.09.2026: bundled-Python interpreter selection (Windows test-run fix) --


def test_base_python_uses_sys_executable_when_not_frozen(monkeypatch):
    monkeypatch.setattr(installer.paths, "is_frozen", lambda: False)
    assert installer._base_python() == Path(sys.executable)


def test_base_python_uses_bundled_python_when_frozen(monkeypatch):
    bundled = Path("/opt/bundled/python")
    monkeypatch.setattr(installer.paths, "is_frozen", lambda: True)
    monkeypatch.setattr(installer.bundled_python, "bundled_python_executable", lambda: bundled)
    assert installer._base_python() == bundled


def test_base_python_raises_when_frozen_and_bundle_missing(monkeypatch):
    monkeypatch.setattr(installer.paths, "is_frozen", lambda: True)
    monkeypatch.setattr(installer.bundled_python, "bundled_python_executable", lambda: None)
    with pytest.raises(InstallError, match="python_runtime"):
        installer._base_python()


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

    def fake_pip_install(venv_python, requirements_file, no_deps=False):
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


# --- 03.09.2026: driver-matched torch wheel index -----------------------------


@pytest.mark.parametrize(
    "cuda_version, expected_index",
    [
        ("12.4", "https://download.pytorch.org/whl/cu128"),
        ("11.8", "https://download.pytorch.org/whl/cu118"),
        ("13.0", None),
        (None, None),
    ],
)
def test_torch_install_command_picks_index(tmp_path, cuda_version, expected_index):
    cmd = installer.torch_install_command(tmp_path / "python", cuda_version)
    assert cmd[:4] == [str(tmp_path / "python"), "-m", "pip", "install"]
    assert "torch" in cmd and "torchvision" in cmd
    if expected_index:
        assert cmd[-2:] == ["--index-url", expected_index]
    else:
        assert "--index-url" not in cmd


def test_install_torch_wraps_errors(monkeypatch, tmp_path):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="no wheel")

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    with pytest.raises(InstallError, match="no wheel"):
        installer.install_torch(tmp_path / "python", "12.4")


def test_run_install_local_installs_torch_before_requirements(monkeypatch, tmp_path):
    dev_source = tmp_path / "dev-source"
    dev_source.mkdir()
    (dev_source / "requirements.txt").write_text("PyMuPDF\n")
    (dev_source / "requirements-gpu.txt").write_text("torch\n")
    order = []
    monkeypatch.setattr(installer, "create_venv", lambda vdir: vdir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(installer, "install_torch", lambda py, cuda: order.append(("torch", cuda)))
    monkeypatch.setattr(installer, "pip_install", lambda py, req, no_deps=False: order.append((req.name, no_deps)))
    monkeypatch.setattr(installer.desktop_integration, "create_desktop_entry", lambda *a, **k: tmp_path / "s")
    progress = []
    installer.run_install(
        tmp_path / "venv",
        tmp_path / "app",
        InstallMode.LOCAL,
        dev_source_override=str(dev_source),
        progress_cb=progress.append,
        cuda_version="12.4",
    )
    assert order == [("torch", "12.4"), ("requirements.txt", False), ("requirements-gpu.txt", False)]
    assert any(p.step is InstallStep.DEPS and p.detail == "torch (cu128)" for p in progress)


def test_run_install_online_never_installs_torch(monkeypatch, tmp_path):
    dev_source = tmp_path / "dev-source"
    dev_source.mkdir()
    (dev_source / "requirements.txt").write_text("PyMuPDF\n")
    called = []
    monkeypatch.setattr(installer, "create_venv", lambda vdir: vdir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(installer, "install_torch", lambda *a: called.append(a))
    monkeypatch.setattr(installer, "pip_install", lambda *a, **k: None)
    monkeypatch.setattr(installer.desktop_integration, "create_desktop_entry", lambda *a, **k: tmp_path / "s")
    installer.run_install(tmp_path / "venv", tmp_path / "app", InstallMode.ONLINE, dev_source_override=str(dev_source))
    assert called == []
