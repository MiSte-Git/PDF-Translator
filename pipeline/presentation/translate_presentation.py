"""Provider-agnostic PPTX translation orchestration.

This module mutates only existing run text through :class:`PptxEngine`.  Opening,
saving and budget confirmation remain caller responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import html
from typing import Callable

from pipeline.presentation.html_bridge import (
    paragraph_to_html,
    run_has_translatable_text,
    translated_run_texts,
)
from pipeline.presentation.pptx_engine import PptxEngine
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.protected_terms import protect_terms, restore_terms


@dataclass
class PresentationTranslationStats:
    paragraphs_translated: int = 0
    paragraphs_skipped: int = 0
    paragraphs_failed: int = 0
    chars_sent: int = 0
    errors: list[str] = field(default_factory=list)


def collect_translatable_html(
    engine: PptxEngine, slide_paths: set[str] | None = None
) -> list[str]:
    """Return provider payloads for cost estimation without translating."""
    payloads: list[str] = []
    for container in engine.get_text_containers():
        if not container.translatable:
            continue
        if slide_paths is not None and container.slide_path not in slide_paths:
            continue
        for paragraph in container.paragraphs:
            converted = paragraph_to_html(paragraph)
            if any(run_has_translatable_text(run.text) for run in paragraph.runs):
                payloads.append(converted.html)
    return payloads


def translate_presentation(
    engine: PptxEngine,
    provider: TranslationProvider,
    protected_terms: list[str],
    target_lang: str,
    source_lang: str | None = None,
    progress_callback: Callable[[str], None] | None = None,
    slide_paths: set[str] | None = None,
) -> PresentationTranslationStats:
    stats = PresentationTranslationStats()
    for container_index, container in enumerate(engine.get_text_containers()):
        if not container.translatable:
            stats.paragraphs_skipped += len(container.paragraphs)
            continue
        if slide_paths is not None and container.slide_path not in slide_paths:
            continue
        for paragraph_index, paragraph in enumerate(container.paragraphs):
            if not any(run_has_translatable_text(run.text) for run in paragraph.runs):
                stats.paragraphs_skipped += 1
                continue
            original = paragraph_to_html(paragraph)
            protected_html, mapping = protect_terms(original.html, protected_terms)
            if progress_callback:
                progress_callback(
                    f"{container.slide_path} shape={container.shape_id} paragraph={paragraph_index}"
                )
            try:
                result = provider.translate_html(
                    protected_html, target_lang=target_lang, source_lang=source_lang
                )
                stats.chars_sent += len(protected_html)
                restored = restore_terms(result.text, mapping)
                try:
                    texts_by_run = translated_run_texts(restored, original)
                except ValueError:
                    # Some providers merge/reorder adjacent span tags in a
                    # complex paragraph. Fall back to translating each
                    # linguistic run independently; original OOXML formatting
                    # and all non-linguistic runs remain untouched.
                    texts_by_run = {}
                    for run_index in original.run_indices:
                        run_html = (
                            f'<span data-run="{run_index}">'
                            f'{html.escape(paragraph.runs[run_index].text, quote=False)}</span>'
                        )
                        protected_run, run_mapping = protect_terms(run_html, protected_terms)
                        run_result = provider.translate_html(
                            protected_run, target_lang=target_lang, source_lang=source_lang
                        )
                        stats.chars_sent += len(protected_run)
                        restored_run = restore_terms(run_result.text, run_mapping)
                        run_original = type(original)(protected_run, (run_index,), 0)
                        texts_by_run.update(translated_run_texts(restored_run, run_original))
            except (TranslationError, ValueError) as exc:
                stats.paragraphs_failed += 1
                stats.errors.append(
                    f"{container.slide_path} shape={container.shape_id} "
                    f"paragraph={paragraph_index}: {type(exc).__name__}: {exc}"
                )
                continue

            for run_index, text in texts_by_run.items():
                engine.set_run_text(paragraph.runs[run_index], text)
            stats.paragraphs_translated += 1
    return stats
