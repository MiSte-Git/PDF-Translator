"""Covers the 02.09.2026 `scopes` parameter on find_drive_pdfs_matching()/
find_drive_docx_matching() (ui/drive_search.py) - the Drive counterpart of
tests/test_ui_merge_search_scopes.py. Uses the same in-memory
_FakeDriveClient pattern as tests/test_ui_drive_search.py.
"""
from __future__ import annotations

from pathlib import Path

from pipeline.drive_auth import DriveEntry
from ui.drive_search import find_drive_docx_matching, find_drive_pdfs_matching
from ui.search_scopes import SCOPE_FULL_TEXT, SCOPE_HEADER, SCOPE_ICO_FORMAT

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME_PDF = FIXTURES / "merge_search_ico_acme.pdf"  # ICO-metadata-only: "Issuer Address: Acme Development GmbH"
ICO_WITH_HEADER_DOCX = FIXTURES / "representative_ico.docx"  # header2.xml: "QSI ICO: TESTMARK"


class _FakeDriveClient:
    def __init__(self, tree: dict[str, list[DriveEntry]], contents: dict[str, bytes]) -> None:
        self._tree = tree
        self._contents = contents

    def list_children(self, folder_id: str, file_mime_type: str = ""):
        return iter(self._tree.get(folder_id, []))

    def download(self, file_id: str, destination: Path) -> None:
        destination.write_bytes(self._contents[file_id])


def test_scopes_none_keeps_the_original_ico_format_only_behavior(tmp_path: Path) -> None:
    client = _FakeDriveClient(
        {"root": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)]},
        {"acme": ICO_ACME_PDF.read_bytes()},
    )
    result = find_drive_pdfs_matching(client, "root", "Welcome to the document", recursive=True, cache_dir=tmp_path)
    assert result.matches == []


def test_full_text_scope_widens_matching_to_the_whole_document(tmp_path: Path) -> None:
    client = _FakeDriveClient(
        {"root": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)]},
        {"acme": ICO_ACME_PDF.read_bytes()},
    )
    result = find_drive_pdfs_matching(
        client, "root", "Welcome to the document", recursive=True, cache_dir=tmp_path, scopes={SCOPE_FULL_TEXT}
    )
    assert [m.drive_name for m in result.matches] == ["Acme.pdf"]


def test_no_scopes_selected_never_matches_a_non_empty_query(tmp_path: Path) -> None:
    client = _FakeDriveClient(
        {"root": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)]},
        {"acme": ICO_ACME_PDF.read_bytes()},
    )
    result = find_drive_pdfs_matching(client, "root", "Acme", recursive=True, cache_dir=tmp_path, scopes=set())
    assert result.matches == []


def test_or_query_matches_if_either_term_is_present(tmp_path: Path) -> None:
    client = _FakeDriveClient(
        {"root": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)]},
        {"acme": ICO_ACME_PDF.read_bytes()},
    )
    result = find_drive_pdfs_matching(client, "root", "Zenith OR Acme", recursive=True, cache_dir=tmp_path)
    assert [m.drive_name for m in result.matches] == ["Acme.pdf"]


def test_docx_header_scope_finds_the_real_word_header(tmp_path: Path) -> None:
    client = _FakeDriveClient(
        {"root": [DriveEntry(id="ico", name="Ico.docx", is_folder=False)]},
        {"ico": ICO_WITH_HEADER_DOCX.read_bytes()},
    )
    result = find_drive_docx_matching(
        client, "root", "TESTMARK", recursive=True, cache_dir=tmp_path, scopes={SCOPE_HEADER}
    )
    assert [m.drive_name for m in result.matches] == ["Ico.docx"]
