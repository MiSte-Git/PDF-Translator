"""Batch orchestration: translate every "approved" document listed in the
ico_translate manifest (see manifest.py) using
pipeline/word/translate_document.py's shared translate_document(), one
output .docx per source file.

Deliberately out of scope here (see anforderungen_word_pfad.md's open
question 8 on the output naming convention): merging several ICOs' output
documents into one combined document. This module only ever produces one
output file per approved source file - a later, separate step can pick
those files up and merge them; nothing here should make that harder, but
building it is not this module's job.
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pipeline.translation.base import TranslationProvider
from pipeline.translation.cost_control import TranslationBudgetGuard, get_month_usage
from pipeline.translation.protected_terms import derive_protected_term
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import paragraph_to_html
from pipeline.word.translate_document import TranslationStats, translate_document

from ico_translate.manifest import load_manifest

# tests/output/ico_batch_errors.jsonl - one JSON object per failed document,
# same append-only JSONL convention as word_break_anomalies.jsonl/
# growth_anomalies.jsonl: a persistent, best-effort log a human can review
# after a run, never something a failure to write should itself escalate.
BATCH_ERROR_LOG_PATH = (
    Path(__file__).resolve().parent.parent / "tests" / "output" / "ico_batch_errors.jsonl"
)


@dataclass
class BatchDocument:
    """One (document number, approved filename) unit of work - NOT one per
    document number: an independent multi-file number (e.g. 1440
    TRUTHSEEK+WOUNDS) contributes one BatchDocument per approved file, so
    it naturally produces one output document per file, not one per
    number.
    """
    number: str
    filename: str


@dataclass
class BatchResult:
    documents_planned: int = 0
    estimated_chars: int = 0
    estimated_cost: float = 0.0
    aborted: bool = False
    """True if the upfront budget-guard confirmation was declined - in
    that case nothing was translated and every other counter stays 0."""
    documents_translated: int = 0
    documents_failed: int = 0
    paragraphs_translated: int = 0
    paragraphs_skipped: int = 0
    paragraphs_failed: int = 0
    total_chars_sent: int = 0
    """Characters actually sent to the provider across the whole run (the
    real, logged figure - as opposed to estimated_chars, the upfront
    pre-scan approximation)."""
    actual_cost: float = 0.0
    """Cost of total_chars_sent under the guard's pricing, on top of this
    run's starting month-usage baseline - the batch-scale analogue of
    tests/manual_translate_full_document.py's single-document
    estimated_cost, i.e. what THIS run actually cost, not the upfront
    guess."""
    elapsed_seconds: float = 0.0
    output_paths: list[Path] = field(default_factory=list)
    errors: list[tuple[str, str, str]] = field(default_factory=list)
    """(number, filename, "ExceptionType: message") for every document
    that failed to open/translate/save - see BATCH_ERROR_LOG_PATH for the
    full traceback."""


def select_documents(
    manifest_path: Path,
    only_numbers: set[str] | None = None,
    limit: int | None = None,
) -> list[BatchDocument]:
    """Every approved file from the manifest, in ascending document-number
    order, one BatchDocument per file (see BatchDocument). `only_numbers`
    restricts to those document numbers (for a small test run instead of
    the whole ~2200-document manifest); `limit` then caps the total
    resulting document COUNT (not number of manifest entries) - so
    limit=3 against a number with 2 approved files plus a following
    single-file number yields exactly 3 BatchDocuments, e.g. both files
    of 1440 plus the next number's one file.
    """
    manifest = load_manifest(manifest_path)
    documents: list[BatchDocument] = []
    for number, entry in sorted(manifest.items(), key=lambda kv: int(kv[0])):
        if entry.status != "approved":
            continue
        if only_numbers is not None and number not in only_numbers:
            continue
        for file_entry in entry.files:
            documents.append(BatchDocument(number=number, filename=file_entry.filename))

    if limit is not None:
        documents = documents[:limit]
    return documents


def collect_translatable_texts(source_folder: Path, documents: list[BatchDocument]) -> list[str]:
    """Every translatable paragraph's HTML (body + header/footer, same
    accounting translate_document() itself uses for chars_sent) across all
    of `documents` - opened read-only, nothing translated - for
    TranslationBudgetGuard.estimate_run()/confirm_run() to size up the
    WHOLE run's character count before any real translate_html() call.

    A document that can't even be opened contributes nothing here rather
    than raising: it will fail again - and get logged - in run_batch()'s
    real loop, so a single bad file must not block the cost estimate for
    everything else, matching run_batch()'s own per-document resilience.
    """
    texts: list[str] = []
    for document in documents:
        try:
            engine = DocxEngine()
            engine.open(str(source_folder / document.filename))
        except Exception:
            continue
        for paragraph in engine.get_paragraphs() + engine.get_header_footer_paragraphs():
            if not paragraph.translatable:
                continue
            html = paragraph_to_html(paragraph).html
            if html.strip():
                texts.append(html)
    return texts


def _output_filename(number: str, ico_name: str, target_lang: str) -> str:
    """"<Nummer> <ICO-Name>_<Zielsprache-Code>.docx" (anforderungen_word_pfad.md
    requirement 8's naming convention), e.g. "2210 INERTIARA_DE.docx".
    `ico_name` comes straight from derive_protected_term() on the SOURCE
    filename (see run_batch()) - for the small minority of approved
    filenames that carry a revision suffix (e.g. "1854 MNEMOSYNE (LS).docx",
    "1746 NOOVIAN Updated Declas.docx"), that suffix rides along into both
    the protected term and this output filename unchanged. Known,
    accepted for now - see run_batch()'s docstring.
    """
    return f"{number} {ico_name}_{target_lang.upper()}.docx"


def _log_batch_error(number: str, filename: str, exc: Exception) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "number": number,
        "filename": filename,
        "error": f"{type(exc).__name__}: {exc}",
        "traceback": traceback.format_exc(),
    }
    try:
        BATCH_ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BATCH_ERROR_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def run_batch(
    manifest_path: Path,
    source_folder: Path,
    output_dir: Path,
    provider: TranslationProvider,
    target_lang: str,
    budget_guard: TranslationBudgetGuard,
    limit: int | None = None,
    only_numbers: set[str] | None = None,
    source_lang: str | None = "en",
) -> BatchResult:
    """Translate every selected approved manifest document (see
    select_documents()) and write one output .docx per source file into
    `output_dir`, named per _output_filename().

    `provider` and `budget_guard` are both required because they serve
    different purposes: `provider` identifies which service/model is in
    use (e.g. for provider.model_name in a caller's report) but is never
    called directly here; every actual translate_html() call goes through
    `budget_guard` (which must already wrap `provider`) so the SAME
    guard instance enforces its character cap and logs real usage across
    the WHOLE batch, not just one document - exactly like
    tests/manual_translate_full_document.py already does for a single
    document, just with one guard shared over many documents instead of
    one.

    Cost estimation happens ONCE, up front, for the whole planned run
    (collect_translatable_texts() + budget_guard.confirm_run()) - not
    per document - before a single real translate_html() call is made. If
    the confirmation is declined, returns immediately with
    BatchResult.aborted=True and nothing translated.

    A single document failing to open/translate/save (any Exception) is
    caught, logged to BATCH_ERROR_LOG_PATH with a full traceback, and
    counted in BatchResult.errors/documents_failed - the run continues
    with the next document rather than aborting, mirroring
    translate_document()'s own per-PARAGRAPH resilience one level up, at
    the whole-document level.

    `protected_terms` per document is derived via
    derive_protected_term() on the SOURCE filename (not
    pipeline/word/source_selection.py's document_ico_name(), which
    additionally strips a "(LS)" suffix) - as directed for this task. For
    the small minority of approved filenames that carry a revision suffix
    (MNEMOSYNE's "(LS)", or "Updated Declas"/"updated"/"Follow Up" on a
    few explicitly-picked files), this means the derived term won't
    exactly match the plain ICO name as it actually appears in the
    document body, so protect_terms() won't find/protect it there. A
    known, accepted limitation of following this instruction literally -
    flagged here rather than silently "fixed" by swapping in a different
    name-derivation function.
    """
    result = BatchResult()

    documents = select_documents(manifest_path, only_numbers=only_numbers, limit=limit)
    result.documents_planned = len(documents)
    if not documents:
        return result

    texts = collect_translatable_texts(source_folder, documents)
    result.estimated_chars, result.estimated_cost = budget_guard.estimate_run(texts)

    if not budget_guard.confirm_run(texts):
        result.aborted = True
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    month_usage_before = get_month_usage(budget_guard.provider_name)

    start_time = time.monotonic()

    for document in documents:
        source_path = source_folder / document.filename
        ico_name = derive_protected_term(document.filename)
        output_path = output_dir / _output_filename(document.number, ico_name, target_lang)

        try:
            engine = DocxEngine()
            engine.open(str(source_path))
            stats: TranslationStats = translate_document(
                engine, budget_guard, [ico_name], target_lang=target_lang, source_lang=source_lang
            )
            engine.save(str(output_path), overwrite=True)
        except Exception as exc:  # noqa: BLE001 - one bad document must not abort the whole batch
            result.documents_failed += 1
            result.errors.append((document.number, document.filename, f"{type(exc).__name__}: {exc}"))
            _log_batch_error(document.number, document.filename, exc)
            continue

        result.documents_translated += 1
        result.total_chars_sent += stats.chars_sent
        result.paragraphs_translated += stats.translated
        result.paragraphs_skipped += stats.skipped
        result.paragraphs_failed += stats.failed
        result.output_paths.append(output_path)

    result.elapsed_seconds = time.monotonic() - start_time
    result.actual_cost = budget_guard.estimate_cost(result.total_chars_sent, month_usage_before)
    return result
