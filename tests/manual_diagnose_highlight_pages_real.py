"""Ad-hoc diagnostic script for highlighted-quote-block handling across
pages 0-6 of "1526 Virelicon.pdf", using a REAL translation provider
(DeepL) instead of synthetic placeholder text.

Context: tests/manual_diagnose_highlight_pages.py ran the same diagnosis
with ~25%-longer placeholder text and found no evidence of the reported
"highlight background detached from text" bug on pages 0-6 - neither an
un-split block with mixed highlighted lines (Point 1), nor a highlight
rectangle removed/moved by redact_block()/apply_redactions() (Point 2).
One open explanation from that script's summary was that the bug might
only show up with real translation's length/wrapping dynamics (DeepL's
German output runs longer than a simple 25%-longer placeholder in
unpredictable, sentence-by-sentence ways) - this script re-runs the same
checks with real DeepL translations for target_lang="de" to test exactly
that, plus a new Step 4 that directly measures, for every highlighted
sub-block, how far the actual translated text's rendered extent overshoots
the (unchanged, un-resized) highlight rectangle behind it.

Not a pytest test - run manually:

    python tests/manual_diagnose_highlight_pages_real.py

Full per-page detail is written to
tests/output/manual_diagnose_highlight_pages_real_output.txt; only the
summary table is printed to the console. Uses TranslationBudgetGuard
(DeepL pricing) for cost logging/capping; prints an upfront cost estimate
(informational only, no confirmation prompt - 7 pages is well within
DeepL's free tier in virtually all cases).
"""
from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import (
    _EXTRACT_FLAGS,
    _get_highlight_rects,
    _line_is_highlighted,
    _line_text,
    PyMuPdfEngine,
    spans_to_html,
)
from pipeline.translation.base import TranslationError
from pipeline.translation.cost_control import DEEPL_PRICING, TranslationBudgetGuard
from pipeline.translation.deepl_provider import DeepLProvider
from tests.manual_e2e_pipeline import TEMPLATE

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "1526 VIRELICON.pdf"
OUTPUT_PDF_PATH = REPO_ROOT / "tests" / "output" / "highlight_diagnose_real_output.pdf"
REPORT_PATH = REPO_ROOT / "tests" / "output" / "manual_diagnose_highlight_pages_real_output.txt"

PAGES = range(0, 7)  # 0..6 inclusive
TARGET_LANG = "de"
SOURCE_LANG = "en"

# Same header/footer geometry already used for this PDF elsewhere (e.g.
# tests/manual_translate_all_providers.py); first_page_zones cleared so
# page 0's metadata split relies entirely on FIRST_PAGE_ANCHOR_TERMS.
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)

_RECT_MATCH_TOLERANCE = 1.0  # pt, for matching an original rect to an output rect
_VERSATZ_TOLERANCE = 5.0  # pt, Step 4's "Versatz" threshold
_LAST_BLOCK_SCAN_MARGIN = 300.0  # pt, generous downward scan cap for a page's last block

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html_tags(html_text: str) -> str:
    """Plain-text rendering of translated HTML, for building a search
    needle / preview - just strips tags, doesn't unescape entities (good
    enough for the short previews/needles used here).
    """
    return _TAG_RE.sub("", html_text)


def search_needle(text: str) -> str:
    """A short, distinctive, whitespace-collapsed prefix of `text`, used to
    locate where this block's translated text actually landed in the
    output PDF via page.search_for(). Kept only as a secondary cross-check
    here (Step 3, carried over from the placeholder-text script) - Step 4
    below uses geometry (get_text('dict')) instead, since a literal
    substring search is fragile (MuPDF's HTML text layout substitutes "fi"
    with the ligature "ﬁ", and very short texts produce needles that
    match unrelated text elsewhere on the page).
    """
    collapsed = " ".join(text.split())
    return collapsed[:40]


