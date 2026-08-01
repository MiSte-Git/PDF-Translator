"""Verify DocxEngine.save() end-to-end against 2210 INERTIARA.docx:
replace paragraph 10, save a full new .docx, reopen it with a FRESH
DocxEngine instance and check that (a) paragraph 10 has the new content,
(b) every other paragraph is textually unchanged, (c) images in
word/media/ are all still present, (d) header/footer text is unchanged,
and (e) python-docx can open the file at all. Not a pytest test - run
manually:

    python tests/manual_verify_word_save.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.base import BREAK_MARKER, WordRun
from pipeline.word.docx_engine import DocxEngine, _w

DOCX_PATH = "2210 INERTIARA.docx"
OUTPUT_PATH = Path("tests/output/2210_INERTIARA_test.docx")
PARAGRAPH_INDEX = 10
_MEDIA_PREFIX = "word/media/"


def header_footer_text(path, part: str) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read(f"word/{part}")
    root = etree.fromstring(xml_bytes)
    return "".join(t.text or "" for t in root.iter(_w("t")))


def media_files(path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return {name for name in archive.namelist() if name.startswith(_MEDIA_PREFIX)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    engine = DocxEngine()
    engine.open(DOCX_PATH)
    original_paragraphs = engine.get_paragraphs()
    original_image_run = next(r for r in original_paragraphs[PARAGRAPH_INDEX].runs if r.is_image)

    test_runs = [
        original_image_run,
        WordRun(text="Überstülp-Titel", bold=True, underline=True),
        WordRun(text=BREAK_MARKER),
        WordRun(text=" Ärmelkanal ist größer als Straße "),
    ]
    engine.replace_paragraph_runs(PARAGRAPH_INDEX, test_runs)

    engine.save(str(OUTPUT_PATH), overwrite=True)
    print(f"Gespeichert: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")
    print()

    # --- overwrite protection check (separate from the main flow) ---
    try:
        engine.save(str(OUTPUT_PATH))
    except FileExistsError as exc:
        print(f"OK: save() ohne overwrite=True auf existierende Datei wirft FileExistsError: {exc}")
    else:
        print("FEHLER: save() ohne overwrite=True haette einen FileExistsError werfen muessen!")
    print()

    # --- reopen with a FRESH engine, not the in-memory one ---
    fresh_engine = DocxEngine()
    fresh_engine.open(str(OUTPUT_PATH))
    new_paragraphs = fresh_engine.get_paragraphs()

    checks: list[tuple[str, bool]] = []

    # (a) paragraph 10 has the new content
    p10 = new_paragraphs[PARAGRAPH_INDEX]
    image_runs = [r for r in p10.runs if r.is_image]
    checks.append(("Absatz 10: genau 1 Bild-Run", len(image_runs) == 1))
    checks.append(("Absatz 10: Bild-Run identisch zum Original", bool(image_runs) and image_runs[0] == original_image_run))

    bold_underline_run = next((r for r in p10.runs if r.text == "Überstülp-Titel"), None)
    checks.append(("Absatz 10: bold+underline korrekt", bold_underline_run is not None and bold_underline_run.bold and bold_underline_run.underline))

    space_run = next((r for r in p10.runs if "Ärmelkanal" in r.text), None)
    checks.append(("Absatz 10: Umlaute/Rand-Leerzeichen erhalten", space_run is not None and space_run.text == " Ärmelkanal ist größer als Straße "))

    has_break = any(r.text == BREAK_MARKER for r in p10.runs)
    checks.append(("Absatz 10: Break-Marker vorhanden", has_break))

    # (b) every OTHER paragraph unchanged
    unchanged_count = 0
    changed_indices: list[int] = []
    for i, (orig, new) in enumerate(zip(original_paragraphs, new_paragraphs)):
        if i == PARAGRAPH_INDEX:
            continue
        orig_text = "".join(r.text for r in orig.runs)
        new_text = "".join(r.text for r in new.runs)
        if orig_text == new_text:
            unchanged_count += 1
        else:
            changed_indices.append(i)
    checks.append((f"Alle anderen {len(original_paragraphs) - 1} Absaetze textlich unveraendert", not changed_indices))
    checks.append(("Absatzanzahl unveraendert", len(original_paragraphs) == len(new_paragraphs)))

    # (c) images in word/media/ all still present
    original_media = media_files(DOCX_PATH)
    new_media = media_files(OUTPUT_PATH)
    checks.append((f"word/media/ unveraendert ({len(original_media)} Dateien)", original_media == new_media))

    # (d) header/footer text identical
    for part in ("header2.xml", "footer1.xml"):
        original_text = header_footer_text(DOCX_PATH, part)
        new_text = header_footer_text(OUTPUT_PATH, part)
        checks.append((f"{part} Text unveraendert", original_text == new_text))

    # (e) python-docx can open the file at all
    try:
        from docx import Document

        Document(str(OUTPUT_PATH))
        checks.append(("python-docx kann die Datei oeffnen", True))
    except Exception as exc:
        checks.append((f"python-docx kann die Datei oeffnen (Fehler: {exc})", False))

    print("=== Regressionscheck ===")
    all_ok = True
    for label, ok in checks:
        all_ok = all_ok and ok
        print(f"  {'OK' if ok else 'FEHLER'}: {label}")

    if changed_indices:
        print()
        print(f"  Veraenderte Absaetze (ausser {PARAGRAPH_INDEX}): {changed_indices}")
        for i in changed_indices:
            print(f"    [{i}] original: {''.join(r.text for r in original_paragraphs[i].runs)!r}")
            print(f"    [{i}] neu:      {''.join(r.text for r in new_paragraphs[i].runs)!r}")

    if original_media != new_media:
        print()
        print(f"  nur im Original: {original_media - new_media}")
        print(f"  nur in der neuen Datei: {new_media - original_media}")

    print()
    print(f"GESAMTERGEBNIS: {'OK' if all_ok else 'FEHLGESCHLAGEN'}")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
