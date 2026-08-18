"""Orchestrates one eigenständige Bildübersetzung end-to-end (RoadMap.md
Phase 3 - Bildübersetzung und OCR).

Mirrors ui/pdf_job.py's structure and responsibilities (see that module's
docstring for the overall shape: independent of Qt, provider construction
plus cost-guard wrapping plus progress/cancellation support plus a QA
report next to the output file) - built on
pipeline.images.translate_image.translate_image() instead of
pipeline.pdf.translate_pdf.translate_pdf().

run_image_job() itself handles only ONE source image per call (unlike
TranslationRequest.source_paths, which allows several for
TranslationMode.IMAGES - the only mode whose validation_errors() permits
more than one selected source file at once). run_image_batch_job() below
is what ui/app.py's Start button actually calls for IMAGES mode: it loops
over every selected file, calling run_image_job() once per file, exactly
mirroring how a multi-page PDF is one run_pdf_job() call but a multi-FILE
image batch is several independent run_image_job() calls, each with its
own QA report next to its own output file (an image has no natural "one
combined report" unit the way a single document's pages do).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from pipeline.images.inpainting import TextReplacement
from pipeline.images.translate_image import (
    DEFAULT_MIN_OCR_CONFIDENCE,
    ImageTranslationStats,
    translate_image,
)
from pipeline.translation.base import TranslationProvider
from pipeline.translation.cost_control import PricingModel, TranslationBudgetGuard
from ui.document_job_common import (
    DestinationConflictError,
    build_inpainting_backend,
    build_ocr_engine,
    build_provider,
    safe_destination,
)


@dataclass
class ImageJobResult:
    source_path: Path
    """The pristine source image this result was translated from - kept
    around (unlike e.g. PdfJobResult, whose caller already tracks a
    single source separately) because IMAGES mode can translate SEVERAL
    files in one batch (see ImageBatchJobResult.results below); without
    this field, ui/app.py's correction-dialog wiring would have no way
    to recover which source file a given batch entry's output came from
    when the user picks one file out of several to correct (see
    run_image_correction_job()'s docstring for why the correct pristine
    source matters there)."""
    output_path: Path
    qa_report_path: Path
    stats: ImageTranslationStats


def run_image_job(
    source: Path,
    destination: Path,
    provider_name: str,
    pricing: PricingModel,
    target_lang: str,
    source_lang: str | None,
    protected_terms: list[str],
    max_chars_per_run: int,
    ocr_engine_name: str = "tesseract",
    inpainting_backend_name: str = "box_overlay",
    ocr_language: str | None = None,
    min_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
    progress_callback: Callable[[str], None] | None = None,
    stats_callback: Callable[[ImageTranslationStats], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    provider: TranslationProvider | None = None,
) -> ImageJobResult:
    """Run one full eigenständige Bildübersetzung job and return its result.

    ``provider`` can be injected (e.g. a fake provider in tests); otherwise
    one is built from ``provider_name`` via build_provider() (see
    ui/document_job_common.py), exactly like run_pdf_job()/run_word_job().

    ``ocr_engine_name``/``inpainting_backend_name`` select which
    pipeline.images.ocr.OcrEngine/pipeline.images.inpainting.InpaintingBackend
    implementation to use - see ui/document_job_common.py's
    OCR_ENGINE_FACTORIES/INPAINTING_BACKEND_FACTORIES for the available
    keys. The caller (ui/app.py) is responsible for only offering an OCR
    engine the user's machine can actually run - see
    ui/document_job_common.py::ocr_engine_available() - build_ocr_engine()
    itself does not re-check availability, mirroring how build_provider()
    doesn't re-check credentials either (both fail naturally, with a clear
    error, the first time they're actually used if skipped).

    ``min_confidence`` is forwarded to translate_image() as-is - see
    pipeline.images.translate_image.DEFAULT_MIN_OCR_CONFIDENCE's docstring.
    Not yet exposed as a UI setting (see RoadMap.md/Backlog.md 18.08.2026);
    a caller (or a test) that needs a different threshold passes it here
    directly.
    """
    source = Path(source)
    destination = Path(destination)
    if destination.resolve() == source.resolve():
        raise DestinationConflictError(
            "Zieldatei darf technisch nicht mit der Quelldatei identisch sein."
        )
    if destination.exists():
        raise DestinationConflictError(f"Zieldatei existiert bereits: {destination}")

    ocr_engine = build_ocr_engine(ocr_engine_name)
    inpainting_backend = build_inpainting_backend(inpainting_backend_name)
    active_provider = provider if provider is not None else build_provider(provider_name)
    guard = TranslationBudgetGuard(active_provider, pricing, max_chars_per_run=max_chars_per_run)

    destination.parent.mkdir(parents=True, exist_ok=True)
    stats = translate_image(
        str(source),
        str(destination),
        ocr_engine,
        inpainting_backend,
        guard,
        protected_terms,
        target_lang,
        source_lang,
        ocr_language=ocr_language,
        min_confidence=min_confidence,
        progress_callback=progress_callback,
        stats_callback=stats_callback,
        should_cancel=should_cancel,
    )

    qa_report_path = destination.with_name(f"{destination.stem}_qa_report.txt")
    qa_report_path.write_text(
        _build_qa_report(
            source, destination, provider_name, target_lang, source_lang, stats,
            ocr_engine_name=ocr_engine_name, inpainting_backend_name=inpainting_backend_name,
        ),
        encoding="utf-8",
    )
    return ImageJobResult(source, destination, qa_report_path, stats)


def run_image_correction_job(
    source: Path,
    destination: Path,
    replacements: list[TextReplacement],
    inpainting_backend_name: str = "box_overlay",
) -> ImageJobResult:
    """Re-render a Bildübersetzung from a corrected list of TextReplacement
    (see pipeline.images.translate_image.build_corrected_replacements()) -
    the image counterpart of ui/pdf_job.py::run_pdf_correction_job(), the
    "Anwenden" step of the correction table opened from
    ImageJobResult.stats.replacements (RoadMap.md Phase 3's "Korrektur-
    Möglichkeit ... analog zur PDF-Variante" item).

    Unlike run_image_job(), `destination` is allowed - expected - to
    already exist: the user explicitly chose "overwrite the existing
    translation" over "always write a new file" for this workflow,
    mirroring run_pdf_correction_job()'s identical decision. Only the
    identical-to-source guard every job function has still applies.

    `source` must be the SAME pristine source image the original
    translate_image() run used - never `destination` itself, and never
    an already-translated file: every InpaintingBackend.apply() call
    re-renders from scratch against whatever `image_path` it's given, so
    reusing an already-translated image as `source` here would layer a
    second rewrite on top of the first instead of replacing it cleanly.

    No OCR pass, no translation provider, no cost/budget guard, no
    progress callback: unlike run_image_job(), this makes no OCR/network
    calls at all (every replacement already carries its final
    translated_text) - see ui/app.py for why that lets the correction
    dialog call this directly on the UI thread instead of via a
    background QThreadPool worker.
    """
    source = Path(source)
    destination = Path(destination)
    if destination.resolve() == source.resolve():
        raise DestinationConflictError(
            "Zieldatei darf technisch nicht mit der Quelldatei identisch sein."
        )

    inpainting_backend = build_inpainting_backend(inpainting_backend_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    inpainting_backend.apply(str(source), replacements, str(destination))

    stats = ImageTranslationStats(
        translated=len(replacements),
        regions=[replacement.region for replacement in replacements],
        replacements=replacements,
    )

    qa_report_path = destination.with_name(f"{destination.stem}_qa_report.txt")
    qa_report_path.write_text(
        _build_correction_qa_report(source, destination, stats), encoding="utf-8"
    )
    return ImageJobResult(source, destination, qa_report_path, stats)


def _build_correction_qa_report(source: Path, destination: Path, stats: ImageTranslationStats) -> str:
    lines = [
        "Bildübersetzung - QA-Bericht (nach manueller Korrektur)",
        f"Erstellt: {datetime.now().isoformat(timespec='seconds')}",
        f"Quelle: {source}",
        f"Ziel: {destination}",
        "",
        "Ergebnis",
        f"  Regionen neu eingefügt: {stats.translated}",
        "",
        "Diese Datei wurde durch eine manuelle Korrektur-Runde ersetzt (siehe RoadMap.md "
        "Phase 3, 'Korrektur-Möglichkeit ... analog zur PDF-Variante'). Der ursprüngliche "
        "QA-Bericht des ersten Übersetzungslaufs wurde durch diesen ersetzt.",
    ]
    return "\n".join(lines) + "\n"


_INPAINTING_BACKEND_LABELS = {
    "box_overlay": "Box-Overlay (Fläche überdecken, Text einfügen)",
    "cv_inpainting": "Klassisches CPU-Inpainting (OpenCV, Hintergrund rekonstruiert)",
}


def _build_qa_report(
    source: Path,
    destination: Path,
    provider_name: str,
    target_lang: str,
    source_lang: str | None,
    stats: ImageTranslationStats,
    ocr_engine_name: str = "tesseract",
    inpainting_backend_name: str = "box_overlay",
) -> str:
    backend_label = _INPAINTING_BACKEND_LABELS.get(inpainting_backend_name, inpainting_backend_name)
    lines: list[str] = [
        "Bildübersetzung - QA-Bericht",
        f"Erstellt: {datetime.now().isoformat(timespec='seconds')}",
        f"Quelle: {source}",
        f"Ziel: {destination}",
        f"Anbieter: {provider_name}",
        f"Sprache: {source_lang or 'automatisch erkannt'} -> {target_lang}",
        f"OCR-Engine: {ocr_engine_name}",
        f"Rückschreibe-Backend: {backend_label}",
        "",
        "Ergebnis",
        f"  Erkannte Textregionen: {len(stats.regions)}",
        f"  Regionen übersetzt: {stats.translated}",
        f"  Regionen übersprungen (niedrige OCR-Konfidenz): {stats.skipped}",
        f"  Regionen fehlgeschlagen: {stats.failed}",
        f"  Gesendete Zeichen: {stats.chars_sent}",
    ]
    if not stats.regions:
        lines.append(
            "  Es wurde kein Text im Bild erkannt - Ergebnisdatei entspricht dem Original."
        )
    if stats.cancelled:
        lines.append(
            "  Lauf wurde vom Benutzer abgebrochen - bereits übersetzte Regionen wurden "
            "trotzdem in die Ergebnisdatei geschrieben, spätere Regionen blieben im "
            "Original."
        )
    lines.append("")
    if stats.errors:
        lines.append("Fehlgeschlagene Regionen (technische Meldung, ohne Zugangsdaten):")
        lines.extend(f"  - {error}" for error in stats.errors)
    else:
        lines.append("Keine fehlgeschlagenen Regionen.")
    lines.append("")
    lines.append(
        "Bekannte, noch nicht automatisiert geprüfte Einschränkungen (siehe RoadMap.md "
        "Phase 3): keine Erkennung/Ausnahme für Logos oder rein dekorative Bildbereiche, "
        "keine Deduplizierung mehrfach identischer Bilder, Konfidenz-Filter fängt nur "
        "die eindeutigsten OCR-Fehllesungen ab (siehe 'Regionen übersprungen' oben - "
        "einzelne fragwürdige Regionen können trotzdem durchrutschen). Bitte das "
        "Ergebnis stichprobenartig prüfen; eine falsch übersetzte oder übersprungene "
        "Region lässt sich über den Korrektur-Dialog (Button unter dem Ergebnis) "
        "nachträglich anpassen."
    )
    return "\n".join(lines) + "\n"


@dataclass
class ImageBatchStats:
    """Aggregate across an ImageBatchJobResult's per-file results -
    shaped to duck-type with PresentationTranslationStats/
    WordTranslationStats/PdfTranslationStats' .processed/.translated/
    .skipped/.failed/.chars_sent/.cancelled contract (see
    ui/app.py::_job_stats()/_update_job_status(), which reads these
    fields identically regardless of format). `skipped` sums every file's
    ImageTranslationStats.skipped (regions never translated because their
    OCR confidence was below min_confidence - see that field's docstring
    and DEFAULT_MIN_OCR_CONFIDENCE, added 18.08.2026) - structurally the
    same "excluded, not an error" meaning PdfTranslationStats.skipped has
    for a PDF link/header block, so the existing UI progress code (see
    ui/app.py::_job_stats()/_update_job_status()) needs no per-mode
    branching for this field.

    `processed`/`files_total` operate at FILE granularity (one unit per
    completed file), not region granularity - see run_image_batch_job()'s
    docstring for why the progress bar tracks files while the detail line
    (via progress_callback) still shows per-region detail within the
    current file.
    """

    translated: int = 0
    skipped: int = 0
    failed: int = 0
    chars_sent: int = 0
    cancelled: bool = False
    files_processed: int = 0
    files_total: int = 0
    results: list[ImageJobResult] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return self.files_processed


@dataclass
class ImageBatchJobResult:
    """Result of translating MULTIPLE image files in one Start-button run
    - see run_image_batch_job()'s docstring. `output_dir` (not a single
    `output_path`) and no single `qa_report_path`: ui/app.py handles this
    type with its own isinstance() branches in _show_job_result()/
    _open_output_folder()/_open_qa_report() rather than forcing it into
    the one-output-one-report shape PresentationJobResult/WordJobResult/
    PdfJobResult/ImageJobResult all share.
    """

    output_dir: Path
    stats: ImageBatchStats


def run_image_batch_job(
    sources: list[Path],
    output_dir: Path,
    provider_name: str,
    pricing: PricingModel,
    target_lang: str,
    source_lang: str | None,
    protected_terms: list[str],
    max_chars_per_run: int,
    ocr_engine_name: str = "tesseract",
    inpainting_backend_name: str = "box_overlay",
    ocr_language: str | None = None,
    min_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
    progress_callback: Callable[[str], None] | None = None,
    stats_callback: Callable[[ImageBatchStats], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    total_callback: Callable[[int], None] | None = None,
    provider: TranslationProvider | None = None,
) -> ImageBatchJobResult:
    """Translate every file in `sources` in turn via run_image_job(), one
    output image + one QA report per file written into `output_dir` (see
    ui.document_job_common.safe_destination() for how each file's own
    destination name is chosen - avoids collisions with both the other
    files in this batch and anything already in `output_dir`, since each
    call checks the real filesystem state, including files this same
    loop already wrote).

    TranslationMode.IMAGES is the only mode whose TranslationRequest
    allows more than one selected source file at once (see
    TranslationRequest.validation_errors()) - this is what ui/app.py's
    Start button calls for that mode, mirroring how run_pdf_job() is
    called for a single multi-page PDF. Works identically for a
    single-file selection too (a one-element `sources` list) - ui/app.py
    does not special-case "just one image".

    Known, documented limitation: each file gets its OWN
    max_chars_per_run budget via its own TranslationBudgetGuard (built
    fresh inside each run_image_job() call), NOT one budget shared across
    the whole batch - unlike a single multi-page PDF, where one guard's
    budget is shared across every page. Sharing one guard across files
    would need run_image_job() to accept an already-guarded provider
    without re-wrapping it, which its current signature doesn't support -
    left as a known simplification for this first cut (RoadMap.md
    Phase 3); each individual image's text volume is small relative to
    max_chars_per_run in practice, so this is unlikely to matter in
    practice, but is not the same guarantee a single-document job makes.

    `should_cancel` is polled BEFORE each file (between files, never
    mid-file) - once True, `stats.cancelled` is set and no further files
    are started; every file already completed keeps its output/QA report.
    A cancellation THIS function catches mid-batch is distinct from one
    the same `should_cancel` callback may ALSO cause inside a single
    file's own translate_image() call (see that function's docstring) -
    both can be true at once for the file that was running when
    cancellation was requested; that file's own result.stats.cancelled
    reflects the latter, `stats.cancelled` here reflects the former.
    """
    sources = [Path(source) for source in sources]
    output_dir = Path(output_dir)
    if total_callback is not None:
        total_callback(len(sources))

    stats = ImageBatchStats(files_total=len(sources))

    def _report() -> None:
        if stats_callback is not None:
            stats_callback(stats)

    for index, source in enumerate(sources):
        if should_cancel is not None and should_cancel():
            stats.cancelled = True
            break
        if progress_callback is not None:
            progress_callback(f"Bild {index + 1}/{len(sources)}: {source.name}")
        destination = safe_destination(source, target_lang, output_dir)
        result = run_image_job(
            source, destination, provider_name, pricing, target_lang, source_lang,
            protected_terms, max_chars_per_run,
            ocr_engine_name=ocr_engine_name, inpainting_backend_name=inpainting_backend_name,
            ocr_language=ocr_language, min_confidence=min_confidence,
            progress_callback=progress_callback,
            should_cancel=should_cancel,
            provider=provider,
        )
        stats.results.append(result)
        stats.translated += result.stats.translated
        stats.skipped += result.stats.skipped
        stats.failed += result.stats.failed
        stats.chars_sent += result.stats.chars_sent
        stats.files_processed += 1
        _report()

    return ImageBatchJobResult(output_dir, stats)
