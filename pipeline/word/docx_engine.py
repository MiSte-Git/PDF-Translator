"""WordEngine implementation reading a .docx's word/document.xml via
zipfile + lxml. replace_paragraph_runs() can rewrite a single paragraph's
runs in the in-memory tree, and save() writes the result back out as a
full .docx.
"""
from __future__ import annotations

import copy
import zipfile
from pathlib import Path

from lxml import etree

from pipeline.word.base import BREAK_MARKER, WordParagraph, WordRun

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XML_NS = "http://www.w3.org/XML/1998/namespace"

_RELS_PATH = "word/_rels/document.xml.rels"
_DOCUMENT_PATH = "word/document.xml"

# The active default header/footer parts - see Backlog.md's docx
# structure analysis (confirmed generic across a 6-document sample):
# header2.xml/footer1.xml are the "default" headerReference/
# footerReference targets in <w:sectPr>, and since these documents have
# neither <w:titlePg/> nor <w:evenAndOddHeaders/>, Word only ever uses the
# "default" header/footer on every page regardless of the "first"/"even"
# references that also exist in the package (header1.xml/header3.xml).
_HEADER_PATH = "word/header2.xml"
_HEADER_RELS_PATH = "word/_rels/header2.xml.rels"
_FOOTER_PATH = "word/footer1.xml"
_FOOTER_RELS_PATH = "word/_rels/footer1.xml.rels"


def _w(tag: str) -> str:
    return f"{{{_W_NS}}}{tag}"


def _mc(tag: str) -> str:
    return f"{{{_MC_NS}}}{tag}"


def _a(tag: str) -> str:
    return f"{{{_A_NS}}}{tag}"


def _r_id_attr() -> str:
    return f"{{{_R_NS}}}id"


def _xml_space_attr() -> str:
    return f"{{{_XML_NS}}}space"


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


def _walk_run(run: etree._Element) -> tuple[list[str], bool]:
    """Walk a run's content, skipping any mc:Fallback subtree entirely
    (e.g. the legacy VML branch of a drawing's mc:AlternateContent
    duplicates the same text/shape for old Word versions - counting it
    would double text or misdetect images). Returns:
    - text segments split at each <w:br/> (N breaks -> N+1 segments,
      possibly empty strings) - see BREAK_MARKER and _build_runs().
    - whether the run carries a <w:drawing> OR a <w:sym/> anywhere in it -
      both are treated identically from here on (WordRun.is_image=True):
      like an image, a <w:sym/> (a symbol-font character reference, e.g. a
      Wingdings bullet glyph - no <w:t/> text at all) has no translatable
      text representation and must be reused verbatim, never rebuilt.

      03.09.2026 (Michael, real translated documents, flagged as "ein
      Muster... kommt immer wieder vor"): a <w:sym/> bullet character
      sitting in its own run was previously invisible to this function
      entirely (only <w:t>/<w:br>/<w:drawing> were recognized), so it was
      never represented as a WordRun from extraction onward and could
      never survive into translated output - it silently vanished on
      every run, in both normal and side-by-side mode. Folding it into
      the existing has_image/is_image handling (rather than adding a
      parallel is_symbol flag) reuses the already-correct "match original
      elements 1:1, in document order, and reuse them verbatim" logic in
      _replace_runs_in_paragraph() and pipeline/word/side_by_side.py's
      _translated_paragraph_element() for free.
    """
    segments: list[str] = [""]
    has_image = False

    def walk(element: etree._Element) -> None:
        nonlocal has_image
        if element.tag == _mc("Fallback"):
            return
        if element.tag == _w("t") and element.text:
            segments[-1] += element.text
        elif element.tag == _w("br"):
            segments.append("")
        elif element.tag in (_w("drawing"), _w("sym")):
            has_image = True
        for child in element:
            walk(child)

    walk(run)
    return segments, has_image


def _run_properties(run: etree._Element) -> tuple[bool, bool, bool]:
    """Read bold/italic/underline from a run's <w:rPr>, per OOXML toggle-
    property semantics: <w:b>/<w:i> mean True unless their w:val is
    explicitly "false"/"0"/"off"; <w:u> means underlined unless its w:val
    is "none" (any other value - single, double, thick, ... - counts as
    underlined).
    """
    rpr = run.find(_w("rPr"))
    if rpr is None:
        return False, False, False

    def toggle(tag: str) -> bool:
        element = rpr.find(_w(tag))
        if element is None:
            return False
        val = element.get(_w("val"))
        return val is None or val.lower() not in ("0", "false", "off")

    bold = toggle("b")
    italic = toggle("i")

    underline_element = rpr.find(_w("u"))
    underline = (
        underline_element is not None
        and (underline_element.get(_w("val")) or "").lower() != "none"
    )

    return bold, italic, underline


def _copy_rpr(rpr: etree._Element | None) -> etree._Element | None:
    """Deep-copy `rpr` (or return None) - every WordRun that stashes a
    source_rpr gets its own independent copy, so mutating one (e.g. inside
    _build_run_properties()) can never affect another WordRun's."""
    return None if rpr is None else copy.deepcopy(rpr)


