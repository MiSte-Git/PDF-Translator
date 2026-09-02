"""Folder scan + ICO-header text filter for the merge dialog's "Ordner
durchsuchen" panel (01.09.2026, generalized beyond PDF on the same day for
ui/word_merge_search_dialog.py's DOCX equivalent).

Michael: "Wie sollten wir es machen wenn ich einen Ordner mit 1000 oder
mehr PDFs habe aber nur bestimmte von ihnen zusammenführen möchte. Zum
Beispiel eines bestimmten Developers in den ICO PDFs. Der Developer Name
steht ja im oberen geschützten Teil." Confirmed with Michael (01.09.2026):
match against the ICO metadata region specifically (not the whole first
page or whole document - see extract_ico_header_text()'s docstring for
exactly what that region is), and make recursive subfolder scanning a
UI-visible toggle rather than a fixed choice.

Like ui/merge_job.py, this is deliberately its own small module rather
than folded into TranslationRequest/ui/analysis.py: a folder scan is a
read-only, non-translating operation with its own result shape (matches +
a text snippet per match for human review, not a cost estimate).

"Können wir eine Google Drive Ordner durchsuchen?" -> "Jetzt noch das
ganze für *.docx" (01.09.2026, same day): rather than duplicating this
whole module for DOCX, find_files_by_extension()/find_matching() below
are the format-agnostic engine - find_pdf_files()/find_pdfs_matching()
are now thin wrappers over them (kept byte-for-byte behavior-compatible,
same existing tests cover them unchanged) and
ui/word_merge_search.py::find_docx_files()/find_docx_files_matching()
are the DOCX-side wrappers calling the exact same two generic functions
with ".docx"/extract_docx_ico_header_text instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from pipeline.date_extract import DateSearchFilter, SOURCE_FILE, matches_document_date, matches_file_date
from pipeline.pdf.pymupdf_engine import extract_ico_header_text
from pipeline.search_query import matches_query
from pipeline.word.docx_engine import extract_docx_ico_header_text
from ui.search_scopes import (
    DOCX_DATE_REGION_EXTRACTORS,
    DOCX_SCOPE_EXTRACTORS,
    PDF_DATE_REGION_EXTRACTORS,
    PDF_SCOPE_EXTRACTORS,
    combined_extractor,
)


@dataclass
class IcoSearchMatch:
    path: Path
    snippet: str
    """The header-extractor's full result for this file - empty ("") only
    for the empty-query "every file in this folder" case (see
    find_matching()'s docstring), where no file is ever opened to begin
    with, so there is nothing to show."""


@dataclass
class IcoSearchResult:
    matches: list[IcoSearchMatch]
    scanned: int
    """Files actually opened/checked - equals len(matches) for an empty
    query (nothing is opened, see above), and can be LESS than the total
    file count found under `folder` if the scan was cancelled partway."""
    errors: list[str] = field(default_factory=list)
    """One entry per file that could not be opened (missing, corrupt,
    encrypted) - see the header-extractor's ValueError. A scan doesn't
    abort on these; they're surfaced for review instead, the same
    "collect, don't abort" policy translate_pdf() uses for a single bad
    block."""
    cancelled: bool = False


def find_files_by_extension(folder: Path, extension: str, recursive: bool = True) -> list[Path]:
    """Every file under `folder` whose suffix matches `extension`
    (case-insensitive, so "Report.PDF"/"Report.DOCX" are found too -
    glob() itself is case-sensitive on Linux, unlike Windows/macOS'
    usually-case-insensitive filesystems), sorted by path for a
    deterministic scan order (and so progress_callback's "X/Y" counts mean
    the same thing on a re-run). `extension` includes the leading dot
    (".pdf", ".docx").
    """
    folder = Path(folder)
    entries = folder.rglob("*") if recursive else folder.glob("*")
    return sorted(path for path in entries if path.is_file() and path.suffix.lower() == extension.lower())


def _passes_date_filter(
    path: Path,
    date_filter: DateSearchFilter,
    date_region_extractor: Callable[[str], str | None] | None,
) -> bool:
    """Whether `path` passes `date_filter` - SOURCE_FILE never opens the
    file at all (just Path.stat(), see matches_file_date()); SOURCE_DOCUMENT
    calls `date_region_extractor` (built by find_pdfs_matching()/
    find_docx_files_matching() from the caller's selected regions) to get
    the text to search for a date in. May raise ValueError (a bad-document
    error from the region extractor), same as the text-query `extractor` -
    the caller catches it the same way.
    """
    if date_filter.source == SOURCE_FILE:
        return matches_file_date(path, date_filter.date_range)
    text = date_region_extractor(str(path)) if date_region_extractor is not None else None
    return matches_document_date(text, date_filter.formats, date_filter.date_range)


def find_matching(
    folder: Path,
    extension: str,
    extractor: Callable[[str], str | None],
    query: str,
    recursive: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    date_filter: DateSearchFilter | None = None,
    date_region_extractor: Callable[[str], str | None] | None = None,
) -> IcoSearchResult:
    """Scan every `extension` file under `folder` and keep those matching
    `query`, per `extractor`'s per-file ICO-header text (or None if that
    file has no ICO header at all - not this document type, not an
    error). See find_pdfs_matching()/find_docx_files_matching() for the
    per-format wrappers this is built for; this function itself never
    imports a document engine directly, only calls whatever `extractor`
    it's given, so it stays format-agnostic.

    An empty/whitespace-only `query` matches EVERY file found - no file is
    even opened in that case - so this one function doubles as "list
    every file in this folder" (an empty search) and "filter by developer
    name" (a non-empty one), rather than being two separate features/
    buttons.

    A non-empty query is matched (see pipeline/search_query.py::
    matches_query() - case-insensitive substring per term, with optional
    UND/AND / ODER/OR combination since 02.09.2026) against ONLY
    `extractor`'s result for each file - never the whole first page/first
    paragraphs or whole document by default (Michael's explicit choice,
    01.09.2026 for PDF, carried over unchanged for DOCX): a document that
    merely MENTIONS another developer's name somewhere in its body text
    must not match UNLESS the caller explicitly widened `extractor` itself
    to cover more (see find_pdfs_matching()'s `scopes` parameter,
    02.09.2026, and ui/search_scopes.py).

    progress_callback, if given, is called once per file, right BEFORE
    that file is opened, as (files_done_so_far, total_files, filename) -
    `total_files` is known upfront (the directory walk happens first, in
    full, before any file is opened), so callers can drive a determinate
    progress bar rather than a busy/marquee one.

    Cancellation is cooperative and polled BETWEEN files only, exactly
    like merge_pdfs()'s between-source polling - whatever was already
    found stays in the result (IcoSearchResult.matches), it is never
    discarded on cancel.

    `date_filter` (02.09.2026, the "Datumsbereich"/"Von"/"Bis"/"Exakt"
    filter - see pipeline/date_extract.py and find_pdfs_matching()'s
    `date_filter` parameter) is an ADDITIONAL, independent condition: a
    file must match both the text query above AND the date filter (if
    either is given) to end up in the result. A file whose date can't be
    determined at all (SOURCE_FILE: unreadable stat - practically never
    happens; SOURCE_DOCUMENT: extractor found no text/no date in the
    selected region(s)) never matches, same "no data, no match"
    convention as the text query's `text=None` case. Opening the document
    is skipped entirely when neither the query nor a SOURCE_DOCUMENT date
    filter needs it - a SOURCE_FILE filter alone only ever calls
    Path.stat(), never `extractor`/`date_region_extractor`.
    """
    paths = find_files_by_extension(folder, extension, recursive=recursive)
    query = (query or "").strip()
    total = len(paths)
    matches: list[IcoSearchMatch] = []
    errors: list[str] = []
    scanned = 0
    cancelled = False

    for path in paths:
        if should_cancel is not None and should_cancel():
            cancelled = True
            break
        if progress_callback is not None:
            progress_callback(scanned, total, path.name)

        header: str | None = None
        if query:
            try:
                header = extractor(str(path))
            except ValueError as exc:
                errors.append(str(exc))
                scanned += 1
                continue
            if not matches_query(header, query):
                scanned += 1
                continue

        if date_filter is not None:
            try:
                if not _passes_date_filter(path, date_filter, date_region_extractor):
                    scanned += 1
                    continue
            except ValueError as exc:
                errors.append(str(exc))
                scanned += 1
                continue

        matches.append(IcoSearchMatch(path, header or ""))
        scanned += 1

    return IcoSearchResult(matches=matches, scanned=scanned, errors=errors, cancelled=cancelled)


def find_pdf_files(folder: Path, recursive: bool = True) -> list[Path]:
    """*.pdf under `folder` - see find_files_by_extension()."""
    return find_files_by_extension(folder, ".pdf", recursive=recursive)


def find_pdfs_matching(
    folder: Path,
    query: str,
    recursive: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    scopes: Iterable[str] | None = None,
    date_filter: DateSearchFilter | None = None,
) -> IcoSearchResult:
    """PDF wrapper over find_matching() - see that function's docstring
    for the full contract.

    `scopes` (02.09.2026, the new "ICO Format"/"Header"/"Volltext"
    checkboxes - see ui/search_scopes.py): which scope(s) to combine.
    None (the default) preserves this function's exact original
    behavior - "ICO Format" only - unchanged for every caller/test that
    predates this feature and doesn't pass it (tests/test_ui_merge_search.py).

    `date_filter` (02.09.2026, "Datumsbereich"/"Von"/"Bis"/"Exakt" - see
    pipeline/date_extract.py): None (the default) means no date filtering
    at all, same as before this feature. A SOURCE_DOCUMENT filter's
    region(s) are looked up in PDF_DATE_REGION_EXTRACTORS (ICO Format/
    Header/Footer - a separate, smaller set from `scopes` above, since
    "Footer" isn't a general text-search scope).
    """
    extractor = extract_ico_header_text if scopes is None else combined_extractor(PDF_SCOPE_EXTRACTORS, scopes)
    date_region_extractor = (
        combined_extractor(PDF_DATE_REGION_EXTRACTORS, date_filter.regions) if date_filter is not None else None
    )
    return find_matching(
        folder, ".pdf", extractor, query, recursive, progress_callback, should_cancel,
        date_filter=date_filter, date_region_extractor=date_region_extractor,
    )


def find_docx_files(folder: Path, recursive: bool = True) -> list[Path]:
    """*.docx under `folder` - see find_files_by_extension()."""
    return find_files_by_extension(folder, ".docx", recursive=recursive)


def find_docx_files_matching(
    folder: Path,
    query: str,
    recursive: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    scopes: Iterable[str] | None = None,
    date_filter: DateSearchFilter | None = None,
) -> IcoSearchResult:
    """DOCX wrapper over find_matching() (01.09.2026, Michael: "Jetzt noch
    das ganze für *.docx.") - see that function's docstring for the full
    contract, and find_pdfs_matching() for the PDF counterpart this
    mirrors exactly, extractor swapped for
    pipeline.word.docx_engine.extract_docx_ico_header_text() (or a
    `scopes`-combined extractor, see find_pdfs_matching()'s docstring for
    that parameter - identical contract here), and `date_filter`'s
    regions looked up in DOCX_DATE_REGION_EXTRACTORS instead of the PDF
    registry (also identical contract, see find_pdfs_matching()'s
    docstring for `date_filter`).
    """
    extractor = extract_docx_ico_header_text if scopes is None else combined_extractor(DOCX_SCOPE_EXTRACTORS, scopes)
    date_region_extractor = (
        combined_extractor(DOCX_DATE_REGION_EXTRACTORS, date_filter.regions) if date_filter is not None else None
    )
    return find_matching(
        folder, ".docx", extractor, query, recursive, progress_callback, should_cancel,
        date_filter=date_filter, date_region_extractor=date_region_extractor,
    )
