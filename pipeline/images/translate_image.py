"""Reusable full-image OCR+Übersetzung+Rückschreibung-Durchlauf
(RoadMap.md Phase 3 - Bildübersetzung und OCR).

Mirrors pipeline.pdf.translate_pdf.translate_pdf() /
pipeline.word.translate_document.translate_document() /
pipeline.presentation.translate_presentation.translate_presentation():
same cooperative-cancellation contract (polled between, never during, API
calls), same "one bad region's TranslationError is caught and counted as
failed rather than aborting the whole image" policy, same progress/stats
callback shape - so ui/image_job.py can drive the same Start/progress/
cancel/QA-report UI flow (ui/app.py::_EXECUTABLE_MODES) the other three
formats already use.

Structurally different from the other three: there is no single
already-open, in-place-mutable document object to redact/insert into.
Instead this module runs OCR once (pipeline.images.ocr.OcrEngine) to get
every text region up front, translates each region's text, and hands the
whole set of (region, translated_text) pairs to a single
pipeline.images.inpainting.InpaintingBackend.apply() call at the end -
partial/incremental writeback per region isn't something any of the four
backends support (see their own docstrings), so unlike the PDF/Word/PPTX
loops, a cancelled run's already-translated regions are NOT reflected in
the output file - see translate_image()'s docstring for what a
cancellation actually does here.
"""
from __future__ import annotations

import dataclasses
import statistics
from dataclasses import dataclass, field
from typing import Callable

from pipeline.images.inpainting import InpaintingBackend, InpaintingError, TextReplacement
from pipeline.images.ocr import (
    OcrEngine,
    OcrTextRegion,
    merge_lines_into_paragraphs,
    merge_region_group,
    region_line_height,
)
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.protected_terms import protect_terms, restore_terms

# Default minimum Tesseract word-confidence (0-100, see OcrTextRegion.confidence's
# docstring) a region must have to be translated/replaced at all - added
# after a real user found garbled, overlapping output on a chat-app
# screenshot (RoadMap.md/Backlog.md, 18.08.2026): several of the worst
# artifacts turned out to be UI icons/graphics (a mute-icon row, a
# down-arrow, anti-aliasing halos around bold headings) that Tesseract
# misread as text, each with a conspicuously low confidence score
# (20s-40s) compared to genuine text lines (80s-90s) in the SAME image.
# 40.0 is deliberately conservative - chosen from that one real sample,
# not a broadly validated cutoff - so it only screens out the clearest
# noise; a region this unsure about being real text at all is skipped
# entirely (left untouched, see ImageTranslationStats.skipped below)
# rather than translated into equally nonsensical target-language text
# and drawn on top of whatever it actually was. This is a heuristic, not
# a fix for the underlying OCR misread - some medium-confidence noise
# (see Backlog.md's documented residual cases) still gets through.
DEFAULT_MIN_OCR_CONFIDENCE = 40.0

# Ratio (region.height / the image's own MEDIAN recognized-line height)
# beyond which a region is treated as an OCR bounding-box outlier and
# skipped rather than drawn - added after a real user-reported infographic
# (RoadMap.md/Backlog.md, 21.08.2026) as a safety net alongside the (more
# targeted) fix for that same image's DOMINANT problem, cross-column line
# merging (see pipeline.images.ocr._MAX_WORD_GAP_RATIO): a region whose
# bounding box got inflated some OTHER way - e.g. Tesseract folding a
# nearby icon/graphic element into a text line's box, inflating just its
# HEIGHT far beyond every other line in the image - would still be drawn
# at close to pipeline.images.inpainting._MAX_FONT_SIZE, towering over and
# overlapping neighbouring text, without necessarily scoring low enough on
# DEFAULT_MIN_OCR_CONFIDENCE to be screened out there instead.
#
# Compared against the image's own MEDIAN recognized-line height (among
# regions that already pass min_confidence) rather than a fixed pixel
# value, since designs vary hugely in base font size - and MEDIAN rather
# than mean so a handful of genuinely large headlines don't drag the
# baseline up and mask a real outlier. 4.0x was picked by checking it
# against the one real sample above AFTER the word-gap fix: two
# legitimately large (but real, not icon-merged) bold banner lines in that
# image sat at ~3.5-3.8x the median and must NOT be skipped, while nothing
# in that sample needed a ceiling below 4x to be caught - so, like
# DEFAULT_MIN_OCR_CONFIDENCE, a real-sample-calibrated heuristic, not a
# broadly validated cutoff.
DEFAULT_MAX_HEIGHT_RATIO = 4.0