# CT_RPr's element order per the OOXML (ECMA-376) schema, truncated to the
# properties this codebase ever reads or writes into a copied <w:rPr> (see
# _build_run_properties()). Needed because _build_run_properties() deep-
# copies an ORIGINAL run's <w:rPr> (which may already carry rFonts/sz/
# rStyle/... in correct schema order) and then adds/replaces its own b/i/u
# toggle elements - simply appending those at the end would put them after
# elements the schema requires them to precede (e.g. <w:sz> must come
# after <w:b>/<w:i>, not before), which Word/LibreOffice can reject or
# silently reinterpret. See _insert_rpr_child().
_RPR_CHILD_ORDER = (
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
    "strike", "dstrike", "outline", "shadow", "emboss", "imprint",
    "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
    "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
    "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
    "eastAsianLayout", "specVanish", "oMath",
)


def _insert_rpr_child(rpr: etree._Element, new_child: etree._Element) -> None:
    """Insert `new_child` into `rpr` at the position CT_RPr's schema order
    (_RPR_CHILD_ORDER) requires, rather than just appending it - see that
    constant's docstring for why. An element whose tag isn't in
    _RPR_CHILD_ORDER (shouldn't happen for b/bCs/i/iCs/u, the only tags
    this is ever called with) is appended at the end as a safe fallback.
    """
    new_tag = etree.QName(new_child).localname
    try:
        new_pos = _RPR_CHILD_ORDER.index(new_tag)
    except ValueError:
        rpr.append(new_child)
        return

    insert_at = len(rpr)
    for i, existing in enumerate(rpr):
        existing_tag = etree.QName(existing).localname
        try:
            existing_pos = _RPR_CHILD_ORDER.index(existing_tag)
        except ValueError:
            continue
        if existing_pos > new_pos:
            insert_at = i
            break
    rpr.insert(insert_at, new_child)


def _build_runs(
    run: etree._Element,
    paragraph_translatable: bool,
    bold: bool,
    italic: bool,
    underline: bool,
    is_hyperlink: bool = False,
    hyperlink_target: str | None = None,
    source_rpr: etree._Element | None = None,
) -> list[WordRun]:
    """Build the WordRun(s) for one <w:r> element - usually one, but a run
    with N embedded <w:br/> line breaks becomes N break-marker WordRuns
    (text == BREAK_MARKER) interleaved with the text segments between them
    (empty segments produce no WordRun). An image run is emitted as its
    own leading WordRun ahead of any text/break segments in the same
    <w:r> - a <w:drawing> sharing a run with real text hasn't been
    observed in practice, but this keeps the image from being lost either
    way.

    `source_rpr` is this run's own <w:r>/<w:rPr> element (see
    _build_paragraph()) - stashed (deep-copied, once per WordRun so later
    in-place mutation of one doesn't leak into another) on every text/
    break WordRun as WordRun.source_rpr, for _build_run_properties() to
    preserve font/size/color/hyperlink-style when this run is later
    rebuilt (translated in place, or reused for the side-by-side
    translated column). Not set on the image/symbol WordRun: that one is
    always reused verbatim (never rebuilt from a WordRun at all - see
    _replace_runs_in_paragraph()), so it has no use for its own rPr here.
    """
    segments, has_image = _walk_run(run)

    runs: list[WordRun] = []
    if has_image:
        runs.append(
            WordRun(
                text="",
                translatable=False,
                is_image=True,
                is_hyperlink=is_hyperlink,
                hyperlink_target=hyperlink_target,
                bold=bold,
                italic=italic,
                underline=underline,
            )
        )

    for i, segment in enumerate(segments):
        if i > 0:
            runs.append(
                WordRun(
                    text=BREAK_MARKER,
                    translatable=paragraph_translatable,
                    is_hyperlink=is_hyperlink,
                    hyperlink_target=hyperlink_target,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    source_rpr=_copy_rpr(source_rpr),
                )
            )
        if segment:
            runs.append(
                WordRun(
                    text=segment,
                    translatable=paragraph_translatable,
                    is_hyperlink=is_hyperlink,
                    hyperlink_target=hyperlink_target,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    source_rpr=_copy_rpr(source_rpr),
                )
            )

    return runs


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
            bold, italic, underline = _run_properties(child)
            runs.extend(
                _build_runs(
                    child, translatable, bold, italic, underline, source_rpr=child.find(_w("rPr"))
                )
            )
        elif child.tag == _w("hyperlink"):
            target = rels.get(child.get(_r_id_attr()))
            for run_element in child.findall(_w("r")):
                bold, italic, underline = _run_properties(run_element)
                runs.extend(
                    _build_runs(
                        run_element,
                        translatable,
                        bold,
                        italic,
                        underline,
                        is_hyperlink=True,
                        hyperlink_target=target,
                        source_rpr=run_element.find(_w("rPr")),
                    )
                )
    return WordParagraph(runs=runs, translatable=translatable)


