"""Coverage for loading protected terms from a file (03.09.2026, Michael:
"Können wir bei den 'geschützten Begriffen' auch noch ein aus Dateien
auslesen hinzufügen? Das man zum Beispiel eine csv laden kann. Nicht nur
von Hand eintragen.").

pipeline.translation.protected_terms.load_protected_terms_file() is the
pure, Qt-free reader; merge_protected_terms() is what the UI uses to append
the loaded list to whatever is already typed into the box.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.translation.protected_terms import load_protected_terms_file, merge_protected_terms


def test_plain_text_one_term_per_line(tmp_path: Path) -> None:
    file = tmp_path / "terms.txt"
    file.write_text("VIRELICON\n\n  Anthropic  \nClaude\n", encoding="utf-8")
    assert load_protected_terms_file(file) == ["VIRELICON", "Anthropic", "Claude"]


def test_semicolon_csv_uses_first_column_and_skips_header(tmp_path: Path) -> None:
    file = tmp_path / "terms.csv"
    file.write_text(
        "Begriff;Kommentar\nVIRELICON;Produktname\nAcme Corp;Kunde\n;leer\n",
        encoding="utf-8",
    )
    assert load_protected_terms_file(file) == ["VIRELICON", "Acme Corp"]


def test_comma_csv_with_quoted_cells(tmp_path: Path) -> None:
    file = tmp_path / "terms.csv"
    file.write_text('term,note\n"Foo, Inc.",company\nBar,\n', encoding="utf-8")
    assert load_protected_terms_file(file) == ["Foo, Inc.", "Bar"]


def test_first_row_is_kept_when_it_is_a_real_term(tmp_path: Path) -> None:
    file = tmp_path / "terms.csv"
    file.write_text("VIRELICON;x\nAcme;y\n", encoding="utf-8")
    assert load_protected_terms_file(file) == ["VIRELICON", "Acme"]


def test_duplicates_are_dropped_case_insensitively_first_spelling_wins(tmp_path: Path) -> None:
    file = tmp_path / "terms.txt"
    file.write_text("Claude\nCLAUDE\nclaude\nAnthropic\n", encoding="utf-8")
    assert load_protected_terms_file(file) == ["Claude", "Anthropic"]


def test_excel_utf8_bom_and_cp1252_fallback(tmp_path: Path) -> None:
    bom_file = tmp_path / "bom.csv"
    bom_file.write_bytes("﻿Müller\nZürich\n".encode("utf-8"))
    assert load_protected_terms_file(bom_file) == ["Müller", "Zürich"]

    legacy_file = tmp_path / "legacy.csv"
    legacy_file.write_bytes("Müller\n".encode("cp1252"))
    assert load_protected_terms_file(legacy_file) == ["Müller"]


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_protected_terms_file(tmp_path / "nope.csv")


def test_merge_appends_only_new_terms_and_keeps_existing_order() -> None:
    merged = merge_protected_terms("Anthropic\nClaude\n", ["claude", "VIRELICON", "Anthropic", "Acme"])
    assert merged == "Anthropic\nClaude\nVIRELICON\nAcme"


def test_merge_into_empty_box() -> None:
    assert merge_protected_terms("", ["A", "B"]) == "A\nB"
    assert merge_protected_terms("A\nB", []) == "A\nB"
