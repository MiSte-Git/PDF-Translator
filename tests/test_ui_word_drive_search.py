"""Covers ui/drive_search.py's DOCX wrapper (find_drive_docx_matching(),
01.09.2026, Michael: "Jetzt noch das ganze für *.docx.") - thin wrapper
wiring tests only; the shared find_drive_matching() engine itself is
already exercised thoroughly by tests/test_ui_drive_search.py's PDF
coverage (recursive/flat, empty vs. non-empty query, cache-dir
keep/discard, collisions, errors, progress, cancellation all apply
identically since that engine is shared).
"""
from __future__ import annotations

from pathlib import Path

from pipeline.drive_auth import DOCX_MIME_TYPE, DriveEntry
from ui.drive_search import find_drive_docx_matching

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.docx"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.docx"
PLAIN = FIXTURES / "merge_search_plain.docx"


class _FakeDriveClient:
    def __init__(self, tree: dict[str, list[DriveEntry]], contents: dict[str, bytes]) -> None:
        self._tree = tree
        self._contents = contents
        self.mime_types_requested: list[str] = []

    def list_children(self, folder_id: str, file_mime_type: str = ""):
        self.mime_types_requested.append(file_mime_type)
        return iter(self._tree.get(folder_id, []))

    def download(self, file_id: str, destination: Path) -> None:
        destination.write_bytes(self._contents[file_id])


def _flat_client() -> _FakeDriveClient:
    tree = {
        "root": [
            DriveEntry(id="acme", name="Acme.docx", is_folder=False),
            DriveEntry(id="zenith", name="Zenith.docx", is_folder=False),
            DriveEntry(id="plain", name="Plain.docx", is_folder=False),
        ]
    }
    contents = {
        "acme": ICO_ACME.read_bytes(),
        "zenith": ICO_ZENITH.read_bytes(),
        "plain": PLAIN.read_bytes(),
    }
    return _FakeDriveClient(tree, contents)


def test_requests_the_docx_mime_type_not_pdf(tmp_path: Path) -> None:
    client = _flat_client()
    find_drive_docx_matching(client, "root", "", recursive=True, cache_dir=tmp_path)
    assert client.mime_types_requested == [DOCX_MIME_TYPE]


def test_matches_only_the_ico_header_region_and_keeps_docx_extension(tmp_path: Path) -> None:
    client = _flat_client()
    result = find_drive_docx_matching(client, "root", "Zenith Capital", recursive=True, cache_dir=tmp_path)
    assert [m.drive_name for m in result.matches] == ["Zenith.docx"]
    match = result.matches[0]
    assert match.local_path.suffix == ".docx"
    assert match.local_path.exists()


def test_empty_query_takes_every_docx_found(tmp_path: Path) -> None:
    client = _flat_client()
    result = find_drive_docx_matching(client, "root", "", recursive=True, cache_dir=tmp_path)
    assert {m.drive_name for m in result.matches} == {"Acme.docx", "Zenith.docx", "Plain.docx"}
