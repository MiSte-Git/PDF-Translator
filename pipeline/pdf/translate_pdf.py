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
from pipeline.pdf.pymupdf_engine import _plain_text_to_html, html_to_plain_text, spans_to_html
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.protected_terms import protect_terms, restore_terms


@dataclass
class TranslatedBlockRecord:
    """One successfully-translated block, captured during translate_pdf()
    for later manual correction (RoadMap.md Phase 2/PDF's "PDF-Übersetzung
    korrigieren" item - a user found a real mistranslation, a proper name
    "Manuel" rendered as "Handbuch", in a live run against
    "1526 VIRELICON.pdf") - see apply_pdf_corrections() below, which turns
    an edited list of these back into redact_block()/insert_text() calls
    against a FRESH engine reopened on the pristine source PDF, never the
    already-mutated one translate_pdf() worked on: redact_block()/
    insert_text() mutate the open document in place, so reusing the same
    engine instance for a correction pass would redact/insert on top of
    the FIRST pass's already-translated result instead of the clean
    original - see apply_pdf_corrections()'s docstring.

    page_index/block_index together locate the exact same TextBlock again
    via a fresh engine.extract_blocks(page_index)[block_index] call -
    extract_blocks() is a pure, read-only function of a page's content
    (see its own docstring), so it reproduces the identical block
    list/order on a second call against the SAME, untouched source file.

    Only populated for the block.spans (HTML/Story) branch of
    translate_pdf()'s main loop below - the only one real production
    callers ever reach (see PyMuPdfEngine.insert_text()'s docstring:
    block.spans is always populated for real extracted blocks). A block
    that went through the plain-text fallback branch (translated_html is
    None, block.spans empty) isn't correctable via this record type - not
    currently reachable in practice, so not a real limitation, just
    documented here for honesty.
    """
    page_index: int
    block_index: int
    original_text: str
    translated_html: str

    @property
    def display_text(self) -> str:
        """Human-editable plain-text projection of translated_html - see
        html_to_plain_text(). Inline formatting (bold/italic/underline) is
        deliberately not shown or editable here - see
        apply_pdf_corrections()'s docstring for what happens to it when a
        row IS edited.
        """
        return html_to_plain_text(self.translated_html)


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
    blocks: list[TranslatedBlockRecord] = field(default_factory=list)
    """One TranslatedBlockRecord per successfully-translated block, in
    processing order - see that class's docstring. Purely additive: every
    existing caller that only reads translated/skipped/failed/chars_sent/
    overflow_blocks/cancelled/errors is unaffected. Empty for a stats
    object returned by apply_pdf_corrections() below - a correction pass
    doesn't itself produce further correctable records (nothing stops a
    caller from re-running the correction UI again from the same original
    `blocks` list, though - see apply_pdf_corrections()'s docstring)."""

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
        if translated_html is not None:
            # See TranslatedBlockRecord's docstring for why only this
            # branch (block.spans populated - the only one real
            # production callers reach) is captured.
            stats.blocks.append(
                TranslatedBlockRecord(
                    page_index=page_index,
                    block_index=block_index,
                    original_text=block.text,
                    translated_html=translated_html,
                )
            )
        _report()

    return stats


def apply_pdf_corrections(
    engine: PdfEngine,
    records: list[TranslatedBlockRecord],
) -> PdfTranslationStats:
    """Apply a (possibly user-edited) list of TranslatedBlockRecord back
    into `engine`'s already-open document via redact_block()/insert_text(),
    without any translation-provider calls - see TranslatedBlockRecord's
    docstring for the correction-table workflow this supports (RoadMap.md
    Phase 2/PDF's "PDF-Übersetzung korrigieren" item).

    CRITICAL precondition, the caller's responsibility: `engine` must be
    freshly opened on the PRISTINE source PDF - the same file
    translate_pdf() originally ran against, untouched since (translate_pdf()
    itself never writes back to the source; only the caller-chosen
    destination file is ever saved to - see that function's module
    docstring). Reusing the SAME engine instance translate_pdf() already
    redacted/inserted into would redact/insert this correction on top of
    the FIRST pass's output instead of the clean original - block.bbox
    would still be right (extract_blocks() results don't change), but
    anything the first pass grew PAST the original bbox (see
    pymupdf_engine.py's try_grow()) would not be covered by a second
    redact_block() call working from that same original bbox, leaving a
    stray remnant of the first translation visible around the edges of
    the corrected text. Starting from the pristine source sidesteps this
    entirely: every record's block gets a completely blank original-PDF
    background to redact from, exactly like translate_pdf()'s own first
    pass did.

    Each record's `translated_html` is inserted AS-IS, whether or not the
    caller changed it since translate_pdf() first produced it - editing is
    the caller's job (e.g. via TranslatedBlockRecord.display_text /
    _plain_text_to_html() for a row a human actually corrected; an
    unedited row's original translated_html is passed straight through
    unchanged, which is what keeps that row's original inline
    bold/italic/underline formatting intact - see TranslatedBlockRecord.
    display_text's docstring for the formatting caveat that applies
    ONLY to a row that's actually been rebuilt from edited plain text).

    Records are grouped by page_index (order otherwise doesn't matter -
    each block's own geometry/collision math only ever looks at OTHER
    blocks' ORIGINAL extract_blocks() positions, never at insertion
    order) so engine.extract_blocks(page_index) - which
    PyMuPdfEngine.extract_blocks() caches per page - is called once per
    distinct page instead of once per record.

    Returns a PdfTranslationStats with `translated`/`overflow_blocks`
    populated the same way translate_pdf() does (so a caller can build an
    equivalent QA-style summary), `blocks` left empty (see
    PdfTranslationStats.blocks' docstring), and every other field at its
    default - there is no provider, no protected-terms handling, and
    nothing here can fail with a TranslationError, so `failed`/`errors`/
    `chars_sent`/`cancelled` simply don't apply to this pass.
    """
    stats = PdfTranslationStats()
    blocks_by_page: dict[int, list[TextBlock]] = {}
    for record in records:
        page_blocks = blocks_by_page.get(record.page_index)
        if page_blocks is None:
            page_blocks = engine.extract_blocks(record.page_index)
            blocks_by_page[record.page_index] = page_blocks
        block = page_blocks[record.block_index]
        engine.redact_block(block)
        fit = engine.insert_text(block, "", block.font_size, translated_html=record.translated_html)
        if not fit:
            stats.overflow_blocks += 1
        stats.translated += 1
    return stats


