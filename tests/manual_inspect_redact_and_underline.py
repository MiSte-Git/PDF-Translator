"""Diagnostic script: redaction rect and underline-flag support for part B.

For 1526 Virelicon.pdf page 0, part B (the anchor-split title block):

1. Prints block.bbox vs. block.insert_bbox, confirms which one
   redact_block() actually passes to PyMuPDF (by reading the source and by
   empirically checking whether the y~259 line disappears from
   page.get_drawings() after calling redact_block() on a throwaway copy of
   the document), and whether that rect covers the y~259 line's y-range.
2. Dumps the raw PyMuPDF span dicts for this block (full "flags" field and
   any other keys) to see whether underline is represented at all in the
   raw data, decodes the known flag bits (superscript/italic/serifed/
   monospaced/bold - no underline bit in PyMuPDF's span "flags"), and
   checks whether TextSpan/_build_text_spans() captures anything beyond
   bold/italic.

Diagnosis only, no fix, no pipeline/ changes. Not a pytest test - run
manually:

    python tests/manual_inspect_redact_and_underline.py
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

PDF_PATH = Path(__file__).resolve().parent.parent / "1526 Virelicon.pdf"
PAGE_INDEX = 0

# PyMuPDF's documented span "flags" bitfield (fitz docs: TextPage.extractDICT).
# No underline bit is defined here.
_KNOWN_FLAG_BITS = {
    1 << 0: "superscript",
    1 << 1: "italic",
    1 << 2: "serifed",
    1 << 3: "monospaced",
    1 << 4: "bold",
}


def decode_flags(flags: int) -> str:
    known = [name for bit, name in _KNOWN_FLAG_BITS.items() if flags & bit]
    unknown_bits = flags & ~sum(_KNOWN_FLAG_BITS)
    parts = known or []
    if unknown_bits:
        parts.append(f"unrecognized-bits=0b{unknown_bits:b}")
    return ", ".join(parts) if parts else "(none)"


def main() -> None:
    engine = PyMuPdfEngine()
    engine.open(str(PDF_PATH))

    part_b = next(
        (
            block
            for block in engine.extract_blocks(PAGE_INDEX)
            if block.translatable and "Virelicon Prism" in block.text
        ),
        None,
    )
    if part_b is None:
        print("part B not found")
        return

    # --- 1. Redaction rect ---
    print("=== 1. Redaction rect ===")
    print(f"block.bbox        = {tuple(round(v, 1) for v in part_b.bbox)}")
    print(f"block.insert_bbox = {tuple(round(v, 1) for v in part_b.insert_bbox) if part_b.insert_bbox else None}")

    source = inspect.getsource(PyMuPdfEngine.redact_block)
    used_field = "insert_bbox" if "insert_bbox" in source else "bbox"
    print(f"redact_block() source uses: block.{used_field}")
    print()
    print("redact_block() source:")
    print(source)

    line_y0, line_y1 = 259.0, 259.0  # from tests/manual_inspect_split_position.py
    redacted_rect = part_b.bbox  # what redact_block() actually passes today
    covers_line = redacted_rect[1] <= line_y0 <= redacted_rect[3]
    print(
        f"y~259 line inside redact rect y-range ({redacted_rect[1]:.1f}, {redacted_rect[3]:.1f})? "
        f"{covers_line}"
    )

    # Empirical check: does the line actually vanish from get_drawings()
    # after redact_block()? Uses a throwaway engine/document so the real
    # inspection above is unaffected.
    probe_engine = PyMuPdfEngine()
    probe_engine.open(str(PDF_PATH))
    probe_block = next(
        block
        for block in probe_engine.extract_blocks(PAGE_INDEX)
        if block.translatable and "Virelicon Prism" in block.text
    )
    page_obj = probe_engine._doc[PAGE_INDEX]
    before = [d["rect"] for d in page_obj.get_drawings() if abs(d["rect"].y0 - 259.0) < 1.0]
    probe_engine.redact_block(probe_block)
    page_obj = probe_engine._doc[PAGE_INDEX]  # redactions may invalidate the page ref
    after = [d["rect"] for d in page_obj.get_drawings() if abs(d["rect"].y0 - 259.0) < 1.0]
    print(f"y~259 line(s) before redact_block(): {before}")
    print(f"y~259 line(s) after redact_block():  {after}")
    print()

    # --- 2. Underline support ---
    print("=== 2. Underline support in raw PyMuPDF data ===")
    raw = engine._doc[PAGE_INDEX].get_text("dict")
    printed = 0
    for raw_block in raw.get("blocks", []):
        if raw_block.get("type") != 0:
            continue
        for line in raw_block.get("lines", []):
            for span in line.get("spans", []):
                if "Virelicon Prism" not in span.get("text", ""):
                    continue
                print(f"raw span dict keys: {sorted(span.keys())}")
                print(f"  text={span['text']!r}")
                print(f"  flags={span.get('flags')} -> {decode_flags(span.get('flags', 0))}")
                for key in span:
                    if key not in ("text", "flags", "bbox", "origin", "font", "size", "color"):
                        print(f"  {key}={span[key]!r}")
                printed += 1
    if not printed:
        print("(no matching span found)")
    print()

    print("--- TextSpan / _build_text_spans() capture ---")
    print("TextSpan dataclass fields (pipeline/pdf/base.py): text, font_name, "
          "font_size, color, bold, italic - no underline field.")
    print("_build_text_spans() only reads span['flags'] to compute bold/italic "
          "(_BOLD_FLAG=1<<4, _ITALIC_FLAG=1<<1) - any other flag bit, or any "
          "underline-related key present in the raw span dict, is currently "
          "read nowhere and therefore silently dropped.")


if __name__ == "__main__":
    main()
