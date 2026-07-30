"""Real-translation end-to-end test for the PdfEngine pipeline.

Like tests/manual_e2e_pipeline.py (which stays unchanged and uses an
artificial placeholder text), but runs open -> extract_blocks ->
redact_block -> insert_text -> save with actual, formatting-preserving
translations: each block's spans are rendered to HTML (spans_to_html()),
translated as HTML via GoogleTranslateProvider.translate_html() (so inline
bold/italic survives), and the translated HTML is inserted directly via
insert_text()'s translated_html parameter. Wrapped in TranslationBudgetGuard
for a cost estimate, a confirmation prompt, and a hard per-run character
cap. Not a pytest test - run manually:

    python tests/manual_e2e_pipeline_real_translation.py path/to/file.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html
from pipeline.translation.cost_control import (
    GOOGLE_PRICING,
    TranslationBudgetGuard,
    get_month_usage,
)
from pipeline.translation.google_provider import GoogleTranslateProvider
from tests.manual_e2e_pipeline import TEMPLATE

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "e2e_real_translation_output.pdf"
TARGET_LANG = "de"
SOURCE_LANG = "en"


def collect_translatable_blocks(engine: PyMuPdfEngine) -> list[TextBlock]:
    """Extract all translatable blocks across every page, before any redaction."""
    blocks: list[TextBlock] = []
    for page in engine.get_pages():
        for block in engine.extract_blocks(page.index):
            if block.translatable:
                blocks.append(block)
    return blocks


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_e2e_pipeline_real_translation.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    engine = PyMuPdfEngine(template=TEMPLATE)
    engine.open(pdf_path)

    provider = TranslationBudgetGuard(
        GoogleTranslateProvider(), pricing=GOOGLE_PRICING, max_chars_per_run=200_000
    )

    blocks = collect_translatable_blocks(engine)
    if not blocks:
        print("No translatable blocks found.")
        return

    # Original (untranslated) HTML per block, built the same way insert_text()
    # would build it internally if no translated_html were given - this is
    # what actually gets sent to Google (and billed/logged), not block.text.
    original_html = [spans_to_html(block.spans) for block in blocks]
    char_count, estimated_cost = provider.estimate_run(original_html)
    usage_so_far = get_month_usage(GOOGLE_PRICING.provider_name)
    print(f"Estimated: {char_count} characters, ~${estimated_cost:.2f} (this month's usage so far: {usage_so_far})")

    if not provider.confirm_run(original_html):
        print("Aborted: translation not confirmed. Nothing was changed or saved.")
        return

    usage_before = get_month_usage(GOOGLE_PRICING.provider_name)
    translated_html = [
        provider.translate_html(html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG).text
        for html in original_html
    ]

    total_blocks = 0
    overflow_blocks = 0
    total_translated_chars = 0

    for block, html in zip(blocks, translated_html):
        engine.redact_block(block)
        # `text=block.text` is required by insert_text()'s signature but is
        # NOT actually used here: block.spans is non-empty and
        # translated_html is given, so the entire fit fallback (font
        # shrink -> width widen -> height grow) operates on translated_html
        # directly - `text` is only consulted when block.spans is empty.
        fit = engine.insert_text(
            block, text=block.text, font_size=block.font_size, translated_html=html
        )

        total_blocks += 1
        total_translated_chars += len(html)
        if not fit:
            overflow_blocks += 1

        bbox = tuple(round(v, 1) for v in block.bbox)
        print(f"page={block.page_index:>3} | bbox={bbox} | fit={str(fit):<5}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(OUTPUT_PATH))

    billed_chars = get_month_usage(GOOGLE_PRICING.provider_name) - usage_before
    actual_cost = provider.estimate_cost(billed_chars, usage_before)

    print()
    print(f"blocks translated: {total_blocks}")
    print(f"overflow cases (fit=False): {overflow_blocks}")
    print(f"total translated characters: {total_translated_chars}")
    print(f"estimated cost (pre-run): ${estimated_cost:.2f}")
    print(f"actual cost (from usage log this run): ${actual_cost:.2f}")
    print(f"output written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
