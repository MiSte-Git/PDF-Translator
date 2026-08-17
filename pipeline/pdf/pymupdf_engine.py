"""PdfEngine implementation backed by PyMuPDF (fitz).

This is the only file in the project allowed to import fitz/PyMuPDF.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import fitz

from pipeline.pdf.base import (
    LINE_BREAK_MARKER,
    PARAGRAPH_BREAK_MARKER,
    ImageBlock,
    PageInfo,
    TextBlock,
    TextSpan,
)
from pipeline.pdf.template import DocumentTemplate, block_overlaps

# PyMuPDF span "flags" bitfield: bit 1 = italic, bit 4 = bold.
_ITALIC_FLAG = 1 << 1
_BOLD_FLAG = 1 << 4

# PyMuPDF span "char_flags" bitfield (only populated with accurate values
# when TEXT_COLLECT_STYLES is passed to get_text() - see extract_blocks()):
# bit 1 = underline. Verified via tests/manual_inspect_redact_and_underline.py
# against 1526 Virelicon.pdf's underlined title.
_CHAR_UNDERLINE_FLAG = 1 << 1

# get_text("dict") flags: PyMuPDF's own TEXTFLAGS_DICT default, plus
# TEXT_COLLECT_STYLES so span["char_flags"] reliably reports underline (see
# _CHAR_UNDERLINE_FLAG) instead of only the coarser italic/bold styling.
_EXTRACT_FLAGS = fitz.TEXTFLAGS_DICT | fitz.TEXT_COLLECT_STYLES

# Base-14 Helvetica variants, keyed by (bold, italic), used as insert_textbox's
# fontname since the block's original embedded font is not available there.
_FONT_VARIANTS = {
    (False, False): "helv",
    (True, False): "hebo",
    (False, True): "heit",
    (True, True): "hebi",
}

_MIN_FONT_SIZE = 6.0
_FONT_STEP = 0.5

# Overflow fallback (insert_text): once at _MIN_FONT_SIZE, widen the box
# toward the right page edge before resorting to growing its height.
_WIDTH_STEP = 20.0
_PAGE_EDGE_MARGIN = 10.0

# Overflow fallback (insert_text): the height-growth step must not grow
# rect.y1 into the template's footer zone or off the page - see
# _max_rect_y1().
_FOOTER_MARGIN = 5.0

# Max allowed spread (pt) between the smallest and largest line x0 within one
# extract_blocks() group. PyMuPDF's raw block bbox is the union of all its
# lines; a paragraph that starts next to an image (narrow, high x0) and
# continues below it at full width (x0 near the margin) would otherwise
# produce one oversized bbox spanning both columns. 50pt safely separates a
# genuine column jump from normal text-alignment jitter (indentation,
# justification) within a single column.
_COLUMN_SPLIT_THRESHOLD = 50.0

# Terms that mark the start of an untranslatable metadata chunk (e.g. an
# account/address line) within an otherwise-translatable page-0 block - see
# _split_first_page_metadata(). Comparison is case-insensitive. Kept as a
# plain list, separate from the split logic itself, so it can later be
# exposed as a per-document, UI-editable list instead of a hardcoded one.
FIRST_PAGE_ANCHOR_TERMS = ["Issuer Address", "Asset Matrix"]

# Fill color of the quote-highlight rectangles found in 1526 Virelicon.pdf
# (confirmed via tests/manual_inspect_quote_blocks.py and
# tests/manual_test_highlight_overlap.py: one ~15pt-tall filled rectangle
# per highlighted line, get_drawings() type='re'). Compared with a small
# per-channel tolerance since drawing fill values are floats.
_HIGHLIGHT_FILL_COLOR = (0.871, 0.918, 0.965)
_HIGHLIGHT_FILL_TOLERANCE = 0.01

# Minimum vertical overlap (pt) a line's bbox must have with a highlight
# rectangle to count as "inside" it - see _line_is_highlighted(). Found via
# tests/manual_diagnose_highlight_pages_real.py (real DeepL translation run):
# in this PDF, an attribution line just below a highlight rectangle (e.g.
# "- Ivan", "- PQ to Unicorn Chat") sometimes sits a hairline (<0.1pt) inside
# the rectangle's bottom edge purely from floating-point rounding in the
# source PDF's own coordinates (confirmed case: line.y0=724.8932 vs.
# rect.y1=724.8999, a 0.0067pt sliver) - a strict `>0` overlap check
# misclassified 3 of 34 highlighted sub-blocks across 7 pages this way. 1.5pt
# is comfortably above that rounding noise (which measured well under 0.1pt)
# while staying well below a real text line's height (~13-15pt in this
# document), so it only screens out hairline touches, not genuine partial
# overlaps.
_HIGHLIGHT_LINE_TOLERANCE = 1.5

# Minimum amount (pt) a highlighted block's actually-inserted text may
# extend past its original highlight rectangle(s) before the background is
# redrawn taller - see _grow_highlight_if_needed(). Small enough to still
# catch genuine translation-driven overflow, but avoids redrawing for
# sub-pixel differences from font metrics/rounding.
_HIGHLIGHT_GROW_TOLERANCE = 1.0

# Safety margin (pt) kept between any block's grown height (and, for a
# highlighted block, its redrawn background) and the next block's own row
# - see _next_block_y0()/_collision_aware_max_y1(). Applies to every
# block, not just highlighted ones (see _insert_html_text()'s docstring).
# Small and fixed since it's just a hairline buffer against float-rounding
# at the boundary, not a layout gap.
_HIGHLIGHT_COLLISION_MARGIN = 3.0

# Fallback line-height-per-font-size ratio used by _estimate_line_height()
# only when a block's own bbox height can't be used directly (see there).
# 1.3x is this document's own observed line-height/font-size ratio at
# 11pt (~13.4-15.4pt measured per line across
# tests/manual_diagnose_highlight_regression_output.txt), not a generic
# typographic guess.
_LINE_HEIGHT_FALLBACK_RATIO = 1.3

# tests/output/growth_anomalies.jsonl (one JSON object per line) - see
# log_growth_anomaly(). Kept alongside this project's other tests/output/
# diagnostic artifacts rather than made configurable: this is a small,
# single-project tool, not a published library, so a fixed path is a
# deliberate simplification, not an oversight - a real multi-document
# deployment would want this injectable instead.
_GROWTH_ANOMALY_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "tests" / "output" / "growth_anomalies.jsonl"

# log_growth_anomaly() thresholds (see _log_growth_anomalies()).
_GROWTH_ANOMALY_FONT_SIZE_THRESHOLD = 8.0  # pt
_GROWTH_ANOMALY_HEIGHT_RATIO = 2.0  # final height / original bbox height


def _group_lines_by_x0(
    lines: list[dict], threshold: float
) -> list[list[dict]]:
    """Split lines into groups whose min/max x0 spread stays within threshold.

    Lines are consumed in order; a new group starts as soon as adding the
    next line would push the current group's x0 range beyond threshold.
    """
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_min = current_max = 0.0
    for line in lines:
        x0 = line["bbox"][0]
        if current and max(current_max, x0) - min(current_min, x0) > threshold:
            groups.append(current)
            current = []
        if current:
            current_min = min(current_min, x0)
            current_max = max(current_max, x0)
        else:
            current_min = current_max = x0
        current.append(line)
    if current:
        groups.append(current)
    return groups


def _union_bbox(
    bboxes: list[tuple[float, float, float, float]]
) -> tuple[float, float, float, float]:
    """Return the smallest bbox containing all given bboxes."""
    return (
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        max(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
    )


def _parse_color(color_int: int) -> tuple[int, int, int]:
    """Convert PyMuPDF's packed sRGB int into an (r, g, b) 0-255 tuple."""
    return (
        (color_int >> 16) & 255,
        (color_int >> 8) & 255,
        color_int & 255,
    )


def _line_text(raw_spans: list[dict]) -> str:
    """Concatenate a raw PyMuPDF line's span texts."""
    return "".join(span["text"] for span in raw_spans)


def _split_first_page_metadata(
    group: list[dict], anchor_terms: list[str]
) -> list[list[dict]]:
    """Split a page-0 line group into an untranslatable metadata part and a
    translatable rest, if any line contains one of `anchor_terms` (e.g. an
    "Issuer Address:" line immediately followed by the account address
    itself, both currently part of the same block as a following title/
    subtitle line - confirmed via tests/manual_inspect_address_block.py).

    The metadata part covers the first anchor line, its non-blank
    continuation lines (e.g. the address text), and - if a blank-line gap
    right after it is immediately followed by another anchor line (e.g. a
    second "Asset Matrix:" line further down the same block) - that chunk
    too, repeating until the next content after a gap is not itself an
    anchor line. The rest of the group (starting at that first non-metadata
    content; any blank lines right before it stay attached, matching how
    _build_text_spans() already drops leading blank-line markers) becomes
    the second part.

    Returns [group] unchanged if no anchor term is found, or if the split
    would leave either part empty.
    """
    def line_text(line: dict) -> str:
        return _line_text(line.get("spans", [])).strip()

    def has_anchor(line: dict) -> bool:
        text = line_text(line).lower()
        return any(term.lower() in text for term in anchor_terms)

    anchor_idx = next((i for i, line in enumerate(group) if has_anchor(line)), None)
    if anchor_idx is None:
        return [group]

    end = anchor_idx
    while end < len(group):
        end += 1
        while end < len(group) and line_text(group[end]):
            end += 1  # skip the chunk's non-blank continuation lines
        gap_end = end
        while gap_end < len(group) and not line_text(group[gap_end]):
            gap_end += 1  # skip the blank-line gap after the chunk
        if gap_end < len(group) and has_anchor(group[gap_end]):
            end = gap_end
            continue  # another metadata chunk follows - keep extending
        break

    metadata_part, rest_part = group[:end], group[end:]
    if not metadata_part or not rest_part:
        return [group]
    return [metadata_part, rest_part]


