"""Regression coverage for image_translate_cli/review_server.py's Schritt-8
split (start_review_server()/ReviewSession.wait() vs. the now-thin
run_review_session() wrapper) and for image_translate_cli/cli.py's
`review` command itself - see Backlog.md 26.08.2026's Schritt-8 entry and
the migration plan's explicit "nach dem Split weiterhin funktioniert"-
Nachweis-Anforderung. Neither had any test coverage before this file -
this is the first test to exercise image_translate_cli/cli.py::main() at
all, not just a regression re-check of something already covered.

No real browser anywhere here - a background thread plays the human's
role, issuing the exact same GET/POST calls _PAGE_HTML's own JS makes
(GET /api/state, GET /api/image, POST /api/apply|/api/cancel) via
urllib.request - same "real HTTP calls, no mocking of the module under
test" style as tests/test_webapp_*.py.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

from image_translate_cli import cli as cli_module
from image_translate_cli import review_server
from pipeline.images.inpainting import TextReplacement
from pipeline.images.ocr import OcrTextRegion


def _replacement(text: str, x: int = 10, y: int = 10) -> TextReplacement:
    region = OcrTextRegion(text=text, x=x, y=y, width=80, height=20, confidence=90.0)
    return TextReplacement(region=region, translated_text=f"{text} [DE]")


def _build_image(path: Path) -> None:
    Image.new("RGB", (200, 100), "white").save(path)


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def _post_json(url: str, body: object) -> dict:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


# --- start_review_server() / ReviewSession (the non-blocking half) ------


def test_start_review_server_returns_immediately_and_serves_state_and_image(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_image(source)
    replacements = [_replacement("Hello")]

    session = review_server.start_review_server(str(source), replacements)
    try:
        assert session.url.startswith("http://127.0.0.1:")
        state = _get_json(session.url + "api/state")
        assert len(state["regions"]) == 1
        assert state["regions"][0]["translated_text"] == "Hello [DE]"

        with urllib.request.urlopen(session.url + "api/image", timeout=5) as response:
            image_bytes = response.read()
        assert image_bytes == source.read_bytes()
    finally:
        # Never applied/cancelled in this test - shut the server down
        # directly rather than via .wait(), which would otherwise block
        # for the default 1800s timeout.
        session.server.shutdown()
        session.server.server_close()


def test_review_session_wait_returns_apply_outcome_from_a_real_http_post(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])

    edited_region = {
        "x": 15, "y": 12, "width": 90, "height": 22,
        "translated_text": "Hallo (bearbeitet)",
        "original_text": "Hello", "confidence": 90.0,
    }

    def _act_like_the_browser() -> None:
        time.sleep(0.1)
        result = _post_json(session.url + "api/apply", [edited_region])
        assert result["ok"] is True

    threading.Thread(target=_act_like_the_browser).start()
    outcome, edited = session.wait(timeout_seconds=5.0)

    assert outcome == "apply"
    assert edited is not None
    assert len(edited) == 1
    assert edited[0].translated_text == "Hallo (bearbeitet)"
    assert edited[0].region.x == 15


def test_review_session_wait_keeps_the_original_region_when_the_browser_moved_the_box(
    tmp_path: Path,
) -> None:
    """26.08.2026 regression guard - real user report, Backlog.md
    26.08.2026: "die Positionen, Grösse und Korrekturen werden nicht
    übernommen". review_server.py's browser page now sends BOTH the
    current (possibly dragged/resized) x/y/width/height AND the
    unchanged orig_x/orig_y/orig_width/orig_height (see collectRegions()'s
    own comment) - `edited[0].region` must come back as the ORIGINAL
    position (what InpaintingBackend.apply() erases), and
    `edited[0].render_box` as the moved-to position (where it draws)."""
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello", x=10, y=10)])

    moved_region = {
        "x": 90, "y": 70, "width": 60, "height": 25,  # where the box was dragged to
        "orig_x": 10, "orig_y": 10, "orig_width": 80, "orig_height": 20,  # unchanged original
        "translated_text": "Hallo (verschoben)",
        "original_text": "Hello", "confidence": 90.0,
    }

    def _act_like_the_browser() -> None:
        time.sleep(0.1)
        result = _post_json(session.url + "api/apply", [moved_region])
        assert result["ok"] is True

    threading.Thread(target=_act_like_the_browser).start()
    outcome, edited = session.wait(timeout_seconds=5.0)

    assert outcome == "apply"
    assert edited is not None
    replacement = edited[0]
    assert (replacement.region.x, replacement.region.y, replacement.region.width, replacement.region.height) == (
        10, 10, 80, 20,
    )
    assert replacement.render_box is not None
    render_box = replacement.render_box
    assert (render_box.x, render_box.y, render_box.width, render_box.height) == (90, 70, 60, 25)
    assert replacement.translated_text == "Hallo (verschoben)"


def test_review_session_wait_returns_cancel_outcome(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])

    def _act_like_the_browser() -> None:
        time.sleep(0.1)
        result = _post_json(session.url + "api/cancel", {})
        assert result["ok"] is True

    threading.Thread(target=_act_like_the_browser).start()
    outcome, edited = session.wait(timeout_seconds=5.0)

    assert outcome == "cancel"
    assert edited is None


def test_start_review_server_state_reflects_an_already_corrected_replacement(tmp_path: Path) -> None:
    """26.08.2026: opening a SECOND review round on an already-corrected
    replacement (one whose `render_box` a prior round already set) must
    show the box at its CURRENT (corrected) position - not silently snap
    back to the original OCR position - while still keeping the TRUE
    original around (as orig_x/y/width/height) for THIS round's own
    erase step, should the human move it yet again. See report.py::
    regions_from_replacements()'s matching docstring."""
    from pipeline.images.ocr import OcrTextRegion

    source = tmp_path / "photo.png"
    _build_image(source)
    original_region = OcrTextRegion(text="Hello", x=10, y=10, width=80, height=20, confidence=90.0)
    already_corrected_box = OcrTextRegion(text="Hello", x=90, y=70, width=60, height=25, confidence=90.0)
    replacement = TextReplacement(
        region=original_region, translated_text="Hallo (verschoben)", render_box=already_corrected_box
    )

    session = review_server.start_review_server(str(source), [replacement])
    try:
        state = _get_json(session.url + "api/state")
        record = state["regions"][0]
        # The box must render at its CURRENT (corrected) position...
        assert (record["x"], record["y"], record["width"], record["height"]) == (90, 70, 60, 25)
        # ...while the TRUE original is still available separately.
        assert (record["orig_x"], record["orig_y"], record["orig_width"], record["orig_height"]) == (
            10, 10, 80, 20,
        )
        assert record["font_size_px"] > 0
    finally:
        session.server.shutdown()
        session.server.server_close()


