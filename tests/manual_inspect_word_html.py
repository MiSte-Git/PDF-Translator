"""Ad-hoc script to inspect paragraph_to_html() output for a Word document.

Analog to tests/manual_inspect_word_blocks.py, one layer up: loads a .docx
via DocxEngine, then for every translatable paragraph shows the HTML
paragraph_to_html() built plus its marker -> run lookups (image_runs,
hyperlink_targets). Not a pytest test - run manually:

    python tests/manual_inspect_word_html.py path/to/file.docx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import paragraph_to_html


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python tests/manual_inspect_word_html.py path/to/file.docx")
        sys.exit(1)

    docx_path = sys.argv[1]

    engine = DocxEngine()
    engine.open(docx_path)

    for index, paragraph in enumerate(engine.get_paragraphs()):
        if not paragraph.translatable:
            continue

        result = paragraph_to_html(paragraph)
        print(f"=== paragraph {index} ===")
        print(f"html: {result.html!r}")
        if result.image_runs:
            for marker, run in result.image_runs.items():
                print(f"  image_runs[{marker!r}] = WordRun(is_image=True, ...)")
        if result.hyperlink_targets:
            for marker, target in result.hyperlink_targets.items():
                print(f"  hyperlink_targets[{marker!r}] = {target!r}")
        print()

    if not engine.separator_found:
        print(
            "WARNUNG: kein straightConnector1-Trennstrich-Shape gefunden - "
            "Seite-1-Metadatenblock konnte nicht erkannt werden, alle "
            "Absaetze bleiben translatable=True. Sonderfall pruefen."
        )


if __name__ == "__main__":
    main()
