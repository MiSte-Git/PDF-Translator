"""Google-Drive-Gegenstück zu ui/merge_search.py (01.09.2026, am selben
Tag für DOCX generalisiert - "Jetzt noch das ganze für *.docx").

Michael: "Können wir eine Google Drive Ordner durchsuchen?" - direkter
Anschluss an die lokale Ordnersuche (ui/merge_search.py). Bestätigt: Feature
fest in der App (nicht nur einmalig hier im Chat), im selben Dialog wie die
lokale Suche über einen Umschalter, und Downloads der TREFFER bleiben in
einem vom Nutzer gewählten lokalen Cache-Ordner liegen statt nach dem Lauf
wieder gelöscht zu werden.

Anders als beim lokalen Scan (Datei bereits auf der Platte, "öffnen" kostet
praktisch nichts) ist das Prüfen einer einzelnen Drive-Datei gegen den
ICO-Kopfbereich nur nach einem echten Download möglich. Damit spätere
"Ausgewählte übernehmen"-Klicks im jeweiligen Such-Dialog nie einen
zweiten, verspäteten Download-Schritt brauchen - und Treffer/Nicht-Treffer
aus demselben Lauf konsistent behandelt werden - lädt find_drive_matching()
JEDE gescannte Datei sofort probeweise in ein Temp-Verzeichnis herunter:
- Treffer (oder jede Datei, wenn der Suchtext leer ist - siehe
  find_matching()s identische Konvention in ui/merge_search.py) werden von
  dort in den Cache-Ordner verschoben und bleiben liegen.
- Nicht-Treffer werden sofort verworfen, damit im Cache-Ordner ausschließlich
  tatsächlich relevante Dateien landen (keine Karteileichen).
Bewusste Vereinfachung für diese erste Version: bei leerem Suchtext ("ganzen
Ordner übernehmen") lädt das trotzdem sofort ALLES herunter, nicht erst beim
tatsächlichen Übernehmen der Auswahl - vermeidet eine zweite, komplexere
Zwei-Phasen-Architektur (Metadaten-Liste vs. bereits heruntergeladene
Treffer) für einen Fall, der laut Nutzer ohnehin die Ausnahme ist ("nur
bestimmte von ihnen" war die eigentliche Fragestellung). Für sehr große
Ordner mit leerem Suchtext ist das entsprechend langsamer als nötig - als
bewusst zurückgestellte künftige Optimierung dokumentiert, siehe
Backlog.md 01.09.2026.

Ebenfalls bewusst NICHT umgesetzt: Drives eigene "fullText contains"-Suche
als schneller Vorfilter vor dem Download. Sie würde bei 1000+ Dateien
potenziell viele Downloads sparen, sucht aber über das GESAMTE
Dokument statt nur den Kopfbereich - exakt der Fehler, den die lokale Suche
bewusst vermeidet ("Ein Treffer erwähnt einen anderen Developer nur im
Fließtext -> KEIN Treffer"). Ein solcher Vorfilter dürfte also nur als reine
Kandidaten-Vorauswahl dienen, deren Ergebnis anschließend trotzdem exakt
gegen den Kopfbereich verifiziert wird, nie als Ersatz für die Verifikation
selbst - als möglicher künftiger Geschwindigkeits-Ausbau festgehalten, nicht
in dieser Runde umgesetzt, um die Standardkorrektheit ("solide Lösung", so
der Nutzer wörtlich) nicht von einer Heuristik abhängig zu machen.

find_drive_matching()/_unique_destination() below are format-agnostic (take
a mime type, an `extractor`, and a `default_extension` for naming) -
find_drive_pdfs_matching() is now a thin PDF-specific wrapper over them
(same behavior/signature as before this generalization), and
ui/word_drive_search.py::find_drive_docx_matching() is the DOCX-specific
wrapper, mirroring ui/merge_search.py's find_files_by_extension()/
find_matching() vs. find_pdf_files()/find_pdfs_matching() split.
"""
from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Protocol