def _build_break_run() -> etree._Element:
    """<w:r><w:br/></w:r> for a WordRun with text == BREAK_MARKER."""
    run = etree.Element(_w("r"))
    etree.SubElement(run, _w("br"))
    return run


def _build_run_properties(run: WordRun) -> etree._Element | None:
    """<w:rPr> for a rebuilt run - None if there's nothing to write (no
    source_rpr AND no bold/italic/underline), since a <w:r> doesn't need
    an (empty, meaningless) rPr.

    03.09.2026 (Michael: "Ich sehe noch Unterschiede bei den Fonts, Links
    werden bei der Übersetzung scheinbar kaputt gemacht"): previously this
    built a <w:rPr> from scratch containing only b/i/u, discarding every
    other original run property (rFonts, sz, color, the hyperlink <w:
    rStyle>, ...) - translated runs fell back to the document's default
    font, and hyperlinks lost their visual styling entirely (the link
    itself still worked - only its <w:rPr> was gone). Now: when the run
    carries a source_rpr (see WordRun.source_rpr's docstring for where
    that comes from - either the original run this WordRun maps 1:1 to,
    or, for a run built from translated HTML, the paragraph's/hyperlink's
    representative original rPr threaded through by
    pipeline/word/html_bridge.py), that's deep-copied as the base, its own
    b/bCs/i/iCs/u stripped out (they'd reflect whatever formatting the
    ORIGINAL run/paragraph happened to have, not necessarily this run's -
    e.g. a translation can restructure which words end up bold), and this
    run's OWN bold/italic/underline flags are written back in at the
    schema-correct position (_insert_rpr_child()) - so rFonts/sz/color/
    rStyle survive untouched while b/i/u stay accurate to this run.
    """
    if run.source_rpr is not None:
        rpr = copy.deepcopy(run.source_rpr)
        for tag in ("b", "bCs", "i", "iCs", "u"):
            existing = rpr.find(_w(tag))
            if existing is not None:
                rpr.remove(existing)
    elif run.bold or run.italic or run.underline:
        rpr = etree.Element(_w("rPr"))
    else:
        return None

    if run.bold:
        bold = etree.Element(_w("b"))
        _insert_rpr_child(rpr, bold)
        bold_cs = etree.Element(_w("bCs"))
        _insert_rpr_child(rpr, bold_cs)
    if run.italic:
        italic = etree.Element(_w("i"))
        _insert_rpr_child(rpr, italic)
        italic_cs = etree.Element(_w("iCs"))
        _insert_rpr_child(rpr, italic_cs)
    if run.underline:
        underline = etree.Element(_w("u"))
        underline.set(_w("val"), "single")
        _insert_rpr_child(rpr, underline)

    return rpr


def _build_text_run(run: WordRun) -> etree._Element:
    """<w:r><w:rPr>...</w:rPr><w:t xml:space="preserve">...</w:t></w:r>
    for a plain (non-image, non-hyperlink, non-break) WordRun. xml:space
    is always set to "preserve" - without it, Word collapses/drops
    leading or trailing whitespace (e.g. a space right next to a <br/>)
    when the document is next opened.
    """
    element = etree.Element(_w("r"))
    run_properties = _build_run_properties(run)
    if run_properties is not None:
        element.append(run_properties)
    text_element = etree.SubElement(element, _w("t"))
    text_element.set(_xml_space_attr(), "preserve")
    text_element.text = run.text
    return element


def _build_hyperlink_element(rid: str, run: WordRun) -> etree._Element:
    """<w:hyperlink r:id="..."><w:r><w:rPr>...</w:rPr><w:t
    xml:space="preserve">...</w:t></w:r></w:hyperlink> for a hyperlink
    WordRun, reusing an existing relationship id (see
    DocxEngine.replace_paragraph_runs()) rather than creating a new
    word/_rels/document.xml.rels entry.

    03.09.2026 (Michael: "Links werden bei der Übersetzung scheinbar
    kaputt gemacht"): this used to build a bare <w:r><w:t>...</w:t></w:r>
    with NO <w:rPr> at all - the link itself still worked (the r:id was
    always preserved), but the original's <w:rStyle w:val="Hyperlink"/>
    plus its font/size were silently dropped, so a translated hyperlink
    rendered as plain, unstyled black text instead of Word's usual blue/
    underlined link style. Now goes through the same _build_run_properties()
    used for a plain text run, so a hyperlink WordRun's source_rpr (its own
    original <w:hyperlink>/<w:r>/<w:rPr> - see
    ParagraphHtml.hyperlink_source_rpr in pipeline/word/html_bridge.py for
    how a run rebuilt from translated HTML gets one) is preserved the same
    way.
    """
    hyperlink = etree.Element(_w("hyperlink"))
    hyperlink.set(_r_id_attr(), rid)
    inner_run = etree.SubElement(hyperlink, _w("r"))
    run_properties = _build_run_properties(run)
    if run_properties is not None:
        inner_run.append(run_properties)
    text_element = etree.SubElement(inner_run, _w("t"))
    text_element.set(_xml_space_attr(), "preserve")
    text_element.text = run.text
    return hyperlink


