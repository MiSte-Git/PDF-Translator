"""Builds a "side-by-side" variant of a translated Word document: a
two-column (Original | Übersetzung) landscape table, one row per body
paragraph, instead of the normal in-place, layout-preserving output.

03.09.2026 (Michael, im selben Zug wie die Datumsfilter-Persistenz):
"Können wir auch noch beim Übersetzen die Option anbieten das der
Original und der Übersetzte Text nebeneinander angezeigt werden? Im
Projekt 'Telegram Nachrichten kopieren' haben wir das schon
implementiert. Kannst Du Dir das mal ansehen und schauen was wir davon
gebrauchen können und es übernehmen oder verbessern." Rückfrage/
Antwort (AskUserQuestion): Kopf-/Fußzeile bleiben unverändert wie im
Original (Word zeigt ohnehin dieselbe Kopf-/Fußzeile auf jeder Seite -
dafür ist hier nichts extra nötig, siehe DocxEngine.save(), das
word/header2.xml/footer1.xml unangetastet übernimmt); nur der BODY
wird zu einer Zweispaltentabelle, das Dokument wird dafür auf
Querformat umgestellt, damit beide Spalten lesbar bleiben (siehe die
Telegram-App's eigene Begründung dafür in odt_writer.py:
_PAGE_USABLE_WIDTH_LANDSCAPE_CM). Die Option ist ein ZUSÄTZLICHER
Modus ("nebeneinander"), kein Ersatz für den bisherigen layoutgetreuen
Modus ("normal") - siehe ui/models.py's TranslationRequest.side_by_side
und ui/app.py's Checkbox. Vorerst nur für Word (Michael: "Nur Word") -
PDF/PPTX folgen bei Bedarf.

Was aus der Telegram-App ("Projekt 'Telegram Nachrichten kopieren'",
pipeline/odt_writer.py) übernommen wurde: die Grundidee einer
zweispaltigen Tabelle (eine Spalte Original, eine Spalte Übersetzung),
Querformat für die nutzbare Breite, und eine spaltenübergreifende Zeile
für Inhalte, die nicht paarweise Original/Übersetzung sind (dort:
Metadaten-Kopfzeile pro Nachricht; hier: der Word-Header ist ohnehin
unverändert, aber das ICO-Seite-1-Metadatenfeld bzw. eine leere
Absatzzeile bekommt dieselbe Behandlung). NICHT übernommen: odfpy/ODT
als Ausgabeformat (dieses Projekt bleibt bei .docx/python-docx und dem
bestehenden In-place-XML-Ansatz von DocxEngine), und der komplette
Neuaufbau des Dokuments von Grund auf - hier wird stattdessen eine
echte .docx-Quelle weiterverwendet: Kopf-/Fußzeile und alle
Dokumenteigenschaften bleiben die des Originals, nur der Haupttext wird
zur Tabelle umgebaut.

Anders als pipeline.word.merge (das mehrere ganze Dokumente
zusammenführt) oder DocxEngine.replace_paragraph_runs() (das einzelne
Absätze in-place ersetzt, ohne die Body-STRUKTUR selbst zu verändern),
ersetzt build_side_by_side_body() unten die komplette
<w:body>-Absatzfolge durch eine neu aufgebaute <w:tbl>.

Bekannte, bewusst dokumentierte Einschränkung (RoadMap.md-Stil - nicht
versteckt): Original-<w:tbl>-Elemente, die direkt im Haupttext stehen
(z. B. eine eingebettete Tabelle), werden von DocxEngine.get_paragraphs()
gar nicht erst erfasst (nur die <w:p>-Kindelemente von <w:body>) und
tauchen deshalb auch im Nebeneinander-Layout nicht auf - wie im
normalen Modus bleiben sie im XML-Baum stehen, werden hier aber beim
Body-Ersatz mit entfernt. Für ein reines Fließtext-Dokument (der
Regelfall laut anforderungen_word_pfad.md) hat das keine Auswirkung.

03.09.2026, Regression an einem echten, zuvor gemergten Mehrfach-ICO-
Dokument (Michael: "Wenn 'Nebeneinander' ausgewählt ist, ist das
Dokument nicht im Landscape Modus. Die erste Seite wird komischer
weise auf der 2. Noch mal wiederholt und der Header ist wieder bei
allen gleich."): pipeline.word.merge fügt mehrere Quelldokumente per
Abschnittsumbruch zusammen (siehe merge.py), jedes mit einer eigenen
<w:sectPr> (und damit eigenem Header/Footer) - ein solcher
Abschnittsumbruch sitzt als <w:sectPr> im <w:pPr> GENAU des Absatzes,
an dem der Abschnitt endet (nur der ALLERLETZTE Abschnitt hat seine
<w:sectPr> stattdessen direkt als Kind von <w:body>, siehe OOXML-
Schema). Die erste Version dieses Moduls kannte nur DIESEN einen,
körpernahen <w:body>->sectPr-Fall und behandelte jeden Absatz
gleich - das verschob jede Abschnittsumbruch-<w:sectPr> in eine
Tabellenzelle hinein, wo ein Abschnittsumbruch strukturell ungültig
ist (Word/LibreOffice reagieren darauf mit genau den gemeldeten
Symptomen: nur der letzte Abschnitt wurde tatsächlich Querformat, die
Seiten-1-Inhalte tauchten doppelt/verschoben auf, und da keine echte
Abschnittsgrenze mehr existierte, griff für alle Seiten derselbe
Header). Behoben durch _section_ranges()/die Section-für-Section-
Schleife in build_side_by_side_body() unten: JEDE Abschnittsgrenze
bekommt jetzt ihre eigene, echte, körperständige (nicht in einer
Tabellenzelle liegende) <w:sectPr> - eine eigene Tabelle pro
Originalabschnitt, jeweils gefolgt vom (jetzt quer gestellten)
Abschnittsumbruch an genau der Stelle, wo er vorher stand. Ergänzend
_renumber_doc_pr_ids(): an demselben Dokument fielen zudem doppelte
wp:docPr-Ids in word/document.xml auf (vermutlich vorbestehend aus
merge.py - jede gemergte Quelle scheint ihre Trennlinien-Form-Id
unabhängig bei 1 zu beginnen; von dieser Änderung hier unberührt,
da nichts hier Absätze dupliziert) - defensiv neu durchnummeriert,
damit ein Nebeneinander-Rebuild dieses Symptom zumindest nicht
weiterträgt.
"""
from __future__ import annotations

