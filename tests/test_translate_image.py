"""Regression coverage for pipeline/images/translate_image.py (RoadMap.md
Phase 3 - Bildübersetzung und OCR): the OCR -> Übersetzung -> Rückschreibung
loop, independent of ui/image_job.py's file-handling/QA-report layer around
it (mirrors how tests/test_pdf_ico_mode.py separates engine-level from
job-level coverage).
"""
from __future__ import annotations

import dataclasses
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
    # "block", not "region" (22.08.2026: a failed provider call now marks
    # a whole merge_lines_into_paragraphs() group as failed, which may
    # span more than one original OCR region - see translate_image()'s
    # docstring).
    assert "block" in stats.errors[0]
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


def test_translate_image_height_outlier_check_ignores_untranslatable_regions(tmp_path: Path) -> None:
    """24.08.2026 - same reasoning as the low-confidence test above, for
    the OTHER kind of region excluded from translation: a `translatable
    =False` region (see that field's docstring) is typically a whole
    graphic-heavy layout block with a much larger bounding box than a
    real text line's - e.g. PaddleOcrEngine's "Thoughts/Emotions/..."
    "image" block is 261px tall against ~20px real text lines on the
    same image. Its height must not pull the median (and therefore the
    outlier threshold) up, or genuinely bad OCR reads elsewhere on the
    same image would slip past the height filter."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    regions = [
        OcrTextRegion(text="Real Text", x=20, y=20, width=150, height=24, confidence=90.0),
        OcrTextRegion(text="Other Real Text", x=20, y=60, width=150, height=22, confidence=90.0),
        # High confidence, but excluded from translation - a large,
        # genuine layout block, not a text line. Must not raise the
        # median used to judge the icon-blob outlier below.
        OcrTextRegion(
            text="Thoughts Emotions ...recorded as PATTERNS",
            x=20, y=95, width=369, height=261, confidence=95.0, translatable=False,
        ),
        # An icon merged into this "line", same as
        # test_translate_image_skips_region_with_outlier_height above.
        OcrTextRegion(text="Icon Blob", x=20, y=400, width=150, height=200, confidence=85.0),
    ]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de", min_confidence=40.0, max_height_ratio=3.5,
    )

    assert stats.translated == 2
    assert stats.skipped == 2  # the untranslatable region + the icon-blob outlier
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


# --- obstacle_regions (22.08.2026 - real user, same real infographic +
# GPU-Inpainting qa_report.txt that motivated the qa_report.txt settings
# fix: "Boxen überlappen oder sind an falscher Stelle". This is the
# translate_image()-level half of the fix - the OTHER half being
# InpaintingBackend.apply()'s new parameter itself, covered in
# tests/test_image_inpainting.py/tests/test_image_cv_inpainting.py. These
# tests confirm translate_image() actually COMPUTES and PASSES the right
# set of regions - every region OCR recognized that is NOT in
# stats.replacements (skipped, failed, or never reached because
# should_cancel fired first), regardless of which of those three reasons
# applies - without depending on font/pixel rendering at all.) -----------


class _RecordingBackend:
    """Fake InpaintingBackend that just records the exact arguments its
    apply() was called with, once - lets these tests assert on the
    obstacle_regions list translate_image() computed without needing a
    real image/font-rendering round-trip (that's what
    tests/test_image_inpainting.py's obstacle_regions tests are for)."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[TextReplacement], list[OcrTextRegion] | None]] = []

    def apply(
        self,
        image_path: str,
        replacements: list[TextReplacement],
        output_path: str,
        obstacle_regions: list[OcrTextRegion] | None = None,
    ) -> None:
        self.calls.append((replacements, obstacle_regions))
        Path(output_path).write_bytes(Path(image_path).read_bytes())


def test_translate_image_passes_skipped_region_as_an_obstacle(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    low_confidence_region = OcrTextRegion(text="0 & Oo", x=20, y=70, width=60, height=18, confidence=22.0)
    regions = [
        OcrTextRegion(text="Real Text", x=20, y=20, width=150, height=24, confidence=90.0),
        low_confidence_region,
    ]
    backend = _RecordingBackend()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), backend,
        _CountingProvider(), [], target_lang="de", min_confidence=40.0,
    )

    assert stats.skipped == 1
    [(replacements, obstacle_regions)] = backend.calls
    # merge_region_group() (22.08.2026) always rebuilds a fresh
    # OcrTextRegion, even for a singleton group - same content as
    # regions[0], but with line_height now set (see that field's
    # docstring), so compare via dataclasses.replace() rather than
    # identity/equality against the original object.
    assert len(replacements) == 1
    assert replacements[0].region == dataclasses.replace(regions[0], line_height=regions[0].height)
    assert obstacle_regions == [low_confidence_region]


