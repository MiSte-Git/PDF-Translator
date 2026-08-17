"""Regression coverage for the "Leerzeilen/Underline/Inline-Formatierung"
item tracked as open in RoadMap.md Phase 2/PDF - spans_to_html() (which
turns a TextBlock's spans into the HTML fed to page.insert_htmlbox(), see
PyMuPdfEngine.insert_text()'s docstring) had zero direct test coverage
before this file, despite being the piece responsible for whether blank
lines (paragraph breaks), <u>/<b>/<i> nesting, and heading/body line
breaks survive being written back out.

Covers two levels:
  - spans_to_html() in isolation: pure function, deterministic, exercises
    marker handling (PARAGRAPH_BREAK_MARKER/LINE_BREAK_MARKER) and
    underline/bold/italic tag nesting/escaping directly against its
    return value.
  - An end-to-end round trip through PyMuPdfEngine.redact_block()/
    insert_text()/save(): hand-built TextSpans (underline=True, mixed
    bold/italic, a PARAGRAPH_BREAK_MARKER) are inserted via
    page.insert_htmlbox(), then the OUTPUT is re-extracted via
    PyMuPdfEngine.extract_blocks() (the same code a later re-translation
    run would use) to confirm the underline/bold/italic flags and the
    paragraph gap are still detectable afterward, not just visually
    present. Note: extract_blocks()'s underline detection needs
    page.get_text(..., flags=_EXTRACT_FLAGS) (TEXT_COLLECT_STYLES) - an
    earlier ad-hoc check against plain get_text("dict") without that flag
    gave a false negative for underline, which is why this file always
    goes through extract_blocks() rather than reading span dicts by hand.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from pipeline.pdf.base import LINE_BREAK_MARKER, PARAGRAPH_BREAK_MARKER, TextBlock, TextSpan
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html


def _span(text: str, *, bold: bool = False, italic: bool = False, underline: bool = False) -> TextSpan:
    return TextSpan(
        text=text, font_name="helv", font_size=11, color=(0, 0, 0),
        bold=bold, italic=italic, underline=underline,
    )


def _marker(marker_text: str) -> TextSpan:
    return TextSpan(text=marker_text, font_name="", font_size=0.0, color=(0, 0, 0), bold=False, italic=False, underline=False)


def test_spans_to_html_wraps_underline_bold_italic_nested_correctly() -> None:
    spans = [_span("Hello ", bold=True), _span("world", bold=True, italic=True, underline=True)]
    assert spans_to_html(spans) == "<p><b>Hello </b><b><i><u>world</u></i></b></p>"


def test_spans_to_html_paragraph_break_marker_starts_a_new_p() -> None:
    spans = [_span("First paragraph."), _marker(PARAGRAPH_BREAK_MARKER), _span("Second paragraph.")]
    assert spans_to_html(spans) == "<p>First paragraph.</p><p>Second paragraph.</p>"


def test_spans_to_html_line_break_marker_becomes_br_within_same_p() -> None:
    spans = [_span("Heading", bold=True), _marker(LINE_BREAK_MARKER), _span("Body text.")]
    assert spans_to_html(spans) == "<p><b>Heading</b><br/>Body text.</p>"


def test_spans_to_html_escapes_html_special_characters() -> None:
    spans = [_span("A & B <tag> \"quoted\"")]
    html = spans_to_html(spans)
    assert "&amp;" in html
    assert "&lt;tag&gt;" in html
    assert "<tag>" not in html


def test_spans_to_html_drops_a_trailing_or_leading_blank_paragraph() -> None:
    # _build_text_spans() already avoids emitting a leading/trailing marker
    # (see its docstring) - spans_to_html() must not reintroduce an empty
    # <p></p> even if one slips through some other caller.
    spans = [_marker(PARAGRAPH_BREAK_MARKER), _span("Only paragraph."), _marker(PARAGRAPH_BREAK_MARKER)]
    assert spans_to_html(spans) == "<p>Only paragraph.</p>"


def test_underline_bold_italic_and_paragraph_gap_survive_a_full_engine_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"

    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 90), "placeholder", fontsize=11, fontname="helv")
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = TextBlock(
        page_index=0, bbox=(50, 50, 350, 200), text="placeholder",
        font_name="helv", font_size=11, color=(0, 0, 0), bold=False, italic=False,
        spans=[
            _span("Underlined heading", bold=True, underline=True),
            _marker(PARAGRAPH_BREAK_MARKER),
            _span("Second paragraph with "),
            _span("italic", italic=True),
            _span(" text."),
        ],
    )
    engine.redact_block(block)
    engine.insert_text(block, "", block.font_size, translated_html=spans_to_html(block.spans))
    engine.save(str(output))

    out_engine = PyMuPdfEngine()
    out_engine.open(str(output))
    extracted = out_engine.extract_blocks(0)
    full_text = "\n".join(b.text for b in extracted)

    assert "Underlined heading" in full_text
    assert "Second paragraph with" in full_text
    assert "italic" in full_text

    all_spans = [span for b in extracted for span in b.spans]
    underlined = [s for s in all_spans if s.text.strip() and "Underlined heading" in s.text]
    assert underlined and all(s.underline and s.bold for s in underlined)

    italic_spans = [s for s in all_spans if s.text.strip() == "italic"]
    assert italic_spans and all(s.italic for s in italic_spans)

    # A real paragraph break (blank line) between the two paragraphs must
    # still be detectable as such after the round trip - either as its own
    # PARAGRAPH_BREAK_MARKER span within one block, or (just as validly,
    # since it depends on how far apart insert_htmlbox() actually laid the
    # two <p>s out) as two separate blocks/paragraphs.
    has_marker_span = any(s.text == PARAGRAPH_BREAK_MARKER for s in all_spans)
    has_two_blocks = len(extracted) >= 2
    assert has_marker_span or has_two_blocks
