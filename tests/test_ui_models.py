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


# 03.09.2026 (Michael: "Werden bei der Kostenkontrolle die übersetzten Bilder
# mit berechnet und weggelassen wenn diese nicht übersetzt werden sollen?"):
# the embedded-image inventory is always reported, but only the chosen image
# mode decides how many of them count as translation candidates - "keine
# Bilder" must never leave a selected/charged image behind, and text_characters
# (the priced number) is unaffected by the image mode either way, because the
# document runs do not translate embedded images yet.

def test_pptx_analysis_excludes_embedded_images_when_mode_is_none() -> None:
    result = analyze_request(TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), embedded_images=EmbeddedImageMode.NONE))
    assert result.selected_image_candidates == 0
    assert "warning.embedded_images_not_estimated" not in result.warnings
    assert result.cost.characters == result.text_characters


def test_pptx_analysis_reports_candidates_but_prices_no_image_text_when_mode_is_all() -> None:
    none = analyze_request(TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), embedded_images=EmbeddedImageMode.NONE))
    result = analyze_request(TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), embedded_images=EmbeddedImageMode.ALL))
    assert result.embedded_images == none.embedded_images
    assert result.selected_image_candidates == result.embedded_images
    assert result.text_characters == none.text_characters
    if result.embedded_images:
        assert "warning.embedded_images_not_estimated" in result.warnings
    else:
        assert "warning.embedded_images_not_estimated" not in result.warnings


def test_pptx_analysis_selected_mode_keeps_its_later_ui_warning() -> None:
    result = analyze_request(TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), embedded_images=EmbeddedImageMode.SELECTED))
    assert "warning.image_selection_later" in result.warnings
    assert result.selected_image_candidates == result.embedded_images
