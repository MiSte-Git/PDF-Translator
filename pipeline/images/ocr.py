"""OCR-Backend-Abstraktion für die Bildübersetzung (RoadMap.md Phase 3).

Spiegelt pipeline/translation/base.py::TranslationProvider bewusst 1:1:
ein Protocol (`OcrEngine`), gegen das mehrere austauschbare
Implementierungen laufen - analog zu DeepL/Google/OpenAI/Grok bei der
Übersetzung. Verfügbarkeit wird jeweils VOR dem eigentlichen Lauf geprüft
(siehe `tesseract_available()` unten und ui/settings.py::
credential_status() für das Übersetzungs-Pendant), damit ein Nutzer ohne
installiertes Tesseract das im UI als ausgegraute/deaktivierte Option
sieht statt mitten im Lauf eine kryptische Exception zu bekommen.

Aktuell ein Backend (TesseractOcrEngine, lokal). Ein Cloud-OCR-Backend
ist als zweite OcrEngine-Implementierung vorgesehen (siehe RoadMap.md),
konkreter Anbieter noch offen - der Grund für die Protocol-Abstraktion
hier statt eines direkten Tesseract-Aufrufs ist genau, dass ein
zusätzliches Backend später ergänzt werden kann, ohne dass Aufrufer
(ui/image_job.py) sich ändern müssen.
"""
from __future__ import annotations

import base64
import shutil
from dataclasses import dataclass, replace as _dataclass_replace
from typing import Protocol, runtime_checkable


class OcrError(Exception):
    """Raised when an OCR engine fails: missing binary, unreadable image,
    or an unexpected recognizer error. Mirrors
    pipeline.translation.base.TranslationError - callers handle OCR
    failures uniformly regardless of which engine is in use.
    """


@dataclass(frozen=True)
class OcrTextRegion:
    """One recognized text line within an image, in pixel coordinates of
    the ORIGINAL image (top-left origin - the convention Pillow, OpenCV
    and PyMuPDF's pixel-space all share).

    `confidence` is the engine's own average word-confidence for this
    line (0-100, Tesseract's scale - not normalized further since there
    is currently only one engine; a future second backend may need its
    own normalization, not this dataclass's job). Not used for filtering
    yet, kept for a future QA report column - mirrors how
    PyMuPdfEngine's TextBlock keeps span-level detail around even before
    every consumer needs it.

    `line_height` (22.08.2026, default None) - set only by
    pipeline.images.translate_image.merge_lines_into_paragraphs() when
    this region is the MERGED union of several original single-line
    regions (see that function's docstring): `height` then spans every
    merged line together (needed for collision avoidance - the merged
    block's true vertical extent), while `line_height` keeps the
    original single line's own height, the value
    pipeline.images.inpainting._initial_font_size() actually needs to
    seed a sensible starting font size - using the merged `height`
    there directly would seed a font sized for the WHOLE multi-line
    block, not one line of it, rendering far too large. None (every
    OTHER region, everywhere else in the codebase - OCR always returns
    single-line regions) means "this region already IS one line, use
    `height` directly", so every existing caller/test that never
    supplies this field keeps working unchanged.

    `translatable` (24.08.2026, default True) - False marks a region
    that pipeline.images.translate_image must NEVER send for
    translation, but whose ORIGINAL pixels are genuinely there and
    must still be protected as a collision obstacle for neighbouring
    regions (pipeline.images.inpainting._vertical_room_below()/
    _horizontal_room()). Added for PaddleOcrEngine's "image"-labeled
    layout blocks with real OCR'd text inside (see
    _PADDLE_TRANSLATABLE_LABELS's docstring for the 24.08.2026 "added,
    then reverted" story) - excluding such a block from
    _PADDLE_TRANSLATABLE_LABELS used to mean it never became an
    OcrTextRegion AT ALL, so translate_image.py's `obstacle_regions`
    mechanism (built 22.08.2026 for exactly this "don't grow text over
    real content" purpose) never even saw it. That gap is what let the
    23.08.2026 horizontal-reflow feature (pipeline.images.inpainting.
    _horizontal_room()) expand a NEIGHBOURING region's text sideways
    straight over the Thoughts/Emotions list's still-visible English
    text once "image" was excluded again (QA-Bericht "(15)", Michael:
    "Das ist jetzt noch schlimmer als das vorherige. Die Font stimmen
    gar nicht mehr usw.") - `regions = [25,457,394,718]`'s block was
    invisible to every collision check, not just to translation.
    `translatable=False` keeps the region OUT of translation (see
    translate_image()'s eligibility loop) while keeping it IN
    `stats.regions`/`obstacle_regions`, so this failure mode cannot
    repeat for the next excluded-but-real-text block found. Every
    other engine/every existing caller leaves this at its True default
    and is unaffected."""

    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    line_height: int | None = None
    translatable: bool = True


def region_line_height(region: OcrTextRegion) -> int:
    """The representative SINGLE-LINE height to use for font-sizing and
    outlier-height checks against `region` - `region.line_height` if set
    (region is a multi-line merged/paragraph block, see that field's
    docstring), otherwise `region.height` directly (region already IS one
    line).

    Shared by pipeline.images.inpainting._initial_font_size() and
    pipeline.images.translate_image (its median-height outlier filter) -
    both need the same correction, and both predate 23.08.2026's
    GoogleVisionOcrEngine/PaddleOcrEngine (see below), the first OcrEngine
    implementations whose recognize() itself can return a region that
    already spans multiple original lines (Tesseract/merge_lines_into_
    paragraphs() were, until then, the only source of multi-line regions,
    always well after this exact check already existed at the call sites
    it's now centralized from).
    """
    return region.line_height if region.line_height is not None else region.height


@runtime_checkable
class OcrEngine(Protocol):
    """Minimal interface every OCR engine (Tesseract/cloud backends) must
    implement - mirrors TranslationProvider.translate()'s role for the
    translation side.

    `returns_paragraph_regions` (class attribute, default False when
    absent - checked with `getattr(engine, "returns_paragraph_regions",
    False)`, not part of the Protocol's structural contract so existing
    engines/tests that don't know about it keep working unchanged): True
    for an engine whose recognize() already groups text at PARAGRAPH/
    layout-block granularity (GoogleVisionOcrEngine, PaddleOcrEngine - see
    their own docstrings) rather than one region per physical OCR line
    (TesseractOcrEngine). pipeline.images.translate_image checks this flag
    to skip its own merge_lines_into_paragraphs() heuristic for such an
    engine - re-running that geometric line-merge heuristic against
    regions that are already whole paragraphs would at best do nothing
    and at worst wrongly fuse two separate, correctly-formed paragraphs
    that happen to sit close together (the heuristic's gap threshold is
    calibrated for single-line gaps, not paragraph-to-paragraph gaps).
    """

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        """Return recognized text regions for the image at `image_path`,
        in reading order (top-to-bottom).

        `language` is an engine-specific hint (Tesseract expects its
        3-letter code, e.g. "eng" or "deu"; GoogleVisionOcrEngine expects
        a BCP-47-ish code, e.g. "en"/"de"; PaddleOcrEngine (PP-OCRv5)
        expects the same short ISO code, e.g. "en"/"de" - see each
        engine's own docstring) - None lets the engine fall back to its
        own default.
        """
        ...


