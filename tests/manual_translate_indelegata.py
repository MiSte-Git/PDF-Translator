"""Translate 2182 INDELEGATA.pdf end-to-end through multiple real providers.

For each of GoogleTranslateProvider, DeepLProvider, and GrokProvider, runs a
full open -> extract_blocks -> translate -> redact_block -> insert_text ->
save pass (formatting-preserving translate_html() for blocks with spans,
plain translate() otherwise) and writes
"2182 INDELEGATA_DE_<provider>.pdf" next to the original. Providers run
independently: a failure in one (TranslationError, quota, etc.) is reported
and the script moves on to the next. Not a pytest test - run manually:

    python tests/manual_translate_indelegata.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, spans_to_html
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from tests.manual_e2e_pipeline import TEMPLATE

PDF_PATH = Path(__file__).resolve().parent.parent / "2182 INDELEGATA.pdf"
TARGET_LANG = "de"
SOURCE_LANG = "en"

# (output-filename suffix, provider factory) - exact names/order as requested.
PROVIDERS: list[tuple[str, Callable[[], TranslationProvider]]] = [
    ("google", GoogleTranslateProvider),
    ("deepl", DeepLProvider),
    ("grok", GrokProvider),
]


def collect_translatable_blocks(engine: PyMuPdfEngine) -> list[TextBlock]:
    """Extract all translatable blocks across every page, before any redaction."""
    blocks: list[TextBlock] = []
    for page in engine.get_pages():
        for block in engine.extract_blocks(page.index):
            if block.translatable:
                blocks.append(block)
    return blocks


def run_provider(name: str, make_provider: Callable[[], TranslationProvider]) -> tuple[bool, str]:
    """Run the full translate-and-save pipeline for one provider.

    Returns (success, message). On a TranslationError partway through, no
    output file is written for this provider and the error is returned as
    the message.
    """
    output_path = PDF_PATH.parent / f"2182 INDELEGATA_DE_{name}.pdf"

    engine = PyMuPdfEngine(template=TEMPLATE)
    engine.open(str(PDF_PATH))
    provider = make_provider()

    blocks = collect_translatable_blocks(engine)

    # Translate first (all-or-nothing): translated text/HTML per block, in
    # the form insert_text() expects (text= for plain, translated_html= for
    # spans-based blocks).
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
        return False, f"TranslationError: {exc}"

    overflow_blocks = 0
    for block, text, translated_html in translations:
        engine.redact_block(block)
        fit = engine.insert_text(block, text=text, font_size=block.font_size, translated_html=translated_html)
        if not fit:
            overflow_blocks += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(output_path))

    overflow_note = f", {overflow_blocks} overflow block(s)" if overflow_blocks else ""
    return True, f"{len(translations)} blocks translated{overflow_note} -> {output_path.name}"


def main() -> None:
    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        sys.exit(1)

    results: list[tuple[str, bool, str]] = []
    for name, make_provider in PROVIDERS:
        print(f"=== {name} ===")
        success, message = run_provider(name, make_provider)
        print(message)
        print()
        results.append((name, success, message))

    print("=== Summary ===")
    for name, success, message in results:
        status = "OK" if success else "FAILED"
        print(f"{name:<8} {status:<7} {message}")


if __name__ == "__main__":
    main()
