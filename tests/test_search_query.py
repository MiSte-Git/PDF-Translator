"""Covers pipeline/search_query.py's matches_query()/parse_query() - the
AND/OR boolean query matching added 02.09.2026 (Michael: "Dann sollte im
Suchfeld auch die Möglichkeit einer ODER und UND Verknüpfung der
Suchbegriffe bestehen"), extended the same day to a full nested AND/OR/
parenthesized grammar (Michael: "Ich habe jetzt gerade doch den Fall von
einer Kombinierten Suche die so aussehen würde 'StellarRussia ODER (The
UND Korolev UND Directive)'. Aktuell werden nur die 'StellarRussia' PDFs
gefunden.") - see that module's docstring for the grammar and the
precedence/fallback rules exercised below.
"""
from __future__ import annotations

from pipeline.search_query import matches_query, parse_query


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
    node = parse_query("Sandra")
    assert node == ("term", "Sandra")
    assert matches_query("Contact: Sandra Miller", "Sandra") is True


def test_empty_query_matches_everything() -> None:
    assert matches_query("any text at all", "") is True
    assert matches_query("any text at all", "   ") is True


def test_none_text_never_matches_a_real_query() -> None:
    assert matches_query(None, "Acme") is False
    assert matches_query(None, "Acme OR Zenith") is False


def test_none_text_matches_an_empty_query() -> None:
    assert matches_query(None, "") is True


def test_parenthesized_group_combined_with_or() -> None:
    # Michael's actual query (02.09.2026): "StellarRussia ODER (The UND
    # Korolev UND Directive)" - matching only on "StellarRussia" (ignoring
    # the parenthesized AND-group entirely) was the reported bug.
    query = "StellarRussia ODER (The UND Korolev UND Directive)"
    assert matches_query("Developer: StellarRussia", query) is True
    assert matches_query("The Korolev Directive - a treaty draft", query) is True
    assert matches_query("The Korolev Memorandum", query) is False  # AND-group needs ALL three
    assert matches_query("Zenith Holdings", query) is False


def test_parenthesized_group_combined_with_and() -> None:
    query = "Acme AND (Zenith OR StellarRussia)"
    assert matches_query("Acme Zenith Holdings", query) is True
    assert matches_query("Acme StellarRussia Ventures", query) is True
    assert matches_query("Acme Corp only", query) is False
    assert matches_query("Zenith Holdings without the other term", query) is False


def test_nested_parentheses() -> None:
    query = "Acme AND (Zenith OR (StellarRussia AND Korolev))"
    assert matches_query("Acme StellarRussia Korolev", query) is True
    assert matches_query("Acme StellarRussia only", query) is False  # missing Korolev
    assert matches_query("Acme Zenith", query) is True


def test_mixed_and_or_without_parentheses_uses_and_before_or_precedence() -> None:
    # "A UND B ODER C" == "(A UND B) ODER C" - standard boolean precedence
    # (AND binds tighter than OR), same convention most search tools use,
    # applied here as the default for a mixed query with no explicit
    # grouping. A strict improvement over the previous "degrades to a flat
    # OR, silently dropping the AND part" behavior.
    query = "Acme UND Vertrag ODER StellarRussia"
    assert matches_query("Acme Vertrag GmbH", query) is True  # Acme AND Vertrag
    assert matches_query("StellarRussia Ventures", query) is True  # OR StellarRussia alone
    assert matches_query("Acme only, no contract term", query) is False


def test_unbalanced_parenthesis_falls_back_to_a_single_literal_term() -> None:
    # Never crash a folder scan on a malformed query - falls back to
    # treating the whole typed text as one literal substring, exactly
    # like a query with no recognized operators.
    query = "Acme AND (Zenith"
    node = parse_query(query)
    assert node == ("term", query)
    assert matches_query(f"literally contains {query} verbatim", query) is True
    assert matches_query("Acme Zenith without the parenthesis", query) is False


def test_dangling_operator_falls_back_to_a_single_literal_term() -> None:
    query = "Acme AND"
    assert parse_query(query) == ("term", query)


def test_symbol_operators_and_and_or_are_synonyms_for_the_word_forms() -> None:
    # 02.09.2026 (Michael: "IM Suchfeld sollten auch die Operatoren '||'
    # und '&&' akzeptiert werden.") - exact synonyms for UND/AND and
    # ODER/OR, usable anywhere the word forms are, including mixed with
    # them in the same query.
    assert matches_query("Developer: StellarRussia, QSI ICO: AUREXIS", "StellarRussia && AUREXIS") is True
    assert matches_query("Developer: StellarRussia, QSI ICO: AUREXIS", "StellarRussia && Zenith") is False
    assert matches_query("Developer: StellarRussia", "Acme || StellarRussia") is True
    assert matches_query("Developer: StellarRussia", "Acme || Zenith") is False


def test_symbol_operators_support_the_same_mixed_precedence_and_parentheses() -> None:
    query = "StellarRussia || (The && Korolev && Directive)"
    assert matches_query("Developer: StellarRussia", query) is True
    assert matches_query("The Korolev Directive - a treaty draft", query) is True
    assert matches_query("The Korolev Memorandum", query) is False
    assert matches_query("Zenith Holdings", query) is False

    # Symbol and word forms mixed in one query.
    assert matches_query("Acme Vertrag GmbH", "Acme UND Vertrag || StellarRussia") is True
    assert matches_query("StellarRussia Ventures", "Acme UND Vertrag || StellarRussia") is True
