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
    color: #fff; font-size: 13px; line-height: 1.25; overflow: hidden;
    cursor: text; outline: none; touch-action: none;
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
    box.title = 'Original: ' + r.original_text;

    const text = document.createElement('div');
    text.className = 'region-text';
    text.contentEditable = 'true';
    text.textContent = r.translated_text;
    box.appendChild(text);

    const handle = document.createElement('div');
    handle.className = 'resize-handle';
    box.appendChild(handle);

    makeDraggable(box, text, handle);
    makeResizable(box, handle);

    stage.appendChild(box);
  });
}

function makeDraggable(box, textEl, handle) {
  let dragging = false, startX = 0, startY = 0, startLeft = 0, startTop = 0;
  box.addEventListener('pointerdown', (e) => {
    if (e.target === textEl || e.target === handle) return;
    dragging = true;
    startX = e.clientX; startY = e.clientY;
    startLeft = parseInt(box.style.left, 10);
    startTop = parseInt(box.style.top, 10);
    box.setPointerCapture(e.pointerId);
  });
  box.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    box.style.left = (startLeft + e.clientX - startX) + 'px';
    box.style.top = (startTop + e.clientY - startY) + 'px';
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
  });
  handle.addEventListener('pointerup', () => { resizing = false; });
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
      translated_text: text.textContent,
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


def run_review_session(
    source_path: str,
    initial_replacements: list[TextReplacement],
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = True,
    timeout_seconds: float = 1800.0,
) -> tuple[str, list[TextReplacement] | None]:
    """Start the review server, block until the human applies/cancels (or
    `timeout_seconds` elapses - 0/None disables the timeout), then shut the
    server down and return the outcome:

        ("apply", <edited replacements>)  - "Anwenden" was clicked;
                                             cli.py re-renders from this.
        ("cancel", None)                  - "Abbrechen" was clicked.
        ("timeout", None)                 - neither happened in time.

    `port=0` (the default) lets the OS pick a free port, printed to stdout
    as part of the URL before this function blocks - a caller scripting
    this (rather than a human watching stdout) can still discover it that
    way, though `--port` (see cli.py's `review` subparser) lets a caller
    pin a fixed port instead if that's more convenient to wire up.
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
    print(f"Korrektur-Ansicht: {url}", file=sys.stdout, flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass  # kein Browser verfügbar/konfiguriert - URL steht oben, Nutzer öffnet selbst

    finished_in_time = done.wait(timeout_seconds if timeout_seconds and timeout_seconds > 0 else None)

    server.shutdown()
    server.server_close()

    if not finished_in_time:
        return "timeout", None
    return str(state["outcome"]), state["replacements"]  # type: ignore[return-value]
