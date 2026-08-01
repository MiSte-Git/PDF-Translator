"""Verify html_to_paragraph() - the paragraph_to_html() inverse - against
a real DeepL translation of 2210 INERTIARA.docx (paragraphs 10 and 17).
No write-back into a .docx - purely checks the resulting WordRun list.
Hits the real DeepL API - run manually:

    python tests/manual_verify_word_roundtrip.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.word.base import BREAK_MARKER, WordParagraph, WordRun
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import html_to_paragraph, paragraph_to_html

DOCX_PATH = "2210 INERTIARA.docx"
TARGET_LANG = "de"
SOURCE_LANG = "en"
PARAGRAPH_INDICES = (10, 17)


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
        text_preview = run.text.replace("\n", "\\n")
        if len(text_preview) > 70:
            text_preview = text_preview[:70] + "..."
        print(f"  [{i:>2}]{flag_str} text={text_preview!r}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = DocxEngine()
    engine.open(DOCX_PATH)
    paragraphs = engine.get_paragraphs()

    provider = DeepLProvider()

    for index in PARAGRAPH_INDICES:
        paragraph = paragraphs[index]
        original = paragraph_to_html(paragraph)

        result = provider.translate_html(original.html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
        translated_runs = html_to_paragraph(result.text, original)

        print(f"=== Absatz {index} ===")
        print("Neue WordRun-Liste:")
        print_runs(translated_runs)
        print()

        if index == 10:
            image_runs_in_result = [r for r in translated_runs if r.is_image]
            assert len(image_runs_in_result) == 1, f"expected exactly 1 image run, got {len(image_runs_in_result)}"
            original_image_run = original.image_runs[0]
            same_object = image_runs_in_result[0] is original_image_run
            equal = image_runs_in_result[0] == original_image_run
            print(f"Bild-Run identisch zum Original (is/==): {same_object}/{equal}")
            print(f"  original:   {original_image_run}")
            print(f"  im Ergebnis: {image_runs_in_result[0]}")
            print()

        if index == 17:
            hyperlink_runs_in_result = [r for r in translated_runs if r.is_hyperlink]
            assert len(hyperlink_runs_in_result) == 2, f"expected 2 hyperlink runs, got {len(hyperlink_runs_in_result)}"
            result_targets = {r.hyperlink_target for r in hyperlink_runs_in_result}
            original_targets = set(original.hyperlink_targets.values())
            print(f"Hyperlink-Targets identisch zum Original: {result_targets == original_targets}")
            print(f"  original: {sorted(original_targets)}")
            print(f"  Ergebnis: {sorted(result_targets)}")
            for run in hyperlink_runs_in_result:
                print(f"    text={run.text!r} -> target={run.hyperlink_target!r}")
            print()

    # Regression fixpoint for the break-adjacent-space fix: a run ending in
    # a real trailing space right before a <br/>, and another starting with
    # a real leading space right after one - the exact shape of the bug
    # (tests/manual_translate_full_document.py: DeepL dropped a genuine
    # space touching a <br/>, e.g. "...muss"Inertiara bezeichnet..." missing
    # the space after the closing quote). A synthetic paragraph (not tied to
    # the docx) keeps this deterministic regardless of how INERTIARA's own
    # text happens to be phrased.
    print("=== Break-adjacent-space Regressionsfall (echte DeepL-Uebersetzung) ===")
    space_paragraph = WordParagraph(
        runs=[
            WordRun(text="This sentence continues after a break "),
            WordRun(text=BREAK_MARKER),
            WordRun(text=" right here without losing the space."),
        ]
    )
    original_space = paragraph_to_html(space_paragraph)
    print(f"Gesendetes HTML: {original_space.html!r}")
    assert "§§SP§§" in original_space.html, "expected the space marker in the outgoing HTML"

    space_result = provider.translate_html(original_space.html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
    print(f"Uebersetztes HTML (vor Rueckwandlung): {space_result.text!r}")

    space_runs = html_to_paragraph(space_result.text, original_space)
    final_space_text = "".join(r.text for r in space_runs)
    print(f"Finaler Text nach html_to_paragraph(): {final_space_text!r}")

    no_leftover_marker = "§§SP§§" not in final_space_text
    print(f"Kein '§§SP§§'-Rest im finalen Text: {no_leftover_marker}")
    if not no_leftover_marker:
        print("FEHLER: Space-Marker wurde nicht vollstaendig zurueckverwandelt!")
        sys.exit(1)
    print()

    # Companion negative case in the same run: no space at the break at all
    # - must stay exactly as tight as the original, no space fabricated.
    tight_paragraph = WordParagraph(
        runs=[
            WordRun(text="Heading"),
            WordRun(text=BREAK_MARKER),
            WordRun(text="NoGapBodyText"),
        ]
    )
    original_tight = paragraph_to_html(tight_paragraph)
    print(f"Kontrollfall (kein Leerzeichen im Original) HTML: {original_tight.html!r}")
    assert "§§SP§§" not in original_tight.html, "must not invent a space marker where none existed"
    print("OK: kein Marker eingefuegt, wo im Original kein Leerzeichen stand.")
    print()

    # Deliberately broken case: strip one <img> tag from a valid translated
    # HTML and confirm html_to_paragraph() raises ValueError instead of
    # silently losing the image.
    print("=== Bewusst kaputter Testfall (fehlendes <img>-Tag) ===")
    paragraph_10 = paragraphs[10]
    original_10 = paragraph_to_html(paragraph_10)
    broken_html = original_10.html.replace('<img data-run="0"/>', "", 1)
    try:
        html_to_paragraph(broken_html, original_10)
    except ValueError as exc:
        print(f"ValueError wie erwartet ausgeloest: {exc}")
    else:
        print("FEHLER: html_to_paragraph() hat KEINEN ValueError geworfen - Bild-Verlust waere unbemerkt geblieben!")
        sys.exit(1)


if __name__ == "__main__":
    main()