def tesseract_available() -> bool:
    """Whether the local Tesseract binary can be found on PATH.

    Checked BEFORE a job starts (ui/analysis.py, mirrors
    ui/settings.py::credential_status() for the translation providers) so
    a missing installation surfaces as a disabled/greyed UI option
    instead of a mid-run crash - relevant in particular for a possible
    future standalone build, where Tesseract may not be present at all
    (see RoadMap.md Phase 3).
    """
    return shutil.which("tesseract") is not None


class TesseractOcrEngine:
    """OcrEngine backed by the local Tesseract binary via pytesseract.

    pytesseract is imported lazily inside recognize(), not at module
    level - mirrors how ui/analysis.py imports PyMuPDF lazily inside the
    PDF branch, so the other UI modes stay usable even in an environment
    where the (optional, listed in requirements-ocr.txt) pytesseract
    package is not installed.
    """

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        if not tesseract_available():
            raise OcrError(
                "Tesseract-Binary wurde nicht gefunden (PATH). Installation "
                "prüfen oder eine Cloud-OCR-Engine wählen."
            )
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise OcrError(
                f"OCR-Abhängigkeit fehlt: {exc}. Siehe requirements-ocr.txt."
            ) from exc

        try:
            with Image.open(image_path) as image:
                data = pytesseract.image_to_data(
                    image,
                    lang=language or "eng",
                    output_type=pytesseract.Output.DICT,
                )
        except Exception as exc:  # tesseract binary/runtime failure, corrupt image, ...
            raise OcrError(f"Tesseract-Erkennung fehlgeschlagen: {exc}") from exc

        return _group_words_into_lines(data)


_VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


def google_vision_available() -> bool:
    """Whether a usable Google API key is configured right now - checked
    BEFORE a job starts (mirrors tesseract_available() above and
    pipeline.registry.provider_credential_status() for translation
    providers). Deliberately reuses pipeline.credentials.
    get_google_translate_api_key() rather than introducing a separate
    "vision" credential: Michael confirmed (23.08.2026) his existing key
    already has both the Cloud Translation and Cloud Vision APIs enabled
    on the same Google Cloud project - Google Cloud API keys are scoped
    per PROJECT, not per API, so a second, separately-named credential
    would only add setup friction with no real benefit. Like
    tesseract_available(), this only checks that A key is configured, not
    that it is valid or has the Vision API actually enabled for its
    project - an invalid/under-permissioned key still surfaces as a clear
    API error message at the first recognize() call below, same
    limitation provider_credential_status() already accepts for the
    translation providers.
    """
    from pipeline.credentials import get_google_translate_api_key

    try:
        get_google_translate_api_key()
    except RuntimeError:
        return False
    return True


def _extract_vision_error(exc) -> str:
    """Pulls a human-readable message out of a failed Vision API request -
    mirrors pipeline.translation.google_provider._extract_error_message()
    (duplicated rather than imported: ocr.py deliberately doesn't depend
    on pipeline.translation.*, keeping the two subsystems' import graphs
    independent, the same reasoning TesseractOcrEngine's lazy imports
    already follow)."""
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


def _vertices_bbox(vertices: list[dict]) -> tuple[int, int, int, int] | None:
    """(x0, y0, x1, y1) union of a Vision boundingBox's `vertices` list -
    None if `vertices` is empty (a degenerate/zero-area box some Vision
    responses do contain; skipped rather than fabricating one). Vision
    OMITS an `x`/`y` key entirely when that coordinate is exactly 0 (a
    documented quirk of its protobuf-to-JSON encoding, confirmed against
    the real image this was built against - not a bug in this code) -
    `.get(..., 0)` handles that.
    """
    if not vertices:
        return None
    xs = [vertex.get("x", 0) for vertex in vertices]
    ys = [vertex.get("y", 0) for vertex in vertices]
    return min(xs), min(ys), max(xs), max(ys)


def _vision_paragraph_to_region(paragraph: dict) -> OcrTextRegion | None:
    """One OcrTextRegion from a single Vision fullTextAnnotation paragraph
    dict - None if the paragraph has no usable bounding box, or ends up
    with no surviving (non-blank, non-decorative) words at all (mirrors
    _group_words_into_lines()'s same policy for Tesseract - a purely
    decorative paragraph never becomes a region rather than becoming one
    whose entire text is noise)."""
    box = _vertices_bbox((paragraph.get("boundingBox") or {}).get("vertices") or [])
    if box is None:
        return None
    x0, y0, x1, y1 = box

    words: list[str] = []
    word_heights: list[int] = []
    for word in paragraph.get("words") or []:
        text = "".join(symbol.get("text", "") for symbol in word.get("symbols") or [])
        if not text or _is_decorative_symbol_token(text):
            continue
        words.append(text)
        word_box = _vertices_bbox((word.get("boundingBox") or {}).get("vertices") or [])
        if word_box is not None:
            word_heights.append(word_box[3] - word_box[1])
    if not words:
        return None

    confidence = float(paragraph.get("confidence", 0.0)) * 100
    # See OcrTextRegion.line_height's docstring: a word's own bounding-box
    # height is always a single-line measurement, whether the PARAGRAPH it
    # belongs to spans one line or several - unlike Tesseract/
    # merge_region_group(), there is no separate "original single line"
    # object to average over here, so word height is the next best proxy.
    line_height = round(sum(word_heights) / len(word_heights)) if word_heights else None
    return OcrTextRegion(
        text=" ".join(words), x=x0, y=y0, width=x1 - x0, height=y1 - y0,
        confidence=confidence, line_height=line_height,
    )


