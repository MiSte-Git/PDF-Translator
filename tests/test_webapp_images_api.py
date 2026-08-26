"""Regression coverage for webapp/server.py + webapp/job_bridge.py's
/api/config and /api/analyze routes (Schritt 2 of the local-server +
pywebview migration, see Backlog.md 26.08.2026 and the plan this package
was built from).

Real HTTP calls via urllib.request against a server bound to port=0 (the
OS picks a free port), same style as tests/test_ui_theme.py/
tests/test_image_ocr.py: concrete assertions against real responses, no
mocking of webapp.server/webapp.job_bridge themselves. The server is
started on a background thread per test and shut down in a finally block
so a failing assertion can never leak a running server into the next
test.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from webapp import server as webapp_server

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_IMAGE = REPO_ROOT / "demo_1_original.png"


@pytest.fixture
def running_server() -> Iterator[str]:
    httpd = webapp_server.create_server(port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _post_json(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_config_route_lists_providers_and_availability_flags(running_server: str) -> None:
    status, payload = _get_json(f"{running_server}/api/config")
    assert status == 200
    # "deepl" is the always-registered default provider (see
    # webapp/settings_store.py's DEFAULTS and ui/app.py's own default) -
    # asserting its presence catches a route that returns an empty/wrong
    # shape without hardcoding the full, evolving provider list.
    assert "deepl" in payload["providers"]
    assert "tesseract" in payload["ocr_engines"]
    assert "box_overlay" in payload["inpainting_backends"]
    # tesseract is a real binary on this machine (pipeline/registry.py's
    # ocr_engine_available() shells out to check) - confirms the route
    # calls the real availability check rather than always returning True.
    assert payload["ocr_engine_available"]["tesseract"] is True
    assert payload["provider_credential_status"]["deepl"] in (
        "credential.environment",
        "credential.keyring",
        "credential.missing",
    )
    assert "form" in payload["last_form_state"]


def test_analyze_route_rejects_empty_source_paths(running_server: str) -> None:
    status, payload = _post_json(f"{running_server}/api/analyze", {"provider": "deepl"})
    assert status == 400
    assert payload["ok"] is False
    assert payload["errors"]
    assert any("Quelldatei" in message for message in payload["errors"])


def test_analyze_route_rejects_source_paths_that_is_not_a_list(running_server: str) -> None:
    status, payload = _post_json(
        f"{running_server}/api/analyze", {"source_paths": "not-a-list"}
    )
    assert status == 400
    assert payload["ok"] is False
    assert payload["errors"] == ["source_paths muss eine Liste von Pfaden (Strings) sein."]


def test_analyze_route_rejects_malformed_json_body(running_server: str) -> None:
    request = urllib.request.Request(
        f"{running_server}/api/analyze",
        data=b"{not valid json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status, payload = response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, json.loads(exc.read())
    assert status == 400
    assert payload["ok"] is False


def test_unknown_path_returns_404(running_server: str) -> None:
    status, payload = _get_json(f"{running_server}/api/does-not-exist")
    assert status == 404
    assert payload["ok"] is False


@pytest.mark.skipif(not DEMO_IMAGE.is_file(), reason="demo_1_original.png not present in this checkout")
def test_analyze_route_runs_a_real_tesseract_pass_over_a_demo_image(running_server: str) -> None:
    # End-to-end proof that this route really wraps ui.analysis.analyze_request()
    # rather than a re-derived approximation (see job_bridge.py::analyze()'s
    # own docstring on why that distinction matters for the RoadMap.md
    # confirmation-gate Leitprinzip) - a real image, real Tesseract OCR,
    # real character count.
    status, payload = _post_json(
        f"{running_server}/api/analyze",
        {
            "source_paths": [str(DEMO_IMAGE)],
            "provider": "deepl",
            "target_language": "DE",
            "ocr_engine": "tesseract",
            "inpainting_backend": "box_overlay",
        },
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["mode"] == "images"
    assert payload["files"] == 1
    assert payload["units"] == 1
    assert payload["ocr_required"] is True
    assert payload["cost"]["provider"] == "deepl"
    assert payload["cost"]["max_chars_per_run"] > 0
