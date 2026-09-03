"""Covers pipeline/translation/protected_terms.py's protect_terms()/
restore_terms() core matching logic - specifically the 03.09.2026
"Case Sensitive" regression (Michael, from a real translated document):
several ordinary English words ("creation", "wisdom", "unfinished", ...)
came back untranslated. Root cause: his protected-terms list holds ICO
names that are meant to always be written in capitals but sometimes
aren't, several of which also happen to be ordinary English words -
matching case-INsensitively protected every casing of those words, not
just the genuine all-caps ICO-name mentions, breaking the surrounding
sentence.

Michael: "Diese Liste sind die einzelnen ICOs, diese sollten immer in
Grossbuchstaben geschrieben sein, sind sie aber nicht immer. Wenn es kein
ICO Name ist, macht es natürlich die ganze Übersetzung kaputt. Von daher
macht es Sinn nur an den Stellen wo das Wort in Grossbuchstaben steht, es
nicht zu übersetzen."
"""
from __future__ import annotations

from pipeline.translation.protected_terms import protect_terms, restore_terms


def test_an_all_caps_occurrence_is_protected() -> None:
    html = "<p>Follow AUREXIS for updates.</p>"

    protected_html, mapping = protect_terms(html, ["Aurexis"])

    assert "AUREXIS" not in protected_html
    assert len(mapping) == 1
    assert list(mapping.values()) == ["AUREXIS"]


def test_a_lowercase_or_mixed_case_occurrence_is_left_untranslated_normally() -> None:
    """The actual regression: "creation" is in Michael's protected-terms
    list (as the name of an ICO that's supposed to be written "CREATION"),
    but an ordinary, lowercase mention of the word must NOT be protected -
    it should translate like any other word."""
    html = "<p>The creation of this system took years. Follow CREATION for updates.</p>"

    protected_html, mapping = protect_terms(html, ["Creation"])

    assert "The creation of this system took years." in protected_html
    assert "CREATION" not in protected_html
    assert len(mapping) == 1
    assert list(mapping.values()) == ["CREATION"]


def test_mixed_case_occurrence_is_never_protected() -> None:
    html = "<p>Follow StellarRussia and QSI to stay updated.</p>"

    protected_html, mapping = protect_terms(html, ["StellarRussia"])

    assert "StellarRussia" in protected_html
    assert not mapping


def test_multiple_occurrences_only_the_all_caps_ones_are_protected() -> None:
    html = "<p>WISDOM guides us. True wisdom is rare. WISDOM never fades.</p>"

    protected_html, mapping = protect_terms(html, ["Wisdom"])

    assert "True wisdom is rare." in protected_html
    assert "WISDOM" not in protected_html
    assert len(mapping) == 2  # both WISDOM occurrences protected, "wisdom" left alone


def test_restore_terms_puts_back_the_exact_all_caps_spelling_found() -> None:
    html = "<p>AUREXIS launches soon.</p>"

    protected_html, mapping = protect_terms(html, ["Aurexis"])
    # Simulate translation of the surrounding text, placeholder untouched.
    translated = protected_html.replace("launches soon", "startet bald")

    restored = restore_terms(translated, mapping)

    assert "AUREXIS startet bald." in restored


def test_matching_is_still_case_insensitive_regardless_of_how_the_term_itself_is_typed() -> None:
    """The term in the settings box can be typed in any casing (Michael
    types "Aurexis", not "AUREXIS") - only the casing of the occurrence
    FOUND in the text decides whether it gets protected, not how the term
    itself happens to be spelled in the list."""
    html = "<p>AUREXIS is live.</p>"

    protected_upper, mapping_upper = protect_terms(html, ["AUREXIS"])
    protected_mixed, mapping_mixed = protect_terms(html, ["Aurexis"])
    protected_lower, mapping_lower = protect_terms(html, ["aurexis"])

    assert protected_upper == protected_mixed == protected_lower
    assert list(mapping_upper.values()) == list(mapping_mixed.values()) == list(mapping_lower.values())
