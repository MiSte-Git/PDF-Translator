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
from typing import Callable

from pipeline.pdf.pymupdf_engine import extract_ico_header_text
from pipeline.word.docx_engine import extract_docx_ico_header_text


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


def find_matching(
    folder: Path,
    extension: str,
    extractor: Callable[[str], str | None],
    query: str,
    recursive: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
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

    A non-empty query is matched as a case-insensitive substring against
    ONLY `extractor`'s result for each file - never the whole first page/
    first paragraphs or whole document (Michael's explicit choice,
    01.09.2026 for PDF, carried over unchanged for DOCX): a document that
    merely MENTIONS another developer's name somewhere in its body text
    must not match.

    progress_callback, if given, is called once per file, right BEFORE
    that file is opened, as (files_done_so_far, total_files, filename) -
    `total_files` is known upfront (the directory walk happens first, in
    full, before any file is opened), so callers can drive a determinate
    progress bar rather than a busy/marquee one.

    Cancellation is cooperative and polled BETWEEN files only, exactly
    like merge_pdfs()'s between-source polling - whatever was already
    found stays in the result (IcoSearchResult.matches), it is never
    discarded on cancel.
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

        if not query:
            matches.append(IcoSearchMatch(path, ""))
        else:
            try:
                header = extractor(str(path))
            except ValueError as exc:
                errors.append(str(exc))
                scanned += 1
                continue
            if header is not None and query.lower() in header.lower():
                matches.append(IcoSearchMatch(path, header))
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
) -> IcoSearchResult:
    """PDF wrapper over find_matching() - see that function's docstring
    for the full contract. Unchanged behavior/signature from before this
    module's 01.09.2026 generalization; the existing PDF test suite
    (tests/test_ui_merge_search.py) covers it unchanged.
    """
    return find_matching(folder, ".pdf", extract_ico_header_text, query, recursive, progress_callback, should_cancel)


def find_docx_files(folder: Path, recursive: bool = True) -> list[Path]:
    """*.docx under `folder` - see find_files_by_extension()."""
    return find_files_by_extension(folder, ".docx", recursive=recursive)


def find_docx_files_matching(
    folder: Path,
    query: str,
    recursive: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> IcoSearchResult:
    """DOCX wrapper over find_matching() (01.09.2026, Michael: "Jetzt noch
    das ganze für *.docx.") - see that function's docstring for the full
    contract, and find_pdfs_matching() for the PDF counterpart this
    mirrors exactly, extractor swapped for
    pipeline.word.docx_engine.extract_docx_ico_header_text().
    """
    return find_matching(folder, ".docx", extract_docx_ico_header_text, query, recursive, progress_callback, should_cancel)
