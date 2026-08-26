"""Regression coverage for webapp/review_bridge.py's Schritt-8 correction
bridge (POST /api/jobs/<id>/files/<index>/correct + GET
/api/corrections/<id>/status, wired in webapp/server.py) - see Backlog.md
26.08.2026's Schritt-8 entry and the migration plan's "Nach Abschluss
ruft job_bridge.py run_image_correction_job() ... auf und aktualisiert
das gespeicherte Job-Ergebnis"-requirement.

Same "real HTTP calls, no mocking of the module under test" style as
tests/test_webapp_jobs_api.py/tests/test_review_server.py: a real batch
translation run produces a real correctable image (box_overlay always
produces at least one TextReplacement for recognized text), then a
background thread plays the human's role against the REVIEW server's own
URL (review_bridge.start_correction() hands back) - exactly like
tests/test_review_server.py already does for the CLI's `review` command,
just reached through webapp/server.py's HTTP routes this time instead of
calling review_server.py directly.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

import ui.image_job as image_job_module
from pipeline.images.ocr import tesseract_available
from pipeline.translation.base import TranslationResult
from webapp import server as webapp_server

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class FakeProvider:
    """Same shape/contract as tests/test_webapp_jobs_api.py's own
    FakeProvider - see that file's docstring for why this is injected via
    monkeypatching ui.image_job.build_provider rather than a `provider=`
    parameter."""

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def _build_image(path: Path, text: str) -> None:
    font = ImageFont.truetype(_FONT_PATH, 24)
    image = Image.new("RGB", (300, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), text, fill="black", font=font)
    image.save(path)


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


@pytest.fixture
def fake_deepl_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPL_API_KEY", "test-only-fake-key")


def _post_json(url: str, body: object) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _get_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _poll_until_finished(base_url: str, job_id: str, timeout_seconds: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status, payload = _get_json(f"{base_url}/api/jobs/{job_id}/status")
        assert status == 200
        if payload["status"] != "running":
            return payload
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish within {timeout_seconds}s")


def _poll_correction_until_finished(base_url: str, correction_id: str, timeout_seconds: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status, payload = _get_json(f"{base_url}/api/corrections/{correction_id}/status")
        assert status == 200
        if payload["status"] != "pending":
            return payload
        time.sleep(0.05)
    raise AssertionError(f"correction {correction_id} did not finish within {timeout_seconds}s")


def _run_batch_job(running_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, dict]:
    monkeypatch.setattr(image_job_module, "build_provider", lambda name: FakeProvider())
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")
    status, start_payload = _post_json(
        f"{running_server}/api/jobs",
        {
            "source_paths": [str(source)],
            "output_dir": str(tmp_path / "out"),
            "provider": "deepl",
            "ocr_engine": "tesseract",
            "inpainting_backend": "box_overlay",
        },
    )
    assert status == 200 and start_payload["ok"] is True
    job_id = start_payload["job_id"]
    _poll_until_finished(running_server, job_id)
    status, result_payload = _get_json(f"{running_server}/api/jobs/{job_id}/result")
    assert status == 200 and result_payload["ok"] is True
    return job_id, result_payload


def test_start_correction_and_apply_updates_the_job_result(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_id, result_payload = _run_batch_job(running_server, tmp_path, monkeypatch)
    assert result_payload["files"][0]["has_correctable_regions"] is True
    original_qa_report = result_payload["files"][0]["qa_report"]

    status, start_payload = _post_json(f"{running_server}/api/jobs/{job_id}/files/0/correct", {})
    assert status == 200
    assert start_payload["ok"] is True
    correction_id = start_payload["correction_id"]
    review_url = start_payload["url"]
    assert review_url.startswith("http://127.0.0.1:")

    # A real browser would GET / then /api/state + /api/image, let a
    # human edit, and POST /api/apply - here (same as
    # tests/test_review_server.py) this test plays that role directly
    # against the review session's own (separate) HTTP server.
    state_status, state_payload = _get_json(review_url + "api/state")
    assert state_status == 200
    assert len(state_payload["regions"]) >= 1
    edited_region = dict(state_payload["regions"][0])
    edited_region["translated_text"] = "Hallo (korrigiert)"

    status, apply_payload = _post_json(review_url + "api/apply", [edited_region])
    assert status == 200 and apply_payload["ok"] is True

    final = _poll_correction_until_finished(running_server, correction_id)
    assert final["status"] == "applied"
    assert final["file"]["translated"] == len(state_payload["regions"])
    # run_image_correction_job() overwrites the SAME output/QA-report
    # paths in place (see its own docstring) - the path stays equal to
    # original_qa_report on purpose; what must change is the CONTENT,
    # proven below via the "nach manueller Korrektur" marker
    # _build_correction_qa_report() always writes.
    assert final["file"]["qa_report"] == original_qa_report
    correction_qa_text = Path(final["file"]["qa_report"]).read_text(encoding="utf-8")
    assert "nach manueller Korrektur" in correction_qa_text

    # job_result() must reflect the corrected file from now on, not the
    # stale pre-correction one - same splice-then-refresh contract
    # ui/app.py::_open_image_correction_dialog() already guarantees for
    # the Qt app (see webapp/job_bridge.py::apply_correction_result()'s
    # docstring).
    status, refreshed = _get_json(f"{running_server}/api/jobs/{job_id}/result")
    assert status == 200
    qa_text = Path(refreshed["files"][0]["qa_report"]).read_text(encoding="utf-8")
    assert "nach manueller Korrektur" in qa_text


def test_start_correction_and_cancel_leaves_the_job_result_untouched(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_id, result_payload = _run_batch_job(running_server, tmp_path, monkeypatch)
    original_qa_report = result_payload["files"][0]["qa_report"]

    status, start_payload = _post_json(f"{running_server}/api/jobs/{job_id}/files/0/correct", {})
    assert status == 200 and start_payload["ok"] is True
    review_url = start_payload["url"]

    status, cancel_payload = _post_json(review_url + "api/cancel", {})
    assert status == 200 and cancel_payload["ok"] is True

    final = _poll_correction_until_finished(running_server, start_payload["correction_id"])
    assert final["status"] == "cancelled"

    status, refreshed = _get_json(f"{running_server}/api/jobs/{job_id}/result")
    assert status == 200
    assert refreshed["files"][0]["qa_report"] == original_qa_report


def test_start_correction_refuses_a_second_concurrent_attempt_on_the_same_file(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_id, _ = _run_batch_job(running_server, tmp_path, monkeypatch)

    status, first = _post_json(f"{running_server}/api/jobs/{job_id}/files/0/correct", {})
    assert status == 200 and first["ok"] is True

    status, second = _post_json(f"{running_server}/api/jobs/{job_id}/files/0/correct", {})
    assert status == 400
    assert second["ok"] is False
    assert second["errors"] == ["Für dieses Bild läuft bereits eine Korrektur."]

    # Clean up: cancel the still-open review session so its background
    # thread/server don't linger past this test.
    _post_json(first["url"] + "api/cancel", {})
    _poll_correction_until_finished(running_server, first["correction_id"])


def test_start_correction_for_unknown_job_returns_400(running_server: str) -> None:
    status, payload = _post_json(f"{running_server}/api/jobs/does-not-exist/files/0/correct", {})
    assert status == 400
    assert payload["ok"] is False


def test_start_correction_for_out_of_range_file_index_returns_400(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_id, _ = _run_batch_job(running_server, tmp_path, monkeypatch)
    status, payload = _post_json(f"{running_server}/api/jobs/{job_id}/files/5/correct", {})
    assert status == 400
    assert payload["ok"] is False


def test_correction_status_for_unknown_id_returns_404(running_server: str) -> None:
    status, payload = _get_json(f"{running_server}/api/corrections/does-not-exist/status")
    assert status == 404
    assert payload["ok"] is False
