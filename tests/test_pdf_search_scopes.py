"""Covers the 02.09.2026 search-scope feature on the PDF side (Michael:
"Wir haben ja nur 'Suchtext (nur ICO-Kopfbereich auf Seite 1)' als
Suchbereich statisch zur Verfügung. Allerdings sollte das eine Option
sein. Genauso wie die Option 'nur im Header'. Dann sollte es auch möglich
sein im ganzen Text suchen zu können."):

- extract_ico_header_text() ("ICO Format") now also captures any block
  BEFORE the metadata anchor - the real fix for Michael's reported bug
  (searching "Developer" found nothing, even though "Developer:"/
  "QSI ICO:" were visibly on page 1 - see this module's fixture below,
  which reproduces his screenshot's shape).
- extract_pdf_header_text() ("Header") - the new recurring-header-across-
  all-pages scope for normal (non-ICO) documents.
- extract_pdf_full_text() ("Volltext") - the new whole-document scope.

See tests/test_pdf_ico_mode.py's module docstring for why fixtures below
use page.insert_text() per line rather than insert_textbox("\\n\\n").
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pipeline.pdf.pymupdf_engine import extract_ico_header_text, extract_pdf_full_text, extract_pdf_header_text


def _build_ico_with_separate_header_block(path: Path) -> None:
    """Page 0: a visually separate "Developer:"/"QSI ICO:" block near the
    top (its own PyMuPDF raw_block - a large vertical gap to the next
    block is what makes PyMuPDF segment it separately, confirmed by
    direct inspection), then the existing "Issuer Address:"-anchored
    metadata chunk further down, then ordinary translatable content -
    reproducing the real-document shape from Michael's screenshot
    (02.09.2026): "Developer"/"QSI ICO" sit above the metadata region,
    in a block of their own.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    header_lines = ["Developer:", "StellarRussia", "QSI ICO:", "AUREXIS"]
    y = 40.0
    for line in header_lines:
        page.insert_text((50, y), line, fontsize=14, fontname="hebo")
        y += 18

    metadata_lines = [
        "Issuer Address:", "123 Main Street", " ",
        "Welcome to the document.", "This is the real content.",
    ]
    y = 160.0  # large gap from the header block above (~66pt) - forces a new raw_block
    for line in metadata_lines:
        page.insert_text((50, y), line, fontsize=11, fontname="helv")
        y += 14
    doc.save(str(path))
    doc.close()


def _build_recurring_header_document(path: Path, pages: int = 3) -> None:
    """A NORMAL (non-ICO) document: the same text repeats near the top of
    every page (a plausible letterhead/confidentiality banner), body text
    differs page to page, and a page number repeats near the bottom.
    """
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=400, height=600)
        page.insert_text((50, 40), "Company Confidential - Internal Use Only", fontsize=10, fontname="helv")
        page.insert_text((50, 200), f"Body text on page {i}, unique content here.", fontsize=11, fontname="helv")
        page.insert_text((50, 560), f"Page {i + 1} of {pages}", fontsize=8, fontname="helv")
    doc.save(str(path))
    doc.close()


def _build_document_without_header(path: Path) -> None:
    """A NORMAL document with no repeating top-of-page text at all."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=400, height=600)
        page.insert_text((50, 200), f"Completely unrelated content on page {i}.", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


# --- "ICO Format": header block before the metadata anchor -----------------


def test_ico_format_now_includes_a_header_block_before_the_metadata_anchor(tmp_path: Path) -> None:
    source = tmp_path / "ico_with_header.pdf"
    _build_ico_with_separate_header_block(source)
    text = extract_ico_header_text(str(source))
    assert text is not None
    assert "Developer" in text
    assert "StellarRussia" in text
    assert "QSI ICO" in text
    assert "Issuer Address" in text  # the previously-working part must still be there
    assert "Welcome to the document" not in text  # the translatable rest must still NOT leak in


def test_ico_format_without_a_separate_header_block_is_unchanged(tmp_path: Path) -> None:
    # A single-block ICO page (no earlier block at all) must behave
    # exactly as before this fix - regression guard for
    # tests/fixtures/merge_search_ico_acme.pdf's existing coverage.
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    lines = ["Issuer Address:", "123 Main Street", " ", "Welcome to the document."]
    y = 60.0
    for line in lines:
        page.insert_text((50, y), line, fontsize=11, fontname="helv")
        y += 14
    source = tmp_path / "ico_single_block.pdf"
    doc.save(str(source))
    doc.close()

    text = extract_ico_header_text(str(source))
    assert text is not None
    assert "Issuer Address" in text
    assert "Welcome to the document" not in text


# --- "Header": recurring header across all pages, normal documents --------


def test_header_scope_finds_the_recurring_top_of_page_text(tmp_path: Path) -> None:
    source = tmp_path / "recurring_header.pdf"
    _build_recurring_header_document(source)
    text = extract_pdf_header_text(str(source))
    assert text is not None
    assert "Company Confidential - Internal Use Only" in text
    # body text (differs per page, so it can't be the "recurring" match) must not leak in
    assert "unique content" not in text


def test_header_scope_returns_none_when_nothing_repeats(tmp_path: Path) -> None:
    source = tmp_path / "no_header.pdf"
    _build_document_without_header(source)
    assert extract_pdf_header_text(str(source)) is None


def test_header_scope_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.pdf"):
        extract_pdf_header_text("does_not_exist.pdf")


# --- "Volltext": the whole document, a strict superset ---------------------


def test_full_text_scope_includes_header_and_body(tmp_path: Path) -> None:
    source = tmp_path / "recurring_header.pdf"
    _build_recurring_header_document(source)
    text = extract_pdf_full_text(str(source))
    assert text is not None
    assert "Company Confidential - Internal Use Only" in text
    assert "unique content here" in text  # unlike the header scope, body text IS included


def test_full_text_scope_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.pdf"):
        extract_pdf_full_text("does_not_exist.pdf")
