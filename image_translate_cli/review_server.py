"""Browser-based correction UI for image_translate_cli's `review` command
(see CLI.md's "review" section and cli.py::_cmd_review()).

Background (22.08.2026, Michael): `correct` (see cli.py/regions_io.py)
already lets any calling app re-render an image from an edited regions
list, but each app still had to build its OWN editing UI to produce that
list - "muss jede App das gleiche nochmal bauen". `review` closes that
gap by shipping the editing UI itself, inside the CLI, instead of leaving
it to every caller:

    1. This module starts a plain stdlib HTTP server bound to 127.0.0.1
       (LOCAL ONLY - no auth, not meant to be reachable over a network;
       see CLI.md's "review" section for why that's fine for now, and
       what would need to change if a caller ever ran this cross-machine).
    2. It serves one self-contained HTML/CSS/JS page (_PAGE_HTML below,
       no external assets, no CDN, no build step) that shows the PRISTINE
       source image with each region's translated text overlaid in an
       editable, draggable, resizable box - a live approximation of the
       final re-rendered result.
    3. A human edits text/geometry in the browser and clicks "Anwenden"
       (POSTs the edited region list to /api/apply) or "Abbrechen"
       (POSTs to /api/cancel). Whichever happens first ends the session -
       this module returns control to cli.py, which does the actual
       re-render via the SAME InpaintingBackend.apply() path `correct`
       uses (this module never touches inpainting itself).

Deliberately NOT: adding/removing regions (mirrors `correct`'s existing
"Bekannte Grenzen" - the region SET is fixed, only text/geometry per
region is editable - see CLI.md), a live re-rendered preview (would mean
re-running InpaintingBackend.apply() on every keystroke; the overlay is a
close-enough approximation without that cost), or anything reachable
without an explicit browser open on the same machine (no bundled auth -
see this module's own module docstring above and CLI.md).
"""
from __future__ import annotations

import http.server
import json
import mimetypes
import sys
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from pipeline.images.inpainting import TextReplacement

from image_translate_cli.regions_io import RegionsError, replacements_from_region_list
from image_translate_cli.report import regions_from_replacements

