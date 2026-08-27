"""Regression coverage for the OCR-Backend-Abstraktion (RoadMap.md Phase 3
- Bildübersetzung und OCR), pipeline/images/ocr.py.

Fixture images are rendered with a real TrueType font (DejaVuSans, present
on this system's fonts) rather than Pillow's tiny built-in bitmap default
font: confirmed by direct experimentation that the default font merges
"Hello World" into a single "Helloworld" word under Tesseract (too small/
tight for real character spacing), while DejaVuSans at a normal text size
recognizes each word separately with high confidence - the same class of
"reproduce the real shape, not a convenient shortcut" fixture-construction
care used throughout this project's PDF tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.images.ocr import (
    GoogleVisionOcrEngine,
    OcrError,
    OcrTextRegion,
    PaddleOcrEngine,
    TesseractOcrEngine,
    _is_decorative_symbol_token,
    google_vision_available,
    merge_lines_into_paragraphs,
    merge_region_group,
    paddleocr_available,
    region_line_height,
    tesseract_available,
)

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _build_two_line_image(path: Path) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Hello World", fill="black", font=font)
    draw.text((20, 70), "Second Line", fill="black", font=font)
    image.save(path)


def _build_blank_image(path: Path) -> None:
    Image.new("RGB", (200, 100), "white").save(path)


def _build_two_column_image(path: Path) -> None:
    """Two single words on the SAME visual row, far enough apart to
    simulate a two-column layout (a main content area + a right-hand
    sidebar box) - the shape that motivated _MAX_WORD_GAP_RATIO (see
    pipeline/images/ocr.py, RoadMap.md/Backlog.md 21.08.2026): without the
    gap-split, Tesseract's (block, par, line) grouping alone would glue
    "Left" and "Right" into one nonsensical "Left Right" region spanning
    the whole gap between them.
    """
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (600, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Left", fill="black", font=font)
    draw.text((420, 20), "Right", fill="black", font=font)
    image.save(path)


def test_tesseract_available_reflects_shutil_which(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipeline.images.ocr.shutil.which", lambda name: "/usr/bin/tesseract")
    assert tesseract_available() is True

    monkeypatch.setattr("pipeline.images.ocr.shutil.which", lambda name: None)
    assert tesseract_available() is False


def test_recognize_raises_ocr_error_when_tesseract_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The availability check must be consulted BEFORE ever touching
    pytesseract/the binary - a caller that skipped the UI-level
    availability gate still gets a clean OcrError, not a raw subprocess
    failure from pytesseract.
    """
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.tesseract_available", lambda: False)

    with pytest.raises(OcrError, match="Tesseract-Binary"):
        TesseractOcrEngine().recognize(str(source))


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_groups_words_into_reading_order_lines(tmp_path: Path) -> None:
    source = tmp_path / "two_lines.png"
    _build_two_line_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 2
    first, second = regions
    assert first.text == "Hello World"
    assert second.text == "Second Line"
    # Reading order: the "Hello World" line sits above "Second Line" in
    # the fixture (y=20 vs y=70) and must be returned first.
    assert first.y < second.y
    # Bounding boxes must be the union of both words on that line, not
    # just the first word's box.
    assert first.width > 50
    assert first.confidence > 0


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_returns_empty_list_for_blank_image(tmp_path: Path) -> None:
    source = tmp_path / "blank.png"
    _build_blank_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert regions == []


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_splits_words_far_apart_on_the_same_line(tmp_path: Path) -> None:
    """A wide horizontal gap between two words Tesseract put on the same
    (block, par, line) - the two-column-layout case - must yield TWO
    regions, not one giant one spanning the gap (see
    _build_two_column_image()'s docstring and _MAX_WORD_GAP_RATIO)."""
    source = tmp_path / "two_columns.png"
    _build_two_column_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 2
    first, second = regions
    assert first.text == "Left"
    assert second.text == "Right"
    # Left-to-right within the row, same as reading order elsewhere.
    assert first.x < second.x


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_accepts_language_hint(tmp_path: Path) -> None:
    """language=None must fall back to "eng" rather than raising - a
    caller-supplied language (e.g. "deu") is passed through to
    pytesseract unchanged.
    """
    source = tmp_path / "two_lines.png"
    _build_two_line_image(source)

    regions_default = TesseractOcrEngine().recognize(str(source))
    regions_explicit = TesseractOcrEngine().recognize(str(source), language="eng")

    assert [r.text for r in regions_default] == [r.text for r in regions_explicit]


# --- decorative-symbol-token filtering (real user, 22.08.2026: "Ich habe
# es hier mit echter Hardware getestet... Hier das Original und unsere
# Ausgabe" - a real infographic's icon/bullet graphics were misread by
# Tesseract as standalone symbol tokens ("©)", "@", "\_", "© *") and
# glued onto the FRONT of otherwise perfectly-readable headings/sentences,
# corrupting the translated, rendered output - see
# _DECORATIVE_SYMBOL_CHARS' docstring for the full real-image evidence
# this was calibrated against.) --------------------------------------


def _build_decorative_prefix_image(path: Path) -> None:
    """A checkbox-icon-style "©)" token immediately before a genuine
    heading - mirrors the real "©) NATURALLY COLLAPSES / ENDS" case
    exactly (same symbol, same position relative to the real text)."""
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (500, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "©) Genuine Heading", fill="black", font=font)
    image.save(path)


