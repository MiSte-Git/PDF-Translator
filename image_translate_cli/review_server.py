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

# _representative_color()/_sample_background() (28.08.2026, Runde 4) are
# otherwise-private inpainting.py helpers, imported here (not just the
# public TextReplacement/estimated_font_size) so _initial_bold_estimates()
# below can run the EXACT SAME background-sampling steps every
# InpaintingBackend.apply() already runs before calling
# pipeline.images.font_style.estimate_font_style() - see that function's
# own call site further down for why a second, slightly-different
# implementation here would risk silently drifting from what apply()
# itself actually does.
from pipeline.images.font_style import estimate_font_style
from pipeline.images.inpainting import (
    TextReplacement,
    _representative_color,
    _sample_background,
    estimated_font_size,
)

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
  /* 28.08.2026 (Runde 4) - real user report, Backlog.md 28.08.2026:
     "Wenn ich etwas korrigiere, muss es auch genauso korrigiert werden
     wie ich es im Viewer sehe" - font size/bold/centered controls, one
     small floating toolbar per region, same dark-UI language as the
     header buttons/.resize-handle above (same #262626/#3b82f6/#3a3a3a
     palette) rather than a new visual style. Positioned just ABOVE the
     box (negative top, mirrors .resize-handle's own negative right/
     bottom offsets below the box) so it never covers the text it edits. */
  .region-toolbar {
    position: absolute; top: -26px; left: -1px; z-index: 5;
    display: flex; align-items: center; gap: 3px;
    background: #262626; border: 1px solid #3a3a3a; border-radius: 5px;
    padding: 2px 3px; cursor: default; touch-action: none;
  }
  .region-toolbar button {
    font-size: 11px; line-height: 1; padding: 3px 6px; border-radius: 3px;
    border: 1px solid #444; background: #333; color: #eee; cursor: pointer;
    min-width: 18px;
  }
  .region-toolbar button.ctrl-active { background: #3b82f6; border-color: #3b82f6; color: #fff; }
  .region-toolbar .ctrl-bold { font-weight: 700; }
  .region-toolbar .ctrl-size-label { font-size: 10px; color: #aaa; min-width: 26px; text-align: center; }
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

// 27.08.2026 - real user report, Backlog.md 27.08.2026: a manually
// enlarged/moved box rendered at roughly its ORIGINAL size/position
// instead of the corrected one - worse for a bigger edit, milder but
// still present for smaller ones. Michael confirmed using the mouse
// wheel to zoom the whole window while editing, which is the leading
// suspect (a zoom implemented as a visual scale on top of this page
// would make every drag/resize's clientX/clientY delta correspond to
// MORE or FEWER actual box pixels than intended - proportionally worse
// the bigger the drag). This sandbox's Chromium can't reproduce
// pywebview/WebKitGTK's own zoom behavior, so rather than guess further,
// Michael's own suggestion: "Können wir nicht Logs aus der
// Fenstersitzung generieren? [...] Welche Box ich wie verändert habe?
// Zumindest für Analysezwecke?" - debugLog records exactly the numbers
// that would expose a scale mismatch (devicePixelRatio, the stage's
// logical vs. actually-rendered size) alongside every drag/resize's
// before/after geometry, POSTed to /api/debug-log on Anwenden (fire-
// and-forget - see that route's own comment) and written next to the
// corrected output, so it can just be attached the next time this
// happens instead of screenshots and guesswork.
const debugLog = [];
function logEvent(type, extra) {
  const stage = document.getElementById('stage');
  const rect = stage ? stage.getBoundingClientRect() : null;
  debugLog.push({
    type,
    t: Date.now(),
    devicePixelRatio: window.devicePixelRatio,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    // stageStyleWidth/Height are the LOGICAL size set once in init()
    // below (img.naturalWidth/Height - never changes); stageRectWidth/
    // Height is what the stage actually occupies on screen right now -
    // equal to the style size at 100% zoom; different from it is
    // exactly the scale-mismatch signature described above.
    stageStyleWidth: stage ? stage.style.width : null,
    stageStyleHeight: stage ? stage.style.height : null,
    stageRectWidth: rect ? rect.width : null,
    stageRectHeight: rect ? rect.height : null,
    ...extra,
  });
}

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
    logEvent('init', {naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight, regionCount: regionsData.length});
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

    // 28.08.2026 (Runde 4) - font-size/bold/centered UI state for the
    // toolbar built below. r.font_size_px/r.bold already reflect the
    // TRUE value the renderer would use for this region even if nobody
    // touches a control this round - the server (start_review_server())
    // fills these from the same estimate_font_style()/estimated_font_size()
    // pixel analysis InpaintingBackend.apply() itself runs, or from an
    // EARLIER round's explicit render_font_size/render_bold override when
    // one already exists (see that function's own comment) - so a region
    // nobody ever touches previews and renders identically, closing the
    // same "Vorschau zeigt X, aber gespeichert wird Y" gap for these
    // fields that render_box already closed for position/size in an
    // earlier round.
    //
    // *Touched* tracks whether THIS control was ever explicitly set -
    // either by a human clicking it THIS session (the click handlers
    // below set it), or already, by an EARLIER session's explicit choice
    // (r.font_size_touched/r.bold_touched, set server-side whenever
    // replacement.render_font_size/render_bold was already not-None) -
    // collectRegions() only ever sends font_size/bold for a *touched*
    // region, see its own comment for why an already-explicit choice from
    // a prior round must count as touched too, or a further round that
    // never revisits this one control would silently regress it back to
    // auto-estimated (image_translate_cli/regions_io.py::
    // replacements_from_region_list()'s tri-state contract has no
    // "keep the old override" fallback - omitted always means "start
    // auto-estimating again").
    box.dataset.fontSize = String(r.font_size_px || 13);
    box.dataset.fontSizeTouched = r.font_size_touched ? '1' : '0';
    box.dataset.bold = r.bold ? '1' : '0';
    box.dataset.boldTouched = r.bold_touched ? '1' : '0';
    // `centered` has no such landmine (see regions_io.py's docstring:
    // False already IS the untouched/auto behaviour) - no *Touched*
    // tracking needed, collectRegions() always sends the box's current
    // value.
    box.dataset.centered = r.centered ? '1' : '0';

    const text = document.createElement('div');
    text.className = 'region-text';
    text.contentEditable = 'true';
    text.textContent = r.translated_text;
    // Approximates the real render (26.08.2026, see .region-text's own
    // CSS comment above) - r.font_size_px is absent only for a
    // hand-written --regions file loaded via `correct` that never went
    // through report.py's regions_from_replacements(), never for
    // anything `review` itself produces; falls back to the CSS default.
    text.dataset.baseFontSize = box.dataset.fontSize;
    // 28.08.2026 (Runde 4) - initial bold/alignment preview, same source
    // of truth (box.dataset.bold/centered, set just above) the toolbar's
    // own click handlers below update - kept in sync from the very first
    // render, not just after a human touches a control.
    text.style.fontWeight = box.dataset.bold === '1' ? '700' : '400';
    text.style.textAlign = box.dataset.centered === '1' ? 'center' : 'left';
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

    box.appendChild(buildRegionToolbar(box, text));

    makeDraggable(box, text, handle);
    makeResizable(box, handle);

    refitText(box, text);
    stage.appendChild(box);
  });
}

