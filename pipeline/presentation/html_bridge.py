"""Strict HTML bridge for translating PPTX paragraphs without rebuilding OOXML.

Every existing DrawingML run is wrapped in an identity-bearing ``span``.
Providers may translate text inside the span but must preserve all span and
line-break markers.  The result maps back to the original ``<a:t>`` nodes.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

from lxml import html as lxml_html

from pipeline.presentation.base import PresentationParagraph

_URL_RE = re.compile(r"^(?:https?://|www\.|mailto:)", re.IGNORECASE)


@dataclass(frozen=True)
class ParagraphHtml:
    html: str
    run_indices: tuple[int, ...]
    break_count: int


def run_has_translatable_text(text: str) -> bool:
    """Exclude symbol-/punctuation-only runs while keeping human language."""
    stripped = text.strip()
    if not stripped or _URL_RE.match(stripped):
        return False
    return any(character.isalpha() for character in stripped)


def paragraph_to_html(paragraph: PresentationParagraph) -> ParagraphHtml:
    parts: list[str] = []
    run_indices: list[int] = []
    breaks_by_position: dict[int, list[int]] = {}
    for break_id, position in enumerate(paragraph.break_positions):
        breaks_by_position.setdefault(position, []).append(break_id)

    for run_index, run in enumerate(paragraph.runs):
        for break_id in breaks_by_position.get(run_index, []):
            parts.append(f'<br data-break="{break_id}"/>')
        if run_has_translatable_text(run.text):
            run_indices.append(run_index)
            parts.append(
                f'<span data-run="{run_index}">{html.escape(run.text, quote=False)}</span>'
            )
    for break_id in breaks_by_position.get(len(paragraph.runs), []):
        parts.append(f'<br data-break="{break_id}"/>')
    return ParagraphHtml(
        "".join(parts), tuple(run_indices), len(paragraph.break_positions)
    )


def translated_run_texts(translated_html: str, original: ParagraphHtml) -> dict[int, str]:
    root = lxml_html.fromstring(f"<div>{translated_html}</div>")
    spans = list(root.iter("span"))
    found_runs = [span.get("data-run") for span in spans]
    expected_runs = [str(index) for index in original.run_indices]
    if found_runs != expected_runs:
        raise ValueError(
            f"PPTX run markers changed during translation: found {found_runs}, "
            f"expected {expected_runs}"
        )

    breaks = list(root.iter("br"))
    found_breaks = [node.get("data-break") for node in breaks]
    expected_breaks = [str(index) for index in range(original.break_count)]
    if found_breaks != expected_breaks:
        raise ValueError(
            f"PPTX break markers changed during translation: found {found_breaks}, "
            f"expected {expected_breaks}"
        )

    if root.text and root.text.strip():
        raise ValueError("Translated HTML contains text outside PPTX run markers")
    for child in root:
        if child.tail and child.tail.strip():
            raise ValueError("Translated HTML contains text outside PPTX run markers")
    return {
        int(span.get("data-run")): span.text_content()
        for span in spans
    }
