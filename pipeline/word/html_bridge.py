"""Bridge between WordParagraph (pipeline.word.base) and an HTML string a
translation provider's translate_html() can safely translate - mirroring
pipeline/pdf/pymupdf_engine.py's spans_to_html() for the same underlying
problem (representing formatting and structural markers as HTML a provider
can pass through mostly unchanged).

Structural markers (images, line breaks, hyperlinks) are real HTML tags,
not text placeholders: tests/manual_verify_word_markers.py found that
DeepL/Google's HTML-aware translate_html() reliably preserves actual tags
(<a> survived intact) but corrupts plain-text §§...§§-style placeholders
sitting between them (DeepL spliced one into a neighboring protected-term
placeholder, Google dropped a "§" where two placeholders touched). Real
tags ride on the same tag-preservation guarantee <a> already benefited
from, instead of relying on a provider treating arbitrary placeholder text
"specially".

No write-back into document.xml yet (see pipeline/word/docx_engine.py's
save() stub) and no protected_terms.py integration yet - purely the
paragraph <-> html conversion in both directions.
"""
from __future__ import annotations

import copy
import html
import json
from dataclasses import dataclass, field
from pathlib import Path

from lxml import html as lxml_html

from pipeline.word.base import BREAK_MARKER, WordParagraph, WordRun

# tests/output/word_break_anomalies.jsonl (one JSON object per line) - see
# log_break_anomaly(). Same fixed-path convention as the PDF path's
# _GROWTH_ANOMALY_LOG_PATH (pipeline/pdf/pymupdf_engine.py): a small,
# single-project tool, not a published library, so a hardcoded path here
# is a deliberate simplification, not an oversight.
_BREAK_ANOMALY_LOG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "tests" / "output" / "word_break_anomalies.jsonl"
)

# Placeholder for a single space character that sits directly next to a
# <br/> tag (see paragraph_to_html()'s _protect_break_adjacent_space()).
# tests/manual_verify_word_roundtrip.py found DeepL sometimes drops a
# literal space immediately touching a <br/> during translation (treating
# it like HTML whitespace collapsing around a block-ish tag), even though
# the space genuinely existed in the HTML we sent - a plain space is
# fragile there in a way a run of ordinary letters/digits isn't. A
# placeholder can't be silently collapsed the same way; same "marker
# principle" as BREAK_MARKER/protect_terms()'s §§N§§ (proven to survive
# translation reliably as long as it isn't itself glued to another
# structural marker - see html_bridge.py's module docstring).
_SPACE_MARKER = "§§SP§§"


@dataclass
class ParagraphHtml:
    """Result of paragraph_to_html(): the HTML string to send to a
    translation provider, plus the run-index -> original-run lookups a
    later write-back step needs to reconstruct the paragraph after
    translation.
    """
    html: str
    image_runs: dict[int, WordRun] = field(default_factory=dict)
    """run_index (the run's position in paragraph.runs, also the value of
    that <img data-run="..."/> tag's data-run attribute in `html`) -> the
    original image WordRun it replaced."""
    hyperlink_targets: dict[int, str] = field(default_factory=dict)
    """run_index (matching a <a data-run="..."> tag's data-run attribute
    in `html`) -> the hyperlink's resolved target. Same run_index scheme
    as image_runs, so both are looked up the same way after translation."""
    base_rpr: object = None
    """A representative original <w:rPr> element (see WordRun.source_rpr)
    for this paragraph's ordinary (non-hyperlink) text - the first
    non-image, non-hyperlink run's source_rpr, or (if the paragraph is
    ALL images/hyperlinks) the first run's regardless. None if the
    paragraph had no runs with a source_rpr at all (e.g. every run was
    built by hand, as in most of this project's own tests).

    03.09.2026 (Michael: "Ich sehe noch Unterschiede bei den Fonts"): a run
    built from translated HTML in html_to_paragraph() doesn't map 1:1 to
    one specific original <w:r> (a provider can merge/split/reorder text
    across the original runs) - there is no single "the" original rPr to
    reuse for it. Using the paragraph's dominant/first-run rPr as a
    stand-in base is an approximation (a paragraph with genuinely mixed
    fonts mid-sentence would still average toward one), but covers the
    overwhelmingly common case (a whole paragraph in one font) that was
    previously lost entirely."""
    hyperlink_source_rpr: dict[int, object] = field(default_factory=dict)
    """Same run_index scheme as hyperlink_targets, but each entry is that
    SPECIFIC original hyperlink run's own source_rpr (carrying, e.g., its
    <w:rStyle w:val="Hyperlink"/> plus whatever font/size the hyperlink
    itself used) - a hyperlink is precise here (unlike base_rpr) because,
    just like hyperlink_targets, html_to_paragraph() always knows exactly
    which original hyperlink run_index a translated <a data-run="n"> tag
    came from."""


