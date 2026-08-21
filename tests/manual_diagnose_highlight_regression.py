"""Ad-hoc regression diagnosis for reported problems in
tests/output/highlight_diagnose_real_output.pdf: narrow/offset highlight
backgrounds, wrong/duplicated text, white gaps inside a highlighted area,
and extremely narrow/compressed font in places - all reported around page
index 2 (0-indexed) / "Seite 3" (1-indexed) of "1526 Virelicon.pdf", the
area containing "PQ to Ivan", "Ra", "Father"/"Vater", "Deities are all
Lucifer meatsuits".

Step 1 verifies whether the existing highlight_diagnose_real_output.pdf on
disk was actually produced by the CURRENT code (the _HIGHLIGHT_LINE_TOLERANCE
tolerance fix and the _grow_highlight_if_needed() background-growth
mechanism, including its later max(block.bbox[2], final_rect.x1) width fix)
before trusting it as evidence of a NEW bug. Step 2 only runs the detailed
per-block diagnosis (a-d) if Step 1 finds the file current; otherwise it
regenerates a fresh, distinctly-named output first.

Not a pytest test - run manually:

    python tests/manual_diagnose_highlight_regression.py

Full output is written to
tests/output/manual_diagnose_highlight_regression_output.txt; a short
summary is printed to the console.
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pymupdf as fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import (
    _EXTRACT_FLAGS,
    _HIGHLIGHT_FILL_COLOR,
    _associated_highlight_extent,
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
ENGINE_SOURCE_PATH = REPO_ROOT / "pipeline" / "pdf" / "pymupdf_engine.py"
BASE_SOURCE_PATH = REPO_ROOT / "pipeline" / "pdf" / "base.py"
PROTECTED_TERMS_PATH = REPO_ROOT / "pipeline" / "translation" / "protected_terms.py"
EXISTING_OUTPUT_PATH = REPO_ROOT / "tests" / "output" / "highlight_diagnose_real_output.pdf"
REPORT_PATH = REPO_ROOT / "tests" / "output" / "manual_diagnose_highlight_regression_output.txt"

TARGET_LANG = "de"
SOURCE_LANG = "en"
PAGES = range(0, 7)
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)

LANDMARK_STRINGS = ["PQ to Ivan", "Deities are all Lucifer", "Father", "Ra"]


def _fmt_mtime(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    return (result.stdout or "") + (result.stderr or "")


def step1_freshness_check(emit) -> bool:
    """Returns True if the existing output file is judged current w.r.t.
    the present pipeline/pdf/pymupdf_engine.py on disk.
    """
    emit("=" * 100)
    emit("STEP 1: freshness check")
    emit("=" * 100)

    if not EXISTING_OUTPUT_PATH.exists():
        emit(f"\n{EXISTING_OUTPUT_PATH} does not exist - nothing to verify, a fresh run is required.")
        return False

    output_mtime = EXISTING_OUTPUT_PATH.stat().st_mtime
    emit(f"\n{EXISTING_OUTPUT_PATH.relative_to(REPO_ROOT)}")
    emit(f"  mtime: {_fmt_mtime(EXISTING_OUTPUT_PATH)}")

    emit("\nSource file mtimes:")
    for p in [ENGINE_SOURCE_PATH, BASE_SOURCE_PATH, PROTECTED_TERMS_PATH]:
        emit(f"  {p.relative_to(REPO_ROOT)}: {_fmt_mtime(p)}")

    emit("\ngit log -1:")
    emit(_run(["git", "log", "-1"]).strip())
    emit(
        "\nNOTE: all of today's highlight-related changes are UNCOMMITTED "
        "(see git status below) - the last commit above predates them. "
        "git commit history is NOT a valid freshness signal here; only "
        "on-disk file mtimes (working tree) are compared below."
    )
    emit("\ngit status --short:")
    emit(_run(["git", "status", "--short"]).strip())

    emit("\nCode-presence checks (grep) for the last implemented fixes:")
    engine_source = ENGINE_SOURCE_PATH.read_text(encoding="utf-8")
    checks = {
        "_HIGHLIGHT_LINE_TOLERANCE = 1.5": "_HIGHLIGHT_LINE_TOLERANCE = 1.5" in engine_source,
        "_grow_highlight_if_needed( defined": "def _grow_highlight_if_needed(" in engine_source,
        "max(block.bbox[2], final_rect.x1) width fix": "max(block.bbox[2], final_rect.x1)" in engine_source,
    }
    all_present = True
    for label, present in checks.items():
        emit(f"  {label}: {'FOUND' if present else 'MISSING'}")
        all_present = all_present and present

    emit("\nWhich script produces this exact filename?")
    for script in [
        "tests/manual_diagnose_highlight_pages.py",
        "tests/manual_diagnose_highlight_pages_real.py",
        "tests/manual_test_highlight_growth.py",
    ]:
        script_path = REPO_ROOT / script
        if script_path.exists():
            content = script_path.read_text(encoding="utf-8")
            matches = "highlight_diagnose_real_output.pdf" in content
            emit(f"  {script}: {'MATCHES this filename' if matches else 'different output filename'}")

    engine_mtime_newer_than_output = ENGINE_SOURCE_PATH.stat().st_mtime > output_mtime
    is_current = all_present and not engine_mtime_newer_than_output
    emit(
        f"\nVerdict: pymupdf_engine.py mtime is "
        f"{'AFTER' if engine_mtime_newer_than_output else 'BEFORE'} the output PDF's mtime, "
        f"and all 3 fix markers are {'present' if all_present else 'NOT all present'} in the source.\n"
        f"=> Existing output file is judged {'CURRENT' if is_current else 'STALE'} "
        f"w.r.t. the code on disk."
    )
    return is_current


def regenerate_fresh_output(emit) -> Path:
    """Re-runs the same translate+redact+insert+save pipeline as
    tests/manual_diagnose_highlight_pages_real.py, saving to a
    timestamp-suffixed path so this run can never be confused with a
    future/past one.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fresh_path = REPO_ROOT / "tests" / "output" / f"highlight_diagnose_real_output_{timestamp}.pdf"
    emit(f"\nRegenerating a fresh output at: {fresh_path.relative_to(REPO_ROOT)}")

    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(PDF_PATH))
    provider = DeepLProvider()
    guard = TranslationBudgetGuard(provider, DEEPL_PRICING)

    for page_index in PAGES:
        for block in engine.extract_blocks(page_index):
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
                emit(f"TranslationError on page {page_index}: {exc}")
                sys.exit(1)
            engine.redact_block(block)
            engine.insert_text(block, text_arg, block.font_size, translated_html=translated_html)

    fresh_path.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(fresh_path))
    emit("Done.")
    return fresh_path