# Kept extremely small and dependency-free on purpose: no React/build step,
# just enough vanilla JS for drag/resize/edit - see this module's docstring
# for what's deliberately out of scope. Pointer Events (not mouse-only
# events) so this also works via touch on a tablet, not just a mouse -
# relevant to the iPad question in Backlog.md's Deployment-Idee entry,
# even though that's a separate decision from this command itself.
_PAGE_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Bildkorrektur</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #1e1e1e; color: #eee; }
  header {
    position: sticky; top: 0; z-index: 10;
    display: flex; align-items: center; gap: 12px;
    padding: 10px 16px; background: #262626; border-bottom: 1px solid #3a3a3a;
  }
  header h1 { font-size: 15px; font-weight: 600; margin: 0; flex: 0 0 auto; }
  #status { flex: 1 1 auto; font-size: 13px; color: #aaa; }
  button {
    font-size: 14px; padding: 7px 14px; border-radius: 6px; border: 1px solid transparent;
    cursor: pointer;
  }
  #apply-btn { background: #3b82f6; color: white; }
  #apply-btn:disabled, #cancel-btn:disabled { opacity: 0.5; cursor: default; }
  #cancel-btn { background: #333; color: #eee; border-color: #444; }
  main { padding: 24px; overflow: auto; }
  #stage { position: relative; background: #000; }
  #stage img { display: block; max-width: none; }
  .region {
    position: absolute; box-sizing: border-box;
    border: 1.5px dashed #3b82f6; background: rgba(20, 20, 20, 0.72);
    cursor: move; touch-action: none;
  }
  .region-text {
    width: 100%; height: 100%; box-sizing: border-box; padding: 2px 4px;
    /* 13px is only the FALLBACK now (26.08.2026) - renderRegions() below
       sets an inline font-size per box from the region's own
       font_size_px (see estimated_font_size()'s docstring: the same
       heuristic size InpaintingBackend.apply() actually renders with),
       real user report Backlog.md 26.08.2026: "Aber es fehlt noch die
       Font Erkennung ... Wenigstens in etwas die Fontgrössen. Annähernd,
       nicht genau." A flat 13px regardless of the real region size was
       part of why the correction view looked disconnected from the
       actual output. */
    color: #fff; font-size: 13px; line-height: 1.25; overflow: hidden;
    cursor: text; outline: none; touch-action: none;
    /* 27.08.2026 - a literal "\\n" (see the keydown handler in
       renderRegions() below) needs this to actually show as a line
       break; the default `normal` collapses it to a space like any
       other whitespace, silently hiding the very break the user just
       typed. */
    white-space: pre-wrap;
  }
  .resize-handle {
    position: absolute; right: -5px; bottom: -5px; width: 12px; height: 12px;
    background: #3b82f6; border: 1px solid #1e1e1e; border-radius: 2px;
    cursor: nwse-resize; touch-action: none;
  }
  .hint { font-size: 12px; color: #888; padding: 0 16px 12px; }
</style>
</head>
<body>
<header>
  <h1>Bildkorrektur</h1>
  <span id="status">Lade ...</span>
  <button id="cancel-btn">Abbrechen</button>
  <button id="apply-btn">Anwenden</button>
</header>
<p class="hint">Box ziehen zum Verschieben, Ecke unten rechts zum Skalieren, Text anklicken zum Bearbeiten. Maus-Titel (Hover) zeigt den erkannten Originaltext.</p>
<main><div id="stage"><img id="bg" alt="Quellbild"></div></main>
<script>
let regionsData = [];

function setStatus(msg) { document.getElementById('status').textContent = msg; }

async function init() {
  try {
    const stateResp = await fetch('/api/state');
    const state = await stateResp.json();
    regionsData = state.regions;
  } catch (e) {
    setStatus('Fehler beim Laden: ' + e);
    return;
  }
  const img = document.getElementById('bg');
  img.onload = () => {
    document.getElementById('stage').style.width = img.naturalWidth + 'px';
    document.getElementById('stage').style.height = img.naturalHeight + 'px';
    renderRegions();
    setStatus(regionsData.length + ' Region(en) geladen.');
  };
  img.onerror = () => setStatus('Bild konnte nicht geladen werden.');
  img.src = '/api/image';
}

// Mirrors pipeline.images.inpainting.py's own constants (27.08.2026) -
// see refitText() below for why.
const _FIT_MIN_SIZE = 9;
const _FIT_LINE_SPACING = 1.15;
let _measureCanvas = null;

function _measureCtx(fontPx) {
  if (!_measureCanvas) _measureCanvas = document.createElement('canvas');
  const ctx = _measureCanvas.getContext('2d');
  ctx.font = fontPx + 'px system-ui, sans-serif';
  return ctx;
}

// Mirrors pipeline.images.inpainting.py's _wrap_text_to_width() - same
// greedy word-wrap, same "\\n" forced-break handling (see that function's
// own 27.08.2026 comment) - kept as a literal port rather than shared
// code since this page has no build step to import Python from (see this
// module's own docstring on why it stays vanilla JS).
function _wrapForWidth(ctx, text, maxWidth) {
  const lines = [];
  text.split('\\n').forEach((segment) => {
    const words = segment.split(/\\s+/).filter(Boolean);
    if (!words.length) { lines.push(''); return; }
    let current = words[0];
    for (let i = 1; i < words.length; i++) {
      const candidate = current + ' ' + words[i];
      if (maxWidth <= 0 || ctx.measureText(candidate).width <= maxWidth) {
        current = candidate;
      } else {
        lines.push(current);
        current = words[i];
      }
    }
    lines.push(current);
  });
  return lines.length ? lines : [''];
}

// 27.08.2026 - real user report, Backlog.md 27.08.2026: "Hier sieht man
// schon verschiedene Boxen und Textgrössen. Schon hier gibt es
// Unterschiede die nicht sein sollten." Root cause: this box's displayed
// font-size (r.font_size_px, see renderRegions() below) was always just
// estimated_font_size()'s HEIGHT-only heuristic, applied with no regard
// for whether the text actually fits the box's WIDTH - the real renderer
// (inpainting.py's _fit_text()) shrinks further whenever it doesn't, so
// a long word/line could show here uncropped-looking (or, worse, visibly
// clipped by .region-text's own `overflow: hidden`) while rendering
// noticeably smaller in the real output. refitText() below runs the SAME
// shrink loop client-side - shrink only, deliberately: the real
// renderer's further "widen into a neighbouring region's free space" step
// depends on every OTHER region's position too, data this page never
// receives, so that part remains an approximation exactly like
// r.font_size_px already was before this change (see its own comment) -
// this just also accounts for the box's own width, closing the gap the
// user actually reported.
function refitText(box, text) {
  const maxWidth = Math.max(parseInt(box.style.width, 10) - 8, 1);
  const maxHeight = Math.max(parseInt(box.style.height, 10) - 4, 1);
  const base = parseInt(text.dataset.baseFontSize, 10) || 13;
  // textWithLineBreaks(), not plain .textContent - see collectRegions()'s
  // own comment: a break the user just typed lives as a <div>/<br>
  // boundary until Anwenden serializes it, and the live preview needs to
  // account for it exactly the same way or it drifts from what
  // Anwenden actually sends.
  const content = textWithLineBreaks(text) || '';
  let size = base;
  while (true) {
    const ctx = _measureCtx(size);
    const lines = _wrapForWidth(ctx, content, maxWidth);
    const lineHeight = Math.max(1, Math.floor(size * _FIT_LINE_SPACING));
    const totalHeight = lineHeight * lines.length;
    const widest = lines.reduce((m, l) => Math.max(m, ctx.measureText(l).width), 0);
    if ((totalHeight <= maxHeight && widest <= maxWidth) || size <= _FIT_MIN_SIZE) break;
    size = Math.max(_FIT_MIN_SIZE, size - 2);
  }
  text.style.fontSize = size + 'px';
  text.style.lineHeight = String(_FIT_LINE_SPACING);
}

function renderRegions() {
  const stage = document.getElementById('stage');
  regionsData.forEach((r) => {
    const box = document.createElement('div');
    box.className = 'region';
    box.style.left = r.x + 'px';
    box.style.top = r.y + 'px';
    box.style.width = r.width + 'px';
    box.style.height = r.height + 'px';
    box.dataset.originalText = r.original_text;
    box.dataset.confidence = r.confidence;
    // TRUE original OCR position (26.08.2026) - kept SEPARATE from the
    // box's own (possibly already corrected, on a second review round)
    // current style.left/top/width/height, so a drag/resize here never
    // loses track of where the untranslated source text really sits.
    // r.orig_x is only present when a PRIOR correction round already
    // moved this region (see report.py::RegionRecord.to_dict()) - falls
    // back to r.x itself (this position IS still the original) the very
    // first time a region gets corrected, same fallback
    // regions_io.py::replacements_from_region_list() applies on the way
    // back in.
    box.dataset.origX = r.orig_x !== undefined ? r.orig_x : r.x;
    box.dataset.origY = r.orig_y !== undefined ? r.orig_y : r.y;
    box.dataset.origWidth = r.orig_width !== undefined ? r.orig_width : r.width;
    box.dataset.origHeight = r.orig_height !== undefined ? r.orig_height : r.height;
    box.title = 'Original: ' + r.original_text;

    const text = document.createElement('div');
    text.className = 'region-text';
    text.contentEditable = 'true';
    text.textContent = r.translated_text;
    // Approximates the real render (26.08.2026, see .region-text's own
    // CSS comment above) - r.font_size_px is absent only for a
    // hand-written --regions file loaded via `correct` that never went
    // through report.py's regions_from_replacements(), never for
    // anything `review` itself produces; falls back to the CSS default.
    text.dataset.baseFontSize = r.font_size_px || 13;
    // 27.08.2026 - real user report, Backlog.md 27.08.2026: "einen
    // Zeilenumbruch sollte mit übernommen werden".
    //
    // Three attempts before this one, all abandoned after being
    // reproduced BROKEN with a real (Playwright-driven) Chromium, not
    // just eyeballed - see repro_linebreak.py, kept in the repo because
    // this class of bug does not show up from reading the code, only
    // from actually typing into it: (1) intercepting Enter and inserting
    // a lone "\\n" text node via Range.insertNode() - the browser's own
    // native typing for the NEXT character then landed BEFORE that node
    // instead of after it, so the "\\n" silently migrated to the end of
    // the string. (2) document.execCommand('insertText', false, '\\n')
    // - inserted nothing at all. (3) splicing '\\n' directly into the
    // existing text node's own data at the caret offset - same failure
    // as (1): Chromium's caret-after-a-trailing-"\\n" is apparently not
    // a stable insertion point for its own subsequent typing, no matter
    // how the "\\n" got there.
    //
    // Given three straight failures at intercepting Enter and hand-
    // placing a raw "\\n" character, this version does the opposite:
    // Enter is left COMPLETELY alone, so the browser's own (very
    // reliable) native contentEditable editing handles typing and caret
    // placement exactly as it always does - which means a plain Enter
    // press produces a new <div> (Chromium's own default), not a "\\n"
    // character. The line break only gets reconstructed as a "\\n"
    // afterwards, when reading the box back out - see
    // textWithLineBreaks() below, used by collectRegions() instead of
    // plain .textContent. Confirmed via the same Playwright repro: the
    // typed text and the break both land exactly where expected, every
    // time, because nothing here ever fights the browser's own caret.
    text.addEventListener('input', () => refitText(box, text));
    box.appendChild(text);

    const handle = document.createElement('div');
    handle.className = 'resize-handle';
    box.appendChild(handle);

    makeDraggable(box, text, handle);
    makeResizable(box, handle);

    refitText(box, text);
    stage.appendChild(box);
  });
}

function makeDraggable(box, textEl, handle) {
  // 26.08.2026 regression fix - real user report, Backlog.md 26.08.2026:
  // "die Positionen, Grösse und Korrekturen werden nicht übernommen".
  // `textEl` (.region-text) is styled width/height 100% of `box` (see
  // its own CSS) - it visually covers the ENTIRE box, so a pointerdown
  // ANYWHERE inside the visible box always had e.target === textEl. The
  // old code (`if (e.target === textEl ...) return;`) therefore bailed
  // out of EVERY drag attempt that started on the visible box - only a
  // pointerdown on the ~1.5px dashed border itself (practically
  // unclickable with a mouse) could ever start one. Confirmed via a real
  // Chromium session driving actual pointer events, not just reading the
  // code: a simulated drag starting on the box left `box.style.left`
  // completely unchanged.
  //
  // Fix: allow a drag to start from anywhere on the box (including over
  // the text), but only actually begin MOVING it once the pointer has
  // travelled past `DRAG_THRESHOLD` px - a plain click (no/negligible
  // movement) still reaches `textEl` as a normal click, so clicking into
  // the text to position the edit cursor keeps working exactly as
  // before. `e.preventDefault()` only fires once real dragging starts,
  // so it never blocks the plain-click case from placing a cursor.
  const DRAG_THRESHOLD = 4;
  let dragging = false, moved = false, startX = 0, startY = 0, startLeft = 0, startTop = 0;
  box.addEventListener('pointerdown', (e) => {
    if (e.target === handle) return;
    dragging = true;
    moved = false;
    startX = e.clientX; startY = e.clientY;
    startLeft = parseInt(box.style.left, 10);
    startTop = parseInt(box.style.top, 10);
    box.setPointerCapture(e.pointerId);
  });
  box.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX, dy = e.clientY - startY;
    if (!moved) {
      if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      moved = true;
      // Only suppress the native click/selection behavior once this is
      // genuinely a drag - keeps a plain click on the text free to place
      // an edit cursor as usual.
      e.preventDefault();
      const selection = window.getSelection();
      if (selection) selection.removeAllRanges();
    }
    box.style.left = (startLeft + dx) + 'px';
    box.style.top = (startTop + dy) + 'px';
  });
  box.addEventListener('pointerup', () => { dragging = false; });
}

