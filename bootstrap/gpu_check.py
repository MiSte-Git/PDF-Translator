"""Pre-install GPU capability check, without requiring PyTorch.

pipeline/images/inpainting.py::gpu_inpainting_available() already checks GPU
suitability, but it does so via `torch.cuda` - which needs PyTorch already
installed. That is unusable here: the bootstrapper must know whether "Lokal"
is a good idea *before* it downloads and installs anything (see the "Online
oder lokal?" step in the 01.09.2026 project doc). This module instead shells
out to `nvidia-smi`, which ships with every NVIDIA driver and needs no
Python package at all.

GPU_MIN_VRAM_GB here (8 GB) is intentionally more conservative than
pipeline/images/inpainting.py::GPU_MIN_VRAM_GB (4 GB) - the two are not a
contradiction. The pipeline constant is the hard technical floor a already-
installed local setup enforces at run time; this one is the bootstrapper's
own up-front *recommendation* to a user who has not installed anything yet
and would otherwise burn a large download on a GPU that technically starts
but runs local inpainting very slowly.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

GPU_MIN_VRAM_GB = 8.0

_NVIDIA_SMI_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vram_gb: float


def detect_nvidia_gpu() -> GpuInfo | None:
    """First NVIDIA GPU reported by `nvidia-smi`, or None if unavailable.

    None covers every "can't tell" case identically (no NVIDIA driver
    installed, no supported GPU present, nvidia-smi hangs/errors) - the
    caller only ever needs to distinguish "usable GPU found" from "not
    found", never the specific reason, so a single Optional return keeps
    every call site simple.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=_NVIDIA_SMI_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        # OSError: nvidia-smi not on PATH (no NVIDIA driver installed).
        # SubprocessError covers CalledProcessError and TimeoutExpired.
        return None

    first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not first_line:
        return None
    # Format: "<name>, <memory.total in MiB>" - name itself may contain commas
    # is not a real-world case for NVIDIA product names, so a simple rsplit
    # on the last comma is safe and avoids CSV-parsing overhead for one row.
    try:
        name_part, vram_mib_part = first_line.rsplit(",", 1)
    except ValueError:
        return None
    name = name_part.strip()
    try:
        vram_mib = float(vram_mib_part.strip())
    except ValueError:
        return None
    # NVIDIA reports MiB (2^20 bytes); GB here means the same binary GiB-ish
    # unit consumer GPU marketing uses (e.g. "8 GB" card -> ~8192 MiB
    # reported), so divide by 1024 rather than 1000 to match what a user
    # reads on the box.
    return GpuInfo(name=name, vram_gb=vram_mib / 1024)


def meets_recommendation(gpu: GpuInfo | None, min_vram_gb: float = GPU_MIN_VRAM_GB) -> bool:
    """True if `gpu` is present and has at least `min_vram_gb` of VRAM."""
    return gpu is not None and gpu.vram_gb >= min_vram_gb
