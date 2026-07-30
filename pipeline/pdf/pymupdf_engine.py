"""PdfEngine implementation backed by PyMuPDF (fitz).

This is the only file in the project allowed to import fitz/PyMuPDF.
"""
from __future__ import annotations

import html
import re

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
                text_spans.append(
                    TextSpan(
                        text=span["text"],
                        font_name=span.get("font", ""),
                        font_size=span.get("size", 0.0),
                        color=_parse_color(span.get("color", 0)),
                        bold=bool(flags & _BOLD_FLAG),
                        italic=bool(flags & _ITALIC_FLAG),
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


def _spans_to_html(spans: list[TextSpan]) -> str:
    """Build <p>-separated HTML from a TextBlock's spans for insert_htmlbox().

    A PARAGRAPH_BREAK_MARKER span starts a new <p>. A LINE_BREAK_MARKER span
    becomes a <br/> within the current <p> (a line break without the extra
    paragraph spacing). Other spans have their text HTML-escaped and wrapped
    in (nestable) <b>/<i> tags per their bold/italic flags.
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
        if span.italic:
            escaped = f"<i>{escaped}</i>"
        if span.bold:
            escaped = f"<b>{escaped}</b>"
        current.append(escaped)
    paragraphs.append("".join(current))
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs if paragraph.strip())


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
    page: fitz.Page, rect: fitz.Rect, block: TextBlock, max_y1: float
) -> bool:
    """Insert block.spans as HTML into rect via page.insert_htmlbox().

    Applies the same font-shrink -> width-widen -> height-grow fallback as
    PyMuPdfEngine.insert_text()'s plain-text path, reusing the same
    _FONT_STEP/_MIN_FONT_SIZE/_WIDTH_STEP/_PAGE_EDGE_MARGIN constants.
    insert_htmlbox() has no usable overflow-magnitude like insert_textbox's
    deficit (see insert_text() docstring for what was tried), so once at
    floor font size and max width, height is grown in doubling steps -
    capped at max_y1 (see _max_rect_y1()) so it never reaches the footer
    zone or page edge - until it fits. If even max_y1 isn't enough, one
    final insert is forced at the capped rect so the text is never silently
    dropped.
    """
    content_html = _spans_to_html(block.spans)

    def fits(fontsize: float) -> bool:
        css = f"body {{font-family: sans-serif; font-size: {fontsize}pt;}}"
        spare_height, _ = page.insert_htmlbox(rect, content_html, css=css, scale_low=1)
        return spare_height >= 0

    size = block.font_size
    while True:
        if fits(size):
            return True
        if size <= _MIN_FONT_SIZE:
            break
        size = max(size - _FONT_STEP, _MIN_FONT_SIZE)

    max_x1 = page.rect.width - _PAGE_EDGE_MARGIN
    while rect.x1 < max_x1:
        rect.x1 = min(rect.x1 + _WIDTH_STEP, max_x1)
        if fits(size):
            return True

    growth = _WIDTH_STEP
    while rect.y1 < max_y1:
        rect.y1 = min(rect.y1 + growth, max_y1)
        if fits(size):
            return False
        growth *= 2

    # Reached the footer/page-edge ceiling without fitting at scale_low=1.
    # A failed insert_htmlbox() call writes nothing at all (like
    # insert_textbox()), so fits() here would silently drop the text -
    # force a real write instead via scale_low=0, which lets PyMuPDF
    # auto-shrink the content as much as needed to fit the capped rect.
    css = f"body {{font-family: sans-serif; font-size: {size}pt;}}"
    page.insert_htmlbox(rect, content_html, css=css, scale_low=0)
    return False


class PyMuPdfEngine:
    """Implements pipeline.pdf.base.PdfEngine on top of PyMuPDF."""

    def __init__(self, template: DocumentTemplate | None = None) -> None:
        """Store an optional template used to exclude header/footer zones."""
        self._template = template
        self._doc: fitz.Document | None = None

    def open(self, path: str) -> None:
        """Load a PDF document for processing."""
        self._doc = fitz.open(path)

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
        full-width below it. A block/group is marked non-translatable if it
        overlaps a link annotation, the template's header/footer zones, or
        (on page_index == 0 only) the template's first_page_zones. Blocks
        with only whitespace text are skipped. Each block's spans list is
        also populated (see _build_text_spans): one TextSpan per PyMuPDF
        span on real text lines, a PARAGRAPH_BREAK_MARKER TextSpan for each
        blank/whitespace-only source line (a genuine paragraph break), and a
        LINE_BREAK_MARKER TextSpan for a heading-like line transition worth
        keeping as a plain line break even without a blank line (see
        _needs_line_break()).
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[page_index]
        raw = page.get_text("dict")

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
                spans = [span for line in group for span in line.get("spans", [])]
                if not spans:
                    continue

                text = "\n".join(
                    "".join(span["text"] for span in line.get("spans", []))
                    for line in group
                ).strip()
                if not text:
                    continue

                first_span = spans[0]
                color = _parse_color(first_span.get("color", 0))
                flags = first_span.get("flags", 0)
                bbox = _union_bbox([tuple(line["bbox"]) for line in group])
                text_spans = _build_text_spans(group)

                translatable = not any(
                    block_overlaps(bbox, link_bbox) for link_bbox in link_bboxes
                )
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
                    )
                )

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
        """Cover the original text area of a block with a white-filled redaction."""
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[block.page_index]
        page.add_redact_annot(fitz.Rect(*block.bbox), fill=(1, 1, 1))
        page.apply_redactions()

    def insert_text(self, block: TextBlock, text: str, font_size: float) -> bool:
        """Insert translated text into a block's area.

        If block.spans is non-empty, renders it as HTML via
        page.insert_htmlbox() (see _spans_to_html()/_insert_html_text()) so
        mixed formatting within one block (e.g. a bold sub-heading followed
        by normal body text) is preserved - each PARAGRAPH_BREAK_MARKER span
        starts a new <p>, each LINE_BREAK_MARKER span becomes a <br/> within
        the current <p> (line break without extra paragraph spacing, e.g.
        heading directly followed by body text with no blank line between
        them), others become escaped text in nestable <b>/<i> tags per
        their bold/italic flags. CSS uses block.font_size as the
        starting size and a generic "sans-serif" font-family: MuPDF's
        Story/CSS engine resolves generic families - and their bold/italic
        variants - internally, so unlike the plain-text path below no
        per-style Base-14 fontname lookup is needed. NOTE: for this step,
        span.text (the original/placeholder text already on the block) is
        what gets rendered - the text/font_size parameters are only used by
        the plain-text fallback path; wiring real per-span translated text
        through is future work.

        If block.spans is empty (backward compatibility), falls back to the
        original path below: text is first normalized, before any fit
        attempt, by splitting it on \\n and regrouping into paragraphs:
        consecutive non-blank lines (wrap artifacts from the source PDF's
        original, narrower per-line extraction) are joined with a single
        space so insert_textbox() can freely reflow them, while a
        blank/whitespace-only line - confirmed by
        tests/manual_diagnose_paragraph_gaps.py to mark a real paragraph
        break in the source - is preserved as a blank line ("\\n\\n")
        between paragraphs so the gap survives reinsertion. Every fit
        attempt reasons about this same normalized text.

        Both paths share the same fit fallback: starts at font_size (or,
        HTML path, block.font_size) and shrinks it in _FONT_STEP steps down
        to _MIN_FONT_SIZE while the insert call reports insufficient space.
        If it still overflows at the floor size, the box is widened in
        _WIDTH_STEP steps toward the right page edge (up to
        _PAGE_EDGE_MARGIN pt from it) - useful for a narrow column block
        (e.g. text next to an image) that has more room to the right than
        below. No neighboring-block collision check is done for this
        widening. Only if the box is at max width and still overflows is
        its height grown - by the exact remaining deficit for the
        plain-text path, or (HTML path, since insert_htmlbox() doesn't
        report a usable deficit) in doubling steps until it fits - capped
        at _max_rect_y1() (_FOOTER_MARGIN pt above self._template's
        footer_bbox, or above the bottom page edge if there's no template/
        footer_bbox) so this growth never runs into the footer zone or off
        the page. If even that capped height isn't enough, one final insert
        is forced at the capped rect so the text is never silently dropped.
        Returns True if it fit (via shrinking and/or widening alone),
        False if the height also had to be grown.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[block.page_index]
        rect = fitz.Rect(*block.bbox)

        if block.spans:
            max_y1 = _max_rect_y1(page, self._template)
            return _insert_html_text(page, rect, block, max_y1)

        fontname = _FONT_VARIANTS[(block.bold, block.italic)]
        color = tuple(component / 255 for component in block.color)

        # Regroup into paragraphs: join each paragraph's wrapped lines into
        # one reflowable line, but keep a blank line between paragraphs so
        # insert_textbox() still shows the original paragraph spacing.
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

        text = "\n\n".join(
            re.sub(r" {2,}", " ", paragraph) for paragraph in paragraphs
        ).strip()

        size = font_size
        while True:
            deficit = page.insert_textbox(
                rect, text, fontsize=size, fontname=fontname, color=color
            )
            if deficit >= 0:
                return True
            if size <= _MIN_FONT_SIZE:
                max_x1 = page.rect.width - _PAGE_EDGE_MARGIN
                while deficit < 0 and rect.x1 < max_x1:
                    rect.x1 = min(rect.x1 + _WIDTH_STEP, max_x1)
                    deficit = page.insert_textbox(
                        rect, text, fontsize=size, fontname=fontname, color=color
                    )
                if deficit >= 0:
                    return True

                max_y1 = _max_rect_y1(page, self._template)
                rect.y1 = min(rect.y1 + (-deficit), max_y1)
                deficit = page.insert_textbox(
                    rect, text, fontsize=size, fontname=fontname, color=color
                )
                # Capping at max_y1 may leave the box still too small for
                # `size`. A failed insert_textbox() call writes nothing at
                # all, so - unlike the uncapped case, where growing by the
                # exact deficit always succeeds - the text could be
                # silently dropped here. insert_textbox() has no auto-scale
                # option, so force a real write by shrinking the font
                # further (below _MIN_FONT_SIZE, for this final call only)
                # until it fits; guaranteed to terminate since any finite
                # text fits a fixed-size rect at a small enough font size.
                while deficit < 0:
                    size /= 2
                    deficit = page.insert_textbox(
                        rect, text, fontsize=size, fontname=fontname, color=color
                    )
                return False
            size = max(size - _FONT_STEP, _MIN_FONT_SIZE)

    def save(self, path: str) -> None:
        """Write the resulting PDF to disk.

        Uses full garbage collection (purges objects orphaned by
        redact_block()'s apply_redactions()) and deflate compression,
        appropriate for a document that went through redaction and text
        insertion. Overwriting the originally opened file in place is not
        supported: PyMuPDF only allows that via an incremental save, which
        is incompatible with garbage collection, so this raises ValueError
        instead of silently skipping cleanup or writing a bloated file.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        if path == self._doc.name:
            raise ValueError(
                "Cannot save to the original path in place; save to a "
                "different path. PyMuPDF requires an incremental save to "
                "overwrite the source file, which is incompatible with "
                "garbage collection after redactions."
            )
        self._doc.save(path, garbage=4, deflate=True)
