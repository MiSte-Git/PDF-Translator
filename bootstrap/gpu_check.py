"""Pre-install GPU capability check, without requiring PyTorch.

01.09.2026 (Michael: "Ist es möglich den HW Check beim Installieren zu
speichern und in einem Hilfe Menü in der App eine Möglichkeit den HW Test
anzeigen zu lassen und auch noch mal zu wiederholen. Dort sollte auch
angezeigt werden ob die HW die Mindestanforderung erfüllt."): also owns
persisting a check's result (save_gpu_check_result()/
read_gpu_check_marker()/detect_and_save_gpu_check() below) to
bootstrap/paths.py::gpu_check_marker_file(), so BOTH the installer's
Stage-1 GPU-check step (bootstrap/controller.py::check_gpu()) and a later
re-check the user triggers from ui/app.py's "Hilfe" -> Hardware-Test
dialog write through the exact same function - one JSON shape, one place
that decides it, rather than two independently-maintained copies.

pipeline/images/inpainting.py::gpu_inpainting_available() already checks GPU
suitability, but it does so via `torch.cuda` - which needs PyTorch already
installed. That is unusable here: the bootstrapper must know whether "Lokal"
is a good idea *before* it downloads and installs anything (see the "Online
oder lokal?" step in the 01.09.2026 project doc). This module instead shells
out to `nvidia-smi`, which ships with every NVIDIA driver and needs no
Python package at all.

GPU_MIN_VRAM_GB here (8 GB) is the bootstrapper's own up-front
*recommendation* to a user who has not installed anything yet and would
otherwise burn a large download on a GPU that technically starts but runs
local inpainting very slowly. Until 01.09.2026 this was deliberately more
conservative than pipeline/images/inpainting.py::GPU_MIN_VRAM_GB (4 GB),
which back then was a hard technical floor the already-installed local
setup enforced at run time. Per Michael's 01.09.2026 decision ("Die GPU
Schwelle auf den realistischen Wert anheben. Mit dem Hinweis, dass es
auch mit geringerem Wert laufen kann, aber ohne Gewähr."), that pipeline
constant is now a recommendation too (no longer a hard gate) and was
raised to the same 8 GB value - the two constants now mean the same
thing at two different points in time (before vs. after install), rather
than being intentionally different.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from bootstrap import paths

GPU_MIN_VRAM_GB = 8.0

_NVIDIA_SMI_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vram_gb: float


def detect_nvidia_gpu() -> GpuInfo | None:
    """First NVIDIA GPU reported by `nvidia-smi`, or None if unavailable.

    None covers every "can't tell" case identically (no NVIDIA driver
    installed - e.g. an AMD/Intel-only machine or a Mac -, no supported GPU
    present, nvidia-smi hangs/errors, or any other unexpected failure while
    running or parsing it) - the caller only ever needs to distinguish
    "usable GPU found" from "not found", never the specific reason, so a
    single Optional return keeps every call site simple.

    Guaranteed to never raise (01.09.2026, Michael: "ist eine fehlgeschlagene
    GPU-Abfrage abgefangen? [...] das sollte auch abgefangen werden, nicht
    dass der Installer abstürzt"): this runs unattended during Stage 1 of
    the installer, before the user has anything else installed to fall back
    on, so any exception escaping this function would leave the wizard
    stuck with no visible error and no way to continue (see
    bootstrap/app.py::_show_gpu_check(), which has no error handling of its
    own around this call and relies entirely on this guarantee). The two
    specific except clauses below document the failures that are actually
    expected in practice (no driver, a malformed/unexpected nvidia-smi
    output); the final bare `except Exception` is a deliberate catch-all
    safety net for anything neither of those anticipated (e.g. a locale
    that makes nvidia-smi emit non-UTF-8 output and raise
    UnicodeDecodeError from `text=True` decoding it) - this function's
    entire contract is "never raises", not "never raises for the failure
    modes I thought of".
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

        first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        if not first_line:
            return None
        # Format: "<name>, <memory.total in MiB>" - name itself may contain
        # commas is not a real-world case for NVIDIA product names, so a
        # simple rsplit on the last comma is safe and avoids CSV-parsing
        # overhead for one row.
        name_part, vram_mib_part = first_line.rsplit(",", 1)
        name = name_part.strip()
        vram_mib = float(vram_mib_part.strip())
        # NVIDIA reports MiB (2^20 bytes); GB here means the same binary
        # GiB-ish unit consumer GPU marketing uses (e.g. "8 GB" card ->
        # ~8192 MiB reported), so divide by 1024 rather than 1000 to match
        # what a user reads on the box.
        return GpuInfo(name=name, vram_gb=vram_mib / 1024)
    except (OSError, subprocess.SubprocessError):
        # OSError: nvidia-smi not on PATH (no NVIDIA driver installed - no
        # NVIDIA GPU, or an AMD/Intel GPU, or a Mac). SubprocessError
        # covers CalledProcessError (nvidia-smi ran but exited non-zero)
        # and TimeoutExpired (nvidia-smi hung).
        return None
    except (ValueError, UnicodeDecodeError):
        # ValueError: rsplit found no comma, or the VRAM part wasn't a
        # number - nvidia-smi's output didn't look like what this function
        # expects (unexpected driver/locale/CSV formatting quirk).
        # UnicodeDecodeError: `text=True` above failed to decode
        # nvidia-smi's raw output as UTF-8.
        return None
    except Exception:
        # Deliberate catch-all - see the docstring's "never raises"
        # guarantee above. Whatever this is, it is not this function's job
        # to surface it; the caller only needs to know no usable GPU could
        # be confirmed.
        return None


def meets_recommendation(gpu: GpuInfo | None, min_vram_gb: float = GPU_MIN_VRAM_GB) -> bool:
    """True if `gpu` is present and has at least `min_vram_gb` of VRAM."""
    return gpu is not None and gpu.vram_gb >= min_vram_gb


@dataclass(frozen=True)
class GpuCheckResult:
    """Everything ui/app.py's Hardware-Test dialog needs to display, in one
    JSON-serializable place - the persisted counterpart of one
    detect_nvidia_gpu() + meets_recommendation() call. `checked_at` is a
    plain ISO-8601 UTC string, not a datetime, so this dataclass round-trips
    through json.dumps()/dataclass field types with no custom encoder.
    `name`/`vram_gb` are None when `found` is False - no GPU means nothing
    to report a name/size for.
    """

    checked_at: str
    found: bool
    name: str | None
    vram_gb: float | None
    meets_recommendation: bool
    min_vram_gb: float


def save_gpu_check_result(gpu: GpuInfo | None, marker_path: Path | None = None) -> GpuCheckResult:
    """Persists an ALREADY-DETECTED `gpu` (from detect_nvidia_gpu()) as JSON
    to `marker_path` (bootstrap.paths.gpu_check_marker_file() by default)
    and returns the same result.

    Takes `gpu` rather than calling detect_nvidia_gpu() itself so a caller
    that already has a fresh result (bootstrap/controller.py::check_gpu(),
    which needs the GpuInfo object itself for its own return value/
    gpu_meets_recommendation()) never probes the hardware twice for one
    logical check. detect_and_save_gpu_check() below is the convenience
    wrapper for callers (ui/app.py's re-check button) that don't already
    have one.
    """
    marker = marker_path if marker_path is not None else paths.gpu_check_marker_file()
    result = GpuCheckResult(
        checked_at=datetime.now(timezone.utc).isoformat(),
        found=gpu is not None,
        name=gpu.name if gpu is not None else None,
        vram_gb=gpu.vram_gb if gpu is not None else None,
        meets_recommendation=meets_recommendation(gpu),
        min_vram_gb=GPU_MIN_VRAM_GB,
    )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(asdict(result)), encoding="utf-8")
    return result


