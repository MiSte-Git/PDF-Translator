"""Regression coverage for PDF's "ICO document" special case (RoadMap.md
Phase 2/PDF), added on direct user request after the underlying
FIRST_PAGE_ANCHOR_TERMS/_split_first_page_metadata() split (in
pipeline/pdf/pymupdf_engine.py) was found to still run UNCONDITIONALLY
for every PDF - meaning any document that happened to contain a line
matching an anchor term (e.g. "Issuer Address") for unrelated reasons
would silently lose that part of its first page to translation, exactly
the class of bug DocxEngine.open()'s ico_mode was already built to avoid
for Word (see that docstring). Mirrors tests/test_word_job.py's
ico_mode coverage: false (default, full document), true-and-found
(metadata excluded), true-and-not-found (warned, nothing excluded).

The synthetic fixture PDFs below use page.insert_text() at manually
controlled y-coordinates (one call per line, uniform spacing) rather than
page.insert_textbox() with "\\n\\n" - confirmed by direct inspection that
insert_textbox() splits on a blank-line paragraph gap into TWO separate
raw PyMuPDF blocks, while _split_first_page_metadata() only ever sees ONE
block's lines (the shape actually observed in the real, confidential
"1526 VIRELICON.pdf" this whole mechanism was built for - metadata line,
address line, blank line, title line, all inside one PyMuPDF block).
insert_text() per line reproduces that single-block, blank-line-as-a-line
shape directly.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pipeline.pdf.pymupdf_engine import PyMuPdfEngine
from pipeline.translation.base import TranslationResult
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.pdf_job import run_pdf_job


def _build_ico_source(path: Path) -> None:
    """Page 0: an "Issuer Address:" metadata chunk (anchor term, plus its
    non-blank continuation line), a blank line, then ordinary translatable
    content - see this module's docstring for why insert_text() per line.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    lines = [
        "Issuer Address:", "123 Main Street", " ",
        "Welcome to the document.", "This is the real content.",
    ]
    y = 60.0
    for line in lines:
        page.insert_text((50, y), line, fontsize=11, fontname="helv")
        y += 14
    doc.save(str(path))
    doc.close()