def _serialize(root: etree._Element) -> bytes:
    """Serialize a parsed part (document.xml/header2.xml/footer1.xml)
    tree back to bytes, with the same XML declaration style (UTF-8,
    standalone) Word itself writes.
    """
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _replace_runs_in_paragraph(
    paragraph: etree._Element,
    rels: dict[str, str],
    new_runs: list[WordRun],
    context_label: str,
) -> None:
    """Core implementation shared by DocxEngine.replace_paragraph_runs()
    (document.xml) and DocxEngine.replace_header_footer_paragraph()
    (header2.xml/footer1.xml): swap `paragraph`'s <w:r>/<w:hyperlink>
    children for XML built from `new_runs`, using `rels` to resolve/reuse
    hyperlink r:ids. `context_label` is only used in error messages, to
    say which part/paragraph a ValueError came from. See
    DocxEngine.replace_paragraph_runs() for the full behavior description.
    """
    # _walk_run() (not a shallow r.find(_w("drawing"))) - a <w:drawing> can
    # sit nested inside mc:AlternateContent/mc:Choice (e.g. the separator-
    # line shape, see _has_separator_shape()) rather than as a direct
    # child of <w:r>. Must match _build_runs()'s detection depth exactly,
    # or a run WordRun extraction flagged is_image=True for has nothing to
    # match here, as a real StopIteration/ValueError from
    # tests/manual_translate_full_document.py confirmed.
    original_image_runs = [r for r in paragraph.findall(_w("r")) if _walk_run(r)[1]]
    target_to_rid: dict[str, str] = {}
    for hyperlink in paragraph.findall(_w("hyperlink")):
        rid = hyperlink.get(_r_id_attr())
        target = rels.get(rid)
        if target is not None:
            target_to_rid[target] = rid

    for child in list(paragraph):
        if child.tag in (_w("r"), _w("hyperlink")):
            paragraph.remove(child)

    image_run_iter = iter(original_image_runs)

    for run in new_runs:
        if run.is_image:
            try:
                original_element = next(image_run_iter)
            except StopIteration:
                raise ValueError(
                    f"{context_label}: new_runs has more image runs than the "
                    f"{len(original_image_runs)} original <w:drawing> run(s) found "
                    f"here - cannot fabricate a new image run structurally."
                )
            paragraph.append(original_element)
            continue

        if run.text == BREAK_MARKER:
            paragraph.append(_build_break_run())
            continue

        if run.is_hyperlink:
            target = run.hyperlink_target or ""
            rid = target_to_rid.get(target)
            if rid is None:
                raise ValueError(
                    f"{context_label}: no original <w:hyperlink> with target "
                    f"{target!r} found here - cannot reuse an r:id (adding a new "
                    f"relationship isn't supported yet)."
                )
            paragraph.append(_build_hyperlink_element(rid, run))
            continue

        paragraph.append(_build_text_run(run))


def _parse_rels(rels_xml: bytes) -> dict[str, str]:
    """Map relationship Id -> Target, from a part's _rels/*.rels file."""
    root = etree.fromstring(rels_xml)
    return {rel.get("Id"): rel.get("Target") for rel in root}


def _parse_part(
    entries_by_name: dict[str, bytes],
    xml_path: str,
    rels_path: str,
    body_tag: str | None,
) -> tuple[etree._Element | None, list[etree._Element], dict[str, str]]:
    """Parse one document part (word/document.xml, word/header2.xml,
    word/footer1.xml) into (root element, its <w:p> paragraph elements,
    its relationship Id -> Target map).

    `body_tag` is "body" for the main document, where paragraphs live one
    level down under <w:document><w:body>; None for header/footer parts,
    where <w:hdr>/<w:ftr> is itself the direct paragraph container.

    Returns (None, [], {}) if `xml_path` isn't present in the archive -
    not every .docx has a header/footer part.
    """
    xml_bytes = entries_by_name.get(xml_path)
    if xml_bytes is None:
        return None, [], {}

    root = etree.fromstring(xml_bytes)
    container = root.find(_w(body_tag)) if body_tag is not None else root
    assert container is not None, f"{xml_path} has no <w:{body_tag}>"
    paragraph_elements = container.findall(_w("p"))

    rels_bytes = entries_by_name.get(rels_path)
    rels = _parse_rels(rels_bytes) if rels_bytes is not None else {}

    return root, paragraph_elements, rels


