"""TranslationProvider implementation backed by the DeepL API v2 REST endpoint."""
from __future__ import annotations

import time
import requests

from pipeline.credentials import get_deepl_api_key
from pipeline.translation.base import TranslationError, TranslationResult
from pipeline.translation.protected_terms import protect_terms, restore_terms

# DeepL Free-tier API keys conventionally end in ":fx" (documented DeepL
# account/API convention - Free keys are only valid against the Free host,
# Pro keys only against the Pro host, so the right endpoint must be picked
# by inspecting the key itself).
_FREE_KEY_SUFFIX = ":fx"
_FREE_API_URL = "https://api-free.deepl.com/v2/translate"
_PRO_API_URL = "https://api.deepl.com/v2/translate"

# Target languages for which DeepL's API accepts the "formality" parameter,
# per DeepL API docs (formality support is per-target-language and DeepL
# adds more over time - if a request 400s with the current key formats,
# check the current list at developers.deepl.com before extending this).
# Passing formality for an unsupported target language is a hard API error,
# so it's only ever added when target_lang is in this set.
_FORMALITY_SUPPORTED_TARGET_LANGS = frozenset(
    {"DE", "FR", "IT", "ES", "NL", "PL", "PT-BR", "PT-PT", "JA", "RU"}
)


def _extract_error_message(exc: requests.RequestException) -> str:
    """Pull a human-readable message out of a failed request: DeepL's JSON
    error body (HTTP status + its "message" field) if present, else str(exc).
    """
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    try:
        message = response.json().get("message")
    except ValueError:
        message = None
    if message:
        return f"HTTP {response.status_code}: {message}"
    return f"HTTP {response.status_code}: {response.text[:200]}"


class DeepLProvider:
    """Implements pipeline.translation.base.TranslationProvider via direct
    REST calls to the DeepL API v2, authenticated with a plain API key.

    DeepL requires uppercase language codes (e.g. "DE", "EN"), unlike this
    project's lowercase convention (e.g. "de", "en") used everywhere else -
    translate()/translate_html() accept/return lowercase and convert
    internally.
    """

    def __init__(self, min_request_interval: float = 0.0) -> None:
        """Defer API-key lookup (and Free-vs-Pro endpoint choice) until the
        first call.
        """
        self._api_key: str | None = None
        self._api_url: str | None = None
        self._min_request_interval = max(min_request_interval, 0.0)
        self._last_request_started: float | None = None

    @property
    def model_name(self) -> str:
        """No selectable model exists for this provider (fixed REST
        endpoint) - returns a fixed API identifier instead, for display in
        tools/compare_providers.py.
        """
        return "DeepL API v2"

    def _get_api_key_and_url(self) -> tuple[str, str]:
        """Load (and cache) the API key, picking the Free or Pro endpoint
        by whether the key ends in _FREE_KEY_SUFFIX.
        """
        if self._api_key is None:
            try:
                self._api_key = get_deepl_api_key()
            except RuntimeError as exc:
                raise TranslationError(str(exc)) from exc
            self._api_url = (
                _FREE_API_URL if self._api_key.endswith(_FREE_KEY_SUFFIX) else _PRO_API_URL
            )
        assert self._api_url is not None
        return self._api_key, self._api_url

    def _call_api(self, body: dict[str, object]) -> dict:
        """POST `body` to the DeepL API v2 endpoint and return the first
        translation object from the response. Raises TranslationError on
        any HTTP or network failure.
        """
        api_key, api_url = self._get_api_key_and_url()
        headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
        for attempt in range(3):
            if self._last_request_started is not None and self._min_request_interval:
                elapsed = time.monotonic() - self._last_request_started
                if elapsed < self._min_request_interval:
                    time.sleep(self._min_request_interval - elapsed)
            self._last_request_started = time.monotonic()
            try:
                response = requests.post(api_url, headers=headers, json=body, timeout=30)
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                response = getattr(exc, "response", None)
                if response is not None and response.status_code == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = max(float(retry_after), 1.0) if retry_after else 60.0
                    except ValueError:
                        delay = 60.0
                    time.sleep(delay)
                    continue
                raise TranslationError(
                    f"DeepL API request failed: {_extract_error_message(exc)}"
                ) from exc
        return response.json()["translations"][0]

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `text` into `target_lang` via the DeepL API v2.
        `target_lang`/`source_lang` are given in this project's lowercase
        convention and uppercased for DeepL. `source_lang` is omitted from
        the request when None, letting DeepL auto-detect it. Requests the
        informal register (formality="less") when target_lang supports it
        (see _FORMALITY_SUPPORTED_TARGET_LANGS), otherwise omits the
        parameter since DeepL rejects it for unsupported languages.
        """
        body: dict[str, object] = {"text": [text], "target_lang": target_lang.upper()}
        if source_lang is not None:
            body["source_lang"] = source_lang.upper()
        if target_lang.upper() in _FORMALITY_SUPPORTED_TARGET_LANGS:
            body["formality"] = "less"
        translation = self._call_api(body)

        detected_source = translation.get("detected_source_language")
        return TranslationResult(
            text=translation["text"],
            source_lang=source_lang or (detected_source.lower() if detected_source else ""),
            target_lang=target_lang,
            provider="deepl",
        )

    def translate_html(
        self,
        html: str,
        target_lang: str,
        source_lang: str | None = None,
        protected_terms: list[str] | None = None,
    ) -> TranslationResult:
        """Translate `html` into `target_lang` via the DeepL API v2 with
        tag_handling="html", preserving markup: DeepL's documented
        mechanism for translating only the text between tags and keeping
        tags in place, analogous to Google's format="html". Language codes
        and formality are handled the same way as translate().

        If `protected_terms` is given, each term is replaced with a
        placeholder (see pipeline.translation.protected_terms) before the
        API call and restored in the result, so those terms pass through
        translation unchanged.

        Not part of the TranslationProvider protocol (base.py): HTML-aware
        translation isn't available from every provider.
        """
        placeholder_mapping: dict[str, str] = {}
        if protected_terms:
            html, placeholder_mapping = protect_terms(html, protected_terms)

        body: dict[str, object] = {
            "text": [html],
            "target_lang": target_lang.upper(),
            "tag_handling": "html",
        }
        if source_lang is not None:
            body["source_lang"] = source_lang.upper()
        if target_lang.upper() in _FORMALITY_SUPPORTED_TARGET_LANGS:
            body["formality"] = "less"
        translation = self._call_api(body)

        translated_text = translation["text"]
        if placeholder_mapping:
            translated_text = restore_terms(translated_text, placeholder_mapping)

        detected_source = translation.get("detected_source_language")
        return TranslationResult(
            text=translated_text,
            source_lang=source_lang or (detected_source.lower() if detected_source else ""),
            target_lang=target_lang,
            provider="deepl",
        )
