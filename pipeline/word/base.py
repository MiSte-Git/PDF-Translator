from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class WordRun:
    """One run of text within a WordParagraph (maps to one <w:r>, or one
    <w:r> nested inside a <w:hyperlink> - see WordEngine.get_paragraphs()).
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
