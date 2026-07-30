"""Provider-agnostic interface for external translation services (DeepL, Google, OpenAI)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class TranslationError(Exception):
    """Raised when a translation provider fails: missing/invalid credentials,
    an API error, or an unexpected response. Providers should raise this
    (not a provider-specific exception) so callers can handle failures
    uniformly regardless of which provider is in use.
    """


@dataclass
class TranslationResult:
    """Result of a single translation call, independent of the provider used."""
    text: str
    source_lang: str
    target_lang: str
    provider: str


@runtime_checkable
class TranslationProvider(Protocol):
    """Minimal interface every translation provider (DeepL/Google/OpenAI) must implement."""

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `text` into `target_lang`.

        `source_lang` is optional since some providers (e.g. DeepL) support
        automatic source language detection.
        """
        ...