def paragraph_to_html(paragraph: WordParagraph) -> ParagraphHtml:
    """Build an HTML representation of `paragraph` for translate_html().

    - Bold/italic/underline runs become nestable <b>/<i>/<u> tags (same
      convention as pipeline.pdf.pymupdf_engine.spans_to_html()).
    - Image runs (run.is_image) are NOT included as content - they're
      replaced with a self-closing <img data-run="<run_index>"/> tag
      (recorded in ParagraphHtml.image_runs) so a translation provider
      can't touch or lose them, while their position is preserved.
    - A <w:br/> line break within a run - extracted by DocxEngine as its
      own WordRun whose text equals BREAK_MARKER (pipeline.word.base,
      mirroring PARAGRAPH_BREAK_MARKER/LINE_BREAK_MARKER in
      pipeline/pdf/base.py) - becomes a real <br/> tag. No data-run
      attribute needed: unlike images/hyperlinks, a write-back step only
      needs the count/order of breaks, not a specific WordRun to restore.
    - Hyperlink runs (run.is_hyperlink) are wrapped in
      <a data-run="<run_index>">text</a> - no href, the resolved target
      never appears in the HTML sent to a provider. The target is
      returned separately in ParagraphHtml.hyperlink_targets, keyed by
      the same run_index as the tag's data-run attribute.
    - A run directly preceding or following a break run keeps a leading/
      trailing space it genuinely has, but the space itself is replaced
      with _SPACE_MARKER at that specific edge only (never added where
      there wasn't one - see _protect_break_adjacent_space()), so it
      can't be lost the way a real space next to a <br/> tag can be.
    """
    parts: list[str] = []
    image_runs: dict[int, WordRun] = {}
    hyperlink_targets: dict[int, str] = {}
    hyperlink_source_rpr: dict[int, object] = {}
    base_rpr: object = None
    fallback_base_rpr: object = None

    for index, run in enumerate(paragraph.runs):
        if run.is_image:
            image_runs[index] = run
            parts.append(f'<img data-run="{index}"/>')
            continue

        if run.text == BREAK_MARKER:
            parts.append("<br/>")
            continue

        if not run.text:
            continue

        # First non-image, non-hyperlink run's rPr is the paragraph's
        # "ordinary text" representative (see ParagraphHtml.base_rpr) -
        # falling back to the first run of ANY kind only if the paragraph
        # turns out to have no such run at all (e.g. it's one giant
        # hyperlink).
        if base_rpr is None and not run.is_hyperlink and run.source_rpr is not None:
            base_rpr = run.source_rpr
        if fallback_base_rpr is None and run.source_rpr is not None:
            fallback_base_rpr = run.source_rpr

        prev_is_break = index > 0 and paragraph.runs[index - 1].text == BREAK_MARKER
        next_is_break = (
            index + 1 < len(paragraph.runs) and paragraph.runs[index + 1].text == BREAK_MARKER
        )
        text = _protect_break_adjacent_space(run.text, prev_is_break, next_is_break)

        escaped = html.escape(text)
        if run.underline:
            escaped = f"<u>{escaped}</u>"
        if run.italic:
            escaped = f"<i>{escaped}</i>"
        if run.bold:
            escaped = f"<b>{escaped}</b>"
        if run.is_hyperlink:
            hyperlink_targets[index] = run.hyperlink_target or ""
            if run.source_rpr is not None:
                hyperlink_source_rpr[index] = run.source_rpr
            escaped = f'<a data-run="{index}">{escaped}</a>'

        parts.append(escaped)

    # Priority for the paragraph's "ordinary text" base rPr:
    # 1. a non-hyperlink run's own rPr (base_rpr) - the most specific.
    # 2. the paragraph mark's own rPr (paragraph.mark_rpr) - many real
    #    documents set font/size once here rather than repeating it on
    #    every run (03.09.2026, Michael: "Dann hat der Originale Body Text
    #    11 pt und der Übersetzte 12 pt" - exactly this case, a paragraph
    #    whose runs carried no rPr of their own at all).
    # 3. any run's rPr regardless of kind (fallback_base_rpr), so a
    #    paragraph that's ENTIRELY one hyperlink still has something.
    if base_rpr is not None:
        resolved_base_rpr = base_rpr
    elif paragraph.mark_rpr is not None:
        resolved_base_rpr = paragraph.mark_rpr
    else:
        resolved_base_rpr = fallback_base_rpr

    return ParagraphHtml(
        html="".join(parts),
        image_runs=image_runs,
        hyperlink_targets=hyperlink_targets,
        base_rpr=resolved_base_rpr,
        hyperlink_source_rpr=hyperlink_source_rpr,
    )


