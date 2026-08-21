"""Regression coverage for pipeline/images/translate_image.py (RoadMap.md
Phase 3 - Bildübersetzung und OCR): the OCR -> Übersetzung -> Rückschreibung
loop, independent of ui/image_job.py's file-handling/QA-report layer around
it (mirrors how tests/test_pdf_ico_mode.py separates engine-level from
job-level coverage).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.inpainting import BoxOverlayBackend, TextReplacement
from pipeline.images.ocr import OcrError, OcrTextRegion, TesseractOcrEngine, tesseract_available
from pipeline.images.translate_image import build_corrected_replacements, translate_image
from pipeline.translation.base import TranslationError, TranslationResult

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


class _FakeProvider:
    """Minimal TranslationProvider: appends " [DE]" to every translated
    text - mirrors FakeHtmlProvider in tests/test_pdf_ico_mode.py, just
    the plain-text translate() half (translate_image() never calls
    translate_html())."""

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


class _SelectiveFailProvider:
    """Raises TranslationError for one specific input text, succeeds for
    everything else - lets a test assert that one bad region doesn't
    abort translation of the rest, mirroring translate_pdf()'s own
    per-block try/except test coverage."""

    def __init__(self, fail_text: str) -> None:
        self._fail_text = fail_text

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        if text == self._fail_text:
            raise TranslationError("simulierter Anbieterfehler")
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


class _StubFailingOcrEngine:
    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        raise OcrError("Tesseract-Binary wurde nicht gefunden")


class _StubOcrEngine:
    """Returns a FIXED list of regions regardless of the image, with
    caller-controlled confidence values - lets the min_confidence
    skipping tests below assert exact behavior without depending on
    whatever confidence real Tesseract happens to assign (see
    Backlog.md 18.08.2026: real Tesseract runs on actual screenshots
    motivated this feature, but the unit tests here need deterministic
    inputs, not a real OCR pass)."""

    def __init__(self, regions: list[OcrTextRegion]) -> None:
        self._regions = regions

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        return self._regions


class _CountingProvider:
    """Records every text it was actually asked to translate - lets a
    test assert that a skipped (low-confidence) region never reaches the
    provider at all, not just that it's absent from the final stats."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        self.calls.append(text)
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def test_translate_image_translates_all_regions_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de",
    )

    assert stats.translated == 2
    assert stats.failed == 0
    assert len(stats.regions) == 2
    assert destination.exists()

    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(destination))]
    assert "Hello World" not in result_texts
    assert "Second Line" not in result_texts
    assert any("[DE]" in text for text in result_texts)


def test_translate_image_counts_failed_region_without_aborting_others(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _SelectiveFailProvider(fail_text="Hello World"), [], target_lang="de",
    )

    assert stats.translated == 1
    assert stats.failed == 1
    assert len(stats.errors) == 1
    assert "region" in stats.errors[0]
    assert destination.exists()


def test_translate_image_replacements_only_include_successful_regions(tmp_path: Path) -> None:
    """stats.replacements (used by the manual correction dialog, see
    ui/image_correction_dialog.py) must mirror PdfTranslationStats.blocks'
    contract: only successfully-translated regions are included - a
    failed region (see test above) has no translated text to show/edit,
    so it must be absent here rather than included with a placeholder.
    """
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _SelectiveFailProvider(fail_text="Hello World"), [], target_lang="de",
    )

    assert len(stats.replacements) == 1
    assert stats.replacements[0].region.text == "Second Line"
    assert stats.replacements[0].translated_text == "Second Line [DE]"
    # Exactly the list handed to inpainting_backend.apply() - same object
    # identity check would be too strict across a hypothetical future
    # refactor, so compare by content instead.
    assert len(stats.replacements) == stats.translated


# --- min_confidence skipping (RoadMap.md/Backlog.md 18.08.2026: real
# user found garbled, overlapping output caused in part by UI icons/
# graphics Tesseract misread as text, each with a conspicuously low
# confidence score - see DEFAULT_MIN_OCR_CONFIDENCE's docstring) --------


def test_translate_image_skips_region_below_min_confidence(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    regions = [
        OcrTextRegion(text="Real Text", x=20, y=20, width=150, height=24, confidence=90.0),
        OcrTextRegion(text="0 & Oo", x=20, y=70, width=60, height=18, confidence=22.0),
    ]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de", min_confidence=40.0,
    )

    assert stats.translated == 1
    assert stats.skipped == 1
    assert stats.failed == 0
    assert stats.processed == 2
    # The low-confidence region's text must never even reach the provider
    # - not just excluded from the final replacements.
    assert provider.calls == ["Real Text"]
    assert len(stats.replacements) == 1
    assert stats.replacements[0].region.text == "Real Text"


