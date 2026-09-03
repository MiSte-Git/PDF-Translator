"""Covers pipeline/word/translate_document.py's per-paragraph error
handling - specifically the 03.09.2026 regression fix (Michael, real-world
crash report from an actual translation run): "ValueError: mismatch
after translation: found ['3', '4', '6'], expected ['3', '4', '5', '6']
(hyperlink lost/duplicated/reindexed - see ParagraphHtml.hyperlink_targets)".

That ValueError is html_bridge.py's _validate_tags() firing by design -
a translation provider dropped one of several <a> tags in a paragraph.
Before this fix, translate_document()'s per-paragraph try/except only
caught TranslationError, so this ValueError propagated all the way up
through run_word_job() and aborted the ENTIRE run before engine.save()
was ever reached - losing every already-translated paragraph, not just
the one with the mangled hyperlink. Uses a minimal duck-typed fake
"engine" (only the methods translate_document() actually calls) rather
than a real DocxEngine + a real hyperlink-bearing .docx fixture - much
cheaper to construct, and translate_document() only relies on that
narrow interface in the first place.
"""
from __future__ import annotations

from pipeline.translation.base import TranslationResult
from pipeline.word.base import WordParagraph, WordRun
from pipeline.word.translate_document import translate_document


class _FakeEngineDroppingHyperlinks:
    """A paragraph 0 with a hyperlink run (whose <a> tag the fake provider
    below will drop from the translated HTML, exactly reproducing the
    real crash) followed by a plain paragraph 1 with no hyperlink at all -
    the whole point of the regression test is that paragraph 1 must still
    end up translated and saved even though paragraph 0 fails.
    """

    def __init__(self) -> None:
        self._paragraphs = [
            WordParagraph(
                runs=[
                    WordRun(text="See "),
                    WordRun(
                        text="our site",
                        is_hyperlink=True,
                        hyperlink_target="https://example.com",
                    ),
                    WordRun(text=" for details."),
                ]
            ),
            WordParagraph(runs=[WordRun(text="A perfectly normal paragraph.")]),
        ]
        self._header_paragraph_elements: list = []
        self.replaced: dict[int, list[WordRun]] = {}

    def get_paragraphs(self) -> list[WordParagraph]:
        return self._paragraphs

    def get_header_footer_paragraphs(self) -> list[WordParagraph]:
        return []

    def replace_paragraph_runs(self, index: int, new_runs: list[WordRun]) -> None:
        self.replaced[index] = new_runs


class _HyperlinkDroppingProvider:
    """Simulates a real translation provider that silently drops an <a>
    tag while translating (keeping its inner text) - the actual failure
    mode behind the reported crash. Every OTHER paragraph translates
    normally, so a working run must still make progress around the one
    bad paragraph.
    """

    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None) -> TranslationResult:
        translated = html.replace('<a data-run="1">our site</a>', "our site")
        return TranslationResult(text=f"[{target_lang}] {translated}", source_lang=source_lang or "en", target_lang=target_lang, provider="fake")


def test_a_dropped_hyperlink_fails_only_its_own_paragraph() -> None:
    engine = _FakeEngineDroppingHyperlinks()

    stats = translate_document(engine, _HyperlinkDroppingProvider(), [], "DE", "en")

    assert stats.body_failed == 1
    assert stats.body_translated == 1
    assert not stats.cancelled
    assert len(stats.errors) == 1
    assert "hyperlink lost/duplicated/reindexed" in stats.errors[0]
    # The failed paragraph (0) was never replace_paragraph_runs()'d - its
    # original hyperlink stays intact rather than being silently dropped.
    assert 0 not in engine.replaced
    # The second, unrelated paragraph translated normally despite the
    # first one failing - this is the actual regression: before the fix,
    # the ValueError above propagated out of translate_document() entirely
    # and this paragraph (along with everything else) was never reached.
    assert 1 in engine.replaced
    assert "".join(run.text for run in engine.replaced[1]) == "[DE] A perfectly normal paragraph."


def test_translate_document_does_not_raise_on_a_dropped_hyperlink() -> None:
    """The bug's actual symptom: translate_document() itself must return
    normally (so run_word_job() reaches engine.save()) instead of letting
    the ValueError escape uncaught."""
    engine = _FakeEngineDroppingHyperlinks()

    # Would raise ValueError before the fix - the test itself IS the
    # assertion here (pytest fails the test on an uncaught exception).
    translate_document(engine, _HyperlinkDroppingProvider(), [], "DE", "en")
