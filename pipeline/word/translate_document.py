"""Reusable full-document Word translation pass, extracted from
tests/manual_translate_full_document.py (the original, single-document
reference script) so it and ico_translate/batch.py's batch run share one
implementation instead of two copies.

Every translatable=True paragraph in the body AND the header/footer gets
run through paragraph_to_html -> protect_terms -> translate_html ->
restore_terms -> html_to_paragraph -> replace_paragraph_runs()/
replace_header_footer_paragraph(); everything else (page-1 metadata block,
images, header/footer text - always translatable=False per requirement 1
of anforderungen_word_pfad.md) is left untouched. Opening the source
document and saving the result afterwards stays the CALLER's job
(tests/manual_translate_full_document.py and ico_translate/batch.py each
do their own, since batch.py also needs to pick the output path/filename
per document) - translate_document() only mutates an already-open
DocxEngine in place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.protected_terms import protect_terms, restore_terms
from pipeline.word.base import WordParagraph, WordRun
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import _BREAK_ANOMALY_LOG_PATH, html_to_paragraph, paragraph_to_html


@dataclass
class TranslationStats:
    """translate_document()'s result: separate body/header/footer
    translated/skipped/failed counters (matching
    tests/manual_translate_full_document.py's original Kurzreport), plus
    aggregate translated/skipped/failed properties for a caller (e.g.
    ico_translate/batch.py's per-run summary) that only wants the total
    across all three.
    """
    body_translated: int = 0
    body_skipped: int = 0
    body_failed: int = 0
    header_translated: int = 0
    header_skipped: int = 0
    header_failed: int = 0
    footer_translated: int = 0
    footer_skipped: int = 0
    footer_failed: int = 0
    chars_sent: int = 0
    """Total HTML characters (including tags/placeholders) actually sent
    to provider.translate_html() across every paragraph - the same
    per-call accounting cost_control.py's usage log uses, summed here for
    a per-document total."""
    new_break_anomalies: int = 0
    """How many NEW entries this call added to html_bridge.py's
    tests/output/word_break_anomalies.jsonl (see _check_break_count()) -
    computed from the log's line count before/after, same technique the
    original single-document script used."""
    cancelled: bool = False
    """Set when should_cancel() stopped the run early (see
    translate_document()) - the UI job layer (ui/word_job.py) surfaces this
    the same way ui/pptx_job.py already does for PresentationTranslationStats:
    a clearly labelled partial result, not an error."""
    errors: list[str] = field(default_factory=list)
    """Human-readable "location: exception" strings for every failed
    paragraph (body/header/footer), same role as
    PresentationTranslationStats.errors - the UI job's QA report
    (ui/word_job.py) lists these so a failure is diagnosable without
    reproducing it, without ever including credentials (TranslationError
    messages are already credential-free, same guarantee the PPTX path
    relies on)."""

    @property
    def translated(self) -> int:
        return self.body_translated + self.header_translated + self.footer_translated

    @property
    def skipped(self) -> int:
        return self.body_skipped + self.header_skipped + self.footer_skipped

    @property
    def failed(self) -> int:
        return self.body_failed + self.header_failed + self.footer_failed

    @property
    def processed(self) -> int:
        """Paragraphs (body + header + footer) that have already reached a
        final outcome - lets a caller (ui/app.py) drive a progress display
        without its own counter, the same role
        PresentationTranslationStats.paragraphs_processed plays for the
        PPTX path. Named without a "paragraphs_" prefix (unlike that
        property) since this dataclass's other fields already carry it
        implicitly through body_/header_/footer_ - kept as-is for backward
        compatibility with existing callers (ico_translate/batch.py)."""
        return self.translated + self.skipped + self.failed


def total_paragraph_count(engine: DocxEngine) -> int:
    """Total number of paragraphs translate_document() will eventually
    report a final outcome for (translated, skipped or failed): every body
    paragraph plus every header/footer paragraph. Mirrors
    pipeline.presentation.translate_presentation.total_paragraph_count() -
    cheap (no API calls), lets a caller (ui/word_job.py) show a determinate
    "X of N paragraphs" progress bar instead of an indeterminate one.
    """
    return len(engine.get_paragraphs()) + len(engine.get_header_footer_paragraphs())


def _translate_paragraph(
    paragraph: WordParagraph,
    provider: TranslationProvider,
    protected_terms: list[str],
    target_lang: str,
    source_lang: str | None,
    log_label: str,
) -> tuple[list[WordRun] | None, int]:
    """paragraph_to_html -> protect_terms -> translate_html -> restore_terms
    -> html_to_paragraph. Returns (None, 0) if the paragraph has no real
    HTML content (e.g. a blank paragraph between sections) - nothing to
    send, nothing to write back. `log_label` (e.g. "body:8"/"header:0")
    identifies the paragraph in word_break_anomalies.jsonl if
    html_to_paragraph() logs a <br/> count mismatch for it.
    """
    original = paragraph_to_html(paragraph)
    if not original.html.strip():
        return None, 0

    protected_html, mapping = protect_terms(original.html, protected_terms)
    result = provider.translate_html(protected_html, target_lang=target_lang, source_lang=source_lang)
    restored_html = restore_terms(result.text, mapping)
    return html_to_paragraph(restored_html, original, paragraph_index=log_label), len(protected_html)


def translate_document(
    engine: DocxEngine,
    provider: TranslationProvider,
    protected_terms: list[str],
    target_lang: str,
    source_lang: str | None = "en",
    progress_callback: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    stats_callback: Callable[[TranslationStats], None] | None = None,
    translated_runs: dict[int, list[WordRun]] | None = None,
) -> TranslationStats:
    """Translate every translatable paragraph of `engine`'s already-open
    document IN PLACE (via engine.replace_paragraph_runs()/
    replace_header_footer_paragraph()). Does not open or save the
    document - see the module docstring for why that stays the caller's
    job.

    A single paragraph's TranslationError is caught and counted as
    failed rather than re-raised, so one bad paragraph never aborts the
    rest of the document - the same "skip, don't abort" policy the
    original single-document script used at paragraph level (independent
    of, and one level below, ico_translate/batch.py's equivalent
    "skip, don't abort" policy at the whole-DOCUMENT level).

    `progress_callback`, if given, is called with a short human-readable
    string before each paragraph attempt and on each per-paragraph
    failure - used by tests/manual_translate_full_document.py to print
    per-paragraph progress; left None (silent) by ico_translate/batch.py,
    which reports per-document, not per-paragraph, progress.

    `should_cancel`, if given, is polled before each paragraph (body, then
    header/footer) - i.e. between API calls, never mid-call - the same
    cooperative-cancellation contract
    pipeline.presentation.translate_presentation.translate_presentation()
    already established for the PPTX path (see its docstring): once it
    returns True, stats.cancelled is set and the run stops, every paragraph
    already translated stays translated, the rest is left untouched.

    `stats_callback`, if given, is called after every paragraph reaches a
    final outcome (translated/skipped/failed, in either loop) with the
    current cumulative `stats`, letting a caller (ui/word_job.py) drive a
    live progress display without polling - again mirroring
    translate_presentation().

    `translated_runs`, if given, is populated with {body_paragraph_index:
    new_runs} for every BODY paragraph that was actually translated (i.e.
    replace_paragraph_runs() was called for it) - header/footer are never
    added, since they're never translated (see the loop below). Added
    03.09.2026 for the "nebeneinander" side-by-side view (Michael: see
    pipeline/word/side_by_side.py's module docstring): that module needs
    both the ORIGINAL paragraph (still available afterwards via
    engine.get_paragraphs() - replace_paragraph_runs() mutates the live
    XML tree, not the WordParagraph dataclasses this function reads from)
    and the TRANSLATED runs for the same paragraph, which otherwise only
    ever end up written into the XML tree with no separate record kept.
    Left None (the default) for every other caller (ico_translate/
    batch.py, tests/manual_translate_full_document.py), which have no use
    for it and shouldn't pay for building a dict they never read.
    """
    stats = TranslationStats()

    def _notify(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    def _report() -> None:
        if stats_callback is not None:
            stats_callback(stats)

    def _cancelled() -> bool:
        return should_cancel is not None and should_cancel()

    body_paragraphs = engine.get_paragraphs()
    header_footer_paragraphs = engine.get_header_footer_paragraphs()
    header_count = len(engine._header_paragraph_elements)

    anomaly_lines_before = (
        len(_BREAK_ANOMALY_LOG_PATH.read_text(encoding="utf-8").splitlines())
        if _BREAK_ANOMALY_LOG_PATH.exists()
        else 0
    )

    for index, paragraph in enumerate(body_paragraphs):
        if _cancelled():
            stats.cancelled = True
            break
        if not paragraph.translatable:
            stats.body_skipped += 1
            _report()
            continue
        _notify(f"Hauptteil-Absatz {index + 1}/{len(body_paragraphs)}...")
        try:
            new_runs, sent = _translate_paragraph(
                paragraph, provider, protected_terms, target_lang, source_lang, f"body:{index}"
            )
        except TranslationError as exc:
            _notify(f"  FEHLER (uebersprungen): {exc}")
            stats.body_failed += 1
            stats.errors.append(f"body:{index}: {type(exc).__name__}: {exc}")
            _report()
            continue
        stats.chars_sent += sent
        if new_runs is None:
            stats.body_skipped += 1
            _report()
            continue
        engine.replace_paragraph_runs(index, new_runs)
        if translated_runs is not None:
            translated_runs[index] = new_runs
        stats.body_translated += 1
        _report()

    for combined_index, paragraph in enumerate(header_footer_paragraphs):
        # stats.cancelled may already be True here (cancelled during the
        # body loop above) - re-checking short-circuits immediately without
        # touching header/footer at all, same "stop cleanly, nothing
        # in-flight" contract as the body loop.
        if stats.cancelled or _cancelled():
            stats.cancelled = True
            break
        if combined_index < header_count:
            source, sub_index = "header", combined_index
        else:
            source, sub_index = "footer", combined_index - header_count

        if not paragraph.translatable:
            if source == "header":
                stats.header_skipped += 1
            else:
                stats.footer_skipped += 1
            _report()
            continue

        # Not expected to ever fire (header/footer are translatable=False
        # per requirement 1 - see DocxEngine.get_header_footer_paragraphs()),
        # kept symmetrical with the body loop regardless.
        _notify(f"{source.capitalize()}-Absatz {sub_index + 1}...")
        try:
            new_runs, sent = _translate_paragraph(
                paragraph, provider, protected_terms, target_lang, source_lang, f"{source}:{sub_index}"
            )
        except TranslationError as exc:
            _notify(f"  FEHLER (uebersprungen): {exc}")
            if source == "header":
                stats.header_failed += 1
            else:
                stats.footer_failed += 1
            stats.errors.append(f"{source}:{sub_index}: {type(exc).__name__}: {exc}")
            _report()
            continue
        stats.chars_sent += sent
        if new_runs is None:
            if source == "header":
                stats.header_skipped += 1
            else:
                stats.footer_skipped += 1
            _report()
            continue
        engine.replace_header_footer_paragraph(source, sub_index, new_runs)
        if source == "header":
            stats.header_translated += 1
        else:
            stats.footer_translated += 1
        _report()

    anomaly_lines_after = (
        len(_BREAK_ANOMALY_LOG_PATH.read_text(encoding="utf-8").splitlines())
        if _BREAK_ANOMALY_LOG_PATH.exists()
        else 0
    )
    stats.new_break_anomalies = anomaly_lines_after - anomaly_lines_before

    return stats
