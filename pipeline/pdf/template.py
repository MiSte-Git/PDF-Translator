from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.pdf.base import PdfEngine


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

    def to_dict(self) -> dict:
        """Lossless JSON-serializable representation of this template (see
        from_dict() for the inverse). Bboxes/zones become plain lists since
        JSON has no tuple type.
        """
        return {
            "name": self.name,
            "header_bbox": list(self.header_bbox) if self.header_bbox is not None else None,
            "footer_bbox": list(self.footer_bbox) if self.footer_bbox is not None else None,
            "first_page_zones": (
                [list(zone) for zone in self.first_page_zones]
                if self.first_page_zones is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocumentTemplate:
        """Build a DocumentTemplate from the dict produced by to_dict()
        (bbox/zone lists are converted back to tuples).
        """
        first_page_zones = data.get("first_page_zones")
        header_bbox = data.get("header_bbox")
        footer_bbox = data.get("footer_bbox")
        return cls(
            name=data["name"],
            header_bbox=tuple(header_bbox) if header_bbox is not None else None,
            footer_bbox=tuple(footer_bbox) if footer_bbox is not None else None,
            first_page_zones=(
                [tuple(zone) for zone in first_page_zones] if first_page_zones is not None else None
            ),
        )


def save_json(template: DocumentTemplate, path: str | Path) -> None:
    """Write `template` to `path` as JSON (see DocumentTemplate.to_dict())."""
    Path(path).write_text(json.dumps(template.to_dict(), indent=2), encoding="utf-8")


def load_json(path: str | Path) -> DocumentTemplate:
    """Load a DocumentTemplate previously written by save_json()."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return DocumentTemplate.from_dict(data)


def block_overlaps(
    block_bbox: tuple[float, float, float, float],
    zone_bbox: tuple[float, float, float, float],
) -> bool:
    """Check whether two bbox rectangles (x0, y0, x1, y1) overlap."""
    bx0, by0, bx1, by1 = block_bbox
    zx0, zy0, zx1, zy1 = zone_bbox
    return bx0 < zx1 and bx1 > zx0 and by0 < zy1 and by1 > zy0


_DIGITS_RE = re.compile(r"\d+")


def _normalize_for_repetition(text: str) -> str:
    """Collapse whitespace and strip digits, so a footer line that embeds a
    per-page page number ("Page 3 of 14") still compares equal across
    pages - see detect_header_footer_zones()'s docstring for why exact
    text match alone would miss exactly this common case.
    """
    return " ".join(_DIGITS_RE.sub("#", text).split()).casefold()


def _union_bbox(
    boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return (x0, y0, x1, y1)


def detect_header_footer_zones(
    engine: "PdfEngine",
    *,
    zone_fraction: float = 0.15,
    min_page_fraction: float = 0.6,
) -> tuple[tuple[float, float, float, float] | None, tuple[float, float, float, float] | None]:
    """Detect a document's recurring header/footer bounding box by finding
    text that repeats, at roughly the same position, near the top/bottom
    of a majority of pages - no document-specific DocumentTemplate file
    needed (see templates/virelicon.json for the manually-authored
    equivalent this generalizes; ui/pdf_job.py's direct PDF path never
    loaded that file, which is the actual bug this exists to fix, see
    RoadMap.md Phase 2/PDF).

    `engine` must already be open() and have had NO blocks redacted yet -
    extract_blocks() is read-only and safe to call here ahead of a real
    translation pass (matches how translate_pdf() itself gathers every
    page's blocks up front). Pass an engine constructed WITHOUT a
    DocumentTemplate: this function needs to see every block's true
    top-level bbox to find repetition, not one that's already had a
    template's header/footer applied.

    Method: for each page, blocks whose bbox falls within the top/bottom
    `zone_fraction` of the page height are candidates. Candidates are
    grouped two ways - by normalized text (whitespace-collapsed,
    digit-masked so a per-page page number like "Page 3 of 14" still
    matches "Page 4 of 14", case-folded) and, separately, by rounded
    position (bbox rounded to the nearest 2pt) - because a lone page-
    number block ("1", "2", ...) has NO stable text across pages but DOES
    sit at a stable position, while boilerplate header/footer text is
    normally stable in both. A group "wins" (contributes to the returned
    bbox) if it appears on at least `min_page_fraction` of the document's
    pages; the header/footer bbox returned is the union of every winning
    group's member block bboxes on that side. Returns None for a side
    with no confident repetition - most documents legitimately have no
    header or no footer, and that must not become an over-eager
    exclusion of ordinary body text that merely starts near the top of
    every page (e.g. a consistent title block) - true body content
    varies in wording page to page and won't repeat the same normalized
    text/position, so it doesn't group.
    """
    pages = engine.get_pages()
    if not pages:
        return None, None
    min_pages = max(1, round(min_page_fraction * len(pages)))

    header_groups: dict[str, list[tuple[float, float, float, float]]] = {}
    header_pages: dict[str, set[int]] = {}
    footer_groups: dict[str, list[tuple[float, float, float, float]]] = {}
    footer_pages: dict[str, set[int]] = {}

    for page in pages:
        header_limit = page.height * zone_fraction
        footer_limit = page.height * (1 - zone_fraction)
        for block in engine.extract_blocks(page.index):
            text = block.text.strip()
            if not text:
                continue
            bbox = block.bbox
            position_key = f"pos:{round(bbox[0] / 2) * 2}:{round(bbox[1] / 2) * 2}:{round(bbox[2] / 2) * 2}:{round(bbox[3] / 2) * 2}"
            normalized = _normalize_for_repetition(text)
            text_key = f"text:{normalized}" if normalized else None

            if bbox[1] <= header_limit:
                for key in (text_key, position_key):
                    if key is None:
                        continue
                    header_groups.setdefault(key, []).append(bbox)
                    header_pages.setdefault(key, set()).add(page.index)
            elif bbox[3] >= footer_limit:
                for key in (text_key, position_key):
                    if key is None:
                        continue
                    footer_groups.setdefault(key, []).append(bbox)
                    footer_pages.setdefault(key, set()).add(page.index)

    def _resolve(groups: dict[str, list[tuple[float, float, float, float]]], pages_by_key: dict[str, set[int]]):
        winning_boxes: list[tuple[float, float, float, float]] = []
        for key, boxes in groups.items():
            if len(pages_by_key[key]) >= min_pages:
                winning_boxes.extend(boxes)
        return _union_bbox(winning_boxes) if winning_boxes else None

    return _resolve(header_groups, header_pages), _resolve(footer_groups, footer_pages)
