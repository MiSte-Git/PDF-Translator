"""Qt QTextDocument <-> this project's minimal translated-block HTML
(pipeline.pdf.pymupdf_engine.spans_to_html()'s tag set: <p>/<br/>/<u>/<i>/
<b>, no attributes) conversion, for ui/correction_dialog.py's rich-text
per-row editor (RoadMap.md Phase 2/PDF's "PDF-Übersetzung korrigieren"
item - added once a plain-text-only editor's formatting-loss-on-edit
trade-off turned out to matter to a real user).

Deliberately its own module, not part of pipeline/pdf/pymupdf_engine.py:
this file is the ONLY place in the project allowed to import Qt's rich
text classes (QFont/QTextDocument), the same separation-of-concerns reason
pymupdf_engine.py is the only file allowed to import PyMuPDF - the
pipeline layer must stay UI-framework-agnostic.

Loading a translated_html string INTO a QTextEdit needs no conversion at
all: QTextEdit.setHtml() already understands this project's tag set
directly (it's a strict subset of the HTML4 dialect Qt's rich text engine
supports) - only the OTHER direction (editor content -> our minimal HTML,
after a user's edit) needs real work, done here by
qt_document_to_project_html().
"""
from __future__ import annotations

import html as html_module

from PySide6.QtGui import QFont, QTextDocument

# Qt's "soft line break" character (Shift+Enter inside one QTextBlock/
# paragraph, as opposed to Enter which starts a whole new QTextBlock) -
# shows up inside QTextFragment.text() as a literal U+2028 LINE SEPARATOR
# character, never as a real newline. Mapped to our own <br/> marker
# (spans_to_html()'s LINE_BREAK_MARKER equivalent at the HTML layer) so a
# user's Shift+Enter round-trips the same way a document's original
# LINE_BREAK_MARKER spans already do.
_QT_LINE_SEPARATOR = " "


def qt_document_to_project_html(document: QTextDocument) -> str:
    """Inverse of "load translated_html via QTextEdit.setHtml()": walk
    `document` block-by-block (= one QTextBlock per paragraph) and
    fragment-by-fragment (= one QTextFragment per maximal run of
    consistent character formatting within a paragraph) and re-emit this
    project's own minimal <p>/<br/>/<u>/<i>/<b> markup - deliberately NOT
    QTextDocument.toHtml()/toMarkdown(), both of which produce a full,
    verbose HTML document (styles, fonts, margins, an <html><body>
    wrapper) completely unlike the plain fragment markup
    spans_to_html()/_plain_text_to_html() produce and
    PyMuPdfEngine.insert_text() expects.

    Bold/italic/underline come from each fragment's QTextCharFormat
    (fontWeight()/fontItalic()/fontUnderline()) - exactly the three
    styling flags TextSpan/spans_to_html() already round-trip, so a block
    that came from spans_to_html() in the first place (every real
    production TranslatedBlockRecord - see that class's docstring) maps
    onto this editor's formatting model with no gaps in either direction.
    A bold-weight check (>= QFont.Weight.Bold) rather than "not Normal"
    matches how PdfCorrectionDialog's Fett button actually sets weight
    (either Bold or Normal, nothing in between - see that class's
    _toggle_bold()).

    A block/paragraph that ends up empty (no fragments, or only
    whitespace/tags) is dropped entirely, matching spans_to_html()'s own
    `if paragraph.strip()` filter - an empty trailing paragraph is a
    normal side effect of how QTextDocument represents an empty last line
    and was never meant to become a genuine (and, on re-insertion, purely
    wasted-space) <p></p>.
    """
    paragraphs: list[str] = []
    block = document.begin()
    while block.isValid():
        paragraph_parts: list[str] = []
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                text = fragment.text()
                if text:
                    char_format = fragment.charFormat()
                    escaped = "<br/>".join(
                        html_module.escape(segment) for segment in text.split(_QT_LINE_SEPARATOR)
                    )
                    if char_format.fontUnderline():
                        escaped = f"<u>{escaped}</u>"
                    if char_format.fontItalic():
                        escaped = f"<i>{escaped}</i>"
                    if char_format.fontWeight() >= QFont.Weight.Bold:
                        escaped = f"<b>{escaped}</b>"
                    paragraph_parts.append(escaped)
            it += 1
        paragraphs.append("".join(paragraph_parts))
        block = block.next()
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs if paragraph.strip())
