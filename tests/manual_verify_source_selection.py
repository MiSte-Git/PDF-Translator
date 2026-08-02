"""Verify pipeline/word/source_selection.py against a real folder of .docx
files:
1. discover_documents() (grouped by document number) +
   resolve_source_document() for all 7 known "(LS)"-duplicate ICOs, plus
   the SILENCE case specifically (1771 SILENCE.docx is an independent,
   unrelated document, not part of the 1868 SILENCE/SILENCE (LS) pair -
   see pipeline/word/source_selection.py's module docstring) and the
   error case for an unlisted ICO.
2. A full scan of the whole folder: how many number-groups have exactly
   1 candidate, how many have >1 and resolve automatically, and how many
   (if any) are genuinely new/unknown conflicts requiring a human look.

Not a pytest test - run manually:

    python tests/manual_verify_source_selection.py "<path to ICO folder>"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.source_selection import (
    LS_PREFERRED_ICOS,
    UnresolvedDuplicateError,
    discover_documents,
    document_ico_name,
    resolve_source_document,
)

KNOWN_DUPLICATE_ICOS_ORDERED = [
    "HARMONICJ",
    "MNEMOSYNE",
    "CONTINUUM",
    "AXIOMCRADLE",
    "WOUNDS",
    "ONEPERCENT",
    "SILENCE",
]


def verify_known_cases(groups: dict[str, list[Path]]) -> bool:
    """Look up each of the 7 known duplicate ICOs by NUMBER (not name -
    groups is keyed by document number now) and check resolution. SILENCE
    is shown by number explicitly: 1868 (the real duplicate pair) and
    1771 (the unrelated document) are two separate groups now.
    """
    all_ok = True

    # number -> expected ICO name, for the 7 known cases (see the real
    # filenames confirmed earlier: e.g. "1854 MNEMOSYNE.docx").
    known_numbers = {
        "1862": "HARMONICJ",
        "1854": "MNEMOSYNE",
        "1834": "CONTINUUM",
        "1822": "AXIOMCRADLE",
        "1440": "WOUNDS",
        "1527": "ONEPERCENT",
        "1868": "SILENCE",  # the real (LS) duplicate pair
    }

    for number, expected_name in known_numbers.items():
        candidates = groups.get(number, [])
        print(f"=== {expected_name} (Nummer {number}) ===")
        print(f"  Kandidaten ({len(candidates)}):")
        for candidate in candidates:
            print(f"    {candidate.name}")

        if not candidates:
            print("  FEHLER: keine Kandidaten gefunden!")
            all_ok = False
            print()
            continue

        name = document_ico_name(candidates[0].name)
        try:
            resolved = resolve_source_document(name, candidates)
        except UnresolvedDuplicateError as exc:
            print(f"  UnresolvedDuplicateError: {exc}")
            all_ok = False
            print()
            continue

        expect_ls = expected_name in LS_PREFERRED_ICOS
        got_ls = "(LS)" in resolved.name.upper()
        ok = got_ls == expect_ls
        all_ok = all_ok and ok
        expected_label = "(LS)" if expect_ls else "Nicht-(LS)"
        print(f"  Gewaehlt: {resolved.name} [{'OK' if ok else 'FEHLER'} - erwartet {expected_label}]")
        print()

    # The independent, unrelated "1771 SILENCE.docx" - must now resolve
    # as its own single-candidate group, no duplicate handling at all.
    print("=== SILENCE, unabhaengiges Dokument (Nummer 1771) ===")
    candidates_1771 = groups.get("1771", [])
    print(f"  Kandidaten ({len(candidates_1771)}):")
    for candidate in candidates_1771:
        print(f"    {candidate.name}")
    if len(candidates_1771) == 1:
        name = document_ico_name(candidates_1771[0].name)
        resolved = resolve_source_document(name, candidates_1771)
        print(f"  Gewaehlt: {resolved.name} [OK - einzelner Kandidat, keine Duplikat-Behandlung]")
    else:
        print(f"  FEHLER: erwartet genau 1 Kandidat, gefunden {len(candidates_1771)}")
        all_ok = False
    print()

    print("=== Fehlerfall: unbekanntes ICO mit 2 Kandidaten (synthetisch) ===")
    fake_candidates = [Path("9999 FAKEICO.docx"), Path("9999 FAKEICO (LS).docx")]
    try:
        resolve_source_document("FAKEICO", fake_candidates)
    except UnresolvedDuplicateError as exc:
        print(f"  UnresolvedDuplicateError wie erwartet ausgeloest: {exc}")
    else:
        print("  FEHLER: kein UnresolvedDuplicateError geworfen!")
        all_ok = False
    print()

    return all_ok


def full_scan(groups: dict[str, list[Path]]) -> None:
    """Run every number-group through resolve_source_document() and
    tally: single-candidate groups (the normal case), multi-candidate
    groups that resolve automatically (the 6 known non-SILENCE pairs +
    1868 SILENCE - SILENCE itself is now a clean pair since 1771 is its
    own group), and multi-candidate groups that DON'T resolve (new,
    previously unknown conflicts - listed in full, not guessed at).
    """
    single = 0
    auto_resolved: list[tuple[str, Path]] = []
    unresolved: list[tuple[str, list[Path]]] = []

    for number, candidates in groups.items():
        if len(candidates) == 1:
            single += 1
            continue
        name = document_ico_name(candidates[0].name)
        try:
            resolved = resolve_source_document(name, candidates)
        except UnresolvedDuplicateError:
            unresolved.append((number, candidates))
        else:
            auto_resolved.append((number, resolved))

    print("=== Vollscan des Ordners ===")
    print(f"Gruppen (Dokumentnummern) gesamt: {len(groups)}")
    print(f"  Gruppen mit genau 1 Kandidat: {single}")
    print(f"  Gruppen mit >1 Kandidat, automatisch aufgeloest: {len(auto_resolved)}")
    for number, resolved in auto_resolved:
        print(f"    {number}: -> {resolved.name}")
    print(f"  Gruppen mit >1 Kandidat, NICHT aufloesbar (UnresolvedDuplicateError): {len(unresolved)}")
    for number, candidates in unresolved:
        print(f"    Nummer {number}:")
        for candidate in candidates:
            print(f"      {candidate}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print('Usage: python tests/manual_verify_source_selection.py "<path to ICO folder>"')
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Ordner nicht gefunden: {root}")
        sys.exit(1)

    groups = discover_documents(root)
    print(f"{len(groups)} Dokumentnummer-Gruppen unter {root} gefunden\n")

    all_ok = verify_known_cases(groups)

    print()
    full_scan(groups)

    print()
    print(f"GESAMTERGEBNIS (bekannte Faelle): {'OK' if all_ok else 'ABWEICHUNGEN GEFUNDEN (siehe oben)'}")


if __name__ == "__main__":
    main()
