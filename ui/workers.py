"""Background workers for the Qt UI."""
from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from bootstrap import paths as bootstrap_paths
from bootstrap import release_source
from bootstrap.installer import pip_install
from pipeline.pdf.pymupdf_engine import MergeSourceSpec
from pipeline.pdf.translate_pdf import PdfTranslationStats
from pipeline.presentation.translate_presentation import PresentationTranslationStats
from pipeline.translation.cost_control import PricingModel
from pipeline.word.translate_document import TranslationStats as WordTranslationStats
from ui.analysis import analyze_request
from ui.image_job import ImageBatchJobResult, ImageBatchStats, run_image_batch_job
from ui.drive_search import DriveClientProtocol, DriveSearchResult, find_drive_docx_matching, find_drive_pdfs_matching
from ui.merge_job import MergeJobResult, run_merge_job
from ui.merge_search import IcoSearchResult, find_docx_files_matching, find_pdfs_matching
from ui.models import AnalysisResult, TranslationRequest
from ui.pdf_job import PdfJobResult, run_pdf_job
from ui.pptx_job import PresentationJobResult, run_presentation_job
from ui.word_job import WordJobResult, run_word_job
from ui.word_merge_job import WordMergeJobResult, run_word_merge_job


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


class ImageTranslationWorker(QRunnable):
    """Runs one eigenständige-Bildübersetzung batch on a background
    thread (RoadMap.md Phase 3). Mirrors PdfTranslationWorker/
    PresentationTranslationWorker/WordTranslationWorker's shape (same
    TranslationSignals, same cooperative-cancellation contract) - the one
    structural difference is that this worker takes MULTIPLE `sources`
    and a single `output_dir` rather than one `source`/`destination`
    pair, since TranslationMode.IMAGES is the only mode whose
    TranslationRequest allows more than one selected source file at once
    (see TranslationRequest.validation_errors()). Calls
    run_image_batch_job() (see ui/image_job.py), not run_image_job()
    directly.

    ``ocr_engine_name``/``inpainting_backend_name`` (defaults
    "tesseract"/"box_overlay") select which
    pipeline.images.ocr.OcrEngine/pipeline.images.inpainting.InpaintingBackend
    to use - see ui/document_job_common.py's factories.
    """

    def __init__(
        self,
        sources: list[Path],
        output_dir: Path,
        provider_name: str,
        pricing: PricingModel,
        target_lang: str,
        source_lang: str | None,
        protected_terms: list[str],
        max_chars_per_run: int,
        ocr_engine_name: str = "tesseract",
        inpainting_backend_name: str = "box_overlay",
    ) -> None:
        super().__init__()
        self.sources = sources
        self.output_dir = output_dir
        self.provider_name = provider_name
        self.pricing = pricing
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.protected_terms = protected_terms
        self.max_chars_per_run = max_chars_per_run
        self.ocr_engine_name = ocr_engine_name
        self.inpainting_backend_name = inpainting_backend_name
        self.signals = TranslationSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: ImageBatchJobResult = run_image_batch_job(
                self.sources,
                self.output_dir,
                self.provider_name,
                self.pricing,
                self.target_lang,
                self.source_lang,
                self.protected_terms,
                self.max_chars_per_run,
                ocr_engine_name=self.ocr_engine_name,
                inpainting_backend_name=self.inpainting_backend_name,
                progress_callback=self.signals.progress.emit,
                stats_callback=lambda stats: self.signals.stats.emit(_copy_image_batch_stats(stats)),
                should_cancel=self._cancel_event.is_set,
                total_callback=self.signals.total.emit,
            )
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class MergeSignals(QObject):
    """Own signal set (01.09.2026) rather than reusing TranslationSignals
    above: a merge run has no per-block/per-character `stats` or a
    determinate `total` to report (see ui/merge_job.py's module docstring
    for why merge isn't built on the translation flow at all) - only a
    per-source `progress` message and the eventual finished/failed
    outcome."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)


class MergeWorker(QRunnable):
    """Runs one PDF merge/insert job (ui/merge_job.py::run_merge_job()) on
    a background thread. Structurally the odd one out among this module's
    workers - no provider/pricing/target_lang (nothing here is a
    translation run) - but otherwise the same shape: MergeSignals instead
    of TranslationSignals, same cooperative cancel_event polled between
    sources (see merge_pdfs()'s docstring for why only between, not
    during, one source's copy).
    """

    def __init__(self, sources: Sequence[MergeSourceSpec], destination: Path) -> None:
        super().__init__()
        self.sources = sources
        self.destination = destination
        self.signals = MergeSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: MergeJobResult = run_merge_job(
                self.sources,
                self.destination,
                progress_callback=self.signals.progress.emit,
                should_cancel=self._cancel_event.is_set,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class WordMergeSignals(QObject):
    """DOCX counterpart of MergeSignals above (01.09.2026, Michael: "Jetzt
    noch das ganze für *.docx.") - same shape, same reasoning (no
    determinate `total`/per-block `stats`, just a per-source `progress`
    message)."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)


class WordMergeWorker(QRunnable):
    """Runs one DOCX merge/insert job (ui/word_merge_job.py::run_word_merge_job())
    on a background thread - the DOCX counterpart of MergeWorker above,
    same cooperative cancel_event/between-files polling contract (see
    pipeline/word/merge.py's merge_docx_files() docstring for the one
    difference: cancellation is not polled again during a batched merge's
    final "combine the completed chunks" pass, so that step is not
    interruptible mid-way once started - this worker doesn't need to know
    that, it just relays whatever should_cancel()/progress the underlying
    job reports).

    `batch_size` is not exposed as a constructor default override from the
    UI (Michael confirmed batching should happen automatically, not be a
    per-run setting) - the default comes from run_word_merge_job() itself.
    """

    def __init__(self, sources: Sequence[Path], destination: Path) -> None:
        super().__init__()
        self.sources = sources
        self.destination = destination
        self.signals = WordMergeSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: WordMergeJobResult = run_word_merge_job(
                self.sources,
                self.destination,
                progress_callback=self.signals.progress.emit,
                should_cancel=self._cancel_event.is_set,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class IcoSearchSignals(QObject):
    """progress carries (files_done_so_far, total_files, current_filename) -
    see find_pdfs_matching()'s docstring - so ui/merge_search_dialog.py can
    drive a DETERMINATE progress bar (total is known upfront from the
    directory walk), unlike MergeSignals.progress above."""

    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)


class IcoSearchWorker(QRunnable):
    """Runs one folder scan (ui/merge_search.py::find_pdfs_matching()) on a
    background thread - ui/merge_search_dialog.py's "Suchen" button. Same
    cooperative cancel_event/between-files polling as MergeWorker above.

    `scopes` (02.09.2026, the "ICO Format"/"Header"/"Volltext" checkboxes -
    see ui/search_scopes.py): which scope(s) the dialog had checked when
    "Suchen" was clicked, passed straight through to find_pdfs_matching().
    """

    def __init__(self, folder: Path, query: str, recursive: bool, scopes) -> None:
        super().__init__()
        self.folder = folder
        self.query = query
        self.recursive = recursive
        self.scopes = scopes
        self.signals = IcoSearchSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: IcoSearchResult = find_pdfs_matching(
                self.folder,
                self.query,
                recursive=self.recursive,
                progress_callback=self.signals.progress.emit,
                should_cancel=self._cancel_event.is_set,
                scopes=self.scopes,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class DriveSearchSignals(QObject):
    """Same shape as IcoSearchSignals above (progress carries (done, total,
    current_name), a determinate total known upfront) - the local-vs-Drive
    scan share MergeSearchDialog's progress bar/status label code, only the
    worker underneath differs (01.09.2026, Google-Drive-Ordnersuche)."""

    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)


class DriveSearchWorker(QRunnable):
    """Runs one Drive folder scan (ui/drive_search.py::find_drive_pdfs_matching())
    on a background thread - the Drive counterpart of IcoSearchWorker above,
    same cooperative cancel_event/between-files polling. Takes an already-
    authorized `client` (see pipeline/drive_auth.py::build_service() +
    DriveClient) rather than building one itself, so constructing this
    worker never itself makes a network call - MergeSearchDialog builds the
    client once (surfacing any auth error immediately, before "Suchen" even
    starts) and passes it in.
    """

    def __init__(
        self, client: DriveClientProtocol, folder_id: str, query: str, recursive: bool, cache_dir: Path, scopes
    ) -> None:
        super().__init__()
        self.client = client
        self.folder_id = folder_id
        self.query = query
        self.recursive = recursive
        self.cache_dir = cache_dir
        self.scopes = scopes
        self.signals = DriveSearchSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: DriveSearchResult = find_drive_pdfs_matching(
                self.client,
                self.folder_id,
                self.query,
                recursive=self.recursive,
                cache_dir=self.cache_dir,
                progress=self.signals.progress.emit,
                is_cancelled=self._cancel_event.is_set,
                scopes=self.scopes,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class WordIcoSearchWorker(QRunnable):
    """DOCX counterpart of IcoSearchWorker above (01.09.2026) - runs one
    folder scan via ui/merge_search.py::find_docx_files_matching() on a
    background thread. Same IcoSearchSignals/cooperative-cancel contract
    (the result shape - IcoSearchResult - is already format-agnostic, see
    ui/merge_search.py's module docstring), so this only differs from
    IcoSearchWorker in which matching function it calls. `scopes` - see
    IcoSearchWorker's docstring (02.09.2026)."""

    def __init__(self, folder: Path, query: str, recursive: bool, scopes) -> None:
        super().__init__()
        self.folder = folder
        self.query = query
        self.recursive = recursive
        self.scopes = scopes
        self.signals = IcoSearchSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: IcoSearchResult = find_docx_files_matching(
                self.folder,
                self.query,
                recursive=self.recursive,
                progress_callback=self.signals.progress.emit,
                should_cancel=self._cancel_event.is_set,
                scopes=self.scopes,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class WordDriveSearchWorker(QRunnable):
    """DOCX counterpart of DriveSearchWorker above (01.09.2026) - runs one
    Drive folder scan via ui/drive_search.py::find_drive_docx_matching()
    on a background thread. Same DriveSearchSignals/cooperative-cancel
    contract and already-authorized-`client` convention as DriveSearchWorker
    (see that class's docstring); only the matching function differs.
    `scopes` - see IcoSearchWorker's docstring (02.09.2026)."""

    def __init__(
        self, client: DriveClientProtocol, folder_id: str, query: str, recursive: bool, cache_dir: Path, scopes
    ) -> None:
        super().__init__()
        self.client = client
        self.folder_id = folder_id
        self.query = query
        self.recursive = recursive
        self.cache_dir = cache_dir
        self.scopes = scopes
        self.signals = DriveSearchSignals()
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result: DriveSearchResult = find_drive_docx_matching(
                self.client,
                self.folder_id,
                self.query,
                recursive=self.recursive,
                cache_dir=self.cache_dir,
                progress=self.signals.progress.emit,
                is_cancelled=self._cancel_event.is_set,
                scopes=self.scopes,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(result)


class DriveConnectSignals(QObject):
    succeeded = Signal()
    failed = Signal(str)


class DriveConnectWorker(QRunnable):
    """Runs pipeline.drive_auth.connect_interactively() on a background
    thread - it opens a system browser and blocks on a local loopback
    server waiting for the OAuth redirect (see that function's docstring),
    which would freeze the whole UI if run directly on the Qt thread like
    MergeSearchDialog's "Mit Google verbinden" button click would otherwise
    do.
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = DriveConnectSignals()

    @Slot()
    def run(self) -> None:
        try:
            from pipeline.drive_auth import connect_interactively

            connect_interactively()
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.succeeded.emit()


def _copy_image_batch_stats(stats: ImageBatchStats) -> ImageBatchStats:
    """Image-batch counterpart of _copy_pdf_stats() above - same reason
    (snapshot before crossing the Qt signal/thread boundary). `results`
    is shallow-copied (list(...)) - each individual ImageJobResult inside
    is immutable in practice (never mutated after construction, see
    ui/image_job.py), so a shallow copy is enough, same as
    _copy_pdf_stats() only shallow-copying `blocks`.
    """
    return ImageBatchStats(
        stats.translated, stats.skipped, stats.failed, stats.chars_sent,
        stats.cancelled, stats.files_processed, stats.files_total, list(stats.results),
    )


# --- self-update (01.09.2026, Michael: "Update sollte die App selbst
# prüfen.") ------------------------------------------------------------
#
# Both workers below import from bootstrap/ - safe in this direction only
# (see bootstrap/__init__.py's own docstring: that package must never
# import from ui/ or pipeline/, but nothing stops ui/ from importing its
# Tk-free modules). bootstrap.release_source/bootstrap.paths pull in
# nothing beyond the standard library, so this adds no new dependency to
# the already-installed venv.


class UpdateCheckSignals(QObject):
    finished = Signal(object)  # release_source.UpdateInfo | None
    failed = Signal(str)


class UpdateCheckWorker(QRunnable):
    """Background check for a newer GitHub release than `current_version` -
    see bootstrap/release_source.py::check_for_update(). Runs via
    QThreadPool exactly like AnalysisWorker above, so the network call
    never blocks the Qt event loop.

    `failed` is used for genuine surprises only, not "no update found" -
    that is `finished.emit(None)`, a normal outcome. ui/app.py's startup
    check connects `failed` to nothing but a debug print: being offline, or
    GitHub being briefly unreachable, must never surface as an error dialog
    for a check nobody explicitly asked for (mirrors this project's
    general pattern of never letting a background availability check
    interrupt the user - see e.g. _update_ocr_engine_hint()/
    _update_inpainting_backend_hint() in ui/app.py, which show an inline
    hint rather than a popup for their own "not available" cases).
    """

    def __init__(self, current_version: str) -> None:
        super().__init__()
        self.current_version = current_version
        self.signals = UpdateCheckSignals()

    @Slot()
    def run(self) -> None:
        try:
            info = release_source.check_for_update(self.current_version)
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(info)


class UpdateApplySignals(QObject):
    finished = Signal()
    failed = Signal(str)


class UpdateApplyWorker(QRunnable):
    """Downloads and installs the release described by `info` OVER the
    currently running app's own source directory
    (bootstrap.paths.app_source_dir() - the same directory
    bootstrap/installer.py's Stage 2 populated on first install) using the
    exact same download/extract code Stage 2 uses
    (bootstrap.release_source.download_release(), pointed at the SPECIFIC
    release the user already confirmed rather than re-resolving "latest" a
    second time - see that function's own docstring for why).

    Re-installs requirements*.txt afterwards via `sys.executable -m pip
    install` (bootstrap.installer.pip_install(), reused as-is) -
    sys.executable IS this already-running venv's own python (ui/app.py
    only ever runs from inside the venv bootstrap/installer.py created,
    never system Python), so this needs no separate venv path the way
    bootstrap/installer.py's own caller (BootstrapController, Stage 2 of a
    FRESH install) has to look up. requirements-gpu.txt is only reinstalled
    if `torch` is already importable in THIS process: the running app has
    no record of which InstallMode the user originally chose (that
    decision lives only in the bootstrapper's own BootstrapController,
    long gone by the time the real app is running) - "is torch already
    here" is the best available signal for "was this a LOCAL install"
    without adding a whole persisted-install-mode concept just for this.

    Deliberately does NOT restart the app itself - ui/app.py shows a
    "please restart" message instead (see MainWindow._update_apply_
    finished()) rather than this worker trying to relaunch the process,
    which would need different handling per platform for comparatively
    little benefit over asking the user to close and reopen it themselves.
    """

    def __init__(self, info: release_source.UpdateInfo) -> None:
        super().__init__()
        self.info = info
        self.signals = UpdateApplySignals()

    @Slot()
    def run(self) -> None:
        try:
            app_source_dir = bootstrap_paths.app_source_dir()
            release_source.download_release(self.info, app_source_dir)
            had_gpu_deps = importlib.util.find_spec("torch") is not None
            for name in ("requirements.txt", "requirements-ocr.txt", "requirements-gpu.txt"):
                if name == "requirements-gpu.txt" and not had_gpu_deps:
                    continue
                requirements_file = app_source_dir / name
                if requirements_file.is_file():
                    pip_install(Path(sys.executable), requirements_file)
        except Exception as exc:  # noqa: BLE001 - mirrors every other worker's catch-all above
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit()
