"""Tests for bootstrap/gpu_check.py."""
from __future__ import annotations

import json
import subprocess

import pytest

from bootstrap import gpu_check
from bootstrap.gpu_check import GpuInfo


class _FakeCompletedProcess:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_detect_nvidia_gpu_parses_output(monkeypatch):
    fake_stdout = "NVIDIA GeForce RTX 4070, 12282\n"

    def fake_run(*args, **kwargs):
        return _FakeCompletedProcess(fake_stdout)

    monkeypatch.setattr(gpu_check.subprocess, "run", fake_run)
    gpu = gpu_check.detect_nvidia_gpu()
    assert gpu is not None
    assert gpu.name == "NVIDIA GeForce RTX 4070"
    assert gpu.vram_gb == pytest.approx(12282 / 1024)


def test_detect_nvidia_gpu_returns_none_when_smi_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi not found")

    monkeypatch.setattr(gpu_check.subprocess, "run", fake_run)
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10)

    monkeypatch.setattr(gpu_check.subprocess, "run", fake_run)
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_nonzero_exit(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="nvidia-smi")

    monkeypatch.setattr(gpu_check.subprocess, "run", fake_run)
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_empty_output(monkeypatch):
    monkeypatch.setattr(gpu_check.subprocess, "run", lambda *a, **k: _FakeCompletedProcess("\n"))
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_malformed_output(monkeypatch):
    monkeypatch.setattr(gpu_check.subprocess, "run", lambda *a, **k: _FakeCompletedProcess("garbage-line\n"))
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_non_numeric_vram(monkeypatch):
    # rsplit finds a comma, but the part after it isn't a number - a
    # different unexpected-output shape than "no comma at all" above.
    monkeypatch.setattr(
        gpu_check.subprocess, "run", lambda *a, **k: _FakeCompletedProcess("NVIDIA GeForce RTX 4070, N/A\n")
    )
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_decode_error(monkeypatch):
    # 01.09.2026: `text=True` decoding nvidia-smi's raw output can itself
    # raise - must be swallowed exactly like every other failure mode here.
    def fake_run(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(gpu_check.subprocess, "run", fake_run)
    assert gpu_check.detect_nvidia_gpu() is None


def test_detect_nvidia_gpu_returns_none_on_wholly_unexpected_error(monkeypatch):
    # 01.09.2026 (Michael: "andere Fehler in diesem Zusammenhang [...]
    # sollte auch abgefangen werden, nicht dass der Installer abstürzt"):
    # the catch-all safety net - something neither of the specific except
    # clauses anticipated must still not escape this function.
    def fake_run(*args, **kwargs):
        raise RuntimeError("something nobody anticipated")

    monkeypatch.setattr(gpu_check.subprocess, "run", fake_run)
    assert gpu_check.detect_nvidia_gpu() is None


@pytest.mark.parametrize(
    "gpu, min_vram_gb, expected",
    [
        (GpuInfo(name="RTX 4090", vram_gb=24.0), gpu_check.GPU_MIN_VRAM_GB, True),
        (GpuInfo(name="GTX 1650", vram_gb=4.0), gpu_check.GPU_MIN_VRAM_GB, False),
        (GpuInfo(name="RTX 3070", vram_gb=8.0), gpu_check.GPU_MIN_VRAM_GB, True),
        (None, gpu_check.GPU_MIN_VRAM_GB, False),
    ],
)
def test_meets_recommendation(gpu, min_vram_gb, expected):
    assert gpu_check.meets_recommendation(gpu, min_vram_gb) is expected


# --- persistence (01.09.2026, Michael: "Ist es möglich den HW Check beim
# Installieren zu speichern...") ----------------------------------------


def test_save_gpu_check_result_writes_found_gpu(tmp_path):
    marker = tmp_path / "gpu_check.json"
    gpu = GpuInfo(name="RTX 4070", vram_gb=12.0)

    result = gpu_check.save_gpu_check_result(gpu, marker_path=marker)

    assert result.found is True
    assert result.name == "RTX 4070"
    assert result.vram_gb == 12.0
    assert result.meets_recommendation is True
    assert result.min_vram_gb == gpu_check.GPU_MIN_VRAM_GB
    assert result.checked_at  # non-empty timestamp string
    saved = json.loads(marker.read_text(encoding="utf-8"))
    assert saved["found"] is True
    assert saved["name"] == "RTX 4070"


def test_save_gpu_check_result_writes_not_found(tmp_path):
    marker = tmp_path / "gpu_check.json"

    result = gpu_check.save_gpu_check_result(None, marker_path=marker)

    assert result.found is False
    assert result.name is None
    assert result.vram_gb is None
    assert result.meets_recommendation is False
    saved = json.loads(marker.read_text(encoding="utf-8"))
    assert saved["found"] is False


def test_save_gpu_check_result_creates_parent_directory(tmp_path):
    marker = tmp_path / "nested" / "does" / "not" / "exist" / "gpu_check.json"
    gpu_check.save_gpu_check_result(None, marker_path=marker)
    assert marker.is_file()


def test_save_gpu_check_result_flags_below_recommended_vram(tmp_path):
    marker = tmp_path / "gpu_check.json"
    gpu = GpuInfo(name="GTX 1650", vram_gb=4.0)

    result = gpu_check.save_gpu_check_result(gpu, marker_path=marker)

    assert result.found is True
    assert result.meets_recommendation is False


def test_read_gpu_check_marker_round_trips_a_saved_result(tmp_path):
    marker = tmp_path / "gpu_check.json"
    gpu_check.save_gpu_check_result(GpuInfo(name="RTX 4090", vram_gb=24.0), marker_path=marker)

    result = gpu_check.read_gpu_check_marker(marker_path=marker)

    assert result is not None
    assert result.found is True
    assert result.name == "RTX 4090"
    assert result.meets_recommendation is True


def test_read_gpu_check_marker_none_when_file_missing(tmp_path):
    assert gpu_check.read_gpu_check_marker(marker_path=tmp_path / "does-not-exist.json") is None


def test_read_gpu_check_marker_none_on_corrupt_json(tmp_path):
    marker = tmp_path / "gpu_check.json"
    marker.write_text("not valid json{{{", encoding="utf-8")
    assert gpu_check.read_gpu_check_marker(marker_path=marker) is None


def test_read_gpu_check_marker_none_on_unexpected_shape(tmp_path):
    # Valid JSON, but not the dict-of-known-fields GpuCheckResult expects -
    # must be treated the same as "corrupt", not raise a TypeError.
    marker = tmp_path / "gpu_check.json"
    marker.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert gpu_check.read_gpu_check_marker(marker_path=marker) is None


def test_detect_and_save_gpu_check_uses_default_marker_path(monkeypatch, tmp_path):
    marker = tmp_path / "gpu_check.json"
    monkeypatch.setattr(gpu_check.paths, "gpu_check_marker_file", lambda: marker)
    fake_gpu = GpuInfo(name="RTX 4070", vram_gb=12.0)
    monkeypatch.setattr(gpu_check, "detect_nvidia_gpu", lambda: fake_gpu)

    gpu, result = gpu_check.detect_and_save_gpu_check()

    assert gpu is fake_gpu
    assert result.name == "RTX 4070"
    assert marker.is_file()


def test_detect_and_save_gpu_check_probes_hardware_exactly_once(monkeypatch, tmp_path):
    marker = tmp_path / "gpu_check.json"
    calls = []

    def fake_detect():
        calls.append(1)
        return GpuInfo(name="RTX 4070", vram_gb=12.0)

    monkeypatch.setattr(gpu_check, "detect_nvidia_gpu", fake_detect)
    gpu_check.detect_and_save_gpu_check(marker_path=marker)
    assert len(calls) == 1
