"""PdfEngine implementation backed by PyMuPDF (fitz).

This is the only file in the project allowed to import fitz/PyMuPDF.
"""
from __future__ import annotations

import fitz

from pipeline.pdf.base import ImageBlock, PageInfo, TextBlock
from pipeline.pdf.template import DocumentTemplate, block_overlaps

# PyMuPDF span "flags" bitfield: bit 1 = italic, bit 4 = bold.
_ITALIC_FLAG = 1 << 1
_BOLD_FLAG = 1 << 4


class PyMuPdfEngine:
    """Implements pipeline.pdf.base.PdfEngine on top of PyMuPDF."""

    def __init__(self, template: DocumentTemplate | None = None) -> None:
        """Store an optional template used to exclude header/footer zones."""
        self._template = template
        self._doc: fitz.Document | None = None

    def open(self, path: str) -> None:
        """Load a PDF document for processing."""
        self._doc = fitz.open(path)

    def get_pages(self) -> list[PageInfo]:
        """Return metadata for all pages."""
        assert self._doc is not None, "Document not opened. Call open() first."
        pages: list[PageInfo] = []
        for index, page in enumerate(self._doc):
            rect = page.rect
            pages.append(PageInfo(index=index, width=rect.width, height=rect.height))
        return pages

    def extract_blocks(self, page_index: int) -> list[TextBlock]:
        """Extract paragraph-level text blocks from a page.

        Spans are grouped into one TextBlock per PyMuPDF block, using the
        block's bbox, combined text, and the first span's font/size/color/
        style as representative values. A block is marked non-translatable
        if it overlaps a link annotation or the template's header/footer
        zones. Blocks with only whitespace text are skipped.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[page_index]
        raw = page.get_text("dict")

        link_bboxes: list[tuple[float, float, float, float]] = []
        for link in page.get_links():
            rect = link.get("from")
            if rect is not None:
                link_bboxes.append((rect.x0, rect.y0, rect.x1, rect.y1))

        blocks: list[TextBlock] = []
        for raw_block in raw.get("blocks", []):
            if raw_block.get("type") != 0:
                continue  # skip image blocks

            lines = raw_block.get("lines", [])
            spans = [span for line in lines for span in line.get("spans", [])]
            if not spans:
                continue

            text = "\n".join(
                "".join(span["text"] for span in line.get("spans", []))
                for line in lines
            ).strip()
            if not text:
                continue

            first_span = spans[0]
            color_int = first_span.get("color", 0)
            color = (
                (color_int >> 16) & 255,
                (color_int >> 8) & 255,
                color_int & 255,
            )
            flags = first_span.get("flags", 0)
            bbox = tuple(raw_block["bbox"])

            translatable = not any(
                block_overlaps(bbox, link_bbox) for link_bbox in link_bboxes
            )
            if translatable and self._template is not None:
                header_bbox = self._template.header_bbox
                footer_bbox = self._template.footer_bbox
                if header_bbox is not None and block_overlaps(bbox, header_bbox):
                    translatable = False
                elif footer_bbox is not None and block_overlaps(bbox, footer_bbox):
                    translatable = False

            blocks.append(
                TextBlock(
                    page_index=page_index,
                    bbox=bbox,
                    text=text,
                    font_name=first_span.get("font", ""),
                    font_size=first_span.get("size", 0.0),
                    color=color,
                    bold=bool(flags & _BOLD_FLAG),
                    italic=bool(flags & _ITALIC_FLAG),
                    translatable=translatable,
                )
            )

        return blocks

    def extract_images(self, page_index: int) -> list[ImageBlock]:
        """Extract all raster images on a page, for collision checks and later
        image-translation (OCR + inpainting). Does not extract image content itself.

        Uses page.get_images(full=True) to enumerate the images referenced by
        the page, then page.get_image_rects(xref) to resolve their on-page
        position(s). An image can be embedded more than once (same xref, e.g.
        a repeated logo), in which case one ImageBlock is created per rect.
        Images without a resolvable rect are skipped.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[page_index]

        images: list[ImageBlock] = []
        for image_info in page.get_images(full=True):
            xref = image_info[0]
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            for rect in rects:
                images.append(
                    ImageBlock(
                        page_index=page_index,
                        bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                        xref=xref,
                    )
                )

        return images

    def replace_image(self, image: ImageBlock, new_image_bytes: bytes) -> None:
        """Replace an image's content in place, keeping its position and size.
        Used by the image-translation feature once OCR/inpainting is implemented.

        Delegates to page.replace_image(xref, stream=...), which swaps the
        object definition stored under the xref while leaving the page's
        appearance instructions (position, rotation, size) untouched.
        """
        assert self._doc is not None, "Document not opened. Call open() first."
        page = self._doc[image.page_index]
        page.replace_image(image.xref, stream=new_image_bytes)

    def redact_block(self, block: TextBlock) -> None:
        """Cover the original text area of a block (e.g. white fill)."""
        raise NotImplementedError

    def insert_text(self, block: TextBlock, text: str, font_size: float) -> bool:
        """Insert translated text into a block's area.
        Returns True if it fit without overflow, False otherwise.
        """
        raise NotImplementedError

    def save(self, path: str) -> None:
        """Write the resulting PDF to disk."""
        raise NotImplementedError