from pipeline.date_extract import DateSearchFilter, SOURCE_FILE, matches_document_date
from pipeline.drive_auth import DOCX_MIME_TYPE, PDF_MIME_TYPE, DriveEntry
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

_FOLDER_URL_RE = re.compile(r"/folders/([A-Za-z0-9_-]+)")
_ID_QUERY_RE = re.compile(r"[?&]id=([A-Za-z0-9_-]+)")
_BARE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def extract_folder_id(text: str) -> str:
    """Pull a Drive folder id out of a pasted share link, or accept a bare id.

    Handles the two link shapes Drive's "Link kopieren" actually produces
    (https://drive.google.com/drive/folders/<id>[?usp=...] and the older
    ?id=<id> query form) plus a bare id pasted directly. Raises ValueError
    with a message meant to be shown to the user directly (see
    MergeSearchDialog._resolve_drive_folder()) rather than a generic
    "invalid input".
    """
    text = text.strip()
    if not text:
        raise ValueError("Bitte einen Drive-Ordnerlink oder eine Ordner-ID eingeben.")
    match = _FOLDER_URL_RE.search(text)
    if match:
        return match.group(1)
    match = _ID_QUERY_RE.search(text)
    if match:
        return match.group(1)
    if _BARE_ID_RE.match(text):
        return text
    raise ValueError(
        "Konnte keine Ordner-ID aus dem eingefügten Text erkennen. Bitte den "
        "Freigabelink des Ordners (Rechtsklick in Drive -> 'Link kopieren') oder "
        "die reine Ordner-ID einfügen."
    )


class DriveClientProtocol(Protocol):
    """Structural shape find_drive_matching() needs - see pipeline/drive_auth.py::DriveClient."""

    def list_children(self, folder_id: str, file_mime_type: str): ...

    def download(self, file_id: str, destination: Path) -> None: ...


@dataclass
class DriveSearchMatch:
    drive_id: str
    drive_name: str
    local_path: Path
    snippet: str = ""


@dataclass
class DriveSearchResult:
    matches: list[DriveSearchMatch] = field(default_factory=list)
    scanned: int = 0
    errors: list[str] = field(default_factory=list)
    cancelled: bool = False


def _unique_destination(cache_dir: Path, name: str, default_extension: str) -> Path:
    """Pick a non-colliding path under cache_dir for a Drive file named `name`.

    Two different Drive folders (or two different developers' files) can
    easily share a plain file name like "Term Sheet.pdf"/"Term Sheet.docx"
    - silently overwriting an earlier match with a same-named later one
    would be exactly the kind of quiet data loss a "solide Lösung" must
    not have. `default_extension` (".pdf"/".docx") is appended only if the
    Drive file's own name doesn't already end in it - Drive file names are
    free text and don't always carry the "real" extension.
    """
    safe_name = name.replace("/", "_").replace("\\", "_").strip() or f"unbenannt{default_extension}"
    if not safe_name.lower().endswith(default_extension.lower()):
        safe_name += default_extension
    candidate = cache_dir / safe_name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while True:
        candidate = cache_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _iter_drive_files(client: DriveClientProtocol, root_folder_id: str, file_mime_type: str, recursive: bool):
    """Breadth-first walk yielding every `file_mime_type` DriveEntry found under root_folder_id."""
    queue: list[str] = [root_folder_id]
    while queue:
        folder_id = queue.pop(0)
        for entry in client.list_children(folder_id, file_mime_type=file_mime_type):
            if entry.is_folder:
                if recursive:
                    queue.append(entry.id)
                continue
            yield entry


