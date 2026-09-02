"""Covers pipeline/search_query.py's matches_query()/split_query_terms() -
the AND/OR boolean query matching added 02.09.2026 (Michael: "Dann sollte
im Suchfeld auch die Möglichkeit einer ODER und UND Verknüpfung der
Suchbegriffe bestehen"). Confirmed deliberately simple (AskUserQuestion,
02.09.2026): one operator per query, no mixed precedence/parentheses.
"""
from __future__ import annotations

from pipeline.search_query import matches_query, split_query_terms


def test_plain_query_without_operator_matches_as_a_single_substring() -> None:
    assert matches_query("Issuer Address: Acme Development GmbH", "Acme") is True
    assert matches_query("Issuer Address: Acme Development GmbH", "Zenith") is False


def test_matching_is_case_insensitive() -> None:
    assert matches_query("Issuer Address: Acme Development GmbH", "acme") is True
    assert matches_query("issuer address: acme development gmbh", "ACME") is True


def test_or_query_matches_if_any_term_is_present() -> None:
    assert matches_query("Developer: StellarRussia", "Acme OR StellarRussia") is True
    assert matches_query("Developer: StellarRussia", "Acme ODER StellarRussia") is True
    assert matches_query("Developer: StellarRussia", "Acme OR Zenith") is False


def test_and_query_requires_every_term() -> None:
    assert matches_query("Developer: StellarRussia, QSI ICO: AUREXIS", "StellarRussia AND AUREXIS") is True
    assert matches_query("Developer: StellarRussia, QSI ICO: AUREXIS", "StellarRussia UND AUREXIS") is True
    assert matches_query("Developer: StellarRussia, QSI ICO: AUREXIS", "StellarRussia AND Zenith") is False


def test_operator_keyword_is_case_insensitive() -> None:
    assert matches_query("Developer: StellarRussia", "Acme or StellarRussia") is True
    assert matches_query("Developer: StellarRussia", "acme and StellarRussia") is False


def test_operator_word_embedded_in_a_term_is_not_split() -> None:
    # "Sandra" contains "and" as a substring - must not be mistaken for
    # the AND operator (word-boundary regex in pipeline/search_query.py).
    terms, mode = split_query_terms("Sandra")
    assert terms == ["Sandra"]
    assert mode == "single"
    assert matches_query("Contact: Sandra Miller", "Sandra") is True


def test_empty_query_matches_everything() -> None:
    assert matches_query("any text at all", "") is True
    assert matches_query("any text at all", "   ") is True


def test_none_text_never_matches_a_real_query() -> None:
    assert matches_query(None, "Acme") is False
    assert matches_query(None, "Acme OR Zenith") is False


def test_none_text_matches_an_empty_query() -> None:
    assert matches_query(None, "") is True


def test_query_with_both_keywords_falls_back_to_or_without_crashing() -> None:
    # Deliberately not a validated case (one operator per query) - must
    # degrade gracefully (OR is checked first) rather than raise.
    terms, mode = split_query_terms("Acme OR Zenith AND StellarRussia")
    assert mode == "or"
    assert terms == ["Acme", "Zenith AND StellarRussia"]