def recompute_line_highlight_flags(
    page: fitz.Page, block: TextBlock, highlight_rects: list[fitz.Rect]
) -> list[bool]:
    """Independently recompute a highlighted/not-highlighted flag for every
    non-blank line inside `block.bbox`, directly from page.get_text('dict'),
    instead of trusting extract_blocks()'s own internal line grouping - the
    cross-check for explanation (1): mixed flags with a uniform
    block.highlighted would mean _split_by_highlight() failed to separate
    them.
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


def measure_actual_text_extent(
    page: fitz.Page, block: TextBlock, scan_bottom: float
) -> fitz.Rect | None:
    """Union bbox of every non-blank text line in the OUTPUT page whose
    horizontal position falls within block.bbox's x-range (+-5pt) and whose
    top (y0) lies between block.bbox.y0-2 and scan_bottom.

    This reads the actually-rendered geometry directly, rather than via a
    literal-text search (see search_needle()'s docstring for why that's
    fragile) - the ground truth for "how tall did this block's translated
    text actually end up" regardless of ligatures/short needles/language.
    Returns None if no matching line is found.
    """
    bx0, by0, bx1, by1 = block.bbox
    raw = page.get_text("dict", flags=_EXTRACT_FLAGS)
    union: fitz.Rect | None = None
    for raw_block in raw.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        for line in raw_block.get("lines", []):
            lx0, ly0, lx1, ly1 = line["bbox"]
            if not _line_text(line.get("spans", [])).strip():
                continue
            if ly0 < by0 - 2 or ly0 > scan_bottom:
                continue
            if lx1 < bx0 - 5 or lx0 > bx1 + 5:
                continue
            r = fitz.Rect(lx0, ly0, lx1, ly1)
            union = r if union is None else union | r
    return union


def associated_highlight_extent(
    block_bbox: tuple[float, float, float, float], highlight_rects: list[fitz.Rect]
) -> fitz.Rect | None:
    """Union bbox of every highlight rect that vertically overlaps
    block_bbox - the "should still be this tall" reference area for a
    highlighted block, taken from the page's (unchanged - see Step 3)
    original highlight rects.
    """
    bx0, by0, bx1, by1 = block_bbox
    overlapping = [r for r in highlight_rects if r.y0 < by1 and r.y1 > by0]
    if not overlapping:
        return None
    union = overlapping[0]
    for r in overlapping[1:]:
        union |= r
    return union


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

    # ================= Step 1: pre-write structure =================
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

    # ================= Step 2: real translation + write pipeline =================
    emit("\n" + "=" * 100)
    emit("STEP 2: running redact_block() + insert_text() with REAL DeepL translations + save()")
    emit("=" * 100)

    provider = DeepLProvider()
    guard = TranslationBudgetGuard(provider, DEEPL_PRICING)

    translatable_blocks: list[TextBlock] = [
        block
        for page_index in PAGES
        for block in per_page_blocks[page_index]
        if block.translatable
    ]

    # Upfront cost estimate (informational only - no confirmation gate,
    # 7 pages of a single document is trivial next to DeepL's free tier).
    billed_texts = [
        spans_to_html(block.spans) if block.spans else block.text
        for block in translatable_blocks
    ]
    char_count, cost = guard.estimate_run(billed_texts)
    cost_line = (
        f"Estimated DeepL cost for {len(translatable_blocks)} blocks / "
        f"{char_count:,} characters (pages 0-6): ${cost:.4f}"
    )
    emit(f"\n{cost_line}")
    print(cost_line)

    block_translated_plain: dict[int, str] = {}  # id(block) -> plain-text rendering
    fit_results: dict[int, bool] = {}

    for page_index in PAGES:
        for block in per_page_blocks[page_index]:
            if not block.translatable:
                continue
            try:
                if block.spans:
                    html = spans_to_html(block.spans)
                    result = guard.translate_html(
                        html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG
                    )
                    translated_html = result.text
                    plain_text = strip_html_tags(translated_html)
                    text_arg = block.text  # ignored by insert_text() when translated_html is given
                else:
                    result = guard.translate(
                        block.text, target_lang=TARGET_LANG, source_lang=SOURCE_LANG
                    )
                    translated_html = None
                    plain_text = result.text
                    text_arg = result.text
            except TranslationError as exc:
                print(f"TranslationError on page {page_index}, block bbox={block.bbox}: {exc}")
                sys.exit(1)

            block_translated_plain[id(block)] = plain_text

            engine.redact_block(block)
            fit = engine.insert_text(
                block, text_arg, block.font_size, translated_html=translated_html
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

    summary_rows: list[tuple[int, int, int, int, str, int, str]] = []

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

        # --- text-consistency check (search_for-based, carried over) ---
        emit(f"\n--- Page {page_index}: text-consistency check ---")
        blocks_sorted = sorted(
            [b for b in per_page_blocks[page_index] if b.translatable],
            key=lambda b: b.bbox[1],
        )
        text_issues = 0
        for i, block in enumerate(blocks_sorted):
            translated_plain = block_translated_plain.get(id(block), "")
            needle = search_needle(translated_plain)
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

            overflow_below = union.y1 > ey1 + 2.0
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

        # ================= Step 4: reflow-versatz check (highlighted blocks) ==
        emit(f"\n--- Page {page_index}: Step 4 - highlight reflow-versatz check ---")
        versatz_count = 0
        # The "next block" boundary must come from EVERY block on the page
        # (translatable or not) - a non-translatable block (e.g. a link
        # overlap, left untranslated) sitting right after a highlighted
        # block would otherwise not bound the scan, and its own (unrelated,
        # still-English) text gets swept into the highlighted block's
        # measured extent, producing a false "versatz" - exactly what
        # happened before this fix (page 2's first highlighted block: the
        # scan ran all the way to the next TRANSLATABLE block 120pt further
        # down, right through two intervening non-translatable blocks).
        all_blocks_sorted = sorted(per_page_blocks[page_index], key=lambda b: b.bbox[1])
        highlighted_blocks = [b for b in blocks_sorted if b.highlighted]
        if not highlighted_blocks:
            emit("  (no highlighted blocks on this page)")
        for block in highlighted_blocks:
            idx_in_sorted = all_blocks_sorted.index(block)
            if idx_in_sorted + 1 < len(all_blocks_sorted):
                scan_bottom = all_blocks_sorted[idx_in_sorted + 1].bbox[1] - 0.5
            else:
                # Last translatable block on the page: cap the scan at the
                # template's footer zone (if any), not just the raw page
                # height - otherwise this generously-sized fallback window
                # sweeps up the (untranslated, unrelated) footer text itself
                # and falsely inflates the measured extent.
                footer_top = (
                    TEMPLATE_NO_ZONES.footer_bbox[1]
                    if TEMPLATE_NO_ZONES.footer_bbox is not None
                    else output_page.rect.height
                )
                scan_bottom = min(
                    block.bbox[3] + _LAST_BLOCK_SCAN_MARGIN, footer_top - 1.0
                )

            actual_extent = measure_actual_text_extent(output_page, block, scan_bottom)
            rect_extent = associated_highlight_extent(block.bbox, original_rects)

            bbox_r = tuple(round(v, 1) for v in block.bbox)
            if rect_extent is None:
                emit(f"  block bbox={bbox_r} => NO ASSOCIATED HIGHLIGHT RECT FOUND (unexpected)")
                continue
            if actual_extent is None:
                emit(
                    f"  block bbox={bbox_r} | highlight rect y=({rect_extent.y0:.1f},"
                    f"{rect_extent.y1:.1f}) => NO TEXT FOUND for this block in output"
                )
                continue

            diff = max(0.0, actual_extent.y1 - rect_extent.y1)
            is_versatz = diff > _VERSATZ_TOLERANCE
            if is_versatz:
                versatz_count += 1
            note = " <== VERSATZ" if is_versatz else ""

            emit(
                f"  block bbox={bbox_r} | highlight rect y=({rect_extent.y0:.1f},{rect_extent.y1:.1f}) "
                f"h={rect_extent.height:.1f} | actual text y=({actual_extent.y0:.1f},"
                f"{actual_extent.y1:.1f}) h={actual_extent.height:.1f} | "
                f"diff (text bottom - rect bottom)={diff:.1f}pt{note}"
            )

        emit(f"\nVersatz-Faelle (>{_VERSATZ_TOLERANCE:.0f}pt) on page {page_index}: {versatz_count}")

        summary_rows.append(
            (
                page_index,
                len(per_page_blocks[page_index]),
                sum(1 for b in per_page_blocks[page_index] if b.highlighted),
                len(per_page_suspect_blocks[page_index]),
                f"{len(original_rects)} / {len(output_rects)}",
                versatz_count,
                f"orphaned={len(orphaned)}, unexpected={len(unexpected)}, text_issues={text_issues}",
            )
        )

    # ================= code-inspection note (static, not runtime-dependent) ==
    emit("\n" + "=" * 100)
    emit("CODE-INSPECTION NOTE (independent of this run's data)")
    emit("=" * 100)
    emit(
        "Grepped pipeline/pdf/pymupdf_engine.py for any code that resizes/redraws a "
        "highlight rectangle: _get_highlight_rects() is called ONLY from extract_blocks() "
        "(to classify TextBlock.highlighted). redact_block() calls only "
        "add_redact_annot()/apply_redactions(); insert_text()/_insert_html_text() call only "
        "insert_htmlbox()/insert_textbox(). None of these touch page.get_drawings() output "
        "or draw/replace any shape. CONFIRMED: there is currently NO mechanism anywhere in "
        "the pipeline that adapts a highlight rectangle's size to the new (translated) text "
        "height - it is always left exactly as in the original PDF, whatever the translated "
        "text's actual extent turns out to be."
    )

    # ================= summary table =================
    emit("\n" + "=" * 100)
    emit("SUMMARY (all pages)")
    emit("=" * 100)
    header = (
        f"{'Seite':>5} | {'Bloecke':>7} | {'highlighted':>11} | "
        f"{'Split-Verdacht':>14} | {'Rects orig/out':>14} | {'Versatz(>5pt)':>13} | Auffaelligkeiten"
    )
    emit(header)
    emit("-" * len(header))
    for row in summary_rows:
        page_index, total_blocks, highlighted_count, suspect_count, rects_str, versatz_count, notes = row
        emit(
            f"{page_index:>5} | {total_blocks:>7} | {highlighted_count:>11} | "
            f"{suspect_count:>14} | {rects_str:>14} | {versatz_count:>13} | {notes}"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"\nFull report written to: {REPORT_PATH}\n")
    print(header)
    print("-" * len(header))
    for row in summary_rows:
        page_index, total_blocks, highlighted_count, suspect_count, rects_str, versatz_count, notes = row
        print(
            f"{page_index:>5} | {total_blocks:>7} | {highlighted_count:>11} | "
            f"{suspect_count:>14} | {rects_str:>14} | {versatz_count:>13} | {notes}"
        )


if __name__ == "__main__":
    main()
