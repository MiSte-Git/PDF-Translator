from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path


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
