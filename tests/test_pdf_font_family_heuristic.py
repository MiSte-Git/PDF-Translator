"""Regression coverage for the "Einbettung beziehungsweise Wiederverwendung
von Originalfonts bewerten" item tracked as open in RoadMap.md Phase 2/PDF.

Full font embedding (extracting and re-embedding the original document's
actual font program - subsetting, bold/italic-variant matching, licensing
considerations) remains an explicitly deferred, larger architecture
question - not attempted here, see Backlog.md. What this file covers
instead is the small, contained improvement that was agreed on for now:
insert_htmlbox()'s CSS previously used the hardcoded generic font-family
"sans-serif" for EVERY block, regardless of the original document's font
(TextBlock.font_name was captured by extract_blocks() but never read
anywhere in this module - confirmed by grep before this fix). A document
whose body or heading text used a serif font (Times, Georgia, Garamond,
...) or a monospace font (Courier, Consolas, ...) therefore always came
out in a generic sans-serif look, a visible fidelity gap for anything
other than an already-sans-serif original.

Fix: _resolve_css_font_family() (pipeline/pdf/pymupdf_engine.py) maps
block.font_name to one of PyMuPDF's built-in CSS generic families -
"serif", "monospace", or the unchanged "sans-serif" default - via a
small, fixed keyword list of common real-world font names. This is a
coarse family match, not real font reproduction: an unrecognized font
name (including symbol/icon fonts like "Wingdings", which aren't a
prose typeface at all) still safely falls back to sans-serif, same as
before this heuristic existed. _insert_html_css() now takes this
resolved family instead of always hardcoding "sans-serif".

Confirmed by direct reproduction (not asserted here, since the exact
backing font PyMuPDF's Story engine picks for each generic family is an
internal implementation detail that could change): "serif" renders as
"CharisSIL", "monospace" as "NimbusMonoPS-Regular", "sans-serif" (the
unrecognized-name / default case) as "NimbusSans-Regular" - three
genuinely different fonts in this environment, i.e. the CSS
font-family really does change what gets drawn, not just what's
requested. What IS asserted below, robust to that font ever changing:
the *resolved CSS family keyword* PyMuPdfEngine actually requests for a
given block.font_name, and that a serif-named block's font is not the
same PyMuPDF-resolved font as a same-page sans-serif/default block's -
i.e. the two visibly differ, without hardcoding which exact font name
either one resolves to.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, _resolve_css_font_family


def _build_source(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 90), "placeholder", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_resolve_css_font_family_serif_names() -> None:
    for name in ["TimesNewRomanPSMT", "Georgia-Bold", "Garamond", "Cambria-Italic", "Book Antiqua"]:
        assert _resolve_css_font_family(name) == "serif", name


def test_resolve_css_font_family_monospace_names() -> None:
    for name in ["CourierNewPSMT", "Consolas", "Menlo-Regular", "Lucida Console"]:
        assert _resolve_css_font_family(name) == "monospace", name


def test_resolve_css_font_family_defaults_to_sans_serif() -> None:
    # Known sans-serif names, and - just as importantly - anything
    # unrecognized (including a symbol font, which isn't a prose typeface
    # at all): both must land on the same safe default as before this
    # heuristic existed.
    for name in ["ArialMT", "Arial-BoldMT", "Calibri", "Verdana", "Wingdings", "SomeRandomCustomFont"]:
        assert _resolve_css_font_family(name) == "sans-serif", name


def test_serif_block_renders_in_a_visibly_different_font_than_default(tmp_path: Path) -> None:
    """End-to-end: two otherwise-identical blocks, one flagged as a serif
    original font and one left as the (unrecognized-name) default, must
    come out of the real insert_htmlbox() pipeline using two DIFFERENT
    actual fonts - proof the resolved CSS family isn't just computed and
    discarded, but actually reaches page.insert_htmlbox().
    """
    serif_source = tmp_path / "serif_source.pdf"
    default_source = tmp_path / "default_source.pdf"
    _build_source(serif_source)
    _build_source(default_source)

    serif_engine = PyMuPdfEngine()
    serif_engine.open(str(serif_source))
    serif_block = serif_engine.extract_blocks(0)[0]
    serif_block.font_name = "TimesNewRomanPSMT"
    serif_engine.redact_block(serif_block)
    serif_engine.insert_text(serif_block, "", serif_block.font_size, translated_html="<p>Serif test text</p>")
    serif_output = tmp_path / "serif_output.pdf"
    serif_engine.save(str(serif_output))

    default_engine = PyMuPdfEngine()
    default_engine.open(str(default_source))
    default_block = default_engine.extract_blocks(0)[0]
    assert _resolve_css_font_family(default_block.font_name) == "sans-serif"
    default_engine.redact_block(default_block)
    default_engine.insert_text(
        default_block, "", default_block.font_size, translated_html="<p>Serif test text</p>"
    )
    default_output = tmp_path / "default_output.pdf"
    default_engine.save(str(default_output))

    def rendered_font(path: Path) -> str:
        doc = fitz.open(str(path))
        raw = doc[0].get_text("dict")
        for b in raw["blocks"]:
            if b.get("type") == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            font = span["font"]
                            doc.close()
                            return font
        doc.close()
        raise AssertionError("no rendered text span found")

    serif_font = rendered_font(serif_output)
    default_font = rendered_font(default_output)
    assert serif_font != default_font
