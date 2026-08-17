from __future__ import annotations

from pathlib import Path

import pytest
from lxml import html as lxml_html

from pipeline.presentation.translate_presentation import PresentationTranslationStats
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.pptx_job import DestinationConflictError, run_presentation_job, safe_destination

FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


class FakeHtmlProvider:
    def __init__(self) -> None:
        self.calls = 0

    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        self.calls += 1
        root = lxml_html.fromstring(f"<div>{html}</div>")
        for span in root.iter("span"):
            span.text = (span.text or "") + " [DE]"
        translated = "".join(lxml_html.tostring(child, encoding="unicode") for child in root)
        return TranslationResult(translated, source_lang or "", target_lang, "fake")


def test_safe_destination_avoids_collision_and_never_equals_source(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())

    first = safe_destination(source, "de", tmp_path)
    assert first.name == "Deck_DE.pptx"
    assert first != source

    first.write_bytes(b"already there")
    second = safe_destination(source, "de", tmp_path)
    assert second.name == "Deck_DE (2).pptx"


def test_run_presentation_job_writes_output_and_qa_report(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Deck_DE.pptx"
    provider = FakeHtmlProvider()
    progress_messages: list[str] = []

    result = run_presentation_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", ["PPTX-Roundtrip"],
        max_chars_per_run=200_000,
        progress_callback=progress_messages.append,
        provider=provider,
    )

    assert result.output_path == destination
    assert destination.exists()
    assert result.qa_report_path.exists()
    assert result.stats.paragraphs_translated == 6
    assert result.stats.paragraphs_failed == 0
    assert not result.stats.cancelled
    assert progress_messages  # per-paragraph location strings were reported
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "Absätze übersetzt: 6" in report
    # The fake provider appends " [DE]" to every run, so the fixture's tight
    # title placeholder legitimately trips the static overflow estimate -
    # exactly the kind of risk the QA report exists to surface for manual
    # review, not to silently reformat.
    assert result.overflow_regressions
    assert "new_fit_risk" in report
    assert "manuellen Sichtprüfung" in report


def test_run_presentation_job_refuses_existing_destination_without_any_api_call(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Deck_DE.pptx"
    destination.write_bytes(b"occupied")
    provider = FakeHtmlProvider()

    with pytest.raises(DestinationConflictError):
        run_presentation_job(
            source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=provider,
        )
    assert provider.calls == 0


def test_run_presentation_job_refuses_source_as_destination(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    provider = FakeHtmlProvider()

    with pytest.raises(DestinationConflictError):
        run_presentation_job(
            source, source, "deepl", DEEPL_PRICING, "de", "en", [],
            max_chars_per_run=200_000, provider=provider,
        )
    assert provider.calls == 0


def test_cancellation_stops_between_api_calls_and_keeps_partial_result(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Deck_DE.pptx"
    provider = FakeHtmlProvider()

    def cancel_after_first_call() -> bool:
        return provider.calls >= 1

    result = run_presentation_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        should_cancel=cancel_after_first_call,
    )

    assert result.stats.cancelled
    assert result.stats.paragraphs_translated == 1
    assert destination.exists()
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "abgebrochen" in report


def test_stats_callback_receives_incremental_progress(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Deck_DE.pptx"
    provider = FakeHtmlProvider()
    snapshots: list[PresentationTranslationStats] = []

    run_presentation_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        stats_callback=lambda stats: snapshots.append(
            PresentationTranslationStats(
                stats.paragraphs_translated, stats.paragraphs_skipped,
                stats.paragraphs_failed, stats.chars_sent, stats.cancelled, list(stats.errors),
            )
        ),
    )

    assert len(snapshots) == 6
    assert [s.paragraphs_translated for s in snapshots] == [1, 2, 3, 4, 5, 6]


def test_total_callback_reports_paragraph_count_before_first_api_call(tmp_path: Path) -> None:
    """Regression guard for a progress-bar bug: the UI used to compute the
    progress bar's max from the CURRENT processed count on every stats
    update, so it always showed 100% regardless of real progress. The fix is
    total_callback, invoked once with the true total before any API call, so
    the bar can be determinate from the start.
    """
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Deck_DE.pptx"
    provider = FakeHtmlProvider()
    totals: list[int] = []
    calls_when_reported: list[int] = []

    def on_total(total: int) -> None:
        totals.append(total)
        calls_when_reported.append(provider.calls)

    run_presentation_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=provider,
        total_callback=on_total,
    )

    assert totals == [6]  # reported once, matching the fixture's 6 paragraphs
    assert calls_when_reported == [0]  # ...and before any translate_html() call was made


def test_budget_guard_stops_run_when_run_limit_too_small(tmp_path: Path) -> None:
    source = tmp_path / "Deck.pptx"
    source.write_bytes(FIXTURE.read_bytes())
    destination = tmp_path / "Deck_DE.pptx"
    provider = FakeHtmlProvider()

    result = run_presentation_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=1, provider=provider,
    )

    assert result.stats.paragraphs_failed == 6
    assert result.stats.paragraphs_translated == 0
    assert all("BudgetExceededError" in error for error in result.stats.errors)
