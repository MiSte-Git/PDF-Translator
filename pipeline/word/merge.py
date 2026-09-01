"""DOCX merge/insert (01.09.2026) - mirrors pipeline/pdf/pymupdf_engine.py's
merge_pdfs(), on Michael's follow-up: "Jetzt noch das ganze für *.docx.
Kann man überhaupt mittlerweile ca. 2000 docx zusammenführen?"

This is the only file in the project allowed to import `docx`
(python-docx) or `docxcompose` - the same import-exclusivity rule
pymupdf_engine.py already applies to PyMuPDF and pipeline/drive_auth.py
applies to the Google API libraries, for the identical reason: nothing
outside this file needs to know these two libraries exist. python-docx
itself has no native "append another document's body" operation (it was
only ever in requirements.txt for python-docx-based fixture generation
elsewhere in the test suite); docxcompose (4teamwork, actively maintained,
built on python-docx) fills that gap - it deep-copies each appended
document's content, remapping numbering (`numId`/`abstractNumId`) and
matching styles by name to avoid the ID collisions/renumbering breakage a
naive python-docx-only concatenation would produce.

Whole-file merge only (confirmed with Michael, 01.09.2026) - unlike
merge_pdfs()'s per-source page-range selection, DOCX has no fixed "pages"
in the file itself (pagination is a rendering-time concept, dependent on
viewer/printer/fonts installed), so a MergeSourceSpec-style page-range
concept doesn't have a DOCX equivalent; MergeSourceSpec's PDF-only
`pages` field simply has no counterpart here.

Two behaviors deliberately differ from merge_pdfs(), both explained where
they happen below:
1. A page break is inserted between every two merged documents (DOCX has
   no page concept as noted above, so nothing does this automatically the
   way PDF's own page boundaries do).
2. A single source that fails to APPEND (as opposed to fails to OPEN) is
   skipped with a warning rather than aborting the whole run - see
   _merge_sequential()'s docstring for why this is not simply
   "merge_pdfs() copied for DOCX", but a deliberate deviation.

Batching for large merges (Michael, 01.09.2026: "automatisch batchen"
confirmed) - see merge_docx_files()'s docstring for the two-level
chunk-then-merge-chunks architecture and why it exists: no library here
is built for streaming/incremental merging (everything happens in
memory), and there are no published reports of anyone merging on the
order of 1000-2000 separate .docx files with this stack - see
Backlog.md 01.09.2026 for the researched background.
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

DEFAULT_BATCH_SIZE = 100
"""Chunk size for merge_docx_files()'s two-level batching - picked as a
round, conservative number comfortably below any scale that's been
publicly reported working with docxcompose (see Backlog.md 01.09.2026's
research summary: essentially untested territory above a few dozen files
in any public report found), not derived from a specific measured limit
on this machine. Exposed as a parameter, not hardcoded, so it can be
tuned later against real documents/real hardware without a code change.
"""


@dataclass
class WordMergeStats:
    segments: int
    """Sources successfully appended (across every batch) - can be LESS
    than len(sources) if some were skipped after a per-file append failure
    (see _merge_sequential()'s docstring) or the run was cancelled."""
    files_processed: int
    """Distinct source files actually opened, counted by resolved path -
    mirrors PdfMergeStats.files_processed's identical dedup convention
    (the same file listed twice, e.g. a repeated cover page, counts once
    here)."""
    batches: int
    """Number of first-level chunk files produced during batching - 0 if
    the whole merge fit in a single pass (len(sources) <= batch_size), in
    which case no intermediate files were ever written to disk at all."""
    cancelled: bool = False
    warnings: list[str] = field(default_factory=list)
    """Per-file notes that do NOT represent the whole run failing - an
    append-compatibility skip (see _merge_sequential()), or an open
    failure discovered only once inside a later batch iteration (see the
    two-level path below for why that can't simply abort the same way the
    single-pass path's open failures do)."""


def _open_docx(path: Path):
    """Open `path` as a python-docx Document, wrapping any failure (missing,
    not a valid .docx/corrupt zip, encrypted) into a clear, file-named
    ValueError - mirrors merge_pdfs()'s identical treatment of a source
    that can't even be opened. Local import: see module docstring for why
    `docx` is only ever imported inside this one file.
    """
    from docx import Document

    try:
        return Document(str(path))
    except Exception as exc:  # noqa: BLE001 - re-raised as a clear, file-named ValueError below
        raise ValueError(f'"{path.name}" konnte nicht geöffnet werden: {exc}') from exc


def _merge_sequential(
    sources: Sequence[Path],
    total_for_progress: int,
    done_before: int,
    progress_callback: Callable[[str], None] | None,
    should_cancel: Callable[[], bool] | None,
):
    """Merge `sources` (a flat list, batching handled by the caller) into
    one in-memory python-docx Document via docxcompose. Returns
    (document_or_None, appended_count, cancelled, warnings) - `document`
    is None only if `sources` was empty or cancelled before the first
    file was even opened.

    Two DIFFERENT kinds of per-source failure are handled deliberately
    differently, unlike merge_pdfs() (which hard-fails on any source
    problem):
    - Opening a source fails (missing/corrupt/not-a-docx): this is almost
      always a real problem with the merge's INPUT LIST itself, exactly
      like merge_pdfs()'s treatment - raises ValueError, aborting the
      whole run. The caller should not have listed a file it can't read.
    - Appending an OPENED, valid .docx fails inside docxcompose (a known,
      documented category of docxcompose limitation - SmartArt, certain
      text boxes, malformed complex-field structures; see Backlog.md
      01.09.2026's research summary): this is a property of that ONE
      file's content, unrelated to whether the merge's input list is
      correct. At the 1000-2000 file scale this feature is explicitly
      built for, aborting an otherwise-successful multi-hour run over one
      such file would be disproportionate - so this case is caught,
      recorded as a warning, and that file is skipped; the merge
      continues with the rest. This is a deliberate deviation from
      merge_pdfs()'s stricter policy, not an oversight - documented here
      and in Backlog.md 01.09.2026.
    """
    from docxcompose.composer import Composer

    warnings: list[str] = []
    composer: "Composer | None" = None
    appended = 0
    cancelled = False

    for index, path in enumerate(sources):
        if should_cancel is not None and should_cancel():
            cancelled = True
            break
        if progress_callback is not None:
            progress_callback(f"Datei {done_before + index + 1}/{total_for_progress}: {path.name}")

        doc = _open_docx(path)  # hard-fail on open, see docstring above

        if composer is None:
            composer = Composer(doc)
            appended += 1
            continue

        try:
            composer.doc.add_page_break()
            composer.append(doc)
        except Exception as exc:  # noqa: BLE001 - soft-fail, see docstring above
            warnings.append(f'"{path.name}" konnte nicht angehängt werden und wurde übersprungen ({exc}).')
            continue
        appended += 1

    return (composer.doc if composer is not None else None), appended, cancelled, warnings


def merge_docx_files(
    sources: Sequence[Path],
    destination: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> WordMergeStats:
    """Merge whole DOCX files, in list order, into one new .docx at
    `destination` - the DOCX counterpart of merge_pdfs(), whole-file only
    (see module docstring for why there is no page-range equivalent).

    A page break is inserted between every two sources' content (DOCX has
    no inherent page boundary the way PDF pages give merge_pdfs() one for
    free) so the merged result reads as distinct documents joined at page
    boundaries rather than paragraphs from different sources running
    together.

    Batching (Michael, 01.09.2026 - "automatisch batchen" confirmed): if
    `sources` fits within one `batch_size` (default 100), it is merged in
    a single pass with no intermediate files, exactly like merge_pdfs().
    Above that, sources are split into `batch_size`-sized groups, each
    merged into its own temporary "chunk" .docx first, and THOSE chunk
    files are then merged together the same way into `destination` - a
    genuine two-level merge, not a single continuous pass, so that:
    - the process never has to hold docxcompose's cumulative style/
      numbering bookkeeping for los of 2000 originals open across the
      whole run at once (only one batch's worth at a time, per level),
    - a crash partway through leaves the already-completed chunk files on
      disk as valid, inspectable .docx files (in the TemporaryDirectory,
      so gone once this call returns - but present for the duration of a
      long run, unlike a pure in-memory single pass which loses
      everything on a crash).
    This two-level shape matches what Michael confirmed explicitly (merge
    ~100 into an intermediate result, then merge the intermediates) rather
    than being read as "any batching" - see the AskUserQuestion exchange
    recorded in Backlog.md 01.09.2026. A style/numbering-matching decision
    docxcompose makes when merging chunk B is made relative to what chunk
    B's own composer already contains, not against every one of the
    original 2000 files' styles directly - in rare cases this could
    theoretically resolve a style-name collision slightly differently
    than one giant flat merge of all 2000 at once would have; documented
    here as an accepted, low-probability trade-off (not a hidden bug) in
    exchange for the crash-resilience and memory-bounding above.

    Cancellation is cooperative, polled BETWEEN sources while ORIGINAL
    files are still being opened and appended (both in the single-pass
    path and, in the two-level path, within each first-level batch).
    Deliberately NOT polled again during the two-level path's final
    "merge the completed chunk files together" pass: should_cancel is
    normally a threading.Event, which once set stays set - polling it
    there too would make that pass immediately bail out and keep only the
    FIRST completed chunk, silently discarding every other chunk the
    first-level loop had already finished. Consolidating already-produced
    chunk files is comparatively fast, bounded work, so it always runs to
    completion once started - the practical effect is that a cancelled
    batched run keeps everything completed up to the batch that was in
    progress when cancellation was requested, not just the first batch.
    Either way, whatever was already merged is still saved
    (stats.cancelled=True), the same "keep the partial result" choice
    merge_pdfs() makes.

    Raises ValueError for: an empty `sources` list; a source that can't
    even be opened (see _merge_sequential()'s docstring - this always
    aborts, at either merge level); or every source being skipped/
    cancelled before anything was ever appended.
    """
    if not sources:
        raise ValueError("Keine Quelldateien zum Zusammenführen angegeben.")

    sources = [Path(p) for p in sources]
    total = len(sources)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    resolved_seen: set[Path] = set()
    for path in sources:
        resolved_seen.add(path.resolve())
    files_processed = len(resolved_seen)

    if total <= batch_size:
        doc, appended, cancelled, warnings = _merge_sequential(sources, total, 0, progress_callback, should_cancel)
        if doc is None:
            raise ValueError("Keine der Quelldateien konnte übernommen werden - keine Ausgabe erzeugt.")
        doc.save(str(destination))
        return WordMergeStats(
            segments=appended, files_processed=files_processed, batches=0, cancelled=cancelled, warnings=warnings
        )

    # --- two-level batched path -----------------------------------------
    all_warnings: list[str] = []
    cancelled = False
    total_appended = 0
    chunk_paths: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="pdf_translator_docx_merge_") as tmp:
        tmp_dir = Path(tmp)
        chunks = [sources[i : i + batch_size] for i in range(0, total, batch_size)]

        for batch_index, chunk in enumerate(chunks):
            if progress_callback is not None:
                progress_callback(f"Batch {batch_index + 1}/{len(chunks)} wird zusammengeführt …")
            doc, appended, chunk_cancelled, warnings = _merge_sequential(
                chunk, total, total_appended, progress_callback, should_cancel
            )
            all_warnings.extend(warnings)
            total_appended += appended
            if doc is not None:
                chunk_path = tmp_dir / f"batch_{batch_index:04d}.docx"
                doc.save(str(chunk_path))
                chunk_paths.append(chunk_path)
            if chunk_cancelled:
                cancelled = True
                break

        if not chunk_paths:
            raise ValueError("Keine der Quelldateien konnte übernommen werden - keine Ausgabe erzeugt.")

        if len(chunk_paths) == 1:
            # A plain rename would raise if the OS temp dir and destination
            # are on different filesystems (common - /tmp is often tmpfs) -
            # shutil.move() falls back to copy+delete in that case.
            shutil.move(str(chunk_paths[0]), str(destination))
        else:
            if progress_callback is not None:
                progress_callback(f"Führe {len(chunk_paths)} Zwischenergebnisse zusammen …")
            # should_cancel is deliberately NOT passed through here (unlike
            # the first-level loop above): should_cancel is normally a
            # threading.Event that, once set, stays set - if this second
            # pass polled it too, cancelling partway through batch 3 of 5
            # would make THIS pass immediately bail out as well and only
            # keep chunk 1, silently discarding chunks 2 and 3's already-
            # completed work. Consolidating the chunks that already exist
            # on disk is comparatively fast, bounded work (no new files are
            # opened beyond len(chunk_paths) of them), so it always runs to
            # completion once started, keeping everything the first-level
            # pass did manage to finish before it was told to stop.
            final_doc, _final_appended, _final_cancelled, final_warnings = _merge_sequential(
                chunk_paths, len(chunk_paths), 0, None, None
            )
            all_warnings.extend(final_warnings)
            assert final_doc is not None  # not cancellable here (should_cancel=None above), and chunk_paths is non-empty
            final_doc.save(str(destination))

    return WordMergeStats(
        segments=total_appended,
        files_processed=files_processed,
        batches=len(chunk_paths),
        cancelled=cancelled,
        warnings=all_warnings,
    )
