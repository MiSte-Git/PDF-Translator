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
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def paragraphs_processed(self) -> int:
        """Paragraphs the run has already reached a final outcome for
        (translated, skipped or failed) - used by callers to drive a
        progress display without needing their own counter.
        """
        return self.paragraphs_translated + self.paragraphs_skipped + self.paragraphs_failed

    # Format-agnostic aliases (translated/skipped/failed/processed) so
    # ui/app.py's job-status code (_job_stats()/_update_job_status()/
    # _show_job_result()) can read either this class or
    # pipeline.word.translate_document.TranslationStats through the same
    # attribute names, without an isinstance branch at every call site.
    # The paragraphs_*-prefixed names above stay the primary ones (existing
    # callers keep using them); these are purely additive.
    @property
    def translated(self) -> int:
        return self.paragraphs_translated

    @property
    def skipped(self) -> int:
        return self.paragraphs_skipped

    @property
    def failed(self) -> int:
        return self.paragraphs_failed

    @property
    def processed(self) -> int:
        return self.paragraphs_processed


def total_paragraph_count(engine: PptxEngine) -> int:
    """Total number of paragraphs translate_presentation() will eventually
    report a final outcome for (translated, skipped or failed), across every
    container - translatable or not. Lets a caller show a determinate "X of
    N paragraphs" progress bar instead of an indeterminate one, without
    duplicating translate_presentation()'s own traversal logic; cheap (no
    API calls), so it's safe to call once right before starting a run.
    """
    return sum(len(container.paragraphs) for container in engine.get_text_containers())


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
    should_cancel: Callable[[], bool] | None = None,
    stats_callback: Callable[[PresentationTranslationStats], None] | None = None,
) -> PresentationTranslationStats:
    """Translate every translatable paragraph in-place via ``provider``.

    ``should_cancel`` is polled before each paragraph (i.e. between API
    calls, never mid-call) so a caller - typically a UI cancel button - can
    stop the run promptly without corrupting an in-flight request. Once it
    returns True, ``stats.cancelled`` is set and the run stops; every
    paragraph already translated stays translated (a clearly labelled
    partial result), remaining paragraphs are left untouched in the engine.

    ``stats_callback``, if given, is called after every paragraph reaches a
    final outcome (translated/skipped/failed) with the current cumulative
    ``stats``, letting a caller drive a live progress display (paragraphs
    processed, characters sent so far) without polling.
    """
    stats = PresentationTranslationStats()
    for container_index, container in enumerate(engine.get_text_containers()):
        if should_cancel is not None and should_cancel():
            stats.cancelled = True
            break
        if not container.translatable:
            stats.paragraphs_skipped += len(container.paragraphs)
            if stats_callback:
                stats_callback(stats)
            continue
        if slide_paths is not None and container.slide_path not in slide_paths:
            continue
        for paragraph_index, paragraph in enumerate(container.paragraphs):
            if should_cancel is not None and should_cancel():
                stats.cancelled = True
                break
            if not any(run_has_translatable_text(run.text) for run in paragraph.runs):
                stats.paragraphs_skipped += 1
                if stats_callback:
                    stats_callback(stats)
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
                if stats_callback:
                    stats_callback(stats)
                continue

            for run_index, text in texts_by_run.items():
                engine.set_run_text(paragraph.runs[run_index], text)
            stats.paragraphs_translated += 1
            if stats_callback:
                stats_callback(stats)
        if stats.cancelled:
            break
    return stats
