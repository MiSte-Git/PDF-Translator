"""Covers pipeline/word/merge.py - the DOCX merge/insert feature
(01.09.2026, Michael: "Jetzt noch das ganze für *.docx. Kann man
überhaupt mittlerweile ca. 2000 docx zusammenführen?"). Mirrors
tests/test_pdf_merge.py's coverage where the same concepts apply
(order, dedup counting, cancellation keeps a partial result, hard vs.
soft per-file failure) and adds DOCX-specific coverage for the
two-level batching architecture Michael explicitly confirmed
("automatisch batchen").

Fixtures used here are the plain synthetic .docx files built inline
below via python-docx (see _make_docx()) - the module-level "only
pipeline/word/merge.py imports docx" rule (see that module's docstring)
has the same narrow, documented test-fixture exception
tests/test_pdf_ico_mode.py already established for fitz/PyMuPDF.
"""
from __future__ import annotations

from pathlib import Path

import docx
import pytest

from pipeline.word.merge import DEFAULT_BATCH_SIZE, WordMergeStats, merge_docx_files


def _make_docx(path: Path, text: str) -> Path:
    document = docx.Document()
    document.add_paragraph(text)
    document.save(str(path))
    return path


def _paragraph_texts(path: Path) -> list[str]:
    return [p.text for p in docx.Document(str(path)).paragraphs]


def test_merge_preserves_source_order(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "First document")
    b = _make_docx(tmp_path / "b.docx", "Second document")
    c = _make_docx(tmp_path / "c.docx", "Third document")
    destination = tmp_path / "out.docx"

    stats = merge_docx_files([a, b, c], destination)

    texts = [t for t in _paragraph_texts(destination) if t]
    assert texts == ["First document", "Second document", "Third document"]
    assert stats == WordMergeStats(segments=3, files_processed=3, batches=0, cancelled=False, warnings=[])


def test_merge_inserts_a_page_break_between_sources(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "First document")
    b = _make_docx(tmp_path / "b.docx", "Second document")
    destination = tmp_path / "out.docx"

    merge_docx_files([a, b], destination)

    document = docx.Document(str(destination))
    xml = document.element.body.xml
    assert 'w:type="page"' in xml  # the <w:br w:type="page"/> from add_page_break()


def test_single_source_has_no_page_break(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "Only document")
    destination = tmp_path / "out.docx"

    merge_docx_files([a], destination)

    document = docx.Document(str(destination))
    assert 'w:type="page"' not in document.element.body.xml
    assert [p.text for p in document.paragraphs if p.text] == ["Only document"]


def test_same_file_listed_twice_counts_once_in_files_processed(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "Repeated document")
    destination = tmp_path / "out.docx"

    stats = merge_docx_files([a, a], destination)

    assert stats.segments == 2  # appended twice - the "insert same file again" use case
    assert stats.files_processed == 1  # but it's the same resolved path


def test_empty_sources_list_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        merge_docx_files([], tmp_path / "out.docx")


def test_destination_parent_directory_is_created(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "Doc")
    destination = tmp_path / "nested" / "deeper" / "out.docx"

    merge_docx_files([a], destination)

    assert destination.exists()


def test_unopenable_source_aborts_the_whole_merge(tmp_path: Path) -> None:
    a = _make_docx(tmp_path / "a.docx", "Good document")
    bad = tmp_path / "bad.docx"
    bad.write_text("not a docx at all")
    destination = tmp_path / "out.docx"

    with pytest.raises(ValueError, match="bad.docx"):
        merge_docx_files([a, bad], destination)
    assert not destination.exists()