function makeResizable(box, handle) {
  let resizing = false, startX = 0, startY = 0, startW = 0, startH = 0;
  handle.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    resizing = true;
    startX = e.clientX; startY = e.clientY;
    startW = parseInt(box.style.width, 10);
    startH = parseInt(box.style.height, 10);
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener('pointermove', (e) => {
    if (!resizing) return;
    box.style.width = Math.max(8, startW + e.clientX - startX) + 'px';
    box.style.height = Math.max(8, startH + e.clientY - startY) + 'px';
    // 27.08.2026 - see refitText()'s own comment: a resize changes the
    // very box width/height that preview font-size now depends on, so it
    // has to re-run live, not just once at initial load.
    const textEl = box.querySelector('.region-text');
    if (textEl) refitText(box, textEl);
  });
  handle.addEventListener('pointerup', () => { resizing = false; });
}

// 27.08.2026 - see renderRegions()'s own comment on why Enter is left
// alone rather than intercepted: a plain Enter inside `.region-text`
// produces Chromium's own default split, a new <div> (occasionally a
// <br> for a shift-Enter-like case) - never a literal "\\n" character.
// This walks the box's actual DOM instead of reading .textContent
// (which would just concatenate every block's text with nothing
// between them, losing the break entirely) and reconstructs exactly
// ONE "\\n" per block boundary / <br>, so pipeline.images.inpainting.py's
// _wrap_text_to_width() (see its own 27.08.2026 comment) sees the same
// forced break the user actually typed. A literal "\\n" already present
// in a text node (round-tripping a PRIOR correction round's break, see
// renderRegions() setting text.textContent = r.translated_text above)
// passes straight through unchanged - this only ADDS breaks for
// DOM-level block boundaries, never removes one already in the text.
function textWithLineBreaks(el) {
  let out = '';
  function walk(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      out += node.textContent;
      return;
    }
    if (node.nodeName === 'BR') {
      out += '\\n';
      return;
    }
    const isBlock = node.nodeName === 'DIV' || node.nodeName === 'P';
    if (isBlock && out.length > 0 && !out.endsWith('\\n')) {
      out += '\\n';
    }
    node.childNodes.forEach(walk);
  }
  el.childNodes.forEach(walk);
  return out;
}