def _max_plausible_height(
    regions: list[OcrTextRegion], min_confidence: float, max_height_ratio: float
) -> float | None:
    """DEFAULT_MAX_HEIGHT_RATIO times the median height among `regions`
    that pass `min_confidence` - the per-image threshold
    translate_image() compares each region's height against (see that
    constant's docstring). None if there are no such regions to compute a
    median from, so the caller can skip the outlier check entirely rather
    than compare against nothing.

    Uses region_line_height(), not `region.height` directly, for both the
    median and (in translate_image()'s own filter below) each individual
    comparison - added 23.08.2026 alongside GoogleVisionOcrEngine/
    PaddleOcrEngine, the first engines whose recognize() can itself return
    a region spanning several original lines (see
    OcrEngine.returns_paragraph_regions's docstring). This check exists to
    catch a bounding box inflated some OTHER way than genuine multi-line
    text (an icon/graphic folded into it - see DEFAULT_MAX_HEIGHT_RATIO's
    docstring), a single-line concept; comparing a legitimate multi-line
    PARAGRAPH's full `height` against a threshold calibrated for
    single-line outliers would misfire exactly the cases these two
    engines exist to get right.

    24.08.2026: also excludes `not region.translatable` regions (see
    that field's docstring) - a label-excluded-but-real-text block
    (e.g. PaddleOcrEngine's "image"-labeled blocks) is never a
    translation candidate and was never part of this median before it
    existed as a region at all; letting its often much larger bbox
    height into the median here would skew the "plausible" threshold
    for the regions this check actually exists to filter.
    """
    heights = [
        region_line_height(region)
        for region in regions
        if region.confidence >= min_confidence and region.translatable
    ]
    if not heights:
        return None
    return statistics.median(heights) * max_height_ratio


@dataclass
class ImageTranslationStats:
    """translate_image()'s result. Flat (translated/skipped/failed), like
    PdfTranslationStats - an image has no header/footer-style structural
    split either."""

    translated: int = 0
    skipped: int = 0
    """Regions recognized by OCR but never even sent for translation, for
    either of two reasons (see translate_image()'s docstring): their
    confidence was below `min_confidence` (DEFAULT_MIN_OCR_CONFIDENCE), or
    their height exceeded the image's own outlier threshold
    (`max_height_ratio`, DEFAULT_MAX_HEIGHT_RATIO) - not distinguished
    further here since both mean the same thing to a user reading the QA
    report ("left untouched, check manually if needed"); the progress
    callback message for each region does distinguish them. Distinct from
    `failed` (a region that WAS attempted but the provider call itself
    raised). Mirrors PdfTranslationStats.skipped's role (a structurally-
    excluded block, not an error)."""
    failed: int = 0
    chars_sent: int = 0
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)
    """Human-readable "region N: exception" strings for every failed
    region - same role as the other three formats' equivalent field,
    never includes credentials."""
    regions: list[OcrTextRegion] = field(default_factory=list)
    """Every region OCR actually recognized, in reading order -
    independent of translated/skipped/failed outcome. Kept for the QA
    report."""
    replacements: list[TextReplacement] = field(default_factory=list)
    """Every SUCCESSFULLY translated region, paired with its translated
    text - mirrors PdfTranslationStats.blocks' role for the manual
    correction dialog (RoadMap.md Phase 3's "Korrektur-Möglichkeit ...
    analog zur PDF-Variante" item, see ui/image_correction_dialog.py).
    Like TranslatedBlockRecord, only successfully-translated regions are
    included here - a FAILED region (see `errors` above) has no
    translated text to show/correct, so it's simply absent from this
    list rather than included with an empty placeholder. This is the
    exact same list that was handed to inpainting_backend.apply() to
    produce the output file - re-running apply() with an edited copy of
    it against the pristine source is the entire correction mechanism
    (see ui/image_job.py::run_image_correction_job()), no OCR/provider
    re-run needed."""

    @property
    def processed(self) -> int:
        return self.translated + self.skipped + self.failed


