"""Ad-hoc diagnostic script for highlighted-quote-block handling across
pages 0-6 of "1526 Virelicon.pdf".

Context: tests/manual_test_highlight_overlap.py confirmed line-level
highlight detection works, and pipeline/pdf/pymupdf_engine.py's
_split_by_highlight() now splits blocks at highlighted/not-highlighted line
runs (verified against ONE known test block on page 1). Bug report: on
other pages, the highlight background in the OUTPUT pdf ends up detached
from / misaligned with the (placeholder-)translated text, and extra,
non-original text sometimes appears. This script gathers evidence for two
competing (non-exclusive) explanations:

  (1) extract_blocks() skips the split somewhere: a block contains lines
      with mixed highlighted/not-highlighted status, but block.highlighted
      is still reported as a single, uniform value - i.e. _split_by_highlight()
      was bypassed or didn't fire for that block.
  (2) extract_blocks() splits correctly, but redact_block()/insert_text()
      still mishandle the result: e.g. a highlight rectangle gets removed
      by apply_redactions() (PyMuPDF removes vector graphics "contained in"
      the redaction rectangle), or insert_text()'s overflow-growth fallback
      (needed more often now that splitting produces smaller, tighter
      boxes) pushes translated text past the block's own bbox into a
      neighboring block's/highlight's area.

Not a pytest test - run manually:

    python tests/manual_diagnose_highlight_pages.py

Full per-page detail is written to
tests/output/manual_diagnose_highlight_pages_output.txt; only the summary
table is printed to the console.
"""
from __future__ import annotations

import dataclasses
import html as html_module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import (
    _EXTRACT_FLAGS,
    _get_highlight_rects,
    _line_is_highlighted,
    _line_text,
    PyMuPdfEngine,
)
from tests.manual_e2e_pipeline import TEMPLATE

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "1526 VIRELICON.pdf"
OUTPUT_PDF_PATH = REPO_ROOT / "tests" / "output" / "highlight_diagnose_output.pdf"
REPORT_PATH = REPO_ROOT / "tests" / "output" / "manual_diagnose_highlight_pages_output.txt"

PAGES = range(0, 7)  # 0..6 inclusive

# Same header/footer geometry already used for this PDF in
# tests/manual_translate_all_providers.py; first_page_zones cleared so
# page 0's metadata split relies entirely on FIRST_PAGE_ANCHOR_TERMS.
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)

_RECT_MATCH_TOLERANCE = 1.0  # pt, for matching an original rect to an output rect


def make_placeholder_text(original: str) -> str:
    """Same ~25%-longer placeholder as tests/manual_e2e_pipeline.py -
    realistic translation-length stand-in, no real translation call needed
    for this diagnostic.
    """
    extra_len = int(len(original) * 0.25)
    return (original + " " + original[:extra_len]).strip()


def make_placeholder_html(placeholder_text: str) -> str:
    """Wrap `placeholder_text` as a single escaped <p>, "\\n" -> <br/>.

    insert_text() ignores its plain `text` argument whenever block.spans is
    non-empty (which is now true for almost every block) unless
    `translated_html` is also given - see insert_text()'s docstring
    ("this is how an already-translated ... result ... gets inserted").
    tests/manual_e2e_pipeline.py's simpler placeholder-only call (`text=`,
    no `translated_html=`) therefore silently re-inserts the ORIGINAL
    (unchanged) text for any spans-having block instead of the placeholder -
    exactly what the real translation scripts (e.g.
    tests/manual_translate_all_providers.py) avoid by also passing
    translated_html=result.text. This diagnostic mirrors that real-pipeline
    behavior instead of manual_e2e_pipeline.py's, so it actually exercises
    the placeholder text's overflow/layout behavior.
    """
    escaped = html_module.escape(placeholder_text).replace("\n", "<br/>")
    return f"<p>{escaped}</p>"


def search_needle(text: str) -> str:
    """A short, distinctive, whitespace-collapsed prefix of `text`, used to
    locate where this block's (placeholder) text actually landed in the
    output PDF via page.search_for() - simpler and more direct than trying
    to reconstruct span/line geometry from get_text('dict').
    """
    collapsed = " ".join(text.split())
    return collapsed[:40]


def recompute_line_highlight_flags(
    page: fitz.Page, block: TextBlock, highlight_rects: list[fitz.Rect]
) -> list[bool]:
    """Independently recompute a highlighted/not-highlighted flag for every
    non-blank line inside `block.bbox`, directly from page.get_text('dict'),
    instead of trusting extract_blocks()'s own internal line grouping - this
    is the cross-check for explanation (1): if these flags are not all
    equal to each other, but block.highlighted is a single fixed value,
    _split_by_highlight() failed to separate them.
    """
    bx0, by0, bx1, by1 = block.bbox
    raw = page.get_text("dict", flags=_EXTRACT_FLAGS)
    flags: list[bool] = []
    for raw_block in raw.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        for line in raw_block.get("lines", []):
            lx0, ly0, lx1, ly1 = line["bbox"]
            if lx1 < bx0 or lx0 > bx1 or ly1 < by0 or ly0 > by1:
                continue
            if not _line_text(line.get("spans", [])).strip():
                continue
            flags.append(_line_is_highlighted(fitz.Rect(*line["bbox"]), highlight_rects))
    return flags


