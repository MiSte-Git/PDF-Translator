"""LOCAL ONLY - no auth. Minimal stdlib HTTP server for webapp/, matching
image_translate_cli/review_server.py's own established pattern
(ThreadingHTTPServer + BaseHTTPRequestHandler, bound to 127.0.0.1, no
framework, no third-party dependency) rather than introducing a new
approach for this pilot.

Deliberately thin: every route handler below does request parsing and
JSON serialization only - all actual logic (which providers exist, what
an analysis costs) lives in webapp/job_bridge.py and can be tested there
without any HTTP machinery involved. See job_bridge.py's own docstring.

Schritt 2 added /api/config and /api/analyze (both read-only). Schritt 4
adds /api/jobs (start a batch translation on a background thread) plus
its polling/cancel/result companions - the first routes with real side
effects (spends provider budget, writes files), which is why job_bridge's
own fail-fast checks (see start_job()'s docstring) matter as much as the
HTTP plumbing here. Schritt 7 adds /api/jobs/<id>/qa-report?file=... -
read-only again, but see job_bridge.job_qa_report()'s docstring for why
its `file` argument needs its own validation, not just the usual JSON
body checks.
"""
from __future__ import annotations

import json
import mimetypes
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from webapp import job_bridge

# webapp/static/ - the real HTML/CSS/JS files built in Schritt 3 (see
# webapp/static/index.html's own docstring comment and Backlog.md
# 26.08.2026) - deliberately real files, not a Python string constant
# like image_translate_cli/review_server.py's _PAGE_HTML, per the
# migration plan's "echte Dateien statt String" decision.
STATIC_DIR = (Path(__file__).resolve().parent / "static").resolve()


def _config_route(_body: None) -> tuple[int, dict[str, Any]]:
    return 200, job_bridge.build_config()


