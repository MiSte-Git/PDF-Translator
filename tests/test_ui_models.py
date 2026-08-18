from pathlib import Path

import pytest

from pipeline.images.ocr import tesseract_available
from ui.analysis import analyze_request
from ui.models import EmbeddedImageMode, TranslationMode, TranslationRequest


FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


def test_mode_validation_does_not_auto_detect() -> None:
    request = TranslationRequest(TranslationMode.PDF, (FIXTURE,))
    assert any("passt nicht" in error for error in request.validation_errors())


def test_pptx_analysis_uses_existing_translation_selection() -> None:
    request = TranslationRequest(
        TranslationMode.PRESENTATION,
        (FIXTURE,),
        embedded_images=EmbeddedImageMode.NONE,
    )
    result = analyze_request(request)
    assert result.units == 1
    assert result.unit_label == "unit.slides"
    assert result.text_characters > 0
    assert result.cost.characters == result.text_characters
    assert result.selected_image_candidates == 0


def test_standalone_images_allow_multiple_files(tmp_path: Path) -> None:
    one = tmp_path / "one.png"
    two = tmp_path / "two.jpg"
    one.write_bytes(b"not decoded during inventory")
    two.write_bytes(b"not decoded during inventory")
    result = analyze_request(TranslationRequest(TranslationMode.IMAGES, (one, two)))
    assert result.units == 2
    assert result.ocr_required
    assert result.text_characters == 0
    assert result.embedded_images == 2


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_standalone_images_analysis_runs_real_ocr_for_a_real_character_count(tmp_path: Path) -> None:
    """Regression guard: analyze_request() must actually run OCR for
    TranslationMode.IMAGES (not just report 0, see
    test_standalone_images_allow_multiple_files() above for the
    undecodable-bytes case) - otherwise the cost estimate a user
    confirms before a real, chargeable run would always silently show
    $0.00, breaking RoadMap.md's "Analyse, Kostenschätzung und
    ausdrückliche Bestätigung vor jedem kostenpflichtigen Lauf"
    guiding principle.
    """
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    source = tmp_path / "photo.png"
    image = Image.new("RGB", (300, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    image.save(source)

    result = analyze_request(TranslationRequest(TranslationMode.IMAGES, (source,)))

    assert result.text_characters == len("Hello World")
    assert result.cost.characters == result.text_characters


def test_standalone_images_analysis_warns_when_ocr_engine_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ui.document_job_common.ocr_engine_available", lambda name: False)
    source = tmp_path / "photo.png"
    source.write_bytes(b"not decoded during inventory")

    result = analyze_request(TranslationRequest(TranslationMode.IMAGES, (source,)))

    assert result.text_characters == 0
    assert "warning.image_cost_unknown" in result.warnings
