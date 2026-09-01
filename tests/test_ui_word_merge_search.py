"""Covers ui/merge_search.py's DOCX wrappers (find_docx_files()/
find_docx_files_matching(), 01.09.2026) - thin wrapper wiring tests only;
the underlying find_files_by_extension()/find_matching() engine itself is
already exercised thoroughly by tests/test_ui_merge_search.py's PDF
coverage (recursive/flat, empty vs. non-empty query, case-insensitivity,
errors, progress, cancellation all apply identically since that engine is
shared - see ui/merge_search.py's module docstring).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ui.merge_search import find_docx_files, find_docx_files_matching

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.docx"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.docx"
PLAIN = FIXTURES / "merge_search_plain.docx"


def _populate(root: Path) -> None:
    shutil.copy(ICO_ACME, root / "acme.docx")
    shutil.copy(ICO_ZENITH, root / "zenith.docx")
    shutil.copy(PLAIN, root / "plain.docx")
    (root / "notes.txt").write_text("not a docx")
    sub = root / "subfolder"
    sub.mkdir()
    shutil.copy(ICO_ACME, sub / "acme_nested.docx")


def test_find_docx_files_recursive_vs_flat(tmp_path: Path) -> None:
    _populate(tmp_path)

    recursive = find_docx_files(tmp_path, recursive=True)
    assert {p.name for p in recursive} == {"acme.docx", "zenith.docx", "plain.docx", "acme_nested.docx"}

    flat = find_docx_files(tmp_path, recursive=False)
    assert {p.name for p in flat} == {"acme.docx", "zenith.docx", "plain.docx"}


def test_find_docx_files_matching_filters_by_ico_header_only(tmp_path: Path) -> None:
    _populate(tmp_path)

    result = find_docx_files_matching(tmp_path, "Acme Development", recursive=True)

    assert {m.path.name for m in result.matches} == {"acme.docx", "acme_nested.docx"}
    assert all("Acme Development" in m.snippet for m in result.matches)


def test_find_docx_files_matching_empty_query_returns_every_docx(tmp_path: Path) -> None:
    _populate(tmp_path)

    result = find_docx_files_matching(tmp_path, "", recursive=True)

    assert {m.path.name for m in result.matches} == {"acme.docx", "zenith.docx", "plain.docx", "acme_nested.docx"}
    assert result.scanned == 4