class DocxEngine:
    """Implements pipeline.word.base.WordEngine by unzipping a .docx and
    parsing word/document.xml (body), word/header2.xml, and
    word/footer1.xml with lxml (see _HEADER_PATH/_FOOTER_PATH for why
    these two specific parts).
    """

    def __init__(self) -> None:
        """Nothing is loaded until open() is called."""
        self._paragraphs: list[WordParagraph] = []
        self._archive_entries: list[tuple[zipfile.ZipInfo, bytes]] = []
        """Every entry of the original .docx zip (ZipInfo + raw bytes),
        captured once at open() time rather than reopened from disk at
        save() time: the source path might move/vanish/change between
        open() and save(), a single read pass is simpler than two, and a
        .docx's total size (some MB at most - text, styles, a handful of
        images) is small enough to keep in memory for this project's
        single-document processing use case. save() copies every entry
        byte-for-byte except word/document.xml/header2.xml/footer1.xml,
        which are replaced with their current (possibly edited) trees -
        every other part (images/rels/styles/docProps/...) is never
        re-parsed or re-serialized, so no Word-internal quirk we don't
        understand risks being silently altered by a round trip through
        lxml."""
        self._root: etree._Element | None = None
        """The parsed word/document.xml tree - kept around (not just used
        to build self._paragraphs and discarded) so replace_paragraph_runs()
        can mutate the same live tree in place."""
        self._paragraph_elements: list[etree._Element] = []
        """The <w:p> elements backing self._paragraphs, same indexing -
        what replace_paragraph_runs() actually edits."""
        self._rels: dict[str, str] = {}
        """Relationship Id -> Target (word/_rels/document.xml.rels), kept
        for replace_paragraph_runs() to resolve/reuse hyperlink r:ids."""
        self._header_root: etree._Element | None = None
        self._header_paragraph_elements: list[etree._Element] = []
        self._header_rels: dict[str, str] = {}
        self._footer_root: etree._Element | None = None
        self._footer_paragraph_elements: list[etree._Element] = []
        self._footer_rels: dict[str, str] = {}
        """Same roles as the self._root/_paragraph_elements/_rels trio
        above, but for word/header2.xml and word/footer1.xml - None/empty
        if the .docx has no such part."""
        self.separator_found: bool = False
        """Whether a page-1 metadata separator shape (see
        _has_separator_shape()) was found on the most recent open() call -
        exposed for callers (e.g. tests/manual_inspect_word_blocks.py) to
        warn when a document doesn't follow the expected structure."""

    def open(self, path: str, ico_mode: bool = False) -> None:
        """Load a .docx document: unzip word/document.xml (+ its rels)
        plus, if present, word/header2.xml and word/footer1.xml (+ their
        rels), then build one WordParagraph per <w:p> in each.

        ``ico_mode`` gates the page-1 metadata block detection: it used to
        run unconditionally for every document, which meant any .docx that
        happened to contain a similar separator shape for unrelated reasons
        would silently lose part of its first page to translation. Now the
        scan for the separator shape (see _has_separator_shape()) only runs
        when the caller explicitly opts in via ico_mode=True (i.e. the user
        ticked the "ICO document" checkbox in ui/app.py for a document of
        that specific internal type) - every other document is translated
        in full, page 1 included. When ico_mode=True, body paragraphs
        before the first separator-shape paragraph are marked non-
        translatable; if no separator shape is found despite ico_mode=True,
        every body paragraph is left translatable=True and self.
        separator_found is False, letting the caller (ui/word_job.py) warn
        that the expected ICO structure wasn't actually present. See
        get_header_footer_paragraphs() for why header/footer paragraphs
        are always translatable=False, unconditionally (independent of
        ico_mode).
        """
        with zipfile.ZipFile(path) as archive:
            self._archive_entries = [
                (info, archive.read(info.filename)) for info in archive.infolist()
            ]

        entries_by_name = {info.filename: data for info, data in self._archive_entries}

        self._root, self._paragraph_elements, self._rels = _parse_part(
            entries_by_name, _DOCUMENT_PATH, _RELS_PATH, body_tag="body"
        )
        assert self._root is not None, f"{path} has no {_DOCUMENT_PATH}"

        self._header_root, self._header_paragraph_elements, self._header_rels = _parse_part(
            entries_by_name, _HEADER_PATH, _HEADER_RELS_PATH, body_tag=None
        )
        self._footer_root, self._footer_paragraph_elements, self._footer_rels = _parse_part(
            entries_by_name, _FOOTER_PATH, _FOOTER_RELS_PATH, body_tag=None
        )

        anchor_index = (
            next((i for i, p in enumerate(self._paragraph_elements) if _has_separator_shape(p)), None)
            if ico_mode
            else None
        )
        self.separator_found = anchor_index is not None

        self._paragraphs = [
            _build_paragraph(
                p, self._rels, translatable=(anchor_index is None or i >= anchor_index)
            )
            for i, p in enumerate(self._paragraph_elements)
        ]

    def get_paragraphs(self) -> list[WordParagraph]:
        """Return every paragraph in the document body, in reading order."""
        return self._paragraphs

    def get_header_paragraphs(self) -> list[WordParagraph]:
        """Just the header half of get_header_footer_paragraphs() below
        (see that method's docstring for the translatable=False
        rationale, unchanged here) - added 02.09.2026 for the new
        "Header"/"ICO Format" search scopes (extract_docx_header_text()/
        extract_docx_ico_header_text() below), which need the real
        word/header2.xml text WITHOUT the footer. Kept as its own method
        rather than filtering get_header_footer_paragraphs()'s combined
        result: that result deliberately doesn't tag which paragraphs
        came from which part, and re-deriving that here would be more
        fragile than reading self._header_paragraph_elements directly.
        """
        return [
            _build_paragraph(p, self._header_rels, translatable=False)
            for p in self._header_paragraph_elements
        ]

    def get_footer_paragraphs(self) -> list[WordParagraph]:
        """Just the footer half of get_header_footer_paragraphs() below -
        the exact mirror of get_header_paragraphs() above, added
        02.09.2026 for the date filter's "Datum im Dokument" source (see
        pipeline/date_extract.py): Michael, on that feature: "Das aber nur
        entweder im Header, im Footer oder im ICO Feld auf der ersten
        Seite." Kept as its own method for the same reason
        get_header_paragraphs() is - reading self._footer_paragraph_elements
        directly rather than re-deriving the header/footer split from
        get_header_footer_paragraphs()'s combined, untagged result.
        """
        return [
            _build_paragraph(p, self._footer_rels, translatable=False)
            for p in self._footer_paragraph_elements
        ]

    def get_header_footer_paragraphs(self) -> list[WordParagraph]:
        """Return every paragraph from the active default header
        (word/header2.xml) followed by every paragraph from the active
        default footer (word/footer1.xml) - [] for either part the
        document doesn't have.

        All of them are translatable=False: per requirement 1 of
        anforderungen_word_pfad.md, header/footer text must NOT be
        translated. (This method's docstring in the task that requested
        it described this as translatable=True, flagged as a deliberate
        planted error to check for during implementation - corrected to
        False here, which is the actually-required behavior.)
        """
        return self.get_header_paragraphs() + self.get_footer_paragraphs()

    def replace_paragraph_runs(self, paragraph_index: int, new_runs: list[WordRun]) -> None:
        """Replace the paragraph_index-th <w:p>'s runs (same indexing as
        get_paragraphs() - includes non-translatable paragraphs, so the
        index stays consistent) with `new_runs`, rebuilt as XML in the
        live document.xml tree. <w:pPr> (paragraph formatting) is left
        untouched; only <w:r>/<w:hyperlink> children are replaced, and the
        new elements are appended in `new_runs` order (after <w:pPr>,
        since that's the only thing left once the old runs are removed).

        Image runs (run.is_image) are matched 1:1, in document order,
        against the paragraph's ORIGINAL <w:drawing>- or <w:sym/>-bearing
        <w:r> elements and reused verbatim, never rebuilt - images (and
        symbol-font characters like Wingdings bullets, which _walk_run()
        treats identically - see that function's docstring) must not be
        touched structurally. Raises ValueError if new_runs has more
        image runs than the paragraph originally had (nothing to reuse -
        fabricating a new image run isn't supported).

        Hyperlink runs (run.is_hyperlink) reuse the r:id of an ORIGINAL
        <w:hyperlink> in this paragraph whose resolved target matches
        run.hyperlink_target, since the target itself never changes.
        Raises ValueError if no original hyperlink in this paragraph
        matches - adding a brand-new word/_rels/document.xml.rels entry
        isn't supported yet, so this fails loudly rather than guessing.

        Does not re-serialize/save the document - see document_xml_bytes()
        to inspect the result, and save() for writing a full .docx back
        out.
        """
        paragraph = self._paragraph_elements[paragraph_index]
        _replace_runs_in_paragraph(
            paragraph, self._rels, new_runs, f"replace_paragraph_runs({paragraph_index})"
        )

    def replace_header_footer_paragraph(
        self, source: str, paragraph_index: int, new_runs: list[WordRun]
    ) -> None:
        """Like replace_paragraph_runs(), but for a paragraph in the
        active default header (source="header", word/header2.xml) or
        footer (source="footer", word/footer1.xml) instead of the
        document body. `paragraph_index` indexes into that part's OWN
        paragraph list (the same order get_header_footer_paragraphs()
        yields header paragraphs, then footer paragraphs, in - so a
        caller iterating that combined list needs to track the header/
        footer split itself, e.g. via
        len(self._header_paragraph_elements)).

        Raises ValueError for an unknown `source`, or (via
        _replace_runs_in_paragraph()) for the same image-count/hyperlink-
        target-mismatch reasons replace_paragraph_runs() would.
        """
        if source == "header":
            paragraph = self._header_paragraph_elements[paragraph_index]
            rels = self._header_rels
        elif source == "footer":
            paragraph = self._footer_paragraph_elements[paragraph_index]
            rels = self._footer_rels
        else:
            raise ValueError(f"source must be 'header' or 'footer', got {source!r}")

        _replace_runs_in_paragraph(
            paragraph, rels, new_runs, f"replace_header_footer_paragraph({source!r}, {paragraph_index})"
        )

    def document_xml_bytes(self) -> bytes:
        """Serialize the current in-memory document.xml tree - including
        any replace_paragraph_runs() edits - back to bytes. Standalone
        helper for inspecting/testing edits before saving.
        """
        assert self._root is not None, "Document not opened. Call open() first."
        return _serialize(self._root)

    def save(self, output_path: str, overwrite: bool = False) -> None:
        """Write the current in-memory state - including any
        replace_paragraph_runs()/replace_header_footer_paragraph() edits -
        out as a new, valid .docx.

        Every zip entry from the original .docx (self._archive_entries,
        captured at open() time) is copied byte-for-byte except
        word/document.xml, word/header2.xml, and word/footer1.xml, which
        are replaced with their current live trees (the header/footer
        ones only if the .docx actually has that part - self._header_root/
        self._footer_root are None otherwise, and there's nothing to
        substitute). Entries are written back in their original order
        with their original ZipInfo (compression type, timestamps, ...)
        reused as-is - zipfile.writestr() recomputes size/CRC from the
        actual bytes being written regardless, so this is safe even for
        the replaced entries.

        Raises FileExistsError if `output_path` already exists and
        `overwrite` is not True, to avoid silently clobbering a file.
        """
        assert self._root is not None, "Document not opened. Call open() first."

        destination = Path(output_path)
        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"{output_path} already exists - pass overwrite=True to replace it."
            )

        replacements = {_DOCUMENT_PATH: self.document_xml_bytes()}
        if self._header_root is not None:
            replacements[_HEADER_PATH] = _serialize(self._header_root)
        if self._footer_root is not None:
            replacements[_FOOTER_PATH] = _serialize(self._footer_root)

        with zipfile.ZipFile(destination, "w") as archive:
            for info, data in self._archive_entries:
                data = replacements.get(info.filename, data)
                archive.writestr(info, data)


