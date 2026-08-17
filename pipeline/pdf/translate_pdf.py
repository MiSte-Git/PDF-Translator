"""Reusable full-document PDF translation pass.

Mirrors pipeline.presentation.translate_presentation.translate_presentation()
and pipeline.word.translate_document.translate_document() - same shape
(cooperative cancellation polled between, never during, API calls;
progress/stats callbacks; one bad block's TranslationError is caught and
counted as failed rather than aborting the whole run, the same "skip,
don't abort" policy used by both other formats) - so ui/pdf_job.py can
drive the exact same Start/progress/cancel/QA-report UI flow
(ui/app.py::_EXECUTABLE_MODES) that ui/pptx_job.py and ui/word_job.py
already use.

Different from every existing PDF entry point (tools/compare_providers.py,
tests/manual_translate_indelegata.py, tests/manual_diagnose_text_duplication.py):
those translate every block first (all-or-nothing per provider run, no
progress/cancellation) and only then redact+insert. This module instead
interleaves translate -> redact -> insert per block, one at a time, so a
cancelled run keeps every already-written block and the UI can show live
progress - the same reason PPTX/Word don't use an all-or-nothing pass
either.

Opening the source document and saving the result afterwards stays the
CALLER's job (ui/pdf_job.py) - translate_pdf() only mutates an
already-open PyMuPdfEngine in place, matching translate_document()'s
division of responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pipeline.pdf.base import PdfEngine, TextBlock
from pipeline.pdf.pymupdf_engine import spans_to_html
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.protected_terms import protect_terms, restore_terms


@dataclass
class PdfTranslationStats:
    """translate_pdf()'s result. Flat (translated/skipped/failed), unlike
    TranslationStats' body_/header_/footer_ split for Word - a PDF page has
    no equivalent structural split (see PdfJobResult/ui/pdf_job.py's QA
    report for how overflow_blocks is surfaced instead).
    """
    translated: int = 0
    skipped: int = 0
    failed: int = 0
    chars_sent: int = 0
    overflow_blocks: int = 0
    """Number of translated blocks whose insert_text() call returned False
    (see PdfEngine.insert_text()) - it grew, shrank, or was force-fit
    rather than dropping in cleanly at the original size/position. Not an
    error (the text was never lost - see pymupdf_engine.py's collision-
    aware growth/shrink fallback), but worth surfacing in the QA report as
    "these are the blocks most worth a manual look"."""
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)
    """Human-readable "page:block: exception" strings for every failed
    block, same role as the other two formats' equivalent field - never
    includes credentials (TranslationError messages are already
    credential-free)."""

    @property
    def processed(self) -> int:
        return self.translated + self.skipped + self.failed


def total_block_count(engine: PdfEngine) -> int:
    """Total number of blocks (translatable and not) translate_pdf() will
    eventually report a final outcome for, across every page. Mirrors
    pipeline.presentation.translate_presentation.total_paragraph_count()/
    pipeline.word.translate_document.total_paragraph_count() - cheap (no
    API calls), lets a caller (ui/pdf_job.py) show a determinate "X of N
    blocks" progress bar instead of an indeterminate one.
    """
    return sum(len(engine.extract_blocks(page.index)) for page in engine.get_pages())


def translate_pdf(
    engine: PdfEngine,
    provider: TranslationProvider,
    protected_terms: list[str],
    target_lang: str,
    source_lang: str | None = "en",
    progress_callback: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    stats_callback: Callable[[PdfTranslationStats], None] | None = None,
) -> PdfTranslationStats:
    """Translate every translatable block of `engine`'s already-open
    document IN PLACE (via engine.redact_block()/insert_text()). Does not
    open or save the document - see the module docstring for why that
    stays the caller's job.

    Blocks are gathered for EVERY page up front (via engine.extract_blocks()
    per page, before any redaction anywhere) rather than page-by-page as
    translation proceeds - required for `total_callback`-style upfront
    counts (see total_block_count()) to reflect reality, and safe because
    extract_blocks() only reads; nothing is redacted until this function's
    main loop below actually reaches that block. Matches
    tests/manual_translate_indelegata.py's collect_translatable_blocks()
    for the same reason.

    A single block's TranslationError is caught and counted as failed
    rather than re-raised, so one bad block never aborts the rest of the
    document - see the module docstring.

    `should_cancel`, if given, is polled before each block (between API
    calls, never mid-call) - once it returns True, stats.cancelled is set
    and the run stops; every block already translated/redacted stays that
    way, the rest is left untouched (original English), matching the other
    two formats' cancellation contract.

    `stats_callback`, if given, is called after every block reaches a
    final outcome (translated/skipped/failed) with the current cumulative
    `stats`, letting a caller (ui/pdf_job.py) drive a live progress
    display without polling.
    """
    stats = PdfTranslationStats()

    def _notify(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    def _report() -> None:
        if stats_callback is not None:
            stats_callback(stats)

    def _cancelled() -> bool:
        return should_cancel is not None and should_cancel()

    all_blocks: list[tuple[int, int, TextBlock]] = [
        (page.index, block_index, block)
        for page in engine.get_pages()
        for block_index, block in enumerate(engine.extract_blocks(page.index))
    ]

    for page_index, block_index, block in all_blocks:
        if _cancelled():
            stats.cancelled = True
            break
        if not block.translatable:
            stats.skipped += 1
            _report()
            continue

        _notify(f"Seite {page_index + 1}, Block {block_index + 1}...")
        try:
            if block.spans:
                html = spans_to_html(block.spans)
                protected_html, mapping = protect_terms(html, protected_terms)
                result = provider.translate_html(
                    protected_html, target_lang=target_lang, source_lang=source_lang
                )
                translated_html = restore_terms(result.text, mapping)
                text_arg = block.text  # ignored by insert_text() when translated_html is given
                sent = len(protected_html)
            else:
                protected_text, mapping = protect_terms(block.text, protected_terms)
                result = provider.translate(
                    protected_text, target_lang=target_lang, source_lang=source_lang
                )
                text_arg = restore_terms(result.text, mapping)
                translated_html = None
                sent = len(protected_text)
        except TranslationError as exc:
            _notify(f"  FEHLER (uebersprungen): {exc}")
            stats.failed += 1
            stats.errors.append(f"page{page_index}:block{block_index}: {type(exc).__name__}: {exc}")
            _report()
            continue

        stats.chars_sent += sent
        engine.redact_block(block)
        fit = engine.insert_text(block, text_arg, block.font_size, translated_html=translated_html)
        if not fit:
            stats.overflow_blocks += 1
        stats.translated += 1
        _report()

    return stats
