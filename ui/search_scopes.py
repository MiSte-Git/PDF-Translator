"""Search-scope registry for the folder/Drive document search (02.09.2026)
- Michael: "Wir haben ja nur 'Suchtext (nur ICO-Kopfbereich auf Seite 1)'
als Suchbereich statisch zur Verfügung. Allerdings sollte das eine Option
sein. Genauso wie die Option 'nur im Header'. Dann sollte es auch möglich
sein im ganzen Text suchen zu können. Auch die Kombination, entweder alle
Optionen, oder nur eine von Dreien..." Confirmed design (02.09.2026, via
AskUserQuestion + a screenshot of a real ICO document's page-1 top area):
three independently-combinable checkboxes -

- "ico_format": page-1-only, header text (word/header2.xml for DOCX, the
  block(s) before the metadata anchor for PDF) UNION the existing
  page-1 metadata region - for ICO-typed documents specifically, silently
  no-match (None) for anything else. See extract_ico_header_text()/
  extract_docx_ico_header_text().
- "header": the document's header, but for NORMAL (non-ICO) documents -
  wiederkehrend über ALLE Seiten (Michael's explicit requirement, unlike
  "ico_format" which stays page-1-only). See extract_pdf_header_text()/
  extract_docx_header_text().
- "full_text": the whole document - the deliberate superset of the other
  two (Michael: "wenn ich im ganzen Dokument suche ist alles inklusive
  Header und oberer Bereich 1. Seite"). See extract_pdf_full_text()/
  extract_docx_full_text().

Kept as its own small module (rather than folded into ui/merge_search.py
or ui/drive_search.py) because BOTH of those - and both search dialogs -
need the exact same registries/combinator, and ui/merge_search.py and
ui/drive_search.py don't otherwise import from each other.
"""
from __future__ import annotations

from typing import Callable

from pipeline.pdf.pymupdf_engine import (
    extract_ico_header_text,
    extract_pdf_footer_text,
    extract_pdf_full_text,
    extract_pdf_header_text,
)
from pipeline.word.docx_engine import (
    extract_docx_footer_text,
    extract_docx_full_text,
    extract_docx_header_text,
    extract_docx_ico_header_text,
)

# Scope keys - shared between both dialogs' checkboxes (ui/merge_search_dialog.py,
# ui/word_merge_search_dialog.py), the worker constructors (ui/workers.py),
# and these registries. Order matters only for display/iteration, not for
# matching (combined_extractor() below just concatenates whichever scopes
# are selected).
SCOPE_ICO_FORMAT = "ico_format"
SCOPE_HEADER = "header"
SCOPE_FULL_TEXT = "full_text"
ALL_SCOPES = (SCOPE_ICO_FORMAT, SCOPE_HEADER, SCOPE_FULL_TEXT)

# Michael's confirmed default (AskUserQuestion, 02.09.2026): a freshly
# opened dialog behaves exactly like before this feature - only the
# former fixed behavior ("ICO Format") is pre-checked.
DEFAULT_SCOPES: frozenset[str] = frozenset({SCOPE_ICO_FORMAT})

PDF_SCOPE_EXTRACTORS: dict[str, Callable[[str], str | None]] = {
    SCOPE_ICO_FORMAT: extract_ico_header_text,
    SCOPE_HEADER: extract_pdf_header_text,
    SCOPE_FULL_TEXT: extract_pdf_full_text,
}

DOCX_SCOPE_EXTRACTORS: dict[str, Callable[[str], str | None]] = {
    SCOPE_ICO_FORMAT: extract_docx_ico_header_text,
    SCOPE_HEADER: extract_docx_header_text,
    SCOPE_FULL_TEXT: extract_docx_full_text,
}


# --- Date-filter regions (02.09.2026) ---------------------------------
#
# Michael, on the date-range filter: "Können wir noch eine nach
# Datumsbereich, von, bis, exakt einbauen." / on where in the document it
# should look: "Das aber nur entweder im Header, im Footer oder im ICO
# Feld auf der ersten Seite, also für diese Option." - a SEPARATE,
# smaller region set from the SCOPE_* text-search scopes above (which
# have no "Footer" option at all, only ICO Format/Header/Volltext):
# DATE_REGION_FOOTER uses the footer extractors added alongside this
# feature (extract_pdf_footer_text()/extract_docx_footer_text()), while
# DATE_REGION_ICO_FORMAT/DATE_REGION_HEADER reuse the exact same
# extractors as SCOPE_ICO_FORMAT/SCOPE_HEADER above - same text, just
# consumed by the date parser (pipeline/date_extract.py) instead of
# matches_query(). combined_extractor() below is format-agnostic (just a
# dict + a set of keys), so it's reused as-is for these regions too - no
# separate combinator needed.
DATE_REGION_ICO_FORMAT = SCOPE_ICO_FORMAT
DATE_REGION_HEADER = SCOPE_HEADER
DATE_REGION_FOOTER = "footer"
ALL_DATE_REGIONS = (DATE_REGION_ICO_FORMAT, DATE_REGION_HEADER, DATE_REGION_FOOTER)

PDF_DATE_REGION_EXTRACTORS: dict[str, Callable[[str], str | None]] = {
    DATE_REGION_ICO_FORMAT: extract_ico_header_text,
    DATE_REGION_HEADER: extract_pdf_header_text,
    DATE_REGION_FOOTER: extract_pdf_footer_text,
}

DOCX_DATE_REGION_EXTRACTORS: dict[str, Callable[[str], str | None]] = {
    DATE_REGION_ICO_FORMAT: extract_docx_ico_header_text,
    DATE_REGION_HEADER: extract_docx_header_text,
    DATE_REGION_FOOTER: extract_docx_footer_text,
}


def combined_extractor(
    scope_extractors: dict[str, Callable[[str], str | None]], scopes
) -> Callable[[str], str | None]:
    """Build one extractor(path) -> text-or-None that concatenates the
    results of every extractor named in `scopes` (see PDF_SCOPE_EXTRACTORS/
    DOCX_SCOPE_EXTRACTORS above) - the mechanism behind the three
    independently-combinable checkboxes. find_matching()/
    find_drive_matching() (ui/merge_search.py, ui/drive_search.py) stay
    format- and scope-agnostic themselves: they only ever call whatever
    single `extractor` callable they're given (see find_matching()'s own
    docstring), so all scope-combination logic lives here.

    Concatenation, not deduplication: "Volltext" alone is already a
    superset of the other two scopes, so selecting it together with
    either is redundant but harmless for substring/AND/OR matching -
    simpler than special-casing which combinations overlap. An empty (or
    all-unrecognized) `scopes` yields an extractor that always returns
    None - deliberately safe rather than silently falling back to some
    default scope if a caller ever passes nothing selected.
    """
    selected = [scope_extractors[name] for name in scopes if name in scope_extractors]

    def extractor(path: str) -> str | None:
        parts = [text for text in (one(path) for one in selected) if text]
        return "\n".join(parts) if parts else None

    return extractor
