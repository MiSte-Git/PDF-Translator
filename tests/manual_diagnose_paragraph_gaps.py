"""Ad-hoc diagnostic script for the "paragraph spacing disappears" question.

Checks whether PyMuPDF's page.get_text("dict") groups multiple visually
separated paragraphs (blank line between them in the original PDF) into one
block, and whether the line-to-line y-gaps within that block reveal where
the real paragraph breaks are (as outlier gaps, larger than normal line
spacing). Uses page.get_text("dict") directly (not extract_blocks()) to see
PyMuPDF's raw line layout. Does not fix anything - diagnosis only. Not a
pytest test - run manually:

    python tests/manual_diagnose_paragraph_gaps.py path/to/file.pdf [page_index]
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

# Known block: body text starting next to the book-cover image and
# continuing full-width below it, page 0 - reported to no longer show
# visible paragraph spacing in the current test output, even though the
# original PDF shows multiple paragraphs separated by blank lines. This is
# the bbox of the single *raw* PyMuPDF block (before extract_blocks()'s
# column-split logic divides it into two TextBlocks) - see
# tests/manual_diagnose_layout.py where this block was first found.
DEFAULT_PAGE_INDEX = 0
TARGET_BBOX_HINT = (42.6, 316.4, 552.8, 761.7)
_HINT_TOLERANCE = 2.0

# A line-to-line gap more than this factor above the median gap is treated
# as a likely real paragraph break rather than normal line spacing.
_OUTLIER_FACTOR = 2.0


def find_target_block(raw: dict, bbox_hint: tuple[float, float, float, float]) -> dict | None:
    """Find the raw text block whose bbox approximately matches bbox_hint."""
    for raw_block in raw.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        bbox = raw_block["bbox"]
        if all(abs(a - b) < _HINT_TOLERANCE for a, b in zip(bbox, bbox_hint)):
            return raw_block
    return None


def line_text(line: dict) -> str:
    """Concatenate a raw line's span texts."""
    return "".join(span["text"] for span in line.get("spans", []))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_diagnose_paragraph_gaps.py <path-to-pdf> [page_index]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_index = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PAGE_INDEX

    engine = PyMuPdfEngine()  # no template for this diagnosis
    engine.open(pdf_path)
    page = engine._doc[page_index]
    raw = page.get_text("dict")

    block = find_target_block(raw, TARGET_BBOX_HINT)
    if block is None:
        print(f"no block found near {TARGET_BBOX_HINT} on page {page_index}")
        sys.exit(1)

    lines = block.get("lines", [])
    print(f"target block bbox={tuple(round(v, 1) for v in block['bbox'])} | {len(lines)} lines")
    print()

    gaps: list[float] = []
    prev_line = None
    for line in lines:
        y0, y1 = line["bbox"][1], line["bbox"][3]
        text = line_text(line)[:60]
        if prev_line is None:
            print(f"  y=({y0:.1f}, {y1:.1f}) | gap=  n/a | text={text!r}")
        else:
            gap = y0 - prev_line["bbox"][3]
            gaps.append(gap)
            print(f"  y=({y0:.1f}, {y1:.1f}) | gap={gap:5.1f} | text={text!r}")
        prev_line = line

    if not gaps:
        print("\nonly one line (or none) - no gaps to analyze")
        return

    median_gap = statistics.median(gaps)
    mean_gap = statistics.mean(gaps)
    print(f"\nmedian line gap: {median_gap:.2f}pt | mean line gap: {mean_gap:.2f}pt")

    outliers = [
        (i, gap) for i, gap in enumerate(gaps) if gap > _OUTLIER_FACTOR * median_gap
    ]
    print(f"outlier gaps (> {_OUTLIER_FACTOR}x median): {len(outliers)}")
    for i, gap in outliers:
        before_text = line_text(lines[i])[:60]
        after_text = line_text(lines[i + 1])[:60]
        ratio = gap / median_gap if median_gap else float("inf")
        print(
            f"  gap={gap:.1f}pt ({ratio:.1f}x median) between:\n"
            f"    before: {before_text!r}\n"
            f"    after:  {after_text!r}"
        )


if __name__ == "__main__":
    main()
