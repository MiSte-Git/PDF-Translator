"""TEMPORARY debug script: visualize insert_text()'s overflow-fallback rect.

For the known book-cover-column block on page 0 of 2182 INDELEGATA.pdf,
draws a red rectangle around the exact rect insert_text() ends up using
after its width-before-height overflow fallback, then inserts the regular
tripled placeholder text so the fill can be visually compared against the
drawn box. Also draws a blue rectangle for the template's footer_bbox on
the same page and reports whether the block's final rect overlaps it. All
other blocks on the page are processed normally, without debug rectangles.

insert_text() doesn't return its final rect, so this script replays its
fallback loop (font shrink -> widen -> grow height) to recover it. Since
insert_textbox() writes to the page as soon as it reports a fit, the replay
runs on a throwaway scratch page (added/removed via the already-open
fitz.Document) so the measurement never touches the real page - no
pipeline/ code is changed for this. Not a pytest test - run manually:

    python tests/manual_debug_bbox_visual.py path/to/file.pdf
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import (
    PyMuPdfEngine,
    _FONT_STEP,
    _FONT_VARIANTS,
    _MIN_FONT_SIZE,
    _PAGE_EDGE_MARGIN,
    _WIDTH_STEP,
)
from pipeline.pdf.template import block_overlaps
from tests.manual_e2e_pipeline import TEMPLATE, make_placeholder_text

# Known problem block: text column right of the book-cover image, page 0.
TARGET_PAGE_INDEX = 0
TARGET_BBOX_HINT = (176.4, 316.4, 552.8, 545.7)
_HINT_TOLERANCE = 1.0

DEBUG_RECT_COLOR = (1, 0, 0)
DEBUG_RECT_WIDTH = 1.5

FOOTER_RECT_COLOR = (0, 0, 1)
FOOTER_RECT_WIDTH = 1.5

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "debug_bbox_visual.pdf"


def is_target_block(block: TextBlock) -> bool:
    """Match the known book-cover-column block by page and approximate bbox."""
    if block.page_index != TARGET_PAGE_INDEX:
        return False
    return all(
        abs(actual - hint) < _HINT_TOLERANCE
        for actual, hint in zip(block.bbox, TARGET_BBOX_HINT)
    )


def final_fallback_rect(
    doc, page, block: TextBlock, text: str, font_size: float
) -> tuple[float, float, float, float]:
    """Replay insert_text()'s newline-normalize + font-shrink +
    width-before-height fallback on a throwaway scratch page to recover the
    final rect it would pass to insert_textbox(), without writing to the
    real page. Must stay in sync with pipeline/pdf/pymupdf_engine.py's
    insert_text() or this would report a stale rect.
    """
    scratch = doc.new_page(width=page.rect.width, height=page.rect.height)
    try:
        fontname = _FONT_VARIANTS[(block.bold, block.italic)]
        color = tuple(component / 255 for component in block.color)
        rect = list(block.bbox)
        text = re.sub(r" {2,}", " ", text.replace("\n", " ")).strip()

        size = font_size
        while True:
            deficit = scratch.insert_textbox(
                tuple(rect), text, fontsize=size, fontname=fontname, color=color
            )
            if deficit >= 0:
                return tuple(rect)
            if size <= _MIN_FONT_SIZE:
                max_x1 = scratch.rect.width - _PAGE_EDGE_MARGIN
                while deficit < 0 and rect[2] < max_x1:
                    rect[2] = min(rect[2] + _WIDTH_STEP, max_x1)
                    deficit = scratch.insert_textbox(
                        tuple(rect), text, fontsize=size, fontname=fontname, color=color
                    )
                if deficit < 0:
                    rect[3] += -deficit
                return tuple(rect)
            size = max(size - _FONT_STEP, _MIN_FONT_SIZE)
    finally:
        doc.delete_page(scratch.number)


def report_footer_overlap(
    rect: tuple[float, float, float, float], footer_bbox: tuple[float, float, float, float]
) -> None:
    """Print whether the block's final rect overlaps footer_bbox and by how much."""
    if not block_overlaps(rect, footer_bbox):
        print(f"no overlap with footer_bbox: block rect y1={rect[3]:.1f} vs footer y0={footer_bbox[1]:.1f}")
        return

    overlap_y0 = max(rect[1], footer_bbox[1])
    overlap_y1 = min(rect[3], footer_bbox[3])
    depth_into_footer = rect[3] - footer_bbox[1]
    print(
        f"OVERLAP with footer_bbox: intersection y=({overlap_y0:.1f}, {overlap_y1:.1f}), "
        f"block-rect reaches {depth_into_footer:.1f}pt into the footer zone "
        f"(block.y1={rect[3]:.1f} vs footer.y0={footer_bbox[1]:.1f})"
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_debug_bbox_visual.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    engine = PyMuPdfEngine(template=TEMPLATE)
    engine.open(pdf_path)

    for page in engine.get_pages():
        page_obj = engine._doc[page.index]
        for block in engine.extract_blocks(page.index):
            if not block.translatable:
                continue

            engine.redact_block(block)
            placeholder = make_placeholder_text(block.text)

            if is_target_block(block):
                rect = final_fallback_rect(
                    engine._doc, page_obj, block, placeholder, block.font_size
                )
                # Adding/removing the scratch page above can invalidate the
                # previously fetched page object, so re-fetch before drawing.
                page_obj = engine._doc[page.index]
                page_obj.draw_rect(rect, color=DEBUG_RECT_COLOR, width=DEBUG_RECT_WIDTH)
                print(f"debug rect drawn on page {page.index}: {tuple(round(v, 1) for v in rect)}")

                if TEMPLATE.footer_bbox is not None:
                    page_obj.draw_rect(
                        TEMPLATE.footer_bbox, color=FOOTER_RECT_COLOR, width=FOOTER_RECT_WIDTH
                    )
                    print(f"footer debug rect drawn on page {page.index}: {TEMPLATE.footer_bbox}")
                    report_footer_overlap(rect, TEMPLATE.footer_bbox)

            engine.insert_text(block, placeholder, block.font_size)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(OUTPUT_PATH))
    print(f"output written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