def _build_all_decorative_line_image(path: Path) -> None:
    """A line consisting ENTIRELY of decorative-symbol tokens (mirrors the
    real "© *" case) alongside one genuine, unrelated line - the
    decorative line must vanish entirely rather than surviving as an
    empty-ish region, while the real line is completely unaffected."""
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (500, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "© *", fill="black", font=font)
    draw.text((20, 70), "Real Sentence", fill="black", font=font)
    image.save(path)


def _build_mixed_symbol_word_image(path: Path) -> None:
    """A decorative symbol MIXED INTO a real word ("@Essence", mirrors the
    real "@SSence" case) - must NOT be touched by this filter (see
    _DECORATIVE_SYMBOL_CHARS' docstring: only a token that is PURELY
    decorative is dropped, never a partial one), a documented, deliberate
    non-fix."""
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (500, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "The @Essence remains", fill="black", font=font)
    image.save(path)


def test_is_decorative_symbol_token_true_for_pure_symbol_tokens() -> None:
    assert _is_decorative_symbol_token("©") is True
    assert _is_decorative_symbol_token("©)") is True
    assert _is_decorative_symbol_token("@") is True
    assert _is_decorative_symbol_token("*") is True
    assert _is_decorative_symbol_token("\\_") is True


def test_is_decorative_symbol_token_false_for_real_content() -> None:
    assert _is_decorative_symbol_token("Heading") is False
    assert _is_decorative_symbol_token("@Essence") is False
    assert _is_decorative_symbol_token("+") is False  # confirmed real bullet glyph, see docstring
    assert _is_decorative_symbol_token("/") is False
    assert _is_decorative_symbol_token(">") is False


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_strips_decorative_symbol_prefix_from_real_heading(tmp_path: Path) -> None:
    source = tmp_path / "decorative_prefix.png"
    _build_decorative_prefix_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 1
    assert regions[0].text == "Genuine Heading"
    assert "©" not in regions[0].text


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_drops_a_line_that_is_entirely_decorative_symbols(tmp_path: Path) -> None:
    source = tmp_path / "all_decorative.png"
    _build_all_decorative_line_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 1
    assert regions[0].text == "Real Sentence"


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")
def test_recognize_leaves_a_symbol_mixed_into_a_real_word_untouched(tmp_path: Path) -> None:
    """Documented non-fix (see _DECORATIVE_SYMBOL_CHARS' docstring): a
    decorative character glued INTO a word, not standing alone as its own
    token, is not this filter's job - confirms the filter stays scoped to
    whole-token matches rather than reaching into a word's characters."""
    source = tmp_path / "mixed_word.png"
    _build_mixed_symbol_word_image(source)

    regions = TesseractOcrEngine().recognize(str(source))

    assert len(regions) == 1
    assert "@Essence" in regions[0].text or "@ Essence" in regions[0].text


# --- merge_lines_into_paragraphs() / merge_region_group() (22.08.2026 -
# real user, after the obstacle_regions collision-avoidance fix was
# verified against a real densely-laid-out infographic and turned out NOT
# to be enough: "Ja, bitte [den] naechsten Punkt angehen." See
# merge_lines_into_paragraphs()'s own module-level docstring for the full
# diagnosis. Pure geometry, synthetic OcrTextRegion objects - no image/
# Tesseract needed, unlike most of this file, since the function only
# ever looks at bounding boxes.) ------------------------------------------


def _region(text: str, x: int, y: int, width: int, height: int, confidence: float = 90.0) -> OcrTextRegion:
    return OcrTextRegion(text=text, x=x, y=y, width=width, height=height, confidence=confidence)


def test_merge_lines_into_paragraphs_merges_a_tightly_wrapped_sentence() -> None:
    """The core real case: two lines of one sentence, same column, a
    small gap relative to their own height (single-line-spacing) -
    exactly the "Operates outside of time" / "and sequence." shape from
    the real image this was calibrated against."""
    first = _region("Operates outside of time", x=822, y=180, width=138, height=12)
    second = _region("and sequence.", x=837, y=196, width=71, height=12)  # gap=4, height ratio=1.0

    chains = merge_lines_into_paragraphs([first, second])

    assert chains == [[first, second]]


def test_merge_lines_into_paragraphs_does_not_merge_across_a_large_gap() -> None:
    """A gap at or above _PARAGRAPH_GAP_RATIO * height reads as a genuine
    new paragraph/bullet, not a wrapped continuation - must stay
    separate, mirrors the real image's "Sees the whole pattern," (new
    bullet, gap=13 on 12px-tall lines) starting its own chain rather than
    continuing the previous bullet."""
    first = _region("First bullet.", x=20, y=20, width=150, height=12)
    second = _region("Second bullet.", x=20, y=53, width=150, height=12)  # gap=21, ratio~1.75

    chains = merge_lines_into_paragraphs([first, second])

    assert chains == [[first], [second]]


def test_merge_lines_into_paragraphs_does_not_merge_different_columns() -> None:
    """No horizontal overlap at all - a different column/box entirely,
    however small the vertical gap - must never merge (mirrors
    _vertical_room_below()'s identical "same horizontal band" rule in
    pipeline.images.inpainting)."""
    left = _region("Left column line", x=20, y=20, width=150, height=12)
    right = _region("Right column line", x=400, y=32, width=150, height=12)  # gap=0, but x ranges don't overlap

    chains = merge_lines_into_paragraphs([left, right])

    assert chains == [[left], [right]]


