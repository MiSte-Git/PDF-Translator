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

from dataclasses import dataclass, field
from typing import Callable

from pipeline.images.inpainting import InpaintingBackend, InpaintingError, TextReplacement
from pipeline.images.ocr import OcrEngine, OcrTextRegion
from pipeline.translation.base import TranslationError, TranslationProvider
from pipeline.translation.protected_terms import protect_terms, restore_terms


@dataclass
class ImageTranslationStats:
    """translate_image()'s result. Flat (translated/failed), like
    PdfTranslationStats - an image has no header/footer-style structural
    split either."""

    translated: int = 0
    failed: int = 0
    chars_sent: int = 0
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)
    """Human-readable "region N: exception" strings for every failed
    region - same role as the other three formats' equivalent field,
    never includes credentials."""
    regions: list[OcrTextRegion] = field(default_factory=list)
    """Every region OCR actually recognized, in reading order -
    independent of translated/failed outcome. Kept for the QA report."""
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
        return self.translated + self.failed


def build_corrected_replacements(
    replacements: list[TextReplacement],
    edited_texts: dict[int, str],
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

    An index outside `range(len(replacements))` in `edited_texts` is
    silently ignored - lets a caller pass a dict built once against a
    possibly-stale `replacements` length without needing to defensively
    filter it first.
    """
    corrected: list[TextReplacement] = []
    for index, replacement in enumerate(replacements):
        edited_text = edited_texts.get(index)
        if edited_text is None or edited_text == replacement.translated_text:
            corrected.append(replacement)
            continue
        corrected.append(TextReplacement(region=replacement.region, translated_text=edited_text))
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
    final outcome (translated/failed) with the current cumulative
    `stats`, mirroring the other three formats' live progress support.
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

    for index, region in enumerate(regions):
        if _cancelled():
            stats.cancelled = True
            break

        _notify(f"Textregion {index + 1}/{len(regions)}...")
        try:
            protected_text, mapping = protect_terms(region.text, protected_terms)
            result = provider.translate(protected_text, target_lang=target_lang, source_lang=source_lang)
            translated_text = restore_terms(result.text, mapping)
        except TranslationError as exc:
            _notify(f"  FEHLER (uebersprungen): {exc}")
            stats.failed += 1
            stats.errors.append(f"region{index}: {type(exc).__name__}: {exc}")
            _report()
            continue

        stats.chars_sent += len(protected_text)
        stats.replacements.append(TextReplacement(region=region, translated_text=translated_text))
        stats.translated += 1
        _report()

    try:
        inpainting_backend.apply(source_path, stats.replacements, destination_path)
    except InpaintingError:
        # Re-raised, not swallowed: without a written output file the
        # job cannot claim success, no matter how many regions were
        # successfully translated above - mirrors how a PDF/Word/PPTX
        # job's own final engine.save() failure is never caught either.
        raise

    return stats
