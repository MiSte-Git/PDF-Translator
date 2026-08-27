"""JSON report schema for image_translate_cli's `translate` and `correct`
commands (see CLI.md, sections "JSON-Report-Schema" and "correct", for the
documented contract this mirrors in code).

One ImageResult per input image, built from the pipeline.images.
translate_image.ImageTranslationStats that translate_image() already
returns per image - this module only reshapes that (plus a per-image
fatal-error path) into the stable, versioned, JSON-serializable report
structure a caller like TME is meant to parse, instead of handing out
ImageTranslationStats (a dataclass with OcrTextRegion/TextReplacement
objects, pipeline.images-internal, not meant as a public contract) as-is.

RegionRecord (22.08.2026, Michael: "Ich schicke ein Bild in die CLI,
bekomme eine Vorschau um etwaige Korrekturen zu machen und bekomme dann
ein übersetztes Bild zurück") is what makes that workflow possible without
every calling app reimplementing correction logic: `translate`'s result
already includes each translated region's editable state
(RegionRecord.to_dict()), and `correct` (see cli.py) accepts that exact
shape back, edited, to re-render - no OCR/provider re-run, mirroring
ui/image_job.py::run_image_correction_job()'s mechanism but exposed
headlessly instead of behind ui/image_correction_dialog.py's PySide6
widget. The actual editing UI (a table, a canvas, a chat flow - whatever
fits the calling app) is deliberately NOT part of this: only the
round-trippable data shape and the re-render step are.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.images.inpainting import TextReplacement, estimated_font_size

from image_translate_cli.config import ImageTranslateConfig, config_to_dict

# Bumped whenever a change here could break a caller parsing an EXISTING
# report shape (a field renamed/removed, a field's meaning/type changes).
# Adding a new field does NOT need a bump - mirrors config.
# CONFIG_SCHEMA_VERSION's policy, see CLI.md's "Versionierung" section.
REPORT_SCHEMA_VERSION = 1

# One image's outcome:
#   "ok"        - translate_image() ran to completion (regardless of how
#                 many of ITS regions were individually skipped/failed -
#                 see ImageTranslationStats.skipped/failed for that detail,
#                 mirrored in this result's own fields below), output file
#                 written.
#   "cancelled" - should_cancel() interrupted the run partway through;
#                 output file was still written (see translate_image()'s
#                 docstring: inpainting still runs once at the end with
#                 whatever was translated before cancellation).
#   "failed"    - a FATAL error for this one image: OCR raised OcrError
#                 (no regions to work with at all) or the final
#                 inpainting_backend.apply() raised InpaintingError (no
#                 output file could be written). `error` carries the
#                 message; `translated`/`skipped`/`failed` reflect
#                 whatever was completed before the fatal error, if
#                 anything.
_VALID_STATUSES = ("ok", "cancelled", "failed")


@dataclass(frozen=True)
class RegionRecord:
    """One successfully-translated region's editable state - a flat,
    JSON-serializable mirror of pipeline.images.inpainting.TextReplacement
    (which wraps pipeline.images.ocr.OcrTextRegion). Appears in
    `translate`'s report (one list per image, only for images with status
    "ok"/"cancelled" - a "failed" image has no rendered regions at all) and
    is exactly the shape `correct --regions` expects back.

    `index` is informational only (lets a UI label "Region 3" consistently
    and lets a human spot a reordered/dropped entry at a glance) - it is
    NOT used to match entries back up: each entry is fully self-contained
    (its own x/y/width/height), so `correct` rebuilds directly from
    whatever order the array is in. Editing `translated_text` is the
    normal case; editing x/y/width/height too is supported (mirrors
    pipeline.images.translate_image.build_corrected_replacements()'s
    `edited_geometry` parameter) for the draggable/resizable-box
    correction UI ui/image_correction_dialog.py already has - an external
    caller's own UI can offer the same if it wants to, or ignore geometry
    entirely and only ever edit `translated_text`.

    `x`/`y`/`width`/`height` mean "where this is drawn right now" -
    `replacement.render_box` if a previous correction round set one
    (26.08.2026, see pipeline.images.inpainting.TextReplacement.
    render_box's docstring), otherwise `replacement.region` (unchanged
    meaning, matches every entry from before this field existed).
    `orig_x`/`orig_y`/`orig_width`/`orig_height` (None unless a
    correction actually moved/resized this entry) carry
    `replacement.region` - the TRUE, ORIGINAL OCR position - forward
    SEPARATELY, so a second correction round (re-opening `review` on an
    already-corrected image, or a `correct --regions` file built from
    THIS report) still knows where the untranslated source text
    genuinely sits and can erase it there too, even though it's no
    longer being drawn there. See image_translate_cli.regions_io.
    replacements_from_region_list()'s matching docstring for the read
    side of this same contract.
    """

    index: int
    x: int
    y: int
    width: int
    height: int
    confidence: float
    original_text: str
    translated_text: str
    orig_x: int | None = None
    orig_y: int | None = None
    orig_width: int | None = None
    orig_height: int | None = None
    font_size_px: int = 0

    def to_dict(self) -> dict:
        data = {
            "index": self.index,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "font_size_px": self.font_size_px,
        }
        # orig_x/y/width/height are only present when a correction
        # actually moved/resized this entry - an UNCORRECTED region's
        # JSON shape only ever gains the new "font_size_px" key relative
        # to before 26.08.2026 (a plain additive field, no
        # REPORT_SCHEMA_VERSION bump needed per this module's own policy
        # above - existing report/--regions consumers that read known
        # keys and ignore unknown ones are unaffected).
        if self.orig_x is not None:
            data["orig_x"] = self.orig_x
            data["orig_y"] = self.orig_y
            data["orig_width"] = self.orig_width
            data["orig_height"] = self.orig_height
        return data


def regions_from_replacements(replacements: list[TextReplacement]) -> list[RegionRecord]:
    """Build the RegionRecord list for one image's report entry from the
    TextReplacement list translate_image() (or a prior `correct` call, see
    cli.py) actually produced/re-rendered - both `translate`'s and
    `correct`'s report use this, so a `correct` result can itself be fed
    into another `correct` round unchanged.
    """
    records = []
    for i, r in enumerate(replacements):
        box = r.render_box or r.region
        records.append(
            RegionRecord(
                index=i,
                x=box.x,
                y=box.y,
                width=box.width,
                height=box.height,
                confidence=r.region.confidence,
                original_text=r.region.text,
                translated_text=r.translated_text,
                orig_x=r.region.x if r.render_box is not None else None,
                orig_y=r.region.y if r.render_box is not None else None,
                orig_width=r.region.width if r.render_box is not None else None,
                orig_height=r.region.height if r.render_box is not None else None,
                # Always from the ORIGINAL region, never `box` - a
                # corrected box's height reflects how big the human
                # wanted the DRAW AREA to be, not a claim about the
                # original glyph size the estimate is meant to
                # approximate (26.08.2026, see estimated_font_size()'s
                # own docstring).
                font_size_px=estimated_font_size(r.region),
            )
        )
    return records


@dataclass
class ImageResult:
    """One input image's result - see module docstring for `status`."""

    input: str
    output: str | None
    status: str
    translated: int = 0
    skipped: int = 0
    failed: int = 0
    chars_sent: int = 0
    errors: list[str] = field(default_factory=list)
    """Per-region error strings - ImageTranslationStats.errors, unchanged.
    Empty unless `failed` > 0."""
    error: str | None = None
    """The fatal exception's message when status == "failed"; None
    otherwise. Never includes credentials (OcrError/InpaintingError/
    TranslationError never carry any - see their own docstrings)."""
    regions: list[RegionRecord] = field(default_factory=list)
    """Every successfully rendered region's editable state (see
    RegionRecord) - empty for a "failed" image (nothing was rendered) and,
    for `translate` specifically, empty when `--dry-run` was used (nothing
    is rendered then either). This is the input to `correct --regions`."""

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"Ungültiger ImageResult.status: {self.status!r}")

    def to_dict(self) -> dict:
        return {
            "input": self.input,
            "output": self.output,
            "status": self.status,
            "translated": self.translated,
            "skipped": self.skipped,
            "failed": self.failed,
            "chars_sent": self.chars_sent,
            "errors": list(self.errors),
            "error": self.error,
            "regions": [r.to_dict() for r in self.regions],
        }