def test_append_failure_is_skipped_with_a_warning_not_aborted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a = _make_docx(tmp_path / "a.docx", "First document")
    b = _make_docx(tmp_path / "b.docx", "Problem document")
    c = _make_docx(tmp_path / "c.docx", "Third document")
    destination = tmp_path / "out.docx"

    from docxcompose.composer import Composer

    original_append = Composer.append
    call_count = {"n": 0}

    def flaky_append(self, doc, remove_property_fields=True):
        call_count["n"] += 1
        if call_count["n"] == 1:  # the second source (b.docx) - first call to append()
            raise RuntimeError("simulated docxcompose SmartArt failure")
        return original_append(self, doc, remove_property_fields=remove_property_fields)

    monkeypatch.setattr(Composer, "append", flaky_append)

    stats = merge_docx_files([a, b, c], destination)

    texts = [t for t in _paragraph_texts(destination) if t]
    assert texts == ["First document", "Third document"]  # b.docx skipped, merge continued
    assert stats.segments == 2
    assert len(stats.warnings) == 1
    assert "b.docx" in stats.warnings[0]


def test_below_batch_size_uses_a_single_pass_with_no_batches(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(3)]
    destination = tmp_path / "out.docx"

    stats = merge_docx_files(sources, destination, batch_size=10)

    assert stats.batches == 0


def test_above_batch_size_uses_two_level_batching_and_preserves_order(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(7)]
    destination = tmp_path / "out.docx"

    stats = merge_docx_files(sources, destination, batch_size=3)

    assert stats.batches == 3  # ceil(7/3)
    assert stats.segments == 7
    texts = [t for t in _paragraph_texts(destination) if t]
    assert texts == [f"Doc {i}" for i in range(7)]


def test_default_batch_size_is_used_when_not_specified(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(3)]
    destination = tmp_path / "out.docx"

    stats = merge_docx_files(sources, destination)

    assert DEFAULT_BATCH_SIZE > 3
    assert stats.batches == 0  # comfortably below the default batch size


def test_cancellation_within_the_first_batch_keeps_only_what_completed(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(6)]
    destination = tmp_path / "out.docx"

    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 2  # stop after the first 2 files of batch 1

    stats = merge_docx_files(sources, destination, batch_size=3, should_cancel=should_cancel)

    assert stats.cancelled is True
    texts = [t for t in _paragraph_texts(destination) if t]
    assert texts == ["Doc 0", "Doc 1"]


def test_cancellation_after_the_first_batch_keeps_every_completed_batch(tmp_path: Path) -> None:
    """Regression guard: an earlier version of this code only kept the
    FIRST completed batch on cancellation (the second-level "merge the
    chunks" pass polled the same should_cancel, which - being a
    threading.Event in real use - stays set once tripped, so it
    immediately bailed out and silently discarded every batch after the
    first). Cancelling partway through batch 2 of 3 must still keep both
    fully-completed batch 1 AND the partial work done in batch 2, not
    just batch 1.
    """
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(9)]
    destination = tmp_path / "out.docx"

    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 4  # completes batch 1 (3 files) + 1 file into batch 2

    stats = merge_docx_files(sources, destination, batch_size=3, should_cancel=should_cancel)

    assert stats.cancelled is True
    assert stats.batches == 2
    texts = [t for t in _paragraph_texts(destination) if t]
    assert texts == ["Doc 0", "Doc 1", "Doc 2", "Doc 3"]


def test_cancellation_before_any_file_is_appended_raises(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(3)]
    destination = tmp_path / "out.docx"

    with pytest.raises(ValueError):
        merge_docx_files(sources, destination, should_cancel=lambda: True)


def test_progress_callback_reports_file_and_batch_messages(tmp_path: Path) -> None:
    sources = [_make_docx(tmp_path / f"f{i}.docx", f"Doc {i}") for i in range(5)]
    destination = tmp_path / "out.docx"
    messages: list[str] = []

    merge_docx_files(sources, destination, batch_size=2, progress_callback=messages.append)

    assert any("Batch" in m for m in messages)
    assert any("f0.docx" in m for m in messages)
    assert any("Zwischenergebnisse" in m for m in messages)
