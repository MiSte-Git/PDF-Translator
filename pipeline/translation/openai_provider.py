"""TranslationProvider implementation backed by the OpenAI Chat Completions API.

OpenAI has no dedicated translate endpoint, so translation is done via a
prompt instructing the model to return only the translated text.
"""
from __future__ import annotations

import requests

from pipeline.credentials import get_openai_api_key
from pipeline.translation.base import TranslationError, TranslationResult
from pipeline.translation.protected_terms import protect_terms, restore_terms

_API_URL = "https://api.openai.com/v1/chat/completions"

# Instructs the model to use the informal register wherever the target
# language distinguishes formal/informal address (German du/Sie, French
# tu/vous, Spanish tú/usted, etc.) - unlike DeepL's formality parameter,
# this isn't enforced by the API, only requested via the prompt.
_INFORMAL_REGISTER_INSTRUCTION = (
    " If the target language distinguishes formal and informal address "
    "(e.g. German 'du' vs 'Sie', French 'tu' vs 'vous', Spanish 'tú' vs "
    "'usted'), always use the informal register throughout (e.g. German "
    "'du', never 'Sie')."
)

DEFAULT_MODEL = "gpt-5.6-terra"

# Low temperature for consistent, literal translations rather than creative
# rephrasing. Not sent to reasoning-tier models (see
# _model_supports_temperature()), which reject any non-default value.
_TEMPERATURE = 0.1

# Reasoning-tier model families (o1/o3/gpt-5, e.g. "o1-mini", "o3",
# "gpt-5-mini") only support the default temperature (1) - passing any
# other value 400s: "Unsupported value: 'temperature' does not support 0.1
# with this model. Only the default (1) value is supported." Matched by
# prefix so this keeps working if DEFAULT_MODEL is bumped within the same
# family (e.g. "gpt-5.1-mini").
_NO_CUSTOM_TEMPERATURE_PREFIXES = ("o1", "o3", "gpt-5")


def _model_supports_temperature(model: str) -> bool:
    return not model.startswith(_NO_CUSTOM_TEMPERATURE_PREFIXES)


def _extract_error_message(exc: requests.RequestException) -> str:
    """Pull a human-readable message out of a failed request: OpenAI's JSON
    error body (HTTP status + its "error.message" field) if present, else
    str(exc).
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


class OpenAIProvider:
    """Implements pipeline.translation.base.TranslationProvider via prompted
    translation through the OpenAI Chat Completions API, authenticated with
    a plain API key.
    """

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        """Defer API-key lookup until the first call. `model` selects the
        Chat Completions model used for every translate()/translate_html()
        call on this instance.
        """
        self._model = model
        self._api_key: str | None = None

    @property
    def model_name(self) -> str:
        """The Chat Completions model used for translate()/translate_html()
        on this instance (e.g. for display in tools/compare_providers.py).
        """
        return self._model

    def _get_api_key(self) -> str:
        if self._api_key is None:
            try:
                self._api_key = get_openai_api_key()
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
        body: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        if _model_supports_temperature(self._model):
            body["temperature"] = _TEMPERATURE
        try:
            response = requests.post(_API_URL, headers=headers, json=body, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TranslationError(
                f"OpenAI API request failed: {_extract_error_message(exc)}"
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
            f"into {target_lang}.{source_hint}{_INFORMAL_REGISTER_INSTRUCTION} "
            f"Respond with ONLY the translated text - no quotation marks, "
            f"no preamble, no explanation, nothing else."
        )
        translated = self._complete(system_prompt, text)

        return TranslationResult(
            text=translated,
            source_lang=source_lang or "",
            target_lang=target_lang,
            provider="openai",
        )

    def translate_html(
        self,
        html: str,
        target_lang: str,
        source_lang: str | None = None,
        protected_terms: list[str] | None = None,
    ) -> TranslationResult:
        """Translate `html` into `target_lang` via a Chat Completions
        prompt that instructs the model to preserve all HTML tags exactly,
        in their original relative position, translating only the text
        between/around them - OpenAI has no native tag-handling mode like
        DeepL's tag_handling="html" or Google's format="html", so this is
        spelled out explicitly in the prompt instead.

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

        source_hint = f" The source text is in {source_lang}." if source_lang else ""
        system_prompt = (
            f"You are a professional translator. Translate the user's HTML "
            f"into {target_lang}.{source_hint} The text contains HTML tags "
            f"(e.g. <b>, <i>, <p>, <br/>). Preserve every tag exactly as-is "
            f"and in the same relative position around its corresponding "
            f"text - translate only the text content, never the tags "
            f"themselves, and do not add, remove, or reorder any tags."
            f"{_INFORMAL_REGISTER_INSTRUCTION} Respond with ONLY the "
            f"translated HTML - no quotation marks, no code fences, no "
            f"markdown, no explanation."
        )
        translated = self._complete(system_prompt, html)

        if placeholder_mapping:
            translated = restore_terms(translated, placeholder_mapping)

        return TranslationResult(
            text=translated,
            source_lang=source_lang or "",
            target_lang=target_lang,
            provider="openai",
        )
