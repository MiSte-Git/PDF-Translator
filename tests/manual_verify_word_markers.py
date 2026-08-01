"""Verify that pipeline/word/html_bridge.py's tag-based markers
(<img data-run="n"/>, <br/>, <a data-run="n">) survive protect_terms() and
a real translation-provider round trip intact, across all four providers,
and that protect_terms() doesn't itself corrupt them when both kinds of
placeholder coexist in the same HTML. No write-back logic - purely
verification. Hits real translation APIs - run manually:

    python tests/manual_verify_word_markers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import html as lxml_html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from pipeline.translation.openai_provider import OpenAIProvider
from pipeline.translation.protected_terms import protect_terms
from pipeline.word.docx_engine import DocxEngine
from pipeline.word.html_bridge import paragraph_to_html

DOCX_PATH = "2210 INERTIARA.docx"
PROTECTED_TERMS = ["INERTIARA"]
TARGET_LANG = "de"
SOURCE_LANG = "en"
PARAGRAPH_INDICES = (10, 17)  # bundling case (image+breaks+bold) / multi-hyperlink case

PROVIDER_FACTORIES: list[tuple[str, type[TranslationProvider]]] = [
    ("DeepL", DeepLProvider),
    ("Google", GoogleTranslateProvider),
    ("OpenAI", OpenAIProvider),
    ("Grok", GrokProvider),
]


def _parse_fragment(html_string: str):
    """Parse an HTML fragment (possibly several sibling elements/plain
    text, not a full document) by wrapping it in a throwaway <div>.
    """
    return lxml_html.fromstring(f"<div>{html_string}</div>")


def marker_snapshot(html_string: str) -> dict[str, object]:
    """<img>/<a> data-run values (as lists, so duplicates aren't silently
    hidden by set-dedup) and the <br/> count, for comparing an original
    ParagraphHtml.html against a translated result.
    """
    root = _parse_fragment(html_string)
    return {
        "img_runs": [el.get("data-run") for el in root.iter("img")],
        "a_runs": [el.get("data-run") for el in root.iter("a")],
        "br_count": len(list(root.iter("br"))),
    }


def _sort_key(value: str | None) -> tuple[bool, str]:
    return (value is None, value or "")


def check_markers_intact(before: dict[str, object], after: dict[str, object]) -> tuple[bool, list[str]]:
    """Compare two marker_snapshot() results. Returns (ok, problems) -
    problems is a list of human-readable mismatch descriptions, empty if
    everything survived (both count AND the exact data-run value set).
    """
    problems: list[str] = []

    for tag, key in (("<img>", "img_runs"), ("<a>", "a_runs")):
        before_runs, after_runs = before[key], after[key]
        if len(before_runs) != len(after_runs):
            problems.append(f"{tag} Anzahl: {len(before_runs)} vorher -> {len(after_runs)} nachher")
        elif set(before_runs) != set(after_runs):
            problems.append(
                f"{tag} data-run Werte: {sorted(before_runs, key=_sort_key)} vorher "
                f"-> {sorted(after_runs, key=_sort_key)} nachher"
            )

    if before["br_count"] != after["br_count"]:
        problems.append(f"<br/> Anzahl: {before['br_count']} vorher -> {after['br_count']} nachher")

    return not problems, problems


def run_provider(
    name: str,
    provider: TranslationProvider,
    protected_html: str,
    before_snapshot: dict[str, object],
    results: list[tuple[int, str, bool, str]],
    paragraph_index: int,
) -> None:
    print(f"--- {name} ---")
    try:
        result = provider.translate_html(  # type: ignore[attr-defined]
            protected_html, target_lang=TARGET_LANG, source_lang=SOURCE_LANG
        )
    except TranslationError as exc:
        print(f"  TranslationError (uebersprungen): {exc}")
        print()
        results.append((paragraph_index, name, False, f"uebersprungen: {exc}"))
        return

    after_snapshot = marker_snapshot(result.text)
    ok, problems = check_markers_intact(before_snapshot, after_snapshot)
    print(f"  Marker intakt: {ok}")
    if not ok:
        for problem in problems:
            print(f"    - {problem}")
    print(f"  Uebersetztes HTML:\n  {result.text}")
    print()

    results.append((paragraph_index, name, ok, "; ".join(problems) if problems else ""))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = DocxEngine()
    engine.open(DOCX_PATH)
    paragraphs = engine.get_paragraphs()

    results: list[tuple[int, str, bool, str]] = []

    for index in PARAGRAPH_INDICES:
        paragraph = paragraphs[index]
        original = paragraph_to_html(paragraph)
        print(f"=== Absatz {index} ===")
        print(f"Original HTML:\n  {original.html}")
        print(f"image_runs: {original.image_runs}")
        print(f"hyperlink_targets: {original.hyperlink_targets}")
        print()

        protected_html, term_mapping = protect_terms(original.html, PROTECTED_TERMS)
        before_snapshot = marker_snapshot(original.html)
        after_protect_snapshot = marker_snapshot(protected_html)
        ok, problems = check_markers_intact(before_snapshot, after_protect_snapshot)
        if not ok:
            print(f"  WARNUNG: protect_terms() hat unsere Marker veraendert! {problems}")
        else:
            print(f"  protect_terms() laesst unsere Marker unangetastet (OK). Schutzbegriff-Platzhalter: {list(term_mapping.keys())}")
        print()

        for provider_name, factory in PROVIDER_FACTORIES:
            run_provider(provider_name, factory(), protected_html, before_snapshot, results, index)

        print()

    print("=== Ergebnis-Tabelle ===")
    header = f"{'Absatz':<8} {'Provider':<10} {'Marker intakt':<14} Details"
    print(header)
    print("-" * len(header))
    for paragraph_index, provider_name, ok, details in results:
        status = "ja" if ok else "nein"
        print(f"{paragraph_index:<8} {provider_name:<10} {status:<14} {details}")


if __name__ == "__main__":
    main()