def test_translate_image_min_confidence_is_configurable(tmp_path: Path) -> None:
    """A caller that explicitly lowers min_confidence gets the borderline
    region translated instead of skipped - confirms the threshold is a
    real parameter, not a hardcoded cutoff."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    regions = [OcrTextRegion(text="Borderline", x=20, y=20, width=150, height=24, confidence=22.0)]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de", min_confidence=0.0,
    )

    assert stats.translated == 1
    assert stats.skipped == 0
    assert provider.calls == ["Borderline"]


# --- max_height_ratio skipping (RoadMap.md/Backlog.md 21.08.2026: real
# user-reported infographic where Tesseract folded a nearby icon/graphic
# element into a text line's bounding box, inflating just its height far
# beyond every other line in the same image - drawn oversized, these
# overlapped neighbouring boxes; several still scored above
# DEFAULT_MIN_OCR_CONFIDENCE, so the confidence filter alone didn't catch
# them - see DEFAULT_MAX_HEIGHT_RATIO's docstring) --------------------------


def test_translate_image_skips_region_with_outlier_height(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    regions = [
        OcrTextRegion(text="Real Text", x=20, y=20, width=150, height=24, confidence=90.0),
        OcrTextRegion(text="Other Real Text", x=20, y=60, width=150, height=22, confidence=90.0),
        # An icon merged into this "line" by Tesseract: height is far
        # beyond the other two regions', even though confidence is high.
        OcrTextRegion(text="Icon Blob", x=20, y=100, width=150, height=200, confidence=85.0),
    ]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de", min_confidence=40.0, max_height_ratio=3.5,
    )

    assert stats.translated == 2
    assert stats.skipped == 1
    assert stats.failed == 0
    # The outlier region's text must never even reach the provider.
    assert provider.calls == ["Real Text", "Other Real Text"]
    assert len(stats.replacements) == 2
    assert all(r.region.text != "Icon Blob" for r in stats.replacements)


def test_translate_image_max_height_ratio_is_configurable(tmp_path: Path) -> None:
    """A caller that explicitly raises max_height_ratio gets the tall
    region translated instead of skipped - confirms the threshold is a
    real parameter, not a hardcoded cutoff."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    regions = [
        OcrTextRegion(text="Real Text", x=20, y=20, width=150, height=24, confidence=90.0),
        OcrTextRegion(text="Tall Text", x=20, y=60, width=150, height=200, confidence=85.0),
    ]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de", min_confidence=40.0, max_height_ratio=100.0,
    )

    assert stats.translated == 2
    assert stats.skipped == 0
    assert provider.calls == ["Real Text", "Tall Text"]


