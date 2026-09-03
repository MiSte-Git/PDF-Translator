"""Covers pipeline/word/html_bridge.py's paragraph_to_html() base_rpr
resolution - specifically the 03.09.2026 follow-up to the font-size fix
(Michael, after re-testing: "Der Font der Übersetzung ist immer noch 1 pt
grösser (12 pt) als das Original mit 11 pt.").

Root cause of the residual mismatch: base_rpr previously took the
paragraph's FIRST non-hyperlink run's source_rpr as "this paragraph's
normal text formatting". A paragraph that happens to START with something
atypical (a short leading run in a different font/size than the rest of
its real content - not unusual in real, hand-edited Word documents) then
poisoned every rebuilt/translated run in that paragraph with the WRONG
font/size, even though the paragraph's actual bulk of text was
consistently something else. Fixed by picking the (font, size) shared by
the MOST runs instead of just the first one - see _dominant_rpr().
"""
from __future__ import annotations

from pipeline.word.base import WordParagraph, WordRun
from pipeline.word.html_bridge import paragraph_to_html
from lxml import etree

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _rpr(ascii_font: str, half_points: str) -> etree._Element:
    rpr = etree.Element(f"{{{_W_NS}}}rPr")
    rfonts = etree.SubElement(rpr, f"{{{_W_NS}}}rFonts")
    rfonts.set(f"{{{_W_NS}}}ascii", ascii_font)
    sz = etree.SubElement(rpr, f"{{{_W_NS}}}sz")
    sz.set(f"{{{_W_NS}}}val", half_points)
    return rpr


def _signature(rpr) -> tuple[str | None, str | None]:
    if rpr is None:
        return (None, None)
    rfonts = rpr.find(f"{{{_W_NS}}}rFonts")
    sz = rpr.find(f"{{{_W_NS}}}sz")
    return (
        rfonts.get(f"{{{_W_NS}}}ascii") if rfonts is not None else None,
        sz.get(f"{{{_W_NS}}}val") if sz is not None else None,
    )


def test_a_leading_atypical_run_does_not_poison_the_whole_paragraphs_formatting() -> None:
    """A paragraph starting with a short run in a different font/size (an
    inline icon glyph, a stray leading space with different formatting,
    ...) followed by several runs of the paragraph's REAL, consistent body
    formatting - the majority must win, not whichever run comes first."""
    paragraph = WordParagraph(
        runs=[
            WordRun(text="", source_rpr=_rpr("Segoe UI Emoji", "24")),  # leading icon, 12pt
            WordRun(text="This is the actual ", source_rpr=_rpr("Montserrat", "22")),  # 11pt
            WordRun(text="body text of the paragraph, ", source_rpr=_rpr("Montserrat", "22")),
            WordRun(text="consistently formatted.", source_rpr=_rpr("Montserrat", "22")),
        ]
    )

    result = paragraph_to_html(paragraph)

    assert _signature(result.base_rpr) == ("Montserrat", "22")


def test_the_dominant_formatting_wins_even_when_it_is_not_the_first_run() -> None:
    paragraph = WordParagraph(
        runs=[
            WordRun(text="A ", source_rpr=_rpr("Arial", "20")),
            WordRun(text="B ", source_rpr=_rpr("Montserrat", "22")),
            WordRun(text="C ", source_rpr=_rpr("Montserrat", "22")),
            WordRun(text="D", source_rpr=_rpr("Montserrat", "22")),
        ]
    )

    result = paragraph_to_html(paragraph)

    assert _signature(result.base_rpr) == ("Montserrat", "22")


def test_a_uniformly_formatted_paragraph_is_unaffected() -> None:
    """Sanity guard: the common case (every run the same) must still work
    exactly as before - this is not a change in behavior for the normal
    case, only for the edge case above."""
    paragraph = WordParagraph(
        runs=[
            WordRun(text="One ", source_rpr=_rpr("Montserrat", "22")),
            WordRun(text="paragraph.", source_rpr=_rpr("Montserrat", "22")),
        ]
    )

    result = paragraph_to_html(paragraph)

    assert _signature(result.base_rpr) == ("Montserrat", "22")