# --- DOCX-Dateien nach ICO-Kopfbereich durchsuchen (01.09.2026) -------------
#
# Michael, im direkten Anschluss an die gleichnamige PDF-Funktion
# (pipeline/pdf/pymupdf_engine.py::extract_ico_header_text()): "Jetzt noch
# das ganze für *.docx." ui/word_merge_search.py is the folder-walk/
# matching orchestration on top of this (mirrors ui/merge_search.py for
# PDF); this function is only the per-file extraction.


def extract_docx_ico_header_text(path: str) -> str | None:
    """"ICO Format" search scope (02.09.2026, renamed/extended from this
    function's original, body-only behavior) - the plain text of the
    real Word header (word/header2.xml, see get_header_paragraphs())
    PLUS every body paragraph BEFORE the page-1 metadata separator shape
    (see _has_separator_shape()) - the DOCX counterpart of
    extract_ico_header_text() in pipeline/pdf/pymupdf_engine.py, same
    "only the protected header/metadata region, never the rest of the
    document" contract. Returns None if no separator shape is found at
    all (most .docx files are not this internal document type - not an
    error) - regardless of whether the document happens to have header
    text, since header text alone doesn't make a document this internal
    type.

    02.09.2026 (Michael, Screenshot vom oberen Bereich einer echten
    ICO-Seite 1: "Developer: StellarRussia" / "QSI ICO: AUREXIS"): dieser
    Text steht im echten Word-Header (word/header2.xml - siehe
    tests/fixtures/representative_ico.docx, das genau so einen Header
    bereits enthält), nicht im Body. Vor dieser Änderung durchsuchte diese
    Funktion nur Body-Absätze - der Header wurde nie einbezogen, weshalb
    eine Suche nach "Developer" hier fehlschlug, obwohl das Wort sichtbar
    auf Seite 1 stand.

    Deliberately built on the full DocxEngine(ico_mode=True) rather than a
    bespoke, leaner parser the way extract_ico_header_text() is (see that
    function's docstring for why it avoids PyMuPdfEngine's overhead): a
    .docx's word/document.xml plus its header/footer parts are small XML
    payloads (kilobytes, not the page-by-page image/link scanning PDF's
    full engine does), so open()'s modest extra header/footer parsing here
    is not worth hand-rolling a second, separate DOCX parser for - reusing
    the same, already-tested DocxEngine/_has_separator_shape() this
    module's translation path already relies on is the safer choice.

    Raises ValueError (never a raw exception) if `path` can't be opened as
    a .docx at all (missing, corrupt, not actually a .docx) - the caller
    (ui/word_merge_search.py) turns that into a per-file, non-fatal error
    entry rather than aborting an entire folder scan over one bad file,
    exactly like the PDF search's identical error contract.
    """
    engine = DocxEngine()
    try:
        engine.open(path, ico_mode=True)
    except Exception as exc:  # noqa: BLE001 - re-raised as a clear, file-named ValueError below
        raise ValueError(f'"{Path(path).name}" konnte nicht geöffnet werden: {exc}') from exc

    if not engine.separator_found:
        return None

    metadata_paragraphs = [p for p in engine.get_paragraphs() if not p.translatable]
    all_paragraphs = engine.get_header_paragraphs() + metadata_paragraphs
    lines = [
        "".join(run.text for run in paragraph.runs).replace(BREAK_MARKER, " ").strip()
        for paragraph in all_paragraphs
    ]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else None


