"""Regression coverage for the "Redaction ueber Hintergrundbildern/
ueberlagerten Bloecken absichern" item tracked as open in RoadMap.md
Phase 2/PDF.

Two things were checked:

1. Background images (confirmed safe, no bug - see
   test_redaction_over_background_image_only_blanks_its_own_rect()):
   page.apply_redactions()'s default `images=2` ("blank out overlapping
   image parts") only whites out the portion of an image actually inside
   the redaction rect - the rest of the image, and the image object
   itself, survive untouched. This is exactly the wanted behavior for a
   block sitting on a background image.

2. Overlaid blocks via a highlighted block's regrowth (confirmed as a
   REAL bug, and fixed here): PyMuPdfEngine._collision_aware_max_y1()
   capped a growing block's height using the y0 of the nearest block
   found via _next_block_y0(), but that search used the growing block's
   own (narrow) bbox x-range to decide which blocks count as "in the
   same column" - even for a HIGHLIGHTED block, whose actual redraw width
   (see redact_block()'s/_grow_highlight_if_needed()'s docstrings) is the
   WIDE associated-highlight-rectangle extent, not its own narrow text
   bbox. A block sitting outside the highlighted block's narrow bbox but
   inside that wide highlight column was invisible to the collision
   check, so nothing capped the highlighted block's height growth before
   it reached that neighbor's row - and _grow_highlight_if_needed()'s
   enlarged highlight-color background redraw (WIDE, unlike its actual
   redaction step which stays narrow - see that function's docstring)
   then painted directly over the neighbor's text. Reproduced directly:
   a short highlighted quote, given a translation long enough to force
   many lines of growth, ended up painting a bright highlight-colored box
   over an unrelated block positioned to the quote's side. Fixed in
   _collision_aware_max_y1()/_next_block_y0() by widening the collision
   x-range to the highlight extent for highlighted blocks specifically.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, _HIGHLIGHT_FILL_COLOR


def _build_overlay_pdf(path: Path) -> None:
    """A wide highlight column (x 50..350) around a narrow quote (x
    50..150), with a second, unrelated block sitting just below the
    quote's own narrow bbox but horizontally OUTSIDE it (x 200..340) -
    i.e. inside the wide highlight column but outside the quote's own
    text extent, the exact shape that used to be invisible to the
    collision check.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    highlight_rect = fitz.Rect(50, 50, 350, 78)
    page.draw_rect(highlight_rect, color=None, fill=_HIGHLIGHT_FILL_COLOR, width=0)
    page.insert_textbox(fitz.Rect(50, 50, 150, 78), "Short quote.", fontsize=10, fontname="helv")
    page.insert_textbox(fitz.Rect(200, 85, 340, 110), "Untouched sidebar text.", fontsize=10, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_highlighted_block_growth_does_not_paint_over_a_side_by_side_block(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_overlay_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = engine.extract_blocks(0)
    quote_block = next(b for b in blocks if b.highlighted)
    sidebar_block = next(b for b in blocks if not b.highlighted)
    assert sidebar_block.bbox[0] >= quote_block.bbox[2]  # sanity: truly to the side, not overlapping

    # Deliberately long enough to force many lines of growth if unchecked.
    long_translation = "<p>" + (
        "Eine sehr viel laengere uebersetzte Version des kurzen Zitats, "
        "die definitiv mehrere Zeilen braucht. "
    ) * 3 + "</p>"

    engine.redact_block(quote_block)
    engine.insert_text(quote_block, "", quote_block.font_size, translated_html=long_translation)
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]

    assert "Untouched sidebar text" in page.get_text()

    # The real bug: even with the text content still "present", the
    # sidebar's rendered area used to get painted over with the
    # highlight fill color. Check actual pixels, not just extracted text.
    pix = page.get_pixmap(clip=fitz.Rect(200, 85, 340, 98.7))
    sample = pix.pixel(20, 5)
    highlight_rgb = tuple(round(c * 255) for c in _HIGHLIGHT_FILL_COLOR)
    assert sample != highlight_rgb
    result.close()


def test_redaction_over_background_image_only_blanks_its_own_rect(tmp_path: Path) -> None:
    output = tmp_path / "bgimg.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    # A solid-color rectangle image spanning the whole page, so any pixel
    # sample outside the redaction rect must still show its original color.
    pixmap = fitz.Pixmap(fitz.csRGB, (0, 0, 400, 500), False)
    pixmap.set_rect(pixmap.irect, (200, 50, 50))
    page.insert_image(fitz.Rect(0, 0, 400, 500), pixmap=pixmap)
    page.insert_textbox(fitz.Rect(50, 200, 350, 240), "Text over background image", fontsize=12, fontname="helv")
    doc.save(str(output))
    doc.close()

    reopened = fitz.open(str(output))
    page = reopened[0]
    images_before = page.get_images()
    assert images_before  # sanity: the image is really there

    redaction_rect = fitz.Rect(50, 200, 350, 240)
    page.add_redact_annot(redaction_rect, fill=(1, 1, 1))
    page.apply_redactions()

    assert page.get_images()  # image object still present, not removed
    inside = page.get_pixmap(clip=redaction_rect).pixel(10, 10)
    outside = page.get_pixmap(clip=fitz.Rect(50, 400, 350, 450)).pixel(10, 10)
    assert inside == (255, 255, 255)  # redacted area blanked white
    assert outside == (200, 50, 50)  # rest of the background image untouched
    reopened.close()
