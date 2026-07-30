"""TranslationProvider implementation backed by the DeepL API v2 REST endpoint."""
from __future__ import annotations

import requests

from pipeline.credentials import get_deepl_api_key
from pipeline.translation.base import TranslationError, TranslationResult

# DeepL Free-tier API keys conventionally end in ":fx" (documented DeepL
# account/API convention - Free keys are only valid against the Free host,
# Pro keys only against the Pro host, so the right endpoint must be picked
# by inspecting the key itself).
_FREE_KEY_SUFFIX = ":fx"
_FREE_API_URL = "https://api-free.deepl.com/v2/translate"
_PRO_API_URL = "https://api.deepl.com/v2/translate"


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

    def __init__(self) -> None:
        """Defer API-key lookup (and Free-vs-Pro endpoint choice) until the
        first call.
        """
        self._api_key: str | None = None
        self._api_url: str | None = None

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
        try:
            response = requests.post(api_url, headers=headers, json=body, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
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
        the request when None, letting DeepL auto-detect it.
        """
        body: dict[str, object] = {"text": [text], "target_lang": target_lang.upper()}
        if source_lang is not None:
            body["source_lang"] = source_lang.upper()
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
    ) -> TranslationResult:
        """Translate `html` into `target_lang` via the DeepL API v2 with
        tag_handling="html", preserving markup: DeepL's documented
        mechanism for translating only the text between tags and keeping
        tags in place, analogous to Google's format="html". Language codes
        are handled the same way as translate().

        Not part of the TranslationProvider protocol (base.py): HTML-aware
        translation isn't available from every provider.
        """
        body: dict[str, object] = {
            "text": [html],
            "target_lang": target_lang.upper(),
            "tag_handling": "html",
        }
        if source_lang is not None:
            body["source_lang"] = source_lang.upper()
        translation = self._call_api(body)

        detected_source = translation.get("detected_source_language")
        return TranslationResult(
            text=translation["text"],
            source_lang=source_lang or (detected_source.lower() if detected_source else ""),
            target_lang=target_lang,
            provider="deepl",
        )
