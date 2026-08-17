"""Mirrors tests/test_pptx_job.py's coverage for the DOCX job
(ui/word_job.py), added when the shared UI job flow (progress/cancel/QA
report/Start button) was extended from PPTX-only to also cover DOCX (see
RoadMap.md Phase 2/Word).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from pipeline.word.translate_document import TranslationStats
from ui.document_job_common import DestinationConflictError
from ui.word_job import run_word_job

FIXTURE = Path(__file__).parent / "fixtures" / "representative.docx"
ICO_FIXTURE = Path(__file__).parent / "fixtures" / "representative_ico.docx"
"""Same shape as FIXTURE, plus a page-1 metadata paragraph ("ICO Metadata:
Issuer XYZ") followed by a paragraph containing the straightConnector1
separator shape DocxEngine._has_separator_shape() looks for - see
tests/fixtures/representative_ico.docx's generation. Lets the ico_mode
tests below actually exercise the "found" branch, unlike FIXTURE (which
has no separator shape at all, so DocxEngine.open()'s scan always comes up
empty regardless of ico_mode)."""


class FakeHtmlProvider:
    """Simpler than test_pptx_job.py's FakeHtmlProvider: the fixture's body
    paragraphs are plain text (no bold/hyperlink/image runs), so there are
    no <img>/<a data-run=...> tags whose count html_to_paragraph() would
    need to see preserved - appending a suffix to the whole HTML string is
    enough to round-trip cleanly.
    """

    def __init__(self) -> None:
        self.calls = 0

    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        self.calls += 1
        return TranslationResult(f"{html} [DE]", source_lang or "", target_lang, "fake")


def test_run_word_job_writes_output_and_qa_report(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()
    progress_messages: list[str] = []

    result = run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000,
        progress_callback=progress_messages.append,
        provider=provider,
    )

    assert result.output_path == destination
    assert destination.exists()
    assert result.qa_report_path.exists()
    # Fixture: 3 body paragraphs (2 with text, 1 blank) + 1 header + 1 footer
    # paragraph (see tests/fixtures/representative.docx / its generation).
    assert result.stats.body_translated == 2
    assert result.stats.body_skipped == 1  # the blank paragraph
    assert result.stats.header_skipped == 1  # header/footer are always
    assert result.stats.footer_skipped == 1  # translatable=False
    assert result.stats.body_failed == 0
    assert not result.stats.cancelled
    assert progress_messages  # per-paragraph location strings were reported
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "Hauptteil - Absätze übersetzt: 2" in report
    assert "Kopfzeile - Absätze übersprungen" in report
    assert "Keine fehlgeschlagenen Absätze." in report
    assert "PAGE-Feld" in report  # known-limitation note, see ui/word_job.py


def test_run_word_job_refuses_existing_destination_without_any_api_call(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    destination.write_bytes(b"occupied")
    provider = FakeHtmlProvider()

    with pytest.raises(DestinationConflictError):
        run_word_job(
            source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=provider,
        )
    assert provider.calls == 0


def test_run_word_job_refuses_source_as_destination(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    provider = FakeHtmlProvider()

    with pytest.raises(DestinationConflictError):
        run_word_job(
            source, source, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=provider,
        )
    assert provider.calls == 0


def test_cancellation_stops_between_api_calls_and_keeps_partial_result(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()

    def cancel_after_first_call() -> bool:
        return provider.calls >= 1

    result = run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        should_cancel=cancel_after_first_call,
    )

    assert result.stats.cancelled
    assert result.stats.body_translated == 1
    assert destination.exists()
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "abgebrochen" in report


def test_stats_callback_receives_incremental_progress(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()
    snapshots: list[int] = []

    run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        stats_callback=lambda stats: snapshots.append(stats.processed),
    )

    # 3 body + 1 header + 1 footer = 5 paragraphs, each reporting once.
    assert snapshots == [1, 2, 3, 4, 5]


def test_total_callback_reports_paragraph_count_before_first_api_call(tmp_path: Path) -> None:
    """Same regression guard as test_pptx_job.py's equivalent test: the
    progress bar must be driven by a total known BEFORE translation starts,
    not by the current processed count (which would always show 100%).
    """
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()
    totals: list[int] = []
    calls_when_reported: list[int] = []

    def on_total(total: int) -> None:
        totals.append(total)
        calls_when_reported.append(provider.calls)

    run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        total_callback=on_total,
    )

    assert totals == [5]
    assert calls_when_reported == [0]


def _destination_body_xml(destination: Path) -> str:
    import zipfile

    with zipfile.ZipFile(destination) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def test_ico_mode_true_skips_page1_metadata_block_when_separator_found(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(ICO_FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()

    result = run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        ico_mode=True,
    )

    assert result.stats.body_failed == 0
    # The decisive check: the page-1 metadata paragraph must survive
    # UNCHANGED (FakeHtmlProvider appends " [DE]" to anything it actually
    # translates) - everything else in the body is free to go through
    # translate_document() normally (e.g. the separator paragraph itself
    # carries a <w:drawing>, so it isn't skipped as "empty" the way a
    # pure-text metadata block would be - that's unrelated to ico_mode).
    body_xml = _destination_body_xml(destination)
    assert "ICO Metadata: Issuer XYZ" in body_xml
    assert "ICO Metadata: Issuer XYZ [DE]" not in body_xml
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "ICO-Modus: aktiv. Der Seite-1-Metadatenbereich" in report


def test_ico_mode_false_translates_page1_metadata_block_regardless_of_separator(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(ICO_FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()

    result = run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        # ico_mode defaults to False - the separator shape is present in
        # ICO_FIXTURE, but must NOT be acted on unless explicitly requested.
    )

    assert result.stats.body_failed == 0
    body_xml = _destination_body_xml(destination)
    assert "ICO Metadata: Issuer XYZ [DE]" in body_xml
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "ICO-Modus: nicht aktiv" in report


def test_ico_mode_true_warns_when_no_separator_found(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())  # no separator shape at all
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()

    result = run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        ico_mode=True,
    )

    assert result.stats.body_translated == 2  # unchanged: full document translated
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "ICO-Modus: aktiv, aber auf Seite 1 wurde KEINE Trennlinie" in report


def test_budget_guard_stops_run_when_run_limit_too_small(tmp_path: Path) -> None:
    source = tmp_path / "Doc.docx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Doc_DE.docx"
    provider = FakeHtmlProvider()

    result = run_word_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=1, provider=provider,
    )

    assert result.stats.body_failed == 2
    assert result.stats.body_translated == 0
    assert all("BudgetExceededError" in error for error in result.stats.errors)
