"""Regression coverage for the "Duplikat-Text-Bug im Redact/Insert-Pfad"
tracked as open in RoadMap.md Phase 2/PDF (originally diagnosed against a
real document in tests/manual_diagnose_text_duplication.py, which needs a
confidential real PDF plus a live DeepL call and can't run here or in CI).

What actually happened, per that diagnosis script's docstring and
pipeline/pdf/pymupdf_engine.py's _insert_html_text()/PyMuPdfEngine.
_collision_aware_max_y1() docstrings: a translated block that needed more
vertical space than its original English text grew (before a fix) without
checking the position of the NEXT block on the page, so its overflow text
could grow right into - and visually overlap/duplicate with - the next
block's own row once THAT block was later redacted and re-inserted with
its own (unrelated, much smaller) translation. The fix - collision-aware
growth (_next_block_y0()/_collision_aware_max_y1()), applied unconditionally
to every block instead of only block.highlighted - already exists and is
documented as done in Backlog.md's "Kollisionsschutz" entry, verified
there against the real document. What was still missing (and is what this
file adds): permanent, real-file-independent regression coverage that
actually exercises PyMuPdfEngine.redact_block()/insert_text() end-to-end
(not just the growth-boundary math in isolation) against a case
deliberately built to reproduce the reported mechanism, so a future change
that reintroduces the bug fails CI instead of only being caught by someone
manually re-running the old diagnosis script against a confidential file.

Every test here builds its own tiny synthetic PDF with real drawn text (so
extract_blocks() sees genuine PyMuPDF-detected TextBlocks, not hand-built
ones), forces a translation deliberately much longer than the English
original to guarantee overflow, and checks the FINAL rendered page text -
the same ground truth a human visually inspecting the output PDF would
use - for the specific failure signature: the original English text (or a
truncated remainder of it) surviving a redaction it should have been wiped
by, or a paragraph's translated text appearing more than once.
"""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pipeline.pdf import pymupdf_engine as pymupdf_engine_module
from pipeline.pdf.pymupdf_engine import PyMuPdfEngine, _HIGHLIGHT_FILL_COLOR


@pytest.fixture()
def isolated_growth_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """log_growth_anomaly() appends to a fixed, shared repo path by default
    (tests/output/growth_anomalies.jsonl) - fine for the real pipeline, but
    would make these tests flaky/order-dependent against each other and any
    manual script run concurrently. Redirect it to a private tmp_path file
    per test instead.
    """
    log_path = tmp_path / "growth_anomalies.jsonl"
    monkeypatch.setattr(pymupdf_engine_module, "_GROWTH_ANOMALY_LOG_PATH", log_path)
    return log_path


def _build_two_paragraph_pdf(path: Path, gap: float = 16.5) -> None:
    """A page with two ordinary (non-highlighted) text blocks stacked
    close together - block A directly above block B, separated only by
    `gap` points. This is the layout shape the real diagnosis found the
    bug in: a block needing to grow taller has very little headroom
    before it would reach the next block's row.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(
        fitz.Rect(50, 50, 350, 85),
        "This is the original English paragraph about the project overview and its context.",
        fontsize=10, fontname="helv",
    )
    page.insert_textbox(
        fitz.Rect(50, 85 + gap, 350, 120 + gap),
        "This second paragraph starts right below the first one with only a small gap.",
        fontsize=10, fontname="helv",
    )
    doc.save(str(path))
    doc.close()


def _build_highlighted_quote_pdf(path: Path) -> None:
    """A short highlighted quote block (colored background, see
    _HIGHLIGHT_FILL_COLOR) immediately followed by an ordinary paragraph -
    exercises PyMuPdfEngine._grow_highlight_if_needed()'s redact-then-
    redraw-then-reinsert path specifically (see its docstring), which is
    the one place outside plain growth that deliberately does a SECOND
    insert_text() call for the same block.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    highlight_rect = fitz.Rect(50, 50, 350, 78)
    page.draw_rect(highlight_rect, color=None, fill=_HIGHLIGHT_FILL_COLOR, width=0)
    page.insert_textbox(fitz.Rect(50, 50, 350, 78), "Short quote text here.", fontsize=10, fontname="helv")
    page.insert_textbox(
        fitz.Rect(50, 90, 350, 125),
        "Following paragraph right after the quote block.",
        fontsize=10, fontname="helv",
    )
    doc.save(str(path))
    doc.close()


