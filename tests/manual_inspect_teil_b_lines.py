"""Diagnostic script: inspect part B's raw lines and spans_to_html() output.

For 1526 Virelicon.pdf page 0, part B (the anchor-split block starting with
"The Virelicon Prism"): prints its raw PyMuPDF lines (bbox + blank/
space-only status), whether its first line is a leading blank line and
whether that survives into spans_to_html()'s output, and the full HTML that
spans_to_html() builds for it - to find out whether the visible offset
(translated text sitting too high, overlapping the y=259 line) is caused by
a leading blank line getting lost when the HTML is built. Diagnosis only,
no fix, no pipeline/ changes. Not a pytest test - run manually:

    python tests/manual_inspect_teil_b_lines.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import (
    FIRST_PAGE_ANCHOR_TERMS,
    PyMuPdfEngine,
    _COLUMN_SPLIT_THRESHOLD,
    _build_text_spans,
    _group_lines_by_x0,
    _line_text,
    _split_first_page_metadata,
    spans_to_html,
)

PDF_PATH = Path(__file__).resolve().parent.parent / "1526 Virelicon.pdf"
PAGE_INDEX = 0


def find_part_b_group(page) -> list[dict] | None:
    """Replicate extract_blocks()'s line-grouping + anchor split to recover
    the raw line dicts for part B (the block starting with "The Virelicon
    Prism"), before they are turned into a TextBlock.
    """
    raw = page.get_text("dict")
    for raw_block in raw.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        lines = raw_block.get("lines", [])
        if not lines:
            continue
        for group in _group_lines_by_x0(lines, _COLUMN_SPLIT_THRESHOLD):
            subgroups = _split_first_page_metadata(group, FIRST_PAGE_ANCHOR_TERMS)
            if len(subgroups) != 2:
                continue
            _, rest_part = subgroups
            text = "\n".join(_line_text(line.get("spans", [])) for line in rest_part)
            if "Virelicon Prism" in text:
                return rest_part
    return None


def main() -> None:
    engine = PyMuPdfEngine()  # no template: raw extraction only
    engine.open(str(PDF_PATH))
    page_obj = engine._doc[PAGE_INDEX]

    group = find_part_b_group(page_obj)
    if group is None:
        print("part B raw line group not found")
        return

    print(f"--- part B raw lines ({len(group)} lines) ---")
    for i, line in enumerate(group):
        bbox = tuple(round(v, 1) for v in line["bbox"])
        text = _line_text(line.get("spans", []))
        is_blank = not text.strip()
        print(f"[{i}] bbox={bbox} | blank={is_blank} | text={text!r}")
    print()

    first_line = group[0]
    first_blank = not _line_text(first_line.get("spans", [])).strip()
    first_bbox = tuple(round(v, 1) for v in first_line["bbox"])
    print(f"--- first line of part B ---")
    print(f"blank={first_blank} | bbox={first_bbox}")
    print()

    text_spans = _build_text_spans(group)
    html = spans_to_html(text_spans)

    print("--- text_spans built from part B's raw lines (first 3 shown) ---")
    for span in text_spans[:3]:
        print(f"  text={span.text!r} bold={span.bold} italic={span.italic}")
    print()

    print("--- spans_to_html() output for part B (complete) ---")
    print(html)

    if first_blank:
        print()
        first_span_text = text_spans[0].text if text_spans else None
        print(f"leading blank line's fate: first TextSpan is {first_span_text!r}")
        print(
            "(if this is the heading text itself, not a marker, the leading "
            "blank line was dropped before/during _build_text_spans() and "
            "never reaches spans_to_html() as a <br/> or empty leading <p>)"
        )


if __name__ == "__main__":
    main()