def test_merge_lines_into_paragraphs_does_not_merge_different_font_sizes() -> None:
    """A heading immediately followed by a much smaller body line can have
    just as small an absolute gap as a real wrapped sentence - must NOT
    merge just because the gap is small; the real image's own "SPIRIT -
    SOUL » MEATSUIT" (height 37) immediately above "HOW THE CHALICE
    RESTORES..." (height 20, gap=13) was exactly this false-merge case
    before _PARAGRAPH_HEIGHT_RATIO_MIN was added."""
    heading = _region("A Big Heading", x=100, y=10, width=300, height=37)
    body = _region("a much smaller caption line", x=100, y=50, width=300, height=20)  # gap=3, tiny

    chains = merge_lines_into_paragraphs([heading, body])

    assert chains == [[heading], [body]]


def test_merge_lines_into_paragraphs_chains_three_or_more_lines() -> None:
    """A paragraph isn't limited to two lines - three (or more) tightly-
    wrapped lines in a row must all end up in ONE chain, in reading
    order."""
    first = _region("This is a long", x=20, y=20, width=150, height=12)
    second = _region("sentence that wraps", x=20, y=33, width=150, height=12)
    third = _region("across three lines.", x=20, y=46, width=150, height=12)

    chains = merge_lines_into_paragraphs([first, second, third])

    assert chains == [[first, second, third]]


def test_merge_lines_into_paragraphs_finds_a_continuation_despite_list_interleaving() -> None:
    """A real multi-column infographic's own reading order can interleave
    two columns' lines (confirmed in the real image this was calibrated
    against - see the module-level docstring) - a continuation must still
    be found by GEOMETRY even when it is not the next item in the input
    list."""
    right_first = _region("Right column first line", x=800, y=20, width=150, height=12)
    left_line = _region("Unrelated left column line", x=20, y=28, width=150, height=12)
    right_second = _region("right column continues", x=800, y=33, width=150, height=12)

    chains = merge_lines_into_paragraphs([right_first, left_line, right_second])

    assert [right_first, right_second] in chains
    assert [left_line] in chains


def test_merge_lines_into_paragraphs_every_region_appears_in_exactly_one_chain() -> None:
    first = _region("A", x=20, y=20, width=150, height=12)
    second = _region("B", x=20, y=33, width=150, height=12)
    third = _region("C", x=20, y=200, width=150, height=12)  # far away, own chain

    chains = merge_lines_into_paragraphs([first, second, third])

    flattened = [r for chain in chains for r in chain]
    assert sorted(id(r) for r in flattened) == sorted(id(r) for r in [first, second, third])


def test_merge_lines_into_paragraphs_handles_a_single_region() -> None:
    only = _region("Alone", x=20, y=20, width=150, height=12)
    assert merge_lines_into_paragraphs([only]) == [[only]]


def test_merge_lines_into_paragraphs_handles_an_empty_list() -> None:
    assert merge_lines_into_paragraphs([]) == []


def test_merge_lines_into_paragraphs_a_claimed_candidate_is_never_double_merged() -> None:
    """If two regions would both consider the SAME third region their
    nearest qualifying continuation, only the earlier one (in input
    order) claims it - the later one starts/ends its own chain instead,
    never leaving the candidate merged into two chains at once. Built by
    giving two same-width regions overlapping x-ranges with a common
    region below both of them, closer to the first."""
    first = _region("First claimant", x=20, y=20, width=200, height=12)
    second = _region("Second claimant", x=100, y=20, width=200, height=12)
    contested = _region("Contested continuation", x=20, y=33, width=280, height=12)

    chains = merge_lines_into_paragraphs([first, second, contested])

    # Every region still appears exactly once across all chains - no
    # region silently dropped or duplicated.
    flattened = [r for chain in chains for r in chain]
    assert sorted(id(r) for r in flattened) == sorted(id(r) for r in [first, second, contested])
    # And `contested` is claimed by at most one chain.
    chains_containing_contested = [c for c in chains if contested in c]
    assert len(chains_containing_contested) == 1


def test_merge_region_group_builds_the_union_bounding_box_and_joined_text() -> None:
    first = _region("Operates outside of time", x=822, y=180, width=138, height=12, confidence=90.0)
    second = _region("and sequence.", x=837, y=196, width=71, height=12, confidence=80.0)

    merged = merge_region_group([first, second])

    assert merged.text == "Operates outside of time and sequence."
    assert merged.x == 822
    assert merged.y == 180
    # union right edge is the wider of the two lines' own right edges
    assert merged.x + merged.width == max(822 + 138, 837 + 71)
    assert merged.y + merged.height == 196 + 12
    assert merged.confidence == pytest.approx(85.0)


def test_merge_region_group_sets_line_height_to_the_members_average_height_not_the_span() -> None:
    """The whole reason OcrTextRegion.line_height exists (22.08.2026, see
    that field's docstring): the merged block's `height` spans every
    member line together, but font-size estimation
    (pipeline.images.inpainting._initial_font_size()) must still seed
    from ONE line's height, not the full multi-line span."""
    first = _region("Line one", x=20, y=20, width=150, height=12)
    second = _region("line two", x=20, y=33, width=150, height=14)

    merged = merge_region_group([first, second])

    assert merged.height > 14  # spans both lines - taller than either member alone
    assert merged.line_height == 13  # average of 12 and 14, NOT the merged span


