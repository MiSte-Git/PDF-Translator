"""Real-browser (Chromium via Playwright) regression coverage for two
Backlog.md 27.08.2026 bugs that Python-only tests completely missed,
because both live entirely in how a real browser resolves DOM/selection
behavior - something no amount of server-side or pure-string testing can
exercise:

1. Enter inside the correction browser's editable textbox - three
   straight hand-built fixes (a lone "\n" text node via
   Range.insertNode(), document.execCommand('insertText', ...), a direct
   text-node data splice) all LOOKED correct from reading the code, and
   the 266 Python tests kept passing through every one of them, but each
   was reproducibly broken the moment a real Chromium actually typed into
   the box (see image_translate_cli/review_server.py's own 27.08.2026
   comment for the blow-by-blow). Real user report: "im Korrekturfenster
   schaut alles nahezu perfekt aus und nach Übernahme ist einiges wieder
   zerschossen."

2. webapp/static/app.js::loadConfig() never read the already-correctly-
   saved `last_output_dir` back into the #output-dir field - a one-line
   omission no Python test could ever catch, since nothing server-side
   was wrong (webapp/job_bridge.py::start_job() saved it correctly the
   whole time). Real user report: "Der Zielordner wird nicht
   gespeichert."

Deliberately optional (pytest.importorskip below): Playwright/Chromium
is not a project dependency (see requirements.txt - it isn't there) and
is not expected to be installed on Michael's machine. `pytest tests/`
must keep working there exactly as before; these two tests just skip
with a clear reason instead of erroring when the browser isn't
available, the same way tests/test_webapp_jobs_api.py's own
tesseract_available() skip already handles a missing OS-level
dependency. Where they DO run (this project's own dev sandbox has
Playwright/Chromium preinstalled), they are the only tests in this suite
that drive a real browser end to end - keep them, this is exactly the
class of bug three straight "all tests pass" ship attempts missed.
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

playwright_sync_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_sync_api.sync_playwright

from image_translate_cli.review_server import start_review_server
from pipeline.images.inpainting import TextReplacement
from pipeline.images.ocr import OcrTextRegion
from webapp import settings_store
from webapp.server import create_server


@pytest.fixture
def chromium_page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        yield page
        browser.close()


def test_enter_in_correction_textbox_produces_a_forced_line_break_end_to_end(
    tmp_path: Path, chromium_page
) -> None:
    # A tiny real JPEG is enough - review_server.py only ever streams
    # source_path's bytes back for /api/image, never decodes it itself.
    from PIL import Image

    source = tmp_path / "quelle.jpg"
    Image.new("RGB", (400, 200), "white").save(source)

    region = OcrTextRegion(text="Titel", x=10, y=10, width=300, height=60, confidence=95.0)
    replacement = TextReplacement(region=region, translated_text="GEIST SEELE FLEISCHANZUG")
    session = start_review_server(str(source), [replacement])

    chromium_page.goto(session.url)
    chromium_page.wait_for_selector(".region-text")
    text_el = chromium_page.query_selector(".region-text")
    text_el.click()
    chromium_page.keyboard.press("Control+A")
    chromium_page.keyboard.type("GEIST SEELE")
    chromium_page.keyboard.press("Enter")
    chromium_page.keyboard.type("FLEISCHANZUG")

    collected = chromium_page.evaluate("collectRegions()")
    assert collected[0]["translated_text"] == "GEIST SEELE\nFLEISCHANZUG"

    chromium_page.click("#apply-btn")
    outcome, replacements = session.wait(timeout_seconds=5.0)
    assert outcome == "apply"
    assert replacements is not None
    assert replacements[0].translated_text == "GEIST SEELE\nFLEISCHANZUG"


def test_output_dir_field_is_restored_from_saved_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, chromium_page
) -> None:
    monkeypatch.setattr(settings_store, "config_dir", lambda: tmp_path / "webapp-config")
    settings_store.save(
        {
            "provider": "google",
            "last_output_dir": "/home/michael/Projekte/PDF-Translator/tests/output",
            "form": {
                "source_lang": "",
                "target_lang": "DE",
                "protected_terms": "",
                "ocr_engine": "paddleocr",
                "inpainting_backend": "gpu_inpainting",
            },
        }
    )

    server = create_server()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        chromium_page.goto(f"http://127.0.0.1:{port}/")
        chromium_page.wait_for_selector("#output-dir")
        chromium_page.wait_for_function("document.getElementById('output-dir').value.length > 0")
        value = chromium_page.evaluate("document.getElementById('output-dir').value")
        assert value == "/home/michael/Projekte/PDF-Translator/tests/output"
    finally:
        server.shutdown()
