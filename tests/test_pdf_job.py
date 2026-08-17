"""Mirrors tests/test_pptx_job.py's/tests/test_word_job.py's coverage for
the PDF job (ui/pdf_job.py), added when the shared UI job flow (progress/
cancel/QA report/Start button) was extended from PPTX+DOCX to also cover
the direct PDF path (see RoadMap.md Phase 2/PDF - gated on the redact/
insert duplicate-text bug, fixed and regression-tested separately in
tests/test_pdf_redact_insert_collision.py).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.pdf.translate_pdf import PdfTranslationStats
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.document_job_common import DestinationConflictError
from ui.pdf_job import run_pdf_job

FIXTURE = Path(__file__).parent / "fixtures" / "representative.pdf"
"""One translatable paragraph plus one link-annotated paragraph (translatable=
False - PyMuPdfEngine.extract_blocks() excludes link text) - see the
fixture's generation. Both blocks carry spans (see TextBlock.spans), so
FakeHtmlProvider.translate_html() is the path exercised below; .translate()
exists too only for interface completeness (see translate_pdf()'s
block.spans-empty fallback, not reachable via this fixture)."""


class FakeHtmlProvider:
    def __init__(self) -> None:
        self.calls = 0

    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        self.calls += 1
        return TranslationResult(f"{html} [DE]", source_lang or "", target_lang, "fake")

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        self.calls += 1
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def test_run_pdf_job_writes_output_and_qa_report(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    provider = FakeHtmlProvider()
    progress_messages: list[str] = []

    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000,
        progress_callback=progress_messages.append,
        provider=provider,
    )

    assert result.output_path == destination
    assert destination.exists()
    assert result.qa_report_path.exists()
    assert result.stats.translated == 1
    assert result.stats.skipped == 1  # the link-annotated block
    assert result.stats.failed == 0
    assert not result.stats.cancelled
    assert progress_messages
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "Blöcke übersetzt: 1" in report
    assert "Blöcke übersprungen" in report
    assert "Keine fehlgeschlagenen Blöcke." in report


def test_run_pdf_job_refuses_existing_destination_without_any_api_call(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    destination.write_bytes(b"occupied")
    provider = FakeHtmlProvider()

    with pytest.raises(DestinationConflictError):
        run_pdf_job(
            source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=provider,
        )
    assert provider.calls == 0


def test_run_pdf_job_refuses_source_as_destination(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    provider = FakeHtmlProvider()

    with pytest.raises(DestinationConflictError):
        run_pdf_job(
            source, source, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=provider,
        )
    assert provider.calls == 0


def test_cancellation_stops_between_api_calls_and_keeps_partial_result(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    provider = FakeHtmlProvider()

    def cancel_immediately() -> bool:
        return True

    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        should_cancel=cancel_immediately,
    )

    assert result.stats.cancelled
    assert result.stats.translated == 0
    assert destination.exists()  # still saved - a partial (here: untouched) result
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "abgebrochen" in report


def test_stats_callback_receives_incremental_progress(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    provider = FakeHtmlProvider()
    snapshots: list[int] = []

    run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        stats_callback=lambda stats: snapshots.append(stats.processed),
    )

    # 1 translatable + 1 skipped (link) block = 2, each reporting once.
    assert snapshots == [1, 2]


def test_total_callback_reports_block_count_before_first_api_call(tmp_path: Path) -> None:
    """Same regression guard as test_pptx_job.py's/test_word_job.py's
    equivalent test: the progress bar must be driven by a total known
    BEFORE translation starts, not by the current processed count (which
    would always show 100%).
    """
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    provider = FakeHtmlProvider()
    totals: list[int] = []
    calls_when_reported: list[int] = []

    def on_total(total: int) -> None:
        totals.append(total)
        calls_when_reported.append(provider.calls)

    run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        total_callback=on_total,
    )

    assert totals == [2]
    assert calls_when_reported == [0]


def test_budget_guard_stops_run_when_run_limit_too_small(tmp_path: Path) -> None:
    source = tmp_path / "Doc.pdf"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.pdf"
    provider = FakeHtmlProvider()

    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=1, provider=provider,
    )

    assert result.stats.failed == 1
    assert result.stats.translated == 0
    assert all("BudgetExceededError" in error for error in result.stats.errors)