def _protect_break_adjacent_space(text: str, prev_is_break: bool, next_is_break: bool) -> str:
    """Replace a leading space (if `prev_is_break`) and/or a trailing
    space (if `next_is_break`) in `text` with _SPACE_MARKER - only if
    that exact character is already there. Never adds a space that wasn't
    present (e.g. a heading immediately followed by body text with no gap
    stays exactly as tight as it was); only ever swaps an existing space
    for its marker form at the specific edge touching a <br/>.
    """
    if prev_is_break and text.startswith(" "):
        text = _SPACE_MARKER + text[1:]
    if next_is_break and text.endswith(" "):
        text = text[:-1] + _SPACE_MARKER
    return text


def _parse_fragment(html_string: str) -> lxml_html.HtmlElement:
    """Parse an HTML fragment (possibly several sibling elements/plain
    text, not a full document) by wrapping it in a throwaway <div> - same
    approach as tests/manual_verify_word_markers.py.
    """
    return lxml_html.fromstring(f"<div>{html_string}</div>")


def _validate_tags(root: lxml_html.HtmlElement, original: ParagraphHtml) -> None:
    """Raise ValueError if the <img>/<a data-run=...> tags found in a
    translated HTML fragment don't exactly match - by count AND data-run
    identity, not just count - what paragraph_to_html() originally put
    there. A lost/duplicated/reindexed image or hyperlink would otherwise
    be a silent data-loss bug instead of a loud, immediate failure.
    """
    found_img = sorted(str(el.get("data-run")) for el in root.iter("img"))
    expected_img = sorted(str(index) for index in original.image_runs)
    if found_img != expected_img:
        raise ValueError(
            f"<img data-run=...> mismatch after translation: found {found_img}, "
            f"expected {expected_img} (image lost/duplicated/reindexed - "
            f"see ParagraphHtml.image_runs)"
        )

    found_a = sorted(str(el.get("data-run")) for el in root.iter("a"))
    expected_a = sorted(str(index) for index in original.hyperlink_targets)
    if found_a != expected_a:
        raise ValueError(
            f"<a data-run=...> mismatch after translation: found {found_a}, "
            f"expected {expected_a} (hyperlink lost/duplicated/reindexed - "
            f"see ParagraphHtml.hyperlink_targets)"
        )


