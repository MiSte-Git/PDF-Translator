"""Covers pipeline/pdf/pymupdf_engine.py's extract_ico_header_text() -
the per-file extraction ui/merge_search.py's folder scan (01.09.2026,
Michael: "Wie sollten wir es machen wenn ich einen Ordner mit 1000 oder
mehr PDFs habe [...] Der Developer Name steht ja im oberen geschützten
Teil.") is built on. See tests/test_pdf_ico_mode.py's module docstring
for why the fixtures below use page.insert_text() per line (with a
single-space " " line standing in for a blank line) rather than
insert_textbox("\\n\\n") - the same real-document shape ico_mode's own
tests already established.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pipeline.pdf.pymupdf_engine import extract_ico_header_text

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.pdf"  # "Issuer Address: Acme Development GmbH"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.pdf"  # "Issuer Address: Zenith Capital Partners"
PLAIN = FIXTURES / "merge_search_plain.pdf"  # no anchor term at all


def test_extracts_only_the_metadata_chunk_not_the_rest_of_the_page() -> None:
    text = extract_ico_header_text(str(ICO_ACME))
    assert text is not None
    assert "Acme Development GmbH" in text
    assert "Issuer Address" in text
    assert "Welcome to the document" not in text  # the translatable rest, must NOT leak in


def test_different_developer_names_are_distinguishable() -> None:
    acme = extract_ico_header_text(str(ICO_ACME))
    zenith = extract_ico_header_text(str(ICO_ZENITH))
    assert acme is not None and zenith is not None
    assert "Acme" in acme and "Acme" not in zenith
    assert "Zenith" in zenith and "Zenith" not in acme


def test_plain_document_without_anchor_returns_none() -> None:
    assert extract_ico_header_text(str(PLAIN)) is None


def test_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.pdf"):
        extract_ico_header_text("does_not_exist.pdf")


# --- a stray blank line at an outlier x0 must not fracture the block -----
# 02.09.2026, Michael's real "2133 XLMFOMO.pdf" (uploaded to diagnose "keine
# PDFs gefunden" with the date filter): a date line ("June 18, 2026") and an
# "ICO Telegram Write Up: Post Link" line went missing from the extracted
# text entirely, even though both sit in the very same PyMuPDF block as
# "Issuer Address" further down. Root cause, confirmed by dumping that PDF's
# raw block/line structure: the blank line PyMuPDF emits right after a
# hyperlink run sits at x0≈553 (the page's right edge) even though every
# real text line around it sits at x0≈43 - _group_lines_by_x0()'s column
# split (pipeline/pdf/pymupdf_engine.py, threshold 50pt) used to compare
# EVERY line's x0, blank or not, so that one stray blank fractured an
# otherwise single-column block into 3 unrelated groups. The date/Telegram
# line ended up alone in a group with no FIRST_PAGE_ANCHOR_TERMS match of
# its own, which _split_first_page_metadata() then returns unchanged - and
# extract_ico_header_text() only ever keeps a group whose split actually
# found the anchor, so that whole group was silently dropped.


def _build_source_with_outlier_blank(path: Path) -> None:
    """One PyMuPDF block, page.insert_text() per line (see this module's
    docstring) - mirrors Michael's real document's shape: a real content
    line, then a blank line placed FAR to the right (the hyperlink-
    trailing-space artifact), then more real content, then the usual
    Issuer Address metadata chunk and, after it, ordinary translatable
    content (the "rest" _split_first_page_metadata() needs to actually
    split this block in two at all).
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    y = 60.0
    for line in ["Special Note: launches soon"]:
        page.insert_text((50, y), line, fontsize=11, fontname="helv")
        y += 14
    page.insert_text((500, y), " ", fontsize=11, fontname="helv")  # the outlier
    y += 14
    for line in [
        "Contact: support@example.com", " ", " ",
        "Issuer Address:", "123 Main Street", " ",
        "Welcome to the document.", "This is the real content.",
    ]:
        page.insert_text((50, y), line, fontsize=11, fontname="helv")
        y += 14
    doc.save(str(path))
    doc.close()


def test_a_blank_line_at_an_outlier_x0_does_not_swallow_the_lines_around_it(tmp_path: Path) -> None:
    source = tmp_path / "outlier_blank.pdf"
    _build_source_with_outlier_blank(source)

    text = extract_ico_header_text(str(source))

    assert text is not None
    assert "Special Note: launches soon" in text
    assert "Contact: support@example.com" in text
    assert "Issuer Address" in text
    assert "Welcome to the document" not in text  # the translatable rest, must NOT leak in
