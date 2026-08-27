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
from urllib.parse import quote

import pytest
from PIL import Image, ImageDraw, ImageFont

import ui.image_job as image_job_module
from pipeline.images.ocr import tesseract_available
from pipeline.translation.base import TranslationResult
from webapp import server as webapp_server
from webapp import settings_store

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="Tesseract binary not installed")

_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@pytest.fixture(autouse=True)
def _isolated_settings_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """27.08.2026, Task #14: start_job() below now calls settings_store.save()
    for real (see webapp/job_bridge.py's own comment on that call) - without
    this, every test in this file that starts a job would write into the
    REAL per-user config file (settings_store.config_dir(), e.g.
    ~/.config/pdf-translator/settings.json on Linux) on whatever machine
    runs this suite, exactly the leak tests/conftest.py's QSettings fixture
    already prevents for the Qt app. Kept file-local (not in conftest.py)
    because tests/test_webapp_settings_store.py's own test_config_dir_*
    tests deliberately exercise config_dir()'s real platform branching - a
    suite-wide patch there would break the tests meant to verify it."""
    monkeypatch.setattr(settings_store, "config_dir", lambda: tmp_path / "webapp-config")


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
    # No /api/analyze call anywhere in this test - Schritt 5's
    # confirmation gate (app.js only enables the Start button after a
    # successful analyze + a checked confirmation box) is a client-side
    # UX affordance, not what makes /api/jobs safe. This test's success
    # here, together with test_start_job_enforces_checks_without_a_prior_
    # analyze_call's rejection below, is the concrete proof for both
    # directions of that claim.
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


def test_start_job_persists_form_state_for_the_next_session(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """27.08.2026 regression guard - real user report, Backlog.md
    27.08.2026, Michael: "Im Web View werden die Einstellungen der
    vorigen Sitzung nicht gespeichert." Root cause: settings_store.save()
    was never called anywhere in webapp/ - start_job() above now calls it
    once a submitted request has passed every fail-fast check. Proves both
    ends of the fix: the JSON file on disk (settings_store.load(), the
    same function build_config() itself uses to prefill a NEW session's
    form - i.e. what a page reload/app restart would actually see) AND
    the live /api/config response reflect the just-submitted values
    afterwards, without a second request or restart needed."""
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
            "source_language": "EN",
            "target_language": "FR",
            "protected_terms": ["Acme", "Foo"],
            "ocr_engine": "tesseract",
            "inpainting_backend": "box_overlay",
        },
    )
    assert status == 200
    assert start_payload["ok"] is True
    _poll_until_finished(running_server, start_payload["job_id"])

    on_disk = settings_store.load()
    assert on_disk["provider"] == "deepl"
    assert on_disk["last_output_dir"] == str(output_dir)
    assert on_disk["last_source_dir"] == str(source.parent)
    assert on_disk["form"]["source_lang"] == "EN"
    assert on_disk["form"]["target_lang"] == "FR"
    assert on_disk["form"]["protected_terms"] == "Acme\nFoo"
    assert on_disk["form"]["ocr_engine"] == "tesseract"
    assert on_disk["form"]["inpainting_backend"] == "box_overlay"

    status, config_payload = _get_json(f"{running_server}/api/config")
    assert status == 200
    assert config_payload["last_form_state"]["form"]["target_lang"] == "FR"
    assert config_payload["last_form_state"]["last_output_dir"] == str(output_dir)


def test_start_job_does_not_persist_a_rejected_request(
    running_server: str, tmp_path: Path
) -> None:
    """The other half of the fix's own docstring claim ("a request that
    gets rejected below never reaches here, so a typo'd form never
    overwrites a good remembered one") - a request missing credentials
    fails start_job()'s fail-fast checks BEFORE settings_store.save(), so
    the on-disk file must stay exactly at DEFAULTS."""
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")

    status, payload = _post_json(
        f"{running_server}/api/jobs",
        {
            "source_paths": [str(source)],
            "output_dir": str(tmp_path / "out"),
            "provider": "deepl",
            "target_language": "FR",
        },
    )
    assert status == 400
    assert payload["ok"] is False  # no DEEPL_API_KEY set in this test

    assert settings_store.load() == settings_store.DEFAULTS


def test_start_job_enforces_checks_without_a_prior_analyze_call(
    running_server: str, tmp_path: Path
) -> None:
    """Schritt 5, the other half of the confirmation-gate proof: a client
    that skips /api/analyze entirely and posts straight to /api/jobs is
    rejected by the SAME fail-fast checks as ui/app.py::_start() runs
    (here: missing credential, no fake_deepl_credential fixture) - the
    RoadMap.md Leitprinzip holds even for a client that never asked for a
    cost estimate at all, not just one that asked and was ignored.
    """
    source = tmp_path / "photo.png"
    _build_image(source, "Hello")
    status, payload = _post_json(
        f"{running_server}/api/jobs",
        {"source_paths": [str(source)], "output_dir": str(tmp_path / "out"), "provider": "deepl"},
    )
    assert status == 400
    assert payload["ok"] is False
    assert any("deepl" in message for message in payload["errors"])


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


# --- /api/jobs/<id>/qa-report (Schritt 7) --------------------------------


def test_qa_report_returns_the_real_report_text_for_a_finished_job(
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

    status, result_payload = _get_json(f"{running_server}/api/jobs/{job_id}/result")
    qa_report_path = result_payload["files"][0]["qa_report"]

    status, payload = _get_json(f"{running_server}/api/jobs/{job_id}/qa-report?file={quote(qa_report_path)}")
    assert status == 200
    assert payload["ok"] is True
    # Same file, read a second time directly from disk - proves the route
    # returns the REAL report content, not a placeholder/echo of the path.
    assert payload["text"] == Path(qa_report_path).read_text(encoding="utf-8")
    assert "Bildübersetzung - QA-Bericht" in payload["text"]


def test_qa_report_rejects_a_path_that_is_not_this_jobs_own_report(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The `file` query parameter is not a free-form filesystem path - see
    job_bridge.job_qa_report()'s docstring: this LOCAL-ONLY, unauthenticated
    server must never read a caller-supplied path that isn't one of THIS
    job's own known QA report files. A real, unrelated, existing file
    (this test module itself) is used here rather than a path that simply
    doesn't exist, to prove the check is an allow-list, not just an
    os.path.exists() guard that a real file would sail through.
    """
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

    unrelated_real_file = str(Path(__file__).resolve())
    status, payload = _get_json(f"{running_server}/api/jobs/{job_id}/qa-report?file={quote(unrelated_real_file)}")
    assert status == 404
    assert payload["ok"] is False


def test_qa_report_for_unknown_job_returns_404(running_server: str) -> None:
    status, payload = _get_json(f"{running_server}/api/jobs/does-not-exist/qa-report?file=/tmp/whatever.txt")
    assert status == 404
    assert payload["ok"] is False


def test_qa_report_before_job_finishes_is_rejected(
    running_server: str, fake_deepl_credential: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(image_job_module, "build_provider", lambda name: FakeProvider(delay_seconds=0.5))
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

    status, payload = _get_json(f"{running_server}/api/jobs/{job_id}/qa-report?file=/tmp/whatever.txt")
    assert status == 404
    assert payload["ok"] is False
    assert payload["errors"] == ["Lauf ist noch nicht abgeschlossen."]

    _poll_until_finished(running_server, job_id)
