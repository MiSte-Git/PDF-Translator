"""Covers pipeline/date_extract.py - the date-range/exact-date search
filter added 02.09.2026 (Michael: "Können wir noch eine nach
Datumsbereich, von, bis, exakt einbauen."). See that module's docstring
for the confirmed design (AskUserQuestion, 02.09.2026): a Von/Bis range
(an "exact" search is just start==end), one source per search (file date
vs. a date found in the document text), and individually selectable
recognized text formats (default ISO only).
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

from pipeline.date_extract import (
    DateRange,
    DateSearchFilter,
    FORMAT_DE,
    FORMAT_EN_MONTH,
    FORMAT_ISO,
    FORMAT_SLASH,
    SOURCE_DOCUMENT,
    compile_custom_date_pattern,
    find_custom_format_dates,
    find_dates,
    matches_document_date,
    matches_file_date,
)


def test_date_range_contains_is_inclusive_on_both_bounds() -> None:
    date_range = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
    assert date_range.contains(date(2026, 1, 1)) is True
    assert date_range.contains(date(2026, 12, 31)) is True
    assert date_range.contains(date(2026, 6, 15)) is True
    assert date_range.contains(date(2025, 12, 31)) is False
    assert date_range.contains(date(2027, 1, 1)) is False


def test_date_range_open_ended_bounds() -> None:
    only_from = DateRange(start=date(2026, 6, 1))
    assert only_from.contains(date(2026, 6, 1)) is True
    assert only_from.contains(date(2026, 5, 31)) is False
    assert only_from.contains(date(2099, 1, 1)) is True

    only_to = DateRange(end=date(2026, 6, 1))
    assert only_to.contains(date(2026, 6, 1)) is True
    assert only_to.contains(date(2026, 6, 2)) is False
    assert only_to.contains(date(1900, 1, 1)) is True


def test_exact_date_is_expressed_as_equal_start_and_end() -> None:
    exact = DateRange(start=date(2026, 9, 1), end=date(2026, 9, 1))
    assert exact.contains(date(2026, 9, 1)) is True
    assert exact.contains(date(2026, 9, 2)) is False
    assert exact.contains(date(2026, 8, 31)) is False


def test_unbounded_range_matches_everything() -> None:
    unbounded = DateRange()
    assert unbounded.is_unbounded is True
    assert unbounded.contains(date(1, 1, 1)) is True
    assert unbounded.contains(date(9999, 12, 31)) is True
    assert DateRange(start=date(2026, 1, 1)).is_unbounded is False


def test_find_iso_dates() -> None:
    assert find_dates("Ausstellungsdatum: 2026-09-01.", {FORMAT_ISO}) == [date(2026, 9, 1)]
    assert find_dates("No date here.", {FORMAT_ISO}) == []
    assert find_dates("Invalid: 2026-13-40.", {FORMAT_ISO}) == []  # month 13, day 40 - never crashes


def test_find_de_dates_including_two_digit_year() -> None:
    assert find_dates("Datum: 01.09.2026", {FORMAT_DE}) == [date(2026, 9, 1)]
    assert find_dates("Datum: 1.9.26", {FORMAT_DE}) == [date(2026, 9, 1)]


def test_find_slash_dates_resolves_day_before_month_when_ambiguous() -> None:
    # "01/09/2026" could be DD/MM or MM/DD - resolved as DD/MM/YYYY (see
    # _resolve_slash_date()'s docstring), matching the DE dot convention.
    assert find_dates("01/09/2026", {FORMAT_SLASH}) == [date(2026, 9, 1)]


def test_find_slash_dates_falls_back_to_month_day_when_day_before_month_is_invalid() -> None:
    # "13/01/2026" can only be DD=13/MM=01 - not a valid DD/MM/YYYY reading
    # in the other direction, so MM/DD/YYYY isn't even needed here; this
    # exercises the actual fallback: "01/13/2026" is invalid as DD=01/MM=13,
    # so it resolves to MM=01/DD=13.
    assert find_dates("01/13/2026", {FORMAT_SLASH}) == [date(2026, 1, 13)]


def test_find_en_month_dates_both_orderings() -> None:
    assert find_dates("Issued: September 1, 2026", {FORMAT_EN_MONTH}) == [date(2026, 9, 1)]
    assert find_dates("Issued: 1 September 2026", {FORMAT_EN_MONTH}) == [date(2026, 9, 1)]
    assert find_dates("Issued: September 1 2026", {FORMAT_EN_MONTH}) == [date(2026, 9, 1)]  # no comma


def test_find_en_month_dates_matches_michaels_own_example() -> None:
    # 02.09.2026 (Michael: "Bei der Datumsuche müssten noch das Format
    # 'September 4, 2026' als Auswahl dabei sein [...]") - already worked
    # before that change (see ui/i18n_data.py's comment on
    # merge_search.date_format_en_month for what actually changed: only
    # the checkbox's LABEL, not this matching logic).
    assert find_dates("September 4, 2026", {FORMAT_EN_MONTH}) == [date(2026, 9, 4)]


def test_find_dates_only_uses_selected_formats() -> None:
    text = "ISO: 2026-09-01, DE: 02.09.2026"
    assert find_dates(text, {FORMAT_ISO}) == [date(2026, 9, 1)]
    assert find_dates(text, {FORMAT_DE}) == [date(2026, 9, 2)]
    assert set(find_dates(text, {FORMAT_ISO, FORMAT_DE})) == {date(2026, 9, 1), date(2026, 9, 2)}


def test_matches_document_date_true_if_any_found_date_is_in_range() -> None:
    date_range = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
    text = "Some unrelated text. Ausstellungsdatum: 2026-09-01."
    assert matches_document_date(text, {FORMAT_ISO}, date_range) is True

    out_of_range = DateRange(start=date(2020, 1, 1), end=date(2020, 12, 31))
    assert matches_document_date(text, {FORMAT_ISO}, out_of_range) is False


def test_matches_document_date_none_text_never_matches() -> None:
    assert matches_document_date(None, {FORMAT_ISO}, DateRange()) is False


def test_matches_document_date_no_recognized_date_never_matches() -> None:
    assert matches_document_date("No date in here at all.", {FORMAT_ISO}, DateRange()) is False


def test_matches_file_date_uses_the_files_modification_date(tmp_path: Path) -> None:
    target = tmp_path / "report.pdf"
    target.write_bytes(b"stub")
    mtime = time.mktime(date(2026, 6, 15).timetuple())
    os.utime(target, (mtime, mtime))

    assert matches_file_date(target, DateRange(start=date(2026, 6, 1), end=date(2026, 6, 30))) is True
    assert matches_file_date(target, DateRange(start=date(2026, 7, 1))) is False


# --- custom (free-text) date format (02.09.2026) --------------------------
# Michael: "Bei der Datumsuche müssten noch das Format 'September 4, 2026'
# als Auswahl dabei sein, Plus Freitext Eintrag. Also 'MMMM D, YYYY' und
# 'MMMM DD, YYYY'. Und für den Freitext sollten eben alle gültigen
# Formate eingebar sein, mit Beispielen."


def test_custom_pattern_matches_michaels_own_two_examples() -> None:
    assert find_custom_format_dates("Filed September 4, 2026.", "MMMM D, YYYY") == [date(2026, 9, 4)]
    assert find_custom_format_dates("Filed September 04, 2026.", "MMMM DD, YYYY") == [date(2026, 9, 4)]


def test_custom_pattern_d_token_also_matches_a_zero_padded_day() -> None:
    # \d{1,2} doesn't care about padding either way - D is the more
    # permissive of the two, not the stricter one.
    assert find_custom_format_dates("September 04, 2026", "MMMM D, YYYY") == [date(2026, 9, 4)]


def test_custom_pattern_dd_token_requires_two_digits() -> None:
    assert find_custom_format_dates("September 4, 2026", "MMMM DD, YYYY") == []


def test_custom_pattern_supports_abbreviated_month_and_two_digit_year() -> None:
    assert find_custom_format_dates("Filed Sep 4, 26.", "MMM D, YY") == [date(2026, 9, 4)]


def test_custom_pattern_supports_numeric_month_orderings() -> None:
    assert find_custom_format_dates("2026/09/04", "YYYY/MM/DD") == [date(2026, 9, 4)]
    assert find_custom_format_dates("04-09-2026", "DD-MM-YYYY") == [date(2026, 9, 4)]


def test_custom_pattern_literal_characters_are_matched_literally() -> None:
    # "2026-09-04" (dashes) must NOT match a pattern that expects slashes.
    assert find_custom_format_dates("2026-09-04", "YYYY/MM/DD") == []


def test_custom_pattern_is_case_insensitive_for_month_names() -> None:
    assert find_custom_format_dates("september 4, 2026", "MMMM D, YYYY") == [date(2026, 9, 4)]


def test_compile_custom_date_pattern_rejects_empty_or_no_tokens() -> None:
    assert compile_custom_date_pattern("") is None
    assert compile_custom_date_pattern("no placeholders here") is None


def test_compile_custom_date_pattern_rejects_a_repeated_field_kind() -> None:
    # A real date has exactly one year/month/day - "YYYY...YYYY" or mixing
    # MM with M for the SAME field can never represent one real date.
    assert compile_custom_date_pattern("YYYY-YYYY") is None
    assert compile_custom_date_pattern("MM/M") is None
    assert compile_custom_date_pattern("DD.D") is None


def test_compile_custom_date_pattern_accepts_a_pattern_missing_a_field() -> None:
    # Missing a token isn't itself invalid (still compiles) - it simply
    # never matches a real date, see the next test.
    assert compile_custom_date_pattern("MMMM YYYY") is not None


def test_find_custom_format_dates_never_matches_with_a_missing_field() -> None:
    assert find_custom_format_dates("September 2026", "MMMM YYYY") == []


def test_find_custom_format_dates_returns_empty_for_an_invalid_pattern_rather_than_raising() -> None:
    assert find_custom_format_dates("anything", "") == []
    assert find_custom_format_dates("anything", "YYYY-YYYY") == []


def test_find_dates_includes_custom_format_alongside_presets() -> None:
    text = "ISO: 2026-01-15. Custom: September 4, 2026."
    found = find_dates(text, {FORMAT_ISO}, custom_format="MMMM D, YYYY")
    assert set(found) == {date(2026, 1, 15), date(2026, 9, 4)}

    # Presets alone (no custom_format) still work unchanged.
    assert find_dates(text, {FORMAT_ISO}) == [date(2026, 1, 15)]


def test_matches_document_date_uses_custom_format_too() -> None:
    date_range = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
    text = "Filed: September 4, 2026."
    assert matches_document_date(text, set(), date_range, custom_format="MMMM D, YYYY") is True
    assert matches_document_date(text, set(), date_range) is False  # no format at all selected


def test_date_search_filter_custom_format_defaults_to_none() -> None:
    filter_ = DateSearchFilter(source=SOURCE_DOCUMENT, date_range=DateRange())
    assert filter_.custom_format is None
