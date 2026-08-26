"""Regression coverage for webapp/server.py + webapp/job_bridge.py's
/api/jobs routes (Schritt 4 of the local-server + pywebview migration,
see Backlog.md 26.08.2026 and the plan this package was built from).

Separate file from tests/test_webapp_images_api.py (Schritt 2/3's
/api/config + /api/analyze + static serving) - this is the first route
with real side effects (spends a translation provider's budget, writes
files to disk), so it gets its own fixtures (a FakeProvider injected the
same way tests/test_image_batch_job.py already does for
run_image_batch_job() itself, plus a real generated test image) rather
than reusing the read-only file's setup.

Real HTTP calls via urllib.request against a server bound to port=0, same
style as the rest of tests/test_webapp_*.py.
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
    """Same shape/contract as tests/test_image_batch_job.py's FakeProvider -
    no network call, deterministic output - injected here by monkeypatching
    ui.image_job.build_provider (the name ui/image_job.py actually looks up
    at call time) rather than passing `provider=` directly, since
    webapp/job_bridge.py's start_job() never exposes that parameter to a
    caller (a webapp/ HTTP client must always go through the real registry -
    see start_job()'s own docstring on why the fail-fast checks matter)."""

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
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
    # start_job()'s credential_status() fail-fast check needs SOME key
    # present - a fake one is enough since build_provider() itself is
    # monkeypatched below and never actually reads it.
    monkeypatch.setenv("DEEPL_API_KEY", "test-only-fake-key")


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


def test_start_job_runs_a_real_batch_end_to_end(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(image_job_module, "build_provider", lambda name: FakeProvider())
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")
    output_dir = tmp_path / "out"

    status, start_payload = _post_json(
        f"{running_server}/api/jobs",
        {
            "source_paths": [str(source)],
            "output_dir": str(output_dir),
            "provider": "deepl",
            "target_language": "DE",
            "ocr_engine": "tesseract",
            "inpainting_backend": "box_overlay",
        },
    )
    assert status == 200
    assert start_payload["ok"] is True
    job_id = start_payload["job_id"]

    final_status = _poll_until_finished(running_server, job_id)
    assert final_status["status"] == "done"
    assert final_status["files_processed"] == 1
    assert final_status["files_total"] == 1
    assert final_status["translated"] == 1

    status, result_payload = _get_json(f"{running_server}/api/jobs/{job_id}/result")
    assert status == 200
    assert result_payload["ok"] is True
    assert result_payload["output_dir"] == str(output_dir)
    assert len(result_payload["files"]) == 1
    file_entry = result_payload["files"][0]
    assert file_entry["source"] == str(source)
    assert file_entry["translated"] == 1
    assert file_entry["has_correctable_regions"] is True
    assert Path(file_entry["output"]).is_file()
    assert Path(file_entry["qa_report"]).is_file()


def test_start_job_rejects_empty_source_paths(running_server: str, fake_deepl_credential: None) -> None:
    status, payload = _post_json(
        f"{running_server}/api/jobs", {"output_dir": "/tmp/does-not-matter", "provider": "deepl"}
    )
    assert status == 400
    assert payload["ok"] is False
    assert any("Quelldatei" in message for message in payload["errors"])


def test_start_job_rejects_missing_output_dir(
    running_server: str, fake_deepl_credential: None, tmp_path: Path
) -> None:
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")
    status, payload = _post_json(f"{running_server}/api/jobs", {"source_paths": [str(source)], "provider": "deepl"})
    assert status == 400
    assert payload["ok"] is False
    assert payload["errors"] == ["Zielordner fehlt."]


def test_start_job_rejects_unavailable_ocr_engine(
    running_server: str, fake_deepl_credential: None, tmp_path: Path
) -> None:
    # google_vision has no configured API key in this environment (see
    # tests/test_webapp_images_api.py's own config-route assertion that
    # ocr_engine_available["google_vision"] is False here) - a real,
    # server-side fail-fast rejection, not a mocked one.
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")
    status, payload = _post_json(
        f"{running_server}/api/jobs",
        {
            "source_paths": [str(source)],
            "output_dir": str(tmp_path / "out"),
            "provider": "deepl",
            "ocr_engine": "google_vision",
        },
    )
    assert status == 400
    assert payload["ok"] is False
    assert any("google_vision" in message for message in payload["errors"])


def test_start_job_rejects_missing_credential(running_server: str, tmp_path: Path) -> None:
    # No fake_deepl_credential fixture here on purpose - the real fail-fast
    # check (RoadMap.md Leitprinzip) must fire even though ocr_engine/
    # inpainting_backend are both fine.
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")
    status, payload = _post_json(
        f"{running_server}/api/jobs",
        {"source_paths": [str(source)], "output_dir": str(tmp_path / "out"), "provider": "deepl"},
    )
    assert status == 400
    assert payload["ok"] is False
    assert any("deepl" in message for message in payload["errors"])


def test_second_job_is_refused_while_one_is_active(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A deliberately slow FakeProvider keeps the first job's background
    # thread in "running" long enough for a synchronous second POST from
    # this same test to observe it - avoids a flaky race on real timing.
    monkeypatch.setattr(image_job_module, "build_provider", lambda name: FakeProvider(delay_seconds=0.5))
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")

    status, first = _post_json(
        f"{running_server}/api/jobs",
        {
            "source_paths": [str(source)],
            "output_dir": str(tmp_path / "out"),
            "provider": "deepl",
            "ocr_engine": "tesseract",
            "inpainting_backend": "box_overlay",
        },
    )
    assert status == 200 and first["ok"] is True

    status, second = _post_json(
        f"{running_server}/api/jobs",
        {
            "source_paths": [str(source)],
            "output_dir": str(tmp_path / "out2"),
            "provider": "deepl",
            "ocr_engine": "tesseract",
            "inpainting_backend": "box_overlay",
        },
    )
    assert status == 400
    assert second["ok"] is False
    assert second["errors"] == ["Ein Lauf ist bereits aktiv."]

    _poll_until_finished(running_server, first["job_id"])


def test_cancel_and_status_and_result_for_unknown_job_return_404(running_server: str) -> None:
    status, payload = _get_json(f"{running_server}/api/jobs/does-not-exist/status")
    assert status == 404 and payload["ok"] is False

    status, payload = _post_json(f"{running_server}/api/jobs/does-not-exist/cancel", {})
    assert status == 404 and payload["ok"] is False

    status, payload = _get_json(f"{running_server}/api/jobs/does-not-exist/result")
    assert status == 404 and payload["ok"] is False


def test_cancel_after_job_finished_is_rejected(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
    job_id = start_payload["job_id"]
    _poll_until_finished(running_server, job_id)

    status, payload = _post_json(f"{running_server}/api/jobs/{job_id}/cancel", {})
    assert status == 404
    assert payload["ok"] is False
    assert payload["errors"] == ["Lauf ist nicht mehr aktiv."]
