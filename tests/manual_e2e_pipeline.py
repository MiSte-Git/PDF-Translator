"""Ad-hoc end-to-end smoke test for the PdfEngine pipeline.

Runs open -> extract_blocks -> redact_block -> insert_text -> save against a
real PDF, using a moderately lengthened placeholder text (no real
translation) that simulates a realistic translation length - many languages
run roughly 20-30% longer than English, unlike an earlier, deliberate x3
extreme stress test of insert_text's fit-shrink/overflow logic. Not a
pytest test - run manually and inspect the output PDF:

    python tests/manual_e2e_pipeline.py path/to/file.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from pipeline.pdf.template import DocumentTemplate, block_overlaps

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "e2e_test_output.pdf"

# Zones for 2182 INDELEGATA.pdf, determined by running extract_blocks() with
# no template on page 0 and page 1 (see tests/manual_diagnose_layout.py) and
# reading off the bbox of the recurring blocks:
#   - header text "Developer: The Korolev Directive  QSI ICO: INDELEGATA" is
#     at the exact same bbox (43.1, 39.5, 257.5, 86.8) on every page 0-5.
#   - footer "<page number>" (x0 drifts 547.0-549.6 with digit count) and
#     "(c)2026 Quantum Stellar Initiative" (42.8, 783.6, 192.8, 794.6) both
#     sit in the y=782.1-794.6 band on every page 0-5.
#   - page 0 only: the "July 14, 2026 ... ICO Telegram Write Up: Post Link"
#     block (42.6, 96.4, 256.7, 142.5) and the "Domain: / Issuer Address:"
#     block (42.6, 144.8, 503.9, 314.3) are the fixed metadata block.
# Zones are padded a few points and widened to the full page width (595.3)
# for robustness, while staying clear of the neighboring body-text blocks
# (header ends 86.8 < 92.0; first_page_zones ends 315.0 < next block's 316.4).
TEMPLATE = DocumentTemplate(
    name="2182 INDELEGATA",
    header_bbox=(0.0, 30.0, 595.3, 92.0),
    footer_bbox=(0.0, 778.0, 595.3, 798.0),
    first_page_zones=[(0.0, 92.0, 595.3, 315.0)],
)


def make_placeholder_text(original: str) -> str:
    """Lengthen the original text by ~25%, simulating a realistic translation
    length (many languages run 20-30% longer than English) rather than the
    earlier x3 extreme overflow stress test.
    """
    extra_len = int(len(original) * 0.25)
    return (original + " " + original[:extra_len]).strip()


def is_zone_excluded(block: TextBlock, template: DocumentTemplate) -> bool:
    """Check whether a block's non-translatable status is explained by the
    template's header/footer/first_page_zones (as opposed to a link overlap).
    """
    if template.header_bbox is not None and block_overlaps(block.bbox, template.header_bbox):
        return True
    if template.footer_bbox is not None and block_overlaps(block.bbox, template.footer_bbox):
        return True
    if (
        block.page_index == 0
        and template.first_page_zones is not None
        and any(block_overlaps(block.bbox, zone) for zone in template.first_page_zones)
    ):
        return True
    return False


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_e2e_pipeline.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    engine = PyMuPdfEngine(template=TEMPLATE)
    engine.open(pdf_path)

    total_blocks = 0
    overflow_blocks = 0

    for page in engine.get_pages():
        zone_excluded_count = 0
        for block in engine.extract_blocks(page.index):
            if not block.translatable:
                if is_zone_excluded(block, TEMPLATE):
                    zone_excluded_count += 1
                continue  # headers/footers/links/first-page zones stay untouched

            engine.redact_block(block)
            placeholder = make_placeholder_text(block.text)
            fit = engine.insert_text(block, placeholder, block.font_size)

            total_blocks += 1
            if not fit:
                overflow_blocks += 1

            bbox = tuple(round(v, 1) for v in block.bbox)
            print(f"page={block.page_index:>3} | bbox={bbox} | fit={str(fit):<5}")

        print(f"page={page.index:>3} | zone-excluded blocks (header/footer/first_page_zones): {zone_excluded_count}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine.save(str(OUTPUT_PATH))

    print()
    print(f"blocks processed: {total_blocks}")
    print(f"overflow cases (fit=False): {overflow_blocks}")
    print(f"output written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
