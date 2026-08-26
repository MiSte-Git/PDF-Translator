"""LOCAL ONLY - no auth. Minimal stdlib HTTP server for webapp/, matching
image_translate_cli/review_server.py's own established pattern
(ThreadingHTTPServer + BaseHTTPRequestHandler, bound to 127.0.0.1, no
framework, no third-party dependency) rather than introducing a new
approach for this pilot.

Deliberately thin: every route handler below does request parsing and
JSON serialization only - all actual logic (which providers exist, what
an analysis costs) lives in webapp/job_bridge.py and can be tested there
without any HTTP machinery involved. See job_bridge.py's own docstring.

This module covers /api/config and /api/analyze only (Schritt 2 of the
migration plan) - both read-only, neither has a side effect, on purpose:
they prove the HTTP foundation and the reuse of pipeline.registry/
ui.analysis before anything here costs money or writes a file. /api/jobs
(which does both) is Schritt 4.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from webapp import job_bridge


def _config_route(_body: None) -> tuple[int, dict[str, Any]]:
    return 200, job_bridge.build_config()


def _analyze_route(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    result = job_bridge.analyze(body)
    return (200 if result.get("ok") else 400), result


# GET routes take no body; POST routes take the parsed JSON body (a dict -
# do_POST() below rejects anything else with a 400 before the route ever
# runs, so handlers can assume `body` is a dict).
_ROUTES_GET: dict[str, Callable[[None], tuple[int, dict[str, Any]]]] = {
    "/api/config": _config_route,
}
_ROUTES_POST: dict[str, Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]] = {
    "/api/analyze": _analyze_route,
}


class Handler(BaseHTTPRequestHandler):
    """Exact-path routing only, matching review_server.py's Handler - no
    dynamic segments needed yet (/api/jobs/<id>/... arrives in Schritt 4
    and will need its own dispatch, not added here to keep this step's
    diff reviewable)."""

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

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        handler = _ROUTES_GET.get(self.path)
        if handler is None:
            self._send_json(404, {"ok": False, "errors": [f"Unbekannter Pfad: {self.path}"]})
            return
        status, payload = handler(None)
        self._send_json(status, payload)

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        handler = _ROUTES_POST.get(self.path)
        if handler is None:
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
        status, payload = handler(body)
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
