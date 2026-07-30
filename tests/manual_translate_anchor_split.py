"""Verify extract_blocks()'s new FIRST_PAGE_ANCHOR_TERMS split end-to-end.

Like tests/manual_translate_indelegata.py, but: (1) takes any PDF path as an
argument instead of being hardcoded to one file, (2) only runs
GoogleTranslateProvider (sufficient to verify the split; no need to spend
DeepL/Grok quota on this), and (3) uses a copy of TEMPLATE with
first_page_zones cleared, so page 0's metadata/title separation relies
entirely on the new anchor-term split in pipeline/pdf/pymupdf_engine.py,
not on the pre-existing fixed-zone exclusion. Writes
"<stem>_DE_google_anchorsplit.pdf" next to the original. Not a pytest test -
run manually:

    python tests/manual_translate_anchor_split.py path/to/file.pdf
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html
from pipeline.translation.base import TranslationError
from pipeline.translation.google_provider import GoogleTranslateProvider
from tests.manual_e2e_pipeline import TEMPLATE

TARGET_LANG = "de"
SOURCE_LANG = "en"

# first_page_zones cleared: only FIRST_PAGE_ANCHOR_TERMS should be excluding
# the page-0 metadata now.
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)


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
        print("Usage: python tests/manual_translate_anchor_split.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    output_path = pdf_path.parent / f"{pdf_path.stem}_DE_google_anchorsplit.pdf"

    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(pdf_path))
    provider = GoogleTranslateProvider()

    # Report page-0 translatable/non-translatable blocks for direct
    # before/after inspection of the anchor split.
    print(f"--- page 0 blocks (translatable status after anchor split) ---")
    for block in engine.extract_blocks(0):
        bbox = tuple(round(v, 1) for v in block.bbox)
        print(f"translatable={block.translatable} | bbox={bbox}")
        print(f"  {block.text!r}")
    print()

    blocks = collect_translatable_blocks(engine)

    try:
        translations: list[tuple[TextBlock, str, str | None]] = []
        for block in blocks:
            if block.spans:
                html = spans_to_html(block.spans)
                result = provider.translate_html(html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
                translations.append((block, block.text, result.text))
            else:
                result = provider.translate(block.text, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
                translations.append((block, result.text, None))
    except TranslationError as exc:
        print(f"TranslationError: {exc}")
        sys.exit(1)

    overflow_blocks = 0
    for block, text, translated_html in translations:
        engine.redact_block(block)
        fit = engine.insert_text(block, text=text, font_size=block.font_size, translated_html=translated_html)
        if not fit:
            overflow_blocks += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(output_path))

    overflow_note = f", {overflow_blocks} overflow block(s)" if overflow_blocks else ""
    print(f"{len(translations)} blocks translated{overflow_note} -> {output_path.name}")


if __name__ == "__main__":
    main()
