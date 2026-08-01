"""WordEngine implementation reading a .docx's word/document.xml via
zipfile + lxml. Extraction only for now - no write-back (see save()).
"""
from __future__ import annotations

import zipfile

from lxml import etree

from pipeline.word.base import WordParagraph, WordRun

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_RELS_PATH = "word/_rels/document.xml.rels"
_DOCUMENT_PATH = "word/document.xml"


def _w(tag: str) -> str:
    return f"{{{_W_NS}}}{tag}"


def _mc(tag: str) -> str:
    return f"{{{_MC_NS}}}{tag}"


def _a(tag: str) -> str:
    return f"{{{_A_NS}}}{tag}"


def _r_id_attr() -> str:
    return f"{{{_R_NS}}}id"


def _has_separator_shape(paragraph: etree._Element) -> bool:
    """Whether `paragraph` contains the horizontal-rule shape Word uses as
    a visual divider between a document's page-1 metadata block and its
    real content: a DrawingML "straightConnector1" AutoShape, wrapped in
    mc:AlternateContent (see Backlog.md's docx structure analysis). Only
    the DrawingML branch uses <a:prstGeom> - the legacy VML mc:Fallback
    branch uses an unrelated shapetype, so no risk of double-matching a
    single shape via both branches.
    """
    for shape in paragraph.iter(_a("prstGeom")):
        if shape.get("prst") == "straightConnector1":
            return True
    return False


def _walk_run(run: etree._Element) -> tuple[str, bool]:
    """Concatenate a run's <w:t> text and detect whether it carries a
    <w:drawing> image, skipping any mc:Fallback subtree entirely (e.g. the
    legacy VML branch of a drawing's mc:AlternateContent duplicates the
    same text/shape for old Word versions - counting it would double text
    or misdetect images).
    """
    text_parts: list[str] = []
    has_image = False

    def walk(element: etree._Element) -> None:
        nonlocal has_image
        if element.tag == _mc("Fallback"):
            return
        if element.tag == _w("t") and element.text:
            text_parts.append(element.text)
        if element.tag == _w("drawing"):
            has_image = True
        for child in element:
            walk(child)

    walk(run)
    return "".join(text_parts), has_image


def _build_run(
    run: etree._Element,
    paragraph_translatable: bool,
    is_hyperlink: bool = False,
    hyperlink_target: str | None = None,
) -> WordRun:
    text, has_image = _walk_run(run)
    return WordRun(
        text=text,
        translatable=False if has_image else paragraph_translatable,
        is_image=has_image,
        is_hyperlink=is_hyperlink,
        hyperlink_target=hyperlink_target,
    )


def _build_paragraph(
    paragraph: etree._Element, rels: dict[str, str], translatable: bool
) -> WordParagraph:
    """Build one WordParagraph from a <w:p>, walking its direct children in
    document order. A <w:hyperlink> is a paragraph-level sibling of <w:r>
    that wraps one or more <w:r> children (standard OOXML) - not nested
    inside a run - so it's handled as its own case, not via _walk_run().
    """
    runs: list[WordRun] = []
    for child in paragraph:
        if child.tag == _w("r"):
            runs.append(_build_run(child, translatable))
        elif child.tag == _w("hyperlink"):
            target = rels.get(child.get(_r_id_attr()))
            for run_element in child.findall(_w("r")):
                runs.append(
                    _build_run(
                        run_element,
                        translatable,
                        is_hyperlink=True,
                        hyperlink_target=target,
                    )
                )
    return WordParagraph(runs=runs, translatable=translatable)


def _parse_rels(rels_xml: bytes) -> dict[str, str]:
    """Map relationship Id -> Target, from word/_rels/document.xml.rels."""
    root = etree.fromstring(rels_xml)
    return {rel.get("Id"): rel.get("Target") for rel in root}


class DocxEngine:
    """Implements pipeline.word.base.WordEngine by unzipping a .docx and
    parsing word/document.xml with lxml. Headers/footers are not handled
    yet - only the document body.
    """

    def __init__(self) -> None:
        """Nothing is loaded until open() is called."""
        self._paragraphs: list[WordParagraph] = []
        self.separator_found: bool = False
        """Whether a page-1 metadata separator shape (see
        _has_separator_shape()) was found on the most recent open() call -
        exposed for callers (e.g. tests/manual_inspect_word_blocks.py) to
        warn when a document doesn't follow the expected structure."""

    def open(self, path: str) -> None:
        """Load a .docx document: unzip word/document.xml and (if present)
        word/_rels/document.xml.rels, then build one WordParagraph per
        <w:p> in the body. Paragraphs before the first separator-shape
        paragraph (see _has_separator_shape()) are marked non-translatable
        (the page-1 metadata block); if no separator shape is found at
        all, every paragraph is left translatable=True (no metadata block
        detected - see self.separator_found).
        """
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read(_DOCUMENT_PATH)
            rels_xml = archive.read(_RELS_PATH) if _RELS_PATH in archive.namelist() else None

        rels = _parse_rels(rels_xml) if rels_xml is not None else {}

        root = etree.fromstring(document_xml)
        body = root.find(_w("body"))
        assert body is not None, "word/document.xml has no <w:body>"
        paragraph_elements = body.findall(_w("p"))

        anchor_index = next(
            (i for i, p in enumerate(paragraph_elements) if _has_separator_shape(p)), None
        )
        self.separator_found = anchor_index is not None

        self._paragraphs = [
            _build_paragraph(
                p, rels, translatable=(anchor_index is None or i >= anchor_index)
            )
            for i, p in enumerate(paragraph_elements)
        ]

    def get_paragraphs(self) -> list[WordParagraph]:
        """Return every paragraph in the document body, in reading order."""
        return self._paragraphs

    def save(self, path: str) -> None:
        """Not implemented yet - this engine is extraction-only for now."""
        raise NotImplementedError(
            "DocxEngine.save() is not implemented yet - extraction-only for now."
        )
