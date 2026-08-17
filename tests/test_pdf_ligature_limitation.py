"""Documents a confirmed, NOT-fixed limitation found while investigating
two open RoadMap.md Phase 2/PDF items together (they turned out to share
one root cause): "Durchsuchbarkeit/Copy-Paste-Qualität" and the "fi-
Ligatur bei Textsuche/Copy-Paste" item specifically.

Reproduced directly (not just read about): whenever PyMuPdfEngine.
insert_text() takes the HTML path (page.insert_htmlbox(), used whenever
block.spans is non-empty - i.e. essentially every real block, since
extract_blocks() always populates spans - see insert_text()'s docstring),
MuPDF's Story/text-shaping engine silently applies the OpenType "liga"
font feature and substitutes common letter sequences with a single
ligature glyph: "office"->"oﬃce" (U+FB03 ffi), "fine"/"film"/"first"->
"ﬁne"/"ﬁlm"/"ﬁrst" (U+FB01 fi), "fluffy"->"ﬂuﬀy" (U+FB02 fl + U+FB00 ff).
page.get_text()/search_for() then operate on that literal ligature
codepoint, not on the original letters - so search_for("office") or
search_for("film") on the OUTPUT PDF returns no hits even though the word
is right there, and a human copy-pasting the text gets the same wrong
codepoints. The plain-text fallback path (insert_textbox(), used only
when block.spans is empty) was checked side by side and does NOT exhibit
this - confirming the Story/HTML engine specifically is what introduces
it, not PyMuPDF/redaction/insertion in general.

What was tried and did NOT fix it (each reproduced directly against this
PyMuPDF/MuPDF version, not assumed from docs):
  - CSS `font-variant-ligatures: none;` on the body/paragraph - ignored.
  - CSS `font-feature-settings: "liga" 0, "clig" 0, "dlig" 0;` - ignored.
  - Switching font-family away from "sans-serif" to explicit "Helvetica"/
    "Arial"/"Times" - still ligates (only "monospace" avoids it, which
    isn't usable for real body text formatting).
  - Inserting U+200C (ZWNJ) between ligature-prone letter pairs to block
    shaping - it DOES stop the ligature substitution, but the Base-14
    font has no zero-width glyph for it in this Story rendering path, so
    it renders as a visible gap/space in the word ("of‌fice" ->
    visibly "of f ice"), corrupting the visual output - not an acceptable
    trade for searchability.

No further options were explored: fixing this properly would mean either
patching each ligature glyph's ToUnicode CMap entry after the fact via
low-level PDF object surgery (invasive, MuPDF-version-fragile, not
attempted here) or replacing the whole HTML/Story insertion path with a
manual per-span insert_textbox() implementation (a substantial rewrite of
the current formatting-preservation approach, and its own project-level
decision - see Backlog.md/RoadMap.md for how this is tracked going
forward). This file exists to lock in the CURRENT, confirmed-still-
present behavior as an executable regression: if a future MuPDF/PyMuPDF
upgrade changes it (fixes the CSS control, or starts including correct
ToUnicode fallbacks), these tests will fail and should be revisited
rather than silently left stale.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from pipeline.pdf.base import TextBlock, TextSpan
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine

_LIGATURE_PRONE_TEXT = "office fine film fluffy first"


def _build_source(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 90), "placeholder", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_html_insertion_path_introduces_ligature_substitution(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = TextBlock(
        page_index=0, bbox=(50, 50, 350, 90), text="placeholder",
        font_name="helv", font_size=11, color=(0, 0, 0), bold=False, italic=False,
        spans=[TextSpan(text="placeholder", font_name="helv", font_size=11, color=(0, 0, 0),
                         bold=False, italic=False, underline=False)],  # non-empty -> HTML path
    )
    engine.redact_block(block)
    engine.insert_text(block, "", block.font_size, translated_html=f"<p>{_LIGATURE_PRONE_TEXT}</p>")
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]
    extracted = page.get_text()

    # The known-bad, currently-unavoidable substitution: plain letters
    # replaced by single ligature codepoints.
    assert "oﬃce" in extracted  # "office" -> U+FB03
    assert "ﬁne" in extracted   # "fine" -> U+FB01
    assert "office" not in extracted
    assert "film" not in extracted

    # The practical consequence this whole investigation was about:
    # searching for the plain word a user would actually type fails.
    assert page.search_for("office") == []
    assert page.search_for("film") == []
    result.close()


def test_plain_text_insertion_path_does_not_ligate(tmp_path: Path) -> None:
    """Side-by-side control: the plain insert_textbox() fallback (only
    used when block.spans is empty) is unaffected - confirms the Story/
    HTML engine specifically is the source of the substitution, not
    PyMuPDF or the redact/insert pipeline in general.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = TextBlock(
        page_index=0, bbox=(50, 50, 350, 90), text="placeholder",
        font_name="helv", font_size=11, color=(0, 0, 0), bold=False, italic=False,
        # spans left empty deliberately -> _insert_plain_text() path
    )
    engine.redact_block(block)
    engine.insert_text(block, _LIGATURE_PRONE_TEXT, block.font_size)
    engine.save(str(output))

    result = fitz.open(str(output))
    page = result[0]
    extracted = page.get_text()

    assert "office" in extracted
    assert "film" in extracted
    assert "oﬃce" not in extracted
    assert page.search_for("office") != []
    assert page.search_for("film") != []
    result.close()
