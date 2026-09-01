"""Orchestrates one DOCX merge/insert job end-to-end (01.09.2026, Michael:
"Jetzt noch das ganze für *.docx.") - the DOCX counterpart of
ui/merge_job.py, see that module's docstring for why this is its own small
module rather than folded into TranslationRequest/ui/analysis.py (the
reasoning is identical: merging spends no API budget, needs no provider,
and doesn't fit RoadMap.md's "jeder kostenpflichtige Lauf braucht
Analyse..." principle).

Two differences from ui/merge_job.py, both following directly from
pipeline/word/merge.py's own design (see that module's docstring):
1. validate_merge_word_sources() has no page-range check at all - DOCX
   merge is whole-file only (confirmed with Michael, 01.09.2026), so there
   is no MergeSourceSpec-style per-source field to validate here.
2. run_word_merge_job() passes a `batch_size` through to
   merge_docx_files() for the "über ca. 2000 Dateien" case - defaulted to
   pipeline.word.merge.DEFAULT_BATCH_SIZE rather than exposed as a UI
   control, since Michael confirmed batching should happen automatically
   ("Ja, automatisch batchen (empfohlen)"), not be a setting to tune per
   run.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from pipeline.word.merge import DEFAULT_BATCH_SIZE, WordMergeStats, merge_docx_files
from ui.document_job_common import DestinationConflictError


@dataclass
class WordMergeJobResult:
    output_path: Path
    stats: WordMergeStats


def validate_merge_word_sources(sources: Sequence[Path], destination: Path | None) -> list[str]:
    """Pre-flight checks the UI runs on every source-list/destination
    change to decide whether the Start button may be enabled - mirrors
    ui/merge_job.py's validate_merge_sources(), minus the page-range
    concept that DOCX has no counterpart for (see module docstring).
    """
    errors: list[str] = []
    if not sources:
        errors.append("Mindestens eine Quelldatei hinzufügen.")
    for source in sources:
        path = Path(source)
        if not path.is_file():
            errors.append(f"Datei nicht gefunden: {path}")
        elif path.suffix.lower() != ".docx":
            errors.append(f"{path.name} ist keine DOCX-Datei.")
    if destination is None or not str(destination).strip():
        errors.append("Zieldatei fehlt.")
    elif Path(destination).suffix.lower() != ".docx":
        errors.append("Zieldatei muss auf \".docx\" enden.")
    return errors


def run_word_merge_job(
    sources: Sequence[Path],
    destination: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> WordMergeJobResult:
    """Run one full DOCX merge/insert job and return its result. Same
    destination-safety check as ui/merge_job.py's run_merge_job() (see that
    function's docstring for why an already-existing, non-source
    destination is deliberately allowed to be overwritten here).
    """
    destination = Path(destination)
    resolved_destination = destination.resolve()
    for source in sources:
        if Path(source).resolve() == resolved_destination:
            raise DestinationConflictError(
                f"Zieldatei darf technisch nicht mit einer Quelldatei identisch sein: {Path(source).name}"
            )

    stats = merge_docx_files(
        [Path(p) for p in sources],
        destination,
        batch_size=batch_size,
        progress_callback=progress_callback,
        should_cancel=should_cancel,
    )
    return WordMergeJobResult(destination, stats)