function collectRegions() {
  const boxes = document.querySelectorAll('.region');
  const out = [];
  boxes.forEach((box) => {
    const text = box.querySelector('.region-text');
    out.push({
      x: parseInt(box.style.left, 10),
      y: parseInt(box.style.top, 10),
      width: parseInt(box.style.width, 10),
      height: parseInt(box.style.height, 10),
      // Always sent back too (26.08.2026), UNCHANGED by drag/resize -
      // see renderRegions()'s matching comment. Lets the backend erase
      // the real original spot even when x/y/width/height above now
      // point somewhere else entirely.
      orig_x: parseInt(box.dataset.origX, 10),
      orig_y: parseInt(box.dataset.origY, 10),
      orig_width: parseInt(box.dataset.origWidth, 10),
      orig_height: parseInt(box.dataset.origHeight, 10),
      translated_text: textWithLineBreaks(text),
      original_text: box.dataset.originalText,
      confidence: parseFloat(box.dataset.confidence),
    });
  });
  return out;
}

async function apply() {
  setStatus('Wird angewendet ...');
  let resp, data;
  try {
    resp = await fetch('/api/apply', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(collectRegions()),
    });
    data = await resp.json();
  } catch (e) {
    setStatus('Fehler: ' + e);
    return;
  }
  if (data.ok) {
    setStatus('Angewendet - dieser Tab kann geschlossen werden.');
    document.getElementById('apply-btn').disabled = true;
    document.getElementById('cancel-btn').disabled = true;
  } else {
    setStatus('Fehler: ' + data.error);
  }
}

