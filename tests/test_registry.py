"""Regression coverage for pipeline/registry.py's OCR-engine wiring
(RoadMap.md Phase 3, 23.08.2026: google_vision/paddleocr added alongside
tesseract) - PROVIDER_REGISTRY/INPAINTING_BACKEND_FACTORIES already had
their own coverage elsewhere (test_image_gpu_inpainting.py,
test_ui_images_mode.py); this file only adds what those don't cover: that
the two new OCR_ENGINE_FACTORIES entries build the right class, and that
ocr_engine_available() dispatches each name to its own real availability
check rather than a shared/wrong one.
"""
from __future__ import annotations

import pytest

from pipeline.images.ocr import GoogleVisionOcrEngine, PaddleOcrEngine, TesseractOcrEngine
from pipeline.registry import OCR_ENGINE_FACTORIES, build_ocr_engine, ocr_engine_available


def test_ocr_engine_factories_contains_all_three_engines() -> None:
    assert set(OCR_ENGINE_FACTORIES) == {"tesseract", "google_vision", "paddleocr"}


def test_build_ocr_engine_returns_the_right_class() -> None:
    assert isinstance(build_ocr_engine("tesseract"), TesseractOcrEngine)
    assert isinstance(build_ocr_engine("google_vision"), GoogleVisionOcrEngine)
    assert isinstance(build_ocr_engine("paddleocr"), PaddleOcrEngine)


def test_build_ocr_engine_raises_for_an_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unbekannte OCR-Engine"):
        build_ocr_engine("not-a-real-engine")


def test_ocr_engine_available_dispatches_to_each_engines_own_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each engine name must consult its OWN availability function, not a
    shared one - a regression here would mean e.g. selecting
    "google_vision" incorrectly reports Tesseract's own PATH check."""
    monkeypatch.setattr("pipeline.images.ocr.tesseract_available", lambda: True)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: False)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    assert ocr_engine_available("tesseract") is True
    assert ocr_engine_available("google_vision") is False
    assert ocr_engine_available("paddleocr") is True

    monkeypatch.setattr("pipeline.images.ocr.tesseract_available", lambda: False)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: True)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: False)

    assert ocr_engine_available("tesseract") is False
    assert ocr_engine_available("google_vision") is True
    assert ocr_engine_available("paddleocr") is False
