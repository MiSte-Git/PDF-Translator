"""Regression coverage for a real bug found via a live user run against
"1526 VIRELICON.pdf": several short, single-line blocks rendered in a
visibly smaller font than their neighbors after translation - down to
_MIN_FONT_SIZE (6pt) vs. the document's normal ~11pt body text.

The user's own observation was the key correction here: the ORIGINAL
boxes for these blocks are completely ordinary - one line of normal
single-line-spaced text, nothing unusually tight about the source layout.
The actual root cause was in PyMuPdfEngine._insert_html_text()'s CSS:
spans_to_html() always wraps every paragraph in <p>...</p> (even a
single-line block with no paragraph breaks gets one <p>), and a
translation provider's HTML response preserves that structure. PyMuPDF's
Story/CSS engine reserves extra margin/line-height space for a <p>
element that the growth logic (_estimate_line_height()-based height
steps, then width) doesn't know about - confirmed by direct
reproduction: for a tight, single-line original box, a translation only
slightly longer than the English original NEVER fit no matter how far
the width was grown (even at the full page width), purely because of
this reserved <p> space, not genuine lack of room. That forced a shrink
through every step down to the font floor.

Fixed via _insert_html_css()'s `p {margin:0; line-height:1;}` reset. A
`p + p {margin-top: ...}` sibling rule restores just enough of that
margin between two ACTUAL sibling paragraphs within one block (a real
paragraph break) so a genuine multi-paragraph gap doesn't collapse -
see tests/test_pdf_formatting_roundtrip.py's existing round-trip
coverage for that side, still passing unchanged.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine


def _build_tight_single_line_pdf(path: Path) -> None:
    """One ordinary, single-line block near the page's bottom-right corner -
    normal single-line spacing, nothing unusually cramped about the text
    itself (matches the user's own observation about the real document's
    layout at the affected spots), but positioned so growth room on both
    axes is small: only ~10pt of height growth before hitting
    _max_rect_y1()'s footer/page-edge cap, and ~44pt of width growth
    before max_x1. Without the CSS reset, the reserved <p> margin/
    line-height eats that little bit of slack and still doesn't fit,
    forcing a shrink; with the reset, the same slightly-longer text fits
    at the original font size. (A block with generous growth room in
    every direction - as an isolated single block on a big page has by
    default - never reaches the shrink path at all, reset or not, which
    is why this specific tight-corner placement matters for reproducing
    the bug.)
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(300, 470, 395, 495), "Short line", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_longer_translation_of_a_short_line_does_not_shrink_the_font(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_tight_single_line_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = engine.extract_blocks(0)[0]
    original_font_size = block.font_size

    # Longer than the English original (mirrors German typically running
    # ~20-30% longer) - the point being this must still fit at the
    # original font size once growth (small as it is, here) is applied;
    # any shrink below the original font size would be the bug, not
    # physics, since the confirmed-working fix fits this exact case.
    long_translation = "<p>Etwas längere Zeile</p>"
    engine.redact_block(block)
    engine.insert_text(block, "", original_font_size, translated_html=long_translation)
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]
    raw = page.get_text("dict")
    sizes = [
        span["size"]
        for b in raw["blocks"]
        if b.get("type") == 0
        for line in b["lines"]
        for span in line["spans"]
        if span["text"].strip()
    ]
    assert sizes
    # No shrinking at all - the translation must fit at the block's own
    # original font size via width growth alone.
    assert all(size >= original_font_size - 0.01 for size in sizes)
    result.close()


def test_multi_paragraph_gap_within_one_block_still_visible(tmp_path: Path) -> None:
    """The margin:0 reset must not collapse a REAL paragraph break (two
    separate <p>s from one block, e.g. from spans_to_html()'s
    PARAGRAPH_BREAK_MARKER handling) into a single run-on paragraph - see
    _insert_html_css()'s p+p sibling rule.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 200), "placeholder", fontsize=11, fontname="helv")
    source = tmp_path / "source.pdf"
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = engine.extract_blocks(0)[0]

    two_paragraphs = "<p>First paragraph text here.</p><p>Second paragraph text here.</p>"
    engine.redact_block(block)
    engine.insert_text(block, "", block.font_size, translated_html=two_paragraphs)
    output = tmp_path / "output.pdf"
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]
    raw = page.get_text("dict")
    text_blocks = sorted(
        (b for b in raw["blocks"] if b.get("type") == 0), key=lambda b: b["bbox"][1]
    )
    assert len(text_blocks) == 2
    gap = text_blocks[1]["bbox"][1] - text_blocks[0]["bbox"][3]
    # A real, visible gap - not the near-zero (or negative/overlapping)
    # spacing a blanket margin:0 with no sibling rule would produce.
    assert gap > 3.0
    result.close()
