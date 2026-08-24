"""One-off PROBE script: run PaddleOCR's PP-StructureV3 layout analysis on a
single image and dump what it recognizes, to compare its paragraph/block
grouping against our own pipeline.images.ocr.merge_lines_into_paragraphs()
heuristic (RoadMap.md/Backlog.md, 22.08.2026 - "Wechsel prüfen" nach dem
Vergleich mit Googles Bild-Uebersetzung).

NOT part of the shipping OcrEngine backends (pipeline/images/ocr.py) and NOT
wired into pipeline/registry.py - purely a throwaway evaluation tool to
answer one question before any real integration work starts: does
PP-StructureV3's layout model produce meaningfully better paragraph
grouping than our geometric heuristic on Michael's real, dense infographic?

Must be run HERE on your own machine, not in the sandbox this was written
in - PP-StructureV3 downloads its models on first use from HuggingFace/
ModelScope/AIStudio/BOS, and the sandbox's network allowlist blocks all
four of those hosts (confirmed 22.08.2026: every one of them refused the
proxy CONNECT). Your machine has normal internet access, so the download
should just work here.

Install (one-time, pulls PaddlePaddle + PaddleOCR + the OCR/layout model
extras - a few hundred MB total, downloaded on first run):
    pip install paddlepaddle paddleocr "paddlex[ocr]"

Usage:
    python tools/probe_paddleocr.py "Spirit - Soul - Meatsuit.jpg"
    python tools/probe_paddleocr.py "Spirit - Soul - Meatsuit.jpg" --output-dir paddle_probe_out

Writes into --output-dir (default: paddle_probe_out/ next to this script's
cwd):
    - a visualized copy of the image with every detected layout/paragraph
      box drawn and labelled (PP-StructureV3's own save_to_img())
    - the full structured result as JSON (save_to_json())
and prints a short block-count-by-category summary to stdout, so the
result can be judged/compared without opening every file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="Pfad zum zu testenden Bild (z.B. das echte Infografik-Bild)")
    parser.add_argument(
        "--output-dir",
        default="paddle_probe_out",
        help="Zielordner fuer visualisiertes Bild + JSON (Default: paddle_probe_out)",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Bild nicht gefunden: {image_path}", file=sys.stderr)
        return 1

    try:
        from paddleocr import PPStructureV3
    except ImportError as exc:
        print(
            f"PaddleOCR-Abhaengigkeit fehlt ({exc}). Erst installieren:\n"
            '    pip install paddlepaddle paddleocr "paddlex[ocr]"',
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Baue PP-StructureV3-Pipeline auf (laedt Modelle beim allerersten Mal herunter)...")
    pipeline = PPStructureV3(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    print(f"Analysiere {image_path} ...")
    results = pipeline.predict(str(image_path))

    category_counts: dict[str, int] = {}
    for result in results:
        result.save_to_json(str(output_dir))
        result.save_to_img(str(output_dir))
        for block in result.get("parsing_res_list", []) or []:
            label = getattr(block, "label", None) or block.get("block_label", "?")
            category_counts[label] = category_counts.get(label, 0) + 1

    print()
    print(f"Ergebnisse geschrieben nach: {output_dir}/")
    print("Erkannte Layout-Bloecke nach Kategorie:")
    if category_counts:
        for label, count in sorted(category_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {label}: {count}")
        print(f"  GESAMT: {sum(category_counts.values())}")
    else:
        print("  (keine 'parsing_res_list'-Struktur gefunden - siehe JSON-Datei fuer die Rohdaten)")

    print()
    print(
        "Zum Vergleich: unsere eigene Absatz-Merge-Heuristik "
        "(merge_lines_into_paragraphs) kommt auf diesem Bild von 82 auf 59 "
        "Uebersetzungs-Bloecke. Bitte das visualisierte Bild in "
        f"{output_dir}/ mit real_output_fixed2.jpg vergleichen: gruppiert "
        "PP-StructureV3 die Absaetze im dichten rechten Bereich/unteren "
        "Zitatblock zuverlaessiger?"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
