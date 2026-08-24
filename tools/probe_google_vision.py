"""One-off PROBE script: run Google Cloud Vision's DOCUMENT_TEXT_DETECTION
on a single image and dump the paragraph/block boxes it recognizes, to
compare against our own pipeline.images.ocr.merge_lines_into_paragraphs()
heuristic and against tools/probe_paddleocr.py's result (RoadMap.md/
Backlog.md, 22.08.2026 - "Wechsel pruefen" nach dem Vergleich mit Googles
Bild-Uebersetzung).

NOT part of the shipping OcrEngine backends (pipeline/images/ocr.py) and
NOT wired into pipeline/registry.py - purely a throwaway evaluation tool,
same purpose as tools/probe_paddleocr.py but for the cloud candidate
instead of the local one.

Reuses the EXISTING Google API key (pipeline.credentials.
get_google_translate_api_key() - Michael confirmed 22.08.2026 that the
same key already has both Cloud Translation and Vision enabled, so no new
credential needs to be configured). The key is never printed or written to
any output file here.

Cannot be run from the sandbox this was written in - vision.googleapis.com
is blocked by the sandbox's network allowlist (confirmed 22.08.2026, same
as googleapis.com generally). Must be run here, on your own machine.

Usage:
    python tools/probe_google_vision.py "Spirit - Soul - Meatsuit.jpg"
    python tools/probe_google_vision.py "Spirit - Soul - Meatsuit.jpg" --output-dir vision_probe_out

Writes into --output-dir (default: vision_probe_out/):
    - a visualized copy of the image with every detected PARAGRAPH box
      drawn and numbered in reading order (the granularity comparable to
      our own merge_lines_into_paragraphs() output and to PP-StructureV3's
      text/paragraph_title blocks)
    - the raw Vision API response as JSON
and prints a short summary (block count, paragraph count, average
confidence) to stdout.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_API_URL = "https://vision.googleapis.com/v1/images:annotate"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="Pfad zum zu testenden Bild (z.B. das echte Infografik-Bild)")
    parser.add_argument(
        "--output-dir",
        default="vision_probe_out",
        help="Zielordner fuer visualisiertes Bild + JSON (Default: vision_probe_out)",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Bild nicht gefunden: {image_path}", file=sys.stderr)
        return 1

    try:
        import requests
        from PIL import Image, ImageDraw
    except ImportError as exc:
        print(f"Abhaengigkeit fehlt: {exc}", file=sys.stderr)
        return 1

    from pipeline.credentials import get_google_translate_api_key

    try:
        api_key = get_google_translate_api_key()
    except RuntimeError as exc:
        print(f"Kein Google-API-Key gefunden: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Sende {image_path} an die Cloud Vision API (DOCUMENT_TEXT_DETECTION) ...")
    image_bytes = image_path.read_bytes()
    body = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }
        ]
    }
    try:
        response = requests.post(_API_URL, params={"key": api_key}, json=body, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Vision-API-Aufruf fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    data = response.json()
    (output_dir / f"{image_path.stem}_res.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    result = (data.get("responses") or [{}])[0]
    if "error" in result:
        print(f"Vision-API meldete einen Fehler: {result['error']}", file=sys.stderr)
        return 1

    full_text = result.get("fullTextAnnotation") or {}
    pages = full_text.get("pages") or []
    if not pages:
        print("Keine fullTextAnnotation in der Antwort - siehe JSON fuer die Rohdaten.")
        return 0

    blocks = pages[0].get("blocks") or []
    paragraphs: list[dict] = []
    confidences: list[float] = []
    for block in blocks:
        for paragraph in block.get("paragraphs") or []:
            paragraphs.append(paragraph)
            conf = paragraph.get("confidence")
            if conf is not None:
                confidences.append(conf)

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        draw = ImageDraw.Draw(image)
        for index, paragraph in enumerate(paragraphs, start=1):
            vertices = paragraph.get("boundingBox", {}).get("vertices") or []
            xs = [v.get("x", 0) for v in vertices]
            ys = [v.get("y", 0) for v in vertices]
            if not xs or not ys:
                continue
            box = (min(xs), min(ys), max(xs), max(ys))
            draw.rectangle(box, outline=(255, 0, 0), width=3)
            draw.text((box[0] + 2, box[1] + 2), str(index), fill=(255, 0, 0))
        vis_path = output_dir / f"{image_path.stem}_paragraphs_vis.jpg"
        image.save(vis_path)

    avg_confidence = sum(confidences) / len(confidences) if confidences else None

    print()
    print(f"Ergebnisse geschrieben nach: {output_dir}/")
    print(f"Erkannte Bloecke (Vision 'block'-Ebene): {len(blocks)}")
    print(f"Erkannte Absaetze (Vision 'paragraph'-Ebene, die Vergleichsgroesse): {len(paragraphs)}")
    if avg_confidence is not None:
        print(f"Durchschnittliche Absatz-Konfidenz: {avg_confidence:.2f}")
    print()
    print(
        "Zum Vergleich: unsere eigene Absatz-Merge-Heuristik "
        "(merge_lines_into_paragraphs) kommt auf diesem Bild von 82 auf 59 "
        "Uebersetzungs-Bloecke, PP-StructureV3 (tools/probe_paddleocr.py) "
        "auf 58. Visualisiertes Bild in "
        f"{vis_path} anschauen: sind die Absatz-Boxen im dichten rechten "
        "Bereich/unteren Zitatblock sauber getrennt (keine ueber mehrere "
        "Karten hinweg zusammengezogenen Boxen)?"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
