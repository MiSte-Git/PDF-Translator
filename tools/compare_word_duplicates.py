"""Side-by-side HTML comparison of the .docx candidates in an
UnresolvedDuplicateError group (pipeline/word/source_selection.py) - a pure
read/review tool for the human decision, no auto-resolve and no change to
source_selection.py. One HTML report per group: a metadata header (reusing
pipeline/word/duplicate_analysis.py's CandidateInfo fields, so the two
tools never disagree about what "developer"/"domain"/"date" mean) plus a
classic difflib.HtmlDiff() side-by-side text diff.

For a 2-candidate group this is one diff. For a group with more than 2
candidates (e.g. 1607 CHALICE, 4 candidates) it's one diff per pairwise
combination, each its own section in the same file - itertools.combinations()
covers every pair, since with >2 candidates it isn't obvious in advance
which pair is most informative.

Not a pytest test - run directly:

    python tools/compare_word_duplicates.py
"""
from __future__ import annotations

import difflib
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.base import BREAK_MARKER
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.duplicate_analysis import CandidateInfo, GroupAnalysis, analyze_candidate_group

# The exact CSS difflib.HtmlDiff() emits via make_file() (copied rather than
# read off the private HtmlDiff._styles attribute, so this doesn't silently
# break on a future stdlib change) - kept so make_table()'s output (used
# here instead of make_file(), to combine several diffs in one page) still
# renders correctly.
_DIFF_CSS = """
table.diff {font-family:Courier; border:medium;}
.diff_header {background-color:#e0e0e0}
td.diff_header {text-align:right}
.diff_next {background-color:#c0c0c0}
.diff_add {background-color:#aaffaa}
.diff_chg {background-color:#ffff77}
.diff_sub {background-color:#ffaaaa}
"""

_PAGE_CSS = """
body { font-family: sans-serif; margin: 2em; color: #111; }
h1 { margin-bottom: 0.2em; }
h2 { margin-top: 2.5em; border-bottom: 2px solid #444; padding-bottom: 0.2em; }
h3 { margin-top: 2em; }
table.meta { border-collapse: collapse; margin: 0.5em 0 1.5em 0; }
table.meta th, table.meta td { border: 1px solid #bbb; padding: 4px 10px; text-align: left; font-size: 0.9em; }
table.meta th { background: #f0f0f0; }
table.meta td.mismatch { background: #ffd6d6; font-weight: bold; }
td.error { background: #ffd6d6; color: #900; }
.toc { background: #f7f7f7; border: 1px solid #ddd; padding: 1em 1.5em; margin-bottom: 2em; }
.toc a { display: block; margin: 0.2em 0; }
.hinweis { color: #555; font-style: italic; }
"""

_METADATA_FIELDS = [
    ("developer_name", "Entwickler"),
    ("domain", "Domain"),
    ("date", "Datum"),
    ("paragraph_count", "Absaetze"),
    ("file_size", "Groesse (Bytes)"),
    ("modified_time", "Geaendert"),
]


def _diff_lines(path: Path) -> list[str]:
    """One line per translatable paragraph in `path`, flattened from its
    WordRuns: an image run becomes the literal placeholder "[BILD]" (so a
    picture-only paragraph doesn't just vanish from the diff), a
    BREAK_MARKER run (a <w:br/> inside the paragraph) becomes " | " (so an
    internal line break is visible instead of silently joining two lines of
    text), everything else is the run's own text.
    """
    engine = DocxEngine()
    engine.open(str(path))
    lines = []
    for paragraph in engine.get_paragraphs():
        if not paragraph.translatable:
            continue
        parts = []
        for run in paragraph.runs:
            if run.is_image:
                parts.append("[BILD]")
            elif run.text == BREAK_MARKER:
                parts.append(" | ")
            else:
                parts.append(run.text)
        text = "".join(parts).strip()
        if text:
            lines.append(text)
    return lines


def _metadata_value(info: CandidateInfo, field: str) -> str:
    if field == "modified_time":
        return info.modified_time.strftime("%Y-%m-%d %H:%M")
    if field == "file_size":
        return f"{info.file_size:,}"
    value = getattr(info, field)
    return "-" if value is None else str(value)


def _metadata_table_html(candidates: list[CandidateInfo]) -> str:
    """Metadata header, one column per candidate - a field whose value
    differs across candidates (developer/domain/date/paragraph_count/
    file_size/modified_time) gets its whole row highlighted, so a mismatch
    like REALOS's differing developer name can't get lost among rows that
    all agree.
    """
    rows = ['<table class="meta">', "<tr><th>Feld</th>"]
    for info in candidates:
        rows.append(f"<th>{_escape(info.path.name)}</th>")
    rows.append("</tr>")

    error_row = any(info.error for info in candidates)
    if error_row:
        rows.append('<tr><th>Fehler</th>')
        for info in candidates:
            cell = f'<td class="error">{_escape(info.error)}</td>' if info.error else "<td>-</td>"
            rows.append(cell)
        rows.append("</tr>")

    for field, label in _METADATA_FIELDS:
        values = [_metadata_value(info, field) if not info.error else "-" for info in candidates]
        mismatch = len({v for v in values}) > 1
        css_class = ' class="mismatch"' if mismatch else ""
        rows.append(f"<tr><th>{label}</th>")
        for value in values:
            rows.append(f"<td{css_class}>{_escape(value)}</td>")
        rows.append("</tr>")

    rows.append("</table>")
    return "\n".join(rows)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pairwise_diff_html(name_i: str, lines_i: list[str], name_j: str, lines_j: list[str]) -> str:
    differ = difflib.HtmlDiff(wrapcolumn=80)
    return differ.make_table(
        lines_i, lines_j, name_i, name_j, context=True, numlines=3
    )


