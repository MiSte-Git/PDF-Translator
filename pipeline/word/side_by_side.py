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
    docstring) - only the body's own <w:sectPr> is adjusted to
    landscape, since header/footer live in their own separate parts
    (word/header2.xml/word/footer1.xml) unaffected by the body's page
    orientation.
    """
    assert engine._root is not None, "Document not opened."
    body = engine._root.find(_w("body"))
    assert body is not None, "word/document.xml has no <w:body>"

    original_paragraphs = engine.get_paragraphs()

    sect_pr = body.find(_w("sectPr"))
    if sect_pr is not None:
        _set_landscape(sect_pr)
        body.remove(sect_pr)  # re-appended last, after every row (schema order)
    usable_width = _usable_width_twips(sect_pr)
    column_width = usable_width // 2

    # Removes the CURRENT (already-translated) body paragraphs, not
    # `original_paragraph_elements` - those are separate, detached deep
    # copies (see capture_original_paragraph_elements()), never part of
    # `body` to begin with.
    for element in list(engine._paragraph_elements):
        body.remove(element)

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

    for index, (original_element, paragraph) in enumerate(zip(original_paragraph_elements, original_paragraphs)):
        new_runs = translated_runs_by_index.get(index)
        if new_runs is None:
            # Not actually translated (ICO-Metadatenbereich, Leerzeile,
            # nicht-übersetzbarer Absatz, ...) - eine spaltenübergreifende
            # Zeile statt identischem Original-Text doppelt in beiden
            # Spalten.
            table.append(_row([_cell(usable_width, [copy.deepcopy(original_element)], span=2)]))
            continue
        translated_element = _translated_paragraph_element(original_element, engine._rels, new_runs)
        table.append(_row([
            _cell(column_width, [copy.deepcopy(original_element)]),
            _cell(column_width, [translated_element]),
        ]))

    body.append(table)
    # A table that ends the body must be followed by at least one <w:p>
    # (some Word/LibreOffice versions render/behave oddly on a body whose
    # very last child is a <w:tbl>), then the <w:sectPr> - required last
    # per the OOXML schema's w:body content model (any number of
    # w:p/w:tbl, then exactly one trailing w:sectPr).
    etree.SubElement(body, _w("p"))
    if sect_pr is not None:
        body.append(sect_pr)
    else:
        etree.SubElement(body, _w("sectPr"))
