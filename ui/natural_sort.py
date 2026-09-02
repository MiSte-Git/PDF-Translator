"""Shared "natural sort" key for filenames that start (or contain
sequences) with a number (02.09.2026, Michael: "Die Dateinamen fangen
hier aktuell alle mit Nummern an, dann ein Leerzeichen und dann Text.
Ich dachte das nach Namen sortieren Standardmässig immer erst die
Nummern ausliest, wenn das nicht der Fall ist kommt da eine falsche
Sortierung für die ICOs für mich zustande.").

A plain string/lexicographic sort compares "176 ChinaAMC.pdf" against
"1747 ABSENCE.pdf" character by character, so "176 ..." sorts AFTER
"1747 ..." (the third character '6' > '4') even though 176 < 1747
numerically - exactly the wrong order for this app's ICO-numbered
filenames. natural_sort_key() splits a name into alternating text/digit
runs and compares digit runs as integers instead, matching how a person
reading the numbers (or Windows Explorer's/macOS Finder's own filename
sort) would expect them ordered.

Shared by every "Sortieren nach Name" button in the app:
ui/merge_dialog.py, ui/word_merge_dialog.py (Fortsetzung 12's sort
buttons) and ui/merge_search_dialog.py, ui/word_merge_search_dialog.py
(the search dialogs' own sort buttons, Fortsetzung 15) - all four used
the same naive `path.name.lower()` key before this fix, so all four are
switched to natural_sort_key() together rather than fixing only the one
Michael happened to notice it in.
"""
from __future__ import annotations

import re

_DIGIT_RUN_RE = re.compile(r"(\d+)")


def natural_sort_key(name: str) -> list:
    """Splits `name` into text/digit runs, converting each digit run to
    an int - use as the `key=` for sorting filenames so a leading (or
    embedded) number is compared numerically, not character-by-character.

    re.split() with a capturing group always alternates
    text-run/digit-run/text-run/... starting and ending with a (possibly
    empty) text run, for ANY input - so the resulting key always has a
    str at every even index and an int at every odd index, regardless of
    where in the original name the digits actually are. Two such keys
    therefore only ever compare str-with-str or int-with-int at any given
    index, never str-with-int - list comparison never raises TypeError,
    even between names with digits in different positions or no digits
    at all.
    """
    return [int(chunk) if chunk.isdigit() else chunk.lower() for chunk in _DIGIT_RUN_RE.split(name)]
