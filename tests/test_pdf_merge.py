"""Covers pipeline/pdf/pymupdf_engine.py's merge_pdfs()/parse_page_selection()
(01.09.2026, Backlog.md 26.08.2026's "PDFs zusammenführen / PDFs
zwischeneinfügen" - see merge_pdfs()'s own docstring for the feature's
shape and open decisions).

FIXTURE files (tests/fixtures/merge_source_a.pdf: 5 pages "A page 1".."A
page 5" with one TOC entry per page; merge_source_b.pdf: 3 pages "B page
1".."B page 3", no TOC) are checked in as real files, generated once the
same way tests/fixtures/representative.pdf already is - see that fixture's
own comment in tests/test_pdf_job.py.

This file (and only this file, besides pipeline/pdf/pymupdf_engine.py
itself) imports `pymupdf` directly - an intentional, narrow exception to
that module's "only file allowed to import PyMuPDF" rule: verifying
merge_pdfs()'s actual output (page order/content, TOC structure) requires
raw PDF introspection that has nothing to do with the engine-swap
abstraction that rule protects (pipeline/pdf/base.py's PdfEngine has no
page-count/TOC surface at all - it was never meant to need one before this
feature existed).
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pipeline.pdf.pymupdf_engine import MergeSourceSpec, merge_pdfs, parse_page_selection

FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_A = FIXTURES / "merge_source_a.pdf"  # 5 pages, own per-page TOC
SOURCE_B = FIXTURES / "merge_source_b.pdf"  # 3 pages, no TOC


def _read_back(path: Path) -> tuple[list[str], list[list]]:
    """Test-only helper: page texts (in order) and simple TOC of a merged
    output file, for assertions below."""
    doc = fitz.open(str(path))
    try:
        texts = [doc.load_page(i).get_text().strip() for i in range(doc.page_count)]
        toc = doc.get_toc(simple=True)
    finally:
        doc.close()
    return texts, toc


# --- parse_page_selection() -------------------------------------------------


@pytest.mark.parametrize(
    "spec, page_count, expected",
    [
        ("", 5, [0, 1, 2, 3, 4]),
        ("1-3", 5, [0, 1, 2]),
        ("3-1", 5, [2, 1, 0]),  # deliberately reversed
        ("2,4", 5, [1, 3]),
        ("3-", 5, [2, 3, 4]),  # open-ended: to the last page
        ("-2", 5, [0, 1]),  # open-ended: from the first page
        (" 1 , 2 - 3 ", 5, [0, 1, 2]),  # whitespace tolerated
        ("1,1", 5, [0, 0]),  # explicit repetition allowed
    ],
)
def test_parse_page_selection_valid(spec: str, page_count: int, expected: list[int]) -> None:
    assert parse_page_selection(spec, page_count) == expected


@pytest.mark.parametrize(
    "spec, page_count",
    [
        ("0", 5),  # below range
        ("6", 5),  # above range
        ("abc", 5),  # not a number
        ("1-6", 5),  # range end out of bounds
        ("1", 0),  # non-empty spec against a 0-page file
    ],
)
def test_parse_page_selection_invalid(spec: str, page_count: int) -> None:
    with pytest.raises(ValueError):
        parse_page_selection(spec, page_count)


# --- merge_pdfs() ------------------------------------------------------------


def test_merge_whole_files_in_order(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    stats = merge_pdfs([MergeSourceSpec(SOURCE_A), MergeSourceSpec(SOURCE_B)], destination)

    assert stats.segments == 2
    assert stats.files_processed == 2
    assert stats.pages_written == 8
    assert not stats.cancelled
    texts, toc = _read_back(destination)
    assert texts == [f"A page {i}" for i in range(1, 6)] + [f"B page {i}" for i in range(1, 4)]
    # A's own per-page TOC survives, offset by 0; B has no TOC, so it gets
    # exactly one synthesized top-level entry at the point it was inserted.
    assert toc == [[1, f"A Chapter {i}", i] for i in range(1, 6)] + [[1, "merge_source_b.pdf", 6]]


def test_merge_selected_pages_only(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    stats = merge_pdfs([MergeSourceSpec(SOURCE_A, pages="2,4")], destination)

    assert stats.pages_written == 2
    texts, toc = _read_back(destination)
    assert texts == ["A page 2", "A page 4"]
    # Selecting a subset still carries the matching (renumbered) TOC
    # entries from the source's own outline - no synthesized fallback here.
    assert toc == [[1, "A Chapter 2", 1], [1, "A Chapter 4", 2]]


def test_insert_between_pages_of_the_same_file(tmp_path: Path) -> None:
    """The "zwischeneinfügen" case: B's pages inserted into the middle of
    A, expressed as A split into two segments around the insertion point -
    no separate "insert" code path, see the module docstring."""
    destination = tmp_path / "merged.pdf"
    stats = merge_pdfs(
        [
            MergeSourceSpec(SOURCE_A, pages="1-2"),
            MergeSourceSpec(SOURCE_B),
            MergeSourceSpec(SOURCE_A, pages="3-5"),
        ],
        destination,
    )

    assert stats.segments == 3
    assert stats.files_processed == 2  # A counted once despite 2 segments
    texts, _ = _read_back(destination)
    assert texts == ["A page 1", "A page 2", "B page 1", "B page 2", "B page 3", "A page 3", "A page 4", "A page 5"]


def test_merge_reversed_range(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    merge_pdfs([MergeSourceSpec(SOURCE_A, pages="3-1")], destination)
    texts, _ = _read_back(destination)
    assert texts == ["A page 3", "A page 2", "A page 1"]


def test_merge_missing_source_file_raises_named_error(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(ValueError, match="does_not_exist.pdf"):
        merge_pdfs([MergeSourceSpec(missing)], destination)
    assert not destination.exists()


def test_merge_invalid_page_range_raises_before_writing(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    with pytest.raises(ValueError, match="außerhalb"):
        merge_pdfs([MergeSourceSpec(SOURCE_A, pages="1-99")], destination)
    assert not destination.exists()


def test_merge_empty_sources_list_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        merge_pdfs([], tmp_path / "merged.pdf")


def test_merge_cancellation_keeps_partial_result(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    # Cancel right before the SECOND source would be processed - mirrors
    # translate_pdf()'s between-block (here: between-source) polling.
    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    stats = merge_pdfs(
        [MergeSourceSpec(SOURCE_A), MergeSourceSpec(SOURCE_B)], destination, should_cancel=should_cancel
    )

    assert stats.cancelled
    assert stats.segments == 1
    assert stats.pages_written == 5
    texts, _ = _read_back(destination)
    assert texts == [f"A page {i}" for i in range(1, 6)]


def test_merge_reports_progress_per_source(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    messages: list[str] = []
    merge_pdfs(
        [MergeSourceSpec(SOURCE_A), MergeSourceSpec(SOURCE_B)],
        destination,
        progress_callback=messages.append,
    )
    assert messages == [
        "Datei 1/2: merge_source_a.pdf",
        "Datei 2/2: merge_source_b.pdf",
    ]