def test_translate_image_height_outlier_check_ignores_low_confidence_regions(tmp_path: Path) -> None:
    """The median used for the height-outlier threshold is computed only
    from regions that already pass min_confidence - a low-confidence
    noise region's (possibly tiny) height must not skew that median."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    regions = [
        OcrTextRegion(text="Real Text", x=20, y=20, width=150, height=24, confidence=90.0),
        OcrTextRegion(text="Other Real Text", x=20, y=60, width=150, height=22, confidence=90.0),
        # Low confidence AND tiny height - skipped for confidence, not
        # height, and must not pull the median down further.
        OcrTextRegion(text="0 & Oo", x=20, y=95, width=30, height=5, confidence=10.0),
    ]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de", min_confidence=40.0, max_height_ratio=3.5,
    )

    assert stats.translated == 2
    assert stats.skipped == 1
    assert provider.calls == ["Real Text", "Other Real Text"]


def _make_replacement(text: str, translated_text: str) -> TextReplacement:
    region = OcrTextRegion(text=text, x=20, y=20, width=150, height=24, confidence=95.0)
    return TextReplacement(region=region, translated_text=translated_text)


def test_build_corrected_replacements_replaces_only_edited_rows() -> None:
    original = [
        _make_replacement("Hello World", "Hallo Welt"),
        _make_replacement("Second Line", "Zweite Zeile"),
    ]

    corrected = build_corrected_replacements(original, {0: "Hallo Welt (korrigiert)"})

    assert corrected[0].translated_text == "Hallo Welt (korrigiert)"
    assert corrected[0].region is original[0].region  # same region, only text changed
    # Untouched row passes through as the EXACT original object.
    assert corrected[1] is original[1]


def test_build_corrected_replacements_treats_unchanged_text_as_untouched() -> None:
    original = [_make_replacement("Hello World", "Hallo Welt")]

    corrected = build_corrected_replacements(original, {0: "Hallo Welt"})

    assert corrected[0] is original[0]


def test_build_corrected_replacements_ignores_out_of_range_index() -> None:
    original = [_make_replacement("Hello World", "Hallo Welt")]

    corrected = build_corrected_replacements(original, {5: "Egal"})

    assert corrected == original


# --- edited_geometry (RoadMap.md/Backlog.md 21.08.2026: the draggable/
# resizable box canvas in ImageCorrectionDialog - a real user asked for a
# way to move/resize individual boxes by hand after the automatic
# placement fixes still left a few in the wrong spot) --------------------


def test_build_corrected_replacements_applies_edited_geometry() -> None:
    original = [_make_replacement("Hello World", "Hallo Welt")]

    corrected = build_corrected_replacements(original, {}, edited_geometry={0: (30, 40, 200, 50)})

    region = corrected[0].region
    assert (region.x, region.y, region.width, region.height) == (30, 40, 200, 50)
    # Text/confidence must survive untouched - only geometry was edited.
    assert region.text == "Hello World"
    assert region.confidence == 95.0
    assert corrected[0].translated_text == "Hallo Welt"


def test_build_corrected_replacements_combines_text_and_geometry_edits_independently() -> None:
    original = [
        _make_replacement("Hello World", "Hallo Welt"),
        _make_replacement("Second Line", "Zweite Zeile"),
    ]

    corrected = build_corrected_replacements(
        original,
        {0: "Hallo Welt (korrigiert)"},  # row 0: text only
        edited_geometry={1: (10, 10, 100, 30)},  # row 1: geometry only
    )

    assert corrected[0].translated_text == "Hallo Welt (korrigiert)"
    assert corrected[0].region is original[0].region  # untouched geometry
    assert corrected[1].translated_text == "Zweite Zeile"  # untouched text
    assert (corrected[1].region.x, corrected[1].region.y) == (10, 10)


def test_build_corrected_replacements_geometry_none_keeps_old_behavior() -> None:
    original = [_make_replacement("Hello World", "Hallo Welt")]

    corrected = build_corrected_replacements(original, {0: "Hallo Welt"})

    assert corrected[0] is original[0]


def test_build_corrected_replacements_ignores_out_of_range_geometry_index() -> None:
    original = [_make_replacement("Hello World", "Hallo Welt")]

    corrected = build_corrected_replacements(original, {}, edited_geometry={5: (0, 0, 10, 10)})

    assert corrected == original


def test_translate_image_cancellation_stops_further_translation(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # cancel right after the first region is processed

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de", should_cancel=should_cancel,
    )

    assert stats.cancelled is True
    assert stats.translated == 1
    # Output is still written (inpainting_backend.apply() always runs at
    # the end, see translate_image()'s docstring) even though the run
    # was cancelled partway through.
    assert destination.exists()


def test_translate_image_propagates_ocr_error(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    with pytest.raises(OcrError):
        translate_image(
            str(source), str(destination), _StubFailingOcrEngine(), BoxOverlayBackend(),
            _FakeProvider(), [], target_lang="de",
        )
    assert not destination.exists()


def test_translate_image_invokes_progress_and_stats_callbacks(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    progress_messages: list[str] = []
    stats_snapshots: list[int] = []

    translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de",
        progress_callback=progress_messages.append,
        stats_callback=lambda stats: stats_snapshots.append(stats.translated),
    )

    assert len(progress_messages) == 2
    assert stats_snapshots == [1, 2]


def test_translate_image_respects_protected_terms(tmp_path: Path) -> None:
    """protect_terms()/restore_terms() must actually be wired in - a
    protected term must survive untranslated inside the (otherwise
    translated) region, mirroring translate_pdf()'s equivalent handling.
    """
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    stats = translate_image(
        str(source), str(destination), TesseractOcrEngine(), BoxOverlayBackend(),
        _FakeProvider(), ["World"], target_lang="de",
    )

    assert stats.translated == 2
    result_texts = [r.text for r in TesseractOcrEngine().recognize(str(destination))]
    assert any("World" in text for text in result_texts)
