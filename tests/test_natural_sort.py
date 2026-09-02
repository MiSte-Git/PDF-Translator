"""Covers ui/natural_sort.py's natural_sort_key() (02.09.2026, Michael:
"Die Dateinamen fangen hier aktuell alle mit Nummern an, dann ein
Leerzeichen und dann Text. Ich dachte das nach Namen sortieren
Standardmässig immer erst die Nummern ausliest, wenn das nicht der Fall
ist kommt da eine falsche Sortierung für die ICOs für mich zustande.").

Michael's own real-world example is used directly below: "176
ChinaAMC.pdf" must sort BEFORE "1747 ABSENCE.pdf" (176 < 1747
numerically), which a plain `str.lower()` key gets backwards (comparing
"176 ..." against "1747 ..." character by character, '6' > '4' at the
third character).
"""
from __future__ import annotations

from ui.natural_sort import natural_sort_key


def test_ico_numbered_filenames_sort_numerically_not_lexicographically() -> None:
    # Plain string sort would give: "1747 ABSENCE.pdf", "1750 ANEMNESIS.pdf",
    # "1759 IDEOGENESIS.pdf", "176 ChinaAMC.pdf" (wrong - 176 last).
    names = [
        "1747 ABSENCE.pdf",
        "1750 ANEMNESIS.pdf",
        "1759 IDEOGENESIS.pdf",
        "176 ChinaAMC.pdf",
    ]
    assert sorted(names, key=natural_sort_key) == [
        "176 ChinaAMC.pdf",
        "1747 ABSENCE.pdf",
        "1750 ANEMNESIS.pdf",
        "1759 IDEOGENESIS.pdf",
    ]
    # A plain string sort really does get this wrong, confirming the test
    # above is actually exercising something (not just restating the input).
    assert sorted(names, key=str.lower) != sorted(names, key=natural_sort_key)


def test_equal_length_numbers_still_compare_numerically() -> None:
    assert sorted(["020 b.pdf", "003 a.pdf", "100 c.pdf"], key=natural_sort_key) == [
        "003 a.pdf",
        "020 b.pdf",
        "100 c.pdf",
    ]


def test_names_without_any_digits_fall_back_to_plain_alphabetical() -> None:
    assert sorted(["Zeta.pdf", "Alpha.pdf", "Mitte.pdf"], key=natural_sort_key) == [
        "Alpha.pdf",
        "Mitte.pdf",
        "Zeta.pdf",
    ]


def test_case_insensitive_like_the_previous_str_lower_key() -> None:
    assert sorted(["Bravo.pdf", "alpha.pdf"], key=natural_sort_key) == ["alpha.pdf", "Bravo.pdf"]


def test_embedded_not_only_leading_digits_are_compared_numerically() -> None:
    # Digits don't have to be at the very start of the name.
    assert sorted(["file9.pdf", "file10.pdf", "file2.pdf"], key=natural_sort_key) == [
        "file2.pdf",
        "file9.pdf",
        "file10.pdf",
    ]


def test_mixed_digit_positions_never_raise_type_error() -> None:
    # Some names start with digits, some have none, some have digits only
    # in the middle/end - natural_sort_key()'s docstring explains why this
    # can never compare a str against an int mid-sort.
    names = ["176 ChinaAMC.pdf", "no-digits-here.pdf", "trailing123.pdf", "42.pdf"]
    sorted(names, key=natural_sort_key)  # must not raise


def test_multi_digit_runs_within_one_name_are_each_compared_numerically() -> None:
    assert sorted(["a2b10.pdf", "a2b9.pdf", "a10b1.pdf"], key=natural_sort_key) == [
        "a2b9.pdf",
        "a2b10.pdf",
        "a10b1.pdf",
    ]
