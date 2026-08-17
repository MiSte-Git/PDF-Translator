from pathlib import Path

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
