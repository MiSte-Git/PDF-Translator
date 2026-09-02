"""Covers the 02.09.2026 search-scope feature on the DOCX side (Michael:
see tests/test_pdf_search_scopes.py's module docstring - identical
feature, mirrored per this project's per-format-engine convention):

- extract_docx_ico_header_text() ("ICO Format") now also includes the
  real Word header (word/header2.xml) - the fix for Michael's reported
  bug (searching "Developer" found nothing, even though it was visibly on
  page 1 - in the actual Word header, not a body paragraph).
- extract_docx_header_text() ("Header") - the new scope for normal
  (non-ICO) documents; unlike the PDF equivalent, a Word header applies
  structurally to every page already, so this needs no cross-page
  detection.
- extract_docx_full_text() ("Volltext") - the new whole-document scope.

tests/fixtures/representative_ico.docx already has BOTH a real
word/header2.xml ("Header Text - QSI ICO: TESTMARK") and the page-1
metadata/separator-shape structure (see its own generation context,
referenced throughout pipeline/word/docx_engine.py) - exactly the shape
these new scopes need, so no new fixture file was required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.word.docx_engine import extract_docx_full_text, extract_docx_header_text, extract_docx_ico_header_text

FIXTURES = Path(__file__).parent / "fixtures"
ICO_WITH_HEADER = FIXTURES / "representative_ico.docx"  # header2.xml: "QSI ICO: TESTMARK"; body: "Issuer XYZ"
PLAIN = FIXTURES / "merge_search_plain.docx"  # no separator shape, no header part at all


# --- "ICO Format": real Word header included -------------------------------


def test_ico_format_now_includes_the_real_word_header() -> None:
    text = extract_docx_ico_header_text(str(ICO_WITH_HEADER))
    assert text is not None
    assert "QSI ICO: TESTMARK" in text
    assert "Issuer XYZ" in text  # the previously-working metadata part must still be there
    assert "translatable paragraph" not in text  # the rest of the document, must NOT leak in


def test_ico_format_plain_document_without_separator_returns_none() -> None:
    # No separator shape at all -> not this internal document type,
    # regardless of whether the document happens to have header text.
    assert extract_docx_ico_header_text(str(PLAIN)) is None


# --- "Header": the real Word header, independent of ICO status ------------


def test_header_scope_returns_the_real_word_header_text() -> None:
    text = extract_docx_header_text(str(ICO_WITH_HEADER))
    assert text is not None
    assert "QSI ICO: TESTMARK" in text
    assert "Issuer XYZ" not in text  # body content must NOT be included in this scope


def test_header_scope_returns_none_when_the_document_has_no_header_part() -> None:
    assert extract_docx_header_text(str(PLAIN)) is None


def test_header_scope_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.docx"):
        extract_docx_header_text("does_not_exist.docx")


# --- "Volltext": the whole document, a strict superset ---------------------


def test_full_text_scope_includes_header_and_every_body_paragraph() -> None:
    text = extract_docx_full_text(str(ICO_WITH_HEADER))
    assert text is not None
    assert "QSI ICO: TESTMARK" in text
    assert "Issuer XYZ" in text
    assert "translatable paragraph" in text  # unlike "ICO Format", the rest of the body IS included


def test_full_text_scope_missing_file_raises_named_value_error() -> None:
    with pytest.raises(ValueError, match="does_not_exist.docx"):
        extract_docx_full_text("does_not_exist.docx")