import copy

from lxml import etree

from pipeline.word.base import BREAK_MARKER, WordRun
from pipeline.word.docx_engine import (
    DocxEngine,
    _R_NS,
    _build_break_run,
    _build_hyperlink_element,
    _build_text_run,
    _inline_section_break,
    _section_ranges,
    _w,
    _walk_run,
)

_XML_SPACE_ATTR = "{http://www.w3.org/XML/1998/namespace}space"

# Fallback nutzbare Breite (twips, 1 cm = 567 twips) falls das Dokument
# keine <w:sectPr>/<w:pgSz> hat (in der Praxis nicht erwartet, aber
# defensiv statt eines harten Fehlers) - ~24cm, plausibel für A4 quer
# minus Rand.
_FALLBACK_USABLE_WIDTH_TWIPS = 13_600

_HEADER_SHADE = "D9E2F3"

_WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

# Start offset for _renumber_doc_pr_ids() - see this module's docstring.
_DOC_PR_ID_START = 900_000


def _set_landscape(sect_pr: etree._Element) -> None:
    """Swap the body's <w:sectPr>'s <w:pgSz> width/height and mark it
    landscape - matches the Telegram project's own rationale (zwei
    Spalten passen auf Hochformat-Breite nicht lesbar nebeneinander).
    Also swaps the page's top/bottom vs. left/right margins in
    <w:pgMar>, so the (originally narrow) side margins don't end up
    running along the new, long top/bottom edge.
    """
    pg_sz = sect_pr.find(_w("pgSz"))
    if pg_sz is not None:
        width, height = pg_sz.get(_w("w")), pg_sz.get(_w("h"))
        if width is not None and height is not None:
            pg_sz.set(_w("w"), height)
            pg_sz.set(_w("h"), width)
        pg_sz.set(_w("orient"), "landscape")

    pg_mar = sect_pr.find(_w("pgMar"))
    if pg_mar is not None:
        for a, b in (("top", "left"), ("bottom", "right")):
            value_a, value_b = pg_mar.get(_w(a)), pg_mar.get(_w(b))
            if value_a is not None and value_b is not None:
                pg_mar.set(_w(a), value_b)
                pg_mar.set(_w(b), value_a)