def rects_match(a: fitz.Rect, b: fitz.Rect, tol: float) -> bool:
    return (
        abs(a.x0 - b.x0) <= tol
        and abs(a.y0 - b.y0) <= tol
        and abs(a.x1 - b.x1) <= tol
        and abs(a.y1 - b.y1) <= tol
    )


def main() -> None:
    if not PDF_PATH.exists():
        print(f"File not found: {PDF_PATH}")
        sys.exit(1)

    report: list[str] = []

    def emit(line: str = "") -> None:
        report.append(line)

    # --- independent read-only handle for "before" inspection ---
    diag_doc = fitz.open(str(PDF_PATH))

    # --- the actual engine that will mutate its own document copy ---
    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(PDF_PATH))

    # ================= Step 1: pre-write structure (all pages first, ==
    # ================= before any redact_block()/insert_text() runs) ==
    per_page_blocks: dict[int, list[TextBlock]] = {}
    per_page_highlight_rects: dict[int, list[fitz.Rect]] = {}
    per_page_suspect_blocks: dict[int, list[TextBlock]] = {}

    emit("=" * 100)
    emit("STEP 1: pre-write structure (extract_blocks() + highlight rects, before any mutation)")
    emit("=" * 100)

    for page_index in PAGES:
        page = diag_doc[page_index]
        highlight_rects = _get_highlight_rects(page)
        per_page_highlight_rects[page_index] = highlight_rects
        blocks = engine.extract_blocks(page_index)
        per_page_blocks[page_index] = blocks

        emit(f"\n--- Page {page_index} ---")
        emit(f"Highlight rects found on page (fill match): {len(highlight_rects)}")
        for r in highlight_rects:
            emit(f"    rect bbox=({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")

        emit(f"\nBlocks from extract_blocks(): {len(blocks)}")
        suspects: list[TextBlock] = []
        for block in blocks:
            bbox = tuple(round(v, 1) for v in block.bbox)
            line_count = len(block.text.splitlines())
            preview = block.text.replace("\n", " ")[:50]

            line_flags = recompute_line_highlight_flags(page, block, highlight_rects)
            mixed = len(set(line_flags)) > 1
            uniform_recomputed = line_flags[0] if line_flags else False
            suspect = mixed or (block.highlighted != uniform_recomputed and not mixed)
            if mixed or block.highlighted != uniform_recomputed:
                suspects.append(block)

            flag_note = ""
            if mixed:
                flag_note = " <== MIXED LINE FLAGS WITHIN ONE BLOCK (split missed)"
            elif block.highlighted != uniform_recomputed:
                flag_note = (
                    f" <== MISMATCH block.highlighted={block.highlighted} "
                    f"vs recomputed={uniform_recomputed}"
                )

            emit(
                f"  bbox={bbox} | highlighted={str(block.highlighted):<5} | "
                f"translatable={str(block.translatable):<5} | lines={line_count} | "
                f'line_flags={line_flags} | text="{preview}"{flag_note}'
            )

        per_page_suspect_blocks[page_index] = suspects
        emit(f"\nBlocks with split-suspicion on page {page_index}: {len(suspects)}")

    # ================= Step 2: run the real write pipeline =================
    emit("\n" + "=" * 100)
    emit("STEP 2: running redact_block() + insert_text() (placeholder text) + save()")
    emit("=" * 100)

    block_placeholders: dict[int, str] = {}  # id(block) -> placeholder text used
    fit_results: dict[int, bool] = {}

    for page_index in PAGES:
        for block in per_page_blocks[page_index]:
            if not block.translatable:
                continue
            engine.redact_block(block)
            placeholder = make_placeholder_text(block.text)
            block_placeholders[id(block)] = placeholder
            translated_html = make_placeholder_html(placeholder) if block.spans else None
            fit = engine.insert_text(
                block, placeholder, block.font_size, translated_html=translated_html
            )
            fit_results[id(block)] = fit

    OUTPUT_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(OUTPUT_PDF_PATH))
    emit(f"\nOutput written to: {OUTPUT_PDF_PATH}")

    # ================= Step 3: inspect the saved output =================
    emit("\n" + "=" * 100)
    emit("STEP 3: inspecting the output PDF (highlight rects + text placement)")
    emit("=" * 100)

    output_doc = fitz.open(str(OUTPUT_PDF_PATH))

    summary_rows: list[tuple[int, int, int, int, str, str] ] = []

    for page_index in PAGES:
        output_page = output_doc[page_index]
        original_rects = per_page_highlight_rects[page_index]
        output_rects = _get_highlight_rects(output_page)

        matched = 0
        orphaned: list[fitz.Rect] = []
        for orect in original_rects:
            if any(rects_match(orect, out_r, _RECT_MATCH_TOLERANCE) for out_r in output_rects):
                matched += 1
            else:
                orphaned.append(orect)
        unexpected = [
            out_r
            for out_r in output_rects
            if not any(rects_match(out_r, orect, _RECT_MATCH_TOLERANCE) for orect in original_rects)
        ]

        emit(f"\n--- Page {page_index}: highlight rects original vs output ---")
        emit(f"Original: {len(original_rects)} | Output: {len(output_rects)} | Matched (unchanged): {matched}")
        emit(f"Orphaned (present originally, missing/moved in output): {len(orphaned)}")
        for r in orphaned:
            emit(f"    orphaned original rect bbox=({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")
        emit(f"Unexpected (present in output, no matching original): {len(unexpected)}")
        for r in unexpected:
            emit(f"    unexpected output rect bbox=({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")

        # --- text-consistency check ---
        emit(f"\n--- Page {page_index}: text-consistency check ---")
        blocks_sorted = sorted(
            [b for b in per_page_blocks[page_index] if b.translatable],
            key=lambda b: b.bbox[1],
        )
        text_issues = 0
        for i, block in enumerate(blocks_sorted):
            placeholder = block_placeholders.get(id(block), "")
            needle = search_needle(placeholder if placeholder else block.text)
            if not needle.strip():
                continue
            hits = output_page.search_for(needle)
            expected_bbox = block.insert_bbox if block.insert_bbox is not None else block.bbox
            ex0, ey0, ex1, ey1 = expected_bbox

            if not hits:
                text_issues += 1
                emit(
                    f"  block bbox={tuple(round(v,1) for v in block.bbox)} "
                    f'highlighted={block.highlighted} fit={fit_results.get(id(block))} '
                    f'=> TEXT NOT FOUND in output for needle="{needle}"'
                )
                continue

            union = hits[0]
            for h in hits[1:]:
                union |= h

            overflow_below = union.y1 > ey1 + 2.0  # tolerance
            overlaps_next = False
            if i + 1 < len(blocks_sorted):
                next_bbox = blocks_sorted[i + 1].bbox
                overlaps_next = union.y1 > next_bbox[1] + 1.0

            note = ""
            if overflow_below and overlaps_next:
                note = " <== TEXT BLEEDS INTO NEXT BLOCK'S AREA"
                text_issues += 1
            elif overflow_below:
                note = " <== text extends below original bbox, but stays clear of the next block"

            emit(
                f"  block bbox={tuple(round(v,1) for v in block.bbox)} "
                f"highlighted={block.highlighted} fit={fit_results.get(id(block))} | "
                f"expected y-range=({ey0:.1f},{ey1:.1f}) | "
                f"actual text y-range=({union.y0:.1f},{union.y1:.1f}){note}"
            )

        emit(f"\nText-consistency issues on page {page_index}: {text_issues}")

        summary_rows.append(
            (
                page_index,
                len(per_page_blocks[page_index]),
                sum(1 for b in per_page_blocks[page_index] if b.highlighted),
                len(per_page_suspect_blocks[page_index]),
                f"{len(original_rects)} / {len(output_rects)}",
                (
                    f"orphaned={len(orphaned)}, unexpected={len(unexpected)}, "
                    f"text_issues={text_issues}"
                ),
            )
        )

    # ================= summary table =================
    emit("\n" + "=" * 100)
    emit("SUMMARY (all pages)")
    emit("=" * 100)
    header = (
        f"{'Seite':>5} | {'Bloecke':>7} | {'highlighted':>11} | "
        f"{'Split-Verdacht':>14} | {'Rects orig/out':>14} | Auffaelligkeiten"
    )
    emit(header)
    emit("-" * len(header))
    for row in summary_rows:
        page_index, total_blocks, highlighted_count, suspect_count, rects_str, notes = row
        emit(
            f"{page_index:>5} | {total_blocks:>7} | {highlighted_count:>11} | "
            f"{suspect_count:>14} | {rects_str:>14} | {notes}"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"Full report written to: {REPORT_PATH}\n")
    print(header)
    print("-" * len(header))
    for row in summary_rows:
        page_index, total_blocks, highlighted_count, suspect_count, rects_str, notes = row
        print(
            f"{page_index:>5} | {total_blocks:>7} | {highlighted_count:>11} | "
            f"{suspect_count:>14} | {rects_str:>14} | {notes}"
        )


if __name__ == "__main__":
    main()
