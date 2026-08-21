"""Ad-hoc diagnostic script for the quote-highlight rectangles in "1526 Virelicon.pdf".

Not a pytest test - run manually to inspect:

    python tests/manual_inspect_quote_blocks.py

Purpose (diagnosis only, no pipeline changes):
1. Find every filled rectangle from page.get_drawings() and print its actual
   fill color value (no guessing at "light blue").
2. For each such rectangle, find which extract_blocks() text blocks overlap
   its bbox (using pipeline.pdf.template.block_overlaps if present) and
   print the full block text.
3. Check whether the last line of each overlapping block matches an
   author-initials pattern like "- XX" (hyphen + 1-4 uppercase letters).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz  # PyMuPDF

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

try:
    from pipeline.pdf.template import block_overlaps
except ImportError:
    def block_overlaps(
        block_bbox: tuple[float, float, float, float],
        zone_bbox: tuple[float, float, float, float],
    ) -> bool:
        bx0, by0, bx1, by1 = block_bbox
        zx0, zy0, zx1, zy1 = zone_bbox
        return bx0 < zx1 and bx1 > zx0 and by0 < zy1 and by1 > zy0

PDF_PATH = "1526 VIRELICON.pdf"

# Hyphen (ASCII or common typographic dashes) + 1-4 uppercase letters, end of string.
AUTHOR_INITIALS_RE = re.compile(r"[-‐‑‒–—]\s*[A-Z]{1,4}\s*$")


def describe_color(value) -> str:
    if value is None:
        return "None"
    if isinstance(value, (int, float)):
        return f"gray({value:.3f})"
    if isinstance(value, (tuple, list)):
        vals = ", ".join(f"{v:.3f}" for v in value)
        n = len(value)
        kind = {1: "gray", 3: "rgb", 4: "cmyk"}.get(n, f"{n}-comp")
        return f"{kind}({vals})"
    return repr(value)


def is_light_fill(fill) -> bool:
    """Heuristic ONLY for deciding what to print as a 'candidate' rectangle -
    the actual color values are printed regardless so nothing is hidden."""
    if fill is None:
        return False
    if isinstance(fill, (int, float)):
        return fill > 0.5
    if isinstance(fill, (tuple, list)) and len(fill) == 3:
        r, g, b = fill
        # light-ish and not plain white, and some blue/cyan bias tolerated but not required
        return (r + g + b) / 3 > 0.55 and not (r > 0.98 and g > 0.98 and b > 0.98)
    return False


def main() -> None:
    pdf_path = PDF_PATH
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    print(f"Inspecting: {pdf_path}\n")

    doc = fitz.open(pdf_path)

    engine = PyMuPdfEngine()  # no template - raw extraction
    engine.open(pdf_path)

    total_candidates = 0
    total_pattern_hits = 0

    for page_index in range(len(doc)):
        page = doc[page_index]
        drawings = page.get_drawings()

        candidate_rects = []
        for d in drawings:
            fill = d.get("fill")
            rect_items = [item for item in d.get("items", []) if item[0] == "re"]
            has_type_re = bool(rect_items)
            has_fill = fill is not None

            if not (has_type_re or has_fill):
                continue
            if not has_fill:
                continue  # need an actual fill color to be a highlight candidate

            # bbox: prefer the drawing's own rect, else union of 're' item rects
            bbox = d.get("rect")
            if bbox is None and rect_items:
                r = rect_items[0][1]
                bbox = r
            if bbox is None:
                continue

            bbox_t = (round(bbox.x0, 1), round(bbox.y0, 1), round(bbox.x1, 1), round(bbox.y1, 1))

            print(
                f"[page {page_index}] drawing: type_re={has_type_re} "
                f"fill={describe_color(fill)} fill_opacity={d.get('fill_opacity')} "
                f"stroke={describe_color(d.get('color'))} bbox={bbox_t}"
            )

            if is_light_fill(fill):
                candidate_rects.append(bbox_t)

        if not candidate_rects:
            continue

        blocks = engine.extract_blocks(page_index)

        for rect_bbox in candidate_rects:
            total_candidates += 1
            print(f"\n--- Candidate light-fill rect on page {page_index}: bbox={rect_bbox} ---")

            overlapping = [b for b in blocks if block_overlaps(b.bbox, rect_bbox)]

            if not overlapping:
                print("  (no overlapping text blocks found)")
                continue

            for b in overlapping:
                bbox_t = tuple(round(v, 1) for v in b.bbox)
                print(f"  block bbox={bbox_t} translatable={b.translatable}")
                print("  text:")
                for line in b.text.splitlines():
                    print(f"    | {line}")

                lines = [ln for ln in b.text.splitlines() if ln.strip()]
                last_line = lines[-1] if lines else ""
                match = AUTHOR_INITIALS_RE.search(last_line)
                if match:
                    total_pattern_hits += 1
                    print(f"  => author-initials pattern MATCH on last line: \"{last_line}\" -> \"{match.group(0)}\"")
                else:
                    print(f"  => no author-initials pattern on last line: \"{last_line}\"")
                print()

    print("\n=== Summary ===")
    print(f"Total candidate light-fill rectangles: {total_candidates}")
    print(f"Overlapping blocks with author-initials pattern match: {total_pattern_hits}")


if __name__ == "__main__":
    main()
