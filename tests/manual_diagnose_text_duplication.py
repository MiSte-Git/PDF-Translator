"""Diagnosis for three reported problems in real-translation output of
"1526 Virelicon.pdf", independent of the highlight feature:

  1. Text duplication: after a text section, a truncated remainder of the
     SAME text appears again (e.g. "...essence The Prism's metaphysical b").
  2. Unexplained suffixes on attribution lines ("- Manuel to PQ - M",
     "- PQ to Manuel - P", "Father F") not present in the original.
  3. On the "Prism's metaphysical brilliance" heading + 5-bullet block:
     bold/underline formatting lost and the heading merges with the first
     bullet onto one line; growing gaps between the 5 bullet blocks.

Method: monkeypatches fitz.Page.add_redact_annot/apply_redactions/
insert_htmlbox/insert_textbox/draw_rect to log every page-mutating call
(method, target rect, fontsize where derivable, return value) in order -
this only wraps methods for observation during this script's own run, it
does not modify any pipeline/*.py file. Runs the real DeepL translation
pipeline for the specific blocks under investigation and reports:
  - the raw block.text / _build_text_spans() output (formatting check),
  - the exact text/HTML sent to translate()/translate_html(),
  - the raw API response text,
  - the full ordered log of redact/insert calls for that block,
  - each block's final rect/insert_bbox (for the growing-gaps check).

Not a pytest test - run manually:

    python tests/manual_diagnose_text_duplication.py

Full output written to
tests/output/manual_diagnose_text_duplication_output.txt; a short summary
is printed to the console. Diagnosis only - no pipeline code is changed.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html
from pipeline.translation.base import TranslationError
from pipeline.translation.cost_control import DEEPL_PRICING, TranslationBudgetGuard
from pipeline.translation.deepl_provider import DeepLProvider
from tests.manual_e2e_pipeline import TEMPLATE

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "1526 VIRELICON.pdf"
OUTPUT_PDF_PATH = REPO_ROOT / "tests" / "output" / "text_duplication_diagnose_output.pdf"
REPORT_PATH = REPO_ROOT / "tests" / "output" / "manual_diagnose_text_duplication_output.txt"

TARGET_LANG = "de"
SOURCE_LANG = "en"
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)

# Found by string search against the original PDF (see conversation) -
# page_index 2 has the "Manuel to PQ"/"PQ to Manuel"/"Father" quote/
# attribution blocks, page_index 4 has the "Prism's metaphysical
# brilliance" heading + 5 bullets.
QUOTE_PAGE = 2
BULLET_PAGE = 4
PAGES_TO_PROCESS = sorted({QUOTE_PAGE, BULLET_PAGE})

# ================= call-logging monkeypatch =================
call_log: list[dict] = []
_current_tag: str | None = None


def _rect_tuple(rect_like) -> tuple[float, float, float, float]:
    r = fitz.Rect(rect_like)
    return (round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2))


def _install_patches() -> None:
    orig_add_redact = fitz.Page.add_redact_annot
    orig_apply_redact = fitz.Page.apply_redactions
    orig_insert_htmlbox = fitz.Page.insert_htmlbox
    orig_insert_textbox = fitz.Page.insert_textbox
    orig_draw_rect = fitz.Page.draw_rect

    def logged_add_redact_annot(self, rect, *args, **kwargs):
        call_log.append({"tag": _current_tag, "call": "add_redact_annot", "rect": _rect_tuple(rect)})
        return orig_add_redact(self, rect, *args, **kwargs)

    def logged_apply_redactions(self, *args, **kwargs):
        call_log.append({"tag": _current_tag, "call": "apply_redactions"})
        return orig_apply_redact(self, *args, **kwargs)

    def logged_insert_htmlbox(self, rect, text, *args, **kwargs):
        result = orig_insert_htmlbox(self, rect, text, *args, **kwargs)
        css = kwargs.get("css", "")
        call_log.append(
            {
                "tag": _current_tag,
                "call": "insert_htmlbox",
                "rect": _rect_tuple(rect),
                "css": css,
                "scale_low": kwargs.get("scale_low"),
                "result": result,
                "text_preview": text[:80],
            }
        )
        return result

    def logged_insert_textbox(self, rect, text, *args, **kwargs):
        result = orig_insert_textbox(self, rect, text, *args, **kwargs)
        call_log.append(
            {
                "tag": _current_tag,
                "call": "insert_textbox",
                "rect": _rect_tuple(rect),
                "fontsize": kwargs.get("fontsize"),
                "result": result,
                "text_preview": text[:80],
            }
        )
        return result

    def logged_draw_rect(self, rect, *args, **kwargs):
        result = orig_draw_rect(self, rect, *args, **kwargs)
        call_log.append(
            {"tag": _current_tag, "call": "draw_rect", "rect": _rect_tuple(rect), "fill": kwargs.get("fill")}
        )
        return result

    fitz.Page.add_redact_annot = logged_add_redact_annot
    fitz.Page.apply_redactions = logged_apply_redactions
    fitz.Page.insert_htmlbox = logged_insert_htmlbox
    fitz.Page.insert_textbox = logged_insert_textbox
    fitz.Page.draw_rect = logged_draw_rect


def set_tag(tag: str | None) -> None:
    global _current_tag
    _current_tag = tag


def main() -> None:
    if not PDF_PATH.exists():
        print(f"File not found: {PDF_PATH}")
        sys.exit(1)

    report: list[str] = []

    def emit(line: str = "") -> None:
        report.append(line)

    _install_patches()

    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(PDF_PATH))
    provider = DeepLProvider()
    guard = TranslationBudgetGuard(provider, DEEPL_PRICING)

    per_page_blocks: dict[int, list[TextBlock]] = {}
    for page_index in PAGES_TO_PROCESS:
        per_page_blocks[page_index] = engine.extract_blocks(page_index)

    # ================= Part 3a: raw _build_text_spans() output for the heading block =================
    emit("=" * 100)
    emit("PART 3a: raw extract_blocks()/_build_text_spans() output for the heading+bullet blocks (page %d)" % BULLET_PAGE)
    emit("=" * 100)
    bullet_blocks = [
        b for b in per_page_blocks[BULLET_PAGE]
        if b.translatable and ("metaphysical" in b.text.lower() or b.text.strip().startswith("⚫") or "prism" in b.text.lower())
    ]
    for i, b in enumerate(bullet_blocks):
        emit(f"\n--- bullet-area block [{i}] bbox={tuple(round(v,1) for v in b.bbox)} highlighted={b.highlighted} ---")
        emit(f"  block.text = {b.text!r}")
        emit(f"  spans ({len(b.spans)}):")
        for s in b.spans:
            emit(f"    text={s.text!r} bold={s.bold} underline={s.underline} italic={s.italic}")
        emit(f"  spans_to_html() = {spans_to_html(b.spans)!r}")

    # ================= translate + write, with call logging =================
    emit("\n" + "=" * 100)
    emit("PART 1/2/3b: translating + writing, with full redact/insert call log per block")
    emit("=" * 100)

    block_html_sent: dict[int, str] = {}
    block_api_result: dict[int, str] = {}

    for page_index in PAGES_TO_PROCESS:
        for block in per_page_blocks[page_index]:
            if not block.translatable:
                continue
            tag = f"page{page_index}_bbox{tuple(round(v,1) for v in block.bbox)}"
            try:
                if block.spans:
                    html = spans_to_html(block.spans)
                    block_html_sent[id(block)] = html
                    result = guard.translate_html(html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
                    translated_html = result.text
                    block_api_result[id(block)] = translated_html
                    text_arg = block.text
                else:
                    block_html_sent[id(block)] = block.text
                    result = guard.translate(block.text, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
                    translated_html = None
                    block_api_result[id(block)] = result.text
                    text_arg = result.text
            except TranslationError as exc:
                emit(f"TranslationError on page {page_index}, block {block.bbox}: {exc}")
                sys.exit(1)

            set_tag(tag)
            engine.redact_block(block)
            engine.insert_text(block, text_arg, block.font_size, translated_html=translated_html)
            set_tag(None)

    OUTPUT_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(OUTPUT_PDF_PATH))
    emit(f"\nOutput written to: {OUTPUT_PDF_PATH}")

    # ================= Part 1: full call log for the heading+bullets and quote blocks =================
    emit("\n--- PART 1: full ordered redact/insert call log, per block ---")
    all_target_blocks = [
        (page_index, b)
        for page_index in PAGES_TO_PROCESS
        for b in per_page_blocks[page_index]
        if b.translatable
    ]
    for page_index, b in all_target_blocks:
        tag = f"page{page_index}_bbox{tuple(round(v,1) for v in b.bbox)}"
        entries = [c for c in call_log if c["tag"] == tag]
        if not entries:
            continue
        emit(f"\n  block tag={tag} highlighted={b.highlighted} text={b.text.replace(chr(10),' ')[:50]!r}")
        emit(f"    original (English) sent: {block_html_sent.get(id(b), '')[:120]!r}")
        emit(f"    API result (translated): {block_api_result.get(id(b), '')[:200]!r}")
        for entry in entries:
            call = entry["call"]
            if call == "insert_htmlbox":
                emit(
                    f"    [{call}] rect={entry['rect']} scale_low={entry['scale_low']} "
                    f"result={entry['result']} css={entry['css']!r}"
                )
            elif call == "insert_textbox":
                emit(f"    [{call}] rect={entry['rect']} fontsize={entry['fontsize']} result={entry['result']}")
            elif call == "add_redact_annot":
                emit(f"    [{call}] rect={entry['rect']}")
            elif call == "draw_rect":
                emit(f"    [{call}] rect={entry['rect']} fill={entry['fill']}")
            else:
                emit(f"    [{call}] {entry}")

    # ================= Part 3b: growing-gaps check for the 5 bullets =================
    emit("\n--- PART 3b: bullet block final positions (growing-gaps check) ---")
    bullet_translatable = [b for b in bullet_blocks if b.translatable]
    for i, b in enumerate(bullet_translatable):
        tag = f"page{BULLET_PAGE}_bbox{tuple(round(v,1) for v in b.bbox)}"
        entries = [c for c in call_log if c["tag"] == tag and c["call"] in ("insert_htmlbox", "insert_textbox")]
        final_rect = entries[-1]["rect"] if entries else None
        original_height = round(b.bbox[3] - b.bbox[1], 1)
        final_height = round(final_rect[3] - final_rect[1], 1) if final_rect else None
        emit(
            f"  bullet [{i}] original bbox={tuple(round(v,1) for v in b.bbox)} "
            f"(height={original_height}) -> final insert rect={final_rect} "
            f"(height={final_height})"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    # ================= console summary =================
    print(f"Full report written to: {REPORT_PATH}")
    print(f"Total logged page-mutating calls: {len(call_log)}")
    for page_index, b in all_target_blocks:
        tag = f"page{page_index}_bbox{tuple(round(v,1) for v in b.bbox)}"
        entries = [c for c in call_log if c["tag"] == tag]
        insert_calls = [c for c in entries if c["call"] in ("insert_htmlbox", "insert_textbox")]
        successful_inserts = [c for c in insert_calls if (c["call"] == "insert_htmlbox" and c["result"][0] >= 0) or (c["call"] == "insert_textbox" and c["result"] >= 0)]
        print(
            f"  page {page_index} block {tuple(round(v,1) for v in b.bbox)}: "
            f"{len(insert_calls)} insert attempt(s), {len(successful_inserts)} successful, "
            f"{sum(1 for c in entries if c['call'] == 'add_redact_annot')} redact(s)"
        )


if __name__ == "__main__":
    main()
