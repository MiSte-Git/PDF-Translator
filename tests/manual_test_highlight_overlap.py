"""Ad-hoc diagnostic script for line-level quote-highlight detection in "1526 Virelicon.pdf".

Not a pytest test - run manually to inspect:

    python tests/manual_test_highlight_overlap.py

Purpose (diagnosis only, no pipeline changes):
Confirmed by tests/manual_inspect_quote_blocks.py that the quote callouts are
filled rectangles at fill=rgb(0.871, 0.918, 0.965), one ~15pt-tall rectangle
per text line, and that extract_blocks() merges several such quotes (from
different authors) into a single TextBlock (page 1, bbox=(42.6, 262.6, 554.3,
708.1) contains "- PQ", "- PQ", "- Ivan" in sequence). This script checks,
line by line within that one block, whether the line's bbox is covered by a
highlight rectangle, to see whether a highlighted/not-highlighted sequence
lines up cleanly with the known quote boundaries.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz  # PyMuPDF

PDF_PATH = "1526 VIRELICON.pdf"
PAGE_INDEX = 1
TEST_BLOCK_BBOX = (42.6, 262.6, 554.3, 708.1)

HIGHLIGHT_FILL = (0.871, 0.918, 0.965)
FILL_TOLERANCE = 0.01

_EXTRACT_FLAGS = fitz.TEXTFLAGS_DICT | fitz.TEXT_COLLECT_STYLES


def fill_matches(fill, target: tuple[float, float, float], tol: float) -> bool:
    if fill is None or not isinstance(fill, (tuple, list)) or len(fill) != 3:
        return False
    return all(abs(fill[i] - target[i]) <= tol for i in range(3))


def vertical_overlap(
    line_bbox: tuple[float, float, float, float],
    rect_bbox: tuple[float, float, float, float],
) -> bool:
    _, ly0, _, ly1 = line_bbox
    _, ry0, _, ry1 = rect_bbox
    return ly0 < ry1 and ly1 > ry0


def collect_highlight_rects(
    page: fitz.Page, target_fill: tuple[float, float, float], tol: float
) -> list[tuple[float, float, float, float]]:
    rects = []
    for d in page.get_drawings():
        fill = d.get("fill")
        if not fill_matches(fill, target_fill, tol):
            continue
        bbox = d.get("rect")
        if bbox is None:
            continue
        rects.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
    return rects


def extract_lines_in_bbox(
    page: fitz.Page, block_bbox: tuple[float, float, float, float]
) -> list[tuple[str, tuple[float, float, float, float]]]:
    bx0, by0, bx1, by1 = block_bbox
    raw = page.get_text("dict", flags=_EXTRACT_FLAGS)
    lines: list[tuple[str, tuple[float, float, float, float]]] = []

    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            lx0, ly0, lx1, ly1 = line["bbox"]
            # keep lines whose bbox lies within (or overlaps) the test block's bbox
            if lx1 < bx0 or lx0 > bx1 or ly1 < by0 or ly0 > by1:
                continue
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            lines.append((text, (lx0, ly0, lx1, ly1)))

    lines.sort(key=lambda item: item[1][1])
    return lines


def main() -> None:
    pdf_path = PDF_PATH
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    print(f"Inspecting: {pdf_path}, page index {PAGE_INDEX}\n")

    doc = fitz.open(pdf_path)
    page = doc[PAGE_INDEX]

    highlight_rects = collect_highlight_rects(page, HIGHLIGHT_FILL, FILL_TOLERANCE)
    print(f"Highlight rectangles found (fill={HIGHLIGHT_FILL}, tol={FILL_TOLERANCE}): {len(highlight_rects)}")
    for r in highlight_rects:
        print(f"  rect bbox=({r[0]:.1f}, {r[1]:.1f}, {r[2]:.1f}, {r[3]:.1f})")

    lines = extract_lines_in_bbox(page, TEST_BLOCK_BBOX)
    print(f"\nLines found within test block bbox={TEST_BLOCK_BBOX}: {len(lines)}\n")

    sequence: list[bool] = []

    for text, line_bbox in lines:
        overlapping = [r for r in highlight_rects if vertical_overlap(line_bbox, r)]
        highlighted = len(overlapping) > 0
        sequence.append(highlighted)

        display_text = text.strip()
        if len(display_text) > 60:
            display_text = display_text[:60] + "..."

        lx0, ly0, lx1, ly1 = line_bbox
        print(
            f"y0={ly0:>6.1f} y1={ly1:>6.1f} | highlighted={str(highlighted):<5} | "
            f"overlaps={len(overlapping)} | text=\"{display_text}\""
        )

    print("\n=== Sequence ===")
    print(sequence)

    highlighted_count = sum(1 for v in sequence if v)
    not_highlighted_count = len(sequence) - highlighted_count

    transitions = sum(1 for i in range(1, len(sequence)) if sequence[i] != sequence[i - 1])

    print("\n=== Summary ===")
    print(f"Total lines: {len(sequence)}")
    print(f"Highlighted: {highlighted_count}")
    print(f"Not highlighted: {not_highlighted_count}")
    print(f"Transitions (True<->False): {transitions}")


if __name__ == "__main__":
    main()
