"""Diagnostic script: print full text of blocks mentioning the address line.

For page 0 of a given PDF, finds every unfiltered extract_blocks() block
whose text contains "Issuer Address" or "Asset Matrix" and prints its full
text (not truncated) - to see whether the following account/address line
(e.g. a long Stellar address) is part of the same block or extracted as its
own separate block. Diagnosis only, no fix, no pipeline/ changes. Not a
pytest test - run manually:

    python tests/manual_inspect_address_block.py path/to/file.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

PAGE_INDEX = 0
SEARCH_TERMS = ("Issuer Address", "Asset Matrix")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_inspect_address_block.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    engine = PyMuPdfEngine()  # no template: unfiltered extract_blocks()
    engine.open(pdf_path)

    blocks = engine.extract_blocks(PAGE_INDEX)
    matches = [
        block for block in blocks if any(term in block.text for term in SEARCH_TERMS)
    ]

    print(f"=== {Path(pdf_path).name} | page {PAGE_INDEX} | {len(matches)} matching block(s) ===")
    for block in matches:
        bbox = tuple(round(v, 1) for v in block.bbox)
        print(f"\n--- bbox={bbox} ---")
        print(block.text)


if __name__ == "__main__":
    main()
