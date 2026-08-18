"""Coverage for run_image_batch_job() (ui/image_job.py, RoadMap.md Phase 3)
- the multi-FILE loop ui/app.py's Start button calls for
TranslationMode.IMAGES, the only mode whose TranslationRequest allows more
than one selected source file at once. Mirrors tests/test_image_job.py's
fixtures/conventions for the single-file run_image_job().
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.ocr import tesseract_available
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.image_job import run_image_batch_job

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")


class FakeProvider:
    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def _build_image(path: Path, text: str) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (300, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), text, fill="black", font=font)
    image.save(path)


def test_run_image_batch_job_processes_every_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    sources = []
    for i in range(3):
        source = tmp_path / f"image{i}.png"
        _build_image(source, f"Photo {i}")
        sources.append(source)

    total_calls: list[int] = []
    progress_messages: list[str] = []

    result = run_image_batch_job(
        sources, output_dir, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
        total_callback=total_calls.append,
        progress_callback=progress_messages.append,
    )

    assert result.output_dir == output_dir
    assert result.stats.files_processed == 3
    assert result.stats.files_total == 3
    assert len(result.stats.results) == 3
    assert result.stats.translated == 3  # one region per fixture image
    assert total_calls == [3]
    assert any("1/3" in msg for msg in progress_messages)
    assert any("3/3" in msg for msg in progress_messages)

    # Every file must have produced its own distinct output image.
    output_files = {r.output_path for r in result.stats.results}
    assert len(output_files) == 3
    for output_path in output_files:
        assert output_path.exists()
        assert output_path.parent == output_dir


def test_run_image_batch_job_avoids_filename_collisions(tmp_path: Path) -> None:
    """Two source files with the SAME stem (from different source
    directories) must not collide in the shared output_dir -
    safe_destination()'s numeric-suffix fallback must kick in for the
    second one.
    """
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    dir_a = tmp_path / "a"; dir_a.mkdir()
    dir_b = tmp_path / "b"; dir_b.mkdir()
    source_a = dir_a / "photo.png"
    source_b = dir_b / "photo.png"
    _build_image(source_a, "First")
    _build_image(source_b, "Second")

    result = run_image_batch_job(
        [source_a, source_b], output_dir, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )

    output_paths = [r.output_path for r in result.stats.results]
    assert len(set(output_paths)) == 2


def test_run_image_batch_job_stops_further_files_when_cancelled(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    sources = []
    for i in range(3):
        source = tmp_path / f"image{i}.png"
        _build_image(source, f"Photo {i}")
        sources.append(source)

    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # cancel right before the second file starts

    result = run_image_batch_job(
        sources, output_dir, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(), should_cancel=should_cancel,
    )

    assert result.stats.cancelled is True
    assert result.stats.files_processed == 1
    assert len(result.stats.results) == 1


def test_run_image_batch_job_stats_callback_reports_cumulative_progress(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    sources = []
    for i in range(2):
        source = tmp_path / f"image{i}.png"
        _build_image(source, f"Photo {i}")
        sources.append(source)

    snapshots: list[tuple[int, int]] = []

    run_image_batch_job(
        sources, output_dir, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
        stats_callback=lambda stats: snapshots.append((stats.files_processed, stats.translated)),
    )

    assert snapshots == [(1, 1), (2, 2)]


def test_run_image_batch_job_works_for_a_single_file(tmp_path: Path) -> None:
    """No special-casing needed in ui/app.py for "just one image" - a
    one-element sources list must behave the same as the loop with more.
    """
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    source = tmp_path / "solo.png"
    _build_image(source, "Solo")

    result = run_image_batch_job(
        [source], output_dir, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeProvider(),
    )

    assert result.stats.files_processed == 1
    assert result.stats.files_total == 1