def build_corrected_replacements(
    replacements: list[TextReplacement],
    edited_texts: dict[int, str],
    edited_geometry: dict[int, tuple[int, int, int, int]] | None = None,
) -> list[TextReplacement]:
    """Turn a correction-table UI's edits back into a new list of
    TextReplacement ready for a fresh InpaintingBackend.apply() call -
    the image counterpart of pipeline.pdf.translate_pdf's
    build_corrected_records_from_html(), simplified because
    TextReplacement.translated_text is a plain str (raster-drawn image
    text via ImageDraw.text() has no bold/italic/underline concept the
    way a PDF's rich-text box does - see ui/image_correction_dialog.py).

    `edited_texts` maps a `replacements` LIST INDEX (row position in the
    correction table, not a (page_index, block_index) pair - a single
    image's replacements have no page concept) -> the CURRENT text shown
    in that row's editable cell. Only an index actually present in
    `edited_texts` AND whose text differs from the original
    `translated_text` gets a brand new TextReplacement (same `region`,
    new `translated_text`); every other row is passed through with its
    EXACT original TextReplacement object, unchanged - mirrors
    build_corrected_records_from_html()'s "only touch rows that were
    genuinely dirty" contract.

    `edited_geometry` - added for the draggable/resizable box canvas in
    ImageCorrectionDialog (RoadMap.md/Backlog.md 21.08.2026: a real user's
    infographic still had a handful of boxes in the wrong place/size even
    after the automatic placement fixes, and asked for a way to nudge
    individual boxes by hand rather than accept-or-redo-nothing) - maps a
    `replacements` LIST INDEX to a (x, y, width, height) pixel tuple in
    the SAME coordinate system as OcrTextRegion (top-left origin, whole
    image). An index present here gets a NEW TextReplacement.render_box
    built with this geometry (26.08.2026 - see that field's own
    docstring: `region` itself is now NEVER touched by a geometry edit,
    it stays the ORIGINAL recognized position forever, exactly what its
    own docstring already promised) independently of whether that same
    index is also present in `edited_texts`: a row can have its text
    corrected, its box moved/resized, both, or neither, in any
    combination. None (the default) behaves exactly like the
    pre-geometry-editing version of this function - no render_box is
    ever set.

    Before 26.08.2026, `geometry` overwrote `region` in place
    (`dataclasses.replace(region, x=..., ...)`) - which quietly broke
    that field's own "keeps the ORIGINAL recognized OcrTextRegion"
    contract the moment a human dragged a box, and was the real cause of
    a real user's report (Backlog.md 26.08.2026: "die Positionen, Grösse
    und Korrekturen werden nicht übernommen") - every InpaintingBackend.
    apply() erases/estimates style from `region`, so once it silently
    became "wherever the box was dragged to", the ORIGINAL untranslated
    source text at its real position was never erased at all.

    An index outside `range(len(replacements))` in either dict is
    silently ignored - lets a caller pass a dict built once against a
    possibly-stale `replacements` length without needing to defensively
    filter it first.
    """
    corrected: list[TextReplacement] = []
    for index, replacement in enumerate(replacements):
        edited_text = edited_texts.get(index)
        text_changed = edited_text is not None and edited_text != replacement.translated_text
        geometry = edited_geometry.get(index) if edited_geometry else None
        if not text_changed and geometry is None:
            corrected.append(replacement)
            continue
        render_box = replacement.render_box
        if geometry is not None:
            x, y, width, height = geometry
            render_box = dataclasses.replace(replacement.region, x=x, y=y, width=width, height=height)
        translated_text = edited_text if text_changed else replacement.translated_text
        corrected.append(
            TextReplacement(region=replacement.region, translated_text=translated_text, render_box=render_box)
        )
    return corrected


