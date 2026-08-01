"""Verify DocxEngine.replace_paragraph_runs() against 2210 INERTIARA.docx,
paragraph 10 - a hand-built WordRun list (no provider/HTML flow), checking
the raw generated XML and a reread round trip. No .docx is saved to disk
(save() isn't implemented yet) - purely in-memory tree manipulation. Not a
pytest test - run manually:

    python tests/manual_verify_word_paragraph_write.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.base import BREAK_MARKER, WordRun
from pipeline.word.docx_engine import DocxEngine, _build_paragraph, _w

DOCX_PATH = "2210 INERTIARA.docx"
PARAGRAPH_INDEX = 10


def reread_paragraph(xml_bytes: bytes, paragraph_index: int, rels: dict[str, str]):
    """Reload a serialized document.xml (bytes) directly with lxml and
    rebuild the WordParagraph at `paragraph_index`, independent of
    DocxEngine.open() (which expects a real .docx zip, not a bare XML
    string) - the "direkt mit lxml" reread path.
    """
    root = etree.fromstring(xml_bytes)
    body = root.find(_w("body"))
    paragraph_elements = body.findall(_w("p"))
    paragraph_element = paragraph_elements[paragraph_index]
    # translatable doesn't matter for this check - reuse True.
    return _build_paragraph(paragraph_element, rels, translatable=True)


def print_runs(runs) -> None:
    for i, run in enumerate(runs):
        flags = []
        if run.bold:
            flags.append("bold")
        if run.italic:
            flags.append("italic")
        if run.underline:
            flags.append("underline")
        if run.is_image:
            flags.append("IMAGE")
        if run.is_hyperlink:
            flags.append(f"hyperlink->{run.hyperlink_target!r}")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  [{i:>2}]{flag_str} text={run.text!r}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = DocxEngine()
    engine.open(DOCX_PATH)
    original_paragraph = engine.get_paragraphs()[PARAGRAPH_INDEX]

    original_image_run = next(r for r in original_paragraph.runs if r.is_image)
    print("Original Bild-Run:", original_image_run)
    print()

    test_runs = [
        original_image_run,
        WordRun(text="Überstülp-Titel", bold=True, underline=True),
        WordRun(text=BREAK_MARKER),
        WordRun(text=" Ärmelkanal ist größer als Straße "),
    ]

    print("=== Test-Run-Liste (Input) ===")
    print_runs(test_runs)
    print()

    engine.replace_paragraph_runs(PARAGRAPH_INDEX, test_runs)

    xml_bytes = engine.document_xml_bytes()
    root = etree.fromstring(xml_bytes)
    body = root.find(_w("body"))
    paragraph_element = body.findall(_w("p"))[PARAGRAPH_INDEX]
    raw_paragraph_xml = etree.tostring(paragraph_element, pretty_print=True, encoding="unicode")

    print("=== Rohes XML des ersetzten Absatzes ===")
    print(raw_paragraph_xml)

    # Reread: parse the serialized document.xml again (independent of the
    # live DocxEngine instance/tree) and rebuild WordParagraph from it.
    reread = reread_paragraph(xml_bytes, PARAGRAPH_INDEX, engine._rels)

    print("=== Reread Absatz (aus serialisiertem XML neu geparst) ===")
    print_runs(reread.runs)
    print()

    checks: list[tuple[str, bool]] = []

    image_runs_reread = [r for r in reread.runs if r.is_image]
    checks.append(("genau 1 Bild-Run beim Reread", len(image_runs_reread) == 1))
    if image_runs_reread:
        checks.append(("Bild-Run identisch zum Original (==)", image_runs_reread[0] == original_image_run))

    text_runs = [r for r in reread.runs if not r.is_image]
    reconstructed_text = "".join(r.text for r in text_runs)
    expected_text = "Überstülp-Titel" + BREAK_MARKER + " Ärmelkanal ist größer als Straße "
    checks.append(("Text (inkl. Umlaute/ß, Break-Marker) exakt erhalten", reconstructed_text == expected_text))

    bold_underline_run = next((r for r in reread.runs if r.text == "Überstülp-Titel"), None)
    checks.append(("bold+underline korrekt gesetzt", bold_underline_run is not None and bold_underline_run.bold and bold_underline_run.underline))

    space_run = next((r for r in reread.runs if "Ärmelkanal" in r.text), None)
    checks.append(("fuehrendes Leerzeichen erhalten", space_run is not None and space_run.text.startswith(" ")))
    checks.append(("nachfolgendes Leerzeichen erhalten", space_run is not None and space_run.text.endswith(" ")))

    print("=== Checks ===")
    all_ok = True
    for label, ok in checks:
        all_ok = all_ok and ok
        print(f"  {'OK' if ok else 'FEHLER'}: {label}")

    print()
    print(f"GESAMTERGEBNIS: {'OK' if all_ok else 'FEHLGESCHLAGEN'}")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