def _build_plain_source(path: Path) -> None:
    """Page 0 with ordinary content and NO anchor term anywhere - the
    "ico_mode=True but nothing to find" case.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    page.insert_text((50, 60), "Just a normal heading.", fontsize=11, fontname="helv")
    page.insert_text((50, 80), "Nothing special about this page.", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


class FakeHtmlProvider:
    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{html} [DE]", source_lang or "", target_lang, "fake")

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


# --- Engine level (PyMuPdfEngine.open()/extract_blocks()) -----------------


def test_ico_mode_false_leaves_page1_metadata_translatable(tmp_path: Path) -> None:
    source = tmp_path / "ico.pdf"
    _build_ico_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))  # ico_mode defaults to False
    blocks = engine.extract_blocks(0)

    assert len(blocks) == 1
    assert blocks[0].translatable is True
    assert "Issuer Address" in blocks[0].text
    assert engine.first_page_metadata_found is False


def test_ico_mode_true_splits_metadata_block_and_marks_it_non_translatable(tmp_path: Path) -> None:
    source = tmp_path / "ico.pdf"
    _build_ico_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source), ico_mode=True)
    blocks = engine.extract_blocks(0)

    assert len(blocks) == 2
    metadata_block, rest_block = blocks
    assert metadata_block.translatable is False
    assert metadata_block.text == "Issuer Address:\n123 Main Street"
    assert rest_block.translatable is True
    assert "Welcome to the document." in rest_block.text
    assert "Issuer Address" not in rest_block.text
    assert engine.first_page_metadata_found is True


def test_ico_mode_true_finds_nothing_when_no_anchor_term_present(tmp_path: Path) -> None:
    source = tmp_path / "plain.pdf"
    _build_plain_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source), ico_mode=True)
    blocks = engine.extract_blocks(0)

    assert all(block.translatable for block in blocks)
    assert engine.first_page_metadata_found is False


def test_ico_mode_does_not_affect_pages_other_than_the_first(tmp_path: Path) -> None:
    """FIRST_PAGE_ANCHOR_TERMS only ever applies to page_index == 0 - an
    anchor term appearing on a LATER page must never be split, ico_mode or
    not (unchanged existing behavior, confirmed still true after gating
    the split behind ico_mode).
    """
    doc = fitz.open()
    doc.new_page(width=400, height=600)  # page 0: nothing special
    page1 = doc.new_page(width=400, height=600)
    page1.insert_text((50, 60), "Issuer Address:", fontsize=11, fontname="helv")
    page1.insert_text((50, 74), "123 Main Street", fontsize=11, fontname="helv")
    source = tmp_path / "later_page.pdf"
    doc.save(str(source))
    doc.close()

    engine = PyMuPdfEngine()
    engine.open(str(source), ico_mode=True)
    page1_blocks = engine.extract_blocks(1)

    assert all(block.translatable for block in page1_blocks)
    assert engine.first_page_metadata_found is False  # only ever set from page 0


def test_reopening_engine_resets_ico_mode_and_first_page_metadata_found(tmp_path: Path) -> None:
    """open() is called once per engine per job (see ui/pdf_job.py) so this
    isn't exercised by a real run, but the state must not leak across a
    hypothetical second open() on the same instance - mirrors how
    DocxEngine's separator_found is freshly computed each open() too.
    """
    source = tmp_path / "ico.pdf"
    _build_ico_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source), ico_mode=True)
    engine.extract_blocks(0)
    assert engine.first_page_metadata_found is True

    engine.open(str(source))  # re-open, ico_mode back to its False default
    assert engine.first_page_metadata_found is False
    blocks = engine.extract_blocks(0)
    assert len(blocks) == 1
    assert blocks[0].translatable is True


# --- Job level (ui/pdf_job.py::run_pdf_job()) ------------------------------


def test_run_pdf_job_ico_mode_true_skips_metadata_and_reports_it(tmp_path: Path) -> None:
    source = tmp_path / "ico.pdf"
    _build_ico_source(source)
    destination = tmp_path / "ico_DE.pdf"

    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
        ico_mode=True,
    )

    assert result.stats.failed == 0
    doc = fitz.open(str(destination))
    text = " ".join(doc[0].get_text().split())
    doc.close()
    # The metadata chunk must survive UNCHANGED - never sent to the
    # provider, so no " [DE]" suffix - while the rest of the page was
    # translated normally.
    assert "Issuer Address:" in text
    assert "Issuer Address: [DE]" not in text
    assert "Welcome to the document. [DE]" in text or "Welcome to the document." in text
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "ICO-Modus: aktiv. Der erkannte Seite-1-Metadatenbereich" in report


def test_run_pdf_job_ico_mode_false_translates_everything(tmp_path: Path) -> None:
    source = tmp_path / "ico.pdf"
    _build_ico_source(source)
    destination = tmp_path / "ico_DE.pdf"

    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
        # ico_mode defaults to False - the anchor term is present in the
        # source, but must NOT be acted on unless explicitly requested.
    )

    assert result.stats.failed == 0
    doc = fitz.open(str(destination))
    text = " ".join(doc[0].get_text().split())
    doc.close()
    assert "[DE]" in text  # the whole block, including "Issuer Address:", went through
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "ICO-Modus: nicht aktiv" in report


def test_run_pdf_job_ico_mode_true_warns_when_nothing_found(tmp_path: Path) -> None:
    source = tmp_path / "plain.pdf"
    _build_plain_source(source)
    destination = tmp_path / "plain_DE.pdf"

    result = run_pdf_job(
        source, destination, "deepl", DEEPL_PRICING, "de", "en", [],
        max_chars_per_run=200_000, provider=FakeHtmlProvider(),
        ico_mode=True,
    )

    assert result.stats.failed == 0
    assert result.stats.translated >= 1  # nothing excluded - full page translated
    report = result.qa_report_path.read_text(encoding="utf-8")
    assert "ICO-Modus: aktiv, aber auf Seite 1 wurde KEIN passender Metadatenbereich" in report
