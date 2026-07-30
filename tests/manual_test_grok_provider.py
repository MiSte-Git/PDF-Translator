"""Ad-hoc live test for GrokProvider against the real xAI Grok API.

Not a pytest test - run manually (requires `pip install -r requirements.txt`
and a key stored via pipeline/credentials.py, service "pdf-translator",
key "grok_api_key"):

    python tests/manual_test_grok_provider.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.translation.base import TranslationError
from pipeline.translation.grok_provider import GrokProvider

TEST_SENTENCE = "This is a quiet way in which a person begins to give away judgment."


def print_result(label: str, result) -> None:
    print(f"--- {label} ---")
    print(f"text:        {result.text!r}")
    print(f"source_lang: {result.source_lang!r}")
    print(f"target_lang: {result.target_lang!r}")
    print(f"provider:    {result.provider!r}")
    print()


def main() -> None:
    provider = GrokProvider()

    try:
        explicit = provider.translate(TEST_SENTENCE, target_lang="de", source_lang="en")
        print_result("explicit source_lang='en'", explicit)

        auto = provider.translate(TEST_SENTENCE, target_lang="de", source_lang=None)
        print_result("auto-detected source_lang", auto)
    except TranslationError as exc:
        print(f"TranslationError: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
