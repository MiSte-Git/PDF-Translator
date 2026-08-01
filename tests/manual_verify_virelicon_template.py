"""Verify templates/virelicon.json against 1526 VIRELICON.pdf.

Loads the template via DocumentTemplate.load_json() and reports every block
extract_blocks() marks non-translatable (header/footer zones, page-0
metadata zone, or link overlaps - see is_zone_excluded() for telling those
apart), so the exclusions can be eyeballed before running
tools/compare_providers.py against this document. Not a pytest test - run
manually:

    python tests/manual_verify_virelicon_template.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from pipeline.pdf.template import DocumentTemplate, block_overlaps, load_json

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = REPO_ROOT / "1526 VIRELICON.pdf"
TEMPLATE_PATH = REPO_ROOT / "templates" / "virelicon.json"


def is_zone_excluded(block: TextBlock, template: DocumentTemplate) -> str | None:
    """Which template zone explains a non-translatable block, if any
    ("header"/"footer"/"first_page_zone") - None means something else
    (e.g. a link-annotation overlap) is responsible instead.
    """
    if template.header_bbox is not None and block_overlaps(block.bbox, template.header_bbox):
        return "header"
    if template.footer_bbox is not None and block_overlaps(block.bbox, template.footer_bbox):
        return "footer"
    if (
        block.page_index == 0
        and template.first_page_zones is not None
        and any(block_overlaps(block.bbox, zone) for zone in template.first_page_zones)
    ):
        return "first_page_zone"
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not PDF_PATH.exists():
        print(f"PDF nicht gefunden: {PDF_PATH}")
        sys.exit(1)
    if not TEMPLATE_PATH.exists():
        print(f"Template nicht gefunden: {TEMPLATE_PATH}")
        sys.exit(1)

    template = load_json(TEMPLATE_PATH)
    print(f"Template geladen: {template}")
    print()

    engine = PyMuPdfEngine(template=template)
    engine.open(str(PDF_PATH))

    total_blocks = 0
    excluded_blocks = 0
    reason_counts: dict[str, int] = {}

    for page in engine.get_pages():
        blocks = sorted(engine.extract_blocks(page.index), key=lambda b: b.bbox[1])
        page_excluded = [b for b in blocks if not b.translatable]
        total_blocks += len(blocks)
        excluded_blocks += len(page_excluded)
        if not page_excluded:
            continue

        print(f"=== Seite {page.index} ({len(page_excluded)} nicht-übersetzbare Block(s)) ===")
        for block in page_excluded:
            reason = is_zone_excluded(block, template) or "sonstiges (z.B. Link-Overlap)"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            bbox = tuple(round(v, 1) for v in block.bbox)
            text = block.text.replace("\n", " | ")
            if len(text) > 80:
                text = text[:80] + "..."
            print(f"  [{reason}] bbox={bbox}")
            print(f"    text={text!r}")
        print()

    print("=== Zusammenfassung ===")
    print(f"Blöcke gesamt: {total_blocks}")
    print(f"Nicht-übersetzbar: {excluded_blocks}")
    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()