# --- "Header" (alle Seiten, normale Dokumente) und "Volltext" (02.09.2026) -
#
# Michael, im direkten Anschluss an obiges "ICO Format": "Genauso wie die
# Option 'nur im Header'. Dann sollte es auch möglich sein im ganzen Text
# suchen zu können." Auf Rückfrage bestätigt: bei normalen (nicht-ICO)
# Dokumenten muss der Header über ALLE Seiten durchsucht werden - anders
# als bei der PDF-Fassung braucht das hier KEINE eigene Erkennung: ein
# Word-Header (word/header2.xml) gilt strukturell schon für jede Seite
# eines Abschnitts, siehe get_header_paragraphs().


def extract_docx_header_text(path: str) -> str | None:
    """"Header" search scope (02.09.2026) for normal (non-ICO) documents -
    Michael: "Bei normalen Dokumenten müssen es die Header aller Seiten
    sein." Word's header applies structurally to every page in a section
    (word/header2.xml, see get_header_paragraphs()'s docstring) - unlike
    the PDF equivalent (extract_pdf_header_text() in pipeline/pdf/
    pymupdf_engine.py), no cross-page repetition detection is needed
    here, so this stays a cheap, single open() + one small XML-part read
    regardless of document length. ico_mode is left at its default False:
    the page-1 separator-shape scan is irrelevant to this scope.

    Returns None if the document has no header part at all, or an empty
    one - most .docx files legitimately don't use a Word header.

    Raises ValueError (never a raw exception) if `path` can't be opened
    as a .docx at all - same contract as extract_docx_ico_header_text().
    """
    engine = DocxEngine()
    try:
        engine.open(path)
    except Exception as exc:  # noqa: BLE001 - re-raised as a clear, file-named ValueError below
        raise ValueError(f'"{Path(path).name}" konnte nicht geöffnet werden: {exc}') from exc

    lines = [
        "".join(run.text for run in paragraph.runs).replace(BREAK_MARKER, " ").strip()
        for paragraph in engine.get_header_paragraphs()
    ]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else None


