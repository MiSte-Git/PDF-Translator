"""Ad-hoc script to inspect the text blocks extracted from a PDF.

Not a pytest test - run manually to eyeball extraction/translatable results:

    python tests/manual_inspect_blocks.py path/to/file.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/manual_inspect_blocks.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    engine = PyMuPdfEngine()  # no template for this first pass
    engine.open(pdf_path)

    for page in engine.get_pages():
        blocks = engine.extract_blocks(page.index)
        for block in blocks:
            bbox = tuple(round(v, 1) for v in block.bbox)
            text = block.text.replace("\n", " ")
            if len(text) > 60:
                text = text[:60] + "..."
            print(
                f"page={block.page_index:>3} | bbox={bbox} | "
                f"translatable={str(block.translatable):<5} | "
                f"font={block.font_name} {block.font_size:.1f} | text=\"{text}\""
            )


if __name__ == "__main__":
    main()