def find_target_page(doc: fitz.Document) -> int | None:
    """Find the (0-indexed) page containing all the reported landmarks, by
    searching the ORIGINAL (untranslated) PDF - "Deities are all Lucifer
    meatsuits" etc. are original English text that would no longer appear
    verbatim in a translated output.
    """
    original_doc = fitz.open(str(PDF_PATH))
    for i in range(len(original_doc)):
        text = original_doc[i].get_text("text")
        if all(s in text for s in LANDMARK_STRINGS):
            return i
    return None


def describe_line_flags(page: fitz.Page, block: TextBlock, highlight_rects: list[fitz.Rect]) -> list[bool]:
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


def main() -> None:
    report: list[str] = []

    def emit(line: str = "") -> None:
        report.append(line)
        print(line)

    is_current = step1_freshness_check(emit)

    if is_current:
        output_path = EXISTING_OUTPUT_PATH
        emit(f"\nUsing existing file as-is: {output_path.relative_to(REPO_ROOT)}")
    else:
        output_path = regenerate_fresh_output(emit)

    # ================= Step 2: diagnosis on the target page =================
    emit("\n" + "=" * 100)
    emit("STEP 2: diagnosis of reported problems (a-d)")
    emit("=" * 100)

    target_page_index = find_target_page(fitz.open(str(PDF_PATH)))
    if target_page_index is None:
        emit("\nCould not locate the target page via landmark strings - aborting Step 2.")
        REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
        return

    emit(f"\nTarget page (0-indexed): {target_page_index}")

    # "Before" state, from the untranslated original PDF.
    original_doc = fitz.open(str(PDF_PATH))
    original_page = original_doc[target_page_index]
    original_highlight_rects = _get_highlight_rects(original_page)

    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(PDF_PATH))
    blocks = engine.extract_blocks(target_page_index)

    emit(f"\nOriginal highlight rects on page {target_page_index}: {len(original_highlight_rects)}")
    for r in original_highlight_rects:
        emit(f"    rect bbox=({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")

    emit(f"\nBlocks from extract_blocks() on page {target_page_index}: {len(blocks)}")
    for i, block in enumerate(blocks):
        bbox = tuple(round(v, 1) for v in block.bbox)
        preview = block.text.replace("\n", " ")[:60]
        line_flags = describe_line_flags(original_page, block, original_highlight_rects)
        emit(
            f"  [{i:>2}] bbox={bbox} highlighted={str(block.highlighted):<5} "
            f'translatable={str(block.translatable):<5} line_flags={line_flags} text="{preview}"'
        )

    # "After" state, from the (existing or freshly generated) translated output.
    output_doc = fitz.open(str(output_path))
    output_page = output_doc[target_page_index]
    output_rects = _get_highlight_rects(output_page)

    emit(f"\nOutput highlight rects on page {target_page_index}: {len(output_rects)}")
    for r in output_rects:
        emit(f"    rect bbox=({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")

    # --- (a) narrow/offset highlight areas: compare per highlighted block ---
    emit("\n--- (a) Per highlighted block: original bbox vs. _associated_highlight_extent() vs. drawn output rects ---")
    highlighted_blocks = [b for b in blocks if b.highlighted]
    for i, block in enumerate(highlighted_blocks):
        original_extent = _associated_highlight_extent(block.bbox, original_highlight_rects)
        bbox_r = tuple(round(v, 1) for v in block.bbox)

        # Output rects overlapping this block's x/y range (candidates for
        # "what actually got drawn behind this block's text").
        overlapping_output_rects = [
            r
            for r in output_rects
            if r.x0 < block.bbox[2] and r.x1 > block.bbox[0]
            and r.y0 < block.bbox[3] + 5 and r.y1 > block.bbox[1] - 5
        ]

        emit(f"\n  highlighted block [{i}] bbox={bbox_r} text={block.text.replace(chr(10), ' ')[:60]!r}")
        emit(f"    _associated_highlight_extent(): {original_extent}")
        emit(f"    overlapping output rects ({len(overlapping_output_rects)}):")
        for r in overlapping_output_rects:
            emit(f"      ({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})")

    # --- (b) wrong/duplicated text: look for identical translated text across DIFFERENT blocks ---
    emit("\n--- (b) Checking for duplicate/identical text landing on different blocks ---")
    # Group blocks by their rendered plain text in the OUTPUT, restricted to
    # this page's x/y area, matched by nearest output text line group.
    seen_texts: dict[str, list[tuple[float, float, float, float]]] = {}
    raw_out = output_page.get_text("dict", flags=_EXTRACT_FLAGS)
    line_records: list[tuple[str, tuple[float, float, float, float]]] = []
    for raw_block in raw_out.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        for line in raw_block.get("lines", []):
            text = _line_text(line.get("spans", [])).strip()
            if text:
                line_records.append((text, tuple(line["bbox"])))

    for text, bbox in line_records:
        seen_texts.setdefault(text, []).append(bbox)

    duplicates = {t: bboxes for t, bboxes in seen_texts.items() if len(bboxes) > 1}
    if not duplicates:
        emit("  No exact-duplicate line texts found on this page's output.")
    for text, bboxes in duplicates.items():
        y_positions = sorted(b[1] for b in bboxes)
        spread = y_positions[-1] - y_positions[0]
        emit(
            f'  text="{text}" appears {len(bboxes)}x at y0={[round(b[1],1) for b in bboxes]} '
            f"(spread={spread:.1f}pt){' <== SUSPECT (far apart, same text)' if spread > 30 else ''}"
        )

    # Also print, per highlighted block in the ORIGINAL (English) and its
    # position in the block list, to make index-mismatch bugs visible: the
    # Nth highlighted block's ENGLISH source text vs. what ends up nearest
    # to that same bbox in the OUTPUT (German).
    emit("\n  Per highlighted block: original (English) text vs. output text found at/near its bbox:")
    for i, block in enumerate(highlighted_blocks):
        bx0, by0, bx1, by1 = block.bbox
        nearby_output_lines = [
            (text, bbox)
            for text, bbox in line_records
            if bbox[1] >= by0 - 5 and bbox[1] <= by1 + 40 and bbox[0] >= bx0 - 10 and bbox[0] <= bx1 + 10
        ]
        original_preview = block.text.replace("\n", " ")[:50]
        emit(f"    [{i}] original={original_preview!r} bbox={tuple(round(v,1) for v in block.bbox)}")
        for text, bbox in nearby_output_lines:
            emit(f"        output line at y0={bbox[1]:.1f}: {text!r}")

    # --- (c) white gaps: check union of ALL originally-overlapping rects vs. what associated_highlight_extent used ---
    emit("\n--- (c) Checking whether _associated_highlight_extent() captures ALL originally-overlapping rects (gap risk) ---")
    for i, block in enumerate(highlighted_blocks):
        all_overlaps = [
            r
            for r in original_highlight_rects
            if min(block.bbox[3], r.y1) - max(block.bbox[1], r.y0) > 0
        ]
        extent = _associated_highlight_extent(block.bbox, original_highlight_rects)
        emit(
            f"  highlighted block [{i}] bbox={tuple(round(v,1) for v in block.bbox)}: "
            f"{len(all_overlaps)} raw-overlapping original rects, "
            f"_associated_highlight_extent={extent}"
        )
        for r in all_overlaps:
            gap_note = ""
            if extent is not None and (r.y0 < extent.y0 - 0.5 or r.y1 > extent.y1 + 0.5):
                gap_note = " <== OUTSIDE the computed extent (potential gap source)"
            emit(f"      rect=({r.x0:.1f},{r.y0:.1f},{r.x1:.1f},{r.y1:.1f}){gap_note}")

    # --- (d) narrow/compressed font: inspect actual output font sizes vs. block.font_size ---
    # Scan window is bounded by the NEXT block in the full (all-blocks,
    # translatable or not) y0-sorted list, not a flat +N margin - a flat
    # margin risks scooping up a neighboring block's own (possibly
    # differently-sized) text and misattributing its font size to this
    # block, the same class of measurement artifact found repeatedly in
    # earlier diagnostics (tests/manual_diagnose_highlight_pages_real.py).
    emit("\n--- (d) Output font sizes vs. block.font_size for highlighted blocks (tightly bounded scan) ---")
    all_blocks_sorted = sorted(blocks, key=lambda b: b.bbox[1])
    for i, block in enumerate(highlighted_blocks):
        bx0, by0, bx1, by1 = block.bbox
        idx_in_all = all_blocks_sorted.index(block)
        if idx_in_all + 1 < len(all_blocks_sorted):
            scan_bottom = all_blocks_sorted[idx_in_all + 1].bbox[1] - 0.5
        else:
            scan_bottom = by1 + 150.0

        raw = output_page.get_text("dict", flags=_EXTRACT_FLAGS)
        sizes: list[float] = []
        widths_per_char: list[float] = []
        for raw_block in raw.get("blocks", []):
            if raw_block.get("type") != 0:
                continue
            for line in raw_block.get("lines", []):
                lx0, ly0, lx1, ly1 = line["bbox"]
                if ly0 < by0 - 2 or ly0 > scan_bottom or lx1 < bx0 - 5 or lx0 > bx1 + 250:
                    continue
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    sizes.append(span.get("size", 0.0))
                    span_bbox = span.get("bbox", (0, 0, 0, 0))
                    span_width = span_bbox[2] - span_bbox[0]
                    if len(text) > 0:
                        widths_per_char.append(span_width / len(text))
        if not sizes:
            emit(f"  highlighted block [{i}] bbox={tuple(round(v,1) for v in block.bbox)}: no spans found in bounded window")
            continue
        min_size = min(sizes)
        emit(
            f"  highlighted block [{i}] bbox={tuple(round(v,1) for v in block.bbox)} "
            f"scan_bottom={scan_bottom:.1f} block.font_size={block.font_size:.1f} | "
            f"output span sizes: min={min_size:.1f} max={max(sizes):.1f} "
            f"| avg width/char={sum(widths_per_char)/len(widths_per_char):.2f}"
            f"{' <== MUCH SMALLER than block.font_size' if min_size < block.font_size * 0.6 else ''}"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"\nFull report written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