def _fill_matches_highlight(fill: object) -> bool:
    """Whether a drawing's fill color matches _HIGHLIGHT_FILL_COLOR within
    _HIGHLIGHT_FILL_TOLERANCE per channel. fill is get_drawings()'s "fill"
    entry: an (r, g, b) float tuple, or None if the drawing isn't filled.
    """
    if fill is None or not isinstance(fill, (tuple, list)) or len(fill) != 3:
        return False
    return all(
        abs(fill[i] - _HIGHLIGHT_FILL_COLOR[i]) <= _HIGHLIGHT_FILL_TOLERANCE for i in range(3)
    )


def _get_highlight_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Collect every filled rectangle drawing on `page` whose fill color
    matches _HIGHLIGHT_FILL_COLOR (see _fill_matches_highlight()) - the
    quote-highlight background confirmed by
    tests/manual_inspect_quote_blocks.py (1526 Virelicon.pdf: one ~15pt-tall
    rectangle per highlighted line, rather than one rectangle per quote).
    """
    rects: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        if not any(item[0] == "re" for item in drawing.get("items", [])):
            continue
        if not _fill_matches_highlight(drawing.get("fill")):
            continue
        rect = drawing.get("rect")
        if rect is not None:
            rects.append(rect)
    return rects


def _line_is_highlighted(line_bbox: fitz.Rect, highlight_rects: list[fitz.Rect]) -> bool:
    """Whether `line_bbox` vertically overlaps at least one of
    `highlight_rects` (see _get_highlight_rects()) by more than
    _HIGHLIGHT_LINE_TOLERANCE. A vertical-only check is enough since each
    highlight rectangle already spans the line's full width (confirmed by
    tests/manual_test_highlight_overlap.py).

    The tolerance (rather than any overlap > 0) matters: a line just below
    a highlight rectangle can share a hairline (<0.1pt) sliver with it from
    floating-point rounding in the source PDF's own coordinates alone, with
    no real visual overlap - see _HIGHLIGHT_LINE_TOLERANCE's comment for the
    confirmed case that motivated this.
    """
    for rect in highlight_rects:
        overlap = min(line_bbox.y1, rect.y1) - max(line_bbox.y0, rect.y0)
        if overlap > _HIGHLIGHT_LINE_TOLERANCE:
            return True
    return False


def _associated_highlight_extent(
    block_bbox: tuple[float, float, float, float], highlight_rects: list[fitz.Rect]
) -> fitz.Rect | None:
    """Union bbox of every highlight rect that meaningfully overlaps
    `block_bbox` vertically (same >_HIGHLIGHT_LINE_TOLERANCE rule as
    _line_is_highlighted()) - the original highlighted area a
    block.highlighted=True sub-block is expected to sit within, used by
    _grow_highlight_if_needed() to detect translation-driven overflow.
    Returns None if no rect qualifies (shouldn't normally happen for a
    block classified highlighted=True by _split_by_highlight(), but callers
    treat that defensively as "nothing to compare against, leave as-is").
    """
    bx0, by0, bx1, by1 = block_bbox
    overlapping = [
        rect
        for rect in highlight_rects
        if min(by1, rect.y1) - max(by0, rect.y0) > _HIGHLIGHT_LINE_TOLERANCE
    ]
    if not overlapping:
        return None
    union = overlapping[0]
    for rect in overlapping[1:]:
        union |= rect
    return union


def _estimate_line_height(block: TextBlock) -> float:
    """Estimate one text line's height (pt) from `block`'s own ORIGINAL
    layout - its bbox height divided by its own source line count (from
    block.text's "\\n"-separated lines) - rather than a guessed constant,
    so a height-growth step sized off this (see
    _insert_html_text()'s try_grow()) matches this specific
    block's actual line spacing/font size. For a block that's already a
    single line (the common case for a highlighted quote/attribution
    after _split_by_highlight()), this is just the block's own bbox
    height, which already directly measures one line in this document
    (confirmed repeatedly across
    tests/manual_diagnose_highlight_regression_output.txt: ~13-15pt per
    line at this document's 11pt body font). Falls back to
    block.font_size * _LINE_HEIGHT_FALLBACK_RATIO only if the bbox height
    is somehow degenerate (zero or negative - shouldn't happen for a real
    block).
    """
    line_count = block.text.count("\n") + 1
    bbox_height = block.bbox[3] - block.bbox[1]
    if bbox_height > 0:
        return max(bbox_height / line_count, 1.0)
    return max(block.font_size * _LINE_HEIGHT_FALLBACK_RATIO, 1.0)


def _next_block_y0(
    block: TextBlock, page_blocks: list[TextBlock], x_range: tuple[float, float] | None = None
) -> float | None:
    """y0 of the nearest OTHER block in `page_blocks` that sits below
    `block` (bbox y0 at or past `block`'s own bbox y1 - see below) AND
    shares roughly the same horizontal column (its bbox x-range overlaps
    `x_range`, or `block`'s own bbox x-range if `x_range` is None) - the
    boundary ANY block's height growth (see
    PyMuPdfEngine._collision_aware_max_y1()) must not cross, so it never
    grows into a different block's row. Returns None if there is no such
    block (e.g. `block` is the last one in its column on the page).

    `x_range` lets a caller widen the column beyond `block`'s own narrow
    bbox - needed for a highlighted block (see
    PyMuPdfEngine._collision_aware_max_y1()), whose actual redaction/
    redraw width (see redact_block()/_grow_highlight_if_needed()) is the
    WIDE associated-highlight-rectangle extent, not just its own text's
    bbox: a neighboring block sitting outside the highlighted block's
    narrow bbox but inside that wide highlight column was otherwise
    invisible to this collision check even though the highlighted block's
    own redraw could - and, confirmed by direct reproduction, did -
    paint over it.

    Compares candidates against `block`'s own bbox y1 (bottom), not y0
    (top): two DIFFERENT extracted blocks can legitimately share the same
    visual text line - e.g. a run of plain text immediately followed by a
    differently-styled run on the same line, which PyMuPDF already
    reports as separate raw blocks (confirmed via direct reproduction
    against "1526 VIRELICON.pdf": a line ending "...in" was immediately
    followed on the same row by a separately-styled "2 ways:" run). Such a
    sibling's own y0 sits INSIDE the current block's y-span, not below it.
    The old y0-vs-y0 comparison picked up that sibling as if it were the
    next row down, capping max_y1 below the current block's own original
    bottom edge - shrinking its usable area rather than growing it, which
    then also left its quote-highlight background never redrawn (see
    PyMuPdfEngine._grow_highlight_if_needed()) because the actually-needed
    height never even reached the point that would have triggered a
    redraw. Comparing against y1 instead correctly treats a same-row
    sibling as not "below" at all.
    """
    bx0, by0, bx1, by1 = block.bbox
    if x_range is not None:
        bx0, bx1 = x_range
    below = [
        other
        for other in page_blocks
        if other is not block
        and other.bbox[1] >= by1
        and other.bbox[0] < bx1
        and other.bbox[2] > bx0
    ]
    if not below:
        return None
    return min(other.bbox[1] for other in below)


def log_growth_anomaly(block: TextBlock, event: str, details: dict) -> None:
    """Append one JSON line to _GROWTH_ANOMALY_LOG_PATH recording a
    noteworthy growth/shrink event for `block` - see
    PyMuPdfEngine._log_growth_anomalies() for the three conditions that
    trigger this (collision-capped growth, a tiny final font size,
    excessive height growth). Meant to run as part of the normal pipeline
    (not just test scripts): so future runs against arbitrary PDFs
    automatically surface suspicious blocks in one shared file, without
    anyone needing to manually inspect every output PDF. Best-effort: any
    I/O failure here is swallowed rather than raised, since a logging
    failure should never break the actual translation/insertion it's
    only observing.
    """
    entry = {
        "page_index": block.page_index,
        "bbox": [round(v, 1) for v in block.bbox],
        "text_preview": block.text.replace("\n", " ")[:80],
        "event": event,
        **details,
    }
    try:
        _GROWTH_ANOMALY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_GROWTH_ANOMALY_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _split_by_highlight(
    group: list[dict], highlight_rects: list[fitz.Rect]
) -> list[tuple[list[dict], bool]]:
    """Split `group`'s lines into consecutive runs of consistent
    highlighted/not-highlighted status (see _line_is_highlighted()),
    returned as (lines, highlighted) pairs in order. Returns the whole
    group as a single, non-highlighted run if there are no highlight_rects
    at all (the common case - most pages have no quote callouts).

    A single blank/whitespace-only line sitting between two runs that
    otherwise have the SAME status (e.g. a quote body and its "- PQ"
    attribution, both highlighted, separated by a blank line - confirmed by
    tests/manual_test_highlight_overlap.py) does not itself trigger a split:
    it's folded into that shared status instead of becoming its own
    (typically non-highlighted, since a bare gap rarely sits under a
    highlight rectangle) one-line run. A run of two or more consecutive
    blank lines, or a single blank line between two DIFFERING statuses, is
    not folded - it keeps its own directly-computed status.

    Known accepted limitation (not solved here): an attribution line
    without its own highlight rectangle (e.g. because the rectangle for the
    preceding quote body ends just before it) is measured like any other
    line and ends up in the non-highlighted run - see Backlog.md.
    """
    if not highlight_rects:
        return [(group, False)]

    raw_statuses = [
        _line_is_highlighted(fitz.Rect(*line["bbox"]), highlight_rects) for line in group
    ]
    is_blank = [not _line_text(line.get("spans", [])).strip() for line in group]

    merged_statuses = list(raw_statuses)
    for i in range(len(group)):
        if not is_blank[i]:
            continue
        prev_blank = i > 0 and is_blank[i - 1]
        next_blank = i + 1 < len(group) and is_blank[i + 1]
        if prev_blank or next_blank or i == 0 or i == len(group) - 1:
            continue  # part of a multi-blank run, or has no both-side neighbor to compare
        if raw_statuses[i - 1] == raw_statuses[i + 1]:
            merged_statuses[i] = raw_statuses[i - 1]

    runs: list[tuple[list[dict], bool]] = []
    current_lines: list[dict] = []
    current_status: bool | None = None
    for line, status in zip(group, merged_statuses):
        if current_status is not None and status != current_status:
            runs.append((current_lines, current_status))
            current_lines = []
        current_lines.append(line)
        current_status = status
    if current_lines:
        runs.append((current_lines, bool(current_status)))
    return runs


# Minimum overlap (pt), required on BOTH axes, between a line's bbox and
# a link annotation's rect for that line to count as "IS the link" - see
# _line_overlaps_link(). Without this, a coincidental sub-pixel/rounding-
# level sliver between an unrelated line and a neighboring link rectangle
# would wrongly count as a real overlap - confirmed in
# "1526 VIRELICON.pdf": a line starting at y0=194.90 sat a mere 0.02pt
# below an unrelated link rectangle ending at y1=194.92, which used to be
# enough (block_overlaps() has no tolerance) to mark that entire line's
# block non-translatable. Same category of false positive
# _HIGHLIGHT_LINE_TOLERANCE already guards against for quote-highlight
# rectangles.
_LINK_OVERLAP_TOLERANCE = 1.0


def _line_overlaps_link(
    line_bbox: fitz.Rect, link_bboxes: list[tuple[float, float, float, float]]
) -> bool:
    """Whether `line_bbox` meaningfully overlaps at least one of
    `link_bboxes` (from page.get_links(), collected once per page in
    extract_blocks()) by more than _LINK_OVERLAP_TOLERANCE on BOTH axes -
    the per-LINE counterpart of the whole-BLOCK check extract_blocks()
    used to run directly against a block's union bbox (see
    _split_by_link()'s docstring for why that was wrong). A 2D check
    (unlike _line_is_highlighted()'s vertical-only one) since a link's
    rect, unlike a highlight rectangle, does not necessarily span a
    line's full width.
    """
    for x0, y0, x1, y1 in link_bboxes:
        dx = min(line_bbox.x1, x1) - max(line_bbox.x0, x0)
        dy = min(line_bbox.y1, y1) - max(line_bbox.y0, y0)
        if dx > _LINK_OVERLAP_TOLERANCE and dy > _LINK_OVERLAP_TOLERANCE:
            return True
    return False


def _split_by_link(
    group: list[dict], link_bboxes: list[tuple[float, float, float, float]]
) -> list[tuple[list[dict], bool]]:
    """Split `group`'s lines into consecutive runs of consistent
    link/not-link overlap status (see _line_overlaps_link()), returned as
    (lines, is_link) pairs in order. Mirrors _split_by_highlight() exactly
    (same blank-line-merging rule and reasoning) but for link annotations
    instead of quote-highlight rectangles.

    Added because extract_blocks() used to mark an entire block
    non-translatable as soon as ANY of its lines overlapped a link
    annotation, even when the link only actually covered a single line
    inside an otherwise ordinary, much longer prose paragraph - confirmed
    by direct reproduction against "1526 VIRELICON.pdf": a live user run
    had a whole 6-line paragraph on page 2 skipped entirely because just
    one line inside it cited a Telegram post via an inline link, and only
    "a small part was carried over correctly" (a neighboring line
    coincidentally NOT overlapping any link, per _line_overlaps_link()'s
    tolerance note). See Backlog.md.

    Returns the whole group as a single, non-link run if there are no
    link_bboxes at all (the common case for most pages).
    """
    if not link_bboxes:
        return [(group, False)]

    raw_statuses = [
        _line_overlaps_link(fitz.Rect(*line["bbox"]), link_bboxes) for line in group
    ]
    is_blank = [not _line_text(line.get("spans", [])).strip() for line in group]

    merged_statuses = list(raw_statuses)
    for i in range(len(group)):
        if not is_blank[i]:
            continue
        prev_blank = i > 0 and is_blank[i - 1]
        next_blank = i + 1 < len(group) and is_blank[i + 1]
        if prev_blank or next_blank or i == 0 or i == len(group) - 1:
            continue  # part of a multi-blank run, or has no both-side neighbor to compare
        if raw_statuses[i - 1] == raw_statuses[i + 1]:
            merged_statuses[i] = raw_statuses[i - 1]

    runs: list[tuple[list[dict], bool]] = []
    current_lines: list[dict] = []
    current_status: bool | None = None
    for line, status in zip(group, merged_statuses):
        if current_status is not None and status != current_status:
            runs.append((current_lines, current_status))
            current_lines = []
        current_lines.append(line)
        current_status = status
    if current_lines:
        runs.append((current_lines, bool(current_status)))
    return runs


def _insert_bbox_for(
    lines: list[dict], bbox: tuple[float, float, float, float]
) -> tuple[float, float, float, float] | None:
    """Tighten bbox's y0 to the first non-blank line in `lines`.

    _build_text_spans() drops leading blank lines (they have no
    representable width/content once turned into spans/HTML), so inserting
    into bbox as-is - which spans every source line including any leading
    blank ones - would place text too high, inside space the blank lines
    used to occupy. Returns None (meaning "use bbox as-is") if the first
    line is already non-blank, or if - which should not happen for a block
    with any real text - no non-blank line is found.
    """
    first_nonblank = next(
        (line for line in lines if _line_text(line.get("spans", [])).strip()), None
    )
    if first_nonblank is None or first_nonblank is lines[0]:
        return None
    return (bbox[0], first_nonblank["bbox"][1], bbox[2], bbox[3])


def _line_is_all_bold(raw_spans: list[dict]) -> bool:
    """Whether every non-whitespace span on a line has the bold flag set.

    Purely whitespace spans (e.g. a trailing space with its own, reset
    formatting - common right after a styled run) are ignored, so they
    don't mask an otherwise fully bold heading line.
    """
    meaningful = [span for span in raw_spans if span["text"].strip()]
    return bool(meaningful) and all(
        bool(span.get("flags", 0) & _BOLD_FLAG) for span in meaningful
    )


def _needs_line_break(current_raw_spans: list[dict], next_raw_spans: list[dict]) -> bool:
    """Heuristic: keep a plain line break between two adjacent, non-blank
    lines that have no blank line between them in the source (which would
    otherwise become a PARAGRAPH_BREAK_MARKER - see _build_text_spans()).

    Triggers on either: (1) the bold status flips completely between the
    two lines (e.g. a bold heading immediately followed by normal body
    text), or (2) the current line ends in sentence-final punctuation
    (. ! ? :) while the next line starts with an uppercase letter.
    """
    if _line_is_all_bold(current_raw_spans) != _line_is_all_bold(next_raw_spans):
        return True
    current_text = _line_text(current_raw_spans).strip()
    next_text = _line_text(next_raw_spans).strip()
    return (
        bool(current_text)
        and bool(next_text)
        and current_text[-1] in ".!?:"
        and next_text[0].isupper()
    )


def _marker_span(marker_text: str) -> TextSpan:
    """Build a structural marker TextSpan (paragraph or line break); its
    formatting fields are unused placeholders.
    """
    return TextSpan(
        text=marker_text,
        font_name="",
        font_size=0.0,
        color=(0, 0, 0),
        bold=False,
        italic=False,
        underline=False,
    )


def _build_text_spans(group: list[dict]) -> list[TextSpan]:
    """Build the span-level formatting list for one group of lines.

    One TextSpan per PyMuPDF span on non-blank lines. A blank/whitespace-only
    line - a real paragraph break, confirmed by
    tests/manual_diagnose_paragraph_gaps.py - becomes a single
    PARAGRAPH_BREAK_MARKER TextSpan instead (and takes precedence: the line
    break heuristic below never runs across a blank line). Consecutive or
    leading/trailing blank lines collapse to at most one marker and never a
    leading/trailing one, mirroring PyMuPdfEngine.insert_text()'s paragraph
    regrouping.

    Between two adjacent non-blank lines with no blank line between them,
    _needs_line_break() decides whether to insert a LINE_BREAK_MARKER
    TextSpan (e.g. a bold heading directly followed by body text) instead
    of letting the lines merge freely on reflow.
    """
    text_spans: list[TextSpan] = []
    for index, line in enumerate(group):
        raw_spans = line.get("spans", [])
        line_text = _line_text(raw_spans)
        if line_text.strip():
            for span in raw_spans:
                flags = span.get("flags", 0)
                char_flags = span.get("char_flags", 0)
                text_spans.append(
                    TextSpan(
                        text=span["text"],
                        font_name=span.get("font", ""),
                        font_size=span.get("size", 0.0),
                        color=_parse_color(span.get("color", 0)),
                        bold=bool(flags & _BOLD_FLAG),
                        italic=bool(flags & _ITALIC_FLAG),
                        underline=bool(char_flags & _CHAR_UNDERLINE_FLAG),
                    )
                )
            next_line = group[index + 1] if index + 1 < len(group) else None
            if next_line is not None:
                next_raw_spans = next_line.get("spans", [])
                if _line_text(next_raw_spans).strip() and _needs_line_break(
                    raw_spans, next_raw_spans
                ):
                    text_spans.append(_marker_span(LINE_BREAK_MARKER))
        elif text_spans and text_spans[-1].text != PARAGRAPH_BREAK_MARKER:
            text_spans.append(_marker_span(PARAGRAPH_BREAK_MARKER))
    if text_spans and text_spans[-1].text in (PARAGRAPH_BREAK_MARKER, LINE_BREAK_MARKER):
        text_spans.pop()  # drop a trailing marker (group/blank-line end)
    return text_spans


def spans_to_html(spans: list[TextSpan]) -> str:
    """Build <p>-separated HTML from a TextBlock's spans for insert_htmlbox().

    A PARAGRAPH_BREAK_MARKER span starts a new <p>. A LINE_BREAK_MARKER span
    becomes a <br/> within the current <p> (a line break without the extra
    paragraph spacing). Other spans have their text HTML-escaped and wrapped
    in (nestable) <u>/<b>/<i> tags per their underline/bold/italic flags.
    """
    paragraphs: list[str] = []
    current: list[str] = []
    for span in spans:
        if span.text == PARAGRAPH_BREAK_MARKER:
            paragraphs.append("".join(current))
            current = []
            continue
        if span.text == LINE_BREAK_MARKER:
            current.append("<br/>")
            continue
        escaped = html.escape(span.text)
        if span.underline:
            escaped = f"<u>{escaped}</u>"
        if span.italic:
            escaped = f"<i>{escaped}</i>"
        if span.bold:
            escaped = f"<b>{escaped}</b>"
        current.append(escaped)
    paragraphs.append("".join(current))
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs if paragraph.strip())


def _regroup_paragraphs(text: str) -> list[str]:
    """Join each paragraph's wrapped lines into one reflowable line, but
    keep paragraphs separate wherever the source had a blank line - shared
    by PyMuPdfEngine._insert_plain_text() (rejoins with "\\n\\n" for
    insert_textbox()) and _plain_text_to_html() (wraps each in <p>, for
    the non-Latin-script fallback - see insert_text()'s docstring).
    """
    paragraphs: list[str] = []
    current_lines: list[str] = []
    for line in text.split("\n"):
        if line.strip():
            current_lines.append(line.strip())
        elif current_lines:
            paragraphs.append(" ".join(current_lines))
            current_lines = []
    if current_lines:
        paragraphs.append(" ".join(current_lines))
    return [re.sub(r" {2,}", " ", paragraph) for paragraph in paragraphs]


def _plain_text_needs_unicode_fallback(text: str) -> bool:
    """Whether `text` contains a character the Base-14 Helvetica variants
    in _FONT_VARIANTS (used by PyMuPdfEngine._insert_plain_text() via
    page.insert_textbox()) cannot represent.

    Base-14 fonts are fixed to WinAnsiEncoding, which covers ASCII plus
    Western-European accented Latin characters (e.g. "café", "Übung") but
    nothing outside the Latin-1 range - confirmed by direct reproduction:
    Cyrillic/Greek/CJK text inserted via insert_textbox(fontname="helv")
    silently comes out as literal "?" characters (mojibake), with
    insert_text() still reporting success (no exception, returns True) -
    see tests/test_pdf_glyph_preservation.py. `ord(ch) > 255` is a
    conservative (not 100% precise - WinAnsiEncoding has a few gaps even
    within 0-255) but safe heuristic: it only ever routes MORE text
    through the known-good HTML/Story fallback (see
    _plain_text_to_html()/insert_text()), never less.
    """
    return any(ord(ch) > 255 for ch in text)


def _plain_text_to_html(text: str) -> str:
    """Build the same shape of <p>-wrapped, HTML-escaped output as
    spans_to_html() would for equivalent plain text, for insert_text()'s
    non-Latin-script fallback (see _plain_text_needs_unicode_fallback()).
    Reuses _regroup_paragraphs() so paragraph/line-wrap handling matches
    _insert_plain_text() exactly - only the destination (HTML vs plain
    insert_textbox()) differs.
    """
    paragraphs = _regroup_paragraphs(text)
    return "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs if paragraph.strip())


def _max_rect_y1(page: fitz.Page, template: DocumentTemplate | None) -> float:
    """Height-fallback ceiling for rect.y1.

    _FOOTER_MARGIN pt above the template's footer_bbox if one is set,
    otherwise _FOOTER_MARGIN pt above the bottom page edge - so the
    height-growth fallback (in either insert_text() path) never grows the
    box into the footer zone or off the page.
    """
    if template is not None and template.footer_bbox is not None:
        return template.footer_bbox[1] - _FOOTER_MARGIN
    return page.rect.height - _FOOTER_MARGIN


def _insert_html_text(
    page: fitz.Page,
    rect: fitz.Rect,
    block: TextBlock,
    max_y1: float,
    translated_html: str | None = None,
) -> tuple[bool, fitz.Rect, float]:
    """Insert HTML into rect via page.insert_htmlbox().

    Uses `translated_html` (e.g. from GoogleTranslateProvider.translate_html())
    directly if given; otherwise builds untranslated HTML from block.spans
    via spans_to_html() (formatting-only fallback, same content as before).

    Growth (see try_grow() below) is tried FIRST, at the block's own
    original font size, before any shrinking - for EVERY block, not just
    highlighted ones (see below for why this used to be highlighted-only,
    and why it no longer is). Shrinking is only used as a last resort,
    once growth is maxed out (page edge / max_y1, already collision-aware
    - see PyMuPdfEngine._collision_aware_max_y1(), the caller) and still
    not enough - and then shrinks within the already-grown rect rather
    than restarting from the small original one.

    History/rationale: this growth-first order, its fine per-line step
    size (see _estimate_line_height()), and max_y1's collision-awareness
    were originally added only for block.highlighted - the reasoning back
    then was that a highlighted block's colored background grows right
    along with it (see PyMuPdfEngine._grow_highlight_if_needed()), so
    there's no normal-body-text concern about a fixed column layout, and a
    short, tightly-split one-line highlighted block (e.g. "- Ivan", "Ra")
    was found to have almost no slack, falling straight through to
    _MIN_FONT_SIZE (6pt) for a translation even slightly longer than the
    English original (tests/manual_diagnose_highlight_regression_output.txt).
    But the actual RISK the collision-aware ceiling exists to prevent -
    growing into the next block's own row once font-shrinking isn't
    checked against neighbors at all - is exactly as real for plain body
    text: tests/manual_diagnose_text_duplication.py reproduced a
    non-highlighted block growing 35pt into its neighbor's row under the
    old width-then-doubling order (_next_block_y0()/
    _collision_aware_max_y1() didn't apply to it), which is almost
    certainly the actual cause behind reported text
    duplication/truncation, unexplained attribution-line suffixes, and
    heading/bullet merging elsewhere in this document. So growth-before-
    shrink plus the collision boundary is now unconditional; only
    _grow_highlight_if_needed()'s colored-background redraw remains
    highlighted-only (a non-highlighted block has no background to redraw).

    insert_htmlbox() has no usable overflow-magnitude like insert_textbox's
    deficit (see insert_text() docstring for what was tried), so height is
    grown in fixed one-line-height steps (re-checking fit after each -
    doubling steps were found to overshoot a real one-extra-line deficit
    by a lot, e.g. 28.9pt -> 88.9pt, once growth started being tried this
    early) before falling back to widening, both capped at max_y1/max_x1
    so growth never runs into the next block, the footer zone, or the
    page edge. If even that's not enough, one final insert is forced at
    the capped rect so the text is never silently dropped.

    Returns (fit, rect, final_font_size): `rect` (the same object passed
    in, mutated in place as it's grown/shrunk) reflects the actual final
    rect the text was written into - used by insert_text() to detect,
    for a highlighted block, whether the text ended up taller than the
    block's original highlight rectangle(s) (see
    _grow_highlight_if_needed()), and for anomaly logging (see
    log_growth_anomaly()) for every block. `final_font_size` is likewise
    for anomaly logging.
    """
    content_html = translated_html if translated_html is not None else spans_to_html(block.spans)

    def fits(fontsize: float) -> bool:
        css = f"body {{font-family: sans-serif; font-size: {fontsize}pt;}}"
        spare_height, _ = page.insert_htmlbox(rect, content_html, css=css, scale_low=1)
        return spare_height >= 0

    max_x1 = page.rect.width - _PAGE_EDGE_MARGIN

    def try_grow(fontsize: float) -> bool | None:
        """Try growing rect.y1 (in fixed one-line-height steps - see
        _estimate_line_height() - up to max_y1) BEFORE widening rect.x1,
        at a fixed `fontsize`. Returns True if widening alone fit, False
        if height also had to grow (and did fit), or None if even maxed
        width+height isn't enough.
        """
        line_height = _estimate_line_height(block)
        while rect.y1 < max_y1:
            rect.y1 = min(rect.y1 + line_height, max_y1)
            if fits(fontsize):
                return False
        while rect.x1 < max_x1:
            rect.x1 = min(rect.x1 + _WIDTH_STEP, max_x1)
            if fits(fontsize):
                return False
        return None

    size = block.font_size
    if fits(size):
        return True, rect, size
    grown = try_grow(size)
    if grown is not None:
        return grown, rect, size
    # Growth alone (at the original font size) wasn't enough even at max
    # width/height - shrink within the now fully-grown rect instead of
    # restarting at the small original one.
    while size > _MIN_FONT_SIZE:
        size = max(size - _FONT_STEP, _MIN_FONT_SIZE)
        if fits(size):
            return False, rect, size
    # Reached the footer/page-edge/collision ceiling without fitting at
    # scale_low=1 even at the floor font size. A failed insert_htmlbox()
    # call writes nothing at all (like insert_textbox()), so fits() here
    # would silently drop the text - force a real write instead via
    # scale_low=0, which lets PyMuPDF auto-shrink the content as much as
    # needed to fit the capped rect.
    css = f"body {{font-family: sans-serif; font-size: {size}pt;}}"
    page.insert_htmlbox(rect, content_html, css=css, scale_low=0)
    return False, rect, size


class PyMuPdfEngine:
    """Implements pipeline.pdf.base.PdfEngine on top of PyMuPDF."""

    def __init__(self, template: DocumentTemplate | None = None) -> None:
        """Store an optional template used to exclude header/footer zones."""
        self._template = template
        self._doc: fitz.Document | None = None
        self._highlight_rects_cache: dict[int, list[fitz.Rect]] = {}
        self._page_blocks_cache: dict[int, list[TextBlock]] = {}
        self._original_links: dict[int, list[dict]] = {}

    def _get_page_highlight_rects(self, page: fitz.Page, page_index: int) -> list[fitz.Rect]:
        """Cached per-page _get_highlight_rects() lookup, shared between
        extract_blocks() and insert_text() so a page's highlight rectangles
        are only scanned via page.get_drawings() once per engine instance.
        Never invalidated: insert_text() only ever ADDS a highlight
        rectangle (see _grow_highlight_if_needed()), it never removes/moves
        one of the originals this cache holds, so the cached list stays
        correct for the lifetime of this engine/document.
        """
        if page_index not in self._highlight_rects_cache:
            self._highlight_rects_cache[page_index] = _get_highlight_rects(page)
        return self._highlight_rects_cache[page_index]

    def _collision_aware_max_y1(
        self, page: fitz.Page, block: TextBlock
    ) -> tuple[float, float | None]:
        """_max_rect_y1() (footer/page-edge cap), further capped by the y0
        of the nearest block below `block` in the same column (see
        _next_block_y0()) minus _HIGHLIGHT_COLLISION_MARGIN, using the
        ORIGINAL (pre-mutation) full-page block list cached by
        extract_blocks() in self._page_blocks_cache - so ANY block's
        height growth (see try_grow() in _insert_html_text()/
        _insert_plain_text()) never draws into a neighboring block's row.
        Applies to every block, not just highlighted ones (see
        _insert_html_text()'s docstring for why the growth-before-shrink
        order this feeds into used to be highlighted-only and no longer
        is). Relies on extract_blocks(page_index) having already been
        called once for this page (always true in practice: callers must
        call it to obtain the TextBlock passed to insert_text()/
        redact_block() in the first place) - falls back to just the
        footer/page-edge cap if the cache is somehow empty.

        For a highlighted block, the collision column uses the WIDE
        associated-highlight-rectangle extent (see
        _associated_highlight_extent()), not just the block's own narrow
        text bbox - matching the width redact_block()/
        _grow_highlight_if_needed() actually redact/redraw (see
        redact_block()'s docstring). Using only the narrow bbox here used
        to let a highlighted block's regrowth redraw its enlarged
        highlight background - which IS full highlight-column width -
        straight over a neighboring block sitting outside that narrow
        bbox but inside the wide column, with nothing capping the growth
        that made it happen; confirmed by direct reproduction (a short
        highlighted quote growing tall enough to paint its widened
        highlight-color background over an unrelated block's text several
        lines below it - see tests/test_pdf_overlay_collision.py) before
        this widened check was added.

        Returns (max_y1, next_y0): `next_y0` is the nearest block's own
        (un-margined) y0 - None if there's no block below in this column -
        used by _log_growth_anomalies() to tell whether growth actually
        reached the collision boundary specifically, as opposed to the
        footer/page-edge cap.
        """
        max_y1 = _max_rect_y1(page, self._template)
        page_blocks = self._page_blocks_cache.get(block.page_index, [])
        x_range: tuple[float, float] | None = None
        if block.highlighted:
            highlight_rects = self._get_page_highlight_rects(page, block.page_index)
            extent = _associated_highlight_extent(block.bbox, highlight_rects)
            if extent is not None:
                x_range = (min(block.bbox[0], extent.x0), max(block.bbox[2], extent.x1))
        next_y0 = _next_block_y0(block, page_blocks, x_range=x_range)
        if next_y0 is not None:
            max_y1 = min(max_y1, next_y0 - _HIGHLIGHT_COLLISION_MARGIN)
        return max_y1, next_y0

    def _log_growth_anomalies(
        self,
        block: TextBlock,
        original_rect: fitz.Rect,
        final_rect: fitz.Rect,
        final_font_size: float,
        max_y1: float,
        next_y0: float | None,
    ) -> None:
        """Check the outcome of _insert_html_text()/_insert_plain_text()
        for three anomaly conditions, logging each that applies via
        log_growth_anomaly() (tests/output/growth_anomalies.jsonl). A
        single insertion can trigger more than one. Called from
        insert_text() for every block, highlighted or not. `original_rect`
        is the rect BEFORE any growth/shrink attempt (a copy taken before
        _insert_html_text()/_insert_plain_text() mutate `rect` in place) -
        used as the "did this actually change" baseline, since block.bbox
        alone isn't reliable for that (a block sitting naturally close to
        the next one has final_rect.y1 near max_y1 even with zero growth,
        which the first version of this check misreported as capped).

        1. growth_capped_by_collision: height actually GREW past
           `original_rect` AND `final_rect` reached (within half a point
           of) the collision boundary from _collision_aware_max_y1() -
           i.e. there WAS a next block in this column and growth reached
           the ceiling that exists specifically to stay clear of it.
           Doesn't fire for a block that fit at its original size, even if
           that size already happened to sit close to the boundary.
        2. small_final_font: the font size that actually fit is at or
           below _GROWTH_ANOMALY_FONT_SIZE_THRESHOLD AND below the block's
           own original font_size (so a document that's naturally set in
           small type throughout isn't flagged - only actual shrinkage is).
        3. excessive_height_growth: final_rect's height is more than
           _GROWTH_ANOMALY_HEIGHT_RATIO times original_rect's height.
        """
        original_height = original_rect.y1 - original_rect.y0
        final_height = final_rect.y1 - final_rect.y0
        grew = final_rect.y1 > original_rect.y1 + 0.5

        if grew and next_y0 is not None and final_rect.y1 >= max_y1 - 0.5:
            log_growth_anomaly(
                block,
                "growth_capped_by_collision",
                {
                    "original_rect": [round(v, 1) for v in original_rect],
                    "final_rect": [round(v, 1) for v in final_rect],
                    "next_block_y0": round(next_y0, 1),
                    "capped_at_y1": round(max_y1, 1),
                },
            )

        if (
            final_font_size <= _GROWTH_ANOMALY_FONT_SIZE_THRESHOLD
            and final_font_size < block.font_size
        ):
            log_growth_anomaly(
                block,
                "small_final_font",
                {
                    "final_font_size": round(final_font_size, 2),
                    "original_font_size": round(block.font_size, 2),
                },
            )

        if original_height > 0 and final_height > _GROWTH_ANOMALY_HEIGHT_RATIO * original_height:
            log_growth_anomaly(
                block,
                "excessive_height_growth",
                {
                    "original_height": round(original_height, 1),
                    "final_height": round(final_height, 1),
                    "ratio": round(final_height / original_height, 2),
                },
            )

    def open(self, path: str) -> None:
        """Load a PDF document for processing.

        Snapshots every page's link annotations into self._original_links
        right after loading, before any redaction happens. redact_block()/
        _grow_highlight_if_needed() call page.apply_redactions(), which
        silently drops ANY annotation whose rect overlaps the redacted
        area - including link annotations belonging to a completely
        unrelated, non-translatable block that merely happens to sit near
        the redacted one. save() reconciles against this snapshot exactly
        once, after all redactions for the document are done, and restores
        anything that went missing (see save()'s docstring for why this
        has to happen there and not per-redaction: a link restored via
        page.insert_link() is invisible to page.get_links() for the rest
        of the live session, so a per-call restore can't detect a SECOND
        redaction later destroying the same link again).
        """
        self._doc = fitz.open(path)
        for page in self._doc:
            self._original_links[page.number] = page.get_links()

    def get_pages(self) -> list[PageInfo]:
        """Return metadata for all pages."""
        assert self._doc is not None, "Document not opened. Call open() first."
        pages: list[PageInfo] = []
        for index, page in enumerate(self._doc):
            rect = page.rect
            pages.append(PageInfo(index=index, width=rect.width, height=rect.height))
        return pages

    def extract_blocks(self, page_index: int) -> list[TextBlock]:
        """Extract paragraph-level text blocks from a page.

        Spans are grouped into one TextBlock per PyMuPDF block, using the
        block's bbox, combined text, and the first span's font/size/color/
        style as representative values. If a block's lines have a min/max x0
        spread over _COLUMN_SPLIT_THRESHOLD, the block is first split into
        sub-groups of lines with similar x0 (see _group_lines_by_x0), each
        becoming its own TextBlock with a tight bbox - this avoids a union
        bbox that spans a paragraph starting next to an image and continuing
        full-width below it. On page_index == 0, each such group is then
        further split on FIRST_PAGE_ANCHOR_TERMS (see
        _split_first_page_metadata()): a metadata chunk like "Issuer
        Address:" plus its address line, which would otherwise share one
        block with a following title/subtitle line, becomes its own
        non-translatable TextBlock, separate from the (normally
        translatable) rest. A block/group is marked non-translatable if it
        overlaps the template's header/footer zones, (on page_index == 0
        only) the template's first_page_zones, is the metadata half of a
        FIRST_PAGE_ANCHOR_TERMS split, or is a LINE-level run that overlaps
        a link annotation (see the next paragraph - NOT "the whole
        block/group contains a link anywhere", which is what this used to
        do). Blocks with only whitespace text are skipped. Each block's
        spans list is also populated (see _build_text_spans): one TextSpan
        per PyMuPDF span on real text lines, a PARAGRAPH_BREAK_MARKER
        TextSpan for each blank/whitespace-only source line (a genuine
        paragraph break), and a LINE_BREAK_MARKER TextSpan for a
        heading-like line transition worth keeping as a plain line break
        even without a blank line (see _needs_line_break()).

        Each such column-split group (after the page-0 metadata split, if
        any) is further split on highlighted/not-highlighted line runs (see
        _get_highlight_rects()/_split_by_highlight()): a run of lines
        sitting inside a quote-highlight rectangle becomes its own
        TextBlock with highlighted=True, separate from the surrounding
        non-highlighted text, even though both stay translatable=True (by
        default - see below) - highlighted is purely informational (for
        later styling), not itself a translation decision. Each such
        highlight run is THEN further split on link/not-link line runs
        (see _line_overlaps_link()/_split_by_link()): a run of lines
        overlapping a link annotation becomes its own, separate
        translatable=False TextBlock, rather than dragging the rest of a
        much longer surrounding paragraph down with it into
        non-translatable status - confirmed as a real bug via a live run
        against "1526 VIRELICON.pdf" (see _split_by_link()'s docstring).

        The returned list is also cached in self._page_blocks_cache - used
        by _collision_aware_max_y1() so a highlighted block's height growth
        knows where the next block on the page starts, without re-scanning
        the (by then possibly already redacted/re-translated) page.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[page_index]
        raw = page.get_text("dict", flags=_EXTRACT_FLAGS)
        highlight_rects = self._get_page_highlight_rects(page, page_index)

        link_bboxes: list[tuple[float, float, float, float]] = []
        for link in page.get_links():
            rect = link.get("from")
            if rect is not None:
                link_bboxes.append((rect.x0, rect.y0, rect.x1, rect.y1))

        blocks: list[TextBlock] = []
        for raw_block in raw.get("blocks", []):
            if raw_block.get("type") != 0:
                continue  # skip image blocks

            lines = raw_block.get("lines", [])
            if not lines:
                continue

            for group in _group_lines_by_x0(lines, _COLUMN_SPLIT_THRESHOLD):
                subgroups = (
                    _split_first_page_metadata(group, FIRST_PAGE_ANCHOR_TERMS)
                    if page_index == 0
                    else [group]
                )
                is_metadata_split = len(subgroups) == 2

                for subgroup_index, subgroup in enumerate(subgroups):
                    for run_lines, highlighted in _split_by_highlight(
                        subgroup, highlight_rects
                    ):
                        for link_lines, is_link in _split_by_link(run_lines, link_bboxes):
                            spans = [
                                span for line in link_lines for span in line.get("spans", [])
                            ]
                            if not spans:
                                continue

                            text = "\n".join(
                                "".join(span["text"] for span in line.get("spans", []))
                                for line in link_lines
                            ).strip()
                            if not text:
                                continue

                            first_span = spans[0]
                            color = _parse_color(first_span.get("color", 0))
                            flags = first_span.get("flags", 0)
                            bbox = _union_bbox([tuple(line["bbox"]) for line in link_lines])
                            insert_bbox = _insert_bbox_for(link_lines, bbox)
                            text_spans = _build_text_spans(link_lines)

                            translatable = not is_link
                            if translatable and self._template is not None:
                                header_bbox = self._template.header_bbox
                                footer_bbox = self._template.footer_bbox
                                if header_bbox is not None and block_overlaps(bbox, header_bbox):
                                    translatable = False
                                elif footer_bbox is not None and block_overlaps(bbox, footer_bbox):
                                    translatable = False

                            if (
                                translatable
                                and self._template is not None
                                and page_index == 0
                                and self._template.first_page_zones is not None
                                and any(
                                    block_overlaps(bbox, zone)
                                    for zone in self._template.first_page_zones
                                )
                            ):
                                translatable = False

                            if is_metadata_split and subgroup_index == 0:
                                translatable = False  # the anchor-term metadata chunk

                            blocks.append(
                                TextBlock(
                                    page_index=page_index,
                                    bbox=bbox,
                                    text=text,
                                    font_name=first_span.get("font", ""),
                                    font_size=first_span.get("size", 0.0),
                                    color=color,
                                    bold=bool(flags & _BOLD_FLAG),
                                    italic=bool(flags & _ITALIC_FLAG),
                                    translatable=translatable,
                                    spans=text_spans,
                                    insert_bbox=insert_bbox,
                                    highlighted=highlighted,
                                )
                            )

        self._page_blocks_cache[page_index] = blocks
        return blocks

    def extract_images(self, page_index: int) -> list[ImageBlock]:
        """Extract all raster images on a page, for collision checks and later
        image-translation (OCR + inpainting). Does not extract image content itself.

        Uses page.get_images(full=True) to enumerate the images referenced by
        the page, then page.get_image_rects(xref) to resolve their on-page
        position(s). An image can be embedded more than once (same xref, e.g.
        a repeated logo), in which case one ImageBlock is created per rect.
        Images without a resolvable rect are skipped.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[page_index]

        images: list[ImageBlock] = []
        for image_info in page.get_images(full=True):
            xref = image_info[0]
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            for rect in rects:
                images.append(
                    ImageBlock(
                        page_index=page_index,
                        bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                        xref=xref,
                    )
                )

        return images

    def replace_image(self, image: ImageBlock, new_image_bytes: bytes) -> None:
        """Replace an image's content in place, keeping its position and size.
        Used by the image-translation feature once OCR/inpainting is implemented.

        Delegates to page.replace_image(xref, stream=...), which swaps the
        object definition stored under the xref while leaving the page's
        appearance instructions (position, rotation, size) untouched.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[image.page_index]
        page.replace_image(image.xref, stream=new_image_bytes)

    def redact_block(self, block: TextBlock) -> None:
        """Cover the original text area of a block with a white-filled redaction.

        Uses block.insert_bbox (see TextBlock) rather than bbox when set:
        the redaction must not paint over more area than it needs to, or it
        also whites out neighboring vector elements (e.g. a separator line
        sitting in bbox's leading-blank-line space) that are meant to stay
        untouched.

        For a highlighted block (block.highlighted), the redaction's WIDTH
        instead spans the full width of its associated highlight
        rectangle(s) (see _associated_highlight_extent()), not just the
        block's own text extent. The quote-highlight background is
        column-wide regardless of how much of that width any one line's
        text actually occupies - confirmed via
        tests/manual_diagnose_highlight_regression_output.txt: redacting
        only the (often much narrower, single-word/short-phrase) block
        width left a white hole under the text with an untouched, wider
        blue band around it, i.e. the text ended up sitting on white while
        empty space nearby stayed highlighted. Height still comes from
        block.insert_bbox/bbox as before (or whatever
        _grow_highlight_if_needed() grows it to afterward) - only the
        width changes here, and only for a highlighted block.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[block.page_index]
        rect = fitz.Rect(*(block.insert_bbox if block.insert_bbox is not None else block.bbox))

        if block.highlighted:
            highlight_rects = self._get_page_highlight_rects(page, block.page_index)
            extent = _associated_highlight_extent(block.bbox, highlight_rects)
            if extent is not None:
                rect.x0 = min(rect.x0, extent.x0)
                rect.x1 = max(rect.x1, extent.x1)

        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions()

    def insert_text(
        self,
        block: TextBlock,
        text: str,
        font_size: float,
        translated_html: str | None = None,
    ) -> bool:
        """Insert translated text into a block's area.

        If block.spans is non-empty, inserts HTML via page.insert_htmlbox()
        (see spans_to_html()/_insert_html_text()) so mixed formatting within
        one block (e.g. a bold sub-heading followed by normal body text) is
        preserved. If `translated_html` is given, it is used as-is (this is
        how an already-translated, formatting-preserving result - e.g. from
        GoogleTranslateProvider.translate_html() - gets inserted; `text` is
        then ignored). Otherwise the HTML is built from block.spans via
        spans_to_html(): each PARAGRAPH_BREAK_MARKER span starts a new <p>,
        each LINE_BREAK_MARKER span becomes a <br/> within the current <p>
        (line break without extra paragraph spacing, e.g. heading directly
        followed by body text with no blank line between them), others
        become escaped text in nestable <b>/<i> tags per their bold/italic
        flags - this is the untranslated, formatting-only fallback (`text`
        is still ignored in this branch too). CSS uses block.font_size as
        the starting size and a generic "sans-serif" font-family: MuPDF's
        Story/CSS engine resolves generic families - and their bold/italic
        variants - internally, so unlike the plain-text path below no
        per-style Base-14 fontname lookup is needed.

        If block.spans is empty (backward compatibility) AND `text` is
        representable in WinAnsiEncoding, falls back to the original path
        below: text is first normalized, before any fit attempt, by
        splitting it on \\n and regrouping into paragraphs:
        consecutive non-blank lines (wrap artifacts from the source PDF's
        original, narrower per-line extraction) are joined with a single
        space so insert_textbox() can freely reflow them, while a
        blank/whitespace-only line - confirmed by
        tests/manual_diagnose_paragraph_gaps.py to mark a real paragraph
        break in the source - is preserved as a blank line ("\\n\\n")
        between paragraphs so the gap survives reinsertion. Every fit
        attempt reasons about this same normalized text.

        If block.spans is empty but `text` contains a character outside
        WinAnsiEncoding - i.e. any non-Latin script (see
        _plain_text_needs_unicode_fallback()) - the plain-text path above
        is skipped even though spans is empty, and the HTML/Story engine
        is used instead (via _plain_text_to_html()): the Base-14
        Helvetica variants the plain path uses cannot represent non-Latin
        scripts at all and silently substitute "?" for every such
        character (confirmed by direct reproduction - real data loss, not
        just a font mismatch - since insert_textbox() has no way to
        signal this back to the caller). This only matters if this
        backward-compatibility path is ever exercised with non-Latin
        target text; translate_pdf()'s real callers always populate
        block.spans, so this only guards a currently-unused-in-production
        path against silent corruption if that ever changes.

        Both paths share the same fit fallback for a NON-highlighted block:
        starts at font_size (or, HTML path, block.font_size) and tries
        growth FIRST (see _insert_html_text()'s/_insert_plain_text()'s
        try_grow()): height, in fixed one-line-height steps (see
        _estimate_line_height()), then width, both capped so growth never
        runs into the next block on the page (see
        _collision_aware_max_y1()/_next_block_y0()), the footer zone, or
        the page edge. Only once growth is maxed out and still not enough
        does it shrink the font in _FONT_STEP steps down to _MIN_FONT_SIZE,
        within the already-grown (collision-safe) rect rather than
        restarting at the small original one. If even the floor font size
        doesn't fit at the capped rect, one final insert is forced there
        so the text is never silently dropped. Returns True if it fit
        without any growth or shrinking, False otherwise.

        This growth-first, collision-capped order applies to every block,
        not just highlighted ones - see _insert_html_text()'s docstring
        for why it used to be highlighted-only and why it no longer is
        (tests/manual_diagnose_text_duplication.py reproduced a
        non-highlighted block growing 35pt into its neighbor's row under
        the old order). Every insertion is also checked for growth
        anomalies (collision-capped, tiny final font, excessive height
        growth) and logged via log_growth_anomaly() - see
        _log_growth_anomalies() - regardless of block.highlighted.

        For a highlighted block (block.highlighted) specifically, if the
        text actually needed more vertical space than the block's original
        highlight rectangle(s) covered, the quote-highlight background is
        also redrawn taller to match - see _grow_highlight_if_needed() -
        so translated text never ends up partly sitting on a plain white
        background. Does nothing extra for a non-highlighted block, which
        has no colored background to redraw.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[block.page_index]
        # insert_bbox (see TextBlock), not bbox, is the actual insertion
        # target: bbox may include leading blank source lines that
        # _build_text_spans() drops, and inserting into bbox as-is would
        # then place text too high, inside the space those lines used to
        # occupy.
        rect = fitz.Rect(*(block.insert_bbox if block.insert_bbox is not None else block.bbox))
        original_rect = fitz.Rect(rect)  # snapshot before growth/shrink mutate rect in place

        original_highlight_extent: fitz.Rect | None = None
        if block.highlighted:
            highlight_rects = self._get_page_highlight_rects(page, block.page_index)
            original_highlight_extent = _associated_highlight_extent(block.bbox, highlight_rects)

        # Collision-aware for every block (see _collision_aware_max_y1()) -
        # growth must never draw into the next block's own row, whether or
        # not this block is highlighted.
        max_y1, next_y0 = self._collision_aware_max_y1(page, block)

        if block.spans:
            fit, final_rect, final_font_size = _insert_html_text(page, rect, block, max_y1, translated_html)
        elif translated_html is None and _plain_text_needs_unicode_fallback(text):
            # The Base-14 Helvetica variants _insert_plain_text() uses
            # (_FONT_VARIANTS) are fixed to WinAnsiEncoding and silently
            # corrupt non-Latin-script text into "?" characters (confirmed
            # by direct reproduction - see
            # _plain_text_needs_unicode_fallback()'s docstring and
            # tests/test_pdf_glyph_preservation.py). The HTML/Story engine
            # does automatic Unicode font fallback and handles this
            # correctly, so route through it instead of the plain path.
            fit, final_rect, final_font_size = _insert_html_text(
                page, rect, block, max_y1, _plain_text_to_html(text)
            )
        else:
            fit, final_rect, final_font_size = self._insert_plain_text(
                page, rect, block, text, font_size, max_y1
            )

        self._log_growth_anomalies(block, original_rect, final_rect, final_font_size, max_y1, next_y0)

        if original_highlight_extent is not None:
            self._grow_highlight_if_needed(
                page, block, original_highlight_extent, final_rect, font_size, text, translated_html
            )

        return fit

    def _insert_plain_text(
        self,
        page: fitz.Page,
        rect: fitz.Rect,
        block: TextBlock,
        text: str,
        font_size: float,
        max_y1: float,
    ) -> tuple[bool, fitz.Rect, float]:
        """Plain-text fallback path for insert_text() (block.spans empty) -
        see insert_text()'s docstring for the paragraph-regrouping
        implemented here.

        Growth (see try_grow() below) is tried FIRST at the original
        font_size, before any shrinking, and shrinking (if growth alone
        isn't enough) happens within the already-grown rect - for EVERY
        block now, not just highlighted ones - see
        _insert_html_text()'s docstring for the full rationale (this path
        exists only for block.spans backward-compatibility, but the two
        behave consistently).

        `max_y1` is the height-growth ceiling (passed in by insert_text(),
        collision-aware - see _collision_aware_max_y1()), used by
        try_grow() below instead of computing its own via _max_rect_y1().

        Returns (fit, rect, final_font_size): `rect` is mutated in place
        as it's grown/shrunk, so by return it reflects the actual final
        rect the text was written into - used by insert_text() to detect,
        for a highlighted block, whether the text ended up taller than the
        block's original highlight rectangle(s) (see
        _grow_highlight_if_needed()), and, for every block, for anomaly
        logging (see log_growth_anomaly()). `final_font_size` is likewise
        for anomaly logging.
        """
        fontname = _FONT_VARIANTS[(block.bold, block.italic)]
        color = tuple(component / 255 for component in block.color)

        # Regroup into paragraphs: join each paragraph's wrapped lines into
        # one reflowable line, but keep a blank line between paragraphs so
        # insert_textbox() still shows the original paragraph spacing.
        text = "\n\n".join(_regroup_paragraphs(text)).strip()

        def insert_at(size: float) -> float:
            return page.insert_textbox(rect, text, fontsize=size, fontname=fontname, color=color)

        max_x1 = page.rect.width - _PAGE_EDGE_MARGIN

        def try_grow(size: float, deficit: float) -> tuple[bool, float]:
            """Grow rect.y1 by the reported deficit (capped at max_y1 -
            collision-aware, see _collision_aware_max_y1()) BEFORE
            widening rect.x1. insert_textbox()'s deficit already reflects
            the height shortfall AT THE CURRENT WIDTH, so growing height
            by that amount is the direct fix (no doubling needed here,
            unlike _insert_html_text()'s try_grow() - insert_textbox()
            reports an exact deficit, insert_htmlbox() doesn't); widening
            is only tried afterward, if height alone (capped at max_y1)
            still isn't enough. Capping at max_y1 means this single jump
            may still leave a negative deficit if the collision boundary
            (or footer/page edge) is reached first - the caller falls
            back to font-shrinking within this same (collision-safe) rect
            in that case, rather than drawing over the next block's row.
            Returns (fit, deficit): fit=True only if widening alone fixed
            it (matching insert_text()'s True="shrink/widen alone"
            convention) - fit=False if height had to grow too.
            """
            rect.y1 = min(rect.y1 + (-deficit), max_y1)
            deficit = insert_at(size)
            if deficit >= 0:
                return False, deficit
            while deficit < 0 and rect.x1 < max_x1:
                rect.x1 = min(rect.x1 + _WIDTH_STEP, max_x1)
                deficit = insert_at(size)
            return False, deficit

        size = font_size
        deficit = insert_at(size)
        if deficit >= 0:
            return True, rect, size
        _, deficit = try_grow(size, deficit)
        if deficit >= 0:
            return False, rect, size  # grew (height, and maybe also width) and fit

        # Growth alone (at the original font size) wasn't enough even at
        # max width/height - shrink within the now fully-grown rect
        # instead of restarting at the small original one.
        while size > _MIN_FONT_SIZE and deficit < 0:
            size = max(size - _FONT_STEP, _MIN_FONT_SIZE)
            deficit = insert_at(size)
        # insert_textbox() has no auto-scale option, so force a real write
        # by shrinking the font further (below _MIN_FONT_SIZE, for this
        # final call only) until it fits; guaranteed to terminate since
        # any finite text fits a fixed-size rect at a small enough font
        # size.
        while deficit < 0:
            size /= 2
            deficit = insert_at(size)
        return False, rect, size

    def _grow_highlight_if_needed(
        self,
        page: fitz.Page,
        block: TextBlock,
        original_extent: fitz.Rect,
        final_rect: fitz.Rect,
        font_size: float,
        text: str,
        translated_html: str | None,
    ) -> None:
        """Redraw a highlighted block's quote-highlight background taller
        if the actually-inserted text (`final_rect`, from
        _insert_html_text()/_insert_plain_text()) extends past the bottom
        of its original highlight rectangle(s) (`original_extent`, see
        _associated_highlight_extent()) by more than
        _HIGHLIGHT_GROW_TOLERANCE. Does nothing - existing rectangles stay
        exactly as in the original PDF - if the original height already
        covers the actual text.

        PyMuPDF's insert_htmlbox()/insert_textbox() only WRITE when they
        successfully fit (see insert_text()'s docstring) - there is no
        non-destructive "measure only" mode - so growth can only be
        detected after the fact, once the text is already written without
        a taller background behind it. When growth is needed: (1) the
        just-written text is undone via a white-fill redaction over
        final_rect, (2) the enlarged highlight rectangle is drawn (from
        original_extent's top to the new required bottom, and at least the
        original block's full width - see new_highlight_rect below) so it
        ends up BEHIND the text once (3) the text is re-inserted at the
        same final_rect - which fits on the first try this time, since it
        is already exactly the size that worked.
        """
        needed_y1 = final_rect.y1
        if needed_y1 <= original_extent.y1 + _HIGHLIGHT_GROW_TOLERANCE:
            return  # original highlight already covers the actual text

        page.add_redact_annot(final_rect, fill=(1, 1, 1))
        page.apply_redactions()

        # x0/x1 use original_extent (the associated highlight rects' own,
        # column-wide span - see _associated_highlight_extent()), not just
        # block.bbox: a highlighted block's own text extent is usually far
        # narrower than the full highlight column (that's the whole reason
        # redact_block() also widens to original_extent for highlighted
        # blocks - see its docstring), so anchoring the redrawn rect to
        # block.bbox alone reintroduced that same narrow-highlight defect
        # here (confirmed via tests/manual_verify_highlight_fixes.py).
        # final_rect.x1 is included too in case the fit fallback also had
        # to widen the box before growing its height (an extreme overflow,
        # e.g. verified via tests/manual_test_highlight_growth.py by
        # forcing a ~7x-longer placeholder): using only original_extent's
        # width there could still leave part of the text past the redrawn
        # background's right edge - exactly the "text pokes out past the
        # highlight" outcome this method exists to prevent.
        new_highlight_rect = fitz.Rect(
            min(block.bbox[0], original_extent.x0),
            original_extent.y0,
            max(block.bbox[2], original_extent.x1, final_rect.x1),
            needed_y1,
        )
        page.draw_rect(new_highlight_rect, color=None, fill=_HIGHLIGHT_FILL_COLOR, width=0)

        # Re-insertion should fit on the first try at final_rect's already-
        # determined size, so this max_y1 is only a defensive backstop;
        # still collision-aware for consistency with the original attempt.
        max_y1, _ = self._collision_aware_max_y1(page, block)
        if block.spans:
            _insert_html_text(page, fitz.Rect(final_rect), block, max_y1, translated_html)
        else:
            self._insert_plain_text(page, fitz.Rect(final_rect), block, text, font_size, max_y1)

    @staticmethod
    def _link_identity(link: dict) -> tuple:
        """Comparable key for a get_links() dict, ignoring the 'xref' key
        (which page.insert_link() assigns fresh and which therefore never
        matches between the open()-time snapshot and a later live read).
        Rect coordinates are rounded to absorb float noise introduced by
        PyMuPDF round-tripping the rect through the page's content stream.
        """
        rect = link.get("from")
        rect_key = (
            round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)
        ) if rect is not None else None
        return (
            rect_key,
            link.get("kind"),
            link.get("uri"),
            link.get("page"),
            link.get("to"),
        )

    def _restore_missing_links(self) -> None:
        """Reconciles every page's live links against the open()-time
        snapshot (self._original_links) and re-inserts anything that a
        page.apply_redactions() call destroyed as a side effect of
        redacting an unrelated, overlapping block. Must run exactly once,
        right before the final self._doc.save() - see open()'s docstring
        for why restoring per-redaction instead is unsafe.
        """
        assert self._doc is not None
        for page in self._doc:
            original = self._original_links.get(page.number, [])
            if not original:
                continue
            current_identities = {self._link_identity(link) for link in page.get_links()}
            for link in original:
                if self._link_identity(link) not in current_identities:
                    # 'xref' and 'id' identify the ORIGINAL annotation object,
                    # which apply_redactions() already deleted; insert_link()
                    # must create a fresh one, and (for 'id') a stale value
                    # instead raises KeyError deep inside PyMuPDF's own
                    # id-collision check (it looks up lnk["xref"] whenever
                    # lnk.get("id") is truthy).
                    restored = {k: v for k, v in link.items() if k not in ("xref", "id")}
                    page.insert_link(restored)

    def save(self, path: str) -> None:
        """Write the resulting PDF to disk.

        Uses full garbage collection (purges objects orphaned by
        redact_block()'s apply_redactions()) and deflate compression,
        appropriate for a document that went through redaction and text
        insertion. Overwriting the originally opened file in place is not
        supported: PyMuPDF only allows that via an incremental save, which
        is incompatible with garbage collection, so this raises ValueError
        instead of silently skipping cleanup or writing a bloated file.

        Before writing, reconciles link annotations via
        _restore_missing_links() - see open()'s docstring for why this
        happens once here rather than after each redaction.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        if path == self._doc.name:
            raise ValueError(
                "Cannot save to the original path in place; save to a "
                "different path. PyMuPDF requires an incremental save to "
                "overwrite the source file, which is incompatible with "
                "garbage collection after redactions."
            )
        self._restore_missing_links()
        self._doc.save(path, garbage=4, deflate=True)
