"""Regression coverage for a real bug found via a live user run against
"1526 VIRELICON.pdf" (see RoadMap.md Phase 2/PDF and Backlog.md): the
first content paragraph on page 2 was skipped entirely - "nur ein
kleiner Teil wurde korrekt übertragen" (only a small part was carried
over correctly) - because ONE line inside a much longer, otherwise
ordinary paragraph cited a Telegram post via an inline link annotation.

PyMuPdfEngine.extract_blocks() used to compute translatable by checking
whether a block's WHOLE union bbox overlapped ANY link annotation
(`translatable = not any(block_overlaps(bbox, link_bbox) ...)`), which
correctly excludes a genuinely link-only block (e.g.
tests/fixtures/representative.pdf's link-annotated paragraph, still
covered by tests/test_pdf_job.py/tests/test_pdf_link_preservation.py) but
also wrongly excluded an entire multi-line paragraph just because one of
its lines happened to sit under a link rectangle - real prose lines with
no link nearby were silently dropped from translation right along with
the one line that actually was the citation.

Fixed via _split_by_link()/_line_overlaps_link(), mirroring the existing
_split_by_highlight()/_line_is_highlighted() pattern exactly: a run of
lines overlapping a link annotation now becomes its own, separate
non-translatable TextBlock, while the surrounding lines of the same
original paragraph stay translatable. _line_overlaps_link() also adds a
tolerance (_LINK_OVERLAP_TOLERANCE), the link counterpart of
_HIGHLIGHT_LINE_TOLERANCE: a real document (see this module's second
test) had a line sitting a mere 0.02pt below an UNRELATED link
rectangle - without a tolerance, that coincidental floating-point sliver
alone would have wrongly excluded the line too.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

_PARAGRAPH = (
    "First line of a longer paragraph.\n"
    "Second line cites a source inline.\n"
    "Third line continues normally."
)


def _build_paragraph_with_link(path: Path, link_rect: fitz.Rect) -> None:
    """A 3-line, single-paragraph block plus one link annotation at
    `link_rect` - callers position it either squarely over the middle
    line (the common real-world "inline citation" case) or with a
    hairline sliver into a neighboring line (the coincidental-overlap
    edge case).
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 110), _PARAGRAPH, fontsize=10, fontname="helv")
    page.insert_link({"kind": fitz.LINK_URI, "from": link_rect, "uri": "https://example.com/cited"})
    doc.save(str(path))
    doc.close()


def test_link_on_one_line_only_excludes_that_line_not_the_whole_paragraph(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    # Squarely covers the middle line only (see the fixture's own
    # extracted line bboxes - stable for this exact insert_textbox() call).
    _build_paragraph_with_link(source, fitz.Rect(50, 64.8, 195.6, 78.5))

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = sorted(engine.extract_blocks(0), key=lambda b: b.bbox[1])

    assert [b.text for b in blocks] == [
        "First line of a longer paragraph.",
        "Second line cites a source inline.",
        "Third line continues normally.",
    ]
    assert [b.translatable for b in blocks] == [True, False, True]


def test_hairline_sliver_overlap_does_not_exclude_the_neighboring_line(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    # Same link, but its top edge reaches 0.05pt into the line ABOVE its
    # real target (mirrors the 0.02pt real-world case from
    # "1526 VIRELICON.pdf" - see this module's docstring). The first
    # line's own bbox ends at y1=63.7 (confirmed via the fixture's own
    # extraction), so 63.65 is a deliberate 0.05pt sliver into it.
    _build_paragraph_with_link(source, fitz.Rect(50, 63.65, 195.6, 78.5))

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = sorted(engine.extract_blocks(0), key=lambda b: b.bbox[1])

    assert [b.text for b in blocks] == [
        "First line of a longer paragraph.",
        "Second line cites a source inline.",
        "Third line continues normally.",
    ]
    # The sliver must NOT pull the first line in - only the second line
    # (the link's real, substantial target) stays non-translatable.
    assert [b.translatable for b in blocks] == [True, False, True]


def test_whole_block_link_still_excludes_entirely(tmp_path: Path) -> None:
    """A block that IS just the link (every line overlaps it) must stay
    fully non-translatable - the split must not accidentally weaken the
    original, still-valid whole-block case (see
    tests/fixtures/representative.pdf / tests/test_pdf_link_preservation.py).
    """
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 70), "Click here to view source", fontsize=10, fontname="helv")
    page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(50, 50, 350, 70), "uri": "https://example.com/cited"})
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = engine.extract_blocks(0)

    assert len(blocks) == 1
    assert blocks[0].translatable is False