def test_merge_region_group_single_element_group_still_sets_line_height() -> None:
    """A singleton chain (no continuation found - the common case) still
    goes through merge_region_group() (see that function's docstring for
    why it's not special-cased) - line_height ends up equal to the one
    member's own height, height/x/y/width unchanged."""
    only = _region("Alone", x=20, y=20, width=150, height=24)

    merged = merge_region_group([only])

    assert merged.line_height == 24
    assert (merged.x, merged.y, merged.width, merged.height) == (20, 20, 150, 24)
    assert merged.text == "Alone"


# --- region_line_height() (23.08.2026) ------------------------------------


def test_region_line_height_prefers_line_height_when_set() -> None:
    region = OcrTextRegion(text="x", x=0, y=0, width=10, height=40, confidence=90.0, line_height=12)
    assert region_line_height(region) == 12


def test_region_line_height_falls_back_to_height_when_unset() -> None:
    region = _region("x", x=0, y=0, width=10, height=40)
    assert region_line_height(region) == 40


# --- GoogleVisionOcrEngine (23.08.2026) ------------------------------------
#
# Fixtures mirror the REAL Cloud Vision response shape (inspected directly
# via tools/probe_google_vision.py's saved JSON against the real
# "Spirit - Soul - Meatsuit.jpg", 23.08.2026 - see GoogleVisionOcrEngine's
# own docstring): responses[0].fullTextAnnotation.pages[0].blocks[].
# paragraphs[].words[].symbols[], boundingBox.vertices as {"x", "y"} dicts
# that OMIT a key entirely when that coordinate is 0.


class _FakeVisionResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self) -> dict:
        return self._payload


def _vision_word(text: str, x0: int, y0: int, x1: int, y1: int) -> dict:
    """One Vision `word` dict, one symbol per character - mirrors the real
    API's own per-character symbol granularity."""
    return {
        "boundingBox": {
            "vertices": [{"x": x0, "y": y0}, {"x": x1, "y": y0}, {"x": x1, "y": y1}, {"x": x0, "y": y1}]
        },
        "symbols": [{"text": char} for char in text],
    }


def _vision_paragraph(words: list[dict], x0: int, y0: int, x1: int, y1: int, confidence: float = 0.95) -> dict:
    return {
        "boundingBox": {
            "vertices": [{"x": x0, "y": y0}, {"x": x1, "y": y0}, {"x": x1, "y": y1}, {"x": x0, "y": y1}]
        },
        "confidence": confidence,
        "words": words,
    }


def _vision_response(paragraphs: list[dict]) -> dict:
    return {"responses": [{"fullTextAnnotation": {"pages": [{"blocks": [{"paragraphs": paragraphs}]}]}}]}


def test_google_vision_available_reflects_credential_presence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pipeline.credentials.get_google_translate_api_key", lambda: "a-key"
    )
    assert google_vision_available() is True

    def _raise() -> str:
        raise RuntimeError("no key")

    monkeypatch.setattr("pipeline.credentials.get_google_translate_api_key", _raise)
    assert google_vision_available() is False


def test_google_vision_recognize_raises_ocr_error_when_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: False)

    with pytest.raises(OcrError, match="API-Key"):
        GoogleVisionOcrEngine().recognize(str(source))


def test_google_vision_recognize_builds_one_region_per_paragraph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: True)
    monkeypatch.setattr("pipeline.credentials.get_google_translate_api_key", lambda: "a-key")

    words = [_vision_word("Hello", 10, 10, 60, 22), _vision_word("World", 65, 10, 115, 22)]
    payload = _vision_response([_vision_paragraph(words, 10, 10, 115, 22, confidence=0.9764)])

    def _fake_post(url, params, json, timeout):  # noqa: A002 - mirrors requests.post's own signature
        assert params == {"key": "a-key"}
        return _FakeVisionResponse(payload)

    monkeypatch.setattr("requests.post", _fake_post)

    regions = GoogleVisionOcrEngine().recognize(str(source))

    assert len(regions) == 1
    region = regions[0]
    assert region.text == "Hello World"
    assert (region.x, region.y, region.width, region.height) == (10, 10, 105, 12)
    assert region.confidence == pytest.approx(97.64, abs=0.01)
    assert region.line_height == 12  # both words' own boundingBox height


def test_google_vision_recognize_omits_x_or_y_key_at_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Vision's own protobuf-to-JSON encoding omits an `x`/`y` key
    entirely when that coordinate is exactly 0 - a region flush against
    the image's top-left edge must not crash or silently mis-place."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: True)
    monkeypatch.setattr("pipeline.credentials.get_google_translate_api_key", lambda: "a-key")

    word = {
        "boundingBox": {"vertices": [{"y": 0}, {"x": 40, "y": 0}, {"x": 40, "y": 12}, {"y": 12}]},
        "symbols": [{"text": char} for char in "Edge"],
    }
    paragraph = {
        "boundingBox": {"vertices": [{"y": 0}, {"x": 40, "y": 0}, {"x": 40, "y": 12}, {"y": 12}]},
        "confidence": 0.9,
        "words": [word],
    }
    payload = _vision_response([paragraph])
    monkeypatch.setattr("requests.post", lambda *a, **k: _FakeVisionResponse(payload))

    regions = GoogleVisionOcrEngine().recognize(str(source))

    assert len(regions) == 1
    assert (regions[0].x, regions[0].y) == (0, 0)


