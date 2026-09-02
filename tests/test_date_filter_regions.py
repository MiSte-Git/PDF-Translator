"""Covers the "Footer" text-extraction added 02.09.2026 for the date
filter (Michael: "Das aber nur entweder im Header, im Footer oder im ICO
Feld auf der ersten Seite, also für diese Option.") -
extract_pdf_footer_text()/extract_docx_footer_text() (exact mirrors of
the existing "Header" extractors, see their own docstrings) and the
DATE_REGION_*/PDF_DATE_REGION_EXTRACTORS/DOCX_DATE_REGION_EXTRACTORS
registry in ui/search_scopes.py that wires ICO Format/Header/Footer up
for the date filter specifically (a separate, smaller set from the
general SCOPE_* free-text search scopes - there is no general "Footer"
text-search scope).
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pipeline.pdf.pymupdf_engine import extract_pdf_footer_text
from pipeline.word.docx_engine import extract_docx_footer_text
from ui.search_scopes import (
    DATE_REGION_FOOTER,
    DATE_REGION_HEADER,
    DATE_REGION_ICO_FORMAT,
    DOCX_DATE_REGION_EXTRACTORS,
    PDF_DATE_REGION_EXTRACTORS,
    combined_extractor,
)

FIXTURES = Path(__file__).parent / "fixtures"
ICO_WITH_HEADER_FOOTER = FIXTURES / "representative_ico.docx"  # header2.xml + footer1.xml, see its own fixtures


def _build_recurring_header_footer_document(path: Path, pages: int = 3) -> None:
    """Same recurring-top-of-page text as test_pdf_search_scopes.py's
    fixture, PLUS a recurring bottom-of-page footer line - so both
    header_bbox and footer_bbox get detected (detect_header_footer_zones()
    needs the SAME text repeating near the top/bottom across most pages).
    """
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=400, height=600)
        page.insert_text((50, 40), "Company Confidential - Internal Use Only", fontsize=10, fontname="helv")
        page.insert_text((50, 200), f"Body text on page {i}, unique content here.", fontsize=11, fontname="helv")
        page.insert_text((50, 560), "Ausstellungsdatum: 2026-09-01", fontsize=8, fontname="helv")
    doc.save(str(path))
    doc.close()


# --- extract_pdf_footer_text() ------------------------------------------


def test_pdf_footer_scope_finds_the_recurring_bottom_of_page_text(tmp_path: Path) -> None:
    source = tmp_path / "recurring_footer.pdf"
    _build_recurring_header_footer_document(source)
    text = extract_pdf_footer_text(str(source))
    assert text is not None
    assert "Ausstellungsdatum: 2026-09-01" in text
    assert "unique content" not in text  # body text must not leak in


def test_pdf_footer_scope_returns_none_when_nothing_repeats(tmp_path: Path) -> None:
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=400, height=600)
        page.insert_text((50, 200), f"Completely unrelated content on page {i}.", fontsize=11, fontname="helv")
    source = tmp_path / "no_footer.pdf"
    doc.save(str(source))
    doc.close()
    assert extract_pdf_footer_text(str(source)) is None


def test_pdf_footer_scope_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.pdf"):
        extract_pdf_footer_text("does_not_exist.pdf")


# --- extract_docx_footer_text() -----------------------------------------


def test_docx_footer_scope_finds_the_word_footer_text() -> None:
    text = extract_docx_footer_text(str(ICO_WITH_HEADER_FOOTER))
    assert text is not None
    assert "Footer Text - Page 1" in text


def test_docx_footer_scope_returns_none_without_a_footer_part(tmp_path: Path) -> None:
    import docx

    document = docx.Document()
    document.add_paragraph("Body only, no footer part at all.")
    source = tmp_path / "no_footer.docx"
    document.save(str(source))
    assert extract_docx_footer_text(str(source)) is None


def test_docx_footer_scope_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.docx"):
        extract_docx_footer_text("does_not_exist.docx")


# --- DATE_REGION_* registries / combined_extractor() ----------------------


def test_pdf_date_region_extractors_cover_ico_header_footer() -> None:
    assert set(PDF_DATE_REGION_EXTRACTORS) == {DATE_REGION_ICO_FORMAT, DATE_REGION_HEADER, DATE_REGION_FOOTER}


def test_docx_date_region_extractors_cover_ico_header_footer() -> None:
    assert set(DOCX_DATE_REGION_EXTRACTORS) == {DATE_REGION_ICO_FORMAT, DATE_REGION_HEADER, DATE_REGION_FOOTER}


def test_combined_date_region_extractor_reads_docx_footer_only() -> None:
    extractor = combined_extractor(DOCX_DATE_REGION_EXTRACTORS, {DATE_REGION_FOOTER})
    text = extractor(str(ICO_WITH_HEADER_FOOTER))
    assert text is not None
    assert "Footer Text - Page 1" in text
    assert "QSI ICO" not in text  # header text must not leak in when only Footer is selected


def test_combined_date_region_extractor_empty_regions_always_none() -> None:
    extractor = combined_extractor(DOCX_DATE_REGION_EXTRACTORS, set())
    assert extractor(str(ICO_WITH_HEADER_FOOTER)) is None
