"""Covers ui/search_scopes.py::combined_extractor() - the mechanism behind
the three independently-combinable "ICO Format"/"Header"/"Volltext"
checkboxes (02.09.2026). Uses small stub extractors rather than real
PDF/DOCX ones - the combination logic itself has nothing format-specific
about it (see tests/test_pdf_search_scopes.py/tests/test_docx_search_scopes.py
for the real per-format extractors).
"""
from __future__ import annotations

from ui.search_scopes import DEFAULT_SCOPES, SCOPE_FULL_TEXT, SCOPE_HEADER, SCOPE_ICO_FORMAT, combined_extractor


def _stub_registry() -> dict:
    return {
        SCOPE_ICO_FORMAT: lambda path: "ico-text" if path == "match.pdf" else None,
        SCOPE_HEADER: lambda path: "header-text" if path in ("match.pdf", "header-only.pdf") else None,
        SCOPE_FULL_TEXT: lambda path: "full-text-with-body" if path == "match.pdf" else None,
    }


def test_single_scope_returns_only_that_scopes_text() -> None:
    extractor = combined_extractor(_stub_registry(), {SCOPE_ICO_FORMAT})
    assert extractor("match.pdf") == "ico-text"
    assert extractor("header-only.pdf") is None  # no ICO text for this file


def test_multiple_scopes_are_concatenated() -> None:
    extractor = combined_extractor(_stub_registry(), {SCOPE_ICO_FORMAT, SCOPE_HEADER})
    text = extractor("match.pdf")
    assert text is not None
    assert "ico-text" in text
    assert "header-text" in text


def test_a_scope_with_no_text_for_this_file_is_simply_skipped() -> None:
    extractor = combined_extractor(_stub_registry(), {SCOPE_ICO_FORMAT, SCOPE_HEADER})
    # header-only.pdf has header text but no ICO text - must not become None overall.
    text = extractor("header-only.pdf")
    assert text == "header-text"


def test_no_scope_selected_always_returns_none() -> None:
    extractor = combined_extractor(_stub_registry(), set())
    assert extractor("match.pdf") is None


def test_unrecognized_scope_names_are_ignored() -> None:
    extractor = combined_extractor(_stub_registry(), {"not_a_real_scope"})
    assert extractor("match.pdf") is None


def test_default_scopes_is_ico_format_only() -> None:
    assert DEFAULT_SCOPES == frozenset({SCOPE_ICO_FORMAT})
