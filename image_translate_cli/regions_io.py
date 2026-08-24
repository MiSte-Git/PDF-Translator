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
        region = OcrTextRegion(
            text=str(entry.get("original_text", "")),
            x=int(entry["x"]),
            y=int(entry["y"]),
            width=int(entry["width"]),
            height=int(entry["height"]),
            confidence=float(entry.get("confidence", 0.0)),
        )
        replacements.append(TextReplacement(region=region, translated_text=str(entry["translated_text"])))
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
