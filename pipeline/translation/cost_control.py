"""Cost estimation, logging, and hard limiting for translation API usage.

Wraps any TranslationProvider (see base.py) so a caller can see an upfront
cost estimate, get a confirmation prompt, and be protected by a hard
per-run character cap, before/while the wrapped provider is actually used.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Callable

from pipeline.translation.base import TranslationError, TranslationProvider, TranslationResult

# Google Cloud Translation Basic (v2) pricing, as of 2026. Adjust here if
# pricing changes or a different provider's pricing should be modeled.
COST_PER_MILLION_CHARS = 20.0  # USD
FREE_TIER_CHARS_PER_MONTH = 500_000

# Hard ceiling on characters translated by one TranslationBudgetGuard
# instance (i.e. one pipeline run), overridable per instance.
DEFAULT_MAX_CHARS_PER_RUN = 200_000

# Local, per-machine usage log - not committed to the repo (see .gitignore).
_USAGE_LOG_PATH = Path(__file__).resolve().parent / ".usage_log.json"


class BudgetExceededError(TranslationError):
    """Raised by TranslationBudgetGuard.translate()/translate_html() when
    translating a text would push this run's cumulative character count
    past max_chars_per_run. The wrapped provider is never called in this
    case.
    """


class TranslationHtmlNotSupportedError(TranslationError):
    """Raised by TranslationBudgetGuard.translate_html() when the wrapped
    provider has no translate_html() method (HTML-aware translation isn't
    part of the TranslationProvider protocol, so not every provider has one).
    """


def _current_month_key() -> str:
    """Return the current calendar month as 'YYYY-MM'."""
    return date.today().strftime("%Y-%m")


def _read_usage_log() -> dict[str, dict[str, int]]:
    """Read the persistent usage log, or {} if it doesn't exist/is invalid."""
    if not _USAGE_LOG_PATH.exists():
        return {}
    try:
        return json.loads(_USAGE_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_month_usage(month_key: str | None = None) -> int:
    """Return characters already logged for `month_key` (default: current
    month), or 0 if nothing is logged for it yet.
    """
    month_key = month_key or _current_month_key()
    return _read_usage_log().get(month_key, {}).get("characters", 0)


def log_usage(char_count: int) -> None:
    """Add `char_count` to the current month's usage total in the
    persistent usage log (creating the file/month entry if needed).
    """
    data = _read_usage_log()
    month_key = _current_month_key()
    month_data = data.setdefault(month_key, {"characters": 0})
    month_data["characters"] += char_count
    _USAGE_LOG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def estimate_cost(char_count: int, already_used_this_month: int) -> float:
    """Estimate the USD cost of translating `char_count` new characters,
    given `already_used_this_month` characters already logged this month.

    Characters within the remaining free-tier allowance are free; only the
    excess is billed at COST_PER_MILLION_CHARS per million characters.
    """
    remaining_free = max(FREE_TIER_CHARS_PER_MONTH - already_used_this_month, 0)
    billable_chars = max(char_count - remaining_free, 0)
    return billable_chars / 1_000_000 * COST_PER_MILLION_CHARS


def _default_confirm(message: str) -> bool:
    """Console y/n confirmation prompt, used when no confirm_callback is given."""
    answer = input(f"{message} [y/N] ").strip().lower()
    return answer in ("y", "yes")


class TranslationBudgetGuard:
    """Wraps a TranslationProvider to estimate, log, and cap translation
    costs. Implements the TranslationProvider protocol itself, so it is a
    drop-in replacement for the provider it wraps.
    """

    def __init__(
        self,
        wrapped_provider: TranslationProvider,
        max_chars_per_run: int = DEFAULT_MAX_CHARS_PER_RUN,
        confirm_callback: Callable[[str], bool] | None = None,
    ) -> None:
        """wrapped_provider performs the actual translation once budget
        checks pass. confirm_callback receives a summary message and
        returns whether to proceed; defaults to a console y/n prompt so a
        later UI can inject its own confirmation dialog instead.
        """
        self._wrapped = wrapped_provider
        self._max_chars_per_run = max_chars_per_run
        self._confirm = confirm_callback or _default_confirm
        self._chars_used_this_run = 0

    def estimate_run(self, texts: list[str]) -> tuple[int, float]:
        """Estimate a full run of not-yet-translated `texts`: total
        character count and its USD cost, given this month's usage so far.
        Meant to be called before the actual pipeline run to show the user
        an upfront summary.
        """
        char_count = sum(len(text) for text in texts)
        cost = estimate_cost(char_count, get_month_usage())
        return char_count, cost

    def confirm_run(self, texts: list[str]) -> bool:
        """Estimate a run of `texts` and ask for confirmation via
        confirm_callback, showing the character count and estimated cost.
        """
        char_count, cost = self.estimate_run(texts)
        message = f"About to translate {char_count:,} characters (estimated cost: ${cost:.2f})."
        return self._confirm(message)

    def _guarded_call(
        self, char_count: int, call: Callable[[], TranslationResult]
    ) -> TranslationResult:
        """Shared budget-check + call + usage-log logic for translate() and
        translate_html(). Raises BudgetExceededError (without invoking
        `call`) if `char_count` more characters would exceed
        max_chars_per_run; otherwise calls it and logs `char_count` to the
        persistent usage log on success.
        """
        if self._chars_used_this_run + char_count > self._max_chars_per_run:
            raise BudgetExceededError(
                f"Translating {char_count} more characters would exceed "
                f"max_chars_per_run ({self._max_chars_per_run}); "
                f"{self._chars_used_this_run} already used this run."
            )

        result = call()

        self._chars_used_this_run += char_count
        log_usage(char_count)
        return result

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `text` via the wrapped provider's translate(), subject
        to the run's character budget (see _guarded_call()).
        """
        return self._guarded_call(
            len(text), lambda: self._wrapped.translate(text, target_lang, source_lang)
        )

    def translate_html(
        self,
        html: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `html` via the wrapped provider's translate_html()
        (e.g. GoogleTranslateProvider.translate_html()), subject to the
        run's character budget (see _guarded_call()). The character count
        includes the HTML tags themselves, matching Google's own billing,
        which counts the full markup sent, not just the visible text.

        Raises TranslationHtmlNotSupportedError if wrapped_provider has no
        translate_html() method, instead of failing with a bare
        AttributeError deep inside the call.
        """
        if not hasattr(self._wrapped, "translate_html"):
            raise TranslationHtmlNotSupportedError(
                f"{type(self._wrapped).__name__} has no translate_html() "
                "method; wrap a provider that supports HTML-aware "
                "translation to use this."
            )
        return self._guarded_call(
            len(html), lambda: self._wrapped.translate_html(html, target_lang, source_lang)
        )