def build_report(
    config: ImageTranslateConfig,
    results: list[ImageResult],
    started_at: str,
    finished_at: str,
    elapsed_seconds: float,
    estimated_cost_usd: float | None,
) -> dict:
    """Assemble the full report dict `translate` writes to --report (or
    stdout - see CLI.md). `started_at`/`finished_at` are ISO-8601
    timestamps (produced by the caller, not this function, so tests can
    pass fixed values instead of depending on wall-clock time).
    `estimated_cost_usd` is None when the provider's pricing model couldn't
    produce an estimate (currently always available - see
    pipeline.translation.cost_control.PricingModel - kept optional here in
    case a future provider has none).
    """
    images_ok = sum(1 for r in results if r.status == "ok")
    images_cancelled = sum(1 for r in results if r.status == "cancelled")
    images_failed = sum(1 for r in results if r.status == "failed")
    total_chars_sent = sum(r.chars_sent for r in results)

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "image_translate_cli",
        "started_at": started_at,
        "finished_at": finished_at,
        "config": config_to_dict(config),
        "results": [r.to_dict() for r in results],
        "summary": {
            "images_planned": len(results),
            "images_ok": images_ok,
            "images_cancelled": images_cancelled,
            "images_failed": images_failed,
            "total_chars_sent": total_chars_sent,
            "estimated_cost_usd": estimated_cost_usd,
            "elapsed_seconds": elapsed_seconds,
        },
    }


def build_correction_report(
    result: ImageResult,
    inpainting_backend_name: str,
    started_at: str,
    finished_at: str,
    command: str = "correct",
) -> dict:
    """Assemble the report dict `correct`/`review` writes to --report (or
    stdout) - a single-image counterpart of build_report(), without the
    fields that make no sense for a pure re-render (no provider/OCR
    config, no cost). `result.regions` (freshly rebuilt from what was
    actually re-rendered, see cli.py::_cmd_correct()/_cmd_review()) is
    what lets this be fed into ANOTHER `correct`/`review` round unchanged,
    the same way `translate`'s report is.

    `command` distinguishes which subcommand produced this report
    ("correct" - the default, kept for backward compatibility with
    existing callers/tests - or "review", added 22.08.2026 when `review`'s
    browser-based correction UI was added on top of the same re-render
    path); the report shape itself is otherwise identical between the two.
    """
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "image_translate_cli",
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "inpainting_backend": inpainting_backend_name,
        "result": result.to_dict(),
    }
