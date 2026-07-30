from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Marks a paragraph break within TextBlock.spans (see TextSpan). Chosen to
# match the "\n\n" convention PyMuPdfEngine.insert_text() already uses to
# separate paragraphs, so both representations agree on one marker.
PARAGRAPH_BREAK_MARKER = "\n\n"

@dataclass
class TextSpan:
    """One run of uniformly formatted text within a TextBlock.

    A blank/whitespace-only source line - a real paragraph break, not a mere
    wrap artifact (see PyMuPdfEngine.extract_blocks()) - is encoded as its
    own TextSpan with text=PARAGRAPH_BREAK_MARKER instead of real content;
    its font_name/font_size/color/bold/italic are unused placeholders.
    """
    text: str
    font_name: str
    font_size: float
    color: tuple[int, int, int]
    bold: bool
    italic: bool

@dataclass
class TextBlock:
    """One paragraph-level text block extracted from a PDF page."""
    page_index: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    text: str
    font_name: str
    font_size: float
    color: tuple[int, int, int]
    bold: bool
    italic: bool
    translatable: bool = True
    """Whether this block should be sent to translation. False for headers,
    footers, and hyperlink text, which must remain unchanged."""
    spans: list[TextSpan] = field(default_factory=list)
    """Formatting runs (and paragraph-break markers) in reading order. An
    empty list means uniform formatting; font_name/font_size/color/bold/
    italic above still hold the first span's formatting either way, for
    code that doesn't use spans yet."""

@dataclass
class PageInfo:
    """Metadata about a PDF page, independent of the underlying engine."""
    index: int
    width: float
    height: float

@dataclass
class ImageBlock:
    """A raster image found on a PDF page, independent of the underlying engine."""
    page_index: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    xref: int
    """Engine-internal reference ID used to locate/replace this image later."""

@runtime_checkable
class PdfEngine(Protocol):
    """Abstraction over the underlying PDF library (e.g. PyMuPDF)."""

    def open(self, path: str) -> None:
        """Load a PDF document for processing."""
        ...

    def get_pages(self) -> list[PageInfo]:
        """Return metadata for all pages."""
        ...

    def extract_blocks(self, page_index: int) -> list[TextBlock]:
        """Extract paragraph-level text blocks from a page."""
        ...

    def extract_images(self, page_index: int) -> list[ImageBlock]:
        """Extract all raster images on a page, for collision checks and later
        image-translation (OCR + inpainting). Does not extract image content itself.
        """
        ...

    def replace_image(self, image: ImageBlock, new_image_bytes: bytes) -> None:
        """Replace an image's content in place, keeping its position and size.
        Used by the image-translation feature once OCR/inpainting is implemented.
        """
        ...

    def redact_block(self, block: TextBlock) -> None:
        """Cover the original text area of a block (e.g. white fill)."""
        ...

    def insert_text(self, block: TextBlock, text: str, font_size: float) -> bool:
        """Insert translated text into a block's area.
        Returns True if it fit without overflow, False otherwise.
        """
        ...

    def save(self, path: str) -> None:
        """Write the resulting PDF to disk."""
        ...