def detect_and_save_gpu_check(marker_path: Path | None = None) -> tuple[GpuInfo | None, GpuCheckResult]:
    """detect_nvidia_gpu() + save_gpu_check_result() in one call - what
    ui/app.py's "Hilfe" -> Hardware-Test dialog's "Erneut prüfen" button
    uses (it has no already-detected GpuInfo lying around the way
    bootstrap/controller.py::check_gpu() does).
    """
    gpu = detect_nvidia_gpu()
    return gpu, save_gpu_check_result(gpu, marker_path)


def read_gpu_check_marker(marker_path: Path | None = None) -> GpuCheckResult | None:
    """Last persisted result written by save_gpu_check_result(), or None if
    no check has ever been persisted (e.g. an ONLINE-mode install, which
    never runs the GPU-check step at all, and the user has not yet used
    the "Hilfe" -> Hardware-Test dialog's re-check button either) or the
    marker file is missing/unreadable/corrupt. Mirrors
    ui/app.py::_bootstrap_language_marker()'s own
    never-raise-on-a-bad-marker-file pattern - this is a convenience
    display only, never a hard requirement.
    """
    marker = marker_path if marker_path is not None else paths.gpu_check_marker_file()
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return GpuCheckResult(**data)
    except (OSError, json.JSONDecodeError, TypeError):
        return None
