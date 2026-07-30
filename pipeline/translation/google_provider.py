"""TranslationProvider implementation backed by the Cloud Translation API v2 REST endpoint."""
from __future__ import annotations

import requests

from pipeline.credentials import get_google_translate_api_key
from pipeline.translation.base import TranslationError, TranslationResult

_API_URL = "https://translation.googleapis.com/language/translate/v2"


def _extract_error_message(exc: requests.RequestException) -> str:
    """Pull a human-readable message out of a failed request: Google's JSON
    error body (HTTP status + its "message" field) if present, else str(exc).
    """
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    try:
        message = response.json().get("error", {}).get("message")
    except ValueError:
        message = None
    if message:
        return f"HTTP {response.status_code}: {message}"
    return f"HTTP {response.status_code}: {response.text[:200]}"


class GoogleTranslateProvider:
    """Implements pipeline.translation.base.TranslationProvider via direct
    REST calls to the Cloud Translation API v2, authenticated with a plain
    API key.

    Uses requests instead of the google-cloud-translate SDK: that SDK's
    Client only supports Application Default Credentials (service account /
    gcloud auth), not pure API-key auth - confirmed by the
    DefaultCredentialsError it raised in tests/manual_test_google_provider.py.
    The key is sent as the documented ?key= query parameter (the officially
    documented auth method for this v2 REST endpoint), not a header.
    """

    def __init__(self) -> None:
        """Defer API-key lookup until the first translate() call."""
        self._api_key: str | None = None

    def _get_api_key(self) -> str:
        if self._api_key is None:
            try:
                self._api_key = get_google_translate_api_key()
            except RuntimeError as exc:
                raise TranslationError(str(exc)) from exc
        return self._api_key

    def _call_api(self, body: dict[str, str]) -> dict:
        """POST `body` to the Cloud Translation API v2 endpoint and return
        the first translation object from the response. Raises
        TranslationError on any HTTP or network failure.
        """
        api_key = self._get_api_key()
        try:
            response = requests.post(_API_URL, params={"key": api_key}, json=body, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TranslationError(
                f"Google Translate API request failed: {_extract_error_message(exc)}"
            ) from exc
        return response.json()["data"]["translations"][0]

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `text` into `target_lang` via the Cloud Translation API
        v2 REST endpoint. `source_lang` is omitted from the request body
        when None, letting Google auto-detect it.
        """
        body: dict[str, str] = {"q": text, "target": target_lang, "format": "text"}
        if source_lang is not None:
            body["source"] = source_lang
        translation = self._call_api(body)

        return TranslationResult(
            text=translation["translatedText"],
            source_lang=source_lang or translation.get("detectedSourceLanguage") or "",
            target_lang=target_lang,
            provider="google",
        )

    def translate_html(
        self,
        html: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `html` into `target_lang` via the Cloud Translation API
        v2 REST endpoint with format="html", preserving markup: Google
        translates only the text between tags, leaving the tags themselves
        unchanged and repositioned "to the extent possible" relative to the
        translated text (per Google's docs - not guaranteed identical for
        complex/nested markup). `source_lang` is omitted from the request
        body when None, letting Google auto-detect it.

        Not part of the TranslationProvider protocol (base.py): HTML-aware
        translation isn't available from every provider, so this is a
        Google-specific extra method rather than a protocol requirement.
        """
        body: dict[str, str] = {"q": html, "target": target_lang, "format": "html"}
        if source_lang is not None:
            body["source"] = source_lang
        translation = self._call_api(body)

        return TranslationResult(
            text=translation["translatedText"],
            source_lang=source_lang or translation.get("detectedSourceLanguage") or "",
            target_lang=target_lang,
            provider="google",
        )
