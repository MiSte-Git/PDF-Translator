"""Covers ui/word_merge_job.py - the destination-safety + pre-flight-
validation layer on top of pipeline/word/merge.py's merge_docx_files()
(see tests/test_word_merge.py for the underlying engine's own coverage,
and ui/word_merge_job.py's module docstring for how this differs from
ui/merge_job.py: no page-range concept at all, since DOCX merge is
whole-file only, 01.09.2026).
"""
from __future__ import annotations

from pathlib import Path

import docx
import pytest

from ui.document_job_common import DestinationConflictError
from ui.word_merge_job import run_word_merge_job, validate_merge_word_sources


def _make_docx(path: Path, text: str) -> Path:
    document = docx.Document()
    document.add_paragraph(text)
    document.save(str(path))
    return path


def test_validate_merge_word_sources_empty_list() -> None:
    errors = validate_merge_word_sources([], Path("out.docx"))
    assert any("Quelldatei" in error for error in errors)


def test_validate_merge_word_sources_missing_file(tmp_path: Path) -> None:
    errors = validate_merge_word_sources([tmp_path / "missing.docx"], tmp_path / "out.docx")
    assert any("nicht gefunden" in error for error in errors)


def test_validate_merge_word_sources_wrong_extension(tmp_path: Path) -> None:
    not_a_docx = tmp_path / "notes.txt"
    not_a_docx.write_text("x")
    errors = validate_merge_word_sources([not_a_docx], tmp_path / "out.docx")
    assert any("keine DOCX-Datei" in error for error in errors)


def test_validate_merge_word_sources_missing_destination(tmp_path: Path) -> None:
    source = _make_docx(tmp_path / "a.docx", "A")
    errors = validate_merge_word_sources([source], None)
    assert any("Zieldatei fehlt" in error for error in errors)


def test_validate_merge_word_sources_destination_wrong_extension(tmp_path: Path) -> None:
    source = _make_docx(tmp_path / "a.docx", "A")
    errors = validate_merge_word_sources([source], tmp_path / "out.pdf")
    assert any(".docx" in error for error in errors)


def test_validate_merge_word_sources_valid_request(tmp_path: Path) -> None:
    source = _make_docx(tmp_path / "a.docx", "A")
    assert validate_merge_word_sources([source], tmp_path / "out.docx") == []


def test_run_word_merge_job_writes_output(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "First")
    b = _make_docx(tmp_path / "b.docx", "Second")
    destination = tmp_path / "merged.docx"

    result = run_word_merge_job([a, b], destination)

    assert result.output_path == destination
    assert destination.exists()
    assert result.stats.segments == 2
    assert result.stats.files_processed == 2
    assert result.stats.batches == 0


def test_run_word_merge_job_rejects_destination_equal_to_a_source(tmp_path: Path) -> None:
    source = _make_docx(tmp_path / "a.docx", "A")
    with pytest.raises(DestinationConflictError):
        run_word_merge_job([source], source)


def test_run_word_merge_job_overwrites_an_existing_destination(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "First")
    destination = tmp_path / "merged.docx"
    destination.write_bytes(b"already here, not even a real docx")

    result = run_word_merge_job([a], destination)

    assert result.stats.files_processed == 1


def test_run_word_merge_job_passes_batch_size_through(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"s{i}.docx", f"Doc {i}") for i in range(5)]
    destination = tmp_path / "merged.docx"

    result = run_word_merge_job(sources, destination, batch_size=2)

    assert result.stats.batches == 3  # ceil(5/2), mirrors test_word_merge.py's batching coverage
    assert result.stats.segments == 5