def test_google_vision_recognize_drops_decorative_symbol_only_words(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: True)
    monkeypatch.setattr("pipeline.credentials.get_google_translate_api_key", lambda: "a-key")

    words = [_vision_word("©", 5, 10, 20, 22), _vision_word("Essence", 25, 10, 95, 22)]
    payload = _vision_response([_vision_paragraph(words, 5, 10, 95, 22)])
    monkeypatch.setattr("requests.post", lambda *a, **k: _FakeVisionResponse(payload))

    regions = GoogleVisionOcrEngine().recognize(str(source))

    assert len(regions) == 1
    assert regions[0].text == "Essence"


def test_google_vision_recognize_raises_ocr_error_on_api_error_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: True)
    monkeypatch.setattr("pipeline.credentials.get_google_translate_api_key", lambda: "a-key")

    payload = {"responses": [{"error": {"code": 3, "message": "Vision API has not been used"}}]}
    monkeypatch.setattr("requests.post", lambda *a, **k: _FakeVisionResponse(payload))

    with pytest.raises(OcrError, match="Vision API has not been used"):
        GoogleVisionOcrEngine().recognize(str(source))


def test_google_vision_recognize_raises_ocr_error_on_request_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.google_vision_available", lambda: True)
    monkeypatch.setattr("pipeline.credentials.get_google_translate_api_key", lambda: "a-key")

    def _fake_post(*args, **kwargs):
        return _FakeVisionResponse({}, status_code=403)

    monkeypatch.setattr("requests.post", _fake_post)

    with pytest.raises(OcrError, match="Vision-API-Aufruf fehlgeschlagen"):
        GoogleVisionOcrEngine().recognize(str(source))


# --- PaddleOcrEngine (23.08.2026) -------------------------------------------
#
# Fixtures mirror the REAL PP-StructureV3 result shape (inspected directly
# via tools/probe_paddleocr.py's saved JSON against the real
# "Spirit - Soul - Meatsuit.jpg", 23.08.2026 - see PaddleOcrEngine's own
# docstring): result["parsing_res_list"] (block_label/block_content/
# block_bbox) and result["overall_ocr_res"] (rec_texts/rec_scores/
# rec_boxes, parallel lists) - both plain dicts here (the real result
# object is dict-LIKE, only .get()/indexing is ever used on it, see
# PaddleOcrEngine.recognize()), not the real paddlex result class.


class _FakePaddlePipeline:
    def __init__(self, result: dict) -> None:
        self._result = result

    def predict(self, image_path: str):
        return [self._result]


def _paddle_result(parsing_res_list: list[dict], overall_ocr_res: dict) -> dict:
    return {"parsing_res_list": parsing_res_list, "overall_ocr_res": overall_ocr_res}


def test_paddleocr_recognize_raises_ocr_error_when_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: False)

    with pytest.raises(OcrError, match="PaddleOCR ist nicht installiert"):
        PaddleOcrEngine().recognize(str(source))


