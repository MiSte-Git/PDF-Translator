"""Tests for bootstrap/controller.py."""
from __future__ import annotations

import json

import pytest

from bootstrap.controller import BootstrapController
from bootstrap.gpu_check import GpuInfo
from bootstrap.installer import InstallError, InstallMode, InstallStep


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "bootstrap.controller.system_lang.detect_system_language", lambda: "en"
    )
    return BootstrapController(venv_dir=tmp_path / "venv", app_source_dir=tmp_path / "app")


def test_initial_language_comes_from_system_detection(controller):
    assert controller.language == "en"


def test_set_language_only_accepts_known_catalogues(controller):
    controller.set_language("de")
    assert controller.language == "de"
    controller.set_language("xx")
    assert controller.language == "de"  # unchanged


def test_text_looks_up_current_language(controller):
    controller.set_language("de")
    assert controller.text("bootstrap.next_button") == "Weiter"
    controller.set_language("en")
    assert controller.text("bootstrap.next_button") == "Next"


def test_text_formats_placeholders(controller):
    controller.set_language("en")
    result = controller.text("bootstrap.gpu_ok", name="RTX 4090", vram_gb=24.0)
    assert "RTX 4090" in result
    assert "24" in result


def test_write_language_marker_writes_json(controller, monkeypatch, tmp_path):
    marker_path = tmp_path / "language.json"
    monkeypatch.setattr("bootstrap.controller.paths.language_marker_file", lambda: marker_path)
    controller.set_language("en")
    result = controller.write_language_marker()
    assert result == marker_path
    assert json.loads(marker_path.read_text()) == {"language": "en"}


def test_check_gpu_stores_and_returns_result(controller, monkeypatch, tmp_path):
    fake_gpu = GpuInfo(name="RTX 4070", vram_gb=12.0)
    monkeypatch.setattr("bootstrap.controller.gpu_check.detect_nvidia_gpu", lambda: fake_gpu)
    # 01.09.2026: check_gpu() now also persists via
    # gpu_check.save_gpu_check_result(), which defaults to the real
    # per-user gpu_check_marker_file() - redirected here exactly like
    # test_write_language_marker_writes_json redirects language_marker_file
    # above, so this test never touches a real machine's install directory.
    marker_path = tmp_path / "gpu_check.json"
    monkeypatch.setattr("bootstrap.gpu_check.paths.gpu_check_marker_file", lambda: marker_path)

    result = controller.check_gpu()

    assert result is fake_gpu
    assert controller.gpu_info is fake_gpu
    assert controller.gpu_meets_recommendation() is True
    saved = json.loads(marker_path.read_text())
    assert saved["found"] is True
    assert saved["name"] == "RTX 4070"
    assert saved["meets_recommendation"] is True


def test_gpu_meets_recommendation_false_when_no_gpu(controller):
    assert controller.gpu_info is None
    assert controller.gpu_meets_recommendation() is False


def test_run_install_requires_mode_first(controller):
    with pytest.raises(RuntimeError):
        controller.run_install()


def test_run_install_delegates_and_stores_venv_python(controller, monkeypatch, tmp_path):
    expected = tmp_path / "venv" / "bin" / "python"

    def fake_run_install(venv_dir, app_source_dir, mode, dev_source_override=None, progress_cb=None, cuda_version=None):
        assert mode is InstallMode.ONLINE
        if progress_cb:
            progress_cb(None)
        return expected

    monkeypatch.setattr("bootstrap.controller.installer.run_install", fake_run_install)
    controller.set_mode(InstallMode.ONLINE)
    seen = []
    result = controller.run_install(progress_cb=seen.append)
    assert result == expected
    assert controller.venv_python == expected
    assert controller.install_error is None


def test_run_install_records_error_and_reraises(controller, monkeypatch):
    def fake_run_install(*a, **k):
        raise InstallError("pip explosion")

    monkeypatch.setattr("bootstrap.controller.installer.run_install", fake_run_install)
    controller.set_mode(InstallMode.LOCAL)
    with pytest.raises(InstallError):
        controller.run_install()
    assert controller.install_error == "pip explosion"


