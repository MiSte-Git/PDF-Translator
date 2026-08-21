"""Regression coverage for a real bug found via a live user run against
"1526 VIRELICON.pdf": every highlighted block that did NOT need to grow
past its original size lost its quote-highlight background entirely -
except a thin sliver at the very edge, described by the user as "a thin
blue line at the bottom, as if a white box with text is lying on top of
it".

Root cause in PyMuPdfEngine.redact_block(): the old assumption (see this
module and redact_block()'s own docstring history) was that the ORIGINAL
quote-highlight rectangle, drawn as page content BEHIND the block's text,
simply survives redact_block()'s white-fill redaction untouched -
needing a redraw only when PyMuPdfEngine._grow_highlight_if_needed()
later found the translated text taller than the original. That
assumption is false: page.add_redact_annot(rect, fill=(1,1,1)) paints
its ENTIRE rect white regardless of what vector content sits underneath,
so EVERY highlighted block redact_block() touches loses its background,
not just ones that grow - _grow_highlight_if_needed() only ever ran (and
therefore only ever restored the color) for the growth case, leaving the
much more common "fits within the original box" case with no background
redraw at all.

Two visible symptoms depending on exact geometry, both reproduced here:
if the redaction rect (from the block's own TEXT bbox, only
width-widened for highlighted blocks) falls entirely within the drawn
highlight rectangle's true bounds, the background is just gone (fully
white). If the drawn highlight rectangle extends a bit further than the
text's own bbox (common: a highlight rectangle's bounds are independent
of the text glyph bbox extract_blocks() derives from), the portion
outside the redaction rect survives untouched - a visible sliver of the
original color right where the new, opaque white area ends.

Fixed by having redact_block() immediately redraw the highlight-color
background, covering the FULL associated-highlight extent (both axes,
not just the width-widening it already did), right after the white-fill
redaction - so every highlighted block starts from a correctly-colored
baseline before any text is ever inserted on top of it, matching what
_grow_highlight_if_needed() already assumed was there.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, _HIGHLIGHT_FILL_COLOR

_HIGHLIGHT_RGB = tuple(round(c * 255) for c in _HIGHLIGHT_FILL_COLOR)


def _build_highlight_taller_than_text_pdf(path: Path) -> None:
    """A one-line highlighted quote whose drawn highlight rectangle
    (y 50..70) is deliberately a few points TALLER than the text's own
    rendered bbox (y ends at ~63.7) - mirrors the real document, where a
    highlight rectangle's own bounds aren't always identical to the text
    glyph bbox extract_blocks() derives block.bbox from (confirmed via
    direct reproduction against "1526 VIRELICON.pdf": ~2pt gap on a real
    block; this fixture uses a larger, more obviously-testable gap).
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    highlight_rect = fitz.Rect(50, 50, 350, 70)
    page.draw_rect(highlight_rect, color=None, fill=_HIGHLIGHT_FILL_COLOR, width=0)
    page.insert_textbox(fitz.Rect(50, 50, 350, 68), "Quote line here.", fontsize=10, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_highlighted_block_keeps_its_background_without_needing_to_grow(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_highlight_taller_than_text_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = engine.extract_blocks(0)
    block = blocks[0]
    assert block.highlighted  # sanity: fixture reproduces the highlighted case

    # Deliberately short (fits the original rect outright, confirmed via
    # the `fit` return value below) so this isolates the no-growth case:
    # _grow_highlight_if_needed() takes its "original extent already
    # covers this" branch and does nothing, so any background restoration
    # visible below must come from redact_block() itself.
    engine.redact_block(block)
    fit = engine.insert_text(block, "", block.font_size, translated_html="<p>Q.</p>")
    assert fit
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]

    # Inside the text's own area: the real bug left this plain white.
    pix = page.get_pixmap(clip=fitz.Rect(300, 56, 302, 58))
    assert pix.pixel(0, 0) == _HIGHLIGHT_RGB

    # Below the text, within the highlight rectangle's own (taller) extent:
    # the real bug's OTHER symptom - a surviving sliver here while the text
    # area above was blanked - must not happen either; this area should be
    # unremarkable, i.e. the same highlight color, not a lone leftover strip.
    pix = page.get_pixmap(clip=fitz.Rect(300, 66, 302, 68))
    assert pix.pixel(0, 0) == _HIGHLIGHT_RGB
    result.close()


def test_non_highlighted_block_unaffected(tmp_path: Path) -> None:
    """redact_block()'s new highlight-redraw step must stay conditional on
    block.highlighted - a plain block has no color to restore and must
    render on ordinary white, unchanged.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 68), "Plain line here.", fontsize=10, fontname="helv")
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = engine.extract_blocks(0)[0]
    assert not block.highlighted

    engine.redact_block(block)
    engine.insert_text(block, "", block.font_size, translated_html="<p>Plain line here.</p>")
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]
    pix = page.get_pixmap(clip=fitz.Rect(300, 56, 302, 58))
    assert pix.pixel(0, 0) == (255, 255, 255)
    result.close()
