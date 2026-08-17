"""UI end-to-end pass for the PPTX/DeepL job the Start button now triggers.

Not a pytest test - drives exactly the function ui/app.py's MainWindow._start()
calls (ui.pptx_job.run_presentation_job()), against a real multi-slide deck,
through the real DeepL API. Requires a DeepL key (see
tests/manual_test_deepl_provider.py) and a real .pptx source file - point it
at the project's known 19-slide real-world test dataset (RoadMap.md Phase 1):

    python tests/manual_e2e_pptx_ui_translation.py [path/to/deck.pptx]

Prints the same short report the UI would show (translated/skipped/failed
paragraphs, characters sent, output path, QA report path) and every overflow
finding the QA report lists for manual review in PowerPoint/Impress -
including the known Slide 11 special case, if that slide is present in the
chosen dataset. Nothing is auto-reformatted; this script only surfaces what
the UI already surfaces.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.credentials import get_deepl_api_key
from pipeline.translation.cost_control import DEEPL_PRICING
from ui.pptx_job import run_presentation_job, safe_destination

DEFAULT_PPTX = "OPRES ES Hub Quorum Activation Call Presentation.pptx"
TARGET_LANG = "de"
SOURCE_LANG = "en"


def _slide_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        return sum(
            1 for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        get_deepl_api_key()
    except RuntimeError as exc:
        print(f"Kein DeepL-Schlüssel verfügbar, Test übersprungen: {exc}")
        return

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_PPTX)
    if not source.exists():
        print(f"Reales Testdokument nicht gefunden ({source}), Test übersprungen.")
        print("Pfad als Argument übergeben oder Datei neben dieses Skript legen.")
        return

    slide_count = _slide_count(source)
    print(f"Quelle: {source} ({slide_count} Folien)")
    if slide_count != 19:
        print(
            f"Hinweis: RoadMap.md nennt einen 19-Folien-Testdatensatz, "
            f"dieses Dokument hat {slide_count} Folien - Lauf wird trotzdem durchgeführt."
        )

    output_dir = Path("tests/output/pptx_ui_e2e")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = safe_destination(source, TARGET_LANG, output_dir)

    protected_terms: list[str] = []
    progress_calls = 0

    def on_progress(location: str) -> None:
        nonlocal progress_calls
        progress_calls += 1
        print(f"  [{progress_calls}] {location}")

    result = run_presentation_job(
        source, destination, "deepl", DEEPL_PRICING, TARGET_LANG, SOURCE_LANG,
        protected_terms, max_chars_per_run=200_000, progress_callback=on_progress,
    )

    stats = result.stats
    print()
    print("=== Kurzreport (wie im UI angezeigt) ===")
    print(f"Übersetzt: {stats.paragraphs_translated}")
    print(f"Übersprungen: {stats.paragraphs_skipped}")
    print(f"Fehlgeschlagen: {stats.paragraphs_failed}")
    print(f"Gesendete Zeichen: {stats.chars_sent:,}")
    print(f"Ausgabedatei: {result.output_path}")
    print(f"QA-Bericht: {result.qa_report_path}")
    if stats.errors:
        print("Fehlerdetails:")
        for error in stats.errors:
            print(f"  - {error}")

    print()
    if result.overflow_regressions:
        print(f"Überlaufhinweise ({len(result.overflow_regressions)}) - manuell prüfen, nicht automatisch korrigiert:")
        for regression in result.overflow_regressions:
            marker = " <-- bekannter Sonderfall?" if "slide11" in regression.slide_path else ""
            print(
                f"  - {regression.slide_path} · {regression.shape_name}: {regression.reason} "
                f"({regression.after_estimated_lines}/{regression.available_lines} Zeilen){marker}"
            )
    else:
        print("Keine neuen oder verschärften Überlaufrisiken gefunden.")


if __name__ == "__main__":
    main()
