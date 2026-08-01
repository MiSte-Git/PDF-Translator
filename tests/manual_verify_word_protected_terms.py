"""Verify protect_terms()/restore_terms() through the FULL Word-HTML
translation flow - not just marker survival in isolation (see
tests/manual_verify_word_markers.py) but the real end-to-end sequence:

    paragraph_to_html -> protect_terms -> translate_html (real DeepL)
    -> restore_terms -> html_to_paragraph

No write-back into document.xml. Hits the real DeepL API - run manually:

    python tests/manual_verify_word_protected_terms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.protected_terms import derive_protected_term, protect_terms, restore_terms
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import html_to_paragraph, paragraph_to_html

DOCX_PATH = "2210 INERTIARA.docx"
TARGET_LANG = "de"
SOURCE_LANG = "en"


def run_case(label: str, paragraph, protected_terms: list[str], provider) -> None:
    print(f"=== {label} ===")
    print(f"protected_terms: {protected_terms}")

    original = paragraph_to_html(paragraph)
    print(f"Original HTML:\n  {original.html}")

    protected_html, mapping = protect_terms(original.html, protected_terms)
    if not mapping:
        print("  WARNUNG: protect_terms() hat keinen Treffer gefunden - Test ist fuer diesen Absatz nicht aussagekraeftig.")
        print()
        return
    print(f"Platzhalter-Mapping: {mapping}")

    result = provider.translate_html(protected_html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
    print(f"Uebersetzt (Platzhalter noch drin):\n  {result.text}")

    restored_html = restore_terms(result.text, mapping)
    print(f"Nach restore_terms():\n  {restored_html}")

    runs = html_to_paragraph(restored_html, original)
    final_text = "".join(run.text for run in runs)
    print(f"Finaler Run-Text:\n  {final_text}")
    print()

    all_restored = True
    for placeholder, original_text in mapping.items():
        present = original_text in final_text
        all_restored = all_restored and present
        print(f"  {placeholder} -> {original_text!r}: exakte Original-Schreibweise im finalen Text vorhanden = {present}")

    leftover = [placeholder for placeholder in mapping if placeholder in final_text]
    print(f"  Platzhalter-Reste im finalen Text: {leftover or 'keine'}")
    print()
    print(f"ERGEBNIS {label}: {'OK' if all_restored and not leftover else 'FEHLGESCHLAGEN'}")
    print()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = DocxEngine()
    engine.open(DOCX_PATH)
    paragraphs = engine.get_paragraphs()
    provider = DeepLProvider()

    ico_term = derive_protected_term(DOCX_PATH)

    # Absatz 10: "Inertiara" (case-insensitive match of the filename-derived
    # term) occurs 3x in this paragraph, including right at the start of
    # the (bold+underlined) title itself - contrary to the task's
    # assumption that it wouldn't. No need for an additional paragraph.
    run_case("Absatz 10 (Fliesstext + Titel)", paragraphs[10], [ico_term], provider)

    # Absatz 17: the ICO name itself doesn't appear here, but "QSI" (the
    # other protected term named in Backlog.md's structure analysis -
    # "Entwicklername, ICO-Name, 'QSI'") is literally the second
    # hyperlink's display text - the realistic case Backlog.md flagged as
    # needing verification ("Protected-Terms-Pruefung ... muss auch
    # innerhalb von <w:hyperlink>-Runs greifen").
    run_case("Absatz 17 (Hyperlink-Anzeigetext)", paragraphs[17], [ico_term, "QSI"], provider)


if __name__ == "__main__":
    main()
