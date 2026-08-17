"""Provider-independent presentation text model.

The model deliberately records both convenient, normalised formatting values
and the complete raw ``<a:rPr>`` XML.  PowerPoint run formatting has a large
and extensible OOXML surface; retaining the raw XML makes the inventory
lossless even when a property is not yet interpreted by this first version.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RunFormatting:
    """Formatting attached directly to one ``<a:r>``/``<a:fld>`` run."""

    properties: dict[str, Any] = field(default_factory=dict)
    raw_rpr_xml: str | None = None


@dataclass
class PresentationRun:
    text: str
    formatting: RunFormatting
    run_kind: str = "run"
    text_node_count: int = 1
    _text_nodes: tuple[Any, ...] = field(default_factory=tuple, repr=False, compare=False)


@dataclass
class PresentationParagraph:
    runs: list[PresentationRun] = field(default_factory=list)
    break_positions: tuple[int, ...] = ()
    """Positions of existing ``<a:br>`` nodes as run counts before the break."""
    paragraph_properties_xml: str | None = None
    end_properties_xml: str | None = None

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass
class PresentationTextContainer:
    """A shape or table cell containing a DrawingML text body."""

    slide_path: str
    shape_id: str
    shape_name: str
    kind: str
    paragraphs: list[PresentationParagraph]
    group_path: tuple[str, ...] = ()
    table_cell: tuple[int, int] | None = None
    placeholder_type: str | None = None
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    rotation: int | None = None
    body_properties: dict[str, str] = field(default_factory=dict)
    translatable: bool = True
    exclusion_reason: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(paragraph.text for paragraph in self.paragraphs)


@dataclass(frozen=True)
class OverflowFinding:
    slide_path: str
    shape_id: str
    shape_name: str
    kind: str
    reason: str
    estimated_lines: int | None = None
    available_lines: int | None = None
    table_cell: tuple[int, int] | None = None


@dataclass(frozen=True)
class OverflowRegression:
    slide_path: str
    shape_id: str
    shape_name: str
    before_estimated_lines: int | None
    after_estimated_lines: int
    available_lines: int
    reason: str
