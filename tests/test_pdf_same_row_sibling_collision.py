"""Regression coverage for a real bug found via a live user run against
"1526 VIRELICON.pdf" (see RoadMap.md Phase 2/PDF and Backlog.md): a
highlighted paragraph's last line ended with plain text, immediately
followed on the SAME visual row by a separately-styled short run ("2
ways:") that PyMuPDF reports as its own, separate raw block - both
highlighted, both sharing the quote's highlight-color background.

_next_block_y0() (used by PyMuPdfEngine._collision_aware_max_y1() to cap
how tall a block may grow before it would paint into the "next" block's
row) used to compare candidate blocks against the CURRENT block's own
bbox y0 ("is the other block's top below MY top?"), rather than its own
bbox y1 ("is the other block's top at or below MY OWN bottom?"). A
same-row sibling's own y0 sits INSIDE the current block's y-span (it's on
the same line, just further right), not below it - so the old check
wrongly treated it as "the next row down" and capped the growing block's
height BELOW its own original bottom edge. In the real document this
made a translated quote's text end up floating above its own
quote-highlight background (which was left empty/white, since the
now-too-small rect never triggered PyMuPdfEngine._grow_highlight_if_needed()'s
redraw) - confirmed directly via a real user's screenshots of the bug.

Reproduced here with a minimal synthetic PDF (mirrors
tests/test_pdf_overlay_collision.py's construction style) rather than the
confidential real document.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, _HIGHLIGHT_FILL_COLOR


def _build_same_row_sibling_pdf(path: Path) -> None:
    """A 3-line highlighted quote block whose third line ends around x=154,
    followed by a SEPARATE highlighted block ("TAIL") positioned at x
    250..340 but with a y-range that starts INSIDE the quote's own third
    line (y0=84, well before the quote's own bbox bottom at ~93.3) - the
    exact same-row-sibling shape confirmed in "1526 VIRELICON.pdf" (see
    this module's docstring). Both blocks are covered by one wide
    highlight-color rectangle, matching how both TextBlocks end up
    block.highlighted=True in the real document.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    highlight_rect = fitz.Rect(50, 50, 350, 101)
    page.draw_rect(highlight_rect, color=None, fill=_HIGHLIGHT_FILL_COLOR, width=0)
    page.insert_textbox(
        fitz.Rect(50, 50, 350, 95),
        "Quote first line here.\nQuote second line now.\nQuote third line ends",
        fontsize=10,
        fontname="helv",
    )
    page.insert_textbox(fitz.Rect(250, 84, 340, 101), "TAIL", fontsize=10, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_same_row_sibling_does_not_cap_growth_below_own_original_bottom(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _build_same_row_sibling_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = engine.extract_blocks(0)
    quote = next(b for b in blocks if "Quote" in b.text)
    tail = next(b for b in blocks if b.text == "TAIL")

    # Sanity: the fixture actually reproduces the same-row-sibling shape -
    # tail starts well before quote's own bbox ends.
    assert tail.bbox[1] < quote.bbox[3]

    max_y1, next_y0 = engine._collision_aware_max_y1(engine._doc[0], quote)

    # The real bug: max_y1 used to be capped at tail.bbox[1] - margin, i.e.
    # BELOW quote's own original bottom edge, shrinking its usable area
    # instead of ever growing it.
    assert max_y1 >= quote.bbox[3]


def test_same_row_sibling_highlighted_block_grows_with_background_intact(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_same_row_sibling_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = engine.extract_blocks(0)
    quote = next(b for b in blocks if "Quote" in b.text)
    original_bottom = quote.bbox[3]

    # Deliberately long enough to need real growth past the original box.
    long_html = "<p>" + (
        "A much longer translated line that needs several extra wrapped rows to fit fully. "
    ) * 4 + "</p>"

    engine.redact_block(quote)
    engine.insert_text(quote, "", quote.font_size, translated_html=long_html)
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]

    # The real bug's visible symptom: translated text ends up floating
    # above an empty (white) highlight box because the box was never
    # grown/redrawn to match. Sample a pixel comfortably past the
    # block's ORIGINAL bottom edge, inside its (now grown) text - it must
    # show the highlight fill color behind the text, not plain white.
    sample_y = original_bottom + 15  # a few lines further down, still inside the grown text
    pix = page.get_pixmap(clip=fitz.Rect(280, sample_y, 300, sample_y + 5))
    sample = pix.pixel(2, 2)
    highlight_rgb = tuple(round(c * 255) for c in _HIGHLIGHT_FILL_COLOR)
    assert sample == highlight_rgb
    result.close()
