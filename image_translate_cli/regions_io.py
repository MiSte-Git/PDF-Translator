"""Shared validation for the JSON region-list shape used across
image_translate_cli's `correct` (--regions file) and `review` (browser
POST body from review_server.py) commands - see
image_translate_cli/report.py::RegionRecord for the shape this validates,
and CLI.md's "correct"/"review" sections for the documented contract.

Split out from cli.py (22.08.2026, when `review` was added) so `review`'s
HTTP handler and `correct`'s file-based path share exactly one validation
path instead of two copies that could drift apart - the same list shape a
human edits in the browser or a caller edits programmatically before
writing a --regions file.
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.images.inpainting import TextReplacement
from pipeline.images.ocr import OcrTextRegion

REGION_REQUIRED_FIELDS = ("x", "y", "width", "height", "translated_text")


class RegionsError(ValueError):
    """Raised for any problem with a region list: not a list, an entry
    missing a required field, or (load_regions_file only) an unreadable
    file / invalid JSON. Mirrors image_translate_cli.config.ConfigError's
    role for --config."""


def replacements_from_region_list(data: object) -> list[TextReplacement]:
    """Validate an already-JSON-decoded region list (a list[dict], see
    REGION_REQUIRED_FIELDS) and rebuild it into list[TextReplacement],
    ready for InpaintingBackend.apply(). Array ORDER doesn't matter and
    `index` (if present) is not used for anything - each entry is fully
    self-contained (see RegionRecord's docstring). `confidence`/
    `original_text` are optional here (defaulted to 0.0/"") so a caller's
    UI doesn't have to round-trip fields it never needed to look at, only
    `x`/`y`/`width`/`height`/`translated_text` are required.

    `orig_x`/`orig_y`/`orig_width`/`orig_height` (26.08.2026, all
    optional, each individually defaulting to the same-named `x`/`y`/
    `width`/`height` value) - the region's TRUE, ORIGINAL OCR position,
    kept SEPARATE from `x`/`y`/`width`/`height` (which keep their
    existing meaning: "where this should be drawn now") so a correction
    UI can move/resize a box without losing track of where the
    untranslated source text actually still sits (see
    pipeline.images.inpainting.TextReplacement.render_box's docstring -
    real user report, Backlog.md 26.08.2026: "die Positionen, Grösse und
    Korrekturen werden nicht übernommen"). Absent (the common case: a
    hand-written --regions file, or any entry that was never moved) means
    "this position IS the original" - `region` and the resulting
    TextReplacement.render_box (left None) are then identical to what
    this function has always built, byte-for-byte. When present and
    different, `region` is built from the orig_* values and `render_box`
    from the plain x/y/width/height values - image_translate_cli/
    review_server.py's browser page is the first caller to actually set
    these (see its collectRegions()), a hand-written --regions file can
    use them too but rarely needs to.

    `font_size`/`bold`/`centered` (28.08.2026, all optional - see
    pipeline.images.inpainting.TextReplacement's matching
    render_font_size/render_bold/render_centered docstring, real user
    report Backlog.md 28.08.2026: "Wenn ich etwas korrigiere, muss es
    auch genauso korrigiert werden wie ich es im Viewer sehe."). Unlike
    orig_*/x/y/width/height above, these have NO "derive from something
    else" fallback - `font_size`/`bold` absent means "keep estimating
    from the original OCR pixels, exactly as before this round" (None on
    TextReplacement), `centered` absent means "left-aligned" (False,
    also the exact previous behaviour). A correction UI only ever sends
    these when a human explicitly set them for THIS region - there is
    deliberately no attempt here (or anywhere in the renderer) to guess
    an original font size/weight/alignment from `orig_width`/
    `orig_height`/OCR data; that guess already happens once, in
    pipeline.images.font_style.estimate_font_style()/_initial_font_size(),
    and stays there.
    """
    if not isinstance(data, list):
        raise RegionsError(f"Regionen müssen eine JSON-Liste sein, nicht {type(data).__name__}")

    replacements: list[TextReplacement] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise RegionsError(f"regions[{i}] ist kein JSON-Objekt")
        missing = [f for f in REGION_REQUIRED_FIELDS if f not in entry]
        if missing:
            raise RegionsError(f"regions[{i}]: Pflichtfeld(er) fehlen: {', '.join(missing)}")
        current_x, current_y = int(entry["x"]), int(entry["y"])
        current_width, current_height = int(entry["width"]), int(entry["height"])
        orig_x = int(entry.get("orig_x", current_x))
        orig_y = int(entry.get("orig_y", current_y))
        orig_width = int(entry.get("orig_width", current_width))
        orig_height = int(entry.get("orig_height", current_height))
        region = OcrTextRegion(
            text=str(entry.get("original_text", "")),
            x=orig_x,
            y=orig_y,
            width=orig_width,
            height=orig_height,
            confidence=float(entry.get("confidence", 0.0)),
        )
        moved = (orig_x, orig_y, orig_width, orig_height) != (current_x, current_y, current_width, current_height)
        render_box = (
            OcrTextRegion(
                text=region.text,
                x=current_x,
                y=current_y,
                width=current_width,
                height=current_height,
                confidence=region.confidence,
            )
            if moved
            else None
        )
        font_size_raw = entry.get("font_size")
        bold_raw = entry.get("bold")
        replacements.append(
            TextReplacement(
                region=region,
                translated_text=str(entry["translated_text"]),
                render_box=render_box,
                render_font_size=int(font_size_raw) if font_size_raw is not None else None,
                render_bold=bool(bold_raw) if bold_raw is not None else None,
                render_centered=bool(entry.get("centered", False)),
            )
        )
    return replacements


def load_regions_file(path: str) -> list[TextReplacement]:
    """Read a --regions JSON file (the exact shape `translate`'s report
    puts in results[].regions, or a prior `correct`/`review` result's
    regions) and validate/rebuild it via replacements_from_region_list().
    """
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RegionsError(f"Regions-Datei konnte nicht gelesen werden: {path} ({exc})") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RegionsError(f"Regions-Datei ist kein gültiges JSON: {path} ({exc})") from exc

    return replacements_from_region_list(data)
