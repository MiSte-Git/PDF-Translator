"""Orchestrates one PPTX translation job end-to-end.

Deliberately independent of Qt so it can be unit-tested directly and reused
by any worker/thread implementation: builds the provider, runs the
translation with progress/cancellation support, saves to a safe destination,
compares text-overflow risk against the untouched source, and writes a QA
report next to the output file. Cost confirmation itself stays a caller
responsibility (see ui/app.py): it must happen once, immediately before this
function is invoked, using the already-computed analysis result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from pipeline.presentation.base import OverflowRegression
from pipeline.presentation.pptx_engine import PptxEngine
from pipeline.presentation.translate_presentation import (
    PresentationTranslationStats,
    total_paragraph_count,
    translate_presentation,
)
from pipeline.translation.base import TranslationProvider
from pipeline.translation.cost_control import PricingModel, TranslationBudgetGuard
from ui.document_job_common import (
    PROVIDER_FACTORIES,
    DestinationConflictError,
    build_provider,
    safe_destination,
)

# PROVIDER_FACTORIES/DestinationConflictError/build_provider/safe_destination
# used to be defined here; they moved to ui/document_job_common.py once
# ui/word_job.py needed the exact same format-agnostic logic (see that
# module's docstring). Re-imported (not just re-exported via __all__) so
# every existing "from ui.pptx_job import ..." caller - ui/app.py,
# ui/workers.py, tests/test_pptx_job.py - keeps working unchanged.


@dataclass
class PresentationJobResult:
    output_path: Path
    qa_report_path: Path
    stats: PresentationTranslationStats
    overflow_regressions: list[OverflowRegression] = field(default_factory=list)


def run_presentation_job(
    source: Path,
    destination: Path,
    provider_name: str,
    pricing: PricingModel,
    target_lang: str,
    source_lang: str | None,
    protected_terms: list[str],
    max_chars_per_run: int,
    progress_callback: Callable[[str], None] | None = None,
    stats_callback: Callable[[PresentationTranslationStats], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    provider: TranslationProvider | None = None,
    total_callback: Callable[[int], None] | None = None,
) -> PresentationJobResult:
    """Run one full PPTX translation job and return its result.

    ``provider`` can be injected (e.g. a fake provider in tests); otherwise
    one is built from ``provider_name`` via PROVIDER_FACTORIES, which reads
    credentials lazily on first use.

    ``total_callback``, if given, is invoked exactly once - right before the
    first API call - with the total number of paragraphs the run will
    process. This lets a caller switch a progress display from indeterminate
    to determinate ("X of N paragraphs") instead of only showing the current
    location, which previously left no visible sign that a long run was
    actually progressing rather than stuck.
    """
    source = Path(source)
    destination = Path(destination)
    if destination.resolve() == source.resolve():
        raise DestinationConflictError(
            "Zieldatei darf technisch nicht mit der Quelldatei identisch sein."
        )
    if destination.exists():
        raise DestinationConflictError(f"Zieldatei existiert bereits: {destination}")

    # A second, untouched engine on the same source is the overflow baseline;
    # the working engine is the one actually mutated by translate_presentation.
    baseline = PptxEngine()
    baseline.open(source)
    engine = PptxEngine()
    engine.open(source)

    if total_callback is not None:
        total_callback(total_paragraph_count(engine))

    active_provider = provider if provider is not None else build_provider(provider_name)
    guard = TranslationBudgetGuard(active_provider, pricing, max_chars_per_run=max_chars_per_run)

    stats = translate_presentation(
        engine,
        guard,
        protected_terms,
        target_lang,
        source_lang,
        progress_callback=progress_callback,
        stats_callback=stats_callback,
        should_cancel=should_cancel,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    engine.save(destination)

    overflow_regressions = engine.compare_overflow(baseline)
    qa_report_path = destination.with_name(f"{destination.stem}_qa_report.txt")
    qa_report_path.write_text(
        _build_qa_report(
            source, destination, provider_name, target_lang, source_lang,
            stats, overflow_regressions, engine.capability_catalog(),
        ),
        encoding="utf-8",
    )
    return PresentationJobResult(destination, qa_report_path, stats, overflow_regressions)


def _build_qa_report(
    source: Path,
    destination: Path,
    provider_name: str,
    target_lang: str,
    source_lang: str | None,
    stats: PresentationTranslationStats,
    regressions: list[OverflowRegression],
    capability_catalog: dict[str, str],
) -> str:
    lines: list[str] = [
        "PPTX-Übersetzung - QA-Bericht",
        f"Erstellt: {datetime.now().isoformat(timespec='seconds')}",
        f"Quelle: {source}",
        f"Ziel: {destination}",
        f"Anbieter: {provider_name}",
        f"Sprache: {source_lang or 'automatisch erkannt'} -> {target_lang}",
        "",
        "Ergebnis",
        f"  Absätze übersetzt: {stats.paragraphs_translated}",
        f"  Absätze übersprungen (nicht übersetzbar): {stats.paragraphs_skipped}",
        f"  Absätze fehlgeschlagen: {stats.paragraphs_failed}",
        f"  Gesendete Zeichen: {stats.chars_sent}",
    ]
    if stats.cancelled:
        lines.append(
            "  Lauf wurde vom Benutzer abgebrochen - dies ist ein Teilergebnis, "
            "bereits übersetzte Absätze wurden gespeichert."
        )
    lines.append("")
    if stats.errors:
        lines.append("Fehlgeschlagene Absätze (technische Meldung, ohne Zugangsdaten):")
        lines.extend(f"  - {error}" for error in stats.errors)
    else:
        lines.append("Keine fehlgeschlagenen Absätze.")
    lines.append("")
    lines.append(
        "Überlaufrisiken gegenüber dem Original (nur zur manuellen Sichtprüfung "
        "in PowerPoint/Impress, nicht automatisch umformatiert):"
    )
    if regressions:
        for regression in regressions:
            lines.append(
                f"  - {regression.slide_path} · {regression.shape_name} "
                f"(id {regression.shape_id}): {regression.reason}, "
                f"geschätzt {regression.after_estimated_lines}/"
                f"{regression.available_lines} Zeilen"
            )
    else:
        lines.append("  Keine neuen oder verschärften Überlaufrisiken gefunden.")
    lines.append("")
    not_supported = {
        key: status for key, status in capability_catalog.items() if status.startswith("not supported")
    }
    if not_supported:
        lines.append("Nicht unterstützte Inhalte (bewusst unverändert belassen):")
        lines.extend(f"  - {key}: {status}" for key, status in not_supported.items())
    return "\n".join(lines) + "\n"