def test_paddleocr_recognize_reattaches_spaced_ocr_lines_to_layout_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The core real finding this engine was built around: parsing_res_
    list's own block_content has no inter-word spaces
    ("HOWTHECHALICE...") - the engine must use overall_ocr_res's properly
    spaced per-line rec_texts instead, matched to each block by bounding-
    box containment."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        {"block_label": "doc_title", "block_content": "GLUEDTOGETHER", "block_bbox": [10, 10, 300, 60], "block_id": 0},
        {"block_label": "image", "block_content": "", "block_bbox": [10, 100, 300, 300], "block_id": 1},
    ]
    overall_ocr_res = {
        "rec_texts": ["SPIRIT · SOUL", "HOW THE CHALICE RESTORES"],
        "rec_scores": [0.99, 0.97],
        "rec_boxes": [[15.0, 12.0, 150.0, 30.0], [15.0, 35.0, 290.0, 55.0]],
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    regions = engine.recognize(str(source))

    assert len(regions) == 1  # the "image" block has no OCR line inside it, stays empty
    region = regions[0]
    assert region.text == "SPIRIT · SOUL HOW THE CHALICE RESTORES"
    assert (region.x, region.y, region.width, region.height) == (10, 10, 290, 50)
    assert region.confidence == pytest.approx(98.0, abs=0.01)
    assert region.line_height == 19  # average of (30-12)=18 and (55-35)=20


def test_paddleocr_recognize_handles_numpy_array_result_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for Michael's real crash (23.08.2026, manual test
    against "Spirit - Soul - Meatsuit.jpg"): "Uebersetzungslauf
    fehlgeschlagen: ValueError: The truth value of an array with more
    than one element is ambiguous. Use a.any() or a.all()".

    Root cause: on the REAL PP-StructureV3 pipeline, `rec_boxes`/
    `rec_scores` and `block_bbox` are numpy arrays, not plain Python
    lists - every fixture above uses plain lists and so never caught
    this. `x or []` / `not x` evaluate `bool(x)`, which numpy refuses
    for an array with more than one element. Fixed in
    _paddle_ocr_lines()/_paddle_block_to_region() by testing `is None`
    instead of relying on truthiness. This test rebuilds the fixture
    with numpy arrays (skipped if numpy is not installed - it ships
    transitively with opencv-python-headless/paddlepaddle, both already
    required for this feature, so it is expected to be present
    wherever this test actually matters)."""
    np = pytest.importorskip("numpy")
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        {
            "block_label": "doc_title",
            "block_content": "GLUEDTOGETHER",
            "block_bbox": np.array([10.0, 10.0, 300.0, 60.0]),
            "block_id": 0,
        },
    ]
    overall_ocr_res = {
        "rec_texts": ["SPIRIT · SOUL"],
        "rec_scores": np.array([0.99]),
        "rec_boxes": np.array([[15.0, 12.0, 150.0, 30.0]]),
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    regions = engine.recognize(str(source))  # must not raise

    assert len(regions) == 1
    assert regions[0].text == "SPIRIT · SOUL"


class _FakeLayoutBlock:
    """Mirrors the real PaddleX `LayoutBlock` object shape - fields as
    plain ATTRIBUTES under their OWN short names ("label"/"bbox"/
    "content"), no `.get()` and NOT the "block_*" names - confirmed
    23.08.2026 via tools/probe_paddleocr_shape.py's real output
    (`vars(parsing_res_list[0])` on Michael's machine included
    `{'label': 'doc_title', 'bbox': [138, 10, 909, 86],
    'content': 'SPIRIT...', ...}` - no "block_label"/"block_bbox"/
    "block_content"/"block_id" attribute exists at all). An EARLIER
    version of this fake (before that real data existed) wrongly used
    the "block_*" names themselves as the attribute names - which
    happened to make the first version of this test pass for the wrong
    reason, without catching the actual bug (see
    test_paddleocr_recognize_handles_attribute_based_layout_blocks()'s
    own docstring for how that surfaced as a second real crash: 0
    regions, no exception, because `getattr(block, "block_label", None)`
    silently returns None for the real object)."""

    def __init__(self, label: str, bbox, content: str = "") -> None:
        self.label = label
        self.bbox = bbox
        self.content = content


def test_paddleocr_recognize_handles_attribute_based_layout_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for Michael's SECOND and THIRD real crashes/bugs
    against the same fake-object shape (23.08.2026, same manual test,
    after the numpy fix above):

    1) "OcrError: PaddleOCR-Ergebnis konnte nicht verarbeitet werden:
       'LayoutBlock' object has no attribute 'get'" - `parsing_res_
       list`'s entries are objects, not dicts. Fixed via `_paddle_
       field()`, a small dict-or-attribute reader.
    2) No exception, but "Erkannte Textregionen: 0" - the FIRST version
       of `_paddle_field()` (and of this test's own `_FakeLayoutBlock`)
       assumed the object's attributes were named the same as the dict
       keys ("block_label" etc.) - real ground truth from
       tools/probe_paddleocr_shape.py showed they're actually named
       "label"/"bbox"/"content". `getattr(block, "block_label", None)`
       silently returned None for every block (no exception - only a
       lookup WITHOUT a default raises), so every block failed the
       `label in _PADDLE_TRANSLATABLE_LABELS` check and got skipped.
       Fixed via `_PADDLE_BLOCK_FIELD_ALIASES` in `_paddle_field()`.

    `overall_ocr_res`/`result` themselves DO support `.get()` even on
    the live object with their ORIGINAL key names (`rec_texts` etc. -
    confirmed again by tools/probe_paddleocr_shape.py's real output) -
    only `parsing_res_list`'s individual block entries have this
    dict-vs-attribute AND key-name-vs-attribute-name difference."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        _FakeLayoutBlock("doc_title", [10.0, 10.0, 300.0, 60.0], content="GLUEDTOGETHER"),
        _FakeLayoutBlock("image", [10.0, 100.0, 300.0, 300.0]),
    ]
    overall_ocr_res = {
        "rec_texts": ["SPIRIT · SOUL"],
        "rec_scores": [0.99],
        "rec_boxes": [[15.0, 12.0, 150.0, 30.0]],
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    regions = engine.recognize(str(source))  # must not raise

    assert len(regions) == 1  # the "image" block has no OCR line inside it, stays empty
    assert regions[0].text == "SPIRIT · SOUL"


def test_paddleocr_recognize_skips_a_block_with_no_matching_ocr_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        {"block_label": "text", "block_content": "x", "block_bbox": [500, 500, 600, 520], "block_id": 0},
    ]
    overall_ocr_res = {
        "rec_texts": ["Somewhere else entirely"],
        "rec_scores": [0.9],
        "rec_boxes": [[10.0, 10.0, 100.0, 30.0]],
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    assert engine.recognize(str(source)) == []


def test_paddleocr_recognize_translates_an_image_labeled_blocks_lines_individually(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fund 1 from Michael's QA-Bericht "(12)": "Einmal in der Mitte ganz
    links, da ist ein kompletter Teil gar nicht übersetzt." Root cause
    (24.08.2026, confirmed via tools/probe_paddleocr.py's real result
    JSON for "Spirit - Soul - Meatsuit.jpg"): PP-StructureV3 classified
    the whole "Thoughts/Emotions/.../recorded as PATTERNS" list as
    layout category "image" (probably because of the ledger/sphere
    graphic sharing the block) even though it genuinely contains
    recognized text. Four attempts now, across two days:

    1) (24.08.2026) Added "image" to _PADDLE_TRANSLATABLE_LABELS - DID
       translate it, but Michael's real next test (QA-Bericht "(13)")
       came back worse than before: _paddle_block_to_region() joins
       every matched OCR line into ONE paragraph and draws ONE text
       blob at the block's bbox - correct for real prose, but this
       block is 9 short, independent icon labels scattered around a
       graphic, not a paragraph. Joined and translated as one string
       they became one garbled blob overlapping the neighbouring
       banner block ("Version 13 ist schlechter als Version 12").
    2) (24.08.2026) Reverted "image" from the whitelist the same day,
       back to the original behaviour: the block, and every OCR line
       matched inside it, was dropped entirely BEFORE
       _paddle_block_to_region() even ran - it never became an
       OcrTextRegion at all.
    3) (24.08.2026) That turned out to be its own, WORSE regression
       (QA-Bericht "(15)", Michael: "Das ist jetzt noch schlimmer als
       das vorherige. Die Font stimmen gar nicht mehr usw."):
       translate_image.py's `obstacle_regions` collision-avoidance
       (built 22.08.2026) only protects regions that exist in
       `stats.regions` in the first place - since this block never
       became one, 23.08.2026's horizontal-reflow feature
       (pipeline.images.inpainting._horizontal_room()) saw "no
       obstacle there" and expanded NEIGHBOURING regions' text
       sideways straight over the block's still-visible English text.
       Fixed that day by returning the block as a `translatable=False`
       obstacle region instead of dropping it - stable, but left the
       list itself untranslated (Michael, 26.08.2026: "Wenn das als
       Bild gesehen wird, sollte das Bild doch auch extrahiert und
       übersetzbar sein.").
    4) (26.08.2026) The "richtiger Fix" attempt 1's own docstring
       already called for: keep the merged block as a
       `translatable=False` obstacle (protects the empty visual gaps
       BETWEEN the scattered labels, same as attempt 3), but ALSO
       return each of its matched OCR lines as its OWN small,
       independently translatable region at its OWN original position
       (_paddle_block_to_line_regions()) - avoids attempt 1's exact
       failure mode (one merged paragraph blob) since every line is
       now translated and drawn completely independently, the same way
       any ordinary text line elsewhere on the page is.

    See Backlog.md, 24.08.2026 and 26.08.2026, for the fuller writeup
    of all four attempts."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        {
            "block_label": "image",
            "block_content": "Thoughts\nEmotions\n...recorded as\nPATTERNS",
            "block_bbox": [25, 457, 394, 718],
            "block_id": 0,
        },
    ]
    overall_ocr_res = {
        "rec_texts": ["Thoughts", "Emotions", "...recorded as", "PATTERNS"],
        "rec_scores": [0.95, 0.94, 0.92, 0.96],
        "rec_boxes": [
            [30.0, 470.0, 110.0, 490.0],
            [30.0, 500.0, 110.0, 520.0],
            [30.0, 690.0, 150.0, 710.0],
            [30.0, 700.0, 120.0, 715.0],
        ],
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    regions = engine.recognize(str(source))

    # The merged block itself: still returned, still an obstacle, still
    # never translated directly - unchanged from attempt 3 (24.08.2026).
    block_region = next(r for r in regions if r.text == "Thoughts Emotions ...recorded as PATTERNS")
    assert block_region.translatable is False
    assert (block_region.x, block_region.y, block_region.width, block_region.height) == (25, 457, 369, 261)

    # NEW (26.08.2026): each of its 4 matched OCR lines is ALSO returned,
    # individually, as its own small translatable region at its own
    # original position - not joined into the blob above.
    line_texts = {r.text for r in regions if r.translatable}
    assert line_texts == {"Thoughts", "Emotions", "...recorded as", "PATTERNS"}
    thoughts = next(r for r in regions if r.text == "Thoughts")
    assert (thoughts.x, thoughts.y, thoughts.width, thoughts.height) == (30, 470, 80, 20)
    assert thoughts.confidence == pytest.approx(95.0)

    assert len(regions) == 5


def test_paddleocr_recognize_does_not_duplicate_a_line_already_claimed_by_a_translatable_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """26.08.2026 - found via the REAL result JSON for "Spirit - Soul -
    Meatsuit.jpg" (not a hypothetical): the "image" block's own bbox
    ([25,457,394,718]) slightly overlaps the neighbouring "paragraph_title"
    banner block's bbox ([333,457,733,476]) at its top-right corner - one
    real OCR line ("WHERE", bbox center at x=365/y=466) falls inside
    BOTH. Fixture reproduces that exact geometry (rounded).

    Before excluding already-claimed lines
    (_paddle_block_to_line_regions()'s `claimed_line_indices`), this
    "WHERE" line would have become a SECOND, independently translated and
    drawn region - directly on top of the banner's own already-correct
    translation of the same text, since the banner's own merged region
    already includes "WHERE" too (`_paddle_block_to_region()` matches by
    the same bounding-box-center rule, joining every line whose center
    falls inside ITS bbox - never de-duplicated against other blocks,
    since until now nothing else ever needed one line in two places)."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        {
            "block_label": "paragraph_title",
            "block_content": "WHEREEXPERIENCES,PATTERNS&DISTORTIONSLIVE",
            "block_bbox": [333, 457, 733, 476],
            "block_id": 0,
        },
        {
            "block_label": "image",
            "block_content": "WHERE \nThoughts",
            "block_bbox": [25, 457, 394, 718],
            "block_id": 1,
        },
    ]
    overall_ocr_res = {
        "rec_texts": ["WHEREEXPERIENCES,PATTERNS&DISTORTIONSLIVE", "WHERE", "Thoughts"],
        "rec_scores": [0.98, 0.996, 0.95],
        "rec_boxes": [
            [334.0, 458.0, 733.0, 476.0],  # banner's own line - matches ONLY the banner
            [336.0, 458.0, 395.0, 475.0],  # "WHERE" - center falls in BOTH blocks
            [30.0, 470.0, 110.0, 490.0],  # "Thoughts" - matches ONLY the image block
        ],
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    regions = engine.recognize(str(source))

    # The banner's own merged region keeps both its lines - unaffected.
    banner = next(r for r in regions if r.translatable and r.x == 333)
    assert banner.text == "WHEREEXPERIENCES,PATTERNS&DISTORTIONSLIVE WHERE"

    # "WHERE" must NOT ALSO appear as its own small region from the
    # image block's line-splitting - only "Thoughts" should.
    image_block_lines = [r for r in regions if r.translatable and r.x != 333]
    assert [r.text for r in image_block_lines] == ["Thoughts"]


def test_paddleocr_recognize_filters_a_stray_icon_glyph_misread_as_short_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fund 2 from the same QA-Bericht "(12)": "Das Kelch Symbol ...
    wird als 'UND' interpretiert." Root cause (24.08.2026, same real
    result JSON): PP-StructureV3's own line-level OCR misread the
    chalice icon between the two footer boxes as the single letter "Y"
    (real confidence 0.8409 - the translator apparently read it in
    context as the Spanish word for "and" and rendered "UND"). A
    second, previously unnoticed case in the same real run: a person
    icon in the "KEY TRUTH" box misread as the Chinese character "穴"
    (confidence 0.2849, the lowest of all 104 real OCR lines on that
    image) - unnoticed only because its block was labeled "image" and
    excluded wholesale before the fix above; it would have started
    rendering a mistranslated "穴" once "image" became translatable,
    without this filter. Both are 1 character and clearly below the
    confidence of any real text on that image (lowest genuine line:
    0.9111) - filtered by _PADDLE_STRAY_GLYPH_MAX_CHARS/_MIN_SCORE.
    A short but confident real line ("OR", 0.9817) must NOT be
    filtered."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    parsing_res_list = [
        {
            "block_label": "footer",
            "block_content": "The chalice icon area",
            "block_bbox": [460, 1240, 510, 1280],
            "block_id": 0,
        },
        {
            "block_label": "image",
            "block_content": "穴",
            "block_bbox": [740, 975, 790, 1025],
            "block_id": 1,
        },
        {
            "block_label": "paragraph_title",
            "block_content": "OR",
            "block_bbox": [540, 925, 570, 950],
            "block_id": 2,
        },
    ]
    overall_ocr_res = {
        "rec_texts": ["Y", "穴", "OR"],
        "rec_scores": [0.8409, 0.2849, 0.9817],
        "rec_boxes": [
            [471.97, 1243.36, 503.17, 1273.83],
            [755.0, 983.0, 779.0, 1016.0],
            [541.0, 930.0, 569.0, 950.0],
        ],
    }
    result = _paddle_result(parsing_res_list, overall_ocr_res)
    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _FakePaddlePipeline(result))

    regions = engine.recognize(str(source))

    # "Y" and "穴" filtered out -> their blocks have no matching OCR
    # line left and produce no region at all. "OR" (short, but high
    # confidence) survives.
    assert len(regions) == 1
    assert regions[0].text == "OR"


