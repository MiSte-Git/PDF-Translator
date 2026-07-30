"""Ad-hoc diagnostic script for the "image gets redacted" layout bug.

Investigates why, on page 1 of 2182 INDELEGATA.pdf (a two-column layout with
a book-cover image on the left and body text on the right), the image ends
up white/covered in the e2e output. Prints image bboxes, text-block bboxes,
and any block/image bbox overlap found. Does not fix anything - diagnosis
only. Not a pytest test - run manually:

    python tests/manual_diagnose_layout.py path/to/file.pdf [page_index]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from pipeline.pdf.template import block_overlaps

# Page 0 (first page) is where the book-cover image sits next to intro text.
DEFAULT_PAGE_INDEX = 0

# extract_blocks() (pipeline/pdf/pymupdf_engine.py) builds one TextBlock per
# PyMuPDF "dict" block via page.get_text("dict"), using that raw block's
# bbox as-is. PyMuPDF reports a block's bbox as the union of all its lines'
# bboxes. If one logical block (e.g. a single wrapped paragraph) has some
# lines confined to a column next to an image and other lines running the
# full page width (e.g. once the text continues below the image), the union
# bbox spans both - even though no actual glyphs sit in the gap. That
# oversized bbox is what redact_block() then whites out, taking the image
# with it.


def rect_intersection(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """Return the intersection rect of two bboxes (assumes they overlap)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_diagnose_layout.py <path-to-pdf> [page_index]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_index = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PAGE_INDEX

    engine = PyMuPdfEngine()  # no template for this diagnosis
    engine.open(pdf_path)

    images = engine.extract_images(page_index)
    print(f"--- images on page {page_index} ---")
    for image in images:
        bbox = tuple(round(v, 1) for v in image.bbox)
        print(f"xref={image.xref} | bbox={bbox}")

    blocks = engine.extract_blocks(page_index)
    print(f"\n--- text blocks on page {page_index} ---")
    for block in blocks:
        bbox = tuple(round(v, 1) for v in block.bbox)
        text = block.text.replace("\n", " ")
        if len(text) > 50:
            text = text[:50] + "..."
        print(f"bbox={bbox} | translatable={block.translatable} | text=\"{text}\"")

    print("\n--- block/image overlaps ---")
    found_overlap = False
    for block in blocks:
        for image in images:
            if not block_overlaps(block.bbox, image.bbox):
                continue
            found_overlap = True
            overlap = tuple(round(v, 1) for v in rect_intersection(block.bbox, image.bbox))
            block_bbox = tuple(round(v, 1) for v in block.bbox)
            image_bbox = tuple(round(v, 1) for v in image.bbox)
            extends_left = max(0.0, image.bbox[2] - block.bbox[0])
            print(
                f"block bbox={block_bbox} overlaps image (xref={image.xref}) "
                f"bbox={image_bbox}\n"
                f"  intersection={overlap}\n"
                f"  block.x0={block.bbox[0]:.1f} is {extends_left:.1f}pt to the left of "
                f"image.x1={image.bbox[2]:.1f} -> block bbox reaches into/through the "
                f"image's column"
            )

    if not found_overlap:
        print("(none found)")


if __name__ == "__main__":
    main()
