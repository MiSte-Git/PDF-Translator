"""Covers pipeline/word/html_bridge.py's html_to_paragraph() forced-break-
before-image/symbol fix (03.09.2026, following up on the earlier <w:sym/>
bullet fix - Michael, from a real translated ICO document): a translation
provider is free to reflow plain text across a <br/> boundary (a
legitimate translation choice - e.g. German's verb-final word order can
pull a word or two past a line break that, in English, cleanly separated
one sentence from the next). When that happens to land right in front of
an image or <w:sym/> bullet, the bullet ends up mid-line instead of at
the start of its own line.

Michael: "Könnten wir wenigstens vor dem Bild einen Zeilenumbruch und Line
Feed in der Übersetzung einbauen? Dann bleibt zwar möglicherweise ein
Wort einfach im Raum stehen." - explicitly accepting that a stray word can
be left alone on the line above, in exchange for the bullet always
starting its own line.
"""
from __future__ import annotations

from pipeline.word.base import BREAK_MARKER, WordParagraph, WordRun
from pipeline.word.html_bridge import html_to_paragraph, paragraph_to_html


def test_a_provider_moving_text_up_to_an_image_gets_a_forced_break_inserted() -> None:
    """Simulates exactly the reported real-world case: the ORIGINAL has a
    clean break right before the bullet/image, but the TRANSLATED HTML
    (as a provider might legitimately return it) has extra words glued
    onto the image tag with no <br/> of its own."""
    paragraph = WordParagraph(
        runs=[
            WordRun(text="...greater coherence"),
            WordRun(text=BREAK_MARKER),
            WordRun(text=BREAK_MARKER),
            WordRun(text=BREAK_MARKER),
            WordRun(text="", is_image=True),
            WordRun(text=" More declas will be posted soon."),
        ]
    )
    original = paragraph_to_html(paragraph)
    assert original.html == (
        "...greater coherence<br/><br/><br/>"
        f'<img data-run="4"/> More declas will be posted soon.'
    )

    # A provider that moved "können entwickeln" up against the <img> tag,
    # with no <br/> separating them - the actual reported shape.
    translated_html = (
        "...größerer Kohärenz<br/><br/><br/>"
        ' entwickeln können<img data-run="4"/> Weitere Meldungen folgen bald.'
    )

    runs = html_to_paragraph(translated_html, original)

    # A break must now sit immediately before the image run, even though
    # the translated HTML itself had none there.
    image_position = next(i for i, r in enumerate(runs) if r.is_image)
    assert image_position > 0
    assert runs[image_position - 1].text == BREAK_MARKER

    # And the stray text is still there, just on its own line above the
    # bullet - not silently dropped (the explicitly accepted trade-off).
    texts = [r.text for r in runs]
    assert "entwickeln können" in "".join(t for t in texts if t != BREAK_MARKER)


def test_no_extra_break_is_added_when_one_already_precedes_the_image() -> None:
    """The common, already-correct case (a <br/> genuinely precedes the
    image/symbol in the translated HTML too) must not get a SECOND,
    redundant break inserted."""
    paragraph = WordParagraph(
        runs=[
            WordRun(text="Some text."),
            WordRun(text=BREAK_MARKER),
            WordRun(text="", is_image=True),
        ]
    )
    original = paragraph_to_html(paragraph)
    translated_html = 'Ein Text.<br/><img data-run="2"/>'

    runs = html_to_paragraph(translated_html, original)

    break_count = sum(1 for r in runs if r.text == BREAK_MARKER)
    assert break_count == 1


def test_an_image_at_the_very_start_of_a_paragraph_gets_no_leading_break() -> None:
    """An image/symbol that's already the first thing in the paragraph
    needs nothing before it - inserting a break there would just add a
    spurious blank line at the top."""
    paragraph = WordParagraph(runs=[WordRun(text="", is_image=True), WordRun(text=" Bullet text.")])
    original = paragraph_to_html(paragraph)
    translated_html = '<img data-run="0"/> Aufzählungstext.'

    runs = html_to_paragraph(translated_html, original)

    assert runs[0].is_image
