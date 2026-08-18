"""Regression coverage for the "Fehlende Glyphen aus Symbol-/Private-Use-
Fonts behandeln" item tracked as open in RoadMap.md Phase 2/PDF.

Distinct from the already-fixed "Glyphen-Verlust" item in
tests/test_pdf_glyph_preservation.py: that one covered ordinary
non-Latin-script Unicode text (Cyrillic/Greek/CJK) being corrupted by the
Base-14 Helvetica plain-text path. This file covers a different, still-
open bug: a symbol/icon-font glyph (e.g. a Wingdings bullet character,
extracted as a Private-Use-Area codepoint like U+F086) going through the
HTML/Story insertion path (used for every real production block, since
block.spans is always populated) and vanishing completely - not even a
visible tofu box, just an invisible gap - because insert_htmlbox()'s CSS
`font-family: sans-serif` resolves to a generic system font that was
never going to have a glyph mapped to that font-specific codepoint.
Confirmed by direct reproduction before the fix: the extracted output
text contained a literal NUL ("\x00") codepoint in place of the symbol,
and the rendered page showed nothing at all at that position - a real,
silent content loss, not just a font mismatch.

Root cause and fix live in pipeline/pdf/pymupdf_engine.py's
_replace_unsupported_glyphs()/_is_private_use_char() (see that module's
Private-Use-Area comment above _insert_html_text()): every Private-Use-
Area codepoint in the HTML content bound for insert_htmlbox() - whether
from a translation provider's response (translated_html) or the
untranslated spans_to_html() fallback - is replaced with a visible
placeholder character (_UNSUPPORTED_GLYPH_PLACEHOLDER, "□") that IS
present in the fallback font, instead of silently vanishing. The exact
original symbol can't be reproduced without embedding the source
document's actual symbol font (a separate, still-open architecture
question - see RoadMap.md/Backlog.md's "Einbettung ... von
Originalfonts"), so a generic, honestly-a-placeholder glyph was chosen
over guessing a specific Unicode equivalent (e.g. a bullet "•") that
might be wrong for a different symbol-font glyph. Every replacement is
also logged via log_growth_anomaly() (event "unsupported_symbol_glyph")
so a document that uses symbol fonts surfaces this in
tests/output/growth_anomalies.jsonl, matching this project's "Nicht
unterstützte Inhalte werden sichtbar katalogisiert" principle.
"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from pipeline.pdf import pymupdf_engine as pymupdf_engine_module
from pipeline.pdf.base import TextSpan
from pipeline.pdf.pymupdf_engine import (
    PyMuPdfEngine,
    _UNSUPPORTED_GLYPH_PLACEHOLDER,
    _is_private_use_char,
    _replace_unsupported_glyphs,
)

# A real-world example: Wingdings commonly maps its bullet-square glyph to
# this Private-Use-Area codepoint (matches the actual codepoint found in
# "1526 VIRELICON.pdf" per Backlog.md's diagnosis).
_SYMBOL_GLYPH = ""


@pytest.fixture()
def isolated_growth_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """See tests/test_pdf_redact_insert_collision.py's identical fixture -
    log_growth_anomaly() appends to a fixed, shared repo path by default;
    redirect it to a private tmp_path file so this test's log entries
    don't leak into (or race with) the real pipeline's log.
    """
    log_path = tmp_path / "growth_anomalies.jsonl"
    monkeypatch.setattr(pymupdf_engine_module, "_GROWTH_ANOMALY_LOG_PATH", log_path)
    return log_path


def _build_source(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_textbox(fitz.Rect(50, 50, 350, 90), "placeholder", fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def test_is_private_use_char() -> None:
    assert _is_private_use_char(_SYMBOL_GLYPH) is True  # BMP PUA
    assert _is_private_use_char("\U000F0000") is True  # Supplementary PUA-A
    assert _is_private_use_char("\U00100000") is True  # Supplementary PUA-B
    assert _is_private_use_char("A") is False
    assert _is_private_use_char("é") is False
    assert _is_private_use_char("日") is False  # ordinary CJK, not PUA


def test_replace_unsupported_glyphs_counts_and_substitutes() -> None:
    html, count = _replace_unsupported_glyphs(f"<p>{_SYMBOL_GLYPH} Bullet item text</p>")
    assert count == 1
    assert html == f"<p>{_UNSUPPORTED_GLYPH_PLACEHOLDER} Bullet item text</p>"
    assert _SYMBOL_GLYPH not in html


def test_replace_unsupported_glyphs_leaves_ordinary_text_untouched() -> None:
    html, count = _replace_unsupported_glyphs("<p>Ganz normaler Text mit Übung und café.</p>")
    assert count == 0
    assert html == "<p>Ganz normaler Text mit Übung und café.</p>"


def test_symbol_glyph_no_longer_vanishes_on_insertion(
    tmp_path: Path, isolated_growth_log: Path
) -> None:
    """The actual bug: before the fix, this exact sequence produced a
    literal NUL codepoint (rendered as nothing at all) instead of any
    visible character at the symbol's position.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = engine.extract_blocks(0)[0]
    block.spans = [
        TextSpan(
            text=f"{_SYMBOL_GLYPH} Bullet item text",
            font_name="Wingdings",
            font_size=11.0,
            color=(0, 0, 0),
            bold=False,
            italic=False,
            underline=False,
        )
    ]

    engine.redact_block(block)
    engine.insert_text(block, "", block.font_size)
    engine.save(str(output))

    result = fitz.open(str(output))
    extracted = result[0].get_text()
    assert "\x00" not in extracted  # the old, silent-loss symptom
    assert _SYMBOL_GLYPH not in extracted  # never renderable as itself either
    assert _UNSUPPORTED_GLYPH_PLACEHOLDER in extracted
    # get_text() wraps at PyMuPDF's own line-detection boundaries (real
    # newlines here, not a content issue) - normalize whitespace before
    # checking the text itself survived intact.
    assert "Bullet item text" in " ".join(extracted.split())
    result.close()

    # Logged for visibility, per this project's "sichtbar katalogisiert"
    # principle for unsupported content.
    log_lines = isolated_growth_log.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in log_lines]
    assert any(
        e["event"] == "unsupported_symbol_glyph" and e["replaced_glyph_count"] == 1
        for e in events
    )


def test_ordinary_translated_block_is_not_logged_or_altered(
    tmp_path: Path, isolated_growth_log: Path
) -> None:
    """Control case: a block with no symbol-font content must not trigger
    the placeholder substitution or the anomaly log entry at all.
    """
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _build_source(source)

    engine = PyMuPdfEngine()
    engine.open(str(source))
    block = engine.extract_blocks(0)[0]

    engine.redact_block(block)
    engine.insert_text(block, "", block.font_size, translated_html="<p>Ganz normaler Text.</p>")
    engine.save(str(output))

    result = fitz.open(str(output))
    extracted = result[0].get_text()
    assert "Ganz normaler Text." in " ".join(extracted.split())
    assert _UNSUPPORTED_GLYPH_PLACEHOLDER not in extracted
    result.close()

    # Other anomaly events (e.g. growth-related ones) are out of scope
    # here and may legitimately fire - only "unsupported_symbol_glyph"
    # must not.
    if isolated_growth_log.exists():
        log_lines = isolated_growth_log.read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in log_lines if line.strip()]
        assert not any(e["event"] == "unsupported_symbol_glyph" for e in events)