def test_moderate_overflow_grows_capped_by_collision_without_duplication(
    tmp_path: Path, isolated_growth_log: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_two_paragraph_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block_a, block_b = engine.extract_blocks(0)

    # Deliberately much longer than the English original, so block_a MUST
    # grow (or shrink) to fit - this is what used to be able to overflow
    # into block_b's row before the collision-aware fix.
    translation_a = (
        "<p>Dies ist die uebersetzte deutsche Version des ersten Absatzes, "
        "aber absichtlich sehr viel laenger als das englische Original, "
        "damit der Text wachsen oder schrumpfen muss, um in die Box zu "
        "passen, und moeglicherweise mit dem naechsten Block kollidiert, "
        "falls der Kollisionsschutz nicht korrekt greift.</p>"
    )
    translation_b = "<p>Zweiter uebersetzter Absatz, kurz.</p>"

    engine.redact_block(block_a)
    engine.insert_text(block_a, "", block_a.font_size, translated_html=translation_a)
    engine.redact_block(block_b)
    engine.insert_text(block_b, "", block_b.font_size, translated_html=translation_b)
    engine.save(str(output))

    final_text = fitz.open(str(output))[0].get_text()
    assert "original English paragraph" not in final_text
    assert final_text.count("uebersetzte deutsche") == 1
    assert final_text.count("Zweiter uebersetzter") == 1

    # The collision cap must actually have engaged (not just have gone
    # unused because the text happened to fit anyway) - otherwise this test
    # wouldn't be exercising the mechanism it claims to guard.
    assert isolated_growth_log.exists()
    log_contents = isolated_growth_log.read_text(encoding="utf-8")
    assert "growth_capped_by_collision" in log_contents


def test_extreme_overflow_forced_shrink_fallback_does_not_duplicate(
    tmp_path: Path, isolated_growth_log: Path,
) -> None:
    """Overflow so large that even shrinking to _MIN_FONT_SIZE within the
    collision-capped rect isn't enough, forcing _insert_html_text()'s final
    scale_low=0 fallback write (see its docstring) - checks that fallback
    path is equally clean, not just the ordinary growth/shrink path above.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_two_paragraph_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block_a, block_b = engine.extract_blocks(0)

    huge_translation = "<p>" + ("Sehr langer wiederholter Fuelltext, der auf keinen Fall passt. " * 40) + "</p>"
    translation_b = "<p>Zweiter uebersetzter Absatz, kurz.</p>"

    engine.redact_block(block_a)
    engine.insert_text(block_a, "", block_a.font_size, translated_html=huge_translation)
    engine.redact_block(block_b)
    engine.insert_text(block_b, "", block_b.font_size, translated_html=translation_b)
    engine.save(str(output))

    final_text = fitz.open(str(output))[0].get_text()
    assert "original English paragraph" not in final_text
    # The phrase is repeated 40x in the deliberately-huge INPUT; at this
    # extreme size scale_low=0's forced auto-shrink may legitimately drop
    # some of the tail rather than shrink infinitely (that's a content-fit
    # tradeoff, not a bug) - the actual regression check is the upper
    # bound: it must never appear MORE than 40 times (that would mean
    # duplication), and it must appear at least once (not silently dropped
    # entirely).
    occurrences = final_text.count("Sehr langer wiederholter Fuelltext")
    assert 0 < occurrences <= 40
    assert final_text.count("Zweiter uebersetzter") == 1


def test_highlighted_block_growth_redraw_does_not_duplicate(
    tmp_path: Path, isolated_growth_log: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_highlighted_quote_pdf(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    blocks = engine.extract_blocks(0)
    block_a = next(b for b in blocks if b.highlighted)
    block_b = next(b for b in blocks if not b.highlighted)

    translation_a = "<p>" + ("Sehr viel laengerer uebersetzter Zitat-Text als das kurze Original. " * 3) + "</p>"
    translation_b = "<p>Nachfolgender uebersetzter Absatz.</p>"

    engine.redact_block(block_a)
    engine.insert_text(block_a, "", block_a.font_size, translated_html=translation_a)
    engine.redact_block(block_b)
    engine.insert_text(block_b, "", block_b.font_size, translated_html=translation_b)
    engine.save(str(output))

    final_text = fitz.open(str(output))[0].get_text()
    assert "Short quote text" not in final_text
    # The 3-times-repeated phrase is the deliberate input, not a bug.
    assert final_text.count("Sehr viel laengerer") == 3
    assert final_text.count("Nachfolgender") == 1