def translate_image(
    source_path: str,
    destination_path: str,
    ocr_engine: OcrEngine,
    inpainting_backend: InpaintingBackend,
    provider: TranslationProvider,
    protected_terms: list[str],
    target_lang: str,
    source_lang: str | None = None,
    ocr_language: str | None = None,
    min_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
    max_height_ratio: float = DEFAULT_MAX_HEIGHT_RATIO,
    progress_callback: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    stats_callback: Callable[[ImageTranslationStats], None] | None = None,
) -> ImageTranslationStats:
    """Recognize, translate, and rewrite every text region of the image at
    `source_path`, writing the result to `destination_path`.

    OCR itself (ocr_engine.recognize()) is NOT wrapped in a try/except -
    unlike a single region's TranslationError below, an OCR failure means
    there are no regions at all to work with, so pipeline.images.ocr.OcrError
    propagates straight to the caller (ui/image_job.py, whose worker already
    wraps the whole job call - mirrors ui/workers.py::PdfTranslationWorker.run()).

    A region whose `region.confidence` is below `min_confidence` (see
    DEFAULT_MIN_OCR_CONFIDENCE's docstring), OR whose height exceeds the
    image's own outlier threshold (`max_height_ratio` times the median
    recognized-line height - see DEFAULT_MAX_HEIGHT_RATIO's docstring), is
    never sent to the provider at all - counted in `stats.skipped`, left
    completely untouched in the output (no translation, no box drawn over
    it), same "don't guess" principle as everything else in this pipeline
    that fails closed.

    `should_cancel`, if given, is polled before each region's translation
    call (between API calls, never mid-call). Once it returns True,
    stats.cancelled is set and translation of further regions stops -
    BUT, unlike the other three formats, inpainting_backend.apply() is
    still called once at the end with whatever regions were successfully
    translated before cancellation: there is no meaningful "partially
    written image file" the way there is a partially-redacted PDF page,
    so a cancelled run still produces an output file with every region
    translated up to the cancellation point, and every later region left
    in its original (untranslated) state.

    `stats_callback`, if given, is called after every region reaches a
    final outcome (translated/skipped/failed) with the current cumulative
    `stats`, mirroring the other three formats' live progress support.

    Since 22.08.2026: every region NOT translated (skipped, failed, or
    never reached due to cancellation) is passed to
    `inpainting_backend.apply()` as `obstacle_regions` - its original
    pixels are still visible in the output, so a NEIGHBOURING translated
    region's text must still avoid growing into it (see that parameter's
    docstring on InpaintingBackend.apply() and
    pipeline.images.inpainting._vertical_room_below()).

    Also since 22.08.2026 (verifying the fix above against a real,
    densely-laid-out infographic showed it wasn't nearly enough - see
    pipeline.images.ocr.merge_lines_into_paragraphs()'s docstring for the
    full diagnosis): regions that pass min_confidence/max_height_ratio are
    no longer translated and redrawn one Tesseract LINE at a time.
    Consecutive lines recognized as the same wrapped sentence/bullet are
    merged first (see that function) into ONE translation call (better
    context too, not just layout) and ONE drawn block, sized against the
    union of their original bounding boxes. `stats.translated`/
    `stats.failed` still count in ORIGINAL-line units, not merged blocks
    - `stats.processed` (translated+skipped+failed) still equals
    len(regions) whenever the run isn't cancelled partway through,
    unchanged from before this merge step existed.

    Since 23.08.2026 (GoogleVisionOcrEngine/PaddleOcrEngine, added after
    comparing Google's own image translation against ours - see
    Backlog.md): when `ocr_engine.returns_paragraph_regions` is True, the
    merge step above is skipped entirely - the engine's own recognize()
    already returned paragraph-grouped regions, so re-running the
    geometric line-merge heuristic against them would be redundant at
    best. `max_plausible_height`'s outlier check also uses each region's
    representative single-line height (pipeline.images.ocr.
    region_line_height()) rather than its raw `height` for exactly this
    reason - a legitimate multi-line paragraph must not be mistaken for
    an icon-inflated bounding box.
    """
    stats = ImageTranslationStats()

    def _notify(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    def _report() -> None:
        if stats_callback is not None:
            stats_callback(stats)

    def _cancelled() -> bool:
        return should_cancel is not None and should_cancel()

    regions = ocr_engine.recognize(source_path, language=ocr_language)
    stats.regions = regions
    max_plausible_height = _max_plausible_height(regions, min_confidence, max_height_ratio)

    eligible: list[OcrTextRegion] = []
    for index, region in enumerate(regions):
        # 24.08.2026: a region an OcrEngine itself marked untranslatable
        # (see OcrTextRegion.translatable's docstring) is skipped here
        # the same way a too-low-confidence region is - never eligible
        # for translation, but (via the `translated_original_ids`
        # bookkeeping below, unchanged) still ends up in
        # `obstacle_regions` so neighbouring regions' collision
        # avoidance still sees its real, untouched pixels.
        if not region.translatable:
            _notify(
                f"Textregion {index + 1}/{len(regions)}: uebersprungen "
                f"(Layout-Kategorie nicht fuer Uebersetzung vorgesehen)"
            )
            stats.skipped += 1
            _report()
            continue

        if region.confidence < min_confidence:
            _notify(
                f"Textregion {index + 1}/{len(regions)}: uebersprungen "
                f"(niedrige OCR-Konfidenz {region.confidence:.0f})"
            )
            stats.skipped += 1
            _report()
            continue

        if max_plausible_height is not None and region_line_height(region) > max_plausible_height:
            _notify(
                f"Textregion {index + 1}/{len(regions)}: uebersprungen "
                f"(ungewoehnlich grosse Bounding-Box, vermutlich Icon-/"
                f"Grafik-Fehllesung - Hoehe {region_line_height(region)}px, "
                f"erwartet bis zu {max_plausible_height:.0f}px)"
            )
            stats.skipped += 1
            _report()
            continue

        eligible.append(region)

    # Since 23.08.2026 (GoogleVisionOcrEngine/PaddleOcrEngine): an engine
    # whose recognize() already returns paragraph-grouped regions skips
    # merge_lines_into_paragraphs() entirely - see
    # OcrEngine.returns_paragraph_regions's docstring for why re-running
    # that geometric heuristic against already-correct paragraphs would be
    # at best redundant and at worst actively harmful (it could wrongly
    # fuse two separate, correctly-formed paragraphs that merely sit close
    # together - its gap threshold is calibrated for single-line gaps).
    # Each eligible region becomes its own one-element group.
    engine_returns_paragraphs = getattr(ocr_engine, "returns_paragraph_regions", False)
    groups = [[region] for region in eligible] if engine_returns_paragraphs else merge_lines_into_paragraphs(eligible)
    translated_original_ids: set[int] = set()

    for group_index, group in enumerate(groups):
        if _cancelled():
            stats.cancelled = True
            break

        _notify(f"Textblock {group_index + 1}/{len(groups)}...")
        joined_text = " ".join(region.text for region in group)
        try:
            protected_text, mapping = protect_terms(joined_text, protected_terms)
            result = provider.translate(protected_text, target_lang=target_lang, source_lang=source_lang)
            translated_text = restore_terms(result.text, mapping)
        except TranslationError as exc:
            _notify(f"  FEHLER (uebersprungen): {exc}")
            stats.failed += len(group)
            stats.errors.append(f"block{group_index}: {type(exc).__name__}: {exc}")
            _report()
            continue

        stats.chars_sent += len(protected_text)
        # For an engine_returns_paragraphs group, `group` is always a
        # single already-correct region (see above) - merge_region_group()
        # would rebuild it from scratch and, critically, RECOMPUTE
        # line_height from group[0].height alone (its own docstring: built
        # for single-LINE Tesseract regions, where height IS the line
        # height), destroying the multi-line-aware line_height
        # GoogleVisionOcrEngine/PaddleOcrEngine already computed correctly
        # at recognize() time. Using the region as-is avoids that.
        merged_region = group[0] if engine_returns_paragraphs else merge_region_group(group)
        stats.replacements.append(TextReplacement(region=merged_region, translated_text=translated_text))
        stats.translated += len(group)
        translated_original_ids.update(id(region) for region in group)
        _report()

    # Every ORIGINAL region OCR recognized but whose id() never made it
    # into translated_original_ids (skipped for low confidence/outlier
    # height, its whole merged group's provider call failed, or never
    # reached at all because should_cancel fired first) still shows its
    # ORIGINAL, untouched pixels in the output - `id()`, not equality,
    # since OcrTextRegion isn't hashable and region objects are reused
    # as-is (never copied) between `regions` and each merge_lines_into_
    # paragraphs() group - see InpaintingBackend.apply()'s
    # `obstacle_regions` parameter docstring (added 22.08.2026, closing
    # the gap _vertical_room_below() documented until then) for why these
    # must still count as collision obstacles for the regions that DO get
    # drawn. Deliberately NOT `{id(r.region) for r in stats.replacements}`
    # any more - a replacement's `region` is now merge_region_group()'s
    # brand-new UNION region, whose id() never matches any of `regions`'
    # original per-line objects at all.
    obstacle_regions = [region for region in stats.regions if id(region) not in translated_original_ids]

    try:
        inpainting_backend.apply(
            source_path, stats.replacements, destination_path, obstacle_regions=obstacle_regions
        )
    except InpaintingError:
        # Re-raised, not swallowed: without a written output file the
        # job cannot claim success, no matter how many regions were
        # successfully translated above - mirrors how a PDF/Word/PPTX
        # job's own final engine.save() failure is never caught either.
        raise

    return stats
