"""TranslationProvider implementation backed by the xAI Grok Chat Completions API.

The Grok API is OpenAI-compatible (POST /v1/chat/completions with the same
request/response shape) - see GrokProvider docstring for how the endpoint
and model were verified. As with OpenAIProvider, there is no dedicated
translate endpoint, so translation is done via a prompt instructing the
model to return only the translated text.
"""
from __future__ import annotations

import requests

from pipeline.credentials import get_grok_api_key
from pipeline.translation.base import TranslationError, TranslationResult

_API_URL = "https://api.x.ai/v1/chat/completions"

# grok-4.20-0309-non-reasoning: verified directly against the raw pricing
# data embedded in docs.x.ai/docs/pricing ($1.25/1M input, $2.50/1M output
# tokens for prompts < 200k tokens). Chosen over:
#   - grok-4.5 ($2.00/$6.00) / grok-4.3 ($1.25/$2.50, but defaults to "high"
#     reasoning effort) - pricier or reasoning-oriented, not needed here.
#   - grok-4.20-0309-reasoning (same price) - the reasoning-enabled sibling
#     of this model; translation doesn't need chain-of-thought reasoning.
#   - grok-4.20-multi-agent-0309 - agentic, not a plain text model.
#   - grok-build-0.1 ($1.00/$2.00, looks cheapest) - its "aliases" field in
#     the raw pricing data lists "grok-code-fast-1"/"grok-code-fast", i.e.
#     it IS xAI's coding model under another name, not a general model.
# Overridable per instance if a different model is preferred.
DEFAULT_MODEL = "grok-4.20-0309-non-reasoning"

# Low temperature for consistent, literal translations rather than creative
# rephrasing.
_TEMPERATURE = 0.1


def _extract_error_message(exc: requests.RequestException) -> str:
    """Pull a human-readable message out of a failed request: Grok's JSON
    error body (HTTP status + its "error" field, OpenAI-compatible shape)
    if present, else str(exc).
    """
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    try:
        payload = response.json()
        message = payload.get("error")
        if isinstance(message, dict):
            message = message.get("message")
    except ValueError:
        message = None
    if message:
        return f"HTTP {response.status_code}: {message}"
    return f"HTTP {response.status_code}: {response.text[:200]}"


def _strip_code_fence(text: str) -> str:
    """Strip a leading/trailing markdown code fence, in case the model
    wraps its output in one despite being told not to (defensive cleanup).
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class GrokProvider:
    """Implements pipeline.translation.base.TranslationProvider via prompted
    translation through the xAI Grok Chat Completions API, authenticated
    with a plain API key.

    Verified directly against docs.x.ai (raw page data, not summaries or
    training-data assumptions): the API is OpenAI-compatible and exposes a
    real, documented POST /v1/chat/completions endpoint (base URL
    https://api.x.ai/v1) alongside its newer /v1/responses endpoint, with
    the same request/response schema this provider already used for
    OpenAIProvider. See DEFAULT_MODEL for how the model was chosen.
    """

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        """Defer API-key lookup until the first call. `model` selects the
        Chat Completions model used for every translate()/translate_html()
        call on this instance.
        """
        self._model = model
        self._api_key: str | None = None

    def _get_api_key(self) -> str:
        if self._api_key is None:
            try:
                self._api_key = get_grok_api_key()
            except RuntimeError as exc:
                raise TranslationError(str(exc)) from exc
        return self._api_key

    def _complete(self, system_prompt: str, user_content: str) -> str:
        """Send a single chat-completion request and return the raw
        response text (stripped, with any code fence removed). Raises
        TranslationError on any HTTP or network failure.
        """
        api_key = self._get_api_key()
        headers = {"Authorization": f"Bearer {api_key}"}
        body = {
            "model": self._model,
            "temperature": _TEMPERATURE,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        try:
            response = requests.post(_API_URL, headers=headers, json=body, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TranslationError(
                f"Grok API request failed: {_extract_error_message(exc)}"
            ) from exc
        content = response.json()["choices"][0]["message"]["content"]
        return _strip_code_fence(content)

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `text` into `target_lang` via a Chat Completions
        prompt. The system prompt instructs the model to return only the
        translated text, no quotes/preamble/explanation. `source_lang`, if
        given, is included as a hint; otherwise the model infers it.
        """
        source_hint = f" The source text is in {source_lang}." if source_lang else ""
        system_prompt = (
            f"You are a professional translator. Translate the user's text "
            f"into {target_lang}.{source_hint} Respond with ONLY the "
            f"translated text - no quotation marks, no preamble, no "
            f"explanation, nothing else."
        )
        translated = self._complete(system_prompt, text)

        return TranslationResult(
            text=translated,
            source_lang=source_lang or "",
            target_lang=target_lang,
            provider="grok",
        )

    def translate_html(
        self,
        html: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate `html` into `target_lang` via a Chat Completions
        prompt that instructs the model to preserve all HTML tags exactly,
        in their original relative position, translating only the text
        between/around them - Grok has no native tag-handling mode like
        DeepL's tag_handling="html" or Google's format="html", so this is
        spelled out explicitly in the prompt instead.

        Not part of the TranslationProvider protocol (base.py): HTML-aware
        translation isn't available from every provider.
        """
        source_hint = f" The source text is in {source_lang}." if source_lang else ""
        system_prompt = (
            f"You are a professional translator. Translate the user's HTML "
            f"into {target_lang}.{source_hint} The text contains HTML tags "
            f"(e.g. <b>, <i>, <p>, <br/>). Preserve every tag exactly as-is "
            f"and in the same relative position around its corresponding "
            f"text - translate only the text content, never the tags "
            f"themselves, and do not add, remove, or reorder any tags. "
            f"Respond with ONLY the translated HTML - no quotation marks, "
            f"no code fences, no markdown, no explanation."
        )
        translated = self._complete(system_prompt, html)

        return TranslationResult(
            text=translated,
            source_lang=source_lang or "",
            target_lang=target_lang,
            provider="grok",
        )