def _analyze_route(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    result = job_bridge.analyze(body)
    return (200 if result.get("ok") else 400), result


def _start_job_route(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    result = job_bridge.start_job(body)
    return (200 if result.get("ok") else 400), result


def _job_status_route(job_id: str) -> tuple[int, dict[str, Any]]:
    result = job_bridge.job_status(job_id)
    return (200 if result.get("ok") else 404), result


def _job_cancel_route(job_id: str, _body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    result = job_bridge.cancel_job(job_id)
    return (200 if result.get("ok") else 404), result


def _job_result_route(job_id: str) -> tuple[int, dict[str, Any]]:
    result = job_bridge.job_result(job_id)
    return (200 if result.get("ok") else 404), result


def _job_qa_report_route(job_id: str, file_path: str) -> tuple[int, dict[str, Any]]:
    result = job_bridge.job_qa_report(job_id, file_path)
    return (200 if result.get("ok") else 404), result


# GET routes take no body; POST routes take the parsed JSON body (a dict -
# do_POST() below rejects anything else with a 400 before the route ever
# runs, so handlers can assume `body` is a dict).
_ROUTES_GET: dict[str, Callable[[None], tuple[int, dict[str, Any]]]] = {
    "/api/config": _config_route,
}
_ROUTES_POST: dict[str, Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]] = {
    "/api/analyze": _analyze_route,
    "/api/jobs": _start_job_route,
}

# Dynamic routes ("/api/jobs/<id>/...") - a plain dict can't express a
# variable segment, so these are matched separately, checked after the
# exact-path dicts above miss. Kept to exactly the shapes each step
# needed rather than a general path-templating mechanism - nothing else in
# this app needs more than that yet.
_JOB_STATUS_RE = re.compile(r"^/api/jobs/([^/]+)/status$")
_JOB_CANCEL_RE = re.compile(r"^/api/jobs/([^/]+)/cancel$")
_JOB_RESULT_RE = re.compile(r"^/api/jobs/([^/]+)/result$")
_JOB_QA_REPORT_RE = re.compile(r"^/api/jobs/([^/]+)/qa-report$")


class Handler(BaseHTTPRequestHandler):
    """Exact-path routing for /api/config, /api/analyze, /api/jobs (POST,
    starts a job); /api/jobs/<id>/status|cancel|result|qa-report use the
    four regexes above instead, matching review_server.py's Handler
    pattern otherwise (no framework, no path-templating library)."""

    server_version = "PDFTranslatorWebapp/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        # Silent by default, same as review_server.py's Handler - a local,
        # single-user dev server printing every request to the console the
        # app was launched from is just noise, not diagnostics.
        pass

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static_file(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self._send_json(404, {"ok": False, "errors": [f"Datei nicht gefunden: {self.path}"]})
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self) -> None:
        # "/" -> index.html; everything else maps 1:1 onto webapp/static/,
        # e.g. "/app.js" -> webapp/static/app.js, "/i18n/de.json" ->
        # webapp/static/i18n/de.json (see app.js's loadCatalogue()).
        # unquote() first (a literal "%2e%2e" must resolve the same as
        # ".." before the traversal check below, not bypass it), then
        # resolve() and require the result to stay inside STATIC_DIR - a
        # request for "/../job_bridge.py" must never be served.
        raw_path = unquote(urlsplit(self.path).path)
        relative = raw_path.lstrip("/") or "index.html"
        candidate = (STATIC_DIR / relative).resolve()
        if candidate != STATIC_DIR and STATIC_DIR not in candidate.parents:
            self._send_json(404, {"ok": False, "errors": [f"Unbekannter Pfad: {self.path}"]})
            return
        self._send_static_file(candidate)

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        path = urlsplit(self.path).path
        handler = _ROUTES_GET.get(path)
        if handler is not None:
            status, payload = handler(None)
            self._send_json(status, payload)
            return
        status_match = _JOB_STATUS_RE.match(path)
        if status_match is not None:
            status, payload = _job_status_route(status_match.group(1))
            self._send_json(status, payload)
            return
        result_match = _JOB_RESULT_RE.match(path)
        if result_match is not None:
            status, payload = _job_result_route(result_match.group(1))
            self._send_json(status, payload)
            return
        qa_report_match = _JOB_QA_REPORT_RE.match(path)
        if qa_report_match is not None:
            # parse_qs() already unquotes percent-encoding (app.js sends
            # the qa_report path through encodeURIComponent()) - no
            # separate unquote() call needed here.
            query = parse_qs(urlsplit(self.path).query)
            file_path = (query.get("file") or [""])[0]
            status, payload = _job_qa_report_route(qa_report_match.group(1), file_path)
            self._send_json(status, payload)
            return
        if path.startswith("/api/"):
            # An unmatched /api/* path is a routing error, not a missing
            # static file - answer with the same JSON 404 shape every
            # other API error uses instead of silently falling through to
            # static lookup (which would 404 too, but with a confusingly
            # file-shaped message for what is really an API typo).
            self._send_json(404, {"ok": False, "errors": [f"Unbekannter Pfad: {self.path}"]})
            return
        self._serve_static()

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        path = urlsplit(self.path).path
        handler = _ROUTES_POST.get(path)
        cancel_match = None if handler is not None else _JOB_CANCEL_RE.match(path)
        if handler is None and cancel_match is None:
            self._send_json(404, {"ok": False, "errors": [f"Unbekannter Pfad: {self.path}"]})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "errors": ["Ungültiges JSON im Request-Body."]})
            return
        if not isinstance(body, dict):
            self._send_json(400, {"ok": False, "errors": ["Request-Body muss ein JSON-Objekt sein."]})
            return
        if handler is not None:
            status, payload = handler(body)
        else:
            status, payload = _job_cancel_route(cancel_match.group(1), body)
        self._send_json(status, payload)


def create_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Binds and returns a ready-to-serve server WITHOUT calling
    serve_forever() - the caller controls the serving thread (mirrors
    review_server.py's own separation of "bind" from "block"). Tests use
    port=0 to let the OS pick a free port, then read it back from
    server.server_address[1] - the same pattern review_server.py's own
    port selection relies on.
    """
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    """`python -m webapp.server` - Schritt 3's interim entry point: the
    static frontend opened in the normal system browser, no pywebview
    yet (that is Schritt 6's webapp/__main__.py bootstrap, which will
    call into this module's create_server() instead of opening a browser
    tab). Blocks in serve_forever() until interrupted - a plain
    developer-facing dev-server run, not how the shipped app will start.
    """
    httpd = create_server()
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    print(f"PDF-Translator (webapp, Schritt 3 - Bild-Modus): {url}")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
