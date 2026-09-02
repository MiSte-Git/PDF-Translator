"""Date-range/exact-date filtering for the document search feature
(02.09.2026, Michael: "Können wir noch eine nach Datumsbereich, von, bis,
exakt einbauen.").

Confirmed design (AskUserQuestion, 02.09.2026):

- UI: a "Von"/"Bis" (from/to) date-range pair, plus an "Exaktes Datum"
  toggle that swaps in a single date field instead - expressed here as
  nothing more than DateRange(start=d, end=d) for that one day (see
  DateRange below), so the UI is the only place that needs an "exact"
  concept at all; the matching logic never does.
- Source: either the FILE's own modification date (SOURCE_FILE - the same
  date already used by the "Nach Datum sortieren" button, see
  ui/merge_dialog.py/ui/word_merge_dialog.py) or a date found IN the
  document text (SOURCE_DOCUMENT), never both combined in one search
  (Michael: "Eine Quelle pro Suche wählen").
- For SOURCE_DOCUMENT, only specific regions are searched - Michael: "Das
  aber nur entweder im Header, im Footer oder im ICO Feld auf der ersten
  Seite, also für diese Option." (see ui/search_scopes.py's
  DATE_REGION_*/PDF_DATE_REGION_EXTRACTORS/DOCX_DATE_REGION_EXTRACTORS -
  a SEPARATE, smaller region set from the general free-text search
  scopes, since "Footer" isn't one of those).
- Date formats recognized in document text are individually selectable
  (Michael: "Auswahl der verschiedenen Formate"), default ISO only
  (Michael: "Standard ist ISO") - see FORMAT_*/DEFAULT_DATE_FORMATS.

This module is pure date-parsing/matching logic - no Qt, no filesystem
scanning. ui/merge_search.py/ui/drive_search.py call into it per file (the
same way they already call into pipeline/search_query.py for the text
query); the two search dialogs build a DateSearchFilter from their own
widgets.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

# --- recognized date formats ------------------------------------------

FORMAT_ISO = "iso"
FORMAT_DE = "de"
FORMAT_EN_MONTH = "en_month"
FORMAT_SLASH = "slash"
ALL_DATE_FORMATS = (FORMAT_ISO, FORMAT_DE, FORMAT_EN_MONTH, FORMAT_SLASH)

# Michael's confirmed default (AskUserQuestion, 02.09.2026): "Standard ist
# ISO" - every other format is opt-in via its own checkbox.
DEFAULT_DATE_FORMATS: frozenset[str] = frozenset({FORMAT_ISO})

_ISO_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_DE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b")
_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")

_EN_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_EN_MONTH_PATTERN = "|".join(_EN_MONTH_NAMES.keys())
# Two orderings, both common in English documents: "September 1, 2026" and
# "1 September 2026". Named groups per ordering so _find_en_month_dates()
# knows which one matched without a second parse pass.
_EN_MONTH_RE = re.compile(
    rf"\b(?:(?P<month1>{_EN_MONTH_PATTERN})\s+(?P<day1>\d{{1,2}}),?\s+(?P<year1>\d{{4}})"
    rf"|(?P<day2>\d{{1,2}})\s+(?P<month2>{_EN_MONTH_PATTERN})\s+(?P<year2>\d{{4}}))\b",
    re.IGNORECASE,
)


def _safe_date(year: int, month: int, day: int) -> date | None:
    """date(...) but returns None instead of raising for an out-of-range
    combination (e.g. month 13, day 32, or Feb 30) - a regex match on
    plain digits/month names has no guarantee the numbers form a real
    date, and a search filter must never crash a folder scan over one
    odd number in a document.
    """
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_two_digit_year(year: int) -> int:
    """A 2-digit DE-format year ("15.03.26") is assumed to mean 20xx - this
    app's documents are never from the 1900s, so there is no real
    ambiguity to resolve here (unlike the day/month order of the slash
    format below, which genuinely is ambiguous)."""
    return year + 2000 if year < 100 else year


def _find_iso_dates(text: str) -> list[date]:
    dates: list[date] = []
    for match in _ISO_RE.finditer(text):
        year, month, day = (int(part) for part in match.groups())
        parsed = _safe_date(year, month, day)
        if parsed is not None:
            dates.append(parsed)
    return dates


def _find_de_dates(text: str) -> list[date]:
    dates: list[date] = []
    for match in _DE_RE.finditer(text):
        day, month, year = (int(part) for part in match.groups())
        parsed = _safe_date(_normalize_two_digit_year(year), month, day)
        if parsed is not None:
            dates.append(parsed)
    return dates


def _resolve_slash_date(first: int, second: int, year: int) -> date | None:
    """"01/09/2026" is genuinely ambiguous between DD/MM/YYYY and
    MM/DD/YYYY. Tries DD/MM/YYYY first - the same day-before-month
    convention as the DE dot format above, and the more common one
    outside the US - and only falls back to MM/DD/YYYY if that
    combination isn't a valid date at all (e.g. "13/01/2026" can only be
    DD=13/MM=01, not MM=13). A value that's valid either way (e.g.
    "01/09/2026") is resolved as DD/MM/YYYY, matching the DE convention;
    this is a deliberate, documented assumption, not a detected fact
    about the specific document.
    """
    primary = _safe_date(year, second, first)  # first=day, second=month
    if primary is not None:
        return primary
    return _safe_date(year, first, second)  # fallback: first=month, second=day


def _find_slash_dates(text: str) -> list[date]:
    dates: list[date] = []
    for match in _SLASH_RE.finditer(text):
        first, second, year = (int(part) for part in match.groups())
        parsed = _resolve_slash_date(first, second, year)
        if parsed is not None:
            dates.append(parsed)
    return dates


def _find_en_month_dates(text: str) -> list[date]:
    dates: list[date] = []
    for match in _EN_MONTH_RE.finditer(text):
        if match.group("month1") is not None:
            month_name, day_str, year_str = match.group("month1"), match.group("day1"), match.group("year1")
        else:
            month_name, day_str, year_str = match.group("month2"), match.group("day2"), match.group("year2")
        month = _EN_MONTH_NAMES[month_name.lower()]
        parsed = _safe_date(int(year_str), month, int(day_str))
        if parsed is not None:
            dates.append(parsed)
    return dates


_FINDERS = {
    FORMAT_ISO: _find_iso_dates,
    FORMAT_DE: _find_de_dates,
    FORMAT_EN_MONTH: _find_en_month_dates,
    FORMAT_SLASH: _find_slash_dates,
}


def find_dates(text: str, formats) -> list[date]:
    """Every date found in `text`, across whichever of `formats` (see
    FORMAT_*/ALL_DATE_FORMATS above) are given - order/duplicates not
    meaningful, only used via "is ANY of these in range" (see
    matches_document_date() below).
    """
    found: list[date] = []
    for fmt in formats:
        finder = _FINDERS.get(fmt)
        if finder is not None:
            found.extend(finder(text))
    return found


# --- range/exact matching ----------------------------------------------


@dataclass(frozen=True)
class DateRange:
    """An inclusive [start, end] range - either bound may be None for an
    open end ("ab 01.01.2026" / "bis 31.12.2026"). An "exact date" search
    is just start == end for that one day - the UI's "Exaktes Datum"
    toggle is purely a widget-layout choice (one date field instead of
    two); this dataclass never distinguishes "range" from "exact" as
    separate modes.
    """

    start: date | None = None
    end: date | None = None

    def contains(self, candidate: date) -> bool:
        if self.start is not None and candidate < self.start:
            return False
        if self.end is not None and candidate > self.end:
            return False
        return True

    @property
    def is_unbounded(self) -> bool:
        """True if this range would match every date - used by dialogs to
        treat "no dates entered at all" as "no filter", same as an empty
        text query."""
        return self.start is None and self.end is None


SOURCE_FILE = "file"
SOURCE_DOCUMENT = "document"


@dataclass(frozen=True)
class DateSearchFilter:
    """Everything one active date filter needs, built once per search by
    the dialog and passed down to find_matching()/find_drive_matching()
    (ui/merge_search.py, ui/drive_search.py) - see this module's
    docstring for the "one source per search" contract.

    `regions`/`formats` are only meaningful for source=SOURCE_DOCUMENT
    (ignored for SOURCE_FILE, which needs neither a document open nor any
    text parsing - see matches_file_date()).
    """

    source: str
    date_range: DateRange
    regions: frozenset[str] = frozenset()
    formats: frozenset[str] = DEFAULT_DATE_FORMATS


def matches_file_date(path: Path, date_range: DateRange) -> bool:
    """Whether `path`'s own filesystem modification date falls in
    `date_range` - the exact same date the "Nach Datum sortieren" button
    already sorts by (Path.stat().st_mtime), just filtered instead of
    ordered. Local files only - see DriveEntry.modified_time's docstring
    (pipeline/drive_auth.py) for why a Drive scan uses the Drive API's own
    modifiedTime instead of this function.
    """
    mtime = datetime.fromtimestamp(Path(path).stat().st_mtime).date()
    return date_range.contains(mtime)


def matches_document_date(text: str | None, formats, date_range: DateRange) -> bool:
    """Whether ANY date found in `text` (per `formats`, see find_dates())
    falls in `date_range`. `text=None` (nothing extractable for the
    selected region(s), e.g. a document with no footer at all when only
    "Footer" is selected) never matches - same "no text, no match"
    convention as pipeline/search_query.py::matches_query().
    """
    if text is None:
        return False
    return any(date_range.contains(found) for found in find_dates(text, formats))
