"""Non-blocking bridge between webapp/server.py's HTTP handlers and
image_translate_cli/review_server.py's browser-based region-correction UI
(Schritt 8 of the local-server + pywebview migration, see Backlog.md
26.08.2026 and the plan this package was built from).

Why this needs its own module instead of living in job_bridge.py: a
review session can stay open for up to 30 minutes (ReviewSession.wait()'s
default timeout, unchanged from image_translate_cli's own `review`
command) waiting for a human to click "Anwenden"/"Abbrechen" in a
SEPARATE browser tab/window - an HTTP request handler must never block
that long (it would tie up a request thread and make the main page feel
frozen for however long the human takes). So start_correction() below
only STARTS the review server (review_server.start_review_server(),
Schritt 8's own bind/block split) and returns immediately with its URL;
a background thread then calls ReviewSession.wait() and, once the human
has acted, performs the actual re-render
(ui/image_job.py::run_image_correction_job(), unchanged - the exact same
function ui/image_correction_dialog.py's _apply() already calls for the
Qt app) and splices the corrected result back into the job's stored
batch result via job_bridge.apply_correction_result() - mirroring
ui/app.py::_open_image_correction_dialog()'s identical splice-by-position,
just driven by a background thread instead of a modal dialog's own Qt
event loop.

The frontend polls GET /api/corrections/<id>/status (same "polling, not
push" decision the migration plan already made for job status, see
job_bridge.py's own module comment on that) to learn when the human has
finished and, on success, gets the corrected file's already-updated
stats/QA-report path back in the same response - no second round trip
through /api/jobs/<id>/result needed.

Kept Qt-free like every other webapp/ HTTP-layer module (see
webapp/__init__.py's docstring): image_translate_cli/review_server.py has
no PySide6 import either, and ui/image_job.py::run_image_correction_job()
is the same Qt-independent function job_bridge.py's own job-start path
already calls into for the initial translation.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any

from image_translate_cli.review_server import ReviewSession, start_review_server
from ui.image_job import run_image_correction_job
from webapp import job_bridge

# Same default image_translate_cli/review_server.py::run_review_session()
# itself uses - a human reviewing one image from this webapp gets the
# same 30 minutes a CLI user driving `image_translate_cli review` already
# gets, not a separately-tuned value.
_DEFAULT_TIMEOUT_SECONDS = 1800.0

_CORRECTIONS_LOCK = threading.Lock()
_CORRECTIONS: dict[str, "_CorrectionState"] = {}
# (job_id, file_index) -> correction_id, present only while that
# correction's status is still "pending" - refuses a second concurrent
# correction attempt on the SAME file (mirrors job_bridge._ACTIVE_JOB_ID's
# "one thing happens to this file/job at a time" principle, just scoped
# to one file instead of the whole job - two DIFFERENT files of the same
# job may still be corrected concurrently, in two browser tabs).
_PENDING_BY_FILE: dict[tuple[str, int], str] = {}


@dataclass
class _CorrectionState:
    id: str
    job_id: str
    file_index: int
    session: ReviewSession
    status: str = "pending"  # "pending" | "applied" | "cancelled" | "timeout" | "failed"
    error: str | None = None
    file_entry: dict[str, Any] | None = None  # set once status == "applied"


def start_correction(job_id: str, file_index: int) -> dict[str, Any]:
    """Backs POST /api/jobs/<id>/files/<index>/correct. Returns
    {"ok": True, "correction_id": ..., "url": ...} immediately - the
    caller (app.js) opens `url` (window.open(), see the migration plan's
    own note on this being pywebview-Qt's native-window behavior, checked
    empirically once this landed) and polls correction_status() below
    with `correction_id` to learn the outcome.
    """
    lookup = job_bridge.get_correctable_file(job_id, file_index)
    if isinstance(lookup, dict):
        return lookup  # {"ok": False, "errors": [...]}
    source_path, destination_path, replacements, inpainting_backend_name, obstacle_regions = lookup

    key = (job_id, file_index)
    with _CORRECTIONS_LOCK:
        if key in _PENDING_BY_FILE:
            return {"ok": False, "errors": ["Für dieses Bild läuft bereits eine Korrektur."]}
        # 27.08.2026 - see start_review_server()'s own docstring (real
        # user report, Backlog.md 27.08.2026, asked for this directly:
        # "Können wir nicht Logs aus der Fenstersitzung generieren?").
        # Named after `destination_path` (not `source_path`) so it lands
        # next to the corrected image and its QA report - the two files
        # Michael already knows to look at/send.
        debug_log_path = str(destination_path.with_name(f"{destination_path.stem}_correction_debug.json"))
        session = start_review_server(str(source_path), replacements, debug_log_path=debug_log_path)
        correction_id = uuid.uuid4().hex
        state = _CorrectionState(id=correction_id, job_id=job_id, file_index=file_index, session=session)
        _CORRECTIONS[correction_id] = state
        _PENDING_BY_FILE[key] = correction_id

    def _wait_and_apply() -> None:
        # Blocks THIS background thread only (see module docstring) -
        # never the HTTP request thread that called start_correction().
        outcome, edited = session.wait(_DEFAULT_TIMEOUT_SECONDS)
        with _CORRECTIONS_LOCK:
            if outcome == "cancel":
                state.status = "cancelled"
            elif outcome == "timeout":
                state.status = "timeout"
            else:  # "apply"
                assert edited is not None  # ReviewSession.wait()'s own contract for this outcome
                try:
                    corrected = run_image_correction_job(
                        source_path,
                        destination_path,
                        edited,
                        inpainting_backend_name=inpainting_backend_name,
                        obstacle_regions=obstacle_regions,
                    )
                except Exception as exc:  # noqa: BLE001 - surfaced via status polling, not raised across threads
                    state.status = "failed"
                    state.error = f"{type(exc).__name__}: {exc}"
                else:
                    file_entry = job_bridge.apply_correction_result(job_id, file_index, corrected)
                    if file_entry.get("ok") is False:
                        # The job vanished from _JOBS or the file index no
                        # longer lines up - practically unreachable (no
                        # code path removes a finished job), but the image
                        # was already re-rendered to disk either way, so
                        # this is reported as a failure rather than
                        # silently discarded.
                        state.status = "failed"
                        state.error = "; ".join(file_entry.get("errors", [])) or "Ergebnis konnte nicht gespeichert werden."
                    else:
                        state.file_entry = file_entry
                        state.status = "applied"
            del _PENDING_BY_FILE[key]

    threading.Thread(target=_wait_and_apply, daemon=True).start()
    return {"ok": True, "correction_id": correction_id, "url": session.url}


def correction_status(correction_id: str) -> dict[str, Any]:
    """Backs GET /api/corrections/<id>/status - polled by app.js while
    status stays "pending" (the human's browser tab is still open)."""
    with _CORRECTIONS_LOCK:
        state = _CORRECTIONS.get(correction_id)
        if state is None:
            return {"ok": False, "errors": ["Unbekannte Korrektur."]}
        payload: dict[str, Any] = {"ok": True, "status": state.status}
        if state.status == "applied":
            payload["file"] = state.file_entry
        elif state.status == "failed":
            payload["errors"] = [state.error or "Korrektur fehlgeschlagen."]
        return payload
