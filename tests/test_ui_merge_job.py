"""Covers ui/merge_job.py - the destination-safety + pre-flight-validation
layer on top of pipeline/pdf/pymupdf_engine.py's merge_pdfs() (see
tests/test_pdf_merge.py for the underlying engine's own coverage, and
ui/merge_job.py's module docstring for why this isn't built on
TranslationRequest like the other *_job.py modules).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.pdf.pymupdf_engine import MergeSourceSpec
from ui.document_job_common import DestinationConflictError
from ui.merge_job import run_merge_job, validate_merge_sources

FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_A = FIXTURES / "merge_source_a.pdf"
SOURCE_B = FIXTURES / "merge_source_b.pdf"


def test_validate_merge_sources_empty_list() -> None:
    errors = validate_merge_sources([], Path("out.pdf"))
    assert any("Quelldatei" in error for error in errors)


def test_validate_merge_sources_missing_file(tmp_path: Path) -> None:
    errors = validate_merge_sources([MergeSourceSpec(tmp_path / "missing.pdf")], tmp_path / "out.pdf")
    assert any("nicht gefunden" in error for error in errors)


def test_validate_merge_sources_wrong_extension(tmp_path: Path) -> None:
    not_a_pdf = tmp_path / "notes.txt"
    not_a_pdf.write_text("x")
    errors = validate_merge_sources([MergeSourceSpec(not_a_pdf)], tmp_path / "out.pdf")
    assert any("keine PDF-Datei" in error for error in errors)


def test_validate_merge_sources_missing_destination() -> None:
    errors = validate_merge_sources([MergeSourceSpec(SOURCE_A)], None)
    assert any("Zieldatei fehlt" in error for error in errors)


def test_validate_merge_sources_destination_wrong_extension(tmp_path: Path) -> None:
    errors = validate_merge_sources([MergeSourceSpec(SOURCE_A)], tmp_path / "out.docx")
    assert any(".pdf" in error for error in errors)


def test_validate_merge_sources_valid_request(tmp_path: Path) -> None:
    assert validate_merge_sources([MergeSourceSpec(SOURCE_A)], tmp_path / "out.pdf") == []


def test_run_merge_job_writes_output(tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    result = run_merge_job([MergeSourceSpec(SOURCE_A), MergeSourceSpec(SOURCE_B)], destination)

    assert result.output_path == destination
    assert destination.exists()
    assert result.stats.pages_written == 8
    assert result.stats.files_processed == 2


def test_run_merge_job_rejects_destination_equal_to_a_source(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(SOURCE_A.read_bytes())
    with pytest.raises(DestinationConflictError):
        run_merge_job([MergeSourceSpec(source)], source)


def test_run_merge_job_overwrites_an_existing_destination(tmp_path: Path) -> None:
    # Deliberately allowed, unlike run_pdf_job() - see run_merge_job()'s
    # docstring: the native Save dialog already confirms this with the
    # user before run_merge_job() is ever called.
    destination = tmp_path / "merged.pdf"
    destination.write_bytes(b"already here, not even a real PDF")
    result = run_merge_job([MergeSourceSpec(SOURCE_A)], destination)
    assert result.stats.pages_written == 5