def log_break_anomaly(paragraph_index: int | str | None, details: dict) -> None:
    """Append one JSON line to _BREAK_ANOMALY_LOG_PATH recording a <br/>
    count mismatch between the HTML sent for translation and what came
    back - see _check_break_count() for when this fires. Mirrors
    pipeline.pdf.pymupdf_engine.log_growth_anomaly()'s pattern
    (structured JSONL, best-effort). Any I/O failure here is swallowed
    rather than raised: logging an anomaly must never itself break the
    translation it's only observing.
    """
    entry = {"paragraph_index": paragraph_index, **details}
    try:
        _BREAK_ANOMALY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_BREAK_ANOMALY_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _plain_text_preview(html_string: str, length: int = 80) -> str:
    """Strip tags from an HTML string for a short, readable log preview -
    not used for anything structural.
    """
    text = _parse_fragment(html_string).text_content()
    return " ".join(text.split())[:length]


def _check_break_count(
    original: ParagraphHtml, translated_html: str, paragraph_index: int | str | None
) -> None:
    """Log (never raise) if the translated HTML's <br/> count differs from
    original.html's.

    Deliberately a warning, not a ValueError like _validate_tags(): an
    <img>/<a data-run=...> mismatch is always a bug, because there's a
    concrete WordRun/hyperlink target that would otherwise be silently
    discarded with nothing to fall back to. A changed <br/> count has no
    such concrete casualty - a provider merging two break-separated
    fragments into one continuous sentence (observed with DeepL on real
    documents - see Backlog.md) can be a perfectly legitimate, more
    fluent translation choice, not data loss. So this is a signal worth
    reviewing in bulk across a document/corpus, not a reason to abort a
    translation that may well be correct.
    """
    original_count = len(list(_parse_fragment(original.html).iter("br")))
    translated_count = len(list(_parse_fragment(translated_html).iter("br")))
    if original_count == translated_count:
        return
    log_break_anomaly(
        paragraph_index,
        {
            "original_break_count": original_count,
            "translated_break_count": translated_count,
            "original_text_preview": _plain_text_preview(original.html),
            "translated_text_preview": _plain_text_preview(translated_html),
        },
    )


def _make_text_run(
    text: str,
    bold: bool,
    italic: bool,
    underline: bool,
    hyperlink_index: int | None,
    original: ParagraphHtml,
) -> WordRun:
    # Restore _SPACE_MARKER back to a real space wherever it ended up -
    # not necessarily still touching a <br/> after translation (the
    # provider is free to reflow text around it), but it always means
    # "a space belongs here" regardless of where it landed.
    text = text.replace(_SPACE_MARKER, " ")
    return WordRun(
        text=text,
        bold=bold,
        italic=italic,
        underline=underline,
        is_hyperlink=hyperlink_index is not None,
        hyperlink_target=(
            original.hyperlink_targets.get(hyperlink_index) if hyperlink_index is not None else None
        ),
        source_rpr=_copy_source_rpr(hyperlink_index, original),
    )


def _copy_source_rpr(hyperlink_index: int | None, original: ParagraphHtml) -> object:
    """The rPr a rebuilt WordRun should carry (see WordRun.source_rpr and
    ParagraphHtml.base_rpr/hyperlink_source_rpr): the specific original
    hyperlink run's own rPr if this text sits inside a <a data-run="n">
    tag, else the paragraph's general base_rpr. Deep-copied per call (like
    DocxEngine's own _copy_rpr()) so multiple WordRuns built from the same
    ParagraphHtml never share - and risk one mutating - the same element.
    """
    source = (
        original.hyperlink_source_rpr.get(hyperlink_index)
        if hyperlink_index is not None
        else original.base_rpr
    )
    return None if source is None else copy.deepcopy(source)