def test_review_session_wait_times_out_without_any_action(tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])

    outcome, edited = session.wait(timeout_seconds=0.2)

    assert outcome == "timeout"
    assert edited is None


# --- run_review_session() (the thin, unchanged-signature wrapper) -------


def test_run_review_session_wrapper_still_behaves_like_before_the_split(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cli.py::_cmd_review() calls run_review_session() with the exact
    same signature it always had - proves the Schritt-8 split (inline
    bind+block -> start_review_server() + ReviewSession.wait()) didn't
    change that: the URL is still handed to webbrowser.open() (when
    open_browser=True), the call still blocks until an action, and the
    returned (outcome, replacements) shape is unchanged.
    """
    source = tmp_path / "photo.png"
    _build_image(source)
    replacements = [_replacement("Hello")]

    real_start = review_server.start_review_server
    captured: list[review_server.ReviewSession] = []

    def _capturing_start(*args: object, **kwargs: object) -> review_server.ReviewSession:
        session = real_start(*args, **kwargs)  # type: ignore[arg-type]
        captured.append(session)
        return session

    monkeypatch.setattr(review_server, "start_review_server", _capturing_start)
    opened_urls: list[str] = []
    monkeypatch.setattr(review_server.webbrowser, "open", lambda url: opened_urls.append(url))

    result_holder: dict[str, object] = {}

    def _run() -> None:
        outcome, edited = review_server.run_review_session(
            str(source), replacements, open_browser=True, timeout_seconds=5.0
        )
        result_holder["outcome"] = outcome
        result_holder["edited"] = edited

    thread = threading.Thread(target=_run)
    thread.start()

    deadline = time.monotonic() + 5.0
    while not captured and time.monotonic() < deadline:
        time.sleep(0.02)
    assert captured, "start_review_server() was not called by run_review_session()"
    session = captured[0]

    result = _post_json(
        session.url + "api/apply",
        [{"x": 1, "y": 1, "width": 10, "height": 10, "translated_text": "Hallo"}],
    )
    assert result["ok"] is True

    thread.join(timeout=5.0)
    assert result_holder["outcome"] == "apply"
    assert result_holder["edited"][0].translated_text == "Hallo"  # type: ignore[index]
    assert opened_urls == [session.url]


# --- _cmd_review() / `image_translate_cli review` end to end ------------


def test_cli_review_command_applies_and_writes_the_corrected_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First test exercising image_translate_cli/cli.py::main() at all -
    proves the whole `review` subcommand (argument parsing, run_review_
    session() wiring, InpaintingBackend.apply(), report output) still
    works end to end after the Schritt-8 split, not just review_server.py
    in isolation.
    """
    source = tmp_path / "photo.png"
    _build_image(source)
    destination = tmp_path / "photo_translated.png"
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(
        json.dumps([{"x": 10, "y": 10, "width": 80, "height": 20, "translated_text": "Hallo"}]),
        encoding="utf-8",
    )

    captured: list[review_server.ReviewSession] = []
    real_start = review_server.start_review_server

    def _capturing_start(*args: object, **kwargs: object) -> review_server.ReviewSession:
        session = real_start(*args, **kwargs)  # type: ignore[arg-type]
        captured.append(session)
        return session

    monkeypatch.setattr(review_server, "start_review_server", _capturing_start)

    exit_code_holder: dict[str, int] = {}

    def _run_cli() -> None:
        exit_code_holder["code"] = cli_module.main(
            [
                "review",
                "--source", str(source),
                "--regions", str(regions_file),
                "--output", str(destination),
                "--no-browser",
                "--timeout", "5",
            ]
        )

    thread = threading.Thread(target=_run_cli)
    thread.start()

    deadline = time.monotonic() + 5.0
    while not captured and time.monotonic() < deadline:
        time.sleep(0.02)
    assert captured, "review command never started a review server"

    result = _post_json(
        captured[0].url + "api/apply",
        [{"x": 10, "y": 10, "width": 80, "height": 20, "translated_text": "Hallo (korrigiert)"}],
    )
    assert result["ok"] is True

    thread.join(timeout=5.0)
    assert exit_code_holder["code"] == 0
    assert destination.is_file()
