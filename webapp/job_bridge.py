"""HTTP-independent glue between webapp/server.py's handlers and the
existing, already Qt-independent pipeline/ui.analysis/ui.settings/
pipeline.registry code - see webapp/__init__.py's docstring for why this
split exists at all (webapp/ must never import PySide6).

Kept separate from server.py on purpose: this module has no `http.server`
import and can be unit-tested (and read) without any HTTP machinery
involved - server.py's handlers stay thin (parse the request, call one
function here, serialize the result), all the actual logic lives here.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.images.inpainting import TextReplacement
from pipeline.registry import (
    INPAINTING_BACKEND_FACTORIES,
    OCR_ENGINE_FACTORIES,
    PROVIDER_FACTORIES,
    inpainting_backend_available,
    ocr_engine_available,
)
from pipeline.translation.cost_control import DEFAULT_MAX_CHARS_PER_RUN
from ui.analysis import PRICING, analyze_request
from ui.image_job import ImageBatchJobResult, ImageBatchStats, ImageJobResult, run_image_batch_job
from ui.models import EmbeddedImageMode, TranslationMode, TranslationRequest
from ui.settings import credential_status
from webapp import settings_store


def build_config() -> dict[str, Any]:
    """Backs GET /api/config - everything the frontend's images-mode form
    needs to render itself: which providers/OCR-engines/inpainting-
    backends exist, whether each is actually usable right now (same
    availability checks ui/app.py's dropdown hints and fail-fast checks
    already use, see pipeline.registry's own docstring), and the
    last-saved form state to prefill with (webapp/settings_store.py, the
    QSettings replacement).
    """
    providers = sorted(PROVIDER_FACTORIES)
    ocr_engines = sorted(OCR_ENGINE_FACTORIES)
    inpainting_backends = sorted(INPAINTING_BACKEND_FACTORIES)
    saved = settings_store.load()
    return {
        "providers": providers,
        "provider_credential_status": {name: credential_status(name) for name in providers},
        "ocr_engines": ocr_engines,
        "ocr_engine_available": {name: ocr_engine_available(name) for name in ocr_engines},
        "inpainting_backends": inpainting_backends,
        "inpainting_backend_available": {
            name: inpainting_backend_available(name) for name in inpainting_backends
        },
        "max_chars_per_run": saved.get("max_chars", DEFAULT_MAX_CHARS_PER_RUN),
        "last_form_state": saved,
    }


class AnalyzeRequestError(ValueError):
    """Raised for a malformed analyze request body (wrong JSON shape, not
    a validation failure of the translation request itself) - analyze()
    catches this specifically to return a 400 with a clear message
    instead of letting a TypeError/AttributeError escape as a 500.
    """


def _request_from_json(body: dict[str, Any]) -> TranslationRequest:
    """Builds the images-mode TranslationRequest this pilot always uses -
    mode is hardcoded to IMAGES (webapp/ covers only the image-translation
    flow for now, see webapp/__init__.py's docstring); every other field
    comes from the request body with the same defaults ui/app.py's form
    fields have (target_lang "DE", ocr_engine "tesseract",
    inpainting_backend "box_overlay" - see webapp/settings_store.py's
    DEFAULTS, which uses the identical defaults).
    """
    source_paths = body.get("source_paths") or []
    if not isinstance(source_paths, list) or not all(isinstance(p, str) for p in source_paths):
        raise AnalyzeRequestError("source_paths muss eine Liste von Pfaden (Strings) sein.")
    protected_terms = body.get("protected_terms") or []
    if not isinstance(protected_terms, list) or not all(isinstance(t, str) for t in protected_terms):
        raise AnalyzeRequestError("protected_terms muss eine Liste von Begriffen (Strings) sein.")
    return TranslationRequest(
        mode=TranslationMode.IMAGES,
        source_paths=tuple(Path(p) for p in source_paths),
        provider=str(body.get("provider", "deepl")),
        source_language=(body.get("source_language") or None),
        target_language=str(body.get("target_language", "DE")),
        embedded_images=EmbeddedImageMode.NONE,
        protected_terms=tuple(protected_terms),
        ocr_engine=str(body.get("ocr_engine", "tesseract")),
        inpainting_backend=str(body.get("inpainting_backend", "box_overlay")),
    )


def analyze(body: dict[str, Any]) -> dict[str, Any]:
    """Backs POST /api/analyze - wraps ui.analysis.analyze_request()
    unchanged (RoadMap.md Leitprinzip: every paid run needs an analysis +
    cost estimate + explicit confirmation before execution - this is the
    ONLY function in webapp/ that produces that estimate, and it must stay
    the exact same estimate the Qt app already shows, not a re-derived
    approximation). Returns {"ok": True, ...AnalysisResult fields...} on
    success or {"ok": False, "errors": [...]} on any validation problem -
    never raises past this point, so server.py's handler can turn either
    shape directly into a JSON response.
    """
    try:
        request = _request_from_json(body)
    except AnalyzeRequestError as exc:
        return {"ok": False, "errors": [str(exc)]}
    max_chars = int(body.get("max_chars_per_run", DEFAULT_MAX_CHARS_PER_RUN))
    try:
        result = analyze_request(request, max_chars)
    except ValueError as exc:
        # TranslationRequest.validation_errors() is joined with "\n" by
        # analyze_request() itself - split back into a list so the
        # frontend can render one item per line instead of one blob.
        return {"ok": False, "errors": str(exc).split("\n")}
    cost = result.cost
    return {
        "ok": True,
        "mode": result.mode.value,
        "files": result.files,
        "units": result.units,
        "unit_label": result.unit_label,
        "text_characters": result.text_characters,
        "embedded_images": result.embedded_images,
        "selected_image_candidates": result.selected_image_candidates,
        "ocr_required": result.ocr_required,
        "warnings": list(result.warnings),
        "cost": {
            "provider": cost.provider,
            "characters": cost.characters,
            "month_usage": cost.month_usage,
            "free_tier": cost.free_tier,
            "estimated_cost_usd": cost.estimated_cost_usd,
            "max_chars_per_run": cost.max_chars_per_run,
            "within_run_limit": cost.within_run_limit,
            "live_usage_available": cost.live_usage_available,
            "live_characters_used": cost.live_characters_used,
            "live_character_limit": cost.live_character_limit,
        },
    }


# --- /api/jobs (Schritt 4) ----------------------------------------------
#
# In-memory job state only, no persistence across a server restart - the
# same "single local user, single server process" assumption the module
# docstring above already makes for settings_store.py, and the same
# reasoning image_translate_cli/review_server.py's own in-memory state
# uses. Runs on a plain threading.Thread (not QThreadPool - webapp/ has
# no Qt event loop to integrate with) and mirrors
# ui/workers.py::ImageTranslationWorker exactly: same run_image_batch_job()
# call, same cooperative threading.Event cancellation, same
# progress/stats/total callback wiring - just polled via HTTP instead of
# Qt signals.
#
# Only one job may run at a time (RoadMap.md/plan's explicit non-goal:
# "kein Mehrfach-Job-Betrieb") - enforced by _ACTIVE_JOB_ID below, not by
# _JOBS itself, so a finished job's status/result stay queryable by id
# after a new one starts.
_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, "_JobState"] = {}
_ACTIVE_JOB_ID: str | None = None


def _snapshot_stats(stats: ImageBatchStats) -> dict[str, Any]:
    # Copied into plain ints/bools under the lock, never the live
    # ImageBatchStats object itself - same "snapshot before crossing the
    # thread boundary" reasoning as ui/workers.py::_copy_image_batch_stats(),
    # just for a lock instead of a Qt signal.
    return {
        "files_processed": stats.files_processed,
        "files_total": stats.files_total,
        "translated": stats.translated,
        "skipped": stats.skipped,
        "failed": stats.failed,
        "chars_sent": stats.chars_sent,
        "cancelled": stats.cancelled,
    }


@dataclass
class _JobState:
    id: str
    request: TranslationRequest
    output_dir: Path
    max_chars_per_run: int
    status: str = "running"  # "running" | "done" | "failed" | "cancelled"
    progress_message: str = ""
    stats: dict[str, Any] = field(
        default_factory=lambda: {
            "files_processed": 0,
            "files_total": 0,
            "translated": 0,
            "skipped": 0,
            "failed": 0,
            "chars_sent": 0,
            "cancelled": False,
        }
    )
    error: str | None = None
    result: ImageBatchJobResult | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


def start_job(body: dict[str, Any]) -> dict[str, Any]:
    """Backs POST /api/jobs. Re-runs every one of ui/app.py::_start()'s
    fail-fast checks server-side (validation_errors(), credential_status(),
    ocr_engine_available(), inpainting_backend_available()) - the
    RoadMap.md Leitprinzip ("jeder kostenpflichtige Lauf braucht Analyse,
    Kostenschätzung und ausdrückliche Bestätigung vor der Ausführung") is
    NOT satisfied by the frontend having called /api/analyze at some
    earlier point; a client that skips straight to /api/jobs must be
    rejected here exactly as if it had never analyzed at all. The actual
    confirmation-gate WIRING (frontend only enables the button after a
    successful analyze) is Schritt 5 - this function's checks are the
    server half of that gate and work standalone already.
    """
    global _ACTIVE_JOB_ID

    try:
        request = _request_from_json(body)
    except AnalyzeRequestError as exc:
        return {"ok": False, "errors": [str(exc)]}

    errors = request.validation_errors()
    if errors:
        return {"ok": False, "errors": errors}
    if credential_status(request.provider) == "credential.missing":
        return {"ok": False, "errors": [f'Kein API-Schlüssel für "{request.provider}" hinterlegt.']}
    if not ocr_engine_available(request.ocr_engine):
        return {
            "ok": False,
            "errors": [f'OCR-Engine "{request.ocr_engine}" ist auf diesem System nicht verfügbar.'],
        }
    if not inpainting_backend_available(request.inpainting_backend):
        return {
            "ok": False,
            "errors": [
                f'Rückschreibe-Methode "{request.inpainting_backend}" ist auf diesem System nicht verfügbar.'
            ],
        }

    output_dir_raw = body.get("output_dir")
    if not isinstance(output_dir_raw, str) or not output_dir_raw.strip():
        return {"ok": False, "errors": ["Zielordner fehlt."]}
    output_dir = Path(output_dir_raw)

    max_chars = body.get("max_chars_per_run")
    max_chars = int(max_chars) if max_chars else settings_store.load().get("max_chars", DEFAULT_MAX_CHARS_PER_RUN)

    with _JOBS_LOCK:
        if _ACTIVE_JOB_ID is not None and _JOBS[_ACTIVE_JOB_ID].status == "running":
            return {"ok": False, "errors": ["Ein Lauf ist bereits aktiv."]}
        job = _JobState(id=uuid.uuid4().hex, request=request, output_dir=output_dir, max_chars_per_run=max_chars)
        job.stats["files_total"] = len(request.source_paths)
        _JOBS[job.id] = job
        _ACTIVE_JOB_ID = job.id

    def _progress(message: str) -> None:
        with _JOBS_LOCK:
            job.progress_message = message

    def _stats(stats: ImageBatchStats) -> None:
        with _JOBS_LOCK:
            job.stats = _snapshot_stats(stats)

    def _total(count: int) -> None:
        with _JOBS_LOCK:
            job.stats["files_total"] = count

    def _run() -> None:
        global _ACTIVE_JOB_ID
        try:
            result = run_image_batch_job(
                list(request.source_paths),
                output_dir,
                request.provider,
                PRICING[request.provider],
                request.target_language,
                request.source_language,
                list(request.protected_terms),
                job.max_chars_per_run,
                ocr_engine_name=request.ocr_engine,
                inpainting_backend_name=request.inpainting_backend,
                progress_callback=_progress,
                stats_callback=_stats,
                should_cancel=job.cancel_event.is_set,
                total_callback=_total,
            )
        except Exception as exc:  # noqa: BLE001 - mirrors ImageTranslationWorker.run()'s own catch-all
            with _JOBS_LOCK:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
        else:
            with _JOBS_LOCK:
                job.result = result
                job.stats = _snapshot_stats(result.stats)
                job.status = "cancelled" if result.stats.cancelled else "done"
        finally:
            with _JOBS_LOCK:
                if _ACTIVE_JOB_ID == job.id:
                    _ACTIVE_JOB_ID = None

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "job_id": job.id}


def job_status(job_id: str) -> dict[str, Any]:
    """Backs GET /api/jobs/<id>/status - polled every 750ms-1s by app.js
    (see the migration plan's "Polling statt SSE/WebSockets"-Entscheidung).
    Returns a flat dict merging ImageBatchStats' fields directly at the
    top level (files_processed/files_total/translated/skipped/failed/
    chars_sent/cancelled) rather than nesting them under a "stats" key -
    keeps app.js's polling code a single flat read, no path-drilling.
    """
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "errors": ["Unbekannter Job."]}
        return {
            "ok": True,
            "status": job.status,
            "progress_message": job.progress_message,
            "error": job.error,
            **job.stats,
        }


def cancel_job(job_id: str) -> dict[str, Any]:
    """Backs POST /api/jobs/<id>/cancel - mirrors
    ImageTranslationWorker.request_cancel(): only sets the cooperative
    threading.Event, does not block waiting for the run to actually stop
    (run_image_batch_job() polls should_cancel() between files - see that
    function's own docstring on when cancellation takes effect)."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "errors": ["Unbekannter Job."]}
        if job.status != "running":
            return {"ok": False, "errors": ["Lauf ist nicht mehr aktiv."]}
        job.cancel_event.set()
        return {"ok": True}


def _file_entry(item: ImageJobResult) -> dict[str, Any]:
    """The per-file dict shape job_result() returns under "files" - pulled
    out on its own (Schritt 7) so webapp/review_bridge.py's
    apply_correction_result() below can return the SAME shape for a
    freshly re-rendered file without duplicating this list-of-fields
    somewhere else. has_correctable_regions mirrors the exact condition
    ui/app.py's correction-dialog button visibility uses: whether this
    file's ImageTranslationStats.replacements (successfully translated
    regions, the same list handed to inpainting_backend.apply()) is
    non-empty - see pipeline/images/translate_image.py's
    ImageTranslationStats.replacements docstring.
    """
    return {
        "source": str(item.source_path),
        "output": str(item.output_path),
        "qa_report": str(item.qa_report_path),
        "translated": item.stats.translated,
        "skipped": item.stats.skipped,
        "failed": item.stats.failed,
        "chars_sent": item.stats.chars_sent,
        "has_correctable_regions": bool(item.stats.replacements),
    }


def job_result(job_id: str) -> dict[str, Any]:
    """Backs GET /api/jobs/<id>/result - only meaningful once status is
    "done"/"cancelled" (a cancelled batch still keeps every file finished
    before the cancellation, see run_image_batch_job()'s docstring, so its
    partial file list is real and worth returning too, not just an
    error).
    """
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "errors": ["Unbekannter Job."]}
        if job.status == "running":
            return {"ok": False, "errors": ["Lauf ist noch nicht abgeschlossen."]}
        if job.status == "failed":
            return {"ok": False, "errors": [job.error or "Lauf fehlgeschlagen."]}
        result = job.result

    assert result is not None  # status done/cancelled always sets .result, see _run() above
    files = [_file_entry(item) for item in result.stats.results]
    return {
        "ok": True,
        "status": job.status,
        "output_dir": str(result.output_dir),
        "files": files,
    }


def job_qa_report(job_id: str, file_path: str) -> dict[str, Any]:
    """Backs GET /api/jobs/<id>/qa-report?file=<path> (Schritt 7) - returns
    the raw text of ONE image's QA report, so app.js can render it inline
    in a <pre> block. Replaces ui/app.py::_open_qa_report()'s
    QDesktopServices.openUrl() for this pilot: the images-mode Qt UI has
    no per-file "open report" button at all (one QA report PER image, see
    job_result()'s docstring above) - it just says "look in the output
    folder yourself" (job.result_summary_images). A local page can show
    the text directly instead, which is strictly more useful than the Qt
    app's own images-mode behavior, not merely a port of it.

    `file_path` MUST exactly match one of THIS job's own
    ImageJobResult.qa_report_path values (the same paths already returned
    by job_result() under "qa_report") - never an arbitrary caller-supplied
    path. Without this check, this LOCAL-ONLY, unauthenticated server (see
    webapp/server.py's module docstring) would read any file readable by
    the process for a query string like "?file=/etc/passwd" - the same
    class of mistake server.py's _serve_static() already guards against
    for static files (see its traversal check), just here for a dynamic
    per-job argument instead of a fixed directory.
    """
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "errors": ["Unbekannter Job."]}
        if job.status == "running":
            return {"ok": False, "errors": ["Lauf ist noch nicht abgeschlossen."]}
        if job.status == "failed":
            return {"ok": False, "errors": [job.error or "Lauf fehlgeschlagen."]}
        result = job.result

    assert result is not None  # status done/cancelled always sets .result, see _run() above
    known_paths = {str(item.qa_report_path) for item in result.stats.results}
    if not file_path or file_path not in known_paths:
        return {"ok": False, "errors": ["Unbekannte QA-Bericht-Datei für diesen Lauf."]}

    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "errors": [f"QA-Bericht konnte nicht gelesen werden: {exc}"]}
    return {"ok": True, "text": text}


# --- Bild-Korrektur-Übergabe (Schritt 8) ---------------------------------
#
# webapp/review_bridge.py drives image_translate_cli/review_server.py's
# browser-based correction UI in a non-blocking way (a review session can
# stay open for up to 30 minutes waiting for a human - see that module's
# own docstring for why it needs its own background thread rather than
# blocking an HTTP request handler). The two functions below are the only
# points where review_bridge.py touches _JOBS/_JOBS_LOCK - kept here,
# like every other _JOBS access, rather than reaching into this module's
# "private" state from outside it.


def get_correctable_file(
    job_id: str, file_index: int
) -> tuple[Path, Path, list[TextReplacement], str] | dict[str, Any]:
    """Looks up file `file_index` of job `job_id`'s stored result and
    returns (source_path, output_path, replacements, inpainting_backend
    name) if that file actually has correctable regions, else an
    {"ok": False, "errors": [...]} dict - review_bridge.start_correction()
    uses this instead of reaching into _JOBS directly. `replacements` is
    copied out of the stored ImageJobResult (list(...) below) so a
    concurrent correction round on a DIFFERENT file of the same job can't
    ever see a partially-mutated list - each file's replacements are only
    ever replaced wholesale, never edited in place, but this keeps that
    guarantee explicit rather than relying on it.
    """
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "errors": ["Unbekannter Job."]}
        if job.status == "running":
            return {"ok": False, "errors": ["Lauf ist noch nicht abgeschlossen."]}
        if job.status == "failed":
            return {"ok": False, "errors": [job.error or "Lauf fehlgeschlagen."]}
        result = job.result
        assert result is not None  # status done/cancelled always sets .result, see _run() above
        results = result.stats.results
        if file_index < 0 or file_index >= len(results):
            return {"ok": False, "errors": ["Unbekannte Datei-Nummer für diesen Lauf."]}
        target = results[file_index]
        if not target.stats.replacements:
            return {"ok": False, "errors": ["Dieses Bild hat keine korrigierbaren Regionen."]}
        return (
            target.source_path,
            target.output_path,
            list(target.stats.replacements),
            job.request.inpainting_backend,
        )


def apply_correction_result(job_id: str, file_index: int, corrected: ImageJobResult) -> dict[str, Any]:
    """Splices a freshly re-rendered ImageJobResult (from
    ui/image_job.py::run_image_correction_job(), called by
    webapp/review_bridge.py once a human clicked "Anwenden") back into job
    `job_id`'s stored batch result at `file_index` - the HTTP-layer
    equivalent of ui/app.py::_open_image_correction_dialog()'s identical
    splice, addressed by index (stable within one job - job_result()'s
    "files" list is never reordered, only individual entries are replaced
    in place) instead of Python object identity, which only makes sense
    inside a single process holding onto the original object. Returns the
    same per-file dict shape job_result() already returns for this file
    (see _file_entry() above), so review_bridge.correction_status() can
    hand it straight to the frontend without a second round trip through
    /api/jobs/<id>/result.
    """
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None or job.result is None:
            return {"ok": False, "errors": ["Unbekannter Job."]}
        results = job.result.stats.results
        if file_index < 0 or file_index >= len(results):
            return {"ok": False, "errors": ["Unbekannte Datei-Nummer für diesen Lauf."]}
        results[file_index] = corrected
        return _file_entry(corrected)
