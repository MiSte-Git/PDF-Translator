"""Einmaliges DIAGNOSE-Skript (23.08.2026): PaddleOcrEngine
(pipeline/images/ocr.py) fand beim echten App-Lauf gegen
"Spirit - Soul - Meatsuit.jpg" 0 Textregionen (QA-Bericht "(11)":
"Erkannte Textregionen: 0"), obwohl tools/probe_paddleocr.py am selben
Bild zuvor 58 Layout-Bloecke gefunden hatte - allerdings ueber
save_to_json() (serialisiert). Bereits ZWEIMAL zuvor hat sich gezeigt
(siehe Backlog.md, 23.08.2026), dass das rohe, nicht-serialisierte
Python-Ergebnis von pipeline.predict() anders aussieht als die
JSON-Fassung: erst numpy-Arrays statt Listen (rec_boxes/rec_scores),
dann `LayoutBlock`-Objekte mit Attributen statt Dict-Keys
(parsing_res_list). Statt ein DRITTES Mal zu raten, welches Feld
diesmal anders heisst oder fehlt, druckt dieses Skript die ECHTEN
Attribut-/Key-Namen des Live-Objekts direkt aus - kein Umweg mehr ueber
JSON.

Nicht Teil der shipping OcrEngine-Backends, rein zur Fehlersuche.

Usage:
    python tools/probe_paddleocr_shape.py "Spirit - Soul - Meatsuit.jpg"

Die Ausgabe (Typnamen, Attribut-/Key-Listen, ggf. der erste Block im
Detail) bitte einfach komplett hierher kopieren.
"""
from __future__ import annotations

import sys


def _dump(label: str, obj: object) -> None:
    print(f"\n--- {label}: {type(obj)!r} ---")
    if isinstance(obj, dict):
        print("  ist ein dict, keys:", list(obj.keys()))
        return
    if isinstance(obj, (list, tuple)):
        print(f"  ist eine Liste/Tuple, Laenge {len(obj)}")
        return
    public_attrs = [a for a in dir(obj) if not a.startswith("_")]
    print("  ist KEIN dict - oeffentliche Attribute/Methoden:", public_attrs)
    if hasattr(obj, "__dict__"):
        try:
            print("  vars():", vars(obj))
        except Exception as exc:  # manche PaddleX-Objekte ueberladen __dict__ ungewoehnlich
            print(f"  vars() fehlgeschlagen: {exc}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/probe_paddleocr_shape.py <Bildpfad>", file=sys.stderr)
        return 1
    image_path = sys.argv[1]

    from paddleocr import PPStructureV3

    pipeline = PPStructureV3(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    results = list(pipeline.predict(image_path))
    if not results:
        print("predict() lieferte gar kein Ergebnis (leere Liste).")
        return 0
    result = results[0]
    _dump("result (results[0])", result)

    # result.get() lief in den vorherigen echten Laeufen fehlerfrei -
    # trotzdem defensiv: dict ODER Attribut probieren.
    def get(obj, key):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    parsing = get(result, "parsing_res_list")
    print(f"\nparsing_res_list: type={type(parsing)!r}, "
          f"len={len(parsing) if parsing is not None else 'None (Schluessel/Attribut fehlt!)'}")
    if parsing:
        _dump("parsing_res_list[0] (erster Block)", parsing[0])
        # Die drei Felder, auf die PaddleOcrEngine sich aktuell verlaesst
        # (echte Attributnamen, bestaetigt 23.08.2026 - siehe
        # pipeline/images/ocr.py::_PADDLE_BLOCK_FIELD_ALIASES):
        for field in ("label", "bbox", "content"):
            print(f"    {field} -> {get(parsing[0], field)!r}")
        print("\n  Alle Labels in parsing_res_list (Haeufigkeit):")
        from collections import Counter
        label_counts = Counter(get(block, "label") for block in parsing)
        for label, count in sorted(label_counts.items(), key=lambda kv: -kv[1]):
            print(f"    {label!r}: {count}")

    # 23.08.2026-Hypothese (Backlog.md, QA-Bericht "(12)"): ein ganzer
    # Abschnitt wurde nicht uebersetzt - PaddleOcrEngine liest NUR
    # parsing_res_list, aber LayoutParsingResultV2 hat eigene Listen fuer
    # chart/table/seal/formula-Inhalte. Falls der fehlende Abschnitt dort
    # gelandet ist statt in parsing_res_list, taucht er hier auf:
    for extra_key in ("chart_res_list", "table_res_list", "seal_res_list", "formula_res_list"):
        extra = get(result, extra_key)
        length = len(extra) if extra is not None else "None (Schluessel/Attribut fehlt!)"
        print(f"\n{extra_key}: type={type(extra)!r}, len={length}")
        if extra:
            _dump(f"{extra_key}[0]", extra[0])

    overall = get(result, "overall_ocr_res")
    _dump("overall_ocr_res", overall)
    if overall is not None:
        for field in ("rec_texts", "rec_scores", "rec_boxes"):
            val = get(overall, field)
            length = len(val) if val is not None else "None (Schluessel/Attribut fehlt!)"
            print(f"    {field} -> type={type(val)!r}, len={length}")
            if val is not None and len(val) > 0:
                print(f"      erstes Element: {val[0]!r}")

        # 23.08.2026-Hypothese (Backlog.md, QA-Bericht "(12)"): das
        # Kelch-Symbol zwischen den zwei Fusszeilen-Boxen wurde als Text
        # "AND"/"UND" erkannt und uebersetzt gerendert - das waere eine
        # Fehlerkennung der TEXT-Detektion selbst (nicht der Layout-
        # Klassifikation), also hier in overall_ocr_res sichtbar. Sucht
        # nach jeder kurzen "and"-aehnlichen Zeile und druckt ihre Box.
        texts = get(overall, "rec_texts") or []
        boxes = get(overall, "rec_boxes")
        boxes = [] if boxes is None else boxes
        print("\n  Kurze rec_texts-Zeilen, die wie 'and' aussehen (Verdacht: Kelch-Icon):")
        found_suspect = False
        for text, box in zip(texts, boxes):
            if text.strip().lower() in ("and", "und", "&"):
                print(f"    {text!r} bei bbox {list(box)!r}")
                found_suspect = True
        if not found_suspect:
            print("    (keine gefunden - falls das Problem trotzdem auftrat, "
                  "steckt es vermutlich in der Layout-Klassifikation, nicht "
                  "in der Text-Detektion)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
