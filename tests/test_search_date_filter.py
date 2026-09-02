"""Covers the `date_filter` parameter added 02.09.2026 to
find_pdfs_matching()/find_docx_files_matching() (ui/merge_search.py) and
find_drive_pdfs_matching() (ui/drive_search.py) - Michael: "Können wir
noch eine nach Datumsbereich, von, bis, exakt einbauen." See
pipeline/date_extract.py's module docstring for the confirmed design
(one source per search: SOURCE_FILE or SOURCE_DOCUMENT).
"""
from __future__ import annotations

import os
import shutil
import time
from datetime import date
from pathlib import Path

import pytest

from pipeline.date_extract import (
    SOURCE_DOCUMENT,
    SOURCE_FILE,
    DateRange,
    DateSearchFilter,
)
from pipeline.drive_auth import DriveEntry
from ui.drive_search import find_drive_pdfs_matching
from ui.merge_search import find_docx_files_matching, find_pdfs_matching
from ui.search_scopes import DATE_REGION_FOOTER, DATE_REGION_HEADER

FIXTURES = Path(__file__).parent / "fixtures"
ICO_ACME = FIXTURES / "merge_search_ico_acme.pdf"
ICO_ZENITH = FIXTURES / "merge_search_ico_zenith.pdf"
ICO_ACME_DOCX = FIXTURES / "merge_search_ico_acme.docx"


def _copy_with_mtime(source: Path, dest_dir: Path, name: str, day: date) -> Path:
    dest = dest_dir / name
    shutil.copy(source, dest)
    mtime = time.mktime(day.timetuple())
    os.utime(dest, (mtime, mtime))
    return dest


# --- SOURCE_FILE, local folder scan (find_pdfs_matching) -------------------


def test_file_date_range_keeps_only_files_modified_in_range(tmp_path: Path) -> None:
    _copy_with_mtime(ICO_ACME, tmp_path, "old.pdf", date(2020, 1, 1))
    _copy_with_mtime(ICO_ZENITH, tmp_path, "recent.pdf", date(2026, 6, 15))

    date_filter = DateSearchFilter(source=SOURCE_FILE, date_range=DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31)))
    result = find_pdfs_matching(tmp_path, "", recursive=False, date_filter=date_filter)

    names = {match.path.name for match in result.matches}
    assert names == {"recent.pdf"}


def test_file_date_exact_day_keeps_only_that_day(tmp_path: Path) -> None:
    _copy_with_mtime(ICO_ACME, tmp_path, "on_day.pdf", date(2026, 9, 1))
    _copy_with_mtime(ICO_ZENITH, tmp_path, "off_day.pdf", date(2026, 9, 2))

    exact = date(2026, 9, 1)
    date_filter = DateSearchFilter(source=SOURCE_FILE, date_range=DateRange(start=exact, end=exact))
    result = find_pdfs_matching(tmp_path, "", recursive=False, date_filter=date_filter)

    assert {match.path.name for match in result.matches} == {"on_day.pdf"}


def test_file_date_filter_combines_with_text_query(tmp_path: Path) -> None:
    # A file must satisfy BOTH the text query and the date filter.
    _copy_with_mtime(ICO_ACME, tmp_path, "acme_in_range.pdf", date(2026, 6, 1))
    _copy_with_mtime(ICO_ACME, tmp_path, "acme_out_of_range.pdf", date(2020, 1, 1))
    _copy_with_mtime(ICO_ZENITH, tmp_path, "zenith_in_range.pdf", date(2026, 6, 1))

    date_filter = DateSearchFilter(source=SOURCE_FILE, date_range=DateRange(start=date(2026, 1, 1)))
    result = find_pdfs_matching(tmp_path, "Acme", recursive=False, date_filter=date_filter)

    assert {match.path.name for match in result.matches} == {"acme_in_range.pdf"}


def test_no_date_filter_means_unaffected_by_file_dates(tmp_path: Path) -> None:
    _copy_with_mtime(ICO_ACME, tmp_path, "old.pdf", date(2000, 1, 1))
    result = find_pdfs_matching(tmp_path, "", recursive=False, date_filter=None)
    assert {match.path.name for match in result.matches} == {"old.pdf"}