def test_translate_image_passes_failed_region_as_an_obstacle(tmp_path: Path) -> None:
    """A region the PROVIDER rejected (TranslationError) never reaches
    stats.replacements either, and its original pixels are just as
    visible in the output as a skipped region's - must be an obstacle
    too, not just the confidence-filtered kind."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    failing_region = OcrTextRegion(text="Second Line", x=20, y=70, width=150, height=24, confidence=90.0)
    regions = [
        OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=90.0),
        failing_region,
    ]
    backend = _RecordingBackend()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), backend,
        _SelectiveFailProvider(fail_text="Second Line"), [], target_lang="de",
    )

    assert stats.failed == 1
    [(replacements, obstacle_regions)] = backend.calls
    assert len(replacements) == 1
    assert replacements[0].region == dataclasses.replace(regions[0], line_height=regions[0].height)
    assert obstacle_regions == [failing_region]


def test_translate_image_passes_cancelled_remainder_as_obstacles(tmp_path: Path) -> None:
    """A region should_cancel() stops translate_image() from ever
    reaching is neither skipped nor failed in the stats sense - but it's
    just as untouched/original in the output, so it must be an obstacle
    too."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    never_reached_region = OcrTextRegion(text="Second Line", x=20, y=70, width=150, height=24, confidence=90.0)
    regions = [
        OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=90.0),
        never_reached_region,
    ]
    backend = _RecordingBackend()
    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), backend,
        _CountingProvider(), [], target_lang="de", should_cancel=should_cancel,
    )

    assert stats.cancelled is True
    assert stats.translated == 1
    [(replacements, obstacle_regions)] = backend.calls
    assert len(replacements) == 1
    assert replacements[0].region == dataclasses.replace(regions[0], line_height=regions[0].height)
    assert obstacle_regions == [never_reached_region]