def build_group_report(number: str, candidates: list[Path]) -> str:
    analysis = analyze_candidate_group(candidates)
    group_label = " / ".join(p.name for p in candidates)

    lines_by_path = {
        info.path: (_diff_lines(info.path) if not info.error else [])
        for info in analysis.candidates
    }

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>Duplikat-Gruppe {number}</title>",
        f"<style>{_PAGE_CSS}{_DIFF_CSS}</style>",
        "</head><body>",
        f"<h1>Duplikat-Gruppe {number}</h1>",
        f"<p>{_escape(group_label)}</p>",
        "<p class='hinweis'>Reines Lesewerkzeug zur manuellen Entscheidung - "
        "keine automatische Auswahl, keine Aenderung an source_selection.py.</p>",
        _metadata_table_html(analysis.candidates),
    ]

    pairs = list(itertools.combinations(range(len(candidates)), 2))

    if len(pairs) > 1:
        parts.append("<div class='toc'><strong>Paarvergleiche:</strong>")
        for i, j in pairs:
            anchor = f"pair-{i}-{j}"
            ratio = analysis.similarity.get((i, j))
            ratio_text = f"{ratio:.1%}" if ratio is not None else "n/a"
            parts.append(
                f"<a href='#{anchor}'>{_escape(candidates[i].name)} &harr; "
                f"{_escape(candidates[j].name)} ({ratio_text} aehnlich)</a>"
            )
        parts.append("</div>")

    for i, j in pairs:
        anchor = f"pair-{i}-{j}"
        ratio = analysis.similarity.get((i, j))
        ratio_text = f"{ratio:.1%}" if ratio is not None else "n/a (Oeffnungsfehler)"
        parts.append(f"<h2 id='{anchor}'>{_escape(candidates[i].name)} &harr; {_escape(candidates[j].name)}</h2>")
        parts.append(f"<p>Aehnlichkeit (Fliesstext): {ratio_text}</p>")

        lines_i = lines_by_path[candidates[i]]
        lines_j = lines_by_path[candidates[j]]
        if not lines_i or not lines_j:
            parts.append("<p class='hinweis'>Kein Diff moeglich - ein Kandidat konnte nicht geoeffnet werden.</p>")
            continue

        parts.append(_pairwise_diff_html(candidates[i].name, lines_i, candidates[j].name, lines_j))

    parts.append("</body></html>")
    return "\n".join(parts)


def write_group_report(number: str, candidates: list[Path], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    label = "_".join(sorted({p.stem.split(" ", 1)[1] if " " in p.stem else p.stem for p in candidates}))
    safe_label = "".join(c if c.isalnum() or c in "_-" else "_" for c in label)[:60]
    output_path = output_dir / f"{number}_{safe_label}.html"
    output_path.write_text(build_group_report(number, candidates), encoding="utf-8")
    return output_path


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    root = Path(r"G:\.shortcut-targets-by-id\1IGMZBUMVcTHj4z9wsDrSRb6xzdS0klPn\ICO PDFs")
    output_dir = Path(__file__).resolve().parent / "output" / "duplicate_review"

    groups: dict[str, list[Path]] = {
        "1298": [root / "1298 DEA (1).docx", root / "1298 DEA.docx"],
        "1417": [root / "1417 AEONLOOM (1).docx", root / "1417 AEONLOOM.docx"],
        "1458": [root / "1458 REALOS (1).docx", root / "1458 REALOS.docx"],
        "1607": [
            root / "1607 CHALICE (1).docx",
            root / "1607 CHALICE (2).docx",
            root / "1607 CHALICE.docx",
            root / "1607 CHALICE-TERMINARCH2 & 3.docx",
        ],
        "1746": [root / "1746 NOOVIAN Updated Declas.docx", root / "1746 NOOVIAN.docx"],
        "1750": [root / "1750 ANEMNESIS updated.docx", root / "1750 ANEMNESIS.docx"],
        "1772": [root / "1772 SVAULT Follow Up.docx", root / "1772 SVAULT.docx"],
        "985": [root / "985 TheCross (1).docx", root / "985 TheCross.docx"],
    }

    for path_list in groups.values():
        for path in path_list:
            if not path.exists():
                print(f"WARNUNG: Datei nicht gefunden: {path}")

    written = []
    for number, candidates in groups.items():
        output_path = write_group_report(number, candidates, output_dir)
        written.append(output_path)
        print(f"{number}: {output_path}")

    print(f"\n{len(written)} Reports geschrieben nach {output_dir}")


if __name__ == "__main__":
    main()
