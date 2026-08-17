"""Regression coverage for the "Glyphen-Verlust + Font-Erhalt" item
tracked as open in RoadMap.md Phase 2/PDF (the user explicitly asked for
these two to be investigated together - see Backlog.md - as one
architecture question: Helvetica-substitute font vs. preserving the
original document font).

Two separate findings came out of that investigation:

1. Font-Erhalt (confirmed, NOT fixed - architecture-level, out of scope
   for a surgical fix): PyMuPdfEngine never uses the original document's
   actual font for translated text. TextBlock.font_name is captured by
   extract_blocks() but never read anywhere in this module (grep confirms
   zero other references) - insertion always uses either the fixed
   Base-14 Helvetica variants (_FONT_VARIANTS, plain-text path) or CSS
   `font-family: sans-serif` (HTML/Story path), regardless of what font
   the original text actually used. This is a real, confirmed visual-
   fidelity gap for documents using a distinctive font (serif headings,
   a corporate brand font, etc.), but fixing it would mean either
   extracting and re-embedding the original font's program (non-trivial:
   licensing/subsetting/embedding complexity) or a font-matching
   heuristic - a project-level decision, not something to bolt on here.
   No test enforces a specific font is used; this paragraph is the
   documentation of the gap.

2. Glyphen-Verlust (confirmed AND fixed - this file's actual regression
   coverage): the plain-text path (_insert_plain_text(), reachable
   whenever block.spans is empty - "backward compatibility" per
   insert_text()'s docstring, not currently reachable via translate_pdf()
   since real blocks always populate spans, but was silently unsafe if it
   ever were) used a Base-14 Helvetica variant fixed to WinAnsiEncoding.
   Reproduced directly: inserting Cyrillic/Greek/CJK text through it
   silently replaced every non-Latin-1 character with "?" - real data
   loss, not just a font mismatch - while insert_text() still returned
   True (no error signal at all). The HTML/Story path (used whenever
   block.spans is non-empty) was checked side by side and round-trips
   the exact same text correctly, confirmed via MuPDF's automatic
   Unicode font fallback. Fixed by routing plain-text insertions through
   the HTML/Story path whenever the text contains a character outside
   WinAnsiEncoding (see _plain_text_needs_unicode_fallback()/
   _plain_text_to_html() in pipeline/pdf/pymupdf_engine.py) instead of
   silently corrupting via insert_textbox().
"""
from __future__ import annotations

from pathlib import Path

import fitz

from pipeline.pdf.base import TextBlock
from pipeline.pdf.pymupdf_engine import (
    PyMuPdfEngine,
    _plain_text_needs_unicode_fallback,
    _plain_text_to_html,
)

_NON_LATIN_TEXT = "Привет мир Ελληνικά 日本語"
_LATIN1_TEXT = "café Übung naïve"


def _build_source(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 90), "placeholder", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_unicode_fallback_detection() -> None:
    assert _plain_text_needs_unicode_fallback(_NON_LATIN_TEXT) is True
    assert _plain_text_needs_unicode_fallback(_LATIN1_TEXT) is False
    assert _plain_text_needs_unicode_fallback("plain ascii only") is False


def test_plain_text_to_html_escapes_and_wraps_paragraphs() -> None:
    html = _plain_text_to_html("First <line>\nSecond line\n\nSecond paragraph & more")
    assert html == "<p>First &lt;line&gt; Second line</p><p>Second paragraph &amp; more</p>"


def test_non_latin_text_no_longer_corrupted_by_plain_insertion_path(tmp_path: Path) -> None:
    """The actual bug: before the fix, this exact sequence produced
    literal "?" characters in the saved PDF.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = TextBlock(
        page_index=0, bbox=(50, 50, 350, 90), text="placeholder",
        font_name="helv", font_size=11, color=(0, 0, 0), bold=False, italic=False,
        # spans left empty deliberately -> exercises the backward-
        # compatibility plain-text path this fix guards.
    )
    engine.redact_block(block)
    fit = engine.insert_text(block, _NON_LATIN_TEXT, block.font_size)
    assert fit is True  # HTML/Story path fits this short text without growth/shrink
    engine.save(str(output))

    result = fitz.open(str(output))
    extracted = result[0].get_text()
    assert "Привет" in extracted
    assert "Ελληνικά" in extracted
    assert "日本語" in extracted
    assert "?" not in extracted
    result.close()


def test_pure_latin_text_still_uses_the_plain_insertion_path(tmp_path: Path) -> None:
    """Side-by-side control: ordinary Latin/Latin-1 text (the vast
    majority of real usage of this backward-compat path) is unaffected -
    still goes through insert_textbox(), not the HTML fallback.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = TextBlock(
        page_index=0, bbox=(50, 50, 350, 90), text="placeholder",
        font_name="helv", font_size=11, color=(0, 0, 0), bold=False, italic=False,
    )
    engine.redact_block(block)
    fit = engine.insert_text(block, "Ganz normaler deutscher Text mit Umlauten: " + _LATIN1_TEXT, block.font_size)
    assert fit is True
    engine.save(str(output))

    result = fitz.open(str(output))
    extracted = result[0].get_text()
    assert "café" in extracted
    assert "Übung" in extracted
    assert "naïve" in extracted
    result.close()
