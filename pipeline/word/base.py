from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Marks a <w:br/> line break found within a <w:r> as its own WordRun (see
# DocxEngine._build_runs() in pipeline/word/docx_engine.py) - the Word
# analog of PARAGRAPH_BREAK_MARKER/LINE_BREAK_MARKER in pipeline/pdf/base.py
# for the same underlying problem (a single paragraph/run bundling several
# visual line transitions, e.g. a title immediately followed by body text -
# see WordParagraph). A dedicated §§...§§-style placeholder rather than a
# literal "<br/>" or "\n": pipeline/word/html_bridge.py sends this through
# translate_html() verbatim, and unlike an HTML tag, a translation model
# instructed to "preserve HTML tags" can still reformat/drop "<br/>" - a
# placeholder survives such a prompt far more reliably, exactly like
# protect_terms()'s §§N§§ placeholders (pipeline/translation/protected_terms.py).
BREAK_MARKER = "§§BR§§"


@dataclass
class WordRun:
    """One run of text within a WordParagraph. Usually maps 1:1 to one
    <w:r> (or one <w:r> nested inside a <w:hyperlink> - see
    WordEngine.get_paragraphs()), except a <w:r> containing one or more
    <w:br/> line breaks, which becomes several WordRuns: the text before/
    after each break as its own WordRun, and each break itself as its own
    WordRun with text == BREAK_MARKER (see DocxEngine._build_runs()).
    """
    text: str
    translatable: bool = True
    is_image: bool = False
    """Whether this run carries a <w:drawing>/<pic:pic> image instead of
    (or alongside) text. Image runs are always translatable=False,
    independent of the paragraph's own translatable flag - images are
    never touched by translation, even inside an otherwise-translatable
    paragraph."""
    is_hyperlink: bool = False
    """Whether this run sits inside a <w:hyperlink> element."""
    hyperlink_target: str | None = None
    """The hyperlink's resolved target (URL, mailto:, ...), looked up via
    the hyperlink's r:id in word/_rels/document.xml.rels. None unless
    is_hyperlink is True."""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    """Formatting read from the run's <w:rPr> (OOXML toggle-property
    semantics - see DocxEngine._run_properties()). Meaningless/False on a
    BREAK_MARKER or image run."""


@dataclass
class WordParagraph:
    """One paragraph extracted from a Word document body (one <w:p>)."""
    runs: list[WordRun] = field(default_factory=list)
    translatable: bool = True
    """Whether this paragraph should be sent to translation. False for the
    page-1 metadata block that precedes the document's separator-line
    shape (see DocxEngine.get_paragraphs())."""


@runtime_checkable
class WordEngine(Protocol):
    """Abstraction over the underlying Word document library (e.g. a
    zipfile/lxml-based .docx reader). Analogous to pipeline.pdf.base.PdfEngine.
    """

    def open(self, path: str) -> None:
        """Load a .docx document for processing."""
        ...

    def get_paragraphs(self) -> list[WordParagraph]:
        """Return every paragraph in the document body, in reading order."""
        ...

    def save(self, path: str) -> None:
        """Write the resulting document to disk."""
        ...
