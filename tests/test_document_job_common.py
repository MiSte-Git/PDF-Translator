"""Regression coverage for the OCR-Engine-/Inpainting-Backend-Factories
in ui/document_job_common.py (RoadMap.md Phase 3), added alongside the
already-existing PROVIDER_FACTORIES pattern - see that module's docstring
for why these live here rather than in pipeline/images/.
"""
from __future__ import annotations

import pytest

from pipeline.images.inpainting import BoxOverlayBackend, CvInpaintingBackend
from pipeline.images.ocr import TesseractOcrEngine
from ui.document_job_common import (
    build_inpainting_backend,
    build_ocr_engine,
    ocr_engine_available,
)


def test_build_ocr_engine_returns_tesseract_instance() -> None:
    engine = build_ocr_engine("tesseract")
    assert isinstance(engine, TesseractOcrEngine)


def test_build_ocr_engine_raises_for_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unbekannte OCR-Engine"):
        build_ocr_engine("does-not-exist")


@pytest.mark.parametrize(
    ("name", "expected_cls"),
    [("box_overlay", BoxOverlayBackend), ("cv_inpainting", CvInpaintingBackend)],
)
def test_build_inpainting_backend_returns_matching_instance(name: str, expected_cls: type) -> None:
    backend = build_inpainting_backend(name)
    assert isinstance(backend, expected_cls)


def test_build_inpainting_backend_raises_for_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unbekanntes Rückschreibe-Backend"):
        build_inpainting_backend("does-not-exist")


def test_ocr_engine_available_reflects_tesseract_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipeline.images.ocr.tesseract_available", lambda: True)
    assert ocr_engine_available("tesseract") is True

    monkeypatch.setattr("pipeline.images.ocr.tesseract_available", lambda: False)
    assert ocr_engine_available("tesseract") is False


def test_ocr_engine_available_false_for_unknown_engine() -> None:
    assert ocr_engine_available("does-not-exist") is False
