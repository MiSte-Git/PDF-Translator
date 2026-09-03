"""Placeholder protection for terms that must survive translation unchanged
(e.g. a product/brand name derived from the source PDF's filename).

Providers replace protected terms with unique §§N§§ placeholders before
sending text to the translation API, then restore the original spelling
after the translation comes back - so the term itself never has to survive
the translation model/engine intact.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

_LEADING_NUMBER_RE = re.compile(r"^\d+\s+(.+)$")

_PLACEHOLDER_FORMAT = "§§{index}§§"

# First-row values that mark a header line rather than a real term when a
# term list is loaded from a file (see load_protected_terms_file()).
_HEADER_WORDS = frozenset({"term", "terms", "begriff", "begriffe", "protected", "geschützt", "wort", "word"})

_CSV_DELIMITERS = ";,\t|"


def load_protected_terms_file(path: str | Path) -> list[str]:
    """Read protected terms from a .csv/.txt/.tsv file - one term per row
    (03.09.2026: Michael wanted to load term lists from a file instead of
    typing every term by hand into the "Geschützte Begriffe" box).

    Rules, kept deliberately simple so any spreadsheet export works:
    - Only the FIRST column of every row is used, so a sheet with a
      "comment"/"translation" column next to the terms still loads fine.
      A plain .txt with one term per line is just a one-column CSV.
    - The delimiter (";", ",", tab or "|") is sniffed per file; a file
      without any delimiter is read as one term per line.
    - A first row that is just a column header ("Term", "Begriff", ...)
      is skipped; every other row is a term.
    - Empty cells, surrounding whitespace and duplicates (case-insensitive,
      first spelling wins) are dropped; the order of the file is kept.
    - Encoding: UTF-8 (a BOM from Excel is tolerated), falling back to
      cp1252 for older Windows exports.

    Raises FileNotFoundError / UnicodeDecodeError untouched so the caller
    (the UI) can show them.
    """
    file_path = Path(path)
    raw = file_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")

    sample = text[:4096]
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(sample, delimiters=_CSV_DELIMITERS)
    except csv.Error:
        # No consistent delimiter (typically a plain "one term per line"
        # .txt): the default excel dialect then yields one cell per line.
        dialect = csv.excel

    terms: list[str] = []
    seen: set[str] = set()
    for row_index, row in enumerate(csv.reader(text.splitlines(), dialect)):
        if not row:
            continue
        term = row[0].strip()
        if not term:
            continue
        if row_index == 0 and term.casefold() in _HEADER_WORDS:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
    return terms


def merge_protected_terms(existing_text: str, new_terms: list[str]) -> str:
    """Append `new_terms` to the newline-separated `existing_text` of the UI's
    protected-terms box, skipping terms already present (case-insensitive)
    so loading the same file twice does not duplicate anything.
    """
    lines = [line.strip() for line in existing_text.splitlines() if line.strip()]
    seen = {line.casefold() for line in lines}
    for term in new_terms:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(term)
    return "\n".join(lines)


def derive_protected_term(filename: str) -> str:
    """Derive the term to protect from a source PDF's filename.

    Strips the file extension (suffix after the last dot) and an optional
    leading "<number> " prefix (e.g. an ISIN-like document number), e.g.
    "1526 VIRELICON.pdf" -> "VIRELICON". If there is no leading
    number-plus-space prefix, the bare stem is returned as-is.
    """
    stem = Path(filename).stem.strip()
    match = _LEADING_NUMBER_RE.match(stem)
    if match:
        return match.group(1).strip()
    return stem


def protect_terms(html: str, terms: list[str]) -> tuple[str, dict[str, str]]:
    """Replace every occurrence of any of `terms` in `html` that is written
    in ALL CAPS with a unique §§N§§ placeholder, matched at word
    boundaries so matches inside HTML tags (e.g. "<b>VIRELICON</b>") are
    found without disturbing the tags themselves. An occurrence of the
    same term that is NOT all-uppercase (lower/mixed case) is left alone -
    untouched, translated normally like any other word.

    03.09.2026 (Michael, real translated documents: several ordinary
    English words - "creation", "wisdom", "unfinished", ... - were coming
    back untranslated): his protected-terms list holds the names of
    individual ICOs, which are meant to always be written in capitals but
    in practice sometimes aren't - and several of those names happen to
    also be ordinary English words. Matching case-INsensitively (the
    previous behavior) meant a lowercase, perfectly ordinary occurrence of
    such a word got "protected" (left untranslated) right along with the
    genuine, all-caps ICO-name occurrences, breaking the surrounding
    sentence's translation. Michael: "Von daher macht es Sinn nur an den
    Stellen wo das Wort in Grossbuchstaben steht, es nicht zu übersetzen,
    ansonsten muss das später per Hand korrigiert werden." Matching is
    still done case-insensitively (a term can be typed in the settings box
    in any casing - only the casing of the occurrence FOUND in the text
    decides whether it's protected), so this is not "exact-case matching
    against the term's own spelling" - it's specifically "protect only
    where the found text is fully uppercase".

    Returns the modified html and a mapping of placeholder -> the exact
    text found in `html` (always its all-caps original spelling, since
    only all-caps occurrences are ever replaced), for use with
    restore_terms().

    Terms are matched longest-first so a shorter term can't shadow a longer
    one that contains it.
    """
    mapping: dict[str, str] = {}

    non_empty_terms = [term for term in terms if term]
    if not non_empty_terms:
        return html, mapping

    ordered_terms = sorted(non_empty_terms, key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(term) for term in ordered_terms) + r")\b",
        re.IGNORECASE,
    )

    counter = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal counter
        found = match.group(0)
        if not found.isupper():
            # Not written in all caps here - not a genuine ICO-name
            # occurrence (or Michael's term list simply hasn't caught up
            # to how this particular mention is capitalized) - leave it
            # for normal translation rather than protecting it.
            return found
        placeholder = _PLACEHOLDER_FORMAT.format(index=counter)
        mapping[placeholder] = found
        counter += 1
        return placeholder

    modified_html = pattern.sub(_replace, html)
    return modified_html, mapping


def restore_terms(html: str, mapping: dict[str, str]) -> str:
    """Replace every §§N§§ placeholder in `html` with its original text
    from `mapping` (as produced by protect_terms()).
    """
    for placeholder, original_text in mapping.items():
        html = html.replace(placeholder, original_text)
    return html
