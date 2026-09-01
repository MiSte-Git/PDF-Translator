"""Regression coverage for the lokale KI-Inpainting-Rückschreibung
(RoadMap.md Phase 3), pipeline/images/inpainting.py::GpuInpaintingBackend.

This development sandbox has no CUDA GPU (see RoadMap.md Phase 3 - "Das
GPU-Backend kann in der Cloud-Sandbox dieser Entwicklungsumgebung nur in
seiner Logik/über einen CPU-Fallback getestet werden"), so what's tested
here is the LOGIC that doesn't need real hardware or the (optional, heavy,
requirements-gpu.txt) torch/simple-lama-inpainting packages actually
installed:

- gpu_inpainting_available()'s branching (torch missing, CUDA missing, a
  device-probe failure, CUDA present) - exercised by inserting a FAKE
  `torch` module into sys.modules rather than installing the real
  (~500 MB+) package, since none of these branches need genuine PyTorch
  behaviour, only the shape gpu_inpainting_available() reads off of it
  (torch.cuda.is_available()/get_device_properties()). Until 01.09.2026
  this also had a "GPU present but below GPU_MIN_VRAM_GB" branch that
  returned False - Michael that day: "GPU Schwelle auf den realistischen
  Wert anheben. Mit dem Hinweis, dass es auch mit geringerem Wert laufen
  kann, aber ohne Gewähr." - VRAM size no longer gates availability at
  all, gpu_vram_gb() covers that branching now (see its own tests below).
- _build_inpainting_mask()'s pure PIL logic (padding, clamping to image
  bounds, empty-replacements case).
- GpuInpaintingBackend.apply()'s fail-fast guard when
  gpu_inpainting_available() is False - the actual model call is never
  reached in that case, so no GPU/dependency is needed to verify it.

The one test that needs a real qualifying GPU (test_apply_end_to_end_on_a_
real_gpu below) is skipped here via the same gpu_inpainting_available()
check the backend itself uses - it exists as the real regression test for
whoever eventually runs this suite on the user's own GPU machine (see
RoadMap.md Phase 3's noted verification plan), not for this sandbox.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.inpainting import (
    GPU_MIN_VRAM_GB,
    GpuInpaintingBackend,
    InpaintingError,
    TextReplacement,
    _build_inpainting_mask,
    gpu_inpainting_available,
    gpu_vram_gb,
)
from pipeline.images.ocr import OcrTextRegion

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _install_fake_torch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cuda_available: bool,
    total_memory: int | None = None,
    probe_raises: bool = False,
) -> None:
    """Injects a minimal stand-in `torch` module into sys.modules so
    gpu_inpainting_available()'s `import torch` picks it up instead of
    the real package (not installed in this sandbox - see module
    docstring). Only the two attributes gpu_inpainting_available()
    actually reads (torch.cuda.is_available()/get_device_properties())
    are implemented - everything else about real torch is irrelevant to
    this function's own logic.
    """
    fake_cuda = types.SimpleNamespace()

    def is_available() -> bool:
        if probe_raises:
            raise RuntimeError("simulated CUDA probe failure")
        return cuda_available

    def get_device_properties(index: int):
        return types.SimpleNamespace(total_memory=total_memory)

    fake_cuda.is_available = is_available
    fake_cuda.get_device_properties = get_device_properties
    fake_torch = types.SimpleNamespace(cuda=fake_cuda, device=lambda name: name)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)


def test_gpu_inpainting_available_false_when_torch_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Setting the sys.modules entry to None makes "import torch" raise
    # ImportError, exactly like a genuinely missing package would -
    # standard technique for exercising an import-failure branch without
    # needing the real package absent from the whole test environment.
    monkeypatch.setitem(sys.modules, "torch", None)
    assert gpu_inpainting_available() is False


def test_gpu_inpainting_available_false_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_torch(monkeypatch, cuda_available=False)
    assert gpu_inpainting_available() is False


def test_gpu_inpainting_available_true_even_below_recommended_vram(monkeypatch: pytest.MonkeyPatch) -> None:
    # 01.09.2026: VRAM size no longer hard-gates availability (see module
    # docstring) - a weak-but-present CUDA GPU still counts as available,
    # only gpu_vram_gb() (tested separately below) lets a caller warn.
    _install_fake_torch(monkeypatch, cuda_available=True, total_memory=1 * 1024**3)  # 1 GB
    assert gpu_inpainting_available() is True


def test_gpu_inpainting_available_true_with_recommended_vram(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_torch(monkeypatch, cuda_available=True, total_memory=8 * 1024**3)  # 8 GB
    assert gpu_inpainting_available() is True


def test_gpu_vram_gb_none_when_torch_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "torch", None)
    assert gpu_vram_gb() is None


def test_gpu_vram_gb_none_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_torch(monkeypatch, cuda_available=False)
    assert gpu_vram_gb() is None


def test_gpu_vram_gb_none_when_device_probe_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_torch(monkeypatch, cuda_available=True, probe_raises=True)
    assert gpu_vram_gb() is None


def test_gpu_vram_gb_reports_detected_size(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_torch(monkeypatch, cuda_available=True, total_memory=1 * 1024**3)  # 1 GB
    assert gpu_vram_gb() == pytest.approx(1.0)


def test_gpu_vram_gb_below_recommendation_flagged_by_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    # Not gpu_inpainting_available()'s job any more (see above) - this is
    # exactly the comparison ui/app.py's inpainting_backend hint makes.
    _install_fake_torch(monkeypatch, cuda_available=True, total_memory=1 * 1024**3)  # 1 GB
    vram = gpu_vram_gb()
    assert vram is not None
    assert vram < GPU_MIN_VRAM_GB


def test_gpu_inpainting_available_false_when_device_probe_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # A driver mismatch/no device index 0/etc. must be swallowed and
    # treated as "not available", never let this check itself crash the
    # analysis/start flow (see its docstring).
    _install_fake_torch(monkeypatch, cuda_available=True, probe_raises=True)
    assert gpu_inpainting_available() is False


def test_build_inpainting_mask_marks_padded_region_white() -> None:
    region = OcrTextRegion(text="Hello", x=10, y=20, width=50, height=15, confidence=90.0)
    replacement = TextReplacement(region=region, translated_text="Hallo")

    mask = _build_inpainting_mask((100, 100), [replacement], padding=4)

    assert mask.size == (100, 100)
    assert mask.mode == "L"
    assert mask.getpixel((30, 25)) == 255  # well inside the padded region
    assert mask.getpixel((5, 5)) == 0  # far outside any region


def test_build_inpainting_mask_clamps_padding_to_image_bounds() -> None:
    # Region sits right at the top-left corner - padding would push the
    # padded box to negative coordinates, which must clamp to 0 rather
    # than wrap around or raise.
    region = OcrTextRegion(text="X", x=0, y=0, width=10, height=10, confidence=90.0)
    replacement = TextReplacement(region=region, translated_text="Y")

    mask = _build_inpainting_mask((20, 20), [replacement], padding=4)

    assert mask.getpixel((0, 0)) == 255


def test_build_inpainting_mask_empty_replacements_is_fully_black() -> None:
    mask = _build_inpainting_mask((10, 10), [])
    assert all(mask.getpixel((x, y)) == 0 for x in range(10) for y in range(10))


def test_build_inpainting_mask_covers_both_original_and_render_box() -> None:
    """26.08.2026 regression guard - real user report, Backlog.md
    26.08.2026: "die Positionen, Grösse und Korrekturen werden nicht
    übernommen". Without `render_box` in the mask too, the model would
    never reconstruct the corrected draw target's background, and without
    `region` in the mask, the ORIGINAL untranslated source text would
    never be removed at all - see TextReplacement.render_box's own
    docstring."""
    region = OcrTextRegion(text="Hello", x=10, y=10, width=20, height=15, confidence=90.0)
    render_box = OcrTextRegion(text="Hello", x=60, y=60, width=20, height=15, confidence=90.0)
    replacement = TextReplacement(region=region, translated_text="Hallo", render_box=render_box)

    mask = _build_inpainting_mask((100, 100), [replacement], padding=4)

    assert mask.getpixel((20, 17)) == 255  # inside the ORIGINAL region
    assert mask.getpixel((70, 67)) == 255  # inside the corrected render_box
    assert mask.getpixel((40, 40)) == 0  # neither - untouched


def test_apply_raises_before_touching_torch_when_gpu_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fail-fast guard: GpuInpaintingBackend.apply() must refuse to run
    (and never even attempt to import torch/download the model) once
    gpu_inpainting_available() says no - mirrors run_image_job()'s
    destination-conflict check and ocr_engine_available()'s UI-level
    fail-fast, just enforced inside the backend itself as a second line
    of defence.
    """
    monkeypatch.setattr("pipeline.images.inpainting.gpu_inpainting_available", lambda: False)
    monkeypatch.setitem(sys.modules, "torch", None)  # would raise if apply() got this far
    source = tmp_path / "in.png"
    Image.new("RGB", (50, 50), "white").save(source)

    with pytest.raises(InpaintingError, match="nicht verfügbar"):
        GpuInpaintingBackend().apply(str(source), [], str(tmp_path / "out.png"))


@pytest.mark.skipif(
    not gpu_inpainting_available(),
    reason="No qualifying CUDA GPU available in this environment - see gpu_inpainting_available()",
)
def test_apply_end_to_end_on_a_real_gpu(tmp_path: Path) -> None:
    """Only runs on a real machine with a qualifying CUDA GPU and the
    requirements-gpu.txt dependencies installed - always skipped in this
    development sandbox (see module docstring). Kept as the real
    regression test for whoever eventually runs this suite on such a
    machine, per RoadMap.md Phase 3's noted verification plan for this
    backend.
    """
    font = ImageFont.truetype(_FONT_PATH, 24)
    source = tmp_path / "photo.png"
    image = Image.new("RGB", (300, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 30), "Hello World", fill="black", font=font)
    image.save(source)

    region = OcrTextRegion(text="Hello World", x=20, y=30, width=150, height=24, confidence=95.0)
    replacement = TextReplacement(region=region, translated_text="Hallo Welt")
    destination = tmp_path / "out.png"

    GpuInpaintingBackend().apply(str(source), [replacement], str(destination))

    assert destination.exists()
