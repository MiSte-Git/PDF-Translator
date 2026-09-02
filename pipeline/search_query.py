"""Simple AND/OR boolean query matching for the document search feature
(02.09.2026) - Michael: "Dann sollte im Suchfeld auch die Möglichkeit
einer ODER und UND Verknüpfung der Suchbegriffe bestehen." Confirmed via
AskUserQuestion (02.09.2026) to stay deliberately simple: exactly ONE
operator per query - either every term OR-combined (any one matching is
enough) or every term AND-combined (every one must match), never mixed
and never with parentheses/precedence. A query using neither keyword is
matched exactly as this feature behaved before 02.09.2026: one literal,
case-insensitive substring - fully backward compatible with every
existing saved/typed query.

Both German (UND/ODER) and English (AND/OR) keywords are recognized,
case-insensitively, so the app's own language toggle (ui/i18n.py) doesn't
also have to translate what the user types into a search field.

Shared between ui/merge_search.py (local scan) and ui/drive_search.py
(Google Drive scan), and both dialogs' PDF/DOCX callers - matching itself
has nothing PDF- or DOCX-specific about it, see ui/search_scopes.py for
where the per-format/per-scope extractor selection happens instead.
"""
from __future__ import annotations

import re

# \b (word boundary) keeps a term like "Sandra" from being split on the
# "and" it happens to contain - \bAND\b only matches "AND" surrounded by
# non-word characters (or string start/end), never mid-word.
_AND_RE = re.compile(r"\b(?:UND|AND)\b", re.IGNORECASE)
_OR_RE = re.compile(r"\b(?:ODER|OR)\b", re.IGNORECASE)


def split_query_terms(query: str) -> tuple[list[str], str]:
    """Split `query` into its individual search terms plus how they
    combine: "or" (any term matching is enough), "and" (every term must
    match), or "single" (no recognized operator - the whole, unsplit
    query is the one term, exactly this feature's pre-02.09.2026
    behavior). Empty/whitespace terms (a leading/trailing/doubled
    operator) are dropped.

    OR is checked before AND, so a query that happens to contain both
    keywords (outside the "one operator per query" contract this was
    deliberately kept simple for - see module docstring) degrades to an
    OR match rather than raising - a folder scan should never crash on
    an unusual query, it should just do its best with it.
    """
    query = (query or "").strip()
    if not query:
        return [], "single"

    or_parts = [part.strip() for part in _OR_RE.split(query) if part.strip()]
    if len(or_parts) > 1:
        return or_parts, "or"

    and_parts = [part.strip() for part in _AND_RE.split(query) if part.strip()]
    if len(and_parts) > 1:
        return and_parts, "and"

    return [query], "single"


def matches_query(text: str | None, query: str) -> bool:
    """Whether `text` matches `query`, term-by-term per split_query_terms()'s
    rules, each term a case-insensitive substring check (same primitive
    this feature always used, just now possibly repeated/combined instead
    of applied once).

    `text=None` (nothing extractable for the file/selected scope(s), e.g.
    a non-ICO document with "ICO Format" as the only checked scope) never
    matches a real query. An empty/whitespace-only `query` matches
    unconditionally - both find_matching() and find_drive_matching()
    already special-case an empty query as "list everything" before an
    extractor is even called, but this function agrees with that
    convention for any other caller too.
    """
    terms, mode = split_query_terms(query)
    if not terms:
        return True
    if text is None:
        return False
    haystack = text.lower()
    if mode == "or":
        return any(term.lower() in haystack for term in terms)
    if mode == "and":
        return all(term.lower() in haystack for term in terms)
    return terms[0].lower() in haystack
