"""Format-agnostic pieces shared by every per-format UI job module
(ui/pptx_job.py, ui/word_job.py, and future ui/pdf_job.py).

Deliberately small: provider construction, destination safety, and the
conflict-error type are the only parts that don't depend on which document
format is being translated. Everything format-specific (which engine to
open, which translate_*() function to call, what a QA report should say)
stays in that format's own job module rather than being folded into one
generic "document job" abstraction here - PPTX's overflow-risk comparison
and Word's header/footer/break-marker concerns don't map onto each other
cleanly enough to be worth forcing into a shared code path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from pipeline.translation.base import TranslationProvider
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from pipeline.translation.openai_provider import OpenAIProvider

PROVIDER_FACTORIES: dict[str, Callable[[], TranslationProvider]] = {
    "deepl": DeepLProvider,
    "google": GoogleTranslateProvider,
    "openai": OpenAIProvider,
    "grok": GrokProvider,
}


class DestinationConflictError(ValueError):
    """The chosen output path is unsafe: same as the source, or already
    exists. Raised before any translation API call is made.
    """


def build_provider(name: str) -> TranslationProvider:
    try:
        factory = PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ValueError(f"Unbekannter Übersetzungsanbieter: {name!r}") from exc
    return factory()


def safe_destination(source: Path, target_lang: str, output_dir: Path | None = None) -> Path:
    """Propose a destination filename that can never collide with the
    source: the target language is always appended, and a numeric suffix is
    added if that name is already taken in the chosen directory. Source and
    destination identity is still re-checked technically in each job
    module's run_*_job()/*.save() before anything is written. Format-
    agnostic (only uses source.suffix), so it's shared as-is rather than
    duplicated per format.
    """
    source = Path(source)
    directory = Path(output_dir) if output_dir is not None else source.parent
    tag = "".join(char for char in target_lang.strip().upper() if char.isalnum()) or "TRANSLATED"
    base_name = f"{source.stem}_{tag}"
    resolved_source = source.resolve()
    candidate = directory / f"{base_name}{source.suffix}"
    counter = 2
    while candidate.exists() or candidate.resolve() == resolved_source:
        candidate = directory / f"{base_name} ({counter}){source.suffix}"
        counter += 1
    return candidate
