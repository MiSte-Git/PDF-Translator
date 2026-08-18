"""Coverage for run_pdf_correction_job() (ui/pdf_job.py) - the UI-job
layer wrapping pipeline.pdf.translate_pdf.apply_pdf_corrections() for the
"PDF-Übersetzung korrigieren" workflow (RoadMap.md Phase 2/PDF). Mirrors
tests/test_pdf_job.py's fixture/provider setup so the two files stay easy
to compare (run_pdf_job() produces the records this file's tests apply
corrections to).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import fitz
import pytest

from pipeline.pdf.translate_pdf import build_corrected_records
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.document_job_common import DestinationConflictError
from ui.pdf_job import run_pdf_correction_job, run_pdf_job

FIXTURE = Path(__file__).parent / "fixtures" / "representative.pdf"


class FakeHtmlProvider:
    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{html} [DE]", source_lang or "", target_lang, "fake")

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def test_correction_job_overwrites_existing_output_with_edited_text(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"

    original_result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
    )
    assert original_result.stats.translated == 1
    assert len(original_result.stats.blocks) == 1
    original_mtime = destination.stat().st_mtime_ns

    record = original_result.stats.blocks[0]
    corrected_records = build_corrected_records(
        original_result.stats.blocks,
        {(record.page_index, record.block_index): "Handkorrigierter Text"},
    )

    corrected_result = run_pdf_correction_job(source, destination, corrected_records)

    assert corrected_result.output_path == destination
    assert destination.exists()
    assert destination.stat().st_mtime_ns >= original_mtime  # actually rewritten
    assert corrected_result.stats.translated == 1

    doc = fitz.open(str(destination))
    text = " ".join(doc[0].get_text().split())
    assert "Handkorrigierter Text" in text
    doc.close()

    report = corrected_result.qa_report_path.read_text(encoding="utf-8")
    assert "manuelle Korrektur" in report
    assert "Blöcke neu eingefügt: 1" in report


def test_correction_job_refuses_source_as_destination(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())

    with pytest.raises(DestinationConflictError):
        run_pdf_correction_job(source, source, [])


def test_correction_job_does_not_require_provider_or_network(tmp_path: Path) -> None:
    """Sanity check on the "no provider" contract mentioned in this
    module's docstring - run_pdf_correction_job() has no provider
    parameter to even pass one to.
    """
    params = inspect.signature(run_pdf_correction_job).parameters
    assert "provider" not in params
    assert "provider_name" not in params
