"""Placeholder protection for terms that must survive translation unchanged
(e.g. a product/brand name derived from the source PDF's filename).

Providers replace protected terms with unique §§N§§ placeholders before
sending text to the translation API, then restore the original spelling
after the translation comes back - so the term itself never has to survive
the translation model/engine intact.
"""
from __future__ import annotations

import re
from pathlib import Path

_LEADING_NUMBER_RE = re.compile(r"^\d+\s+(.+)$")

_PLACEHOLDER_FORMAT = "§§{index}§§"


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
    """Replace every occurrence of any of `terms` in `html` with a unique
    §§N§§ placeholder, matched case-insensitively at word boundaries so
    matches inside HTML tags (e.g. "<b>VIRELICON</b>") are found without
    disturbing the tags themselves.

    Returns the modified html and a mapping of placeholder -> the exact
    text found in `html` (preserving its original casing, not the search
    term's casing), for use with restore_terms().

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
        placeholder = _PLACEHOLDER_FORMAT.format(index=counter)
        mapping[placeholder] = match.group(0)
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