def extract_docx_footer_text(path: str) -> str | None:
    """Footer text extraction (02.09.2026, Datumsfilter) - the exact
    mirror of extract_docx_header_text() above, just for
    get_footer_paragraphs() (word/footer1.xml) instead of
    get_header_paragraphs(). Used by the date filter's "Datum im
    Dokument" source (see pipeline/date_extract.py), not by the general
    free-text search scopes - Michael never asked for a general "Footer"
    text-search scope, only for the date filter to be able to look there
    (see pipeline/pdf/pymupdf_engine.py::extract_pdf_footer_text()'s
    identical comment).

    Returns None if the document has no footer part at all, or an empty
    one - most .docx files legitimately don't use a Word footer.

    Raises ValueError (never a raw exception) if `path` can't be opened
    as a .docx at all - same contract as extract_docx_ico_header_text().
    """
    engine = DocxEngine()
    try:
        engine.open(path)
    except Exception as exc:  # noqa: BLE001 - re-raised as a clear, file-named ValueError below
        raise ValueError(f'"{Path(path).name}" konnte nicht geöffnet werden: {exc}') from exc

    lines = [
        "".join(run.text for run in paragraph.runs).replace(BREAK_MARKER, " ").strip()
        for paragraph in engine.get_footer_paragraphs()
    ]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else None


def extract_docx_full_text(path: str) -> str | None:
    """"Volltext" search scope (02.09.2026) - every body paragraph plus
    the header, in reading order (header first, matching how it visually
    sits above the body). Confirmed as the deliberate superset (Michael:
    "Wenn ich also im ganzen Dokument suche ist alles inklusive Header
    und oberer Bereich 1. Seite"), so this makes no attempt to exclude
    anything extract_docx_ico_header_text()/extract_docx_header_text()
    above already cover. ico_mode is left at its default False: the
    page-1 translatable/metadata split is irrelevant to a plain full-text
    search.

    Raises ValueError (never a raw exception) if `path` can't be opened
    as a .docx at all - same contract as extract_docx_ico_header_text().
    """
    engine = DocxEngine()
    try:
        engine.open(path)
    except Exception as exc:  # noqa: BLE001 - re-raised as a clear, file-named ValueError below
        raise ValueError(f'"{Path(path).name}" konnte nicht geöffnet werden: {exc}') from exc

    all_paragraphs = engine.get_header_paragraphs() + engine.get_paragraphs()
    lines = [
        "".join(run.text for run in paragraph.runs).replace(BREAK_MARKER, " ").strip()
        for paragraph in all_paragraphs
    ]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else None