def test_paddleocr_recognize_wraps_inference_failure_in_ocr_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E.g. Backlog.md's real PaddlePaddle 3.3.x oneDNN/PIR regression - a
    run against an incompatible install must fail as a clean OcrError,
    not propagate a raw NotImplementedError."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    class _BrokenPipeline:
        def predict(self, image_path: str):
            raise NotImplementedError("ConvertPirAttribute2RuntimeAttribute not support ...")

    engine = PaddleOcrEngine()
    monkeypatch.setattr(engine, "_get_pipeline", lambda: _BrokenPipeline())

    with pytest.raises(OcrError, match="PaddleOCR-Erkennung fehlgeschlagen"):
        engine.recognize(str(source))


def test_paddleocr_pipeline_is_built_once_and_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PPStructureV3 is expensive to construct (loads several ML models) -
    _get_pipeline() must cache it on the instance rather than rebuild it
    on every recognize() call (see PaddleOcrEngine's own docstring)."""
    source = tmp_path / "irrelevant.png"
    _build_blank_image(source)
    monkeypatch.setattr("pipeline.images.ocr.paddleocr_available", lambda: True)

    result = _paddle_result([], {"rec_texts": [], "rec_scores": [], "rec_boxes": []})
    build_calls: list[int] = []

    class _FakePaddleOcrModule:
        @staticmethod
        def PPStructureV3(**kwargs):
            build_calls.append(1)
            return _FakePaddlePipeline(result)

    monkeypatch.setitem(sys.modules, "paddleocr", _FakePaddleOcrModule)

    engine = PaddleOcrEngine()
    engine.recognize(str(source))
    engine.recognize(str(source))

    assert len(build_calls) == 1
