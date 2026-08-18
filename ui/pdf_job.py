"""Orchestrates one PDF translation job end-to-end.

Mirrors ui/word_job.py's structure and responsibilities (see that module's
docstring for the overall shape: independent of Qt, provider construction
plus cost-guard wrapping plus progress/cancellation support plus a QA
report next to the output file; cost confirmation itself stays a caller
responsibility in ui/app.py) - built on pipeline.pdf.translate_pdf()
instead of pipeline.word.translate_document.translate_document(). Kept as
its own module rather than merged into a generic "document job" - see
ui/document_job_common.py's docstring for the general rationale, and
PdfTranslationStats.overflow_blocks below for PDF's own risk profile that
has no equivalent in either other format: PPTX has fixed-size text boxes
that can visibly overflow their slide, DOCX reflows automatically with no
such risk, and PDF sits in between - insert_text() always makes text FIT
somewhere (via growth/shrink/force-fit, see pipeline/pdf/pymupdf_engine.py),
but "fit" isn't the same as "fits cleanly at the original size", which is
exactly what overflow_blocks flags for a QA follow-up look.

No "ICO document" first-page-skip option yet (unlike ui/word_job.py's
ico_mode) - the underlying detection already exists in
pipeline/pdf/pymupdf_engine.py (FIRST_PAGE_ANCHOR_TERMS/
_split_first_page_metadata(), DocumentTemplate.first_page_zones) but isn't
wired to a UI toggle yet; see RoadMap.md Phase 2/PDF.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from pipeline.pdf.template import DocumentTemplate, detect_header_footer_zones
from pipeline.pdf.translate_pdf import (
    PdfTranslationStats,
    TranslatedBlockRecord,
    apply_pdf_corrections,
    total_block_count,
    translate_pdf,
)
from pipeline.translation.base import TranslationProvider
from pipeline.translation.cost_control import PricingModel, TranslationBudgetGuard
from ui.document_job_common import DestinationConflictError, build_provider


@dataclass
class PdfJobResult:
    output_path: Path
    qa_report_path: Path
    stats: PdfTranslationStats


def run_pdf_job(
    source: Path,
    destination: Path,
    provider_name: str,
    pricing: PricingModel,
    target_lang: str,
    source_lang: str | None,
    protected_terms: list[str],
    max_chars_per_run: int,
    progress_callback: Callable[[str], None] | None = None,
    stats_callback: Callable[[PdfTranslationStats], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    provider: TranslationProvider | None = None,
    total_callback: Callable[[int], None] | None = None,
    exclude_header: bool = False,
    exclude_footer: bool = False,
) -> PdfJobResult:
    """Run one full PDF translation job and return its result.

    ``provider`` can be injected (e.g. a fake provider in tests); otherwise
    one is built from ``provider_name`` via PROVIDER_FACTORIES (see
    ui/document_job_common.py), which reads credentials lazily on first use.

    ``total_callback``, if given, is invoked exactly once - right before the
    first API call - with the total number of blocks (translatable and not,
    across every page) the run will process, mirroring ui/pptx_job.py's/
    ui/word_job.py's equivalent so all three jobs drive the same
    determinate progress display in ui/app.py.

    No hand-authored, document-specific DocumentTemplate file (see
    templates/virelicon.json) is loaded here - the generic UI flow has no
    way to select one. Instead, if ``exclude_header``/``exclude_footer``
    is set (see the matching checkboxes in ui/app.py), header_bbox/
    footer_bbox are found automatically via
    pipeline.pdf.template.detect_header_footer_zones() - reproduced by a
    real user's live run: the direct PDF path used to translate a
    document's repeating header right along with the body, because
    NEITHER a template file NOR any detection was ever applied here (see
    RoadMap.md Phase 2/PDF). Detection needs its own throwaway,
    template-free engine opened on the same source first (extract_blocks()
    is read-only, so this doesn't disturb anything the real run below
    does) - the real PyMuPdfEngine is then constructed WITH the resulting
    template, since PyMuPdfEngine takes its template at construction time
    and extract_blocks() caches per page once called, so swapping the
    template on an already-used engine instance would be unsafe. See this
    module's docstring for why there's still no ico_mode-equivalent
    first-page option.
    """
    source = Path(source)
    destination = Path(destination)
    if destination.resolve() == source.resolve():
        raise DestinationConflictError(
            "Zieldatei darf technisch nicht mit der Quelldatei identisch sein."
        )
    if destination.exists():
        raise DestinationConflictError(f"Zieldatei existiert bereits: {destination}")

    template: DocumentTemplate | None = None
    detected_header: tuple[float, float, float, float] | None = None
    detected_footer: tuple[float, float, float, float] | None = None
    if exclude_header or exclude_footer:
        detection_engine = PyMuPdfEngine()
        detection_engine.open(str(source))
        detected_header, detected_footer = detect_header_footer_zones(detection_engine)
        template = DocumentTemplate(
            name=source.stem,
            header_bbox=detected_header if exclude_header else None,
            footer_bbox=detected_footer if exclude_footer else None,
        )

    engine = PyMuPdfEngine(template=template)
    engine.open(str(source))

    if total_callback is not None:
        total_callback(total_block_count(engine))

    active_provider = provider if provider is not None else build_provider(provider_name)
    guard = TranslationBudgetGuard(active_provider, pricing, max_chars_per_run=max_chars_per_run)

    stats = translate_pdf(
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
            exclude_header=exclude_header, exclude_footer=exclude_footer,
            detected_header=detected_header, detected_footer=detected_footer,
        ),
        encoding="utf-8",
    )
    return PdfJobResult(destination, qa_report_path, stats)


def _build_qa_report(
    source: Path,
    destination: Path,
    provider_name: str,
    target_lang: str,
    source_lang: str | None,
    stats: PdfTranslationStats,
    exclude_header: bool = False,
    exclude_footer: bool = False,
    detected_header: tuple[float, float, float, float] | None = None,
    detected_footer: tuple[float, float, float, float] | None = None,
) -> str:
    lines: list[str] = [
        "PDF-Übersetzung - QA-Bericht",
        f"Erstellt: {datetime.now().isoformat(timespec='seconds')}",
        f"Quelle: {source}",
        f"Ziel: {destination}",
        f"Anbieter: {provider_name}",
        f"Sprache: {source_lang or 'automatisch erkannt'} -> {target_lang}",
        "",
        "Ergebnis",
        f"  Blöcke übersetzt: {stats.translated}",
        f"  Blöcke übersprungen (nicht übersetzbar, z. B. Header/Footer/Links): {stats.skipped}",
        f"  Blöcke fehlgeschlagen: {stats.failed}",
        f"  Gesendete Zeichen: {stats.chars_sent}",
    ]
    if exclude_header:
        lines.append(
            f"  Header ausschließen: aktiviert, "
            + ("automatisch erkannt und ausgeschlossen." if detected_header
               else "keine wiederkehrende Kopfzeile erkannt - nichts ausgeschlossen.")
        )
    if exclude_footer:
        lines.append(
            f"  Footer ausschließen: aktiviert, "
            + ("automatisch erkannt und ausgeschlossen." if detected_footer
               else "keine wiederkehrende Fußzeile erkannt - nichts ausgeschlossen.")
        )
    if stats.overflow_blocks:
        lines.append(
            f"  Blöcke mit Wachstum/Schrumpfung beim Einfügen: {stats.overflow_blocks} "
            "(Text musste vergrößert, verkleinert oder anders skaliert werden, um in "
            "die ursprüngliche Fläche zu passen - kein Fehler für sich genommen, siehe "
            "pipeline/pdf/pymupdf_engine.py, aber diese Stellen lohnen eine kurze "
            "visuelle Prüfung)."
        )
    else:
        lines.append("  Kein Block musste beim Einfügen wachsen oder schrumpfen.")
    if stats.cancelled:
        lines.append(
            "  Lauf wurde vom Benutzer abgebrochen - dies ist ein Teilergebnis, "
            "bereits übersetzte Blöcke wurden gespeichert."
        )
    lines.append("")
    if stats.errors:
        lines.append("Fehlgeschlagene Blöcke (technische Meldung, ohne Zugangsdaten):")
        lines.extend(f"  - {error}" for error in stats.errors)
    else:
        lines.append("Keine fehlgeschlagenen Blöcke.")
    lines.append("")
    lines.append(
        "Bekannte, noch nicht automatisiert geprüfte Einschränkungen (siehe RoadMap.md "
        "Phase 2/PDF): Erhalt von Link-Annotationen nach Redaction, Durchsuchbarkeit und "
        "Copy/Paste-Qualität des Ergebnisses, fehlende Glyphen aus Symbol-/Private-Use-"
        "Fonts, ungewollte fi-Ligatur, Erhalt/Wiederverwendung von Originalfonts, sowie "
        "zwei aus einer früheren Diagnose bekannte, hier nicht geprüfte Symptome "
        "(unerklärte Suffixe an Zuschreibungszeilen; verlorene Formatierung und wachsende "
        "Lücken bei Überschrift+Bullet-Blöcken - siehe "
        "tests/manual_diagnose_text_duplication.py). Bitte das Ergebnis stichprobenartig "
        "prüfen."
    )
    return "\n".join(lines) + "\n"


def run_pdf_correction_job(
    source: Path,
    destination: Path,
    records: list[TranslatedBlockRecord],
    exclude_header: bool = False,
    exclude_footer: bool = False,
) -> PdfJobResult:
    """Re-render a PDF translation from a corrected list of
    TranslatedBlockRecord (see pipeline.pdf.translate_pdf's
    apply_pdf_corrections()/build_corrected_records()) - the "Anwenden"
    step of the correction table opened from PdfJobResult.stats.blocks
    (RoadMap.md Phase 2/PDF's "PDF-Übersetzung korrigieren" item, added
    after a real user found a genuine mistranslation - a proper name
    rendered as an unrelated German word - in a live run).

    Unlike run_pdf_job(), `destination` is allowed - expected - to
    already exist: the user explicitly chose "overwrite the existing
    translation" over "always write a new file" for this workflow (see
    ui/app.py's correction-dialog wiring), so there is deliberately no
    DestinationConflictError-on-exists check here, only the
    identical-to-source guard every job function has.

    `source` must be the SAME pristine source PDF the original
    translate_pdf() run used - never `destination` itself, and never an
    already-translated file - see apply_pdf_corrections()'s docstring
    for why: reusing an already-translated document as the "source" for
    a second redact/insert pass can leave stray remnants of the first
    translation behind for any block that grew past its original box.

    `exclude_header`/`exclude_footer` must match whatever the ORIGINAL
    run used (the caller is expected to have those from the same
    TranslationRequest/PdfTranslationWorker call that produced `records`
    in the first place) - reconstructs the identical DocumentTemplate so
    engine.extract_blocks() returns the same block list/order the
    records' page_index/block_index indices were captured against.

    No provider, no cost/budget guard, no progress callback: unlike
    run_pdf_job(), this makes no translation-provider/network calls at
    all (every record already carries its final translated_html) - see
    ui/app.py for why that lets the correction dialog call this directly
    on the UI thread instead of via a background QThreadPool worker.
    """
    source = Path(source)
    destination = Path(destination)
    if destination.resolve() == source.resolve():
        raise DestinationConflictError(
            "Zieldatei darf technisch nicht mit der Quelldatei identisch sein."
        )

    template: DocumentTemplate | None = None
    if exclude_header or exclude_footer:
        detection_engine = PyMuPdfEngine()
        detection_engine.open(str(source))
        detected_header, detected_footer = detect_header_footer_zones(detection_engine)
        template = DocumentTemplate(
            name=source.stem,
            header_bbox=detected_header if exclude_header else None,
            footer_bbox=detected_footer if exclude_footer else None,
        )

    engine = PyMuPdfEngine(template=template)
    engine.open(str(source))
    stats = apply_pdf_corrections(engine, records)

    destination.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(destination))

    qa_report_path = destination.with_name(f"{destination.stem}_qa_report.txt")
    qa_report_path.write_text(
        _build_correction_qa_report(source, destination, stats), encoding="utf-8"
    )
    return PdfJobResult(destination, qa_report_path, stats)


def _build_correction_qa_report(source: Path, destination: Path, stats: PdfTranslationStats) -> str:
    lines = [
        "PDF-Übersetzung - QA-Bericht (nach manueller Korrektur)",
        f"Erstellt: {datetime.now().isoformat(timespec='seconds')}",
        f"Quelle: {source}",
        f"Ziel: {destination}",
        "",
        "Ergebnis",
        f"  Blöcke neu eingefügt: {stats.translated}",
    ]
    if stats.overflow_blocks:
        lines.append(
            f"  Blöcke mit Wachstum/Schrumpfung beim Einfügen: {stats.overflow_blocks} "
            "(kein Fehler für sich genommen, aber diese Stellen lohnen eine kurze "
            "visuelle Prüfung)."
        )
    else:
        lines.append("  Kein Block musste beim Einfügen wachsen oder schrumpfen.")
    lines.append("")
    lines.append(
        "Diese Datei wurde durch eine manuelle Korrektur-Runde ersetzt (siehe "
        "RoadMap.md Phase 2/PDF, 'PDF-Übersetzung korrigieren'). Der ursprüngliche "
        "QA-Bericht des ersten Übersetzungslaufs wurde durch diesen ersetzt."
    )
    return "\n".join(lines) + "\n"