def _usable_width_twips(sect_pr: etree._Element | None) -> int:
    """Page width minus left/right margins, in twips - called AFTER
    _set_landscape() so pgSz already reflects the new (wider) landscape
    dimensions."""
    if sect_pr is None:
        return _FALLBACK_USABLE_WIDTH_TWIPS
    pg_sz = sect_pr.find(_w("pgSz"))
    pg_mar = sect_pr.find(_w("pgMar"))
    if pg_sz is None:
        return _FALLBACK_USABLE_WIDTH_TWIPS
    try:
        width = int(pg_sz.get(_w("w")))
        left = int(pg_mar.get(_w("left"))) if pg_mar is not None and pg_mar.get(_w("left")) else 0
        right = int(pg_mar.get(_w("right"))) if pg_mar is not None and pg_mar.get(_w("right")) else 0
        usable = width - left - right
        return usable if usable > 1000 else _FALLBACK_USABLE_WIDTH_TWIPS
    except (TypeError, ValueError):
        return _FALLBACK_USABLE_WIDTH_TWIPS


def _paragraph_is_empty(paragraph: etree._Element) -> bool:
    """Whether `paragraph` has no <w:r>/<w:hyperlink> content at all - used
    to skip emitting a visible (empty, spanning) row for a section-break
    paragraph that carries nothing but the break itself (the common case:
    pipeline.word.merge inserts a dedicated, otherwise-empty paragraph to
    hold each section break). A section-break paragraph that DOES also
    carry real text is still shown normally.
    """
    return paragraph.find(_w("r")) is None and paragraph.find(_w("hyperlink")) is None


def _renumber_doc_pr_ids(body: etree._Element) -> None:
    """Assign fresh, sequential wp:docPr ids (drawing/shape anchors) to
    every one left in the rebuilt body, starting from a high offset to
    stay clear of whatever ids header/footer parts already use (see this
    module's docstring: docxcompose renumbers those during merge.py's own
    merge, body-level shapes apparently not). Purely defensive
    normalization - see the docstring for why any duplicates here are
    very unlikely to be caused by THIS module.
    """
    next_id = _DOC_PR_ID_START
    for doc_pr in body.iter(f"{{{_WP_NS}}}docPr"):
        doc_pr.set("id", str(next_id))
        next_id += 1


