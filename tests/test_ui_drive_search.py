"""Covers ui/drive_search.py - the Google-Drive-Ordnersuche feature's scan/
download orchestration (01.09.2026, Michael: "Können wir eine Google Drive
Ordner durchsuchen?"). Exercised entirely against a small in-memory
_FakeDriveClient (an in-memory folder tree + real PDF bytes taken from the
existing merge_search_ico_*/plain fixtures) rather than a real Google
account - see ui/drive_search.py's DriveClientProtocol and
pipeline/drive_auth.py's own test file for why that split exists.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.drive_auth import DriveEntry
from ui.drive_search import _unique_destination, extract_folder_id, find_drive_pdfs_matching

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.pdf"  # "Issuer Address: Acme Development GmbH"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.pdf"  # "Issuer Address: Zenith Capital Partners"
PLAIN = FIXTURES / "merge_search_plain.pdf"  # no anchor term at all


# --- extract_folder_id() ----------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("https://drive.google.com/drive/folders/1AbC-XyZ_9?usp=sharing", "1AbC-XyZ_9"),
        ("https://drive.google.com/drive/folders/1AbC-XyZ_9", "1AbC-XyZ_9"),
        ("https://drive.google.com/open?id=1AbC-XyZ_9", "1AbC-XyZ_9"),
        ("1AbC-XyZ_9", "1AbC-XyZ_9"),
        ("  1AbC-XyZ_9  ", "1AbC-XyZ_9"),
    ],
)
def test_extract_folder_id_accepts_links_and_bare_ids(text: str, expected: str) -> None:
    assert extract_folder_id(text) == expected


def test_extract_folder_id_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        extract_folder_id("   ")


def test_extract_folder_id_rejects_unrecognized_text() -> None:
    with pytest.raises(ValueError):
        extract_folder_id("https://example.com/not-a-drive-link")


# --- _unique_destination() --------------------------------------------------


def test_unique_destination_uses_the_plain_name_when_free(tmp_path: Path) -> None:
    assert _unique_destination(tmp_path, "Report.pdf", ".pdf") == tmp_path / "Report.pdf"


def test_unique_destination_appends_a_counter_on_collision(tmp_path: Path) -> None:
    (tmp_path / "Report.pdf").write_bytes(b"existing")
    assert _unique_destination(tmp_path, "Report.pdf", ".pdf") == tmp_path / "Report (2).pdf"
    (tmp_path / "Report (2).pdf").write_bytes(b"existing too")
    assert _unique_destination(tmp_path, "Report.pdf", ".pdf") == tmp_path / "Report (3).pdf"


def test_unique_destination_adds_pdf_suffix_if_missing(tmp_path: Path) -> None:
    assert _unique_destination(tmp_path, "NoExtension", ".pdf") == tmp_path / "NoExtension.pdf"


def test_unique_destination_uses_the_given_default_extension(tmp_path: Path) -> None:
    assert _unique_destination(tmp_path, "NoExtension", ".docx") == tmp_path / "NoExtension.docx"


# --- find_drive_pdfs_matching() against a fake client -----------------------


class _FakeDriveClient:
    """folder_id -> list[DriveEntry] tree, plus file_id -> real PDF bytes."""

    def __init__(self, tree: dict[str, list[DriveEntry]], contents: dict[str, bytes]) -> None:
        self._tree = tree
        self._contents = contents
        self.downloaded: list[str] = []

    def list_children(self, folder_id: str, file_mime_type: str = ""):
        return iter(self._tree.get(folder_id, []))

    def download(self, file_id: str, destination: Path) -> None:
        self.downloaded.append(file_id)
        destination.write_bytes(self._contents[file_id])


def _flat_client() -> _FakeDriveClient:
    tree = {
        "root": [
            DriveEntry(id="acme", name="Acme.pdf", is_folder=False),
            DriveEntry(id="zenith", name="Zenith.pdf", is_folder=False),
            DriveEntry(id="plain", name="Plain.pdf", is_folder=False),
        ]
    }
    contents = {
        "acme": ICO_ACME.read_bytes(),
        "zenith": ICO_ZENITH.read_bytes(),
        "plain": PLAIN.read_bytes(),
    }
    return _FakeDriveClient(tree, contents)


def test_empty_query_takes_every_pdf_found(tmp_path: Path) -> None:
    client = _flat_client()
    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path)
    assert {m.drive_name for m in result.matches} == {"Acme.pdf", "Zenith.pdf", "Plain.pdf"}
    assert result.scanned == 3
    assert not result.errors
    # every match ends up as a real, readable file in the cache dir
    for match in result.matches:
        assert match.local_path.exists()
        assert match.local_path.parent == tmp_path


def test_query_matches_only_the_ico_header_region(tmp_path: Path) -> None:
    client = _flat_client()
    result = find_drive_pdfs_matching(client, "root", "Acme Development", recursive=True, cache_dir=tmp_path)
    assert [m.drive_name for m in result.matches] == ["Acme.pdf"]
    assert "Acme Development" in result.matches[0].snippet


def test_query_case_insensitive(tmp_path: Path) -> None:
    client = _flat_client()
    result = find_drive_pdfs_matching(client, "root", "acme development", recursive=True, cache_dir=tmp_path)
    assert [m.drive_name for m in result.matches] == ["Acme.pdf"]


def test_non_matching_files_are_not_kept_in_the_cache_dir(tmp_path: Path) -> None:
    client = _flat_client()
    find_drive_pdfs_matching(client, "root", "Zenith Capital", recursive=True, cache_dir=tmp_path)
    # only the one real match should be sitting in the cache dir afterwards
    assert [p.name for p in tmp_path.iterdir()] == ["Zenith.pdf"]


def test_recursive_true_descends_into_subfolders(tmp_path: Path) -> None:
    tree = {
        "root": [
            DriveEntry(id="sub", name="Subfolder", is_folder=True),
            DriveEntry(id="plain", name="Plain.pdf", is_folder=False),
        ],
        "sub": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)],
    }
    contents = {"plain": PLAIN.read_bytes(), "acme": ICO_ACME.read_bytes()}
    client = _FakeDriveClient(tree, contents)
    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path)
    assert {m.drive_name for m in result.matches} == {"Plain.pdf", "Acme.pdf"}


def test_recursive_false_ignores_subfolders(tmp_path: Path) -> None:
    tree = {
        "root": [
            DriveEntry(id="sub", name="Subfolder", is_folder=True),
            DriveEntry(id="plain", name="Plain.pdf", is_folder=False),
        ],
        "sub": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)],
    }
    contents = {"plain": PLAIN.read_bytes(), "acme": ICO_ACME.read_bytes()}
    client = _FakeDriveClient(tree, contents)
    result = find_drive_pdfs_matching(client, "root", "", recursive=False, cache_dir=tmp_path)
    assert {m.drive_name for m in result.matches} == {"Plain.pdf"}


def test_a_name_collision_between_two_matches_is_kept_not_overwritten(tmp_path: Path) -> None:
    tree = {
        "root": [
            DriveEntry(id="sub1", name="Sub1", is_folder=True),
            DriveEntry(id="sub2", name="Sub2", is_folder=True),
        ],
        "sub1": [DriveEntry(id="a1", name="Term Sheet.pdf", is_folder=False)],
        "sub2": [DriveEntry(id="a2", name="Term Sheet.pdf", is_folder=False)],
    }
    # Both are ICO docs so an empty query keeps both; content differs (acme vs zenith).
    contents = {"a1": ICO_ACME.read_bytes(), "a2": ICO_ZENITH.read_bytes()}
    client = _FakeDriveClient(tree, contents)
    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["Term Sheet (2).pdf", "Term Sheet.pdf"]


def test_download_failure_is_collected_as_an_error_not_a_crash(tmp_path: Path) -> None:
    class _FailingClient(_FakeDriveClient):
        def download(self, file_id: str, destination: Path) -> None:
            if file_id == "acme":
                raise RuntimeError("network blip")
            super().download(file_id, destination)

    client = _FailingClient(
        {"root": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False), DriveEntry(id="plain", name="Plain.pdf", is_folder=False)]},
        {"acme": ICO_ACME.read_bytes(), "plain": PLAIN.read_bytes()},
    )
    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path)
    assert [m.drive_name for m in result.matches] == ["Plain.pdf"]
    assert len(result.errors) == 1
    assert "Acme.pdf" in result.errors[0]


def test_listing_failure_is_reported_without_raising(tmp_path: Path) -> None:
    class _BrokenClient:
        def list_children(self, folder_id: str, file_mime_type: str = ""):
            raise RuntimeError("folder not accessible")

        def download(self, file_id: str, destination: Path) -> None:
            raise AssertionError("must not be called")

    result = find_drive_pdfs_matching(_BrokenClient(), "root", "", recursive=True, cache_dir=tmp_path)
    assert not result.matches
    assert result.errors


def test_progress_reports_a_stable_total_known_up_front(tmp_path: Path) -> None:
    client = _flat_client()
    calls: list[tuple[int, int, str]] = []
    find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path, progress=lambda d, t, c: calls.append((d, t, c)))
    totals = {t for _, t, _ in calls}
    assert totals == {3}  # never changes across the run
    assert calls[0][0] == 0
    assert calls[-1][0] == 3  # final call reports completion


def test_cancellation_stops_between_files_and_reports_partial_result(tmp_path: Path) -> None:
    client = _flat_client()
    calls_made = {"count": 0}

    def is_cancelled() -> bool:
        calls_made["count"] += 1
        return calls_made["count"] > 1  # cancel right after the first file starts

    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path, is_cancelled=is_cancelled)
    assert result.cancelled is True
    assert len(result.matches) < 3
