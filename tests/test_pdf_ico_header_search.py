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
