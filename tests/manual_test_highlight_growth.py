"""Ad-hoc verification script for _grow_highlight_if_needed()
(pipeline/pdf/pymupdf_engine.py, Part 2 of the highlight-detachment fix).

Forces height-growth for one small, highlighted, single-line block (by
inserting a deliberately much longer placeholder than the original text)
and checks that:
  1. a new, taller highlight rectangle was drawn, covering the actual text
     extent (not just the original one-line rectangle),
  2. the original highlight rectangle(s) for that block are still present
     underneath (untouched) - only a NEW one was added on top for the
     grown area,
  3. the text itself is still present and readable (i.e. actually got
     written) at the grown position.

Also renders a cropped screenshot of the affected area to
tests/output/highlight_growth_test.png for visual double-checking.

Not a pytest test - run manually:

    python tests/manual_test_highlight_growth.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz

from pipeline.pdf.pymupdf_engine import (
    _HIGHLIGHT_FILL_COLOR,
    _associated_highlight_extent,
    _get_highlight_rects,
    PyMuPdfEngine,
    spans_to_html,
)
from tests.manual_e2e_pipeline import TEMPLATE

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "1526 VIRELICON.pdf"
OUTPUT_PDF_PATH = REPO_ROOT / "tests" / "output" / "highlight_growth_test.pdf"
SCREENSHOT_PATH = REPO_ROOT / "tests" / "output" / "highlight_growth_test.png"

PAGES_TO_SCAN = range(0, 7)

TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)

# Deliberately much longer than any short highlighted one-liner in this
# document ("NOT", "- Ivan", " Ra ", ...) - guarantees the height-grow
# fallback kicks in.
FORCED_LONG_TEXT = (
    "Dies ist ein absichtlich sehr viel laengerer Platzhaltertext, der "
    "garantiert nicht mehr in die urspruengliche einzeilige Hoehe des "
    "highlighted Blocks passt und daher ein Hoehen-Wachstum der Box "
    "erzwingt, damit dieser Test ueberprueft, ob die farbige "
    "Hervorhebungsflaeche korrekt mitwaechst und der Text lesbar darueber "
    "liegt, anstatt auf einem weissen Hintergrund zu landen oder ueber die "
    "Flaeche hinauszuragen."
)


def rects_roughly_equal(a: fitz.Rect, b: fitz.Rect, tol: float = 1.0) -> bool:
    return (
        abs(a.x0 - b.x0) <= tol
        and abs(a.y0 - b.y0) <= tol
        and abs(a.x1 - b.x1) <= tol
        and abs(a.y1 - b.y1) <= tol
    )


def find_short_highlighted_block(engine: PyMuPdfEngine):
    """Pick the shortest (by bbox height) highlighted+translatable,
    single-line block across PAGES_TO_SCAN - the smallest original
    highlight area, to make height-growth as obvious as possible.
    """
    best = None
    best_height = float("inf")
    for page_index in PAGES_TO_SCAN:
        for block in engine.extract_blocks(page_index):
            if not (block.highlighted and block.translatable):
                continue
            if len(block.text.splitlines()) != 1:
                continue
            height = block.bbox[3] - block.bbox[1]
            if height < best_height:
                best_height = height
                best = block
    return best


def main() -> None:
    if not PDF_PATH.exists():
        print(f"File not found: {PDF_PATH}")
        sys.exit(1)

    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(PDF_PATH))

    target = find_short_highlighted_block(engine)
    if target is None:
        print("No short highlighted single-line block found - aborting.")
        sys.exit(1)

    page = engine._doc[target.page_index]  # read-only inspection, test-only
    original_highlight_rects = _get_highlight_rects(page)
    original_extent = _associated_highlight_extent(target.bbox, original_highlight_rects)

    print(f"Target block: page={target.page_index} bbox={target.bbox} text={target.text!r}")
    print(f"Original associated highlight extent: {original_extent}")
    assert original_extent is not None, "expected an associated highlight rect for this block"

    engine.redact_block(target)
    translated_html = None
    if target.spans:
        translated_html = f"<p>{FORCED_LONG_TEXT}</p>"
    fit = engine.insert_text(
        target, FORCED_LONG_TEXT, target.font_size, translated_html=translated_html
    )
    print(f"insert_text() fit={fit} (False is expected - forced overflow)")

    # Inspect the live page's drawings right away (same in-memory document,
    # no save/reopen needed for this check).
    rects_after = _get_highlight_rects(page)
    print(f"\nHighlight rects on the page after insert: {len(rects_after)}")

    # The original rectangle(s) should still be present unchanged...
    originals_still_present = [
        r for r in original_highlight_rects
        if any(rects_roughly_equal(r, r2) for r2 in rects_after)
    ]
    print(
        f"Original highlight rects still present unchanged: "
        f"{len(originals_still_present)}/{len(original_highlight_rects)}"
    )

    # ...and a NEW, taller one should have appeared, starting at the same
    # y0 as the original but extending further down.
    new_rects = [
        r
        for r in rects_after
        if not any(rects_roughly_equal(r, r2) for r2 in original_highlight_rects)
        and abs(r.y0 - original_extent.y0) <= 1.0
        and r.y1 > original_extent.y1 + 1.0
    ]
    print(f"New, taller highlight rect(s) found: {len(new_rects)}")
    for r in new_rects:
        print(f"    new rect bbox=({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")

    # Actual text extent, read directly from the page. Scan window is
    # tightly capped just below the new highlight rect (if one was found)
    # so unrelated, later content on the page doesn't get swept in - the
    # exact same class of measurement artifact found (in this diagnostic
    # script, not the pipeline) during tests/manual_diagnose_highlight_pages_real.py.
    bx0, by0, bx1, by1 = target.bbox
    scan_bottom = (new_rects[0].y1 + 2.0) if new_rects else (by1 + 150.0)
    raw = page.get_text("dict")
    text_union: fitz.Rect | None = None
    for raw_block in raw.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        for line in raw_block.get("lines", []):
            lx0, ly0, lx1, ly1 = line["bbox"]
            text = "".join(s.get("text", "") for s in line.get("spans", []))
            if not text.strip():
                continue
            if ly0 < by0 - 2 or ly0 > scan_bottom or lx1 < bx0 - 5 or lx0 > bx1 + 250:
                continue
            r = fitz.Rect(lx0, ly0, lx1, ly1)
            text_union = r if text_union is None else text_union | r

    print(f"\nActual inserted text extent: {text_union}")

    if new_rects and text_union is not None:
        new_rect = new_rects[0]
        covers = (
            text_union.y0 >= new_rect.y0 - 1.0 and text_union.y1 <= new_rect.y1 + 1.0
        )
        print(f"New highlight rect covers the actual text vertically: {covers}")

    OUTPUT_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(OUTPUT_PDF_PATH))
    print(f"\nOutput written to: {OUTPUT_PDF_PATH}")

    # Cropped screenshot of the affected area for visual double-checking.
    saved_doc = fitz.open(str(OUTPUT_PDF_PATH))
    saved_page = saved_doc[target.page_index]
    crop = fitz.Rect(
        max(target.bbox[0] - 20, 0),
        max(target.bbox[1] - 20, 0),
        min(target.bbox[2] + 40, saved_page.rect.width),
        min((text_union.y1 if text_union else target.bbox[3]) + 40, saved_page.rect.height),
    )
    pix = saved_page.get_pixmap(clip=crop, dpi=200)
    pix.save(str(SCREENSHOT_PATH))
    print(f"Screenshot written to: {SCREENSHOT_PATH}")


if __name__ == "__main__":
    main()
