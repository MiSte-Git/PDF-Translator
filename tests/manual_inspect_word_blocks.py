"""Ad-hoc script to inspect the paragraphs extracted from a Word document.

Analog to tests/manual_inspect_blocks.py (the PDF counterpart). Not a
pytest test - run manually to eyeball extraction/translatable results:

    python tests/manual_inspect_word_blocks.py path/to/file.docx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.word.base import WordParagraph
from pipeline.word.docx_engine import DocxEngine


def _paragraph_text(paragraph: WordParagraph) -> str:
    return "".join(run.text for run in paragraph.runs)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python tests/manual_inspect_word_blocks.py path/to/file.docx")
        sys.exit(1)

    docx_path = sys.argv[1]

    engine = DocxEngine()
    engine.open(docx_path)

    for index, paragraph in enumerate(engine.get_paragraphs()):
        text = _paragraph_text(paragraph).replace("\n", " ")
        if len(text) > 60:
            text = text[:60] + "..."

        image_count = sum(1 for run in paragraph.runs if run.is_image)
        hyperlink_runs = [run for run in paragraph.runs if run.is_hyperlink]
        targets = ", ".join(sorted({run.hyperlink_target or "" for run in hyperlink_runs}))

        hyperlink_info = f"{len(hyperlink_runs)}"
        if hyperlink_runs:
            hyperlink_info += f" ({targets})"

        print(
            f"index={index:>3} | translatable={str(paragraph.translatable):<5} | "
            f"images={image_count} | hyperlinks={hyperlink_info} | text=\"{text}\""
        )

    if not engine.separator_found:
        print()
        print(
            "WARNUNG: kein straightConnector1-Trennstrich-Shape gefunden - "
            "Seite-1-Metadatenblock konnte nicht erkannt werden, alle "
            "Absaetze bleiben translatable=True. Sonderfall pruefen."
        )


if __name__ == "__main__":
    main()
