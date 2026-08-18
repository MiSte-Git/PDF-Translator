"""Regression coverage for "PDF-Übersetzung korrigieren" (RoadMap.md
Phase 2/PDF) - a manual-correction workflow added after a real user found
a genuine mistranslation in a live run against "1526 VIRELICON.pdf": the
proper name "Manuel" (a speaker's name in a quote's attribution line, "-
Manuel to PQ") came back as "Handbuch" (German for "manual", the
document/instruction-booklet sense) from the translation provider.
Protected terms (pipeline/translation/protected_terms.py) can prevent
this for a name that is ALWAYS a name, but the user correctly pointed out
that a global term substitution is the wrong tool for a word that is
SOMETIMES a real name and sometimes a real word needing translation - so
this file covers a proper correction step instead: a per-block review/
edit workflow built on the SAME redact_block()/insert_text() machinery
translate_pdf() already uses, not a new PDF-editing engine.

Three pieces, each covered below:

1. html_to_plain_text() (pipeline/pdf/pymupdf_engine.py) - turns
   spans_to_html()/a translation provider's HTML response back into
   plain, human-editable text for display in a correction table.

2. translate_pdf() (pipeline/pdf/translate_pdf.py) now additionally
   populates PdfTranslationStats.blocks with one TranslatedBlockRecord
   per successfully-translated block (page_index, block_index, original
   text, the html actually inserted) - purely additive, every existing
   field/caller is unaffected (see tests/test_pdf_job.py, still passing
   unchanged).

3. build_corrected_records()/apply_pdf_corrections() - given the original
   records plus a human's edits (as plain text per row), rebuilds HTML
   only for the CHANGED rows (losing their inline bold/italic/underline
   formatting - a documented, deliberate trade-off) while unedited rows
   keep their exact original html (and therefore their exact original
   formatting) untouched, then re-runs redact_block()/insert_text() for
   every record against a FRESH engine opened on the pristine source PDF
   - never the already-translated one, which apply_pdf_corrections()'s
   docstring explains would leave stray remnants of the first
   translation for any block that grew past its original box.
"""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pipeline.pdf.base import TextSpan
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, html_to_plain_text
from pipeline.pdf.translate_pdf import (
    PdfTranslationStats,
    TranslatedBlockRecord,
    apply_pdf_corrections,
    build_corrected_records,
    translate_pdf,
)
from pipeline.translation.base import TranslationResult


class FakeHtmlProvider:
    """Mirrors tests/test_pdf_job.py's FakeHtmlProvider - appends " [DE]"
    so translated output is trivially distinguishable from the original
    English without needing a real provider/network call.
    """

    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{html} [DE]", source_lang or "", target_lang, "fake")

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        return TranslationResult(f"{text} [DE]", source_lang or "", target_lang, "fake")