def _walk(
    element: lxml_html.HtmlElement,
    bold: bool,
    italic: bool,
    underline: bool,
    hyperlink_index: int | None,
    runs: list[WordRun],
    original: ParagraphHtml,
) -> None:
    """Depth-first walk of a parsed HTML fragment, appending one WordRun
    per text/img/br node found, tracking the active bold/italic/underline/
    hyperlink context through nesting (<b><u>...</u></b> -> both flags
    True on the inner text; a <br/> or plain text inherits whatever's
    currently active). Splits strictly on tag boundaries, never on text
    position relative to a <br/> - a provider can (and does, e.g. DeepL)
    shift plain text slightly across a break boundary, so this must not
    assume stable text offsets around breaks.

    lxml represents "text right after a tag closes, still part of the
    PARENT's content" as that child's .tail - handled with the parent's
    (not the child's) formatting/hyperlink context, per OOXML/HTML nesting
    semantics.
    """
    tag = element.tag
    if tag == "img":
        index = int(element.get("data-run"))
        runs.append(original.image_runs[index])
        return
    if tag == "br":
        runs.append(
            WordRun(
                text=BREAK_MARKER,
                bold=bold,
                italic=italic,
                underline=underline,
                is_hyperlink=hyperlink_index is not None,
                hyperlink_target=(
                    original.hyperlink_targets.get(hyperlink_index)
                    if hyperlink_index is not None
                    else None
                ),
                source_rpr=_copy_source_rpr(hyperlink_index, original),
            )
        )
        return

    child_bold = bold or tag == "b"
    child_italic = italic or tag == "i"
    child_underline = underline or tag == "u"
    child_hyperlink_index = int(element.get("data-run")) if tag == "a" else hyperlink_index

    if element.text:
        runs.append(
            _make_text_run(element.text, child_bold, child_italic, child_underline, child_hyperlink_index, original)
        )

    for child in element:
        _walk(child, child_bold, child_italic, child_underline, child_hyperlink_index, runs, original)
        if child.tail:
            runs.append(_make_text_run(child.tail, bold, italic, underline, hyperlink_index, original))


def html_to_paragraph(
    translated_html: str, original: ParagraphHtml, paragraph_index: int | str | None = None
) -> list[WordRun]:
    """Convert translated HTML (as produced by translating
    paragraph_to_html()'s output through a provider's translate_html())
    back into a list of WordRun - the inverse of paragraph_to_html().
    Does not write anything back into a .docx, purely builds the new run
    list, for a later write-back step to consume.

    - <img data-run="n"/> -> the ORIGINAL WordRun from
      original.image_runs[n] is reused as-is (same object) - the image is
      never translated/recreated.
    - <br/> -> a new WordRun with text=BREAK_MARKER (same convention
      DocxEngine uses when reading a <w:br/>).
    - <a data-run="n">text</a> -> a new WordRun with is_hyperlink=True,
      text=the translated text, hyperlink_target from
      original.hyperlink_targets[n] (the target is never translated,
      only the display text is new).
    - <b>/<i>/<u> around text -> a new WordRun with the translated text
      and the corresponding bold/italic/underline flags, correctly
      combining nested tags.
    - Plain text with no wrapping tag -> a new WordRun with whatever
      formatting/hyperlink context is active at that point.

    Raises ValueError if the translated HTML's <img>/<a data-run=...>
    tags don't exactly match (count AND identity) what the original
    ParagraphHtml recorded - see _validate_tags(). Only logs (never
    raises) a <br/> count mismatch - see _check_break_count().
    `paragraph_index`, if given, is included in that log entry to say
    which paragraph an anomaly came from; purely for logging, has no
    effect on the returned runs.
    """
    root = _parse_fragment(translated_html)
    _validate_tags(root, original)
    _check_break_count(original, translated_html, paragraph_index)

    runs: list[WordRun] = []
    _walk(root, False, False, False, None, runs, original)
    return runs