def test_credentials_delegation(controller, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "bootstrap.controller.credentials_step.list_providers",
        lambda app_dir: ["deepl", "openai"],
    )
    monkeypatch.setattr(
        "bootstrap.controller.credentials_step.provider_status",
        lambda app_dir, provider: calls.append(("status", provider)) or "credential.missing",
    )
    monkeypatch.setattr(
        "bootstrap.controller.credentials_step.save_provider_credential",
        lambda app_dir, provider, value: calls.append(("save", provider, value)),
    )
    monkeypatch.setattr(
        "bootstrap.controller.credentials_step.open_signup_page",
        lambda provider: calls.append(("open", provider)) or True,
    )

    assert controller.list_providers() == ["deepl", "openai"]
    assert controller.provider_status("deepl") == "credential.missing"
    controller.save_provider_credential("openai", "sk-test")
    assert controller.open_signup_page("deepl") is True
    assert ("status", "deepl") in calls
    assert ("save", "openai", "sk-test") in calls
    assert ("open", "deepl") in calls


def test_launch_app_uses_stored_venv_python(controller, monkeypatch, tmp_path):
    controller.venv_python = tmp_path / "venv" / "bin" / "python"
    captured = {}

    def fake_popen(cmd, cwd):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return "process-handle"

    monkeypatch.setattr("bootstrap.controller.subprocess.Popen", fake_popen)
    result = controller.launch_app()
    assert result == "process-handle"
    assert captured["cmd"] == [str(controller.venv_python), "-m", "ui.app"]
    assert captured["cwd"] == str(controller.app_source_dir)


def test_launch_app_falls_back_to_paths_venv_python(controller, monkeypatch):
    monkeypatch.setattr("bootstrap.controller.subprocess.Popen", lambda cmd, cwd: cmd)
    result = controller.launch_app()
    assert str(controller.venv_dir) in result[0]


# --- 03.09.2026: driver CUDA version reaches run_install ----------------------


def test_run_install_passes_cuda_version_from_gpu_check(monkeypatch, tmp_path):
    from bootstrap.controller import BootstrapController
    from bootstrap.installer import InstallMode

    controller = BootstrapController(venv_dir=tmp_path / "venv", app_source_dir=tmp_path / "app")
    monkeypatch.setattr(
        "bootstrap.controller.gpu_check.detect_nvidia_gpu",
        lambda: GpuInfo(name="RTX 4070", vram_gb=12.0, cuda_version="12.4"),
    )
    monkeypatch.setattr("bootstrap.gpu_check.paths.gpu_check_marker_file", lambda: tmp_path / "gpu.json")
    controller.check_gpu()
    assert controller.gpu_driver_supported() is True
    seen = {}

    def fake_run_install(venv_dir, app_source_dir, mode, dev_source_override=None, progress_cb=None, cuda_version=None):
        seen["cuda_version"] = cuda_version
        return tmp_path / "venv" / "bin" / "python"

    monkeypatch.setattr("bootstrap.controller.installer.run_install", fake_run_install)
    controller.set_mode(InstallMode.LOCAL)
    controller.run_install()
    assert seen["cuda_version"] == "12.4"


def test_gpu_driver_supported_false_for_old_driver(monkeypatch, tmp_path):
    from bootstrap.controller import BootstrapController

    controller = BootstrapController(venv_dir=tmp_path / "venv", app_source_dir=tmp_path / "app")
    monkeypatch.setattr(
        "bootstrap.controller.gpu_check.detect_nvidia_gpu",
        lambda: GpuInfo(name="GTX 1080", vram_gb=8.0, cuda_version="11.4"),
    )
    monkeypatch.setattr("bootstrap.gpu_check.paths.gpu_check_marker_file", lambda: tmp_path / "gpu.json")
    controller.check_gpu()
    assert controller.gpu_driver_supported() is False
