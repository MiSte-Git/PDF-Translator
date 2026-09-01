"""Covers pipeline/word/docx_engine.py's extract_docx_ico_header_text() -
the DOCX counterpart of pipeline/pdf/pymupdf_engine.py's
extract_ico_header_text() (see tests/test_pdf_ico_header_search.py),
built for ui/word_merge_search.py's folder scan (01.09.2026, Michael:
"Jetzt noch das ganze für *.docx.").

Fixtures (tests/fixtures/merge_search_ico_acme.docx/
merge_search_ico_zenith.docx/merge_search_plain.docx) mirror the existing
PDF fixtures' developer-name content exactly, generated with the same
minimal word/document.xml shape as tests/fixtures/representative_ico.docx
(a bare <a:prstGeom prst="straightConnector1"> inside one paragraph's
<w:drawing> - see pipeline/word/docx_engine.py::_has_separator_shape()).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.word.docx_engine import extract_docx_ico_header_text

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.docx"  # "Issuer Address: Acme Development GmbH"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.docx"  # "Issuer Address: Zenith Capital Partners"
PLAIN = FIXTURES / "merge_search_plain.docx"  # no separator shape at all


def test_extracts_only_the_metadata_paragraphs_not_the_rest_of_the_document() -> None:
    text = extract_docx_ico_header_text(str(ICO_ACME))
    assert text is not None
    assert "Acme Development GmbH" in text
    assert "Issuer Address" in text
    assert "translatable paragraph" not in text  # the rest of the document, must NOT leak in


def test_different_developer_names_are_distinguishable() -> None:
    acme = extract_docx_ico_header_text(str(ICO_ACME))
    zenith = extract_docx_ico_header_text(str(ICO_ZENITH))
    assert acme is not None and zenith is not None
    assert "Acme" in acme and "Acme" not in zenith
    assert "Zenith" in zenith and "Zenith" not in acme


def test_plain_document_without_separator_returns_none() -> None:
    assert extract_docx_ico_header_text(str(PLAIN)) is None


def test_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.docx"):
        extract_docx_ico_header_text("does_not_exist.docx")
