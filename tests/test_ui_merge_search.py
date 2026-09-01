"""Covers ui/merge_search.py's folder scan + ICO-header filter (see
tests/test_pdf_ico_header_search.py for the underlying per-file
extraction's own coverage).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ui.merge_search import find_pdf_files, find_pdfs_matching

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.pdf"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.pdf"
PLAIN = FIXTURES / "merge_search_plain.pdf"


def _populate(root: Path) -> None:
    """acme.pdf, zenith.pdf, plain.pdf directly under root; a copy of
    acme.pdf ALSO under root/subfolder/ - to distinguish recursive from
    non-recursive scans."""
    shutil.copy(ICO_ACME, root / "acme.pdf")
    shutil.copy(ICO_ZENITH, root / "zenith.pdf")
    shutil.copy(PLAIN, root / "plain.pdf")
    (root / "notes.txt").write_text("not a pdf")
    sub = root / "subfolder"
    sub.mkdir()
    shutil.copy(ICO_ACME, sub / "acme_nested.pdf")


def test_find_pdf_files_recursive_vs_flat(tmp_path: Path) -> None:
    _populate(tmp_path)

    recursive = find_pdf_files(tmp_path, recursive=True)
    assert {p.name for p in recursive} == {"acme.pdf", "zenith.pdf", "plain.pdf", "acme_nested.pdf"}

    flat = find_pdf_files(tmp_path, recursive=False)
    assert {p.name for p in flat} == {"acme.pdf", "zenith.pdf", "plain.pdf"}


def test_empty_query_matches_every_pdf_without_opening_any_file(tmp_path: Path) -> None:
    _populate(tmp_path)
    result = find_pdfs_matching(tmp_path, "", recursive=True)

    assert {m.path.name for m in result.matches} == {
        "acme.pdf", "zenith.pdf", "plain.pdf", "acme_nested.pdf",
    }
    assert all(m.snippet == "" for m in result.matches)
    assert result.scanned == 4
    assert not result.errors


def test_query_matches_only_the_ico_header_not_the_rest_of_the_page(tmp_path: Path) -> None:
    _populate(tmp_path)
    result = find_pdfs_matching(tmp_path, "Acme", recursive=True)

    matched_names = {m.path.name for m in result.matches}
    assert matched_names == {"acme.pdf", "acme_nested.pdf"}
    assert all("Acme Development GmbH" in m.snippet for m in result.matches)
    assert result.scanned == 4  # every pdf was opened and checked


def test_query_is_case_insensitive() -> None:
    result = find_pdfs_matching(FIXTURES, "acme development", recursive=False)
    assert any(m.path.name == "merge_search_ico_acme.pdf" for m in result.matches)


def test_query_does_not_match_a_developer_only_mentioned_in_the_body(tmp_path: Path) -> None:
    # "Welcome to the document." is real page-1 body text in the fixture,
    # OUTSIDE the ICO header chunk (see test_pdf_ico_header_search.py) -
    # must not match.
    _populate(tmp_path)
    result = find_pdfs_matching(tmp_path, "Welcome to the document", recursive=True)
    assert result.matches == []


def test_respects_recursive_flag(tmp_path: Path) -> None:
    _populate(tmp_path)
    result = find_pdfs_matching(tmp_path, "Acme", recursive=False)
    assert {m.path.name for m in result.matches} == {"acme.pdf"}


def test_unreadable_file_is_reported_as_error_not_a_crash(tmp_path: Path) -> None:
    shutil.copy(ICO_ACME, tmp_path / "acme.pdf")
    (tmp_path / "corrupt.pdf").write_bytes(b"not a real pdf")

    result = find_pdfs_matching(tmp_path, "Acme", recursive=False)

    assert {m.path.name for m in result.matches} == {"acme.pdf"}
    assert len(result.errors) == 1
    assert "corrupt.pdf" in result.errors[0]
    assert result.scanned == 2


def test_progress_callback_reports_index_total_and_filename(tmp_path: Path) -> None:
    _populate(tmp_path)
    calls: list[tuple[int, int, str]] = []
    find_pdfs_matching(tmp_path, "Acme", recursive=True, progress_callback=lambda *args: calls.append(args))

    assert len(calls) == 4
    assert all(total == 4 for _, total, _ in calls)
    assert [index for index, _, _ in calls] == [0, 1, 2, 3]


def test_cancellation_keeps_matches_found_so_far(tmp_path: Path) -> None:
    _populate(tmp_path)
    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 2  # cancel partway through the 4-file scan

    result = find_pdfs_matching(tmp_path, "", recursive=True, should_cancel=should_cancel)

    assert result.cancelled
    assert result.scanned == 2
    assert len(result.matches) == 2
