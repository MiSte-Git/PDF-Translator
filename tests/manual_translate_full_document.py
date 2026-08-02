"""Full-document Word translation pass: every translatable=True paragraph
in the body AND the active header/footer gets translated. Thin wrapper
around pipeline/word/translate_document.py's translate_document() (this
script's original logic, extracted so ico_translate/batch.py's batch run
shares it instead of duplicating it) - this script's own job is just
opening the source file, wiring up the DeepL provider/budget guard/
protected terms, calling translate_document(), and printing the Kurzreport.
Hits the real DeepL API - run manually:

    python tests/manual_translate_full_document.py [path/to/file.docx]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.translation.cost_control import DEEPL_PRICING, TranslationBudgetGuard, get_month_usage
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.protected_terms import derive_protected_term
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.translate_document import translate_document

TARGET_LANG = "de"
SOURCE_LANG = "en"
DEFAULT_DOCX = "2210 INERTIARA.docx"


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

    protected_terms = [derive_protected_term(docx_path.name)]
    print(f"Schutzbegriff(e): {protected_terms}")
    print()

    month_usage_before = get_month_usage(DEEPL_PRICING.provider_name)
    guard = TranslationBudgetGuard(DeepLProvider(), DEEPL_PRICING)

    start_time = time.monotonic()
    stats = translate_document(
        engine,
        guard,
        protected_terms,
        target_lang=TARGET_LANG,
        source_lang=SOURCE_LANG,
        progress_callback=print,
    )
    engine.save(str(output_path), overwrite=True)
    elapsed = time.monotonic() - start_time

    estimated_cost = guard.estimate_cost(stats.chars_sent, month_usage_before)

    print()
    print("=== Kurzreport ===")
    print(f"Hauptteil: {stats.body_translated} uebersetzt, {stats.body_skipped} uebersprungen, {stats.body_failed} fehlgeschlagen")
    print(f"Header:    {stats.header_translated} uebersetzt, {stats.header_skipped} uebersprungen, {stats.header_failed} fehlgeschlagen")
    print(f"Footer:    {stats.footer_translated} uebersetzt, {stats.footer_skipped} uebersprungen, {stats.footer_failed} fehlgeschlagen")
    print(f"Gesendete Zeichen (HTML, inkl. Tags): {stats.chars_sent:,}")
    print(f"Grobe Kostenschaetzung (DeepL-Pricing-Modell): ${estimated_cost:.4f}")
    print(f"Gesamtlaufzeit: {elapsed:.1f}s")
    print(f"Ausgabe: {output_path}")
    if stats.new_break_anomalies:
        print(
            f"Absaetze mit Break-Anomalie (<br/>-Anzahl veraendert): {stats.new_break_anomalies} - "
            "siehe tests/output/word_break_anomalies.jsonl"
        )
    else:
        print("Absaetze mit Break-Anomalie: 0")


if __name__ == "__main__":
    main()
