"""Translate both sample PDFs through all three real translation providers.

For 2182 INDELEGATA.pdf and 1526 Virelicon.pdf, x GoogleTranslateProvider,
DeepLProvider, GrokProvider (no OpenAI - known account quota issue, see
Backlog.md): runs the full open -> extract_blocks -> redact_block ->
translate_html/translate -> insert_text -> save pipeline, using a copy of
TEMPLATE with first_page_zones cleared so page 0's metadata/title
separation relies entirely on the FIRST_PAGE_ANCHOR_TERMS split in
pipeline/pdf/pymupdf_engine.py. Writes "<stem>_DE_<provider>.pdf" per pair
(6 files total). Each (PDF, provider) pair is independent: a failure
(TranslationError, quota, etc.) is reported and the script moves on. Not a
pytest test - run manually:

    python tests/manual_translate_all_providers.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import FIRST_PAGE_ANCHOR_TERMS, PyMuPdfEngine, spans_to_html
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from tests.manual_e2e_pipeline import TEMPLATE

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATHS = [
    REPO_ROOT / "2182 INDELEGATA.pdf",
    REPO_ROOT / "1526 Virelicon.pdf",
]
TARGET_LANG = "de"
SOURCE_LANG = "en"

# first_page_zones cleared: only FIRST_PAGE_ANCHOR_TERMS should exclude the
# page-0 metadata now.
TEMPLATE_NO_ZONES = dataclasses.replace(TEMPLATE, first_page_zones=None)

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


def check_anchor_split(engine: PyMuPdfEngine) -> tuple[bool, str]:
    """Check whether page 0's anchor-term metadata chunk was excluded from
    translation and a translatable block (the title/subtitle) follows it.
    Provider-independent (extract_blocks() alone). Returns (fired, detail).
    """
    blocks = sorted(engine.extract_blocks(0), key=lambda block: block.bbox[1])
    metadata_block = next(
        (
            block
            for block in blocks
            if not block.translatable
            and any(term.lower() in block.text.lower() for term in FIRST_PAGE_ANCHOR_TERMS)
        ),
        None,
    )
    if metadata_block is None:
        return False, "no non-translatable anchor-term block found on page 0"

    following = [
        block
        for block in blocks
        if block.translatable and block.bbox[1] >= metadata_block.bbox[1]
    ]
    if not following:
        return False, "anchor-term block excluded, but no translatable block follows it"

    metadata_preview = metadata_block.text.replace("\n", " ")[:80]
    title_preview = following[0].text.replace("\n", " ")[:80]
    return True, f'metadata (untranslated)="{metadata_preview}" | next translatable="{title_preview}"'


def run_pair(
    pdf_path: Path, provider_name: str, make_provider: Callable[[], TranslationProvider]
) -> tuple[bool, str]:
    """Run the full translate-and-save pipeline for one (PDF, provider) pair.

    Returns (success, message). On a TranslationError partway through, no
    output file is written and the error is returned as the message.
    """
    output_path = pdf_path.parent / f"{pdf_path.stem}_DE_{provider_name}.pdf"

    engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
    engine.open(str(pdf_path))
    provider = make_provider()

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
    results: list[tuple[str, str, bool, str]] = []
    anchor_results: list[tuple[str, bool, str]] = []

    for pdf_path in PDF_PATHS:
        if not pdf_path.exists():
            print(f"PDF not found: {pdf_path}")
            sys.exit(1)

        probe_engine = PyMuPdfEngine(template=TEMPLATE_NO_ZONES)
        probe_engine.open(str(pdf_path))
        fired, detail = check_anchor_split(probe_engine)
        anchor_results.append((pdf_path.name, fired, detail))

        for provider_name, make_provider in PROVIDERS:
            print(f"=== {pdf_path.name} | {provider_name} ===")
            success, message = run_pair(pdf_path, provider_name, make_provider)
            print(message)
            print()
            results.append((pdf_path.name, provider_name, success, message))

    print("=== Anchor split check (page 0) ===")
    for pdf_name, fired, detail in anchor_results:
        status = "OK" if fired else "NOT DETECTED"
        print(f"{pdf_name:<25} {status:<13} {detail}")
    print()

    print("=== Translation summary ===")
    for pdf_name, provider_name, success, message in results:
        status = "OK" if success else "FAILED"
        print(f"{pdf_name:<25} {provider_name:<8} {status:<7} {message}")


if __name__ == "__main__":
    main()
