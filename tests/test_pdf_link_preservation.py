"""Regression coverage for the "Link-Annotationen nach Redaction" item
tracked as open in RoadMap.md Phase 2/PDF.

What actually happens (confirmed via direct reproduction, not just reading
PyMuPDF's docs): page.apply_redactions() - called by both
PyMuPdfEngine.redact_block() and _grow_highlight_if_needed() - silently
drops ANY annotation whose rect overlaps the redacted area, including link
annotations that belong to a completely unrelated, non-translatable block
that merely happens to sit close enough for its link rect to be touched by
another block's redaction (e.g. after that other block's text grows taller
than its original space, or simply due to tight page layout). Since a link
block is always translatable=False (see PyMuPdfEngine.extract_blocks()),
the link's OWN block is never redacted - the loss only ever happens as a
side effect of redacting a different, nearby block.

A first fix attempt (restore immediately after each redact_block() call by
diffing page.get_links() before/after) was built and then discarded before
ever being wired in: page.insert_link() makes a link invisible to
page.get_links() for the rest of that live session (reproduced directly -
see the assertion below), so a second, later redaction touching the same
restored link's rect would silently destroy it again with no way for a
live before/after diff to detect the second loss. The actual fix instead
snapshots every page's links once in PyMuPdfEngine.open() (before any
redaction happens) and reconciles against that snapshot exactly once, in
save() (see PyMuPdfEngine._restore_missing_links()), which is immune to
that problem because it never depends on reading back a link inserted
earlier in the same session.

Builds its own synthetic PDF directly with fitz, following the same
pattern as tests/test_pdf_redact_insert_collision.py, and constructs the
TextBlock passed to redact_block() by hand (rather than going through
extract_blocks()) so the block's bbox can be made to deliberately overlap
the link's rect - reproducing the "unrelated block's redaction rect ends
up touching a nearby link" mechanism directly, independent of exactly
which higher-level code path (plain growth, highlight regrowth, tight
original layout) would put a real document into that situation.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

LINK_RECT = fitz.Rect(60, 90, 340, 110)
LINK_URI = "https://example.com/unrelated-link"


def _build_pdf_with_link_and_paragraph(path: Path) -> None:
    """A link-annotated line (block B, never redacted - link blocks are
    always translatable=False) with an ordinary paragraph (block A)
    directly above it, separated only by a small gap - the same tight-
    layout shape used in test_pdf_redact_insert_collision.py, just with a
    link on the lower block instead of plain text.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(
        fitz.Rect(50, 50, 350, 85),
        "This is the original English paragraph that will be redacted and replaced.",
        fontsize=10, fontname="helv",
    )
    page.insert_textbox(LINK_RECT, "See our unrelated website for details.", fontsize=10, fontname="helv")
    page.insert_link({"kind": fitz.LINK_URI, "from": LINK_RECT, "uri": LINK_URI})
    doc.save(str(path))
    doc.close()


def test_insert_link_is_invisible_to_live_get_links_in_the_same_session() -> None:
    """Documents the exact failure mode that sank the first (per-call
    restore) fix attempt, so a future reader doesn't reintroduce it: right
    after page.insert_link(), the SAME live page's get_links() does not
    show it - only a save()+reopen makes it visible again.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_link({"kind": fitz.LINK_URI, "from": LINK_RECT, "uri": LINK_URI})

    assert page.get_links() == []  # invisible in the live session
    doc.close()


def test_redaction_overlapping_a_link_rect_destroys_it_without_the_fix(tmp_path: Path) -> None:
    """Baseline proof that the bug is real: a plain page.apply_redactions()
    call with a rect overlapping the link's rect removes the link
    annotation, confirming PyMuPdfEngine.save()'s reconciliation step has
    something real to fix. Uses a link that was saved to disk and reopened
    (not inserted earlier in this same live session - see the live-
    visibility caveat proven above) so this test isolates the
    apply_redactions() behaviour alone.
    """
    source = tmp_path / "source.pdf"
    _build_pdf_with_link_and_paragraph(source)

    reopened = fitz.open(str(source))
    page = reopened[0]
    assert len(page.get_links()) == 1  # sanity: link persisted to disk correctly

    overlapping_rect = fitz.Rect(55, 80, 345, 100)  # touches LINK_RECT (60,90,340,110)
    assert overlapping_rect.intersects(LINK_RECT)
    page.add_redact_annot(overlapping_rect, fill=(1, 1, 1))
    page.apply_redactions()

    assert page.get_links() == []  # the link is gone - the bug, unmitigated
    reopened.close()


def test_engine_save_restores_a_link_destroyed_by_an_unrelated_redaction(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_pdf_with_link_and_paragraph(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))

    # Hand-built block A: bbox deliberately reaches down far enough to
    # overlap LINK_RECT, simulating a nearby unrelated block's redaction
    # rect ending up touching the link (see module docstring for why this
    # is built by hand instead of relying on extract_blocks()/growth to
    # happen to produce this exact geometry).
    block_a = TextBlock(
        page_index=0,
        bbox=(50, 50, 350, 100),  # y1=100 overlaps LINK_RECT's y0=90..y1=110
        text="This is the original English paragraph that will be redacted and replaced.",
        font_name="helv",
        font_size=10,
        color=(0, 0, 0),
        bold=False,
        italic=False,
        translatable=True,
    )

    engine.redact_block(block_a)
    engine.insert_text(block_a, "", block_a.font_size, translated_html="<p>Ersetzter deutscher Absatz.</p>")
    engine.save(str(output))

    result = fitz.open(str(output))
    links = result[0].get_links()
    assert len(links) == 1
    assert links[0]["uri"] == LINK_URI
    restored_rect = links[0]["from"]
    assert abs(restored_rect.x0 - LINK_RECT.x0) < 0.5
    assert abs(restored_rect.y0 - LINK_RECT.y0) < 0.5
    assert abs(restored_rect.x1 - LINK_RECT.x1) < 0.5
    assert abs(restored_rect.y1 - LINK_RECT.y1) < 0.5
    result.close()


def test_engine_save_is_a_noop_for_links_never_touched_by_any_redaction(tmp_path: Path) -> None:
    """A page whose link is never anywhere near a redaction must still
    have exactly one link afterward - not two (accidentally re-inserted
    on top of the original that was never actually removed).
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_pdf_with_link_and_paragraph(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))

    block_a = TextBlock(
        page_index=0,
        bbox=(50, 50, 350, 85),  # does not reach LINK_RECT (y0=90)
        text="This is the original English paragraph that will be redacted and replaced.",
        font_name="helv",
        font_size=10,
        color=(0, 0, 0),
        bold=False,
        italic=False,
        translatable=True,
    )

    engine.redact_block(block_a)
    engine.insert_text(block_a, "", block_a.font_size, translated_html="<p>Ersetzter deutscher Absatz.</p>")
    engine.save(str(output))

    result = fitz.open(str(output))
    links = result[0].get_links()
    assert len(links) == 1
    assert links[0]["uri"] == LINK_URI
    result.close()