def _build_section_table(usable_width: int, column_width: int, target_lang: str) -> etree._Element:
    """A fresh, empty two-column comparison table (borders, style, the
    "Original"/"Übersetzung (...)" header row) for one section - factored
    out of build_side_by_side_body() so a multi-section document (see
    this module's docstring) gets one such table per original section
    instead of one giant table spanning section boundaries it can't
    actually represent.
    """
    table = etree.Element(_w("tbl"))
    tbl_pr = etree.SubElement(table, _w("tblPr"))
    tbl_style = etree.SubElement(tbl_pr, _w("tblStyle"))
    tbl_style.set(_w("val"), "TableGrid")
    tbl_w = etree.SubElement(tbl_pr, _w("tblW"))
    tbl_w.set(_w("w"), str(usable_width))
    tbl_w.set(_w("type"), "dxa")
    tbl_borders = etree.SubElement(tbl_pr, _w("tblBorders"))
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = etree.SubElement(tbl_borders, _w(edge))
        border.set(_w("val"), "single")
        border.set(_w("sz"), "4")
        border.set(_w("space"), "0")
        border.set(_w("color"), "BFBFBF")
    tbl_look = etree.SubElement(tbl_pr, _w("tblLook"))
    tbl_look.set(_w("val"), "04A0")
    tbl_look.set(_w("firstRow"), "1")
    tbl_look.set(_w("noHBand"), "0")
    tbl_look.set(_w("noVBand"), "1")

    grid = etree.SubElement(table, _w("tblGrid"))
    for _ in range(2):
        col = etree.SubElement(grid, _w("gridCol"))
        col.set(_w("w"), str(column_width))

    table.append(_row([
        _cell(column_width, [_label_paragraph("Original")], shade=_HEADER_SHADE),
        _cell(column_width, [_label_paragraph(f"Übersetzung ({target_lang})")], shade=_HEADER_SHADE),
    ]))
    return table


def _cell(width_twips: int, paragraph_elements: list[etree._Element], span: int = 1, shade: str | None = None) -> etree._Element:
    tc = etree.Element(_w("tc"))
    tc_pr = etree.SubElement(tc, _w("tcPr"))
    tc_w = etree.SubElement(tc_pr, _w("tcW"))
    tc_w.set(_w("w"), str(width_twips))
    tc_w.set(_w("type"), "dxa")
    if span > 1:
        grid_span = etree.SubElement(tc_pr, _w("gridSpan"))
        grid_span.set(_w("val"), str(span))
    if shade is not None:
        shd = etree.SubElement(tc_pr, _w("shd"))
        shd.set(_w("val"), "clear")
        shd.set(_w("color"), "auto")
        shd.set(_w("fill"), shade)
    if paragraph_elements:
        for element in paragraph_elements:
            tc.append(element)
    else:
        # A <w:tc> without at least one <w:p> is invalid OOXML.
        etree.SubElement(tc, _w("p"))
    return tc


def _row(cells: list[etree._Element]) -> etree._Element:
    tr = etree.Element(_w("tr"))
    for cell in cells:
        tr.append(cell)
    return tr


def _label_paragraph(text: str) -> etree._Element:
    p = etree.Element(_w("p"))
    r = etree.SubElement(p, _w("r"))
    r_pr = etree.SubElement(r, _w("rPr"))
    etree.SubElement(r_pr, _w("b"))
    t = etree.SubElement(r, _w("t"))
    t.set(_XML_SPACE_ATTR, "preserve")
    t.text = text
    return p


def _translated_paragraph_element(
    original_paragraph: etree._Element,
    rels: dict[str, str],
    new_runs: list[WordRun],
) -> etree._Element:
    """A fresh <w:p>, reusing `original_paragraph`'s <w:pPr> (deep-copied,
    so alignment/indentation/style survive) with `new_runs` as its
    content - the read-only counterpart of DocxEngine.
    _replace_runs_in_paragraph(), which mutates an existing paragraph in
    place instead of building a brand-new, separate one.
    """
    p = etree.Element(_w("p"))
    p_pr = original_paragraph.find(_w("pPr"))
    if p_pr is not None:
        p.append(copy.deepcopy(p_pr))

    original_image_runs = [r for r in original_paragraph.findall(_w("r")) if _walk_run(r)[1]]
    image_iter = iter(original_image_runs)

    target_to_rid: dict[str, str] = {}
    for hyperlink in original_paragraph.findall(_w("hyperlink")):
        rid = hyperlink.get(f"{{{_R_NS}}}id")
        target = rels.get(rid)
        if target is not None:
            target_to_rid[target] = rid

    for run in new_runs:
        if run.is_image:
            try:
                p.append(copy.deepcopy(next(image_iter)))
            except StopIteration:
                # More image runs than the original paragraph had - can't
                # fabricate a new image structurally (mirrors
                # DocxEngine.replace_paragraph_runs()'s same limit), just
                # drop it rather than raising: a side-by-side comparison
                # view is best-effort, not the authoritative output.
                continue
            continue
        if run.text == BREAK_MARKER:
            p.append(_build_break_run())
            continue
        if run.is_hyperlink:
            rid = target_to_rid.get(run.hyperlink_target or "")
            if rid is not None:
                p.append(_build_hyperlink_element(rid, run))
                continue
            # No matching original hyperlink to reuse the r:id from - fall
            # through and render as plain text rather than raising, same
            # best-effort reasoning as the image case above.
        p.append(_build_text_run(run))

    return p


