from __future__ import annotations
from dataclasses import dataclass


@dataclass
class DocumentTemplate:
    """Defines reusable exclusion zones for PDF documents that share a
    common layout (e.g. recurring report templates).

    header_bbox/footer_bbox apply to every page. first_page_zones applies
    only to page_index == 0 (e.g. a fixed metadata block that only appears
    on the first page, like a title/date/issuer block).
    """
    name: str
    header_bbox: tuple[float, float, float, float] | None
    footer_bbox: tuple[float, float, float, float] | None
    first_page_zones: list[tuple[float, float, float, float]] | None = None


def block_overlaps(
    block_bbox: tuple[float, float, float, float],
    zone_bbox: tuple[float, float, float, float],
) -> bool:
    """Check whether two bbox rectangles (x0, y0, x1, y1) overlap."""
    bx0, by0, bx1, by1 = block_bbox
    zx0, zy0, zx1, zy1 = zone_bbox
    return bx0 < zx1 and bx1 > zx0 and by0 < zy1 and by1 > zy0
