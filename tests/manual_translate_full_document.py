"""Full-document Word translation pass: every translatable=True paragraph
in the body AND the active header/footer gets translated (paragraph_to_html
-> protect_terms -> DeepL -> restore_terms -> html_to_paragraph ->
replace_paragraph_runs()/replace_header_footer_paragraph()); everything
else (page-1 metadata block, header/footer, images) is left untouched.
A standalone script - not yet wired into a general pipeline orchestration
class. Hits the real DeepL API - run manually:

    python tests/manual_translate_full_document.py [path/to/file.docx]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.translation.base import TranslationError
from pipeline.translation.cost_control import DEEPL_PRICING, TranslationBudgetGuard, get_month_usage
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.protected_terms import derive_protected_term, protect_terms, restore_terms
from pipeline.word.base import WordParagraph
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import _BREAK_ANOMALY_LOG_PATH, html_to_paragraph, paragraph_to_html

TARGET_LANG = "de"
SOURCE_LANG = "en"
DEFAULT_DOCX = "2210 INERTIARA.docx"


def translate_paragraph(paragraph: WordParagraph, provider, protected_terms: list[str], log_label: str):
    """paragraph_to_html -> protect_terms -> translate_html -> restore_terms
    -> html_to_paragraph. Returns None (nothing to do) if the paragraph
    has no real HTML content (e.g. a blank paragraph between sections).
    `log_label` (e.g. "body:8"/"header:0") identifies the paragraph in
    tests/output/word_break_anomalies.jsonl if html_to_paragraph() logs a
    <br/> count mismatch for it - see pipeline/word/html_bridge.py.
    """
    original = paragraph_to_html(paragraph)
    if not original.html.strip():
        return None, 0

    protected_html, mapping = protect_terms(original.html, protected_terms)
    result = provider.translate_html(protected_html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG)
    restored_html = restore_terms(result.text, mapping)
    return html_to_paragraph(restored_html, original, paragraph_index=log_label), len(protected_html)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    docx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_DOCX)
    if not docx_path.exists():
        print(f"Datei nicht gefunden: {docx_path}")
        sys.exit(1)

    output_path = Path("tests/output") / f"{docx_path.stem.replace(' ', '_')}_DE_full.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    engine = DocxEngine()
    engine.open(str(docx_path))
    if not engine.separator_found:
        print("WARNUNG: kein Trennstrich-Shape gefunden - Metadatenblock evtl. nicht korrekt erkannt.")

    body_paragraphs = engine.get_paragraphs()
    header_footer_paragraphs = engine.get_header_footer_paragraphs()
    header_count = len(engine._header_paragraph_elements)

    protected_terms = [derive_protected_term(docx_path.name)]
    print(f"Schutzbegriff(e): {protected_terms}")
    print()

    month_usage_before = get_month_usage(DEEPL_PRICING.provider_name)
    guard = TranslationBudgetGuard(DeepLProvider(), DEEPL_PRICING)

    # word_break_anomalies.jsonl is a persistent, cross-run log (same
    # convention as the PDF path's growth_anomalies.jsonl) - record the
    # line count before this run so the report below only counts NEW
    # anomalies from THIS run, not ones left over from earlier runs.
    anomaly_lines_before = (
        len(_BREAK_ANOMALY_LOG_PATH.read_text(encoding="utf-8").splitlines())
        if _BREAK_ANOMALY_LOG_PATH.exists()
        else 0
    )

    body_translated = body_skipped = body_failed = 0
    header_translated = header_skipped = header_failed = 0
    footer_translated = footer_skipped = footer_failed = 0
    chars_sent = 0

    start_time = time.monotonic()

    for index, paragraph in enumerate(body_paragraphs):
        if not paragraph.translatable:
            body_skipped += 1
            continue
        print(f"Hauptteil-Absatz {index + 1}/{len(body_paragraphs)}...")
        try:
            new_runs, sent = translate_paragraph(paragraph, guard, protected_terms, f"body:{index}")
        except TranslationError as exc:
            print(f"  FEHLER (uebersprungen): {exc}")
            body_failed += 1
            continue
        chars_sent += sent
        if new_runs is None:
            body_skipped += 1
            continue
        engine.replace_paragraph_runs(index, new_runs)
        body_translated += 1

    for combined_index, paragraph in enumerate(header_footer_paragraphs):
        if combined_index < header_count:
            source, sub_index = "header", combined_index
        else:
            source, sub_index = "footer", combined_index - header_count

        if not paragraph.translatable:
            if source == "header":
                header_skipped += 1
            else:
                footer_skipped += 1
            continue

        # Not expected to ever fire (header/footer are translatable=False
        # per requirement 1), but kept symmetrical with the body loop -
        # see get_header_footer_paragraphs()'s docstring for why False.
        print(f"{source.capitalize()}-Absatz {sub_index + 1}...")
        try:
            new_runs, sent = translate_paragraph(paragraph, guard, protected_terms, f"{source}:{sub_index}")
        except TranslationError as exc:
            print(f"  FEHLER (uebersprungen): {exc}")
            if source == "header":
                header_failed += 1
            else:
                footer_failed += 1
            continue
        chars_sent += sent
        if new_runs is None:
            if source == "header":
                header_skipped += 1
            else:
                footer_skipped += 1
            continue
        engine.replace_header_footer_paragraph(source, sub_index, new_runs)
        if source == "header":
            header_translated += 1
        else:
            footer_translated += 1

    engine.save(str(output_path), overwrite=True)
    elapsed = time.monotonic() - start_time

    estimated_cost = guard.estimate_cost(chars_sent, month_usage_before)

    anomaly_lines_after = (
        len(_BREAK_ANOMALY_LOG_PATH.read_text(encoding="utf-8").splitlines())
        if _BREAK_ANOMALY_LOG_PATH.exists()
        else 0
    )
    new_break_anomalies = anomaly_lines_after - anomaly_lines_before

    print()
    print("=== Kurzreport ===")
    print(f"Hauptteil: {body_translated} uebersetzt, {body_skipped} uebersprungen, {body_failed} fehlgeschlagen")
    print(f"Header:    {header_translated} uebersetzt, {header_skipped} uebersprungen, {header_failed} fehlgeschlagen")
    print(f"Footer:    {footer_translated} uebersetzt, {footer_skipped} uebersprungen, {footer_failed} fehlgeschlagen")
    print(f"Gesendete Zeichen (HTML, inkl. Tags): {chars_sent:,}")
    print(f"Grobe Kostenschaetzung (DeepL-Pricing-Modell): ${estimated_cost:.4f}")
    print(f"Gesamtlaufzeit: {elapsed:.1f}s")
    print(f"Ausgabe: {output_path}")
    if new_break_anomalies:
        print(f"Absaetze mit Break-Anomalie (<br/>-Anzahl veraendert): {new_break_anomalies} - siehe {_BREAK_ANOMALY_LOG_PATH}")
    else:
        print("Absaetze mit Break-Anomalie: 0")


if __name__ == "__main__":
    main()
