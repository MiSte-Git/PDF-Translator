"""Diagnostic script: inspect page 0 for a natural first_page_zones boundary.

Prints the current TEMPLATE.first_page_zones bbox (tests/manual_e2e_pipeline.py)
as a reference, page 0's images (page.get_images()/get_image_rects()), all
vector drawings from page.get_drawings() - both a filtered "looks like a
horizontal line" summary and the full raw per-item data (type/fill/color) -
any tables found via page.find_tables(), and all text blocks from an
unfiltered extract_blocks() (no template) - to identify what actually draws
the horizontal separator visible between the metadata block and body text
(image, rect, table, or something else) and whether its y-position would
make a better natural lower bound for first_page_zones than the current
hand-picked value. Diagnosis only, no fix, no pipeline/ changes. Not a
pytest test - run manually:

    python tests/manual_inspect_first_page_zone.py path/to/file.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from tests.manual_e2e_pipeline import TEMPLATE

PAGE_INDEX = 0

# Heuristic for "this drawing looks like a horizontal ruled line": much wider
# than it is tall, and thin enough not to be a filled block/box.
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


def describe_images(page) -> list[tuple[int, tuple[float, float, float, float], float, float, bool]]:
    """Return (xref, rect, width, height, is_horizontal_strip) for every
    image on the page, one entry per placement rect (an image's xref can be
    placed more than once via get_image_rects()), sorted by rect.y0.
    """
    entries = []
    for image_info in page.get_images(full=True):
        xref = image_info[0]
        for rect in page.get_image_rects(xref):
            width = rect.width
            height = rect.height
            is_strip = height < _LINE_MAX_HEIGHT and width > height * _LINE_WIDTH_HEIGHT_RATIO
            entries.append((xref, tuple(round(v, 1) for v in rect), width, height, is_strip))
    entries.sort(key=lambda entry: entry[1][1])
    return entries


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_inspect_first_page_zone.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print(f"--- reference: TEMPLATE.first_page_zones ({Path(pdf_path).name}) ---")
    print(f"{TEMPLATE.first_page_zones}")
    print()

    engine = PyMuPdfEngine()  # no template: unfiltered extract_blocks()
    engine.open(pdf_path)
    page_obj = engine._doc[PAGE_INDEX]

    print(f"--- page {PAGE_INDEX} images (page.get_images() + get_image_rects()), sorted by y0 ---")
    images = describe_images(page_obj)
    if not images:
        print("(none found)")
    for xref, rect, width, height, is_strip in images:
        flag = " <-- horizontal strip" if is_strip else ""
        print(f"xref={xref} | rect={rect} | width={width:>7.1f} height={height:>6.2f}{flag}")
    print()

    print(f"--- page {PAGE_INDEX} vector drawings (page.get_drawings()), sorted by y0 ---")
    drawings = describe_drawings(page_obj)
    if not drawings:
        print("(none found)")
    for y0, y1, width, height, is_line in drawings:
        flag = " <-- horizontal line" if is_line else ""
        print(f"y0={y0:>7.1f} y1={y1:>7.1f} width={width:>7.1f} height={height:>6.2f}{flag}")
    print()

    print(f"--- page {PAGE_INDEX} vector drawings, RAW (page.get_drawings(), unfiltered) ---")
    raw_drawings = page_obj.get_drawings()
    if not raw_drawings:
        print("(none found)")
    for i, drawing in enumerate(raw_drawings):
        rect = tuple(round(v, 1) for v in drawing["rect"])
        print(
            f"[{i}] rect={rect} | fill={drawing.get('fill')!r} | color={drawing.get('color')!r} | "
            f"width={drawing.get('width')!r} | closePath={drawing.get('closePath')!r} | "
            f"even_odd={drawing.get('even_odd')!r}"
        )
        for item in drawing["items"]:
            kind = item[0]
            print(f"    item type={kind!r} data={item[1:]}")
    print()

    print(f"--- page {PAGE_INDEX} tables (page.find_tables()) ---")
    tables = page_obj.find_tables().tables
    if not tables:
        print("(none found)")
    for i, table in enumerate(tables):
        bbox = tuple(round(v, 1) for v in table.bbox)
        print(f"[{i}] bbox={bbox} | rows={table.row_count} | cols={table.col_count}")
    print()

    print(f"--- page {PAGE_INDEX} text blocks (extract_blocks(), no template), sorted by y0 ---")
    blocks = sorted(engine.extract_blocks(PAGE_INDEX), key=lambda block: block.bbox[1])
    for block in blocks:
        bbox = tuple(round(v, 1) for v in block.bbox)
        text = block.text.replace("\n", " ")
        if len(text) > 60:
            text = text[:60] + "..."
        print(f"bbox={bbox} | text=\"{text}\"")


if __name__ == "__main__":
    main()