class GoogleVisionOcrEngine:
    """OcrEngine backed by the Cloud Vision API's DOCUMENT_TEXT_DETECTION
    feature (REST, plain API-key auth - same auth style as
    pipeline.translation.google_provider.GoogleTranslateProvider, see that
    module's docstring for why requests instead of the google-cloud-vision
    SDK).

    returns_paragraph_regions = True (see OcrEngine's docstring): Vision's
    response is already grouped page -> block -> PARAGRAPH -> word ->
    symbol by its own trained layout model, not per physical OCR line -
    added and calibrated (23.08.2026) after Michael asked "was nutzt
    Google da?" (following up on why Google's own image translation shows
    so much less overlap than ours) and, once prototyped against the real
    "Spirit - Soul - Meatsuit.jpg" via tools/probe_google_vision.py, it
    visibly grouped the exact dense areas pipeline.images.ocr.
    merge_lines_into_paragraphs()'s geometric heuristic still struggled
    with (58 paragraphs recognized, average confidence 0.96 - see
    Backlog.md for the full comparison, including PaddleOcrEngine below).

    One OcrTextRegion is built per Vision PARAGRAPH (not per line, not per
    block - a block can itself hold several unrelated paragraphs, e.g. a
    whole sidebar card read as one block). `line_height` is the AVERAGE
    height of the paragraph's own words' bounding boxes - see
    _vision_paragraph_to_region()'s docstring.

    Known, deliberately unaddressed gap (documented rather than silently
    ignored, same policy as this module's other real-image-calibrated
    heuristics): a word Vision's own OCR broke across a line with a
    hyphen is still joined with a plain space, not de-hyphenated - no
    real example of this in the one real image this was built against,
    left for whenever one actually surfaces.
    """

    returns_paragraph_regions = True

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        if not google_vision_available():
            raise OcrError(
                "Kein Google-API-Key konfiguriert. In den Einstellungen "
                "hinterlegen oder eine andere OCR-Engine waehlen."
            )
        try:
            import requests
        except ImportError as exc:
            raise OcrError(f"OCR-Abhaengigkeit fehlt: {exc}.") from exc

        from pipeline.credentials import get_google_translate_api_key

        api_key = get_google_translate_api_key()
        with open(image_path, "rb") as handle:
            image_bytes = handle.read()

        body = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    **({"imageContext": {"languageHints": [language]}} if language else {}),
                }
            ]
        }
        try:
            response = requests.post(_VISION_API_URL, params={"key": api_key}, json=body, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OcrError(f"Vision-API-Aufruf fehlgeschlagen: {_extract_vision_error(exc)}") from exc

        result = (response.json().get("responses") or [{}])[0]
        if "error" in result:
            error = result["error"]
            raise OcrError(f"Vision-API meldete einen Fehler: {error.get('message', error)}")

        pages = (result.get("fullTextAnnotation") or {}).get("pages") or []
        if not pages:
            return []

        regions: list[OcrTextRegion] = []
        for block in pages[0].get("blocks") or []:
            for paragraph in block.get("paragraphs") or []:
                region = _vision_paragraph_to_region(paragraph)
                if region is not None:
                    regions.append(region)
        return regions


# _PADDLE_TRANSLATABLE_LABELS - PP-StructureV3's own documented category
# list is far longer than this (table, chart, formula, image, header,
# aside_text, reference, algorithm, ...) - only these, CONFIRMED on
# real images this was built against, to actually be plain translatable
# prose, are whitelisted here. Everything else is deliberately skipped
# rather than guessed at - same real-data-conservative policy as this
# module's other calibrated constants; extend this set only once a real
# image with one of those other categories confirms it should be
# translated as plain text too.
#
# 24.08.2026: "image" was ADDED, then REVERTED the same day after a
# real regression. Michael's QA-Bericht "(12)" ("Einmal in der Mitte
# ganz links, da ist ein kompletter Teil gar nicht übersetzt") traced
# to the "Thoughts/Emotions/.../recorded as PATTERNS" list being
# classified "image" (presumably the ledger/sphere graphic sharing the
# block) despite genuinely containing OCR'd text - so "image" was
# added here to translate it. That DID work label-wise, but the real
# QA-Bericht "(13)" run Michael tried it against came back worse than
# "(12)", not better ("Version 13 ist schlechter als Version 12"):
# _paddle_block_to_region() joins EVERY OCR line matched inside a
# block into ONE paragraph and renders it as ONE text blob at the
# block's bbox - fine for a real paragraph, but this particular block
# is not prose: it is 9 short, independent labels ("Thoughts",
# "Emotions", "Choices", ... "PATTERNS") scattered around a circular
# graphic. Joined and translated as one string, they became one
# garbled blob ("WO Gedanken Emotionen Entscheidungen BUCH GEDANKEN
# TRAUMA Karma Erfahrungen ...aufgezeichnet als MUSTER") rendered on
# top of the neighbouring "WHERE EXPERIENCES..." banner block (both
# blocks start at the same y=457) - confirmed from Michael's actual
# screenshot of the "(13)" output. Leaving the block in English
# (the pre-fix behaviour) was more readable than this. Reverted back
# to excluding "image" until there is a real per-LINE rendering path
# for this kind of block (each of the 9 labels drawn at its OWN
# original position, not joined into one paragraph) - see Backlog.md,
# 24.08.2026, for the fuller writeup and the region-count arithmetic
# that confirmed this diagnosis (v12's 42 regions included the
# chalice-icon "Y" as its own bogus footer region; v13's 42 = that
# region correctly dropped by the filter below, minus one, plus this
# now-reverted "image" region, plus one - net unchanged, which is
# exactly why the total looked identical in both QA reports despite
# two real, opposite-direction changes underneath).
_PADDLE_TRANSLATABLE_LABELS = frozenset({"text", "paragraph_title", "doc_title", "footer"})

# 26.08.2026 - the "richtiger Fix" the 24.08.2026 writeup above pointed
# to but didn't build yet: for a block with one of THESE labels (not in
# _PADDLE_TRANSLATABLE_LABELS above, so still never merged into one
# paragraph and translated as a blob), _paddle_block_to_line_regions()
# additionally emits each of its matched OCR lines as its OWN small,
# independently translatable region - real user report, Backlog.md
# 26.08.2026: "Wenn das als Bild gesehen wird, sollte das Bild doch auch
# extrahiert und übersetzbar sein." The block itself is STILL also kept
# (translatable=False, see OcrTextRegion.translatable's docstring) as a
# full-bbox collision obstacle in addition to the per-line regions - so
# a neighbouring region still can't grow sideways into the empty visual
# gaps BETWEEN the scattered labels (the failure mode the 24.08.2026
# revert-of-the-revert fixed), while the labels themselves now get
# translated in place at their own small boxes instead of staying
# permanently in English. Only "image" is listed - a genuinely
# graphic-only "image" block (no OCR line matches at all) still produces
# zero line regions, same as before this existed.
_PADDLE_SCATTERED_TEXT_LABELS = frozenset({"image"})

# 24.08.2026: two of PP-StructureV3's own per-line OCR results turned
# out to be small decorative icons misread as a short, spurious text
# token rather than a bug on our side - found via the real result JSON
# for "Spirit - Soul - Meatsuit.jpg", Michael's QA-Bericht "(12)": "Das
# Kelch Symbol zwischen den beiden Text boxen wird als 'UND'
# interpretiert."
#   - the chalice icon between the two footer boxes: its OWN separate
#     "footer"-labeled block (bbox roughly 32x30px, clearly icon-
#     sized, not a text line), OCR'd as the single letter "Y"
#     (confidence 0.8409) - "footer" was ALWAYS in
#     _PADDLE_TRANSLATABLE_LABELS, so this became its own real,
#     bogus, translated region even before the "image" experiment
#     above. The translation step apparently read the stray "Y" in
#     its sentence context as the Spanish word for "and" and rendered
#     "UND".
#   - a person icon in the "KEY TRUTH" box (the "Meatsuit/Body/
#     Identity" row's icon): OCR'd as the Chinese character "穴"
#     (confidence 0.2849 - the LOWEST of all 104 real OCR lines on
#     that image). This one's block was labeled "image" and so was
#     already excluded by the whitelist above both before and after
#     today's revert - this filter is what would have kept it safe
#     had "image" stayed whitelisted, and still protects it (and any
#     other icon caught inside a normally-translatable block) now
#     that "image" is excluded again.
# Both are short (1 character) AND clearly below the confidence of any
# real text line on that image (the lowest genuine text line scored
# 0.9111) - filtered out by combining a max-length and a min-score
# check so real short text (e.g. "OR", confidence 0.9817) is left
# alone. Applied in _paddle_ocr_lines() so it protects every
# translatable block, not just the two found here. Unlike the "image"
# experiment above, real-world testing (QA-Bericht "(13)") did not
# turn up any downside from this filter - keeping it.
_PADDLE_STRAY_GLYPH_MAX_CHARS = 2
_PADDLE_STRAY_GLYPH_MIN_SCORE = 0.90


def paddleocr_available() -> bool:
    """Whether the (optional, NOT in requirements-ocr.txt - see
    requirements-paddleocr.txt) paddleocr package is importable right now
    - mirrors tesseract_available()'s cheap PATH check, but for a Python
    package rather than a binary. Uses importlib.util.find_spec() rather
    than actually importing paddleocr - that import alone pulls in the
    full PaddlePaddle framework and is slow enough to notice, not
    something a UI dropdown's availability check should pay for on every
    repaint.
    """
    import importlib.util

    return importlib.util.find_spec("paddleocr") is not None


# parsing_res_list entries expose the SAME data under two different
# names depending on shape (see _paddle_field()'s docstring): the JSON/
# save_to_json() convention this engine was originally built against
# ("block_label"/"block_bbox"/"block_content" - keys used below and in
# every existing tests/test_image_ocr.py dict fixture) versus the real
# LayoutBlock object's own short attribute names, confirmed 23.08.2026
# via tools/probe_paddleocr_shape.py's real output against Michael's
# machine ("Spirit - Soul - Meatsuit.jpg"):
#   vars(parsing_res_list[0]) included
#   {'label': 'doc_title', 'bbox': [138, 10, 909, 86],
#    'content': 'SPIRIT·SOUL·MEATSUIT ...', ...}
# i.e. "label"/"bbox"/"content" - NOT "block_label"/"block_bbox"/
# "block_content". `getattr(block, "block_label", None)` therefore
# silently returned None for every real block (no exception - "block
# has no attribute block_label" only raises for an attribute lookup
# without a default), so EVERY block failed the `label in
# _PADDLE_TRANSLATABLE_LABELS` check and got skipped: 0 regions, no
# error (Michael's QA-Bericht "(11)": "Erkannte Textregionen: 0").
# There is no real "block_id" attribute at all (the closest live
# equivalent is `index`/`order_index`) - dropped below since
# _paddle_block_to_region() never read it anyway.
_PADDLE_BLOCK_FIELD_ALIASES = {
    "block_label": "label",
    "block_bbox": "bbox",
    "block_content": "content",
}


def _paddle_field(obj, key: str, default=None):
    """Read `key` (one of the "block_*" names above) from `obj`,
    whichever of TWO different shapes PaddleX hands a `parsing_res_list`
    entry to us in: a plain dict using the "block_*" key names (every
    fixture in tests/test_image_ocr.py, and what a round-trip through
    tools/probe_paddleocr.py's `save_to_json()` produces), or the real
    `LayoutBlock` object exposing the same data as plain attributes
    under its OWN, shorter names (`_PADDLE_BLOCK_FIELD_ALIASES` above) -
    what `parsing_res_list`'s entries actually are on the real, live
    `pipeline.predict()` result. `result` and `overall_ocr_res`
    themselves DO support `.get()` even on the live object (confirmed
    both times this was investigated); only `parsing_res_list`'s
    individual block entries have this dict-vs-attribute AND
    key-name-vs-attribute-name difference."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, _PADDLE_BLOCK_FIELD_ALIASES.get(key, key), default)


def _paddle_ocr_lines(overall_ocr_res: dict) -> list[tuple[tuple[float, float, float, float], str, float]]:
    """The (box, text, score) triples from PP-StructureV3's raw per-line
    OCR pass (`overall_ocr_res` - see PaddleOcrEngine's docstring for why
    THIS, not `parsing_res_list`'s own block_content, is the text source
    used here). `box` is (x0, y0, x1, y1) float pixel coordinates,
    `rec_boxes`'s own convention already.

    23.08.2026: `rec_boxes`/`rec_scores` come back from the real
    PaddleOCR/PaddleX pipeline as numpy arrays, not plain Python lists
    (Michael's real run: "ValueError: The truth value of an array with
    more than one element is ambiguous. Use a.any() or a.all()"). The
    fake fixtures in tests/test_image_ocr.py used plain lists, so this
    was missed there. `x or []` evaluates `bool(x)` when `x` is
    falsy-or-truthy-checked - for a numpy array with more than one
    element that raises instead of returning True/False, so the
    `or []` fallback (meant only for a missing/None key) has to be
    written as an explicit `is None` check instead."""
    boxes = overall_ocr_res.get("rec_boxes")
    boxes = [] if boxes is None else boxes
    texts = overall_ocr_res.get("rec_texts")
    texts = [] if texts is None else texts
    scores = overall_ocr_res.get("rec_scores")
    scores = [] if scores is None else scores

    # 24.08.2026: drop stray-icon-glyph misreads (see
    # _PADDLE_STRAY_GLYPH_MAX_CHARS's docstring above) before any block
    # matching happens, so this protects every translatable block
    # uniformly rather than each caller having to remember to check.
    lines = []
    for box, text, score in zip(boxes, texts, scores):
        if len(text.strip()) <= _PADDLE_STRAY_GLYPH_MAX_CHARS and score < _PADDLE_STRAY_GLYPH_MIN_SCORE:
            continue
        lines.append((box, text, score))
    return lines


def _match_block_lines(
    block_box: tuple[float, float, float, float],
    ocr_lines: list[tuple[tuple[float, float, float, float], str, float]],
) -> list[int]:
    """Indices into `ocr_lines` of every line whose box CENTER falls
    inside `block_box` - the geometric matching step shared by
    _paddle_block_to_region() (joins them into one paragraph region) and
    _paddle_block_to_line_regions() (26.08.2026, keeps them as separate
    small regions - see that function's docstring). Factored out so both
    can never disagree about which lines belong to a block.

    Returns INDICES (26.08.2026, was the matched `(box, text, score)`
    tuples themselves until then) rather than the tuples: a caller that
    needs to recognize "this exact line" across multiple blocks (see
    `claimed_line_indices` below) can't reliably do that via identity or
    equality on a tuple rebuilt from unpacked-and-repacked values - the
    index into the one shared `ocr_lines` list is the only stable
    handle."""
    bx0, by0, bx1, by1 = block_box
    matched: list[int] = []
    for index, (box, text, score) in enumerate(ocr_lines):
        lx0, ly0, lx1, ly1 = box
        center_x, center_y = (lx0 + lx1) / 2, (ly0 + ly1) / 2
        if bx0 <= center_x <= bx1 and by0 <= center_y <= by1:
            matched.append(index)
    return matched


def _paddle_block_to_region(
    block: dict, ocr_lines: list[tuple[tuple[float, float, float, float], str, float]]
) -> OcrTextRegion | None:
    """One OcrTextRegion for a single translatable parsing_res_list
    `block`, built from whichever `ocr_lines` fall geometrically inside
    it (a line's box CENTER inside the block's box - see
    PaddleOcrEngine's docstring) - None if none do (the layout and OCR
    passes disagreed about where text is; skipped rather than translating
    a block with no text) or if `block` itself has no usable bbox."""
    block_box = _paddle_field(block, "block_bbox")
    # same numpy-truthiness pitfall as _paddle_ocr_lines() above:
    # block_bbox is a numpy array on the real pipeline, so `not block_box`
    # raises for it instead of testing "is it missing".
    if block_box is None or len(block_box) != 4:
        return None
    bx0, by0, bx1, by1 = block_box

    matched = [ocr_lines[i] for i in _match_block_lines(block_box, ocr_lines)]
    if not matched:
        return None

    matched.sort(key=lambda item: (item[0][1], item[0][0]))  # top-to-bottom, then left-to-right
    text = " ".join(item[1] for item in matched if item[1])
    if not text.strip():
        return None
    scores = [item[2] for item in matched]
    confidence = (sum(scores) / len(scores)) * 100
    line_height = round(sum(item[0][3] - item[0][1] for item in matched) / len(matched))
    return OcrTextRegion(
        text=text,
        x=round(bx0), y=round(by0), width=round(bx1 - bx0), height=round(by1 - by0),
        confidence=confidence, line_height=line_height,
    )


def _paddle_block_to_line_regions(
    block: dict,
    ocr_lines: list[tuple[tuple[float, float, float, float], str, float]],
    claimed_line_indices: set[int],
) -> list[OcrTextRegion]:
    """26.08.2026 - the "richtiger Fix" _PADDLE_SCATTERED_TEXT_LABELS's
    docstring points to: one SMALL, independently translatable
    OcrTextRegion per matched OCR line, each at its OWN original
    position - instead of _paddle_block_to_region()'s single merged
    paragraph region for the same lines.

    Only called for a block whose label is in
    _PADDLE_SCATTERED_TEXT_LABELS (currently just "image") - i.e. a
    layout block PP-StructureV3 itself did NOT classify as prose, so
    joining its lines into one paragraph (like a real "text" block)
    is exactly the wrong shape for it (see Backlog.md 24.08.2026's full
    "Version 13 ist schlechter als Version 12" writeup: nine short,
    scattered icon labels joined into one string and drawn as one blob
    over a neighbouring block was less readable than the untranslated
    original). Returning each line as its own tiny region lets every
    normal downstream mechanism - translation, per-region font sizing
    (estimated_font_size() reads a region's own line_height), and
    inpainting's collision avoidance (_vertical_room_below()/
    _horizontal_room() treat every OcrTextRegion as a potential
    neighbour, translated or not) - handle these exactly like any other
    short text line anywhere else on the page, with no special-casing
    needed beyond this function existing.

    `claimed_line_indices` (26.08.2026, indices into `ocr_lines` already
    matched into a genuinely translatable block - built by recognize()
    in a pass over EVERY block before this one runs) excludes a line
    already spoken for elsewhere. Found via the real result JSON for
    "Spirit - Soul - Meatsuit.jpg": this exact "image" block's bbox
    [25,457,394,718] slightly overlaps the NEIGHBOURING
    "WHEREEXPERIENCES,PATTERNS&DISTORTIONSLIVE" banner's own separate
    `paragraph_title` block bbox ([333,457,733,476]) at its top-right
    corner - without this exclusion, the banner's own "WHERE" OCR line
    would ALSO match here (bounding-box-center containment doesn't know
    a line "belongs" to only one block) and get translated and drawn a
    SECOND time, on top of the banner's own, already-correct
    translation of the same text (confirmed empirically: without this
    exclusion, a second, garbled "WHEREEXPERIENCES,PATTERNS&
    DISTORTIONSLIVE WHERE" region appeared at x=333,y=457, right where
    the banner already draws itself). Harmless for the merged
    _paddle_block_to_region() obstacle above (its `.text` is never
    rendered, only its bbox matters) - not harmless once a line becomes
    its own independently drawn region.

    Returns [] on no bbox / no matched lines, same as
    _paddle_block_to_region()."""
    block_box = _paddle_field(block, "block_bbox")
    if block_box is None or len(block_box) != 4:
        return []

    regions = []
    for index in _match_block_lines(block_box, ocr_lines):
        if index in claimed_line_indices:
            continue
        box, text, score = ocr_lines[index]
        if not text.strip():
            continue
        lx0, ly0, lx1, ly1 = box
        height = round(ly1 - ly0)
        regions.append(
            OcrTextRegion(
                text=text,
                x=round(lx0), y=round(ly0), width=round(lx1 - lx0), height=height,
                confidence=score * 100, line_height=height,
            )
        )
    return regions


class PaddleOcrEngine:
    """OcrEngine backed by PaddleOCR's PP-StructureV3 pipeline (local,
    Apache-2.0 license, no cloud dependency - see
    requirements-paddleocr.txt).

    returns_paragraph_regions = True (see OcrEngine's docstring): like
    GoogleVisionOcrEngine, PP-StructureV3's own trained layout model
    groups text into blocks/paragraphs directly - added and calibrated
    the same day and against the same real image (23.08.2026,
    "Spirit - Soul - Meatsuit.jpg", tools/probe_paddleocr.py: 58 layout
    blocks recognized).

    Two DIFFERENT parts of one predict() result are combined here, not
    just `parsing_res_list` alone: that list's own `block_content` field
    turned out (found by inspecting the real image's actual result JSON)
    to concatenate every word in a block WITHOUT spaces
    ("HOWTHECHALICERESTORESWHATISETERNALLYPURE") - fine for
    PP-StructureV3's own intended use (feeding a layout-aware document-to-
    markdown/HTML converter that re-flows text itself), but unusable
    as-is for translation, which would otherwise send that as one giant
    nonsense token to the provider. The pipeline's OTHER result,
    `overall_ocr_res`, is the underlying per-LINE OCR pass (properly
    spaced `rec_texts`, one per detected text line, with its own
    `rec_boxes`) that PP-StructureV3 runs before laying blocks out - this
    engine re-attaches those correctly-spaced OCR lines to each
    translatable layout block by simple bounding-box containment (see
    _paddle_block_to_region()), sorts the matched lines top-to-bottom,
    and joins THEM with spaces instead.

    Only blocks whose `block_label` is in _PADDLE_TRANSLATABLE_LABELS are
    considered - see that constant's docstring for why the rest (images,
    tables, ...) are excluded.

    `line_height` is the average height of the matched OCR lines' own
    boxes (each already a single-line measurement, same reasoning as
    GoogleVisionOcrEngine's word-height average, just at line instead of
    word granularity - overall_ocr_res has no word-level boxes unless
    return_word_box is explicitly requested, not done here).

    The PPStructureV3 pipeline object is expensive to build (loads
    several ML models) and is lazily created on the FIRST recognize()
    call, then reused for the lifetime of this PaddleOcrEngine instance
    (one instance per translate_image() run - see
    pipeline.registry.build_ocr_engine()) rather than rebuilt per call.
    """

    returns_paragraph_regions = True

    def __init__(self) -> None:
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is None:
            from paddleocr import PPStructureV3

            self._pipeline = PPStructureV3(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return self._pipeline

    def recognize(self, image_path: str, language: str | None = None) -> list[OcrTextRegion]:
        if not paddleocr_available():
            raise OcrError(
                "PaddleOCR ist nicht installiert. Siehe requirements-paddleocr.txt "
                "oder eine andere OCR-Engine waehlen."
            )
        try:
            pipeline = self._get_pipeline()
        except ImportError as exc:
            raise OcrError(f"OCR-Abhaengigkeit fehlt: {exc}.") from exc
        except Exception as exc:  # model download/build failure, unsupported hardware, ...
            raise OcrError(f"PaddleOCR-Initialisierung fehlgeschlagen: {exc}") from exc

        try:
            results = list(pipeline.predict(image_path))
        # Inference failure - e.g. Backlog.md's PaddlePaddle 3.3.x oneDNN/
        # PIR regression (worked around by pinning paddlepaddle==3.2.2) -
        # a run against an incompatible install still fails cleanly here
        # (OcrError, same as every other engine's own failure mode)
        # rather than crashing the whole job with a raw traceback.
        except Exception as exc:
            raise OcrError(f"PaddleOCR-Erkennung fehlgeschlagen: {exc}") from exc
        if not results:
            return []
        result = results[0]

        # 23.08.2026: this parsing step crashed with a raw, unwrapped
        # ValueError on Michael's real run (the numpy-truthiness bug fixed
        # above in _paddle_ocr_lines()/_paddle_block_to_region() - see
        # their docstrings). Wrapping it here too means any FUTURE
        # surprise in PaddleX's result shape fails as a clean OcrError,
        # same as the predict() call above, instead of a raw traceback.
        try:
            ocr_lines = _paddle_ocr_lines(result.get("overall_ocr_res") or {})
            blocks = result.get("parsing_res_list") or []

            # 26.08.2026 - a first pass over EVERY translatable block,
            # before any region is built: which ocr_lines indices a
            # normal, genuinely translatable block already claims (see
            # _paddle_block_to_line_regions()'s `claimed_line_indices`
            # docstring for the real overlap this guards against - a
            # scattered-label block's own bbox can slightly overlap a
            # neighbouring translatable block's bbox). Must run to
            # completion BEFORE the second pass below, since a block
            # that claims a line can appear AFTER the scattered-label
            # block in `blocks`' own order - PaddleX doesn't guarantee
            # any particular block ordering here.
            claimed_line_indices: set[int] = set()
            for block in blocks:
                if _paddle_field(block, "block_label") in _PADDLE_TRANSLATABLE_LABELS:
                    block_box = _paddle_field(block, "block_bbox")
                    if block_box is not None and len(block_box) == 4:
                        claimed_line_indices.update(_match_block_lines(block_box, ocr_lines))

            regions: list[OcrTextRegion] = []
            for block in blocks:
                region = _paddle_block_to_region(block, ocr_lines)
                if region is None:
                    continue
                label = _paddle_field(block, "block_label")
                # 24.08.2026: a label-excluded block that genuinely has
                # OCR'd text (see OcrTextRegion.translatable's
                # docstring) is still returned, marked untranslatable,
                # so it stays visible to translate_image.py's
                # obstacle_regions collision-avoidance instead of
                # disappearing from every collision check the way it
                # did before this field existed.
                if label not in _PADDLE_TRANSLATABLE_LABELS:
                    region = _dataclass_replace(region, translatable=False)
                    regions.append(region)
                    # 26.08.2026 - see _PADDLE_SCATTERED_TEXT_LABELS's
                    # docstring: additionally translate each of this
                    # block's own OCR lines individually, in place,
                    # instead of leaving the whole block untranslated.
                    if label in _PADDLE_SCATTERED_TEXT_LABELS:
                        regions.extend(
                            _paddle_block_to_line_regions(block, ocr_lines, claimed_line_indices)
                        )
                    continue
                regions.append(region)
        except Exception as exc:
            raise OcrError(f"PaddleOCR-Ergebnis konnte nicht verarbeitet werden: {exc}") from exc
        return regions


# Ratio (horizontal gap between two adjacent words / the taller of their
# two heights) beyond which two words Tesseract grouped into the SAME
# (block, par, line) are nonetheless split into two separate OcrTextRegion
# - added after a real user-reported infographic (RoadMap.md/Backlog.md,
# 21.08.2026) with a two-column layout (main content + a right-hand
# sidebar box): Tesseract's page segmentation doesn't understand the
# columns, so on several rows it read straight across the gap between
# them, gluing two logically unrelated fragments - e.g. a left-column
# ledger label and the right sidebar's heading, dozens to hundreds of
# pixels apart - into one (block, par, line) group with a single giant
# bounding box spanning both. Translated as one string, that produced
# garbled, contextless nonsense far worse than either fragment translated
# on its own (see translate_image()'s docstring on garbage in tends to
# stay garbage out); drawn back as one oversized box, it also overlapped
# whatever sat between the two original fragments - a DIFFERENT root
# cause than pipeline.images.translate_image.DEFAULT_MAX_HEIGHT_RATIO's
# icon-inflated-height case, addressed here at the source instead of
# downstream.
#
# 2.5 was picked by inspecting this one real image's actual word gaps:
# every genuine single-column line's largest internal word gap stayed
# under 2.2x that gap's own text height (normal word/punctuation spacing,
# even in a wide letter-spaced headline), while every column-merged
# line's SMALLEST such gap was 3.4x or more - a clean separation with
# margin on both sides, not a broadly validated cutoff (same caveat as
# DEFAULT_MIN_OCR_CONFIDENCE/DEFAULT_MAX_HEIGHT_RATIO in translate_image.py).
_MAX_WORD_GAP_RATIO = 2.5

# Characters that, as a WORD ON THEIR OWN (Tesseract gave it its own
# space-separated token, no letters/digits attached), are essentially
# never genuine prose content - they show up here almost exclusively when
# Tesseract mis-recognizes a graphic element (a bullet dot, a checkbox/
# tick icon, a decorative rule, a stray anti-aliasing fragment next to a
# heading) as if it were a text character. Found and calibrated
# (22.08.2026, Michael, real user infographic - "Ich habe es hier mit
# echter Hardware getestet... Hier das Original und unsere Ausgabe") by
# comparing every purely-symbolic OCR token in that real image against
# what was actually drawn there: e.g. a checkbox icon before "NATURALLY
# COLLAPSES / ENDS" came back as the token "©)" (94/35 confidence - HIGH
# confidence for a flatly WRONG reading, so confidence alone cannot catch
# this - see DEFAULT_MIN_OCR_CONFIDENCE's own docstring for the same
# lesson at the region level), a bullet-icon pair before "THE ESSENCE
# RETURNS." came back as two extra tokens "@" and "\_". Left uncaught,
# these got glued onto the front of an otherwise perfectly-readable
# sentence, sent to translation and rendered as visible garbage
# ("©) NATURALLY COLLAPSES" -> mistranslated/rendered with the stray
# symbol still attached).
#
# Deliberately a SMALL, conservative set - every character here was only
# added after being confirmed, in the same real image, to have no
# legitimate standalone (space-separated, no adjacent letters/digits in
# the same token) use. Characters that DO have a confirmed legitimate
# standalone use in that same real design are deliberately left OUT even
# though they also appear as OCR noise elsewhere in the wild: "+" (a real
# bullet-point glyph this design's own lists use throughout), "/" (real
# slashes inside phrases like "SPIRIT / ESSENCE / ORIGINAL IMPRINT"),
# "-"/"="/"&"/">"/"<"/"»" (all confirmed real design punctuation/arrows
# somewhere in that same image, e.g. "previous state > resolves
# accordingly"). Stripping those too would trade one kind of visible
# corruption for another (silently dropped real punctuation) on nothing
# more than a hunch - left alone until a real example justifies it,
# mirroring this module's other calibrated-on-one-real-image constants
# (_MAX_WORD_GAP_RATIO, DEFAULT_MIN_OCR_CONFIDENCE/DEFAULT_MAX_HEIGHT_RATIO
# in translate_image.py) rather than a broadly validated list.
#
# NOT a fix for a decorative character MIXED INTO a real word (e.g. "The
# @SSence was never corrupted." from that same real image, where "@" sits
# glued to otherwise-correct letters) - splitting a token apart mid-word
# without corrupting genuine content is a materially harder problem, left
# as a known, documented gap (see Backlog.md) rather than attempted here.
_DECORATIVE_SYMBOL_CHARS = frozenset("©®™~\\|*•§¶†‡°@()[]{}_‘’“”\".,")


def _is_decorative_symbol_token(text: str) -> bool:
    """True if `text` (a single Tesseract word token, already known
    non-blank) consists ENTIRELY of characters from
    _DECORATIVE_SYMBOL_CHARS - see that constant's docstring. A token
    with even one letter/digit/other character is never considered
    decorative here, however low its own confidence - that is
    DEFAULT_MIN_OCR_CONFIDENCE's job, not this function's."""
    return all(char in _DECORATIVE_SYMBOL_CHARS for char in text)


def _group_words_into_lines(data: dict) -> list[OcrTextRegion]:
    """pytesseract.image_to_data() (Output.DICT) returns ONE ROW PER WORD,
    each tagged with its (block_num, par_num, line_num) position in
    Tesseract's own hierarchical page/block/paragraph/line/word scan.
    Grouping consecutive words that share the same (block, par, line) key
    reconstructs a single reading-order text LINE per group - the same
    granularity PyMuPdfEngine's TextBlock lines represent for PDFs,
    rather than exposing one OcrTextRegion per single word (which would
    make e.g. inpainting box merging or QA display far noisier than
    necessary).

    Each group is further split wherever two adjacent words are further
    apart than _MAX_WORD_GAP_RATIO allows (see that constant's docstring)
    - Tesseract's (block, par, line) key alone is not a reliable "these
    words belong on one visual line" signal once a multi-column layout is
    involved, so a single key can still legitimately yield more than one
    OcrTextRegion here.

    Insertion order of the resulting dict already matches reading order:
    image_to_data() itself iterates block-by-block, then line-by-line
    within a block, so the FIRST time a given (block, par, line) key is
    seen is always in document reading order - no separate sort needed;
    a key's own gap-split sub-regions are emitted left-to-right.

    A token that is purely decorative (see _is_decorative_symbol_token())
    is dropped here, same as a blank token - it contributes to neither
    the region's text nor its bounding box/confidence. A (block, par,
    line) group left with ZERO surviving words this way (e.g. the real
    "© *" case _DECORATIVE_SYMBOL_CHARS was calibrated against - both
    tokens purely decorative) simply never becomes a region at all,
    rather than one region whose entire text is decorative noise.
    """
    lines: dict[tuple[int, int, int], list[int]] = {}
    word_count = len(data["text"])
    for i in range(word_count):
        text = data["text"][i]
        if not text or not text.strip() or _is_decorative_symbol_token(text):
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(i)

    regions: list[OcrTextRegion] = []
    for indices in lines.values():
        regions.extend(_split_by_horizontal_gap(data, indices))
    return regions


def _split_by_horizontal_gap(data: dict, indices: list[int]) -> list[OcrTextRegion]:
    """Split one Tesseract (block, par, line) word-index group into one or
    more left-to-right OcrTextRegion clusters, breaking wherever the
    horizontal gap between two adjacent words exceeds _MAX_WORD_GAP_RATIO
    times the taller of the two words' heights (see that constant's
    docstring). A group with no such gap returns exactly one region -
    identical to _group_words_into_lines()'s pre-split behaviour."""
    ordered = sorted(indices, key=lambda i: data["left"][i])
    clusters: list[list[int]] = [[ordered[0]]]
    for prev_index, index in zip(ordered, ordered[1:]):
        prev_right = data["left"][prev_index] + data["width"][prev_index]
        gap = data["left"][index] - prev_right
        local_height = max(data["height"][prev_index], data["height"][index], 1)
        if gap > _MAX_WORD_GAP_RATIO * local_height:
            clusters.append([])
        clusters[-1].append(index)
    return [_region_from_word_indices(data, cluster) for cluster in clusters]


def _region_from_word_indices(data: dict, indices: list[int]) -> OcrTextRegion:
    """Build one OcrTextRegion from a cluster of word indices already
    established to belong together (a whole gap-split group, or a group
    that never needed splitting) - the shared bounding-box/confidence
    computation _split_by_horizontal_gap() calls once per cluster."""
    words = [data["text"][i] for i in indices]
    x0 = min(data["left"][i] for i in indices)
    y0 = min(data["top"][i] for i in indices)
    x1 = max(data["left"][i] + data["width"][i] for i in indices)
    y1 = max(data["top"][i] + data["height"][i] for i in indices)
    # Tesseract reports -1 confidence for non-word rows; none should
    # remain after _group_words_into_lines()'s text.strip() filter, but
    # guard anyway rather than let a stray -1 drag the average down.
    confidences = [float(data["conf"][i]) for i in indices if float(data["conf"][i]) >= 0]
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return OcrTextRegion(
        text=" ".join(words), x=x0, y=y0, width=x1 - x0, height=y1 - y0,
        confidence=confidence,
    )


# merge_lines_into_paragraphs() (22.08.2026) - real user, after the
# obstacle_regions collision-avoidance fix (same date, see
# InpaintingBackend.apply()'s docstring) was verified against the SAME
# real infographic ("Spirit - Soul - Meatsuit.jpg") and turned out NOT to
# meaningfully improve it: "Ja, bitte [den] naechsten Punkt angehen."
# Diagnosis (instrumenting a real translate_image() run against that
# image): _vertical_room_below() only ever finds the NEXT region below in
# the same column as a region's growth ceiling - but pipeline.images.ocr
# recognizes text at TESSERACT-LINE granularity (one OcrTextRegion per
# physical line), so a normal multi-line sentence/bullet ("Operates
# outside of time" / "and sequence." as two physical lines of ONE
# sentence) becomes TWO independently-translated-and-redrawn regions,
# each only a few original single-line-spacing pixels apart (4-13px in
# the real image) - nowhere near enough room for a translated (usually
# LONGER) line to wrap into, let alone for both halves of the sentence to
# grow independently without colliding with each other. 48 of 82
# translated regions in that real run needed more room than
# _vertical_room_below() could give them - confirmed the dominant real
# cause of the still-visible overlaps, not the skipped/failed-region gap
# obstacle_regions had already closed.
#
# The fix: before translation, merge consecutive ORIGINAL lines that are
# almost certainly the same wrapped sentence/bullet - same column
# (horizontal overlap), a SMALL vertical gap relative to line height
# (single-line-spacing, not a new paragraph/bullet's larger gap), and a
# SIMILAR line height (same font size - a heading immediately followed by
# a smaller body line often also has a small absolute gap, but must never
# be merged into one translation unit; the real image's own top eyebrow
# label + headline, and a sidebar's own heading + first bullet, were both
# confirmed false-merges before this check was added) - into ONE
# translation+layout unit, translated as a single (better-context, too)
# provider call and laid out as one word-wrapped block against the
# UNION of the merged lines' bounding boxes.
#
# _PARAGRAPH_GAP_RATIO/_PARAGRAPH_HEIGHT_RATIO_MIN were calibrated
# directly against that real image's actual OCR output (only the
# regions that pass DEFAULT_MIN_OCR_CONFIDENCE - see
# pipeline.images.translate_image's caller, which filters BEFORE calling
# this function - low-confidence OCR noise sitting geometrically close
# to real text produced nonsense merges when tried unfiltered, e.g. a
# real sentence merged with an adjacent misread garbage fragment):
# 0.6/0.6 produced 18 clean paragraph merges out of 82 real regions with
# ZERO cases, on manual review of every single merge, of two genuinely
# unrelated pieces of content ending up joined - not a broadly validated
# cutoff, same caveat as this module's other real-image-calibrated
# constants (_MAX_WORD_GAP_RATIO, DEFAULT_MIN_OCR_CONFIDENCE/
# DEFAULT_MAX_HEIGHT_RATIO in translate_image.py).
_PARAGRAPH_GAP_RATIO = 0.6
_PARAGRAPH_HEIGHT_RATIO_MIN = 0.6


def _nearest_region_below_same_column(
    region: OcrTextRegion, candidates: list[OcrTextRegion]
) -> tuple[OcrTextRegion | None, float | None]:
    """The candidate whose top sits closest below `region`'s bottom,
    among those overlapping `region` horizontally (same column) AND
    within _PARAGRAPH_HEIGHT_RATIO_MIN of its own height (same font
    size) - (None, None) if no such candidate exists. Deliberately
    scans ALL candidates rather than just `region`'s neighbour in
    whatever list order they arrived in: a real multi-column layout's
    OWN natural reading order can interleave two columns' lines (Block A
    line 1, Block B line 1, Block A line 2, ... - confirmed in the real
    image this was calibrated against, see merge_lines_into_paragraphs()'s
    docstring), so list-adjacency is not a reliable stand-in for visual
    adjacency here."""
    region_bottom = region.y + region.height
    best: OcrTextRegion | None = None
    best_gap: float | None = None
    for other in candidates:
        if other is region:
            continue
        if other.x + other.width <= region.x or other.x >= region.x + region.width:
            continue  # no horizontal overlap - a different column
        if other.y < region_bottom:
            continue  # not actually below (overlaps or sits above)
        smaller_height, larger_height = sorted([region.height, other.height])
        if larger_height == 0 or smaller_height / larger_height < _PARAGRAPH_HEIGHT_RATIO_MIN:
            continue  # too different a font size to be the same paragraph
        gap = other.y - region_bottom
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best = other
    return best, best_gap


def merge_lines_into_paragraphs(regions: list[OcrTextRegion]) -> list[list[OcrTextRegion]]:
    """Group `regions` (already filtered to whatever the caller considers
    eligible for translation - see pipeline.images.translate_image, which
    filters by min_confidence/max_height_ratio BEFORE calling this) into
    paragraph-level chains: consecutive wrapped lines of the same
    sentence/bullet, in reading order. A region with no qualifying
    continuation becomes its own single-element chain - every input
    region appears in EXACTLY one output chain, in the same relative
    order it appeared in `regions` (a chain's position is its FIRST
    member's position; see _nearest_region_below_same_column()'s
    docstring for why a chain's LATER members don't need to be
    list-adjacent to its first).

    Each region is linked to at most ONE predecessor: if two different
    regions would both consider the same third region their nearest
    qualifying continuation (possible in a dense layout, though not
    observed in the real image this was calibrated against), the
    EARLIER one (in `regions` order) claims it; the later one simply
    gets no continuation there and starts/ends its own chain instead -
    deterministic, and never a region ending up merged into two chains
    at once.
    """
    next_of: dict[int, OcrTextRegion] = {}
    claimed: set[int] = set()
    for region in regions:
        candidate, gap = _nearest_region_below_same_column(region, regions)
        if candidate is None or gap is None:
            continue
        if gap >= _PARAGRAPH_GAP_RATIO * region.height:
            continue
        if id(candidate) in claimed:
            continue
        next_of[id(region)] = candidate
        claimed.add(id(candidate))

    chain_starts = [region for region in regions if id(region) not in claimed]
    chains: list[list[OcrTextRegion]] = []
    for start in chain_starts:
        chain = [start]
        current = start
        while id(current) in next_of:
            current = next_of[id(current)]
            chain.append(current)
        chains.append(chain)
    return chains


def merge_region_group(group: list[OcrTextRegion]) -> OcrTextRegion:
    """Build ONE OcrTextRegion representing `group` (a merge_lines_into_
    paragraphs() chain) as a single translation+layout unit: the UNION of
    every member's bounding box (needed so collision avoidance/word-wrap
    know the block's true full extent), `text` the members' original text
    joined with a single space (same joining convention
    _region_from_word_indices() already uses for words within one line),
    `confidence` the plain average (every member already individually
    passed the caller's min_confidence, so the average trivially does
    too), and `line_height` set to the members' own average height - see
    OcrTextRegion.line_height's docstring for why that, not the merged
    `height`, is what font-size estimation must use. A single-element
    group (the common case - most lines have no continuation) still goes
    through this unchanged, at the cost of one redundant pass - kept
    uniform rather than special-cased, since translate_image() calls this
    for every chain regardless of length.
    """
    x0 = min(r.x for r in group)
    y0 = min(r.y for r in group)
    x1 = max(r.x + r.width for r in group)
    y1 = max(r.y + r.height for r in group)
    confidence = sum(r.confidence for r in group) / len(group)
    line_height = round(sum(r.height for r in group) / len(group))
    return OcrTextRegion(
        text=" ".join(r.text for r in group),
        x=x0, y=y0, width=x1 - x0, height=y1 - y0,
        confidence=confidence,
        line_height=line_height,
    )