async function cancelReview() {
  document.getElementById('apply-btn').disabled = true;
  document.getElementById('cancel-btn').disabled = true;
  setStatus('Abgebrochen - dieser Tab kann geschlossen werden.');
  try { await fetch('/api/cancel', {method: 'POST'}); } catch (e) { /* egal, Server beendet sich ohnehin */ }
}

document.getElementById('apply-btn').addEventListener('click', apply);
document.getElementById('cancel-btn').addEventListener('click', cancelReview);
init();
</script>
</body>
</html>
"""


@dataclass
class ReviewSession:
    """A review server that has been bound and started (see
    start_review_server()) but not yet waited on - handed back to the
    caller immediately, `server.server_address` already valid, so a
    non-blocking caller (webapp/review_bridge.py, Schritt 8 of the local-
    server + pywebview migration, see Backlog.md 26.08.2026) can read
    `.url` and hand it to a browser tab/window without blocking the
    thread that started the session. `.wait()` is the blocking half that
    `run_review_session()` below always ran inline - split out so a
    caller can run `.wait()` on ITS OWN background thread instead.
    """

    server: http.server.ThreadingHTTPServer
    url: str
    _done: threading.Event
    _state: dict[str, object]

    def wait(self, timeout_seconds: float | None = 1800.0) -> tuple[str, list[TextReplacement] | None]:
        """Blocks until the human applies/cancels (or `timeout_seconds`
        elapses - 0/None disables the timeout), then shuts the server down
        and returns the outcome, exactly as run_review_session() always
        did:

            ("apply", <edited replacements>)  - "Anwenden" was clicked.
            ("cancel", None)                  - "Abbrechen" was clicked.
            ("timeout", None)                 - neither happened in time.
        """
        finished_in_time = self._done.wait(timeout_seconds if timeout_seconds and timeout_seconds > 0 else None)
        self.server.shutdown()
        self.server.server_close()
        if not finished_in_time:
            return "timeout", None
        return str(self._state["outcome"]), self._state["replacements"]  # type: ignore[return-value]


def start_review_server(
    source_path: str,
    initial_replacements: list[TextReplacement],
    host: str = "127.0.0.1",
    port: int = 0,
) -> ReviewSession:
    """Bind and start the review server WITHOUT blocking - mirrors
    webapp/server.py::create_server()'s own "bind, don't block" split.
    Returns a ReviewSession whose `.url` is ready to hand to a browser
    immediately; call `.wait()` (on whatever thread should block - a CLI's
    main thread via run_review_session() below, or a background thread
    for an HTTP caller like webapp/review_bridge.py) to get the outcome.

    `port=0` (the default) lets the OS pick a free port - already resolved
    in `.url` by the time this function returns, no need to poll
    `server.server_address` separately.
    """
    initial_regions = [r.to_dict() for r in regions_from_replacements(initial_replacements)]
    state: dict[str, object] = {"outcome": None, "replacements": None}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # keep stdout/stderr limited to the CLI's own documented output

        def _send_json(self, obj: dict, status: int = 200) -> None:
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                body = _PAGE_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/state":
                self._send_json({"regions": initial_regions})
            elif self.path == "/api/image":
                try:
                    data = Path(source_path).read_bytes()
                except OSError as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=404)
                    return
                content_type = mimetypes.guess_type(source_path)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b""
            if self.path == "/api/apply":
                try:
                    payload = json.loads(raw.decode("utf-8")) if raw else []
                    replacements = replacements_from_region_list(payload)
                except (json.JSONDecodeError, UnicodeDecodeError, RegionsError) as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=400)
                    return
                state["outcome"] = "apply"
                state["replacements"] = replacements
                self._send_json({"ok": True})
                done.set()
            elif self.path == "/api/cancel":
                state["outcome"] = "cancel"
                self._send_json({"ok": True})
                done.set()
            else:
                self.send_response(404)
                self.end_headers()

    server = http.server.ThreadingHTTPServer((host, port), Handler)
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://{host}:{actual_port}/"
    return ReviewSession(server=server, url=url, _done=done, _state=state)


def run_review_session(
    source_path: str,
    initial_replacements: list[TextReplacement],
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    timeout_seconds: float = 1800.0,
) -> tuple[str, list[TextReplacement] | None]:
    """cli.py's `review` command entry point - unchanged in behavior and
    signature since before the Schritt 8 split above: start the review
    server, print/open its URL, block until the human applies/cancels (or
    `timeout_seconds` elapses), then return the outcome. A thin wrapper
    around start_review_server() + ReviewSession.wait() now instead of
    doing both inline - see start_review_server()'s own docstring for why
    the split exists (a non-blocking caller like webapp/review_bridge.py
    needs the URL before the human has acted, this function's own callers
    never did).
    """
    session = start_review_server(source_path, initial_replacements, host, port)
    print(f"Korrektur-Ansicht: {session.url}", file=sys.stdout, flush=True)
    if open_browser:
        try:
            webbrowser.open(session.url)
        except Exception:
            pass  # kein Browser verfügbar/konfiguriert - URL steht oben, Nutzer öffnet selbst
    return session.wait(timeout_seconds)