// 28.08.2026 (Runde 4) - font-size stepper + bold/centered toggles, real
// user report Backlog.md 28.08.2026: "Wenn ich etwas korrigiere, muss es
// auch genauso korrigiert werden wie ich es im Viewer sehe" - a simple
// rich-text-style toolbar per region, factored out of renderRegions()
// since it needs no data besides the box/text elements it controls (both
// already carry every piece of state - box.dataset.fontSize/bold/
// centered/*Touched, set by renderRegions() above - these handlers need).
// Every control mutates that SAME box.dataset state collectRegions()
// later reads, and re-applies the live preview (refitText()/
// text.style.fontWeight/textAlign) immediately, so what a human sees the
// instant they click a control is already what a further collectRegions()
// call would send - no separate "confirm" step.
function buildRegionToolbar(box, text) {
  const toolbar = document.createElement('div');
  toolbar.className = 'region-toolbar';
  // A pointerdown anywhere on the toolbar (including its own padding,
  // between buttons) must never reach box's own drag handler (see
  // makeDraggable() below) - mirrors makeResizable()'s handle
  // e.stopPropagation() on its own pointerdown for the exact same reason.
  toolbar.addEventListener('pointerdown', (e) => e.stopPropagation());

  const sizeDown = document.createElement('button');
  sizeDown.type = 'button';
  sizeDown.textContent = '-';
  sizeDown.title = 'Schrift kleiner';
  const sizeLabel = document.createElement('span');
  sizeLabel.className = 'ctrl-size-label';
  sizeLabel.textContent = box.dataset.fontSize + 'px';
  const sizeUp = document.createElement('button');
  sizeUp.type = 'button';
  sizeUp.textContent = '+';
  sizeUp.title = 'Schrift grösser';
  const boldBtn = document.createElement('button');
  boldBtn.type = 'button';
  boldBtn.className = 'ctrl-bold' + (box.dataset.bold === '1' ? ' ctrl-active' : '');
  boldBtn.textContent = 'B';
  boldBtn.title = 'Fett';
  const alignBtn = document.createElement('button');
  alignBtn.type = 'button';
  alignBtn.className = box.dataset.centered === '1' ? 'ctrl-active' : '';
  alignBtn.textContent = box.dataset.centered === '1' ? 'C' : 'L';
  alignBtn.title = 'Linksbündig/Zentriert';

  // No hard maximum (27.08.2026's renderer, pipeline.images.inpainting.py
  // _fit_text(), only ever SHRINKS a render_font_size override that
  // doesn't fit - it never clamps a start_size against _MAX_FONT_SIZE the
  // way the auto-estimate itself is capped, see _initial_font_size()'s
  // own docstring) - only a floor (matches _FIT_MIN_SIZE/_MIN_FONT_SIZE,
  // below which the renderer's own shrink loop already stops) and a
  // generous upper safety bound against a stray huge value, not a claim
  // about what the renderer would actually still fit on the page.
  function setFontSize(newSize) {
    newSize = Math.max(_FIT_MIN_SIZE, Math.min(400, newSize));
    box.dataset.fontSize = String(newSize);
    box.dataset.fontSizeTouched = '1';
    text.dataset.baseFontSize = String(newSize);
    sizeLabel.textContent = newSize + 'px';
    refitText(box, text);
  }
  sizeDown.addEventListener('click', (e) => {
    e.preventDefault();
    setFontSize(parseInt(box.dataset.fontSize, 10) - 2);
  });
  sizeUp.addEventListener('click', (e) => {
    e.preventDefault();
    setFontSize(parseInt(box.dataset.fontSize, 10) + 2);
  });
  boldBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const newBold = box.dataset.bold !== '1';
    box.dataset.bold = newBold ? '1' : '0';
    box.dataset.boldTouched = '1';
    text.style.fontWeight = newBold ? '700' : '400';
    boldBtn.classList.toggle('ctrl-active', newBold);
  });
  alignBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const newCentered = box.dataset.centered !== '1';
    box.dataset.centered = newCentered ? '1' : '0';
    text.style.textAlign = newCentered ? 'center' : 'left';
    alignBtn.classList.toggle('ctrl-active', newCentered);
    alignBtn.textContent = newCentered ? 'C' : 'L';
  });

  toolbar.appendChild(sizeDown);
  toolbar.appendChild(sizeLabel);
  toolbar.appendChild(sizeUp);
  toolbar.appendChild(boldBtn);
  toolbar.appendChild(alignBtn);
  return toolbar;
}

