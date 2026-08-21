"""Verification script for the two highlight fixes applied after
tests/output/manual_diagnose_highlight_regression_output.txt:

  1. redact_block() now redacts at the full width of a highlighted block's
     associated highlight rectangle(s), not just the block's own (often
     much narrower) text extent.
  2. insert_text()'s fallback order is reversed for highlighted blocks:
     width/height growth is tried before font-shrinking, so a short,
     tightly-split one-line highlighted block no longer falls straight
     through to _MIN_FONT_SIZE (6pt) the moment translated text is even
     slightly longer than the original.

Runs pages 0-6 of "1526 Virelicon.pdf" through the real DeepL translation
pipeline (same as tests/manual_diagnose_highlight_pages_real.py), saving to
its OWN output path (the original tests/output/highlight_diagnose_real_output.pdf
was locked by another process when this was written - kept as a distinct
file rather than fighting that lock). Reports, for page index 2 specifically
(the page with "Ra"/"Father"/"Deities are all Lucifer meatsuits" examined in
the regression diagnosis):
  - for each highlighted block: the white redaction rect's width vs. the
    blue highlight rect's width (should now match, not just a narrow strip).
  - the font size actually used for each highlighted block's text (should
    be above _MIN_FONT_SIZE=6.0 wherever growth could plausibly cover the
    deficit instead).
Also renders before/after screenshots of the same crop region as the
regression diagnosis, and runs a full 14-page placeholder-text regression
pass (all pages, not just 0-6) to confirm non-highlighted blocks are
unaffected (0 new overflow/crash cases).

Not a pytest test - run manually:

    python tests/manual_verify_highlight_fixes.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import (
    _EXTRACT_FLAGS,
    _MIN_FONT_SIZE,
    _associated_highlight_extent,
    _get_highlight_rects,
    _line_text,
    PyMuPdfEngine,
    spans_to_html,
)
from pipeline.translation.base import TranslationError
from pipeline.translation.cost_control import DEEPL_PRICING, TranslationBudgetGuard
from pipeline.translation.deepl_provider import DeepLProvider
from tests.manual_e2e_pipeline import TEMPLATE, make_placeholder_text

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "1526 VIRELICON.pdf"
OUTPUT_PDF_PATH = REPO_ROOT / "tests" / "output" / "highlight_fix_verify_output.pdf"
REGRESSION_PDF_PATH = REPO_ROOT / "tests" / "output" / "highlight_fix_regression_full_doc.pdf"
BEFORE_PNG = REPO_ROOT / "tests" / "output" / "verify_before_fix.png"
AFTER_PNG = REPO_ROOT / "tests" / "output" / "verify_after_fix.png"

PAGES = range(0, 7)
TARGET_PAGE = 2
TARGET_LANG = "de"
SOURCE_LANG = "en"
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)


def translate_and_write(output_path: Path) -> tuple[PyMuPdfEngine, dict[int, list[TextBlock]]]:
    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(PDF_PATH))
    provider = DeepLProvider()
    guard = TranslationBudgetGuard(provider, DEEPL_PRICING)

    per_page_blocks: dict[int, list[TextBlock]] = {}
    for page_index in PAGES:
        blocks = engine.extract_blocks(page_index)
        per_page_blocks[page_index] = blocks
        for block in blocks:
            if not block.translatable:
                continue
            try:
                if block.spans:
                    html = spans_to_html(block.spans)
                    result = guard.translate_html(html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
                    translated_html = result.text
                    text_arg = block.text
                else:
                    result = guard.translate(block.text, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
                    translated_html = None
                    text_arg = result.text
            except TranslationError as exc:
                print(f"TranslationError on page {page_index}: {exc}")
                sys.exit(1)
            engine.redact_block(block)
            engine.insert_text(block, text_arg, block.font_size, translated_html=translated_html)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(output_path))
    return engine, per_page_blocks


def main() -> None:
    if not PDF_PATH.exists():
        print(f"File not found: {PDF_PATH}")
        sys.exit(1)

    print("Running real DeepL translation pipeline (pages 0-6)...")
    _, per_page_blocks = translate_and_write(OUTPUT_PDF_PATH)
    print(f"Output written to: {OUTPUT_PDF_PATH}")

    original_doc = fitz.open(str(PDF_PATH))
    original_page = original_doc[TARGET_PAGE]
    original_highlight_rects = _get_highlight_rects(original_page)

    output_doc = fitz.open(str(OUTPUT_PDF_PATH))
    output_page = output_doc[TARGET_PAGE]

    blocks = per_page_blocks[TARGET_PAGE]
    highlighted_blocks = [b for b in blocks if b.highlighted and b.translatable]

    print(f"\n=== Page {TARGET_PAGE}: highlighted-block width/font check ===")
    print(f"{'block bbox':<40} {'blue rect width':>16} {'white redaction width':>22} {'match?':>7} {'font size used':>15}")

    all_blocks_sorted = sorted(blocks, key=lambda b: b.bbox[1])
    drawings = output_page.get_drawings()

    width_ok_count = 0
    font_ok_count = 0
    for block in highlighted_blocks:
        extent = _associated_highlight_extent(block.bbox, original_highlight_rects)
        if extent is None:
            continue
        blue_width = extent.x1 - extent.x0

        # Find the white redaction rect matching this block's area (drawn
        # after the blue one, seqno tells paint order - highest seqno with
        # a y-range overlapping this block's own bbox and fill=white).
        candidates = [
            d for d in drawings
            if d.get("fill") == (1.0, 1.0, 1.0)
            and d.get("rect") is not None
            and d["rect"].y0 < block.bbox[3] + 1 and d["rect"].y1 > block.bbox[1] - 1
        ]
        if not candidates:
            white_width = None
        else:
            best = max(candidates, key=lambda d: d["seqno"])
            r = best["rect"]
            white_width = r.x1 - r.x0

        width_match = white_width is not None and abs(white_width - blue_width) < 2.0
        if width_match:
            width_ok_count += 1

        # Font size actually used: scan output page text tightly bounded
        # by the next block's own y0 (any block, translatable or not).
        idx = all_blocks_sorted.index(block)
        scan_bottom = (
            all_blocks_sorted[idx + 1].bbox[1] - 0.5
            if idx + 1 < len(all_blocks_sorted)
            else block.bbox[3] + 150.0
        )
        raw = output_page.get_text("dict", flags=_EXTRACT_FLAGS)
        sizes: list[float] = []
        bx0, by0, bx1, by1 = block.bbox
        for raw_block in raw.get("blocks", []):
            if raw_block.get("type") != 0:
                continue
            for line in raw_block.get("lines", []):
                lx0, ly0, lx1, ly1 = line["bbox"]
                if ly0 < by0 - 2 or ly0 > scan_bottom or lx1 < bx0 - 5 or lx0 > bx1 + 250:
                    continue
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        sizes.append(span.get("size", 0.0))
        min_size = min(sizes) if sizes else None
        if min_size is not None and min_size > _MIN_FONT_SIZE + 0.5:
            font_ok_count += 1

        bbox_str = str(tuple(round(v, 1) for v in block.bbox))
        white_str = f"{white_width:.1f}" if white_width is not None else "N/A"
        size_str = f"{min_size:.1f}" if min_size is not None else "N/A"
        print(
            f"{bbox_str:<40} {blue_width:>16.1f} {white_str:>22} "
            f"{str(width_match):>7} {size_str:>15}"
        )

    print(f"\nBlocks with matching white/blue width: {width_ok_count}/{len(highlighted_blocks)}")
    print(f"Blocks with font size above {_MIN_FONT_SIZE}pt floor: {font_ok_count}/{len(highlighted_blocks)}")

    # Screenshots: same crop as tests/manual_diagnose_highlight_regression.py
    crop = fitz.Rect(30, 245, 400, 270)  # "Just like in" / "Genau wie in" row
    original_page.get_pixmap(clip=crop, dpi=250).save(str(BEFORE_PNG))
    output_page.get_pixmap(clip=crop, dpi=250).save(str(AFTER_PNG))
    print(f"\nScreenshots written to: {BEFORE_PNG} (original), {AFTER_PNG} (fixed)")

    # Wider crop covering Ra/Father/Deities for a fuller visual check.
    wide_crop = fitz.Rect(30, 460, 595, 600)
    wide_path = REPO_ROOT / "tests" / "output" / "verify_after_fix_wide.png"
    output_page.get_pixmap(clip=wide_crop, dpi=150).save(str(wide_path))
    print(f"Wide screenshot written to: {wide_path}")

    # ================= Full-document regression (placeholder text) =================
    print("\n=== Full 14-page regression run (placeholder text) ===")
    engine = PyMuPdfEngine(template=TEMPLATE)
    engine.open(str(PDF_PATH))
    total = 0
    overflow = 0
    for page in engine.get_pages():
        for block in engine.extract_blocks(page.index):
            if not block.translatable:
                continue
            engine.redact_block(block)
            placeholder = make_placeholder_text(block.text)
            translated_html = None
            if block.spans:
                import html as html_module
                translated_html = f"<p>{html_module.escape(placeholder)}</p>"
            fit = engine.insert_text(block, placeholder, block.font_size, translated_html=translated_html)
            total += 1
            if not fit:
                overflow += 1
    engine.save(str(REGRESSION_PDF_PATH))
    print(f"Total blocks: {total}, overflow (fit=False): {overflow}")
    print(f"Regression output written to: {REGRESSION_PDF_PATH}")


if __name__ == "__main__":
    main()
