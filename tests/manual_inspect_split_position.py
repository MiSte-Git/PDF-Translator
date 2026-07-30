"""Diagnostic script: check part A/part B bboxes vs. drawn lines on page 0.

For 1526 Virelicon.pdf, prints the exact bbox of the anchor-split metadata
block (part A, ends at "Asset Matrix...") and the following title block
(part B, starts at "The Virelicon Prism..."), all page-0 vector drawings
from page.get_drawings() with y-position/width, and explicit comparisons:
part B.y0 vs. each drawing's y-position, and part B.y0 vs. part A.y1 - to
find out whether a drawn line actually sits between the two blocks, and
whether extract_blocks()'s raw bboxes already leave a gap/overlap before
any insert_text() fallback logic runs. Diagnosis only, no fix, no
pipeline/ changes. Not a pytest test - run manually:

    python tests/manual_inspect_split_position.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import FIRST_PAGE_ANCHOR_TERMS, PyMuPdfEngine

PDF_PATH = Path(__file__).resolve().parent.parent / "1526 Virelicon.pdf"
PAGE_INDEX = 0

# Same heuristic as tests/manual_inspect_first_page_zone.py.
_LINE_WIDTH_HEIGHT_RATIO = 5.0
_LINE_MAX_HEIGHT = 3.0


def describe_drawings(page) -> list[tuple[float, float, float, float, bool]]:
    """Return (y0, y1, width, height, is_horizontal_line) per drawing's
    bounding rect, sorted by y0.
    """
    entries = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        width = rect.width
        height = rect.height
        is_line = height < _LINE_MAX_HEIGHT and width > height * _LINE_WIDTH_HEIGHT_RATIO
        entries.append((rect.y0, rect.y1, width, height, is_line))
    entries.sort(key=lambda entry: entry[0])
    return entries


def main() -> None:
    engine = PyMuPdfEngine()  # no template: unfiltered extract_blocks()
    engine.open(str(PDF_PATH))
    page_obj = engine._doc[PAGE_INDEX]

    blocks = sorted(engine.extract_blocks(PAGE_INDEX), key=lambda block: block.bbox[1])
    part_a = next(
        (
            block
            for block in blocks
            if not block.translatable
            and any(term.lower() in block.text.lower() for term in FIRST_PAGE_ANCHOR_TERMS)
        ),
        None,
    )
    part_b = next(
        (block for block in blocks if block.translatable and "Virelicon Prism" in block.text),
        None,
    )

    print(f"--- {PDF_PATH.name} | page {PAGE_INDEX} ---")
    print(f"part A (untranslatable, ends at 'Asset Matrix...'): bbox={part_a.bbox if part_a else None}")
    print(f"part B (translatable, starts at 'The Virelicon Prism...'): bbox={part_b.bbox if part_b else None}")
    print()

    print(f"--- page {PAGE_INDEX} vector drawings (page.get_drawings()), sorted by y0 ---")
    drawings = describe_drawings(page_obj)
    if not drawings:
        print("(none found)")
    for y0, y1, width, height, is_line in drawings:
        flag = " <-- horizontal line" if is_line else ""
        print(f"y0={y0:>7.1f} y1={y1:>7.1f} width={width:>7.1f} height={height:>6.2f}{flag}")
    print()

    if part_a is None or part_b is None:
        print("Could not locate part A and/or part B - aborting comparison.")
        return

    part_a_y1 = part_a.bbox[3]
    part_b_y0 = part_b.bbox[1]

    print("--- comparison: part B.y0 vs. each drawing's y-position ---")
    for y0, y1, width, height, is_line in drawings:
        if part_b_y0 < y0:
            relation = "BEFORE (part B.y0 < line.y0)"
        elif part_b_y0 > y0:
            relation = "AFTER (part B.y0 > line.y0)"
        else:
            relation = "ON (part B.y0 == line.y0)"
        flag = " [horizontal line]" if is_line else ""
        print(f"line y0={y0:>7.1f} width={width:>7.1f}{flag} -> part B.y0={part_b_y0:.1f} is {relation}")
    print()

    print("--- comparison: part B.y0 vs. part A.y1 ---")
    gap = part_b_y0 - part_a_y1
    if gap > 0:
        print(f"part B.y0 ({part_b_y0:.1f}) is AFTER part A.y1 ({part_a_y1:.1f}) - gap of {gap:.1f}pt, no overlap")
    elif gap < 0:
        print(f"part B.y0 ({part_b_y0:.1f}) is BEFORE part A.y1 ({part_a_y1:.1f}) - overlap of {-gap:.1f}pt")
    else:
        print(f"part B.y0 ({part_b_y0:.1f}) == part A.y1 ({part_a_y1:.1f}) - flush, no gap")


if __name__ == "__main__":
    main()
