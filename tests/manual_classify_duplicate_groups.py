"""Pre-sort the UnresolvedDuplicateError groups from a full
source_selection scan using pipeline/word/duplicate_analysis.py: per-
candidate metadata (developer/ICO name from the header, domain/date from
the page-1 metadata block, paragraph count, file size/mtime) plus a
pairwise text-similarity score, then a rough heuristic classification.
Nothing is auto-resolved - every group is shown in full for manual
confirmation. Not a pytest test - run manually:

    python tests/manual_classify_duplicate_groups.py "<path to ICO folder>"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.duplicate_analysis import GroupAnalysis, analyze_candidate_group, classify_group
from pipeline.word.source_selection import (
    UnresolvedDuplicateError,
    discover_documents,
    document_ico_name,
    resolve_source_document,
)


def find_unresolved_groups(root: Path) -> list[list[Path]]:
    """Re-run the same discover_documents()/resolve_source_document() scan
    as tests/manual_verify_source_selection.py, returning just the groups
    that raise UnresolvedDuplicateError - re-derived live against the
    current folder contents, not a hardcoded path list.
    """
    groups = discover_documents(root)
    unresolved: list[list[Path]] = []
    for _, candidates in sorted(groups.items()):
        if len(candidates) < 2:
            continue
        name = document_ico_name(candidates[0].name)
        try:
            resolve_source_document(name, candidates)
        except UnresolvedDuplicateError:
            unresolved.append(candidates)
    return unresolved


def print_group_table(analysis: GroupAnalysis) -> None:
    header = (
        f"  {'Datei':<42} {'Entwickler':<20} {'Domain':<18} {'Datum':<15} "
        f"{'Absaetze':>8} {'Groesse':>10} {'Geaendert':<17}"
    )
    print(header)
    for info in analysis.candidates:
        if info.error:
            print(f"  {info.path.name:<42} FEHLER BEIM OEFFNEN: {info.error}")
            continue
        print(
            f"  {info.path.name[:42]:<42} "
            f"{(info.developer_name or '-')[:20]:<20} "
            f"{(info.domain or '-')[:18]:<18} "
            f"{(info.date or '-')[:15]:<15} "
            f"{info.paragraph_count:>8} "
            f"{info.file_size:>10,} "
            f"{info.modified_time.strftime('%Y-%m-%d %H:%M'):<17}"
        )

    print()
    print("  Paarweise Aehnlichkeit (Fliesstext, difflib.SequenceMatcher):")
    count = len(analysis.candidates)
    for i in range(count):
        for j in range(i + 1, count):
            name_i = analysis.candidates[i].path.name
            name_j = analysis.candidates[j].path.name
            ratio = analysis.similarity.get((i, j))
            if ratio is None:
                print(f"    {name_i} <-> {name_j}: n/a (Oeffnungsfehler)")
            else:
                print(f"    {name_i} <-> {name_j}: {ratio:.1%}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print('Usage: python tests/manual_classify_duplicate_groups.py "<path to ICO folder>"')
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Ordner nicht gefunden: {root}")
        sys.exit(1)

    unresolved_groups = find_unresolved_groups(root)
    print(f"{len(unresolved_groups)} unaufgeloeste Gruppen gefunden\n")

    category_counts: dict[str, int] = {}

    for candidates in unresolved_groups:
        numbers = sorted({p.name.split()[0] for p in candidates})
        print(f"=== Nummer(n) {'/'.join(numbers)} ({len(candidates)} Kandidaten) ===")
        analysis = analyze_candidate_group(candidates)
        print_group_table(analysis)
        category = classify_group(analysis)
        category_counts[category] = category_counts.get(category, 0) + 1
        print(f"\n  Einschaetzung: {category}")
        print()

    print("=== Kategorien-Uebersicht ===")
    for category, count in sorted(category_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {category}: {count}")
    print(f"  Gesamt: {sum(category_counts.values())} Gruppen")


if __name__ == "__main__":
    main()
