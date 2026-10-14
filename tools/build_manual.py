"""Build the user manual PDFs (docs/pdf/manual-<lang>.pdf) from
docs/<lang>/manual.md for every UI language.

14.10.2026 (Michael: "Dann sollten wir das pdf in alle Sprachen uebersetzen
und in der App verlinken"): the manual exists in all nine UI languages
(see ui/i18n_data.py::LOCALES); ui/app.py's Hilfe -> Benutzerhandbuch opens
docs/pdf/manual-<current language>.pdf (falls back to English, then German).

The PDFs are committed to the repo on purpose: the release is a plain
`git archive` of HEAD (see .github/workflows/build-bootstrap.yml), and the
installed app has no pandoc/LaTeX to build them itself.

Requirements (build machine only): pandoc and xelatex (TeX Live), plus the
DejaVu fonts - DejaVu Sans covers Latin and Cyrillic, so the Russian manual
needs no separate font.

Usage:
    python tools/build_manual.py            # all languages
    python tools/build_manual.py de en      # only these
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT_DIR = DOCS / "pdf"
LANGUAGES = ("de", "en", "fr", "es", "it", "nl", "fi", "hr", "ru")


def build(lang: str) -> Path:
    source = DOCS / lang / "manual.md"
    target = OUT_DIR / f"manual-{lang}.pdf"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pandoc",
            str(source),
            "--from=markdown",
            "--pdf-engine=xelatex",
            f"--resource-path={source.parent}",
            "-V", "mainfont=DejaVu Sans",
            "-V", "monofont=DejaVu Sans Mono",
            "-V", "papersize=a4",
            "-V", "geometry:margin=2.2cm",
            "-V", "colorlinks=true",
            "-V", "linkcolor=blue",
            "-V", "urlcolor=blue",
            "-o", str(target),
        ],
        check=True,
    )
    return target


def main(argv: list[str]) -> int:
    languages = argv or list(LANGUAGES)
    unknown = [lang for lang in languages if lang not in LANGUAGES]
    if unknown:
        print(f"Unknown language(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    for lang in languages:
        print(f"Building {build(lang).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