def _build_two_block_source(path: Path) -> None:
    """Two ordinary, well-separated single-line blocks on one page - block
    0 will get its formatting/translation edited via extract_blocks()
    below, block 1 stays a plain-formatting control.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    page.insert_textbox(fitz.Rect(50, 50, 350, 70), "Manuel to PQ", fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(50, 150, 350, 170), "Second block text", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_html_to_plain_text_strips_tags_and_unescapes() -> None:
    assert html_to_plain_text("<p>Hello <b>world</b></p>") == "Hello world"
    assert html_to_plain_text("<p>First</p><p>Second</p>") == "First\n\nSecond"
    assert html_to_plain_text("<p>Line1<br/>Line2</p>") == "Line1\nLine2"
    assert html_to_plain_text("<p>Fish &amp; Chips</p>") == "Fish & Chips"
    assert html_to_plain_text("<p><b><i>Bold italic</i></b> plain</p>") == "Bold italic plain"


def test_translate_pdf_populates_block_records(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _build_two_block_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    provider = FakeHtmlProvider()

    stats = translate_pdf(engine, provider, [], target_lang="de", source_lang="en")

    assert stats.translated == 2
    assert len(stats.blocks) == 2
    first, second = stats.blocks
    assert isinstance(first, TranslatedBlockRecord)
    assert first.page_index == 0
    assert first.block_index == 0
    assert "Manuel to PQ" in first.original_text
    assert "Manuel to PQ" in first.display_text  # FakeHtmlProvider echoes the source text
    assert "[DE]" in first.display_text
    assert second.block_index == 1
    assert "Second block text" in second.original_text


def test_build_corrected_records_only_rebuilds_edited_rows() -> None:
    unedited_record = TranslatedBlockRecord(
        page_index=0, block_index=0, original_text="Manuel to PQ",
        translated_html="<p><b>Manuel to PQ</b> [DE]</p>",
    )
    other_record = TranslatedBlockRecord(
        page_index=0, block_index=1, original_text="Second block text",
        translated_html="<p>Second block text [DE]</p>",
    )
    edits = {
        (0, 0): unedited_record.display_text,  # unchanged - must be left as-is (formatting intact)
        (0, 1): "Corrected second block text",  # actually changed
    }

    corrected = build_corrected_records([unedited_record, other_record], edits)

    assert corrected[0] is unedited_record  # untouched row: same object, same html/formatting
    assert corrected[0].translated_html == "<p><b>Manuel to PQ</b> [DE]</p>"
    assert corrected[1] is not other_record
    assert corrected[1].translated_html == "<p>Corrected second block text</p>"
    assert corrected[1].page_index == 0
    assert corrected[1].block_index == 1


def test_build_corrected_records_ignores_missing_keys() -> None:
    record = TranslatedBlockRecord(
        page_index=2, block_index=5, original_text="Foo", translated_html="<p>Foo [DE]</p>"
    )
    corrected = build_corrected_records([record], edited_texts={})
    assert corrected == [record]


def test_apply_corrections_fixes_edited_block_and_preserves_unedited_formatting(
    tmp_path: Path,
) -> None:
    """End-to-end: the actual "Manuel" -> "Handbuch" scenario, fixed via a
    correction, while an untouched bold block keeps its bold formatting.
    """
    source = tmp_path / "source.pdf"
    _build_two_block_source(source)

    # First pass: simulate the real bug directly (rather than depending on
    # a live provider mistranslating a name) - block 0's "translation"
    # really is the wrong word, block 1 is fine and bold (to prove
    # untouched-row formatting survives the correction pass too).
    engine = PyMuPdfEngine()
    engine.open(str(source))
    block0 = engine.extract_blocks(0)[0]
    block1 = engine.extract_blocks(0)[1]
    block0.spans = [TextSpan(text="- Handbuch to PQ", font_name="helv", font_size=11.0,
                              color=(0, 0, 0), bold=False, italic=False, underline=False)]
    block1.spans = [TextSpan(text="Second block translated", font_name="helv", font_size=11.0,
                              color=(0, 0, 0), bold=True, italic=False, underline=False)]

    from pipeline.pdf.pymupdf_engine import spans_to_html
    original_output = tmp_path / "original.pdf"
    engine.redact_block(block0)
    engine.insert_text(block0, "", block0.font_size, translated_html=spans_to_html(block0.spans))
    engine.redact_block(block1)
    engine.insert_text(block1, "", block1.font_size, translated_html=spans_to_html(block1.spans))
    engine.save(str(original_output))

    records = [
        TranslatedBlockRecord(
            page_index=0, block_index=0, original_text="Manuel to PQ",
            translated_html=spans_to_html(block0.spans),
        ),
        TranslatedBlockRecord(
            page_index=0, block_index=1, original_text="Second block text",
            translated_html=spans_to_html(block1.spans),
        ),
    ]

    # Human correction: only the mistranslated name is edited.
    corrected_records = build_corrected_records(
        records,
        {
            (0, 0): "- Manuel to PQ",
            (0, 1): records[1].display_text,  # left exactly as shown -> unedited
        },
    )

    # CRITICAL per apply_pdf_corrections()'s docstring: a FRESH engine on
    # the untouched source, not the already-mutated `engine` above.
    correction_engine = PyMuPdfEngine()
    correction_engine.open(str(source))
    corrected_stats = apply_pdf_corrections(correction_engine, corrected_records)
    corrected_output = tmp_path / "corrected.pdf"
    correction_engine.save(str(corrected_output))

    assert isinstance(corrected_stats, PdfTranslationStats)
    assert corrected_stats.translated == 2
    assert corrected_stats.blocks == []  # correction passes don't themselves emit further records

    result = fitz.open(str(corrected_output))
    page = result[0]
    extracted = " ".join(page.get_text().split())
    assert "Handbuch" not in extracted
    assert "Manuel" in extracted

    raw = page.get_text("dict")
    # insert_htmlbox() may wrap this text across more than one span (e.g.
    # by line) - collect every span whose text is part of the expected
    # phrase rather than assuming it's a single span.
    matching_spans = [
        span
        for b in raw["blocks"] if b.get("type") == 0
        for line in b["lines"]
        for span in line["spans"]
        if span["text"].strip() and span["text"].strip() in "Second block translated"
    ]
    assert matching_spans, "expected to find spans making up 'Second block translated'"
    assert " ".join(span["text"] for span in matching_spans).strip() == "Second block translated"
    assert all("bold" in span["font"].lower() for span in matching_spans)
    result.close()


def test_apply_corrections_requires_no_provider_and_leaves_records_empty(tmp_path: Path) -> None:
    """Sanity check on apply_pdf_corrections()'s contract: no provider
    argument exists at all (impossible to call it with one by mistake),
    and it never raises TranslationError-related state.
    """
    source = tmp_path / "source.pdf"
    _build_two_block_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = engine.extract_blocks(0)[0]
    record = TranslatedBlockRecord(
        page_index=0, block_index=0, original_text=block.text,
        translated_html="<p>Korrigierter Text</p>",
    )
    stats = apply_pdf_corrections(engine, [record])
    assert stats.failed == 0
    assert stats.errors == []
    assert stats.chars_sent == 0
    assert stats.cancelled is False
