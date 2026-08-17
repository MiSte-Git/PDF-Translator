"""Loss-minimising OOXML engine for PowerPoint ``.pptx`` files.

Only slide text in normal shapes/placeholders, tables and nested group shapes
is exposed.  The engine keeps direct references to original ``<a:t>`` nodes;
write-back changes their text only.  It never rebuilds shapes or paragraphs.
"""
from __future__ import annotations

import hashlib
import math
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Iterable

from lxml import etree

from pipeline.presentation.base import (
    OverflowFinding,
    OverflowRegression,
    PresentationParagraph,
    PresentationRun,
    PresentationTextContainer,
    RunFormatting,
)

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
_NON_TRANSLATABLE_PLACEHOLDER_TYPES = frozenset({"ftr", "dt", "sldNum"})
_A = f"{{{NS['a']}}}"
_P = f"{{{NS['p']}}}"


def _xml(element: etree._Element | None) -> str | None:
    return None if element is None else etree.tostring(element, encoding="unicode")


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _slide_sort_key(path: str) -> tuple[int, str]:
    stem = Path(path).stem
    digits = "".join(char for char in stem if char.isdigit())
    return (int(digits) if digits else 0, path)


class PptxEngine:
    """Read and minimally edit supported text containers in a PPTX package."""

    def __init__(self) -> None:
        self._source_path: Path | None = None
        self._archive_entries: list[tuple[zipfile.ZipInfo, bytes]] = []
        self._original_by_name: dict[str, bytes] = {}
        self._slide_roots: dict[str, etree._Element] = {}
        self._containers: list[PresentationTextContainer] = []
        self._dirty_slides: set[str] = set()

    def open(self, path: str | Path) -> None:
        source = Path(path).resolve()
        if source.suffix.lower() != ".pptx":
            raise ValueError(f"Expected a .pptx file, got {source}")
        with zipfile.ZipFile(source) as archive:
            entries = [(info, archive.read(info.filename)) for info in archive.infolist()]

        self._source_path = source
        self._archive_entries = entries
        self._original_by_name = {info.filename: data for info, data in entries}
        self._slide_roots = {}
        self._containers = []
        self._dirty_slides = set()

        slide_paths = sorted(
            (
                name
                for name in self._original_by_name
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ),
            key=_slide_sort_key,
        )
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
        for slide_path in slide_paths:
            root = etree.fromstring(self._original_by_name[slide_path], parser)
            self._slide_roots[slide_path] = root
            self._containers.extend(self._extract_slide(slide_path, root))

    def get_text_containers(self) -> list[PresentationTextContainer]:
        return self._containers

    def set_run_text(self, run: PresentationRun, text: str) -> None:
        """Replace a run's text by changing only its existing ``<a:t>`` nodes.

        Multi-``a:t`` runs are rare but legal.  New text goes into the first
        node and the remaining nodes are cleared, avoiding any element rebuild.
        """
        if not run._text_nodes:
            raise ValueError("This run has no writable <a:t> node")
        run._text_nodes[0].text = text
        for node in run._text_nodes[1:]:
            node.text = ""
        run.text = text
        slide_path = self._slide_for_node(run._text_nodes[0])
        self._dirty_slides.add(slide_path)

    def save(self, output_path: str | Path) -> None:
        """Save to a new path; the opened source can never be overwritten."""
        if self._source_path is None:
            raise RuntimeError("No presentation opened")
        destination = Path(output_path).resolve()
        if destination == self._source_path:
            raise ValueError("Refusing to overwrite the source presentation")
        if destination.exists():
            raise FileExistsError(f"Destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Strongest possible no-op roundtrip: preserve every byte, including
        # ZIP central-directory details that a rewrite could legitimately alter.
        if not self._dirty_slides:
            shutil.copyfile(self._source_path, destination)
            return

        replacements = {
            path: etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            for path, root in self._slide_roots.items()
            if path in self._dirty_slides
        }
        with zipfile.ZipFile(destination, "w") as output:
            for info, original in self._archive_entries:
                output.writestr(info, replacements.get(info.filename, original))

    def structural_fingerprint(self) -> dict[str, str]:
        """Hashes package parts while ignoring only the values of ``<a:t>``.

        This supports proving that a text edit did not alter geometry,
        animation, relationships, paragraph properties, or other structures.
        """
        result: dict[str, str] = {}
        for name, original in self._original_by_name.items():
            if name in self._slide_roots:
                root = deepcopy(self._slide_roots[name])
                for node in root.xpath(".//a:t", namespaces=NS):
                    node.text = ""
                payload = etree.tostring(root, method="c14n", with_comments=True)
            else:
                payload = original
            result[name] = hashlib.sha256(payload).hexdigest()
        return result

    def detect_text_overflow(self) -> list[OverflowFinding]:
        """Report likely overflow without modifying font sizes or geometry.

        OOXML contains no authoritative post-layout overflow flag; PowerPoint's
        renderer computes it.  This conservative static estimate reports only
        fixed-size text bodies whose approximate line demand exceeds available
        height.  Visual rendering remains the definitive verification step.
        """
        findings: list[OverflowFinding] = []
        for container in self._containers:
            if not container.text.strip() or not container.width or not container.height:
                continue
            autofit = next(
                (
                    mode
                    for mode in ("normAutofit", "spAutoFit")
                    if mode in container.body_properties
                ),
                None,
            )
            font_points = self._representative_font_size(container)
            if font_points <= 0:
                continue
            width_points = container.width / 12700
            height_points = container.height / 12700
            chars_per_line = max(int(width_points / (font_points * 0.52)), 1)
            estimated_lines = sum(
                max(1, math.ceil(len(paragraph.text) / chars_per_line))
                for paragraph in container.paragraphs
            )
            available_lines = max(int(height_points / (font_points * 1.2)), 1)
            if estimated_lines > available_lines:
                findings.append(
                    OverflowFinding(
                        slide_path=container.slide_path,
                        shape_id=container.shape_id,
                        shape_name=container.shape_name,
                        kind=container.kind,
                        reason=(
                            f"static_estimate_exceeds_text_body_with_{autofit}"
                            if autofit
                            else "static_estimate_exceeds_fixed_text_body"
                        ),
                        estimated_lines=estimated_lines,
                        available_lines=available_lines,
                        table_cell=container.table_cell,
                    )
                )
        return findings

    def compare_overflow(self, baseline: "PptxEngine") -> list[OverflowRegression]:
        """Report only new or more severe static fit risks versus a source deck."""
        before = {
            (finding.slide_path, finding.shape_id, finding.table_cell): finding
            for finding in baseline.detect_text_overflow()
        }
        regressions: list[OverflowRegression] = []
        for finding in self.detect_text_overflow():
            key = (finding.slide_path, finding.shape_id, finding.table_cell)
            previous = before.get(key)
            previous_lines = previous.estimated_lines if previous is not None else None
            if previous_lines is not None and finding.estimated_lines <= previous_lines:
                continue
            regressions.append(
                OverflowRegression(
                    slide_path=finding.slide_path,
                    shape_id=finding.shape_id,
                    shape_name=finding.shape_name,
                    before_estimated_lines=previous_lines,
                    after_estimated_lines=finding.estimated_lines or 0,
                    available_lines=finding.available_lines or 0,
                    reason=("new_fit_risk" if previous is None else "increased_fit_risk"),
                )
            )
        return regressions

    def capability_catalog(self) -> dict[str, str]:
        return {
            "normal_text_boxes": "supported",
            "placeholders": "supported (slide-local text only)",
            "tables": "supported",
            "grouped_shapes": "supported recursively",
            "smartart": "not supported; left byte-identical",
            "chart_text": "not supported; left byte-identical",
            "speaker_notes": "not supported; left byte-identical",
            "embedded_objects": "not supported; left byte-identical",
            "text_in_images": "not supported; left byte-identical",
            "master_and_layout_text": "not supported; left byte-identical",
        }

    def _slide_for_node(self, node: etree._Element) -> str:
        root = node.getroottree().getroot()
        for path, candidate in self._slide_roots.items():
            if candidate is root:
                return path
        raise RuntimeError("Text node does not belong to an opened slide")

    def _extract_slide(
        self, slide_path: str, root: etree._Element
    ) -> Iterable[PresentationTextContainer]:
        shape_tree = root.find(".//p:cSld/p:spTree", namespaces=NS)
        if shape_tree is None:
            return []
        containers: list[PresentationTextContainer] = []
        self._walk_shape_children(slide_path, shape_tree, (), containers)
        return containers

    def _walk_shape_children(
        self,
        slide_path: str,
        parent: etree._Element,
        group_path: tuple[str, ...],
        output: list[PresentationTextContainer],
    ) -> None:
        for child in parent:
            if child.tag == _P + "sp":
                tx_body = child.find("p:txBody", namespaces=NS)
                if tx_body is not None:
                    output.append(self._shape_container(slide_path, child, tx_body, group_path))
            elif child.tag == _P + "grpSp":
                group_id, group_name = self._shape_identity(child, "group")
                self._walk_shape_children(
                    slide_path, child, group_path + (f"{group_id}:{group_name}",), output
                )
            elif child.tag == _P + "graphicFrame":
                table = child.find(".//a:tbl", namespaces=NS)
                if table is not None:
                    output.extend(self._table_containers(slide_path, child, table, group_path))

    def _shape_container(
        self,
        slide_path: str,
        shape: etree._Element,
        tx_body: etree._Element,
        group_path: tuple[str, ...],
    ) -> PresentationTextContainer:
        shape_id, name = self._shape_identity(shape, "shape")
        placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", namespaces=NS)
        placeholder_type = placeholder.get("type") if placeholder is not None else None
        excluded = placeholder_type in _NON_TRANSLATABLE_PLACEHOLDER_TYPES
        x, y, width, height, rotation = self._geometry(shape.find("p:spPr/a:xfrm", namespaces=NS))
        return PresentationTextContainer(
            slide_path=slide_path,
            shape_id=shape_id,
            shape_name=name,
            kind="placeholder" if placeholder is not None else "text_box",
            placeholder_type=placeholder_type,
            paragraphs=self._paragraphs(tx_body),
            group_path=group_path,
            x=x,
            y=y,
            width=width,
            height=height,
            rotation=rotation,
            body_properties=self._body_properties(tx_body),
            translatable=not excluded,
            exclusion_reason=(
                f"protected_placeholder:{placeholder_type}" if excluded else None
            ),
        )

    def _table_containers(
        self,
        slide_path: str,
        frame: etree._Element,
        table: etree._Element,
        group_path: tuple[str, ...],
    ) -> Iterable[PresentationTextContainer]:
        shape_id, name = self._shape_identity(frame, "table")
        x, y, width, height, rotation = self._geometry(
            frame.find("p:xfrm", namespaces=NS)
        )
        for row_index, row in enumerate(table.findall("a:tr", namespaces=NS)):
            for column_index, cell in enumerate(row.findall("a:tc", namespaces=NS)):
                tx_body = cell.find("a:txBody", namespaces=NS)
                if tx_body is None:
                    continue
                yield PresentationTextContainer(
                    slide_path=slide_path,
                    shape_id=shape_id,
                    shape_name=name,
                    kind="table_cell",
                    table_cell=(row_index, column_index),
                    paragraphs=self._paragraphs(tx_body),
                    group_path=group_path,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    rotation=rotation,
                    body_properties=self._body_properties(tx_body),
                )

    @staticmethod
    def _shape_identity(shape: etree._Element, fallback: str) -> tuple[str, str]:
        node = shape.find(".//p:cNvPr", namespaces=NS)
        if node is None:
            return "", fallback
        return node.get("id", ""), node.get("name", fallback)

    @staticmethod
    def _geometry(
        xfrm: etree._Element | None,
    ) -> tuple[int | None, int | None, int | None, int | None, int | None]:
        if xfrm is None:
            return None, None, None, None, None
        offset = xfrm.find("a:off", namespaces=NS)
        extent = xfrm.find("a:ext", namespaces=NS)
        return (
            _int(offset.get("x")) if offset is not None else None,
            _int(offset.get("y")) if offset is not None else None,
            _int(extent.get("cx")) if extent is not None else None,
            _int(extent.get("cy")) if extent is not None else None,
            _int(xfrm.get("rot")),
        )

    def _paragraphs(self, tx_body: etree._Element) -> list[PresentationParagraph]:
        paragraphs: list[PresentationParagraph] = []
        for paragraph in tx_body.findall("a:p", namespaces=NS):
            runs: list[PresentationRun] = []
            break_positions: list[int] = []
            for child in paragraph:
                if child.tag == _A + "br":
                    break_positions.append(len(runs))
                    continue
                if child.tag not in {_A + "r", _A + "fld"}:
                    continue
                text_nodes = tuple(child.findall("a:t", namespaces=NS))
                if not text_nodes:
                    continue
                rpr = child.find("a:rPr", namespaces=NS)
                runs.append(
                    PresentationRun(
                        text="".join(node.text or "" for node in text_nodes),
                        formatting=self._run_formatting(rpr),
                        run_kind="field" if child.tag == _A + "fld" else "run",
                        text_node_count=len(text_nodes),
                        _text_nodes=text_nodes,
                    )
                )
            paragraphs.append(
                PresentationParagraph(
                    runs=runs,
                    break_positions=tuple(break_positions),
                    paragraph_properties_xml=_xml(paragraph.find("a:pPr", namespaces=NS)),
                    end_properties_xml=_xml(paragraph.find("a:endParaRPr", namespaces=NS)),
                )
            )
        return paragraphs

    @staticmethod
    def _body_properties(tx_body: etree._Element) -> dict[str, str]:
        body = tx_body.find("a:bodyPr", namespaces=NS)
        if body is None:
            return {}
        properties = dict(body.attrib)
        for child in body:
            properties[etree.QName(child).localname] = _xml(child) or ""
        return properties

    @staticmethod
    def _run_formatting(rpr: etree._Element | None) -> RunFormatting:
        if rpr is None:
            return RunFormatting()
        properties: dict[str, object] = dict(rpr.attrib)
        properties["attributes"] = dict(rpr.attrib)
        properties["children"] = [
            {
                "name": etree.QName(child).localname,
                "attributes": dict(child.attrib),
                "xml": _xml(child),
            }
            for child in rpr
        ]
        for font_tag in ("latin", "ea", "cs", "sym"):
            font = rpr.find(f"a:{font_tag}", namespaces=NS)
            if font is not None:
                properties[f"{font_tag}_typeface"] = font.get("typeface")
        solid_fill = rpr.find("a:solidFill", namespaces=NS)
        if solid_fill is not None and len(solid_fill):
            color = solid_fill[0]
            properties["color_type"] = etree.QName(color).localname
            properties["color_value"] = color.get("val") or color.get("lastClr")
        return RunFormatting(properties=properties, raw_rpr_xml=_xml(rpr))

    @staticmethod
    def _representative_font_size(container: PresentationTextContainer) -> float:
        sizes: list[float] = []
        for paragraph in container.paragraphs:
            for run in paragraph.runs:
                size = run.formatting.properties.get("sz")
                try:
                    sizes.append(int(str(size)) / 100)
                except (TypeError, ValueError):
                    continue
        return max(sizes) if sizes else 18.0
