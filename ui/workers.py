"""Background workers for the Qt UI."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pipeline.pdf.translate_pdf import PdfTranslationStats
from pipeline.presentation.translate_presentation import PresentationTranslationStats
from pipeline.translation.cost_control import PricingModel
from pipeline.word.translate_document import TranslationStats as WordTranslationStats
from ui.analysis import analyze_request
from ui.models import AnalysisResult, TranslationRequest
from ui.pdf_job import PdfJobResult, run_pdf_job
from ui.pptx_job import PresentationJobResult, run_presentation_job
from ui.word_job import WordJobResult, run_word_job


class AnalysisSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class AnalysisWorker(QRunnable):
    def __init__(self, request: TranslationRequest, max_chars_per_run: int) -> None:
        super().__init__()
        self.request = request
        self.max_chars_per_run = max_chars_per_run
        self.signals = AnalysisSignals()

    @Slot()
    def run(self) -> None:
        try:
            result: AnalysisResult = analyze_request(self.request, self.max_chars_per_run)
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class TranslationSignals(QObject):
    progress = Signal(str)
    stats = Signal(object)
    total = Signal(int)
    finished = Signal(object)
    failed = Signal(str)


class PresentationTranslationWorker(QRunnable):
    """Runs one PPTX translation job on a background thread.

    Cancellation is cooperative: request_cancel() only sets a flag that
    run_presentation_job()/translate_presentation() poll between API calls,
    so an in-flight request always finishes cleanly before the run stops.
    """

    def __init__(
        self,
        source: Path,
        destination: Path,
        provider_name: str,
        pricing: PricingModel,
        target_lang: str,
        source_lang: str | None,
        protected_terms: list[str],
        max_chars_per_run: int,
    ) -> None:
        super().__init__()
        self.source = source
        self.destination = destination
        self.provider_name = provider_name
        self.pricing = pricing
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.protected_terms = protected_terms
        self.max_chars_per_run = max_chars_per_run
        self.signals = TranslationSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: PresentationJobResult = run_presentation_job(
                self.source,
                self.destination,
                self.provider_name,
                self.pricing,
                self.target_lang,
                self.source_lang,
                self.protected_terms,
                self.max_chars_per_run,
                progress_callback=self.signals.progress.emit,
                stats_callback=lambda stats: self.signals.stats.emit(_copy_stats(stats)),
                should_cancel=self._cancel_event.is_set,
                total_callback=self.signals.total.emit,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


def _copy_stats(stats: PresentationTranslationStats) -> PresentationTranslationStats:
    """Snapshot mutable stats before crossing the Qt signal/thread boundary,
    so a later mutation of the worker's live object can't retroactively
    change a value the UI already displayed.
    """
    return PresentationTranslationStats(
        stats.paragraphs_translated, stats.paragraphs_skipped, stats.paragraphs_failed,
        stats.chars_sent, stats.cancelled, list(stats.errors),
    )


class WordTranslationWorker(QRunnable):
    """Runs one DOCX translation job on a background thread. Mirrors
    PresentationTranslationWorker exactly (same cooperative-cancellation
    contract, same TranslationSignals) - see that class's docstring - just
    calling run_word_job()/ui.word_job instead of run_presentation_job()/
    ui.pptx_job.

    ``ico_mode`` (default False) is the one deliberate difference from
    PresentationTranslationWorker's constructor: PPTX has no equivalent
    "ICO document" special case (see ui/app.py's ico_mode checkbox, only
    enabled for Word mode), so it isn't added there just to keep the two
    signatures identical.
    """

    def __init__(
        self,
        source: Path,
        destination: Path,
        provider_name: str,
        pricing: PricingModel,
        target_lang: str,
        source_lang: str | None,
        protected_terms: list[str],
        max_chars_per_run: int,
        ico_mode: bool = False,
    ) -> None:
        super().__init__()
        self.source = source
        self.destination = destination
        self.provider_name = provider_name
        self.pricing = pricing
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.protected_terms = protected_terms
        self.max_chars_per_run = max_chars_per_run
        self.ico_mode = ico_mode
        self.signals = TranslationSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: WordJobResult = run_word_job(
                self.source,
                self.destination,
                self.provider_name,
                self.pricing,
                self.target_lang,
                self.source_lang,
                self.protected_terms,
                self.max_chars_per_run,
                progress_callback=self.signals.progress.emit,
                stats_callback=lambda stats: self.signals.stats.emit(_copy_word_stats(stats)),
                should_cancel=self._cancel_event.is_set,
                total_callback=self.signals.total.emit,
                ico_mode=self.ico_mode,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


def _copy_word_stats(stats: WordTranslationStats) -> WordTranslationStats:
    """Word counterpart of _copy_stats() above - same reason (snapshot
    before crossing the Qt signal/thread boundary), just with
    TranslationStats' body_/header_/footer_ fields instead of
    PresentationTranslationStats' flat paragraphs_* fields.
    """
    return WordTranslationStats(
        stats.body_translated, stats.body_skipped, stats.body_failed,
        stats.header_translated, stats.header_skipped, stats.header_failed,
        stats.footer_translated, stats.footer_skipped, stats.footer_failed,
        stats.chars_sent, stats.new_break_anomalies, stats.cancelled, list(stats.errors),
    )


class PdfTranslationWorker(QRunnable):
    """Runs one PDF translation job on a background thread. Mirrors
    PresentationTranslationWorker/WordTranslationWorker exactly (same
    cooperative-cancellation contract, same TranslationSignals) - see
    PresentationTranslationWorker's docstring - just calling
    run_pdf_job()/ui.pdf_job instead.

    ``ico_mode`` (default False) is the same "ICO-Dokument" checkbox
    WordTranslationWorker already exposes - ui/app.py now shows it for
    BOTH Word and PDF mode (see PyMuPdfEngine.open()'s docstring/
    RoadMap.md Phase 2/PDF), reusing TranslationRequest.ico_mode rather
    than adding a PDF-specific field.

    ``exclude_header``/``exclude_footer`` (default False) are PDF's own
    additional special case - the "Header ausschließen"/"Footer
    ausschließen" checkboxes in ui/app.py, PDF-mode only. See
    run_pdf_job()'s docstring for what they actually do (automatic
    header/footer detection via
    pipeline.pdf.template.detect_header_footer_zones()).
    """

    def __init__(
        self,
        source: Path,
        destination: Path,
        provider_name: str,
        pricing: PricingModel,
        target_lang: str,
        source_lang: str | None,
        protected_terms: list[str],
        max_chars_per_run: int,
        exclude_header: bool = False,
        exclude_footer: bool = False,
        ico_mode: bool = False,
    ) -> None:
        super().__init__()
        self.source = source
        self.destination = destination
        self.provider_name = provider_name
        self.pricing = pricing
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.protected_terms = protected_terms
        self.max_chars_per_run = max_chars_per_run
        self.ico_mode = ico_mode
        self.exclude_header = exclude_header
        self.exclude_footer = exclude_footer
        self.signals = TranslationSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: PdfJobResult = run_pdf_job(
                self.source,
                self.destination,
                self.provider_name,
                self.pricing,
                self.target_lang,
                self.source_lang,
                self.protected_terms,
                self.max_chars_per_run,
                progress_callback=self.signals.progress.emit,
                stats_callback=lambda stats: self.signals.stats.emit(_copy_pdf_stats(stats)),
                should_cancel=self._cancel_event.is_set,
                total_callback=self.signals.total.emit,
                exclude_header=self.exclude_header,
                exclude_footer=self.exclude_footer,
                ico_mode=self.ico_mode,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


def _copy_pdf_stats(stats: PdfTranslationStats) -> PdfTranslationStats:
    """PDF counterpart of _copy_stats()/_copy_word_stats() above - same
    reason (snapshot before crossing the Qt signal/thread boundary).
    """
    return PdfTranslationStats(
        stats.translated, stats.skipped, stats.failed, stats.chars_sent,
        stats.overflow_blocks, stats.cancelled, list(stats.errors), list(stats.blocks),
    )