def capture_original_paragraph_elements(engine: DocxEngine) -> list[etree._Element]:
    """Deep-copy every current body <w:p> element, BEFORE
    translate_document() is run. Must be called right after engine.open()
    (or at least before translate_document()): translate_document()'s
    replace_paragraph_runs() mutates engine's live XML tree in place
    (engine._paragraph_elements), which is what engine.get_paragraphs()'s
    WordParagraph dataclasses are built FROM but never point back into -
    so by the time a caller reaches build_side_by_side_body() further
    below, engine._paragraph_elements no longer holds the original,
    untranslated XML (a real symptom this shipped with once: the "Original"
    column showed already-translated text, caught by
    tests/test_word_side_by_side.py). The plain WordRun-level content is
    still available afterwards via engine.get_paragraphs() (untouched),
    but the actual XML structure - <w:pPr>, image runs, hyperlink
    relationships - is not, and rebuilding the left/original column
    needs that structure verbatim, not just its text.
    """
    return [copy.deepcopy(element) for element in engine._paragraph_elements]


def build_side_by_side_body(
    engine: DocxEngine,
    original_paragraph_elements: list[etree._Element],
    translated_runs_by_index: dict[int, list[WordRun]],
    target_lang: str,
) -> None:
    """Replace `engine`'s in-memory body (word/document.xml's <w:body>)
    with a two-column (Original | Übersetzung) table, one row per body
    paragraph. Mutates `engine` in place - call this AFTER
    translate_document() (with a `translated_runs` dict passed to it, see
    that function's docstring) and BEFORE engine.save().

    `original_paragraph_elements` must be the result of
    capture_original_paragraph_elements(engine), called BEFORE
    translate_document() - see that function's docstring for why engine's
    own, live _paragraph_elements can no longer be used for this by the
    time translate_document() has run.

    `translated_runs_by_index` maps a body paragraph index (same
    indexing as engine.get_paragraphs()) to the WordRun list that
    paragraph was actually translated to. A paragraph with no entry
    (never translated: not translatable, or empty/whitespace-only) is
    rendered as a single, spanning row showing the original text once,
    instead of duplicating identical text into both columns.

    Header/footer are left completely untouched (see this module's
    docstring) - only each section's own <w:sectPr> is adjusted to
    landscape, since header/footer live in their own separate parts
    (word/header2.xml/word/footer1.xml, one set per section on a
    previously merged multi-source document) unaffected by a section's
    page orientation.

    A document with MULTIPLE sections (e.g. produced by pipeline.word.
    merge - see this module's 03.09.2026 docstring entry) gets one
    separate comparison table per original section, each followed by its
    own (now-landscaped) section break, exactly where that break
    originally sat - never one single table spanning several sections,
    which would trap a section-break paragraph inside a table cell
    (structurally invalid, and the actual root cause of the 03.09.2026
    bug report this fix addresses).
    """
    assert engine._root is not None, "Document not opened."
    body = engine._root.find(_w("body"))
    assert body is not None, "word/document.xml has no <w:body>"

    final_sect_pr = body.find(_w("sectPr"))
    if final_sect_pr is not None:
        body.remove(final_sect_pr)  # re-appended per-section below (schema order)

    # Removes the CURRENT (already-translated) body paragraphs, not
    # `original_paragraph_elements` - those are separate, detached deep
    # copies (see capture_original_paragraph_elements()), never part of
    # `body` to begin with.
    for element in list(engine._paragraph_elements):
        body.remove(element)

    for indices, inline_sect_pr in _section_ranges(original_paragraph_elements):
        governing_sect_pr = inline_sect_pr if inline_sect_pr is not None else final_sect_pr
        # A private, landscaped COPY of whichever sectPr governs this
        # section - only used for width/orientation and as this
        # section's own terminator below. The ORIGINAL inline_sect_pr
        # element (still living inside its paragraph's <w:pPr> in
        # original_paragraph_elements) is left untouched here; it gets
        # stripped from a dedicated cell-only copy in the loop below
        # instead, since a section break cannot live inside a table cell.
        landscape_sect_pr = copy.deepcopy(governing_sect_pr) if governing_sect_pr is not None else None
        if landscape_sect_pr is not None:
            _set_landscape(landscape_sect_pr)
        usable_width = _usable_width_twips(landscape_sect_pr)
        column_width = usable_width // 2

        if indices:
            table = _build_section_table(usable_width, column_width, target_lang)
            for index in indices:
                original_element = original_paragraph_elements[index]
                cell_source = original_element
                if _inline_section_break(original_element) is not None:
                    # This IS the section-break paragraph itself - use a
                    # separate copy with the sectPr stripped out for the
                    # cell; the break itself is re-attached as this
                    # section's own terminator further below instead.
                    cell_source = copy.deepcopy(original_element)
                    cell_p_pr = cell_source.find(_w("pPr"))
                    cell_p_pr.remove(cell_p_pr.find(_w("sectPr")))
                    if _paragraph_is_empty(cell_source):
                        # The common case: a dedicated, otherwise-empty
                        # paragraph holding just the section break - the
                        # break itself is still emitted below either way,
                        # skip only the pointless empty row it would
                        # otherwise leave behind in this section's table.
                        continue
                new_runs = translated_runs_by_index.get(index)
                if new_runs is None:
                    # Not actually translated (ICO-Metadatenbereich,
                    # Leerzeile, nicht-übersetzbarer Absatz, ...) - eine
                    # spaltenübergreifende Zeile statt identischem
                    # Original-Text doppelt in beiden Spalten.
                    table.append(_row([_cell(usable_width, [copy.deepcopy(cell_source)], span=2)]))
                    continue
                translated_element = _translated_paragraph_element(cell_source, engine._rels, new_runs)
                table.append(_row([
                    _cell(column_width, [copy.deepcopy(cell_source)]),
                    _cell(column_width, [translated_element]),
                ]))
            body.append(table)

        if inline_sect_pr is not None:
            # This section's own break, as its own body-level paragraph -
            # exactly where the original section break sat, one per
            # merged source document.
            closing = etree.SubElement(body, _w("p"))
            closing_p_pr = etree.SubElement(closing, _w("pPr"))
            if landscape_sect_pr is not None:
                closing_p_pr.append(landscape_sect_pr)
        else:
            # The FINAL section's sectPr is never wrapped in a paragraph -
            # it's body's own trailing, direct child, per the OOXML
            # schema (w:body's content model: any number of w:p/w:tbl,
            # then exactly one trailing w:sectPr). A table that ends the
            # body must be followed by at least one <w:p> first (some
            # Word/LibreOffice versions render/behave oddly otherwise).
            etree.SubElement(body, _w("p"))
            if landscape_sect_pr is not None:
                body.append(landscape_sect_pr)
            else:
                etree.SubElement(body, _w("sectPr"))

    _renumber_doc_pr_ids(body)