def test_translate_image_passes_untranslatable_region_as_an_obstacle_and_never_sends_it(tmp_path: Path) -> None:
    """24.08.2026 - real-world regression (QA-Bericht "(15)", Michael:
    "Das ist jetzt noch schlimmer als das vorherige. Die Font stimmen
    gar nicht mehr usw."): PaddleOcrEngine can now return a region with
    `translatable=False` (see that field's docstring - a label-
    excluded-but-real-text layout block, e.g. an "image"-labeled
    block). Before this fix such a block simply never became a region
    at all, which meant it was invisible to the very obstacle_regions
    mechanism the three tests above exist to cover - a neighbouring
    region's horizontal reflow (pipeline.images.inpainting.
    _horizontal_room()) could then expand straight over its still-
    visible original text. Must never reach the translation provider
    (_CountingProvider records every text it actually saw - asserted
    below) and must still end up in obstacle_regions, exactly like a
    low-confidence or failed region."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    untranslatable_region = OcrTextRegion(
        text="Thoughts Emotions ...recorded as PATTERNS",
        x=20, y=70, width=150, height=24, confidence=95.0, translatable=False,
    )
    regions = [
        OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=90.0),
        untranslatable_region,
    ]
    backend = _RecordingBackend()
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine(regions), backend,
        provider, [], target_lang="de",
    )

    assert stats.skipped == 1
    assert stats.translated == 1
    assert provider.calls == ["Hello World"]  # the untranslatable region's text never sent
    [(replacements, obstacle_regions)] = backend.calls
    assert len(replacements) == 1
    assert replacements[0].region == dataclasses.replace(regions[0], line_height=regions[0].height)
    assert obstacle_regions == [untranslatable_region]


def test_translate_image_obstacle_regions_empty_when_everything_translated(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"
    backend = _RecordingBackend()

    translate_image(
        str(source), str(destination), TesseractOcrEngine(), backend,
        _FakeProvider(), [], target_lang="de",
    )

    [(_replacements, obstacle_regions)] = backend.calls
    assert obstacle_regions == []


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


# --- paragraph merging (22.08.2026 - real user, after obstacle_regions
# was verified against a real densely-laid-out infographic and turned out
# NOT to be enough: "Ja, bitte [den] naechsten Punkt angehen." See
# pipeline.images.ocr.merge_lines_into_paragraphs()'s module-level
# docstring for the full diagnosis. These tests confirm translate_image()
# itself actually FEEDS eligible regions through the merge step and
# handles the resulting groups correctly - merge_lines_into_paragraphs()/
# merge_region_group()'s own geometry is covered directly in
# tests/test_image_ocr.py.) ------------------------------------------------


def test_translate_image_merges_a_tightly_wrapped_sentence_into_one_translation_call(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    first = OcrTextRegion(text="Operates outside of time", x=20, y=20, width=150, height=12, confidence=90.0)
    second = OcrTextRegion(text="and sequence.", x=25, y=32, width=90, height=12, confidence=90.0)  # gap=0
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine([first, second]), BoxOverlayBackend(),
        provider, [], target_lang="de",
    )

    # ONE provider call with the JOINED text - not two independent calls.
    assert provider.calls == ["Operates outside of time and sequence."]
    assert stats.translated == 2  # counted in original-line units, not groups
    assert len(stats.replacements) == 1
    assert stats.replacements[0].region.text == "Operates outside of time and sequence."


def test_translate_image_does_not_merge_two_unrelated_far_apart_regions(tmp_path: Path) -> None:
    """Baseline/control - confirms the merge test above is actually
    exercising the merge path and not just an artifact of _StubOcrEngine:
    the SAME two-region shape used throughout this file's other tests
    (far apart, same as _build_two_line_image's real layout) must still
    translate as two independent calls."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    first = OcrTextRegion(text="Hello World", x=20, y=20, width=150, height=24, confidence=90.0)
    second = OcrTextRegion(text="Second Line", x=20, y=70, width=150, height=24, confidence=90.0)
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine([first, second]), BoxOverlayBackend(),
        provider, [], target_lang="de",
    )

    assert sorted(provider.calls) == ["Hello World", "Second Line"]
    assert len(stats.replacements) == 2