def _passes_drive_date_filter(
    entry: DriveEntry,
    tmp_path: Path,
    date_filter: DateSearchFilter,
    date_region_extractor: Callable[[str], str | None] | None,
) -> bool:
    """Drive counterpart of ui/merge_search.py::_passes_date_filter() -
    SOURCE_FILE uses `entry.modified_time` (Drive's own metadata, see
    DriveEntry.modified_time's docstring in pipeline/drive_auth.py) rather
    than tmp_path's local filesystem mtime, which would only ever reflect
    "when this scan happened to download it", not the file's real,
    Drive-side modification date. SOURCE_DOCUMENT reads `tmp_path` (the
    already-downloaded temp copy) exactly like the text-query extractor
    already does.
    """
    if date_filter.source == SOURCE_FILE:
        return entry.modified_time is not None and date_filter.date_range.contains(entry.modified_time)
    text = date_region_extractor(str(tmp_path)) if date_region_extractor is not None else None
    return matches_document_date(text, date_filter.formats, date_filter.date_range)


def find_drive_matching(
    client: DriveClientProtocol,
    root_folder_id: str,
    file_mime_type: str,
    extractor: Callable[[str], str | None],
    default_extension: str,
    query: str,
    recursive: bool,
    cache_dir: Path,
    progress: Callable[[int, int, str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    date_filter: DateSearchFilter | None = None,
    date_region_extractor: Callable[[str], str | None] | None = None,
) -> DriveSearchResult:
    """Scan a Drive folder (optionally recursive) for `file_mime_type`
    files matching query, using `extractor` for the per-file ICO-header
    text check - the Drive counterpart of ui/merge_search.py::
    find_matching(). See find_drive_pdfs_matching()/
    ui/word_drive_search.py::find_drive_docx_matching() for the per-format
    wrappers this is built for.

    query="" means every file found counts as a match (still downloaded,
    see module docstring), a non-empty query is matched (see
    pipeline/search_query.py::matches_query() - case-insensitive
    substring per term, with optional UND/AND / ODER/OR combination since
    02.09.2026) against ONLY `extractor`'s result - never the rest of the
    document by default, unless the caller explicitly widened `extractor`
    itself (see find_drive_pdfs_matching()'s `scopes` parameter,
    02.09.2026, and ui/search_scopes.py). Per-file download/read errors
    are collected into result.errors rather
    than aborting the whole scan; is_cancelled() is checked between files
    so a long scan can be stopped promptly, and result.scanned always
    reflects files actually looked at even when cancelled partway through.

    The full list of candidate files is gathered up front (list_children()
    is metadata-only and cheap even for 1000+ files - it is the download
    step afterwards that is slow), so `progress`'s `total` argument is a
    real, stable count from the very first call, exactly like the local
    scan's deterministic progress bar.

    `date_filter` (02.09.2026, see pipeline/date_extract.py and
    ui/merge_search.py::find_matching()'s identical parameter for the
    full contract) is an ADDITIONAL, independent condition alongside the
    text query. SOURCE_FILE reads the file's date from Drive's own
    metadata (entry.modified_time), never from the downloaded temp
    copy's local mtime - see _passes_drive_date_filter()'s docstring for
    why that distinction matters here specifically.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    result = DriveSearchResult()
    query_normalized = query.strip().casefold()

    try:
        candidates = list(_iter_drive_files(client, root_folder_id, file_mime_type, recursive))
    except Exception as exc:
        result.errors.append(f"Ordner konnte nicht gelesen werden: {exc}")
        return result

    total = len(candidates)
    with tempfile.TemporaryDirectory(prefix="pdf_translator_drive_scan_") as tmp:
        tmp_dir = Path(tmp)
        for index, entry in enumerate(candidates):
            if is_cancelled is not None and is_cancelled():
                result.cancelled = True
                return result
            if progress is not None:
                progress(index, total, entry.name)

            tmp_path = tmp_dir / f"{entry.id}{default_extension}"
            try:
                client.download(entry.id, tmp_path)
            except Exception as exc:
                result.errors.append(f"{entry.name}: Download fehlgeschlagen ({exc})")
                result.scanned += 1
                continue

            header_text = None
            if query_normalized:
                try:
                    header_text = extractor(str(tmp_path))
                except Exception as exc:
                    result.errors.append(f"{entry.name}: {exc}")
                    result.scanned += 1
                    continue
                if not matches_query(header_text, query):
                    result.scanned += 1
                    continue

            if date_filter is not None:
                try:
                    date_ok = _passes_drive_date_filter(entry, tmp_path, date_filter, date_region_extractor)
                except Exception as exc:
                    result.errors.append(f"{entry.name}: {exc}")
                    result.scanned += 1
                    continue
                if not date_ok:
                    result.scanned += 1
                    continue

            result.scanned += 1
            snippet = header_text or ""

            destination = _unique_destination(cache_dir, entry.name, default_extension)
            tmp_path.replace(destination)
            result.matches.append(DriveSearchMatch(drive_id=entry.id, drive_name=entry.name, local_path=destination, snippet=snippet))

    if progress is not None:
        progress(total, total, "")
    return result


def find_drive_pdfs_matching(
    client: DriveClientProtocol,
    root_folder_id: str,
    query: str,
    recursive: bool,
    cache_dir: Path,
    progress: Callable[[int, int, str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    scopes: Iterable[str] | None = None,
    date_filter: DateSearchFilter | None = None,
) -> DriveSearchResult:
    """PDF wrapper over find_drive_matching() - unchanged behavior for
    every caller/test that predates the `scopes` parameter (02.09.2026,
    the new "ICO Format"/"Header"/"Volltext" checkboxes - see
    find_pdfs_matching() in ui/merge_search.py and ui/search_scopes.py):
    None (the default) keeps this function's exact original, "ICO
    Format"-only behavior (tests/test_ui_drive_search.py covers it
    unchanged).

    `date_filter` (02.09.2026, see find_pdfs_matching()'s identical
    parameter in ui/merge_search.py for the full contract): None (the
    default) means no date filtering, same as before this feature.
    """
    extractor = extract_ico_header_text if scopes is None else combined_extractor(PDF_SCOPE_EXTRACTORS, scopes)
    date_region_extractor = (
        combined_extractor(PDF_DATE_REGION_EXTRACTORS, date_filter.regions) if date_filter is not None else None
    )
    return find_drive_matching(
        client, root_folder_id, PDF_MIME_TYPE, extractor, ".pdf", query, recursive, cache_dir, progress, is_cancelled,
        date_filter=date_filter, date_region_extractor=date_region_extractor,
    )


def find_drive_docx_matching(
    client: DriveClientProtocol,
    root_folder_id: str,
    query: str,
    recursive: bool,
    cache_dir: Path,
    progress: Callable[[int, int, str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    scopes: Iterable[str] | None = None,
    date_filter: DateSearchFilter | None = None,
) -> DriveSearchResult:
    """DOCX wrapper over find_drive_matching() (01.09.2026, Michael:
    "Jetzt noch das ganze für *.docx.") - the Drive counterpart of
    find_docx_files_matching() (ui/merge_search.py), mirroring
    find_drive_pdfs_matching() exactly with the DOCX mime type and
    extractor(s)/date-region-extractor(s) swapped in - see that
    function's docstring for the `scopes` (02.09.2026) and `date_filter`
    (02.09.2026) parameters.
    """
    extractor = extract_docx_ico_header_text if scopes is None else combined_extractor(DOCX_SCOPE_EXTRACTORS, scopes)
    date_region_extractor = (
        combined_extractor(DOCX_DATE_REGION_EXTRACTORS, date_filter.regions) if date_filter is not None else None
    )
    return find_drive_matching(
        client, root_folder_id, DOCX_MIME_TYPE, extractor, ".docx", query, recursive, cache_dir, progress, is_cancelled,
        date_filter=date_filter, date_region_extractor=date_region_extractor,
    )