# --- SOURCE_DOCUMENT, local folder scan -------------------------------------


def test_document_date_source_reads_the_selected_region(tmp_path: Path) -> None:
    import pymupdf as fitz

    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=400, height=600)
        page.insert_text((50, 40), "Company Confidential - Internal Use Only", fontsize=10, fontname="helv")
        page.insert_text((50, 200), f"Body {i}", fontsize=11, fontname="helv")
        page.insert_text((50, 560), "Ausstellungsdatum: 2026-09-01", fontsize=8, fontname="helv")
    source = tmp_path / "dated.pdf"
    doc.save(str(source))
    doc.close()

    in_range = DateSearchFilter(
        source=SOURCE_DOCUMENT, date_range=DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31)),
        regions=frozenset({DATE_REGION_FOOTER}),
    )
    result = find_pdfs_matching(tmp_path, "", recursive=False, date_filter=in_range)
    assert {match.path.name for match in result.matches} == {"dated.pdf"}

    # Selecting the HEADER region instead must not find the footer's date.
    header_only = DateSearchFilter(
        source=SOURCE_DOCUMENT, date_range=DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31)),
        regions=frozenset({DATE_REGION_HEADER}),
    )
    result2 = find_pdfs_matching(tmp_path, "", recursive=False, date_filter=header_only)
    assert result2.matches == []

    out_of_range = DateSearchFilter(
        source=SOURCE_DOCUMENT, date_range=DateRange(start=date(2020, 1, 1), end=date(2020, 12, 31)),
        regions=frozenset({DATE_REGION_FOOTER}),
    )
    result3 = find_pdfs_matching(tmp_path, "", recursive=False, date_filter=out_of_range)
    assert result3.matches == []


# --- DOCX wrapper ------------------------------------------------------


def test_docx_file_date_filter(tmp_path: Path) -> None:
    _copy_with_mtime(ICO_ACME_DOCX, tmp_path, "recent.docx", date(2026, 6, 1))
    date_filter = DateSearchFilter(source=SOURCE_FILE, date_range=DateRange(start=date(2026, 1, 1)))
    result = find_docx_files_matching(tmp_path, "", recursive=False, date_filter=date_filter)
    assert {match.path.name for match in result.matches} == {"recent.docx"}


# --- Drive wrapper: SOURCE_FILE uses Drive's own modifiedTime -------------


class _FakeDriveClient:
    def __init__(self, tree, contents) -> None:
        self._tree = tree
        self._contents = contents

    def list_children(self, folder_id: str, file_mime_type: str = ""):
        return iter(self._tree.get(folder_id, []))

    def download(self, file_id: str, destination: Path) -> None:
        destination.write_bytes(self._contents[file_id])


def test_drive_file_date_filter_uses_drive_modified_time_not_download_time(tmp_path: Path) -> None:
    tree = {
        "root": [
            DriveEntry(id="acme", name="Acme.pdf", is_folder=False, modified_time=date(2026, 6, 15)),
            DriveEntry(id="zenith", name="Zenith.pdf", is_folder=False, modified_time=date(2020, 1, 1)),
        ]
    }
    contents = {"acme": ICO_ACME.read_bytes(), "zenith": ICO_ZENITH.read_bytes()}
    client = _FakeDriveClient(tree, contents)

    date_filter = DateSearchFilter(source=SOURCE_FILE, date_range=DateRange(start=date(2026, 1, 1)))
    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path, date_filter=date_filter)

    assert {match.drive_name for match in result.matches} == {"Acme.pdf"}


def test_drive_file_date_filter_excludes_entries_with_no_modified_time(tmp_path: Path) -> None:
    # A DriveEntry built without modified_time (e.g. resolve_folder()'s
    # own construction, which never requests that field) defaults to
    # None - must never match a file-date filter rather than crashing.
    tree = {"root": [DriveEntry(id="acme", name="Acme.pdf", is_folder=False)]}
    contents = {"acme": ICO_ACME.read_bytes()}
    client = _FakeDriveClient(tree, contents)

    date_filter = DateSearchFilter(source=SOURCE_FILE, date_range=DateRange())
    result = find_drive_pdfs_matching(client, "root", "", recursive=True, cache_dir=tmp_path, date_filter=date_filter)
    assert result.matches == []