// 27.08.2026 - see logEvent()'s own comment above for the full story
// (real user report, Backlog.md 27.08.2026): a zoomed window can make
// the stage's ACTUAL on-screen size differ from the LOGICAL size
// (`stage.style.width/height`, set once in init() to the image's real
// pixel dimensions and never touched again) that `box.style.left/top/
// width/height` are expressed in. `e.clientX/clientY` are always
// reported in on-screen (post-zoom) pixels - applying their deltas to
// `box.style.*` directly, unscaled, is only correct at exactly 100%
// zoom; at any other zoom level every drag/resize ends up proportionally
// too big or too small, worse the larger the gesture. Dividing by this
// ratio (computed fresh from the stage's actual rendered size vs. its
// logical size, not from an assumed zoom API) self-corrects regardless
// of how the zoom was implemented, and is a no-op (ratio 1) whenever the
// two already match - safe to apply unconditionally.
function stageScale() {
  const stage = document.getElementById('stage');
  const logicalWidth = parseInt(stage.style.width, 10);
  if (!logicalWidth) return 1;
  const rect = stage.getBoundingClientRect();
  return rect.width / logicalWidth || 1;
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
  let dragging = false, moved = false, startX = 0, startY = 0, startLeft = 0, startTop = 0, dragScale = 1;
  box.addEventListener('pointerdown', (e) => {
    if (e.target === handle) return;
    dragging = true;
    moved = false;
    startX = e.clientX; startY = e.clientY;
    startLeft = parseInt(box.style.left, 10);
    startTop = parseInt(box.style.top, 10);
    dragScale = stageScale();
    // 27.08.2026 - see makeResizable()'s matching comment: guarded the
    // same way for the same WebKitGTK-robustness reasoning, even though
    // this call already sits after every piece of state pointermove
    // needs (unlike the resize handler, no logging depends on it here).
    try { box.setPointerCapture(e.pointerId); } catch (err) { /* see comment above */ }
  });
  box.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = (e.clientX - startX) / dragScale, dy = (e.clientY - startY) / dragScale;
    if (!moved) {
      if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      moved = true;
      // Only suppress the native click/selection behavior once this is
      // genuinely a drag - keeps a plain click on the text free to place
      // an edit cursor as usual.
      e.preventDefault();
      const selection = window.getSelection();
      if (selection) selection.removeAllRanges();
      logEvent('drag-start', {origX: box.dataset.origX, origY: box.dataset.origY, styleLeftBefore: startLeft + 'px', styleTopBefore: startTop + 'px', scale: dragScale});
    }
    box.style.left = (startLeft + dx) + 'px';
    box.style.top = (startTop + dy) + 'px';
  });
  box.addEventListener('pointerup', () => {
    if (moved) logEvent('drag-end', {origX: box.dataset.origX, origY: box.dataset.origY, styleLeftAfter: box.style.left, styleTopAfter: box.style.top, scale: dragScale});
    dragging = false;
  });
}

