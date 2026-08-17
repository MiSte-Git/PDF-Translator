"""Orchestrates one DOCX translation job end-to-end.

Mirrors ui/pptx_job.py's structure and responsibilities (see that module's
docstring for the overall shape: independent of Qt, provider construction
plus cost-guard wrapping plus progress/cancellation support plus a QA
report next to the output file; cost confirmation itself stays a caller
responsibility in ui/app.py). Kept as its own module rather than merged
with ui/pptx_job.py into one generic "document job" - see
ui/document_job_common.py's docstring for why.

Difference from the PPTX job worth calling out: there is no PPTX-style
overflow-risk comparison here. Word reflows text automatically (unlike a
PPTX text box with a fixed size), so the closest analogous risk - the
PAGE-field/page-count not updating on a document that grows - is a still-
open RoadMap item (see RoadMap.md Phase 2/Word), not something this job can
verify yet. What IS already implemented and worth surfacing is
TranslationStats.new_break_anomalies (pipeline/word/html_bridge.py's
<br/>-count mismatch detector) - the QA report below reports it explicitly
instead of silently dropping it, consistent with this project's "catalogue,
don't hide" principle for known-imperfect areas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from pipeline.translation.base import TranslationProvider
from pipeline.translation.cost_control import PricingModel, TranslationBudgetGuard
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.translate_document import TranslationStats, total_paragraph_count, translate_document
from ui.document_job_common import DestinationConflictError, build_provider


@dataclass
class WordJobResult:
    output_path: Path
    qa_report_path: Path
    stats: TranslationStats


def run_word_job(
    source: Path,
    destination: Path,
    provider_name: str,
    pricing: PricingModel,
    target_lang: str,
    source_lang: str | None,
    protected_terms: list[str],
    max_chars_per_run: int,
    progress_callback: Callable[[str], None] | None = None,
    stats_callback: Callable[[TranslationStats], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    provider: TranslationProvider | None = None,
    total_callback: Callable[[int], None] | None = None,
    ico_mode: bool = False,
) -> WordJobResult:
    """Run one full DOCX translation job and return its result.

    ``provider`` can be injected (e.g. a fake provider in tests); otherwise
    one is built from ``provider_name`` via PROVIDER_FACTORIES (see
    ui/document_job_common.py), which reads credentials lazily on first use.

    ``total_callback``, if given, is invoked exactly once - right before the
    first API call - with the total number of paragraphs (body + header +
    footer) the run will process, mirroring ui/pptx_job.py's
    run_presentation_job() so both jobs drive the same determinate progress
    display in ui/app.py.

    ``ico_mode`` is passed straight through to DocxEngine.open() (see its
    docstring): only when True does the page-1 metadata block in front of
    the separator shape get excluded from translation - the user opts in
    explicitly via the "ICO-Dokument" checkbox in ui/app.py, it is never
    inferred automatically. Left False by default so existing callers
    (tests, ico_translate/batch.py) keep their prior full-document
    behaviour unless they ask for the special case.
    """
    source = Path(source)
    destination = Path(destination)
    if destination.resolve() == source.resolve():
        raise DestinationConflictError(
            "Zieldatei darf technisch nicht mit der Quelldatei identisch sein."
        )
    if destination.exists():
        raise DestinationConflictError(f"Zieldatei existiert bereits: {destination}")

    engine = DocxEngine()
    engine.open(str(source), ico_mode=ico_mode)

    if total_callback is not None:
        total_callback(total_paragraph_count(engine))

    active_provider = provider if provider is not None else build_provider(provider_name)
    guard = TranslationBudgetGuard(active_provider, pricing, max_chars_per_run=max_chars_per_run)

    stats = translate_document(
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
    engine.save(str(destination))

    qa_report_path = destination.with_name(f"{destination.stem}_qa_report.txt")
    qa_report_path.write_text(
        _build_qa_report(
            source, destination, provider_name, target_lang, source_lang, stats,
            ico_mode, engine.separator_found,
        ),
        encoding="utf-8",
    )
    return WordJobResult(destination, qa_report_path, stats)


def _build_qa_report(
    source: Path,
    destination: Path,
    provider_name: str,
    target_lang: str,
    source_lang: str | None,
    stats: TranslationStats,
    ico_mode: bool = False,
    separator_found: bool = False,
) -> str:
    lines: list[str] = [
        "DOCX-Übersetzung - QA-Bericht",
        f"Erstellt: {datetime.now().isoformat(timespec='seconds')}",
        f"Quelle: {source}",
        f"Ziel: {destination}",
        f"Anbieter: {provider_name}",
        f"Sprache: {source_lang or 'automatisch erkannt'} -> {target_lang}",
        "",
    ]
    if ico_mode and separator_found:
        lines.append(
            "ICO-Modus: aktiv. Der Seite-1-Metadatenbereich vor der Trennlinie wurde "
            "NICHT übersetzt (in \"Absätze übersprungen\" unten enthalten)."
        )
    elif ico_mode and not separator_found:
        lines.append(
            "ICO-Modus: aktiv, aber auf Seite 1 wurde KEINE Trennlinie/-form gefunden - "
            "das gesamte Dokument wurde regulär übersetzt, kein Bereich wurde "
            "ausgeschlossen. Bitte prüfen, ob dieses Dokument wirklich vom internen "
            "Typ ICO ist bzw. die erwartete Struktur hat."
        )
    else:
        lines.append("ICO-Modus: nicht aktiv - das gesamte Dokument wurde regulär übersetzt.")
    lines += [
        "",
        "Ergebnis",
        f"  Hauptteil - Absätze übersetzt: {stats.body_translated}",
        f"  Hauptteil - Absätze übersprungen (nicht übersetzbar/leer): {stats.body_skipped}",
        f"  Hauptteil - Absätze fehlgeschlagen: {stats.body_failed}",
        f"  Kopfzeile - Absätze übersprungen (bleibt immer unübersetzt): {stats.header_skipped}",
        f"  Fußzeile - Absätze übersprungen (bleibt immer unübersetzt): {stats.footer_skipped}",
        f"  Gesendete Zeichen: {stats.chars_sent}",
    ]
    if stats.header_failed or stats.footer_failed:
        # Not expected in normal operation (header/footer are always
        # translatable=False - see DocxEngine.get_header_footer_paragraphs()
        # and translate_document()'s docstring), surfaced regardless rather
        # than silently ignored if it ever does happen.
        lines.append(
            f"  Kopf-/Fußzeile - unerwartet fehlgeschlagen: "
            f"{stats.header_failed + stats.footer_failed} (siehe Fehlerliste unten)"
        )
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
    if stats.new_break_anomalies:
        lines.append(
            f"Achtung: {stats.new_break_anomalies} Absatz/Absätze mit abweichender "
            "Zeilenumbruch-Anzahl nach der Übersetzung (DeepL/Anbieter kann an "
            "<br/>-Grenzen Text verschieben oder Fragmente verschmelzen - siehe "
            "RoadMap.md Phase 2/Word). Details: "
            "pipeline/word/.word_break_anomalies.jsonl bzw. "
            "tests/output/word_break_anomalies.jsonl. Rein kosmetisch (z. B. "
            "einzelne fehlende Leerzeichen an Satzgrenzen), keine Struktur- oder "
            "Markerbeschädigung."
        )
    else:
        lines.append("Keine Zeilenumbruch-Anomalien festgestellt.")
    lines.append("")
    lines.append(
        "Bekannte, noch nicht automatisiert geprüfte Einschränkung (siehe "
        "RoadMap.md Phase 2/Word): ob ein PAGE-Feld in der Fußzeile sich bei "
        "einem länger gewordenen Dokument korrekt aktualisiert, wurde noch "
        "nicht an einem tatsächlich länger werdenden Dokument verifiziert - "
        "bitte Seitenzahlen nach der Übersetzung manuell stichprobenartig "
        "prüfen."
    )
    return "\n".join(lines) + "\n"
