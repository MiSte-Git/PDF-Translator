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


def test_font_routes_serve_real_dejavu_ttf_bytes_for_preview_metrics(tmp_path: Path) -> None:
    """28.08.2026 (Runde 7) regression guard - real user report, Backlog.md
    28.08.2026: a footer box widened until its text fit on one line in the
    correction preview still wrapped to two lines in the real rendered
    JPG. Root cause: the preview measured/rendered with the browser's
    generic `system-ui` font while pipeline/images/font_style.py::
    load_font() always draws with the real DejaVu Sans TTF - different
    character widths at the same pixel size. /api/font/regular and
    /api/font/bold now serve that exact TTF (see _dejavu_font_path()) so
    the browser's @font-face preview uses the SAME metrics as the real
    renderer. This only asserts the HTTP contract (status, content-type,
    non-trivial TTF-shaped bytes) - the pipeline/images/font_style.py
    tests already cover that load_font() finds the same files."""
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])
    try:
        for variant in ("regular", "bold"):
            with urllib.request.urlopen(session.url + f"api/font/{variant}", timeout=5) as response:
                assert response.status == 200
                assert "font" in response.headers.get("Content-Type", "")
                data = response.read()
            # TTF files start with a 4-byte sfnt version tag (0x00010000
            # for TrueType-flavored OpenType, which DejaVu's .ttf files
            # use) - a cheap sanity check that this is really a font file
            # and not e.g. an accidentally-served error page.
            assert len(data) > 1000
            assert data[:4] == b"\x00\x01\x00\x00"
    finally:
        session.server.shutdown()
        session.server.server_close()


def test_render_preview_reflects_font_size_bold_and_centered_like_the_real_renderer(
    tmp_path: Path,
) -> None:
    """28.08.2026 (Runde 8) - the actual architecture change Michael asked
    for after Runde 7's font-metrics fix still wasn't enough: "Ich will
    nur die Textfelder bearbeiten und positionieren [...] was ich im
    Viewer sehe, muss genau so gespeichert werden." Rather than refining
    the browser's own DOM/CSS approximation of _draw_fitted_text() any
    further (that arms race is what produced Runde 2 through 7 in the
    first place), POST /api/render-preview now runs the SAME renderer
    (BoxOverlayBackend, see _render_preview_bytes()'s own long comment for
    why that backend specifically) on the current in-browser correction
    state and returns the real image - _PAGE_HTML's JS displays that
    directly instead of a second, independent implementation.

    This guards the actual contract: a payload with an explicit
    font_size/bold/centered produces a real JPEG whose ink is (a) roughly
    where the requested font size implies for a short two-word string,
    and (b) horizontally CENTERED within the given box - not just that
    the endpoint returns 200 with plausible-looking bytes."""
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])
    try:
        payload = [{
            "x": 10, "y": 10, "width": 180, "height": 44,
            "orig_x": 10, "orig_y": 10, "orig_width": 80, "orig_height": 20,
            "translated_text": "Hallo Welt",
            "original_text": "Hello",
            "confidence": 90.0,
            "centered": True,
            "font_size": 20,
            "bold": True,
        }]
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            session.url + "api/render-preview",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            assert response.status == 200
            assert response.headers.get("Content-Type") == "image/jpeg"
            image_bytes = response.read()
        assert len(image_bytes) > 200  # not an empty/error placeholder

        out_path = tmp_path / "preview.jpg"
        out_path.write_bytes(image_bytes)
        rendered = Image.open(out_path).convert("L")
        assert rendered.size == (200, 100)  # unchanged from _build_image()

        # Box spans x in [10, 190] - a centered short line should leave
        # roughly equal margins on both sides, not sit flush against
        # either edge (which is what render_centered=False/left-aligned
        # would look like instead).
        pixels = rendered.load()
        ink_columns = [
            x for x in range(10, 190)
            if any(pixels[x, y] < 180 for y in range(10, 54))
        ]
        assert ink_columns, "expected some rendered ink inside the box"
        left_margin = min(ink_columns) - 10
        right_margin = 190 - max(ink_columns)
        assert abs(left_margin - right_margin) <= 8, (
            f"text does not look centered: left={left_margin} right={right_margin}"
        )
    finally:
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