function makeResizable(box, handle) {
  let resizing = false, startX = 0, startY = 0, startW = 0, startH = 0, resizeScale = 1;
  handle.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    resizing = true;
    startX = e.clientX; startY = e.clientY;
    startW = parseInt(box.style.width, 10);
    startH = parseInt(box.style.height, 10);
    resizeScale = stageScale();
    // 27.08.2026 - logEvent() BEFORE setPointerCapture(): the capture
    // call can throw (observed in a synthetic-PointerEvent test, but not
    // relied on here as browser-specific behavior - WebKitGTK's
    // PointerEvent support has a history of being less complete than
    // Chromium's, and this is the engine pywebview uses on Michael's
    // Linux setup) - logging the gesture's start must not depend on
    // capture succeeding, or a resize-start could silently go missing
    // from exactly the kind of session this logging exists to diagnose.
    // 27.08.2026 - styleLeft/styleTop added (not just width/height): a
    // resize never changes them, but after N correction rounds this
    // box's CURRENT left/top may already differ from origX/origY (a
    // PRIOR round may have dragged it) - without logging the actual
    // position too, a debug log can't tell "was this box already
    // somewhere else before today's resize" from "did today's resize
    // itself move it", which matters for diagnosing a real-world case
    // (Backlog.md 27.08.2026 round 5) where two boxes with an existing,
    // multi-round-old custom size broke on a further small resize.
    logEvent('resize-start', {origX: box.dataset.origX, origY: box.dataset.origY, styleLeft: box.style.left, styleTop: box.style.top, styleWidthBefore: box.style.width, styleHeightBefore: box.style.height, scale: resizeScale});
    try { handle.setPointerCapture(e.pointerId); } catch (err) { /* see comment above */ }
  });
  handle.addEventListener('pointermove', (e) => {
    if (!resizing) return;
    const dw = (e.clientX - startX) / resizeScale, dh = (e.clientY - startY) / resizeScale;
    box.style.width = Math.max(8, startW + dw) + 'px';
    box.style.height = Math.max(8, startH + dh) + 'px';
    // 27.08.2026 - see refitText()'s own comment: a resize changes the
    // very box width/height that preview font-size now depends on, so it
    // has to re-run live, not just once at initial load.
    const textEl = box.querySelector('.region-text');
    if (textEl) refitText(box, textEl);
  });
  handle.addEventListener('pointerup', (e) => {
    // 27.08.2026 - stopPropagation() here mirrors the pointerdown
    // handler above: without it, this event bubbles from the handle up
    // to box's OWN pointerup listener (makeDraggable(), same box) and -
    // since that listener's `moved` flag stays true from whatever the
    // LAST actual drag on this box was, not reset by a resize - logs a
    // spurious 'drag-end' for a gesture that was never a drag. Caught
    // via this feature's own diagnostic log looking wrong in exactly
    // the way it exists to prevent, so worth not shipping as-is.
    e.stopPropagation();
    if (resizing) logEvent('resize-end', {origX: box.dataset.origX, origY: box.dataset.origY, styleLeft: box.style.left, styleTop: box.style.top, styleWidthAfter: box.style.width, styleHeightAfter: box.style.height, scale: resizeScale});
    resizing = false;
  });
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
    const record = {
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
      // 28.08.2026 (Runde 4) - `centered` has NO "leave it out to keep
      // the old behaviour" fallback on the way back in (see
      // image_translate_cli/regions_io.py::replacements_from_region_list()'s
      // docstring: False - left-aligned - already IS the untouched/auto
      // behaviour), so unlike font_size/bold right below, it is always
      // safe to send the box's current toggle state, touched or not.
      centered: box.dataset.centered === '1',
    };
    // font_size/bold (28.08.2026, Runde 4) are the OPPOSITE: omitted here
    // means "keep auto-estimating, exactly as before this round" on the
    // way back in - so each is only ever included when its control was
    // actually TOUCHED for THIS region. "Touched" starts out true already
    // for a region whose replacement carried an explicit render_font_size/
    // render_bold from an EARLIER round (see start_review_server()'s own
    // comment on why) - without that, a further round that never revisits
    // this one control would silently regress an already-explicit choice
    // back to auto-estimated the moment it's re-applied, exactly the
    // regression this file's own instructions warn against (turning a
    // real bold heading non-bold again just because some OTHER box was
    // moved this round).
    if (box.dataset.fontSizeTouched === '1') {
      record.font_size = parseInt(box.dataset.fontSize, 10);
    }
    if (box.dataset.boldTouched === '1') {
      record.bold = box.dataset.bold === '1';
    }
    out.push(record);
  });
  return out;
}