def build_corrected_records(
    records: list[TranslatedBlockRecord],
    edited_texts: dict[tuple[int, int], str],
) -> list[TranslatedBlockRecord]:
    """Turn a correction-table UI's edits back into a new list of
    TranslatedBlockRecord ready for apply_pdf_corrections() - the bridge
    between "what a human typed in a table cell" and "what actually gets
    reinserted into the PDF".

    `edited_texts` maps (page_index, block_index) -> the CURRENT plain
    text shown in that row's editable cell, for every row the correction
    table has (typically ALL of `records`, not just changed ones - the UI
    doesn't need to track which rows were touched, this function does).
    A row is treated as unedited - reusing its original record, and so
    its original translated_html, completely unchanged - whenever its
    current text still equals TranslatedBlockRecord.display_text (the
    plain-text projection of that original html); this is what preserves
    inline bold/italic/underline formatting for every row the user didn't
    actually touch. A row whose text differs gets a BRAND NEW record with
    translated_html rebuilt from the edited plain text via
    _plain_text_to_html() (paragraph-per-blank-line, HTML-escaped, no
    inline formatting) - a deliberate, documented trade-off: correctness
    of the actual words wins over preserving formatting for a row the
    user had to hand-fix anyway. A (page_index, block_index) missing from
    `edited_texts` is also treated as unedited (falls back to the
    original record) - lets a caller only pass rows it actually knows
    about without having to special-case missing keys.

    NOTE: ui/correction_dialog.py's Qt dialog no longer calls this
    function - see build_corrected_records_from_html() below, added once
    a real user asked for the "edited rows lose their formatting"
    trade-off documented above to not apply anymore. Kept as-is for its
    own test coverage and as the primitive a future plain-text-only
    editing surface (e.g. a CLI or a file-based correction workflow)
    could still reuse.
    """
    corrected: list[TranslatedBlockRecord] = []
    for record in records:
        edited_text = edited_texts.get((record.page_index, record.block_index))
        if edited_text is None or edited_text == record.display_text:
            corrected.append(record)
            continue
        corrected.append(
            TranslatedBlockRecord(
                page_index=record.page_index,
                block_index=record.block_index,
                original_text=record.original_text,
                translated_html=_plain_text_to_html(edited_text),
            )
        )
    return corrected


def build_corrected_records_from_html(
    records: list[TranslatedBlockRecord],
    edited_html: dict[tuple[int, int], str],
) -> list[TranslatedBlockRecord]:
    """Rich-text counterpart of build_corrected_records() for the Qt
    correction dialog's per-row rich-text editor (ui/correction_dialog.py,
    ui/rich_text.py) - added after the plain-text-only editor's "bearbeitete
    Zeilen verlieren ihre Formatierung" trade-off turned out to matter to a
    real user, who asked for a proper Fett/Kursiv/Unterstrichen-capable
    editor instead of accepting silent formatting loss on every edited row.

    `edited_html` maps (page_index, block_index) -> a NEW translated_html
    string ALREADY in this project's own minimal tag set (<p>/<br/>/<u>/
    <i>/<b>, no attributes - see spans_to_html()'s docstring), built by
    ui/rich_text.py's qt_document_to_project_html() from the dialog's
    QTextEdit - unlike build_corrected_records()'s _plain_text_to_html()
    rebuild, inline formatting the user just applied (or that survived
    untouched inside an edited row) is preserved as-is, no lossy
    plain-text round-trip.

    Only a (page_index, block_index) actually present in `edited_html` is
    replaced; every other record is passed through with its EXACT original
    translated_html object, unchanged - the dialog only populates
    edited_html for rows its own dirty-tracking (see
    PdfCorrectionDialog._dirty) saw a real edit happen in, so a row the
    user merely selected/viewed but never changed keeps its pristine
    original string rather than a re-serialized-but-visually-identical
    round-trip through Qt's rich text engine.
    """
    corrected: list[TranslatedBlockRecord] = []
    for record in records:
        html = edited_html.get((record.page_index, record.block_index))
        if html is None:
            corrected.append(record)
            continue
        corrected.append(
            TranslatedBlockRecord(
                page_index=record.page_index,
                block_index=record.block_index,
                original_text=record.original_text,
                translated_html=html,
            )
        )
    return corrected
