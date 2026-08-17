from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ui.analysis import analyze_request
from ui.models import TranslationMode, TranslationRequest

FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


def _request() -> TranslationRequest:
    return TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), provider="deepl")


def test_live_deepl_quota_is_used_when_available() -> None:
    with patch("ui.analysis.DeepLProvider") as mocked_provider_cls:
        mocked_provider_cls.return_value.get_usage.return_value = {
            "character_count": 990_000, "character_limit": 1_000_000,
        }
        result = analyze_request(_request())

    assert result.cost.live_usage_available
    assert result.cost.live_characters_used == 990_000
    assert result.cost.live_character_limit == 1_000_000
    # Only 10,000 characters of free allowance remain -> the fixture's
    # handful of characters should already be (mostly) billable.
    assert "warning.live_quota_unavailable" not in result.warnings


def test_live_deepl_quota_unlimited_account_reports_no_bill_from_free_tier() -> None:
    with patch("ui.analysis.DeepLProvider") as mocked_provider_cls:
        mocked_provider_cls.return_value.get_usage.return_value = {
            "character_count": 5_000_000, "character_limit": None,
        }
        result = analyze_request(_request())

    assert result.cost.live_usage_available
    assert result.cost.live_character_limit is None
    assert result.cost.estimated_cost_usd == 0.0


def test_falls_back_to_local_estimate_when_live_check_fails() -> None:
    from pipeline.translation.base import TranslationError

    with patch("ui.analysis.DeepLProvider") as mocked_provider_cls:
        mocked_provider_cls.return_value.get_usage.side_effect = TranslationError("no key")
        result = analyze_request(_request())

    assert not result.cost.live_usage_available
    assert result.cost.live_characters_used is None
    assert "warning.live_quota_unavailable" in result.warnings


def test_non_deepl_provider_never_attempts_a_live_check() -> None:
    with patch("ui.analysis.DeepLProvider") as mocked_provider_cls:
        request = TranslationRequest(TranslationMode.PRESENTATION, (FIXTURE,), provider="google")
        result = analyze_request(request)

    mocked_provider_cls.assert_not_called()
    assert not result.cost.live_usage_available