def test_translate_image_a_failed_merged_group_marks_every_member_line_failed(tmp_path: Path) -> None:
    """When the ONE provider call for a merged group raises, every
    ORIGINAL line in that group counts as failed (not just one) - each
    of their original pixels is equally still visible in the output, so
    stats.failed (and, via translate_image()'s obstacle_regions
    computation, collision avoidance) must reflect all of them."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    first = OcrTextRegion(text="Operates outside of time", x=20, y=20, width=150, height=12, confidence=90.0)
    second = OcrTextRegion(text="and sequence.", x=25, y=32, width=90, height=12, confidence=90.0)
    provider = _SelectiveFailProvider(fail_text="Operates outside of time and sequence.")

    stats = translate_image(
        str(source), str(destination), _StubOcrEngine([first, second]), BoxOverlayBackend(),
        provider, [], target_lang="de",
    )

    assert stats.failed == 2
    assert stats.translated == 0
    assert stats.replacements == []


class _StubParagraphOcrEngine:
    """Like _StubOcrEngine above, but with returns_paragraph_regions =
    True - lets the tests below assert translate_image()'s "skip
    merge_lines_into_paragraphs() for an engine that already returns
    paragraph-level regions" branch (23.08.2026, GoogleVisionOcrEngine/
    PaddleOcrEngine) without depending on either real engine/network."""

    returns_paragraph_regions = True

    def __init__(self, regions: list[OcrTextRegion]) -> None:
        self._regions = regions

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        return self._regions


def test_translate_image_skips_merge_for_an_engine_that_returns_paragraph_regions(tmp_path: Path) -> None:
    """Two regions that merge_lines_into_paragraphs() WOULD merge (same
    column, tiny gap, same height - the identical shape
    test_image_ocr.py's own merge test uses) must NOT be merged when the
    engine itself already returns paragraph-level regions - each stays
    its own translation call/replacement."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    first = OcrTextRegion(text="Operates outside of time", x=822, y=180, width=138, height=12, confidence=90.0)
    second = OcrTextRegion(text="and sequence.", x=837, y=196, width=71, height=12, confidence=90.0)
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubParagraphOcrEngine([first, second]), BoxOverlayBackend(),
        provider, [], target_lang="de",
    )

    assert sorted(provider.calls) == ["Operates outside of time", "and sequence."]
    assert len(stats.replacements) == 2


def test_translate_image_preserves_engine_supplied_line_height_for_paragraph_regions(tmp_path: Path) -> None:
    """merge_region_group() would RECOMPUTE line_height from the group's
    own `height` (its own docstring: built for single-line Tesseract
    regions) - for a returns_paragraph_regions engine, that recomputation
    must be skipped entirely so the engine's own, already-correct
    line_height (e.g. GoogleVisionOcrEngine's word-height average)
    survives unchanged into the final replacement."""
    source = tmp_path / "source.png"
    _build_two_line_image(source)
    destination = tmp_path / "out.png"

    region = OcrTextRegion(
        text="A whole paragraph", x=10, y=10, width=200, height=40, confidence=90.0, line_height=12
    )

    stats = translate_image(
        str(source), str(destination), _StubParagraphOcrEngine([region]), BoxOverlayBackend(),
        _FakeProvider(), [], target_lang="de",
    )

    assert len(stats.replacements) == 1
    assert stats.replacements[0].region.line_height == 12
    assert stats.replacements[0].region.height == 40


def test_translate_image_height_outlier_check_uses_line_height_for_paragraph_regions(tmp_path: Path) -> None:
    """A legitimate multi-line paragraph block (large `height`, normal
    `line_height`) must not be mistaken for an icon-inflated outlier -
    the median/outlier check (DEFAULT_MAX_HEIGHT_RATIO) must compare
    region_line_height(), not raw `height`, for exactly this reason: this
    block's raw height (200) is 10x a normal ~20px line, far past the
    default 4x ratio, but its line_height (20) is unremarkable."""
    source = tmp_path / "source.png"
    # Taller than _build_two_line_image()'s canvas (150px) - the
    # (y=200, height=200) paragraph region below must fit fully inside
    # the image for InpaintingBackend.apply()'s background sampling.
    Image.new("RGB", (400, 450), "white").save(source)
    destination = tmp_path / "out.png"

    regions = [
        OcrTextRegion(text=f"Line {i}", x=10, y=10 + i * 30, width=100, height=20, confidence=90.0)
        for i in range(3)
    ] + [
        OcrTextRegion(
            text="A big paragraph block", x=10, y=200, width=200, height=200, confidence=90.0, line_height=20,
        )
    ]
    provider = _CountingProvider()

    stats = translate_image(
        str(source), str(destination), _StubParagraphOcrEngine(regions), BoxOverlayBackend(),
        provider, [], target_lang="de",
    )

    assert stats.skipped == 0
    assert "A big paragraph block" in provider.calls
