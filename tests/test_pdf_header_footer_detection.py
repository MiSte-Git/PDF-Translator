"""Regression coverage for detect_header_footer_zones() (pipeline/pdf/
template.py), built while fixing a real bug the user hit on a live run
against the real "1526 VIRELICON.pdf": the direct PDF UI path
(ui/pdf_job.py::run_pdf_job()) never loaded a DocumentTemplate, so the
document's header ("Developer: StellarRussia QSI ICO: ...", repeated on
every page) got translated along with the body text, even though a
manually-authored template for this exact document already existed
(templates/virelicon.json) - it just was never wired into the UI flow.

Rather than only fixing the wiring for this one document, this adds a
GENERIC detector: find text that repeats, at roughly the same page
position, across a majority of pages near the top (header) or bottom
(footer) - so any document gets the same protection without a hand-built
template file, backing the new "Header ausschließen"/"Footer ausschließen"
checkboxes in the PDF UI (see ui/app.py/ui/pdf_job.py).

Every test builds its own synthetic multi-page PDF directly with fitz
(same established pattern as tests/test_pdf_redact_insert_collision.py
and friends), since the real, confidential source document isn't
available in this environment.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from pipeline.pdf.template import DocumentTemplate, detect_header_footer_zones


def _build_document(path: Path, pages: int = 6, header_on_every_page: bool = True) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=400, height=500)
        if header_on_every_page:
            page.insert_textbox(fitz.Rect(20, 20, 380, 40), "Developer: Acme Corp Header Line",
                                 fontsize=10, fontname="helv")
        page.insert_textbox(fitz.Rect(20, 100, 380, 400),
                             f"Body paragraph number {i} with unique content that changes every page.",
                             fontsize=11, fontname="helv")
        page.insert_textbox(fitz.Rect(20, 470, 300, 485), "Copyright 2025 Acme Corp", fontsize=8, fontname="helv")
        page.insert_textbox(fitz.Rect(370, 470, 390, 485), str(i + 1), fontsize=8, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_detects_repeated_header_and_footer_including_page_number(tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    _build_document(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    header, footer = detect_header_footer_zones(engine)

    assert header is not None
    assert header[1] < 50  # near the top

    assert footer is not None
    assert footer[3] > 460  # near the bottom
    # The lone page-number block ("1", "2", ...) has no stable text across
    # pages but a stable position - must still be folded into the footer
    # bbox via position-based grouping, not just text-based.
    assert footer[2] >= 370  # footer bbox reaches out to the page-number block's x-position


def test_body_text_never_misdetected_as_header_or_footer(tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    _build_document(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    header, footer = detect_header_footer_zones(engine)

    body_bbox = (20.0, 100.0, 380.0, 400.0)
    from pipeline.pdf.template import block_overlaps
    assert header is None or not block_overlaps(body_bbox, header)
    assert footer is None or not block_overlaps(body_bbox, footer)


def test_no_repeating_header_or_footer_returns_none(tmp_path: Path) -> None:
    # Genuinely different chapter titles - different wording AND different
    # rendered length/position (not just a single digit swapped inside an
    # otherwise-fixed template), so neither the text-repetition nor the
    # position-repetition signal should fire.
    titles = [
        "Introduction",
        "A Rather Long Methodology Section Overview",
        "Results",
        "Discussion And Broader Implications For The Field",
        "Conclusion",
        "Appendix: Supplementary Material And Notes",
    ]
    source = tmp_path / "doc.pdf"
    doc = fitz.open()
    for i, title in enumerate(titles):
        page = doc.new_page(width=400, height=500)
        page.insert_textbox(fitz.Rect(20, 20, 380, 40), title, fontsize=10, fontname="helv")
        page.insert_textbox(fitz.Rect(20, 100, 380, 400), f"Body paragraph {i}.", fontsize=11, fontname="helv")
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source))
    header, footer = detect_header_footer_zones(engine)

    assert header is None
    assert footer is None


def test_header_below_min_page_fraction_is_not_detected(tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    doc = fitz.open()
    for i in range(6):
        page = doc.new_page(width=400, height=500)
        if i == 0:  # only the FIRST page has this text - not a real repeating header
            page.insert_textbox(fitz.Rect(20, 20, 380, 40), "One-off cover title", fontsize=10, fontname="helv")
        page.insert_textbox(fitz.Rect(20, 100, 380, 400), f"Body paragraph {i}.", fontsize=11, fontname="helv")
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source))
    header, _ = detect_header_footer_zones(engine)

    assert header is None


def test_detected_zones_correctly_exclude_header_footer_blocks_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    _build_document(source)

    detect_engine = PyMuPdfEngine()
    detect_engine.open(str(source))
    header, footer = detect_header_footer_zones(detect_engine)

    template = DocumentTemplate(name="detected", header_bbox=header, footer_bbox=footer)
    engine = PyMuPdfEngine(template=template)
    engine.open(str(source))
    blocks = engine.extract_blocks(0)

    by_text = {b.text: b.translatable for b in blocks}
    assert by_text["Developer: Acme Corp Header Line"] is False
    assert by_text["Copyright 2025 Acme Corp"] is False
    assert by_text["1"] is False
    assert by_text["Body paragraph number 0 with unique content that changes every page."] is True


def test_empty_document_returns_none_without_crashing() -> None:
    class EmptyEngine:
        def get_pages(self):
            return []

        def extract_blocks(self, page_index):
            return []

    header, footer = detect_header_footer_zones(EmptyEngine())
    assert header is None
    assert footer is None
