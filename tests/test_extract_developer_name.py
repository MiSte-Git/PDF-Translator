"""Covers ui/merge_search.py::extract_developer_name() (02.09.2026,
Michael, on the search dialogs' results list: "Es reicht wenn hinter dem
Namen nur der Teil mit Developer erscheint und nicht die ganze 1. Seite.
Wenn kein Developer gefunden wird, darf es leer bleiben.").
"""
from __future__ import annotations

from ui.merge_search import extract_developer_name


def test_extracts_the_developer_value_from_a_multiline_header_block() -> None:
    snippet = "Developer: StellarRussia\nQSI ICO: AUREXIS\nIssuer Address: ...\n"
    assert extract_developer_name(snippet) == "StellarRussia"


def test_handles_developer_and_ico_running_together_with_no_space() -> None:
    # Real-world case (see pipeline/word/duplicate_analysis.py's own
    # comment on this) - PDF/DOCX text extraction sometimes concatenates
    # adjacent fields with no whitespace between them at all.
    snippet = "Developer: The Korolev DirectiveQSI ICO: INERTIARA"
    assert extract_developer_name(snippet) == "The Korolev Directive"


def test_returns_empty_string_when_no_developer_field_is_present() -> None:
    assert extract_developer_name("Issuer Address: 123 Main St\nAsset Matrix: X") == ""
    assert extract_developer_name("") == ""


def test_returns_empty_string_for_a_developer_field_with_no_value() -> None:
    assert extract_developer_name("Developer: \nQSI ICO: AUREXIS") == ""


def test_is_case_insensitive() -> None:
    assert extract_developer_name("developer: Acme Development GmbH") == "Acme Development GmbH"


def test_uses_the_first_developer_line_when_several_are_present() -> None:
    snippet = "Developer: First Co\nsome other text\nDeveloper: Second Co"
    assert extract_developer_name(snippet) == "First Co"