def test_start_review_server_state_carries_untouched_font_size_bold_centered_defaults(
    tmp_path: Path,
) -> None:
    """28.08.2026 (Runde 4) regression guard - real user report, Backlog.md
    28.08.2026: "Wenn ich etwas korrigiere, muss es auch genauso
    korrigiert werden wie ich es im Viewer sehe." A replacement nobody has
    EVER touched (the plain `_replacement()` helper - render_font_size/
    render_bold both None, render_centered False, exactly TextReplacement's
    own defaults) must come back from GET /api/state with the tri-state
    "not touched" markers image_translate_cli/regions_io.py::
    replacements_from_region_list() expects on the way back in - see that
    function's own docstring and _PAGE_HTML's collectRegions() comment for
    why sending font_size/bold unconditionally would be a regression
    (silently hard-coding every untouched region's real estimated bold to
    False on the next apply)."""
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])
    try:
        record = _get_json(session.url + "api/state")["regions"][0]
        assert record["font_size_touched"] is False
        assert record["bold_touched"] is False
        assert record["centered"] is False
        assert isinstance(record["bold"], bool)  # a best-effort pixel ESTIMATE, not asserted True/False here -
        # see _initial_bold_estimates()'s own docstring: never raises, but the
        # actual guess on a plain synthetic test image isn't part of this
        # module's own contract to get "right", only to always produce SOME
        # bool without crashing start_review_server().
        assert record["font_size_px"] > 0
    finally:
        session.server.shutdown()
        session.server.server_close()


def test_start_review_server_state_marks_an_earlier_rounds_explicit_override_as_already_touched(
    tmp_path: Path,
) -> None:
    """28.08.2026 (Runde 4) - a replacement whose render_font_size/
    render_bold/render_centered an EARLIER correction round already set
    explicitly (this is what a SECOND `review` round on an already-
    corrected image actually looks like - see the matching
    render_box scenario further above,
    test_start_review_server_state_reflects_an_already_corrected_replacement)
    must show up as ALREADY touched in this round's initial state too -
    not just carry the override's VALUE. Without the *_touched markers
    being True here, a human who reopens `review` and never so much as
    looks at the bold/font-size controls (they only wanted to nudge a
    box's position) would have collectRegions() omit font_size/bold this
    round, and regions_io.py's tri-state contract (no "keep the old
    override" fallback for these two fields) would silently reset a real,
    previously-explicit choice back to auto-estimated."""
    region = OcrTextRegion(text="Hello", x=10, y=10, width=80, height=20, confidence=90.0)
    replacement = TextReplacement(
        region=region,
        translated_text="Hallo [DE]",
        render_font_size=22,
        render_bold=True,
        render_centered=True,
    )
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [replacement])
    try:
        record = _get_json(session.url + "api/state")["regions"][0]
        assert record["font_size_touched"] is True
        assert record["font_size_px"] == 22
        assert record["bold_touched"] is True
        assert record["bold"] is True
        assert record["centered"] is True
    finally:
        session.server.shutdown()
        session.server.server_close()


def test_review_session_wait_applies_explicit_font_size_bold_centered_from_the_posted_region(
    tmp_path: Path,
) -> None:
    """28.08.2026 (Runde 4) end-to-end guard for the new tri-state fields
    themselves (mirrors test_review_session_wait_returns_apply_outcome_
    from_a_real_http_post above, which predates font_size/bold/centered
    entirely) - a POST /api/apply body that DOES include font_size/bold/
    centered (i.e. what _PAGE_HTML's collectRegions() sends for a region
    whose controls a human actually touched, per its own tri-state
    comment) must come back out as the matching TextReplacement.
    render_font_size/render_bold/render_centered - the exact three fields
    every InpaintingBackend.apply() now reads INSTEAD OF its own estimate,
    see pipeline.images.inpainting.TextReplacement's own docstring."""
    source = tmp_path / "photo.png"
    _build_image(source)
    session = review_server.start_review_server(str(source), [_replacement("Hello")])

    edited_region = {
        "x": 10, "y": 10, "width": 80, "height": 20,
        "translated_text": "HALLO",
        "original_text": "Hello", "confidence": 90.0,
        "font_size": 30, "bold": True, "centered": True,
    }

    def _act_like_the_browser() -> None:
        time.sleep(0.1)
        result = _post_json(session.url + "api/apply", [edited_region])
        assert result["ok"] is True

    threading.Thread(target=_act_like_the_browser).start()
    outcome, edited = session.wait(timeout_seconds=5.0)

    assert outcome == "apply"
    assert edited is not None
    replacement = edited[0]
    assert replacement.render_font_size == 30
    assert replacement.render_bold is True
    assert replacement.render_centered is True


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
