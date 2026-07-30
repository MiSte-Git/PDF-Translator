from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

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
