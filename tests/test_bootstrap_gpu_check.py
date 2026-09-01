"""Tests for bootstrap/gpu_check.py."""
from __future__ import annotations

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
