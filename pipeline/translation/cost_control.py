"""Cost estimation, logging, and hard limiting for translation API usage.

Wraps any TranslationProvider (see base.py) so a caller can see an upfront
cost estimate, get a confirmation prompt, and be protected by a hard
per-run character cap, before/while the wrapped provider is actually used.
Pricing is provider-specific (see PricingModel) since providers differ in
free-tier size and per-character cost, and usage is logged per provider
since each has its own account/quota.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from pipeline.translation.base import TranslationError, TranslationProvider, TranslationResult


@dataclass
class PricingModel:
    """A translation provider's pricing, for budget estimation purposes.

    cost_per_million_chars models a simple linear pay-as-you-go price (e.g.
    Google's per-character billing). For providers with a subscription- or
    quota-based pricing structure instead (e.g. DeepL Pro), this is only a
    rough approximation useful for budget warnings - not an exact billing
    model.
    """
    provider_name: str
    cost_per_million_chars: float
    free_tier_chars_per_month: int


# Google Cloud Translation Basic (v2) pricing, as of 2026.
GOOGLE_PRICING = PricingModel(
    provider_name="google", cost_per_million_chars=20.0, free_tier_chars_per_month=500_000
)

# The free tier here (500,000 chars/month) matches the legacy "DeepL API
# Free" plan (":fx" keys) that existing subscribers keep. DeepL no longer
# sells that plan to new signups: new free accounts instead get a one-time,
# non-renewing 1,000,000-character allowance (verified against DeepL's own
# plan documentation, Aug 2026) - this monthly-reset model would silently
# under-estimate cost for those accounts once the one-time allowance runs
# out. free_tier_chars_per_month therefore stays a local, provider-agnostic
# fallback estimate only; prefer DeepLProvider.get_usage() (GET /v2/usage,
# the account's own live, authoritative character_count/character_limit)
# wherever a live check is possible - see ui/analysis.py. The paid DeepL API
# Pro tier is subscription-based (a monthly fee plus a fair-use character
# allowance), not linear pay-per-character, so cost_per_million_chars is
# only a rough estimate for the guard's budget warning here either way, not
# DeepL's real Pro pricing model.
DEEPL_PRICING = PricingModel(
    provider_name="deepl", cost_per_million_chars=20.0, free_tier_chars_per_month=500_000
)

# OpenAI/Grok are billed per-token through a Chat Completions API, not
# per-character like Google/DeepL's dedicated translate endpoints - there
# is no exact per-character price to quote. These two are a deliberately
# rough per-character approximation (no free tier), good enough for the
# same upfront budget-warning purpose as the other two, not for precise
# billing reconciliation.
OPENAI_PRICING = PricingModel(
    provider_name="openai", cost_per_million_chars=15.0, free_tier_chars_per_month=0
)
GROK_PRICING = PricingModel(
    provider_name="grok", cost_per_million_chars=15.0, free_tier_chars_per_month=0
)

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


def _usage_log_key(provider_name: str, month_key: str) -> str:
    """Build the usage-log dict key 'provider_name:YYYY-MM'. Usage is
    tracked per provider since each has its own account/quota/pricing.
    """
    return f"{provider_name}:{month_key}"


def _read_usage_log() -> dict[str, dict[str, int]]:
    """Read the persistent usage log, or {} if it doesn't exist/is invalid."""
    if not _USAGE_LOG_PATH.exists():
        return {}
    try:
        return json.loads(_USAGE_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_month_usage(provider_name: str, month_key: str | None = None) -> int:
    """Return characters already logged for `provider_name` in `month_key`
    (default: current month), or 0 if nothing is logged for it yet.
    """
    key = _usage_log_key(provider_name, month_key or _current_month_key())
    return _read_usage_log().get(key, {}).get("characters", 0)


def log_usage(provider_name: str, char_count: int) -> None:
    """Add `char_count` to `provider_name`'s current-month usage total in
    the persistent usage log (creating the file/entry if needed).
    """
    data = _read_usage_log()
    key = _usage_log_key(provider_name, _current_month_key())
    entry = data.setdefault(key, {"characters": 0})
    entry["characters"] += char_count
    _USAGE_LOG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _default_confirm(message: str) -> bool:
    """Console y/n confirmation prompt, used when no confirm_callback is given."""
    answer = input(f"{message} [y/N] ").strip().lower()
    return answer in ("y", "yes")


class TranslationBudgetGuard:
    """Wraps a TranslationProvider to estimate, log, and cap translation
    costs, using provider-specific pricing (see PricingModel). Implements
    the TranslationProvider protocol itself, so it is a drop-in replacement
    for the provider it wraps.
    """

    def __init__(
        self,
        wrapped_provider: TranslationProvider,
        pricing: PricingModel,
        max_chars_per_run: int = DEFAULT_MAX_CHARS_PER_RUN,
        confirm_callback: Callable[[str], bool] | None = None,
    ) -> None:
        """wrapped_provider performs the actual translation once budget
        checks pass. pricing supplies the cost/free-tier numbers used for
        estimates and picks which provider's usage-log entry is read/
        written (see PricingModel.provider_name). confirm_callback receives
        a summary message and returns whether to proceed; defaults to a
        console y/n prompt so a later UI can inject its own confirmation
        dialog instead.
        """
        self._wrapped = wrapped_provider
        self._pricing = pricing
        self._max_chars_per_run = max_chars_per_run
        self._confirm = confirm_callback or _default_confirm
        self._chars_used_this_run = 0

    @property
    def provider_name(self) -> str:
        """This guard's pricing.provider_name - the same key its usage log
        entries are stored/read under (see log_usage()/get_month_usage()).
        Exposed so a caller that only holds the guard (e.g.
        ico_translate/batch.py, computing a whole batch's actual cost from
        its real accumulated chars_sent) doesn't need its own reference to
        the PricingModel just to look up this string.
        """
        return self._pricing.provider_name

    def estimate_cost(self, char_count: int, already_used_this_month: int) -> float:
        """Estimate the USD cost of translating `char_count` new characters
        under this guard's pricing, given `already_used_this_month`
        characters already logged this month for this provider.

        Characters within the remaining free-tier allowance are free; only
        the excess is billed at pricing.cost_per_million_chars per million
        characters.
        """
        remaining_free = max(
            self._pricing.free_tier_chars_per_month - already_used_this_month, 0
        )
        billable_chars = max(char_count - remaining_free, 0)
        return billable_chars / 1_000_000 * self._pricing.cost_per_million_chars

    def estimate_run(self, texts: list[str]) -> tuple[int, float]:
        """Estimate a full run of not-yet-translated `texts`: total
        character count and its USD cost, given this month's usage so far
        for this guard's provider. Meant to be called before the actual
        pipeline run to show the user an upfront summary.
        """
        char_count = sum(len(text) for text in texts)
        cost = self.estimate_cost(char_count, get_month_usage(self._pricing.provider_name))
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
        max_chars_per_run; otherwise calls it and logs `char_count` to this
        guard's provider's persistent usage log on success.
        """
        if self._chars_used_this_run + char_count > self._max_chars_per_run:
            raise BudgetExceededError(
                f"Translating {char_count} more characters would exceed "
                f"max_chars_per_run ({self._max_chars_per_run}); "
                f"{self._chars_used_this_run} already used this run."
            )

        result = call()

        self._chars_used_this_run += char_count
        log_usage(self._pricing.provider_name, char_count)
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
