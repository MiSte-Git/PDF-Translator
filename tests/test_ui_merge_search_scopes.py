"""Covers the 02.09.2026 `scopes` parameter on find_pdfs_matching()/
find_docx_files_matching() (ui/merge_search.py) - the wiring between the
new "ICO Format"/"Header"/"Volltext" checkboxes (ui/search_scopes.py) and
the existing folder-scan/matching engine, plus the new AND/OR query
support (pipeline/search_query.py) end to end. See tests/test_ui_merge_search.py
for this module's pre-existing, `scopes=None` (unchanged) coverage.
"""
from __future__ import annotations

from pathlib import Path

from ui.merge_search import find_docx_files_matching, find_pdfs_matching
from ui.search_scopes import SCOPE_FULL_TEXT, SCOPE_HEADER, SCOPE_ICO_FORMAT

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME_PDF = FIXTURES / "merge_search_ico_acme.pdf"  # ICO-metadata-only: "Issuer Address: Acme Development GmbH"
ICO_WITH_HEADER_DOCX = FIXTURES / "representative_ico.docx"  # header2.xml: "QSI ICO: TESTMARK"; body: "Issuer XYZ"


def test_scopes_none_keeps_the_original_ico_format_only_behavior(tmp_path: Path) -> None:
    (tmp_path / "acme.pdf").write_bytes(ICO_ACME_PDF.read_bytes())
    result = find_pdfs_matching(tmp_path, "Welcome to the document", recursive=False)  # body text, not in "ICO Format"
    assert result.matches == []


def test_full_text_scope_widens_matching_to_the_whole_document(tmp_path: Path) -> None:
    (tmp_path / "acme.pdf").write_bytes(ICO_ACME_PDF.read_bytes())
    result = find_pdfs_matching(tmp_path, "Welcome to the document", recursive=False, scopes={SCOPE_FULL_TEXT})
    assert {m.path.name for m in result.matches} == {"acme.pdf"}


def test_combining_two_scopes_matches_a_term_from_either(tmp_path: Path) -> None:
    (tmp_path / "acme.pdf").write_bytes(ICO_ACME_PDF.read_bytes())
    result = find_pdfs_matching(
        tmp_path, "Welcome", recursive=False, scopes={SCOPE_ICO_FORMAT, SCOPE_FULL_TEXT}
    )
    assert {m.path.name for m in result.matches} == {"acme.pdf"}


def test_no_scopes_selected_never_matches_a_non_empty_query(tmp_path: Path) -> None:
    (tmp_path / "acme.pdf").write_bytes(ICO_ACME_PDF.read_bytes())
    result = find_pdfs_matching(tmp_path, "Acme", recursive=False, scopes=set())
    assert result.matches == []


def test_and_query_across_ico_format_and_body_via_full_text_scope(tmp_path: Path) -> None:
    (tmp_path / "acme.pdf").write_bytes(ICO_ACME_PDF.read_bytes())
    result = find_pdfs_matching(
        tmp_path, "Acme AND Welcome", recursive=False, scopes={SCOPE_FULL_TEXT}
    )
    assert {m.path.name for m in result.matches} == {"acme.pdf"}

    # the same AND query against "ICO Format" alone must NOT match - "Welcome"
    # only appears in the document body, outside that scope.
    result_narrow = find_pdfs_matching(
        tmp_path, "Acme AND Welcome", recursive=False, scopes={SCOPE_ICO_FORMAT}
    )
    assert result_narrow.matches == []


def test_or_query_matches_if_either_term_is_present(tmp_path: Path) -> None:
    (tmp_path / "acme.pdf").write_bytes(ICO_ACME_PDF.read_bytes())
    result = find_pdfs_matching(tmp_path, "Zenith OR Acme", recursive=False)
    assert {m.path.name for m in result.matches} == {"acme.pdf"}


def test_docx_header_scope_finds_the_real_word_header(tmp_path: Path) -> None:
    (tmp_path / "ico.docx").write_bytes(ICO_WITH_HEADER_DOCX.read_bytes())
    result = find_docx_files_matching(tmp_path, "TESTMARK", recursive=False, scopes={SCOPE_HEADER})
    assert {m.path.name for m in result.matches} == {"ico.docx"}


def test_docx_ico_format_scope_also_finds_header_text_since_the_02092026_fix(tmp_path: Path) -> None:
    # See tests/test_docx_search_scopes.py for the underlying per-file
    # extraction fix this depends on: "ICO Format" now includes the real
    # Word header, not just the page-1 metadata region.
    (tmp_path / "ico.docx").write_bytes(ICO_WITH_HEADER_DOCX.read_bytes())
    result = find_docx_files_matching(tmp_path, "TESTMARK", recursive=False, scopes={SCOPE_ICO_FORMAT})
    assert {m.path.name for m in result.matches} == {"ico.docx"}