// 27.08.2026 - fire-and-forget: the debug log is a diagnostic aid, never
// allowed to delay or block the actual /api/apply//api/cancel POST that
// ends the session. Errors are swallowed on purpose - a browser without
// a debug_log_path configured (server started without one) gets a plain
// {"ok": false} back, not a thrown exception, but this still guards
// against a network hiccup on top of that.
function sendDebugLog(reason) {
  logEvent(reason);
  try {
    fetch('/api/debug-log', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(debugLog),
    });
  } catch (e) { /* diagnostic only, never blocks the real action */ }
}

async function apply() {
  setStatus('Wird angewendet ...');
  sendDebugLog('apply-clicked');
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
  sendDebugLog('cancel-clicked');
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


def _initial_bold_estimates(source_path: str, initial_replacements: list[TextReplacement]) -> list[bool]:
    """Best-effort per-region bold ESTIMATE for _PAGE_HTML's "B" toggle's
    initial state (28.08.2026, Runde 4 - see TextReplacement.render_bold's
    own docstring and Backlog.md 28.08.2026: "Wenn ich etwas korrigiere,
    muss es auch genauso korrigiert werden wie ich es im Viewer sehe").

    For a replacement whose `render_bold` is already set (an EARLIER
    correction round's explicit choice), that value is returned as-is -
    no pixel analysis needed or wanted, an explicit human choice always
    wins. Only for `render_bold is None` (never touched, still fully
    auto-estimated) does this run the EXACT SAME three calls every
    InpaintingBackend.apply() makes before erasing a region's pixels -
    _sample_background() -> _representative_color() -> estimate_font_
    style() (pipeline.images.inpainting/pipeline.images.font_style) -
    using `replacement.translated_text` and `estimated_font_size(region)`
    as candidate_text/size, exactly like apply() does. start_review_server()
    always calls this BEFORE any apply()/erase ever runs, so `source_path`
    is still the fully pristine, untouched image at this point - the same
    real pixels the renderer itself would read for a replacement nobody
    ever touches. This closes the same "Vorschau zeigt X, aber gespeichert
    wird Y" gap for the bold toggle's DEFAULT state that estimated_font_size()
    already closed for the size stepper's default value (26.08.2026,
    report.py::regions_from_replacements()) - a region nobody ever touches
    now previews with the SAME bold/non-bold guess the final render will
    actually use, not just a hand-wavy always-False default.

    Returns one bool per entry in `initial_replacements`, SAME order.
    Never raises: the image failing to open, or any single region's own
    estimate failing (a 0-sized/degenerate region, an unexpected pixel
    layout - not reproduced, just not worth risking a working review
    session over), falls back to `False` for that entry rather than
    aborting start_review_server() - this only seeds a control's STARTING
    position, a wrong initial guess costs the human one extra click on
    "B", never a corrupted apply().
    """
    estimates: list[bool] = []
    image = None  # lazy-opened once, only if at least one entry needs it; False once opening it failed, so later entries don't retry it uselessly
    for replacement in initial_replacements:
        if replacement.render_bold is not None:
            estimates.append(replacement.render_bold)
            continue
        if image is None:
            try:
                from PIL import Image as PILImage

                image = PILImage.open(source_path).convert("RGB")
            except Exception:
                image = False
        if image is False:
            estimates.append(False)
            continue
        region = replacement.region
        try:
            background = _sample_background(image, region.x, region.y, region.width, region.height)
            representative = _representative_color(background)
            size = estimated_font_size(region)
            style = estimate_font_style(image, region, representative, replacement.translated_text, size)
            estimates.append(style.bold)
        except Exception:
            estimates.append(False)
    return estimates


def start_review_server(
    source_path: str,
    initial_replacements: list[TextReplacement],
    host: str = "127.0.0.1",
    port: int = 0,
    debug_log_path: str | None = None,
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

    `debug_log_path` (27.08.2026, optional, `None` for `run_review_session()`/
    `cli.py`'s `review` command - only webapp/review_bridge.py passes one) -
    real user report, Backlog.md 27.08.2026: a manually enlarged/moved box
    (the title, "Spirit - Soul - Meatsuit_DE") rendered at roughly its
    ORIGINAL tiny size/position instead of the much bigger one set in the
    browser, worse for a bigger edit and present but milder for smaller
    ones - a pattern consistent with a coordinate-scale mismatch, but not
    reproducible from this sandbox's Chromium (Michael's machine runs
    pywebview/WebKitGTK on Linux, a different rendering engine, and he
    confirmed using the mouse wheel to zoom the whole window while
    editing). Michael's own suggestion: "Können wir nicht Logs aus der
    Fenstersitzung generieren? [...] Welche Box ich wie verändert habe?
    Zumindest für Analysezwecke?" This is that - see _PAGE_HTML's
    `logEvent()`/`debugLog` for what gets recorded (every drag/resize's
    before/after box geometry, plus `window.devicePixelRatio` and the
    stage's logical vs. actually-rendered size at each step - exactly the
    numbers that would expose a zoom-related scale mismatch) and the new
    POST /api/debug-log route below for where it lands: a plain JSON file
    next to the corrected output (see review_bridge.py's own comment for
    the exact path), so it shows up right alongside the QA report with no
    extra step from Michael - he can just attach it next time this
    happens. Best-effort only: a write failure here must never abort or
    even delay "Anwenden" itself, which is why _handle_debug_log() below
    swallows OSError rather than propagating it as a 500 (Anwenden's own
    POST to /api/apply is a completely separate request, already
    processed/acknowledged by the time this one lands).
    """
    initial_regions = [r.to_dict() for r in regions_from_replacements(initial_replacements)]
    # 28.08.2026 (Runde 4) - enrich each region dict with the font-size/
    # bold/centered UI state _PAGE_HTML's toolbar (buildRegionToolbar())
    # needs - see TextReplacement.render_font_size/render_bold/
    # render_centered's own docstring and regions_io.py::
    # replacements_from_region_list()'s matching read-side contract.
    # Deliberately done HERE, not by adding fields to report.py's
    # RegionRecord/to_dict() - report.py's JSON shape is a separate,
    # versioned public contract (REPORT_SCHEMA_VERSION) meant for
    # `translate`'s report / `correct --regions`, not this page's own
    # private wire format, and this task's own scope is this file only.
    #
    # font_size_px: RegionRecord.to_dict() already set this to
    # estimated_font_size(r.region) - the TRUE auto-estimate, unchanged
    # for a replacement whose render_font_size is still None. Overwritten
    # here ONLY when an EARLIER correction round already set an explicit
    # render_font_size, so the stepper's initial number (and the live
    # preview it seeds, via _PAGE_HTML's text.dataset.baseFontSize) shows
    # that real override, not the auto-estimate it no longer applies.
    #
    # bold: computed once, below, via _initial_bold_estimates() - either
    # an EARLIER round's explicit render_bold, or (only when that's still
    # None) the same pixel-based estimate InpaintingBackend.apply() itself
    # would compute for this replacement were it left untouched.
    #
    # *_touched: True whenever the corresponding TextReplacement field is
    # already NOT None - i.e. an EARLIER round's explicit choice, which
    # must keep counting as "touched" even if nobody revisits that one
    # control THIS round, or collectRegions() would omit it and
    # regions_io.py's tri-state contract (no "keep the old override"
    # fallback) would silently reset it back to auto-estimated. See
    # collectRegions()'s own matching comment for the read side of this.
    bold_estimates = _initial_bold_estimates(source_path, initial_replacements)
    for replacement, record, bold_value in zip(initial_replacements, initial_regions, bold_estimates):
        if replacement.render_font_size is not None:
            record["font_size_px"] = replacement.render_font_size
        record["font_size_touched"] = replacement.render_font_size is not None
        record["bold"] = bold_value
        record["bold_touched"] = replacement.render_bold is not None
        record["centered"] = replacement.render_centered
    state: dict[str, object] = {"outcome": None, "replacements": None}
    done = threading.Event()

    # 27.08.2026 (round 5, see debug_log_path's own docstring paragraph
    # above) - two sibling files, written next to debug_log_path, that
    # together give the EXACT region data for this round without relying
    # on the browser's own JS to have captured everything correctly:
    #   *_regions_before.json - this round's STARTING orig_x/y/width/
    #     height + x/y/width/height per box, i.e. what a PRIOR round (or
    #     the original translate_image() run, if this is the first
    #     correction) left this box at - the piece `debugLog` itself
    #     cannot show, since it only logs DELTAS from whatever the box's
    #     position already was when this page loaded, never that starting
    #     position itself.
    #   *_regions_after.json - the exact POST body /api/apply received
    #     (server-side, so independent of any client-side logging bug) -
    #     the literal input replacements_from_region_list() built this
    #     round's TextReplacement.region/render_box from.
    # Together with the QA report and *_correction_debug.json, this is
    # enough to reconstruct a whole round's region/render_box math by
    # hand instead of guessing at it.
    if debug_log_path:
        try:
            Path(debug_log_path).with_name(
                Path(debug_log_path).stem.replace("_correction_debug", "") + "_regions_before.json"
            ).write_text(json.dumps(initial_regions, indent=2), encoding="utf-8")
        except OSError:
            pass

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
                # 27.08.2026 - see the matching *_regions_before.json write
                # near initial_regions above: this is that pair's other
                # half, the EXACT payload this round sent, written before
                # anything else so it's captured even if a later step in
                # this handler (rare, but state/done below) ever changed.
                if debug_log_path:
                    try:
                        Path(debug_log_path).with_name(
                            Path(debug_log_path).stem.replace("_correction_debug", "") + "_regions_after.json"
                        ).write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    except OSError:
                        pass
                state["outcome"] = "apply"
                state["replacements"] = replacements
                self._send_json({"ok": True})
                done.set()
            elif self.path == "/api/cancel":
                state["outcome"] = "cancel"
                self._send_json({"ok": True})
                done.set()
            elif self.path == "/api/debug-log":
                # 27.08.2026 - see start_review_server()'s own docstring.
                # Fire-and-forget from the browser's side (app.js/
                # _PAGE_HTML never awaits this before/after "Anwenden") -
                # this handler mirrors that by never letting a write
                # problem here become a request failure the human would
                # even see, let alone one that could interfere with the
                # separate /api/apply request that actually matters.
                if debug_log_path:
                    try:
                        Path(debug_log_path).write_bytes(raw)
                    except OSError:
                        pass
                self._send_json({"ok": True})
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
