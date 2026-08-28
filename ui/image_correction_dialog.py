"""Manual-correction table for a finished Bildübersetzung (RoadMap.md
Phase 3's "Korrektur-Möglichkeit ... analog zur PDF-Variante" item) -
built directly after ui/correction_dialog.py's PdfCorrectionDialog, on the
explicit reasoning that the correction pattern is needed everywhere
(images, and later PDF/Word/PPTX embedded image translation too), so it
should be built once, well, rather than reinvented per format.

Reuses pipeline.images.translate_image.build_corrected_replacements() (via
ui.image_job.run_image_correction_job()) - the same InpaintingBackend.apply()
machinery translate_image() itself uses, just re-run against a fresh copy
of the pristine source image with the (edited) translations already known,
no OCR/provider/network call involved.

Deliberately SIMPLER than PdfCorrectionDialog: plain-text editing only (a
QPlainTextEdit, no rich-text toolbar/shortcuts) - raster-drawn image text
via PIL's ImageDraw.text() has no bold/italic/underline concept the way a
PDF's rich-text box does, so there is no INLINE (per-character) formatting
to preserve or toggle here. Also no page column - a single image has no
page concept, so the table is just Original/Übersetzung.

Font size/bold/alignment (28.08.2026, same day as pipeline.images.
inpainting.TextReplacement's render_font_size/render_bold/render_centered
fields - real user report, Backlog.md 28.08.2026: "Wenn ich etwas
korrigiere, muss es auch genauso korrigiert werden wie ich es im Viewer
sehe.") ARE now editable here, per box - self.font_size_spin/bold_button/
centered_button below, one set shared by whichever row is currently active
(loaded into self.editor), exactly like the editor itself. These are WHOLE-
BOX choices, not per-character rich text (still no bold-just-one-word), so
they don't contradict the paragraph above - "no formatting" always meant
"no inline formatting", never "the whole box's size/weight/alignment can't
be changed at all". Before this date, _ResizableRegionItem.paint()'s live
preview drew every box's translated-text preview unconditionally centered
(Qt.AlignmentFlag.AlignCenter, regardless of any per-box state, because
there was none) while the real renderer had no alignment concept at all -
so the preview not only couldn't be trusted for alignment, it actively
lied about it for every box. See _ResizableRegionItem.paint()'s own
updated docstring for the fix, and pipeline.images.translate_image.
build_corrected_replacements()'s edited_font_size/edited_bold/
edited_centered docstring for the tri-state ("untouched this round" vs.
"explicitly cleared back to auto" vs. "explicit new value") contract
_apply() below now feeds from self._edited_font_size/_edited_bold/
_edited_centered.

A user testing the OCR-driven box placement (see Backlog.md 18.08.2026's
three-layer fix in pipeline/images/ocr.py and pipeline/images/
inpainting.py) then asked, explicitly, whether the boxes themselves could
also be corrected by hand - even the best OCR/rendering heuristics can
still misplace or mis-size a box on a real, messy infographic layout, and
no automatic fix ever covers 100% of cases. That request is the
_ResizableRegionItem canvas below: a QGraphicsView showing the pristine
source image with one draggable/resizable rectangle per row, mirroring
each row's current OcrTextRegion geometry. Moving/resizing a box records
an (x, y, width, height) override in self._edited_geometry, index-aligned
with `replacements` exactly like self._row_text already is for edited
translations - both are threaded independently into
build_corrected_replacements()'s edited_texts/edited_geometry parameters
at _apply() time, so a user can fix a box's position, its text, both, or
neither, per row.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QGraphicsItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsView, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from pipeline.images.inpainting import TextReplacement, estimated_font_size
from pipeline.images.ocr import OcrTextRegion
from pipeline.images.translate_image import build_corrected_replacements
from ui.i18n import LanguageManager
from ui.image_job import ImageJobResult, run_image_correction_job

_ORIGINAL_COLUMN = 0
_TRANSLATION_COLUMN = 1

_HANDLE_SCREEN_PX = 10.0
"""Side length of the hit-test/visible square anchored at a box's
bottom-right corner, in VIEW (screen) pixels rather than scene (source-
image) pixels - dragging inside it resizes the box instead of moving it.
QGraphicsRectItem has no built-in resize handle; this is the smallest
hand-rolled version that covers "make the box bigger/smaller" without a
full 8-handle resize widget nobody asked for.

Fixed in view pixels, NOT scene pixels, on purpose: the canvas fits the
whole source image into the view (see _ImageCanvasView.resizeEvent()), so
a large infographic is often shown zoomed well below 100% - a handle sized
in scene units would shrink along with it and become unclickable. See
_view_scale()/_handle_rect() for the conversion.

Deliberately smaller than the original 14px, and (see _ResizableRegionItem.
paint()/hoverMoveEvent()/mousePressEvent()) only ever drawn/hit-tested on
the currently ACTIVE box, not every box at once - a real user reported the
handle square as "sehr gross" (too big) precisely because a small-text
infographic can have dozens of boxes, and a handle on every single one of
them cluttered the image far more than any one handle's own size. The
canvas's new Strg+Mausrad zoom (_ImageCanvasView.wheelEvent()) covers the
rest of that same complaint - the user can zoom in on a small box instead
of needing an oversized, always-visible handle to hit it reliably."""
_MIN_HANDLE_SCENE_SIZE = 3.0
"""Floor for the handle's size in scene units, applied after converting
_HANDLE_SCREEN_PX via the current view scale - keeps the handle usable
even at extreme zoom-in levels."""
_ZOOM_STEP = 1.25
"""Multiplicative step for one Strg+Mausrad notch or one +/- toolbar
click. 1.25 (25% per step) matches common image-editor conventions -
noticeable per click/notch without needing many of them to reach a useful
zoom level."""
_MIN_VIEW_SCALE = 0.2
_MAX_VIEW_SCALE = 16.0
"""Clamp for the view's absolute scale (transform().m11()) - stops the
image from either shrinking to an unusable sliver or zooming in so far
that a box's coordinates lose meaningful screen precision. 16x covers
"one screen pixel per fifth of a source-image pixel" for even a modest
infographic, which is already far more precision than manual box-editing
needs."""
_MIN_BOX_SIZE = 8
"""Floor for a resized box's width/height (scene units, i.e. source-image
pixels) - stops a careless drag from collapsing a box to zero/negative
size, which would make it invisible and unrecoverable without the reset
button."""
_MIN_PREVIEW_FONT_SIZE = 5.0
_MAX_PREVIEW_FONT_SIZE = 18.0
"""Only the FALLBACK now (27.08.2026, see _ResizableRegionItem's
`font_size_px` constructor param) - used only for a manually added box
(ImageCorrectionDialog._on_new_box_drawn(), no OCR region to estimate a
real font size from). Real user report, Backlog.md 27.08.2026 (WebViewer
round 3, then confirmed present here too): this preview used to compute
its OWN font size from half the box's height, hard-capped at 18pt with
no relation whatsoever to pipeline.images.inpainting.estimated_font_size()
(the SAME OCR-line-height-based estimate the real renderer and (since
26.08.2026) review_server.py's WebViewer both start from) - so a big
title (estimated ~48px in the real render) always looked capped-small
here, "der Font ist noch sehr schlecht". Every box built FROM a real
OcrTextRegion now passes its real estimate in instead."""
_INACTIVE_PEN_COLOR = QColor(220, 30, 30)
_ACTIVE_PEN_COLOR = QColor(30, 140, 230)
_FILL_COLOR = QColor(220, 30, 30, 40)

_MIN_FONT_SIZE_SPIN = 1
_MAX_FONT_SIZE_SPIN = 9999
"""Range for ImageCorrectionDialog.font_size_spin (28.08.2026). No hard
tie to pipeline.images.inpainting._MIN_FONT_SIZE/_MAX_FONT_SIZE (9/48) on
purpose - those bound the AUTO-ESTIMATE only; a deliberately human-chosen
render_font_size is passed straight through as _fit_text()'s `start_size`
and is free to ask for a much bigger headline than any auto-estimate would
ever guess (it can still shrink further from there if it doesn't fit the
box - see _fit_text()'s own docstring). This range is just wide enough to
never get in the way, not a claim about what looks good."""


class _ResizableRegionItem(QGraphicsRectItem):
    """One draggable/resizable box overlaid on the canvas image, one per
    TextReplacement/table row.

    The rect itself always stays anchored at local (0, 0); the box's
    on-canvas position lives entirely in the item's pos() instead. That
    split is what lets native Qt dragging (ItemIsMovable, handled by
    QGraphicsItem's own mouseMoveEvent) update pos() for a plain move,
    while this class's own mouseMoveEvent override updates rect() for a
    corner-handle resize - the two never fight over the same value.

    QGraphicsItem is not a QObject and cannot emit Qt signals (see the
    PySide6/Qt docs) - on_changed(row)/on_selected(row) are plain Python
    callables the dialog passes in and this class calls directly, instead
    of a signal/slot connection.
    """

    def __init__(
        self,
        row: int,
        x: float,
        y: float,
        width: float,
        height: float,
        text: str = "",
        on_changed=None,
        on_selected=None,
        font_size_px: float | None = None,
        font_size_override: int | None = None,
        bold: bool = False,
        centered: bool = False,
    ) -> None:
        super().__init__(0, 0, width, height)
        self.row = row
        self._text = text
        self._show_preview = True
        self._on_changed = on_changed
        self._on_selected = on_selected
        # 27.08.2026 - see _MAX_PREVIEW_FONT_SIZE's own updated docstring:
        # the real, OCR-line-height-based estimate for this region
        # (pipeline.images.inpainting.estimated_font_size(replacement.region))
        # when the caller has one, None for a manually added box that has
        # no underlying OcrTextRegion to estimate from - paint() falls back
        # to the old box-height heuristic only in that case.
        self._font_size_px = font_size_px
        # 28.08.2026 - the human-set overrides ImageCorrectionDialog now
        # tracks per row (self._row_font_size/_row_bold/_row_centered),
        # mirrored into this item by set_font_size_override()/set_bold()/
        # set_centered() every time that row's control changes AND on
        # construction/_load_row() so a box built from an already-corrected
        # replacement (render_box/render_font_size/... from an earlier
        # round, see the constructor loop in ImageCorrectionDialog.__init__)
        # starts out showing exactly that, not the plain auto-estimate.
        # `font_size_override` (None = no override, use `font_size_px`/the
        # box-height fallback below exactly like before this date) is
        # deliberately a SEPARATE field from `font_size_px` rather than
        # overwriting it - `font_size_px` stays the true OCR-derived
        # estimate so clearing the override (the "Automatisch" button) can
        # fall back to it without the dialog needing to re-supply it.
        self._font_size_override = font_size_override
        self._bold = bold
        self._centered = centered
        self._resizing = False
        self._resize_start_scene_pos: QRectF | None = None
        self._resize_start_rect: QRectF | None = None
        self._active = False
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.set_active(False)

    def set_text(self, text: str) -> None:
        """Update the live text PREVIEW drawn inside the box (see paint())
        - called on construction and again on every keystroke in the
        active row's editor (ImageCorrectionDialog._on_editor_text_changed()),
        so what the user sees on the canvas always matches what they just
        typed, not just the original machine translation. A real user
        reported dragging a box and seeing no text in it at all - this is
        the fix: previously nothing was ever drawn inside a box, only the
        colored outline."""
        if text == self._text:
            return
        self._text = text
        self.update()

    def set_show_preview(self, show: bool) -> None:
        """Toggle the translated-text overlay drawn inside this box (see
        paint()) - added after Michael reported (23.08.2026): "Bei der
        Korrektur sieht man leider den Text nicht deutlich, da ja die
        Übersetzung das Original überlagert." The box's semi-transparent
        FILL (_FILL_COLOR, alpha 40/255) already lets the pristine
        original mostly show through, but the translated PREVIEW TEXT
        itself is drawn fully opaque directly on top of it - exactly
        where the original text sits, since both share the same box -
        so the two visually collide, especially for a longer German
        translation. `show=False` skips the text draw entirely (outline
        + faint fill only), leaving the original underneath fully
        legible; called from every box at once via
        ImageCorrectionDialog._on_toggle_original_visible()."""
        if show == self._show_preview:
            return
        self._show_preview = show
        self.update()

    def set_font_size_override(self, size: int | None) -> None:
        """Update the live PREVIEW's font size (see paint()) - called from
        ImageCorrectionDialog._on_font_size_changed()/_reset_active_font_size()
        every time the active row's font-size spinbox changes or is reset
        to "Automatisch" (28.08.2026, see this class's constructor
        docstring). `None` (also this item's own construction default)
        means "no override" - paint() falls back to `font_size_px` (the
        real OCR estimate) or, lacking that, the old box-height guess,
        exactly the pre-28.08.2026 behaviour."""
        if size == self._font_size_override:
            return
        self._font_size_override = size
        self.update()

    def set_bold(self, bold: bool) -> None:
        """Update the live PREVIEW's font weight (see paint()) - called
        from ImageCorrectionDialog._on_bold_toggled() every time the
        active row's "Fett" button is toggled (28.08.2026)."""
        if bold == self._bold:
            return
        self._bold = bold
        self.update()

    def set_centered(self, centered: bool) -> None:
        """Update the live PREVIEW's horizontal alignment (see paint()) -
        called from ImageCorrectionDialog._on_centered_toggled() every
        time the active row's "Zentriert" button is toggled (28.08.2026).
        `False` (also this item's own construction default) draws left-
        aligned, matching what the real renderer has always done and what
        every box drew here too BEFORE this date, once this fix replaced
        paint()'s old unconditional Qt.AlignmentFlag.AlignCenter."""
        if centered == self._centered:
            return
        self._centered = centered
        self.update()

    def set_active(self, active: bool) -> None:
        """Visually mark this box as the one loaded in the editor below -
        called from ImageCorrectionDialog._load_row(), never from a mouse
        event, so it never itself triggers on_changed/on_selected.

        Also gates the resize handle (see _handle_rect() usage in paint()/
        hoverMoveEvent()/mousePressEvent()): only the active box ever draws
        or hit-tests one. A real user reported the handle square as "sehr
        gross" on a small-text infographic with many boxes - with every box
        drawing its own handle at once, that was true even after shrinking
        _HANDLE_SCREEN_PX, simply because there were so many of them
        cluttering the image. Restricting the handle to whichever single
        box is already selected/loaded in the editor removes that clutter
        without giving up resizing itself - it's still exactly the same
        select-then-drag-the-corner workflow as before.
        """
        self._active = active
        color = _ACTIVE_PEN_COLOR if active else _INACTIVE_PEN_COLOR
        pen = QPen(color, 3 if active else 2)
        self.setPen(pen)
        self.setBrush(QBrush(_FILL_COLOR))
        self.setZValue(1 if active else 0)
        self.update()

    def geometry(self) -> tuple[int, int, int, int]:
        """Current (x, y, width, height) in source-image pixel space -
        pos() (top-left, moved by dragging) combined with rect()'s own
        width/height (changed by resizing)."""
        pos = self.pos()
        rect = self.rect()
        return (round(pos.x()), round(pos.y()), round(rect.width()), round(rect.height()))

    def set_geometry(self, x: float, y: float, width: float, height: float) -> None:
        """Reprogram this box's position/size directly (used by the
        "Position/Größe zurücksetzen" button) - a plain setter, not a
        simulated drag, so it deliberately does NOT call on_changed()
        itself; the caller decides what to do with self._edited_geometry."""
        self.setPos(x, y)
        self.setRect(0, 0, width, height)

    def _view_scale(self) -> float:
        """Current horizontal scale factor of the first QGraphicsView
        showing this item's scene (1.0 - identity - if none is attached
        yet, e.g. before the dialog's canvas view exists). Used to convert
        _HANDLE_SCREEN_PX (a constant SCREEN size) into the right size in
        SCENE units for the current zoom level - see _HANDLE_SCREEN_PX's
        docstring for why a fixed scene-unit handle broke at any zoom
        level other than 1:1."""
        scene = self.scene()
        if scene is not None:
            views = scene.views()
            if views:
                scale = views[0].transform().m11()
                if scale > 0:
                    return scale
        return 1.0

    def _handle_rect(self) -> QRectF:
        rect = self.rect()
        size = _HANDLE_SCREEN_PX / self._view_scale()
        size = max(size, _MIN_HANDLE_SCENE_SIZE)
        size = max(2.0, min(size, rect.width(), rect.height()))
        return QRectF(rect.right() - size, rect.bottom() - size, size, size)

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        rect = self.rect()

        # A small filled square at the resize corner - purely cosmetic
        # (the actual hit-test always uses _handle_rect() directly, not
        # this drawing), but without SOME visible marker a user has no way
        # to know a resize handle exists at all, let alone where exactly.
        # Only drawn for the ACTIVE box - see set_active()'s docstring for
        # why every box showing one at once was reported as visual clutter.
        if self._active:
            painter.save()
            try:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self.pen().color()))
                painter.drawRect(self._handle_rect())
            finally:
                painter.restore()

        if not self._show_preview or not self._text or rect.width() < 6 or rect.height() < 6:
            return
        painter.save()
        try:
            painter.setClipRect(rect)
            font = painter.font()
            # 28.08.2026 - a human-set size override (self.
            # _font_size_override, see set_font_size_override()'s
            # docstring) now takes priority over both the real OCR
            # estimate and the box-height fallback below, exactly
            # mirroring pipeline.images.inpainting.TextReplacement.
            # render_font_size overriding the auto-estimate in the real
            # renderer (see that field's docstring) - the whole point
            # being that this preview and the real render start from the
            # SAME number. Below it, unchanged from 27.08.2026: start from
            # the REAL estimate (see _MAX_PREVIEW_FONT_SIZE's own updated
            # docstring) when this box has one; only a manually added box
            # (no OcrTextRegion behind it, and never explicitly sized by
            # hand either) falls back to the old box-height-derived guess.
            if self._font_size_override is not None:
                size = max(_MIN_PREVIEW_FONT_SIZE, float(self._font_size_override))
            elif self._font_size_px is not None:
                size = max(_MIN_PREVIEW_FONT_SIZE, self._font_size_px)
            else:
                size = max(_MIN_PREVIEW_FONT_SIZE, min(_MAX_PREVIEW_FONT_SIZE, rect.height() * 0.5))
            font.setBold(self._bold)
            # Simple shrink-to-fit, mirroring (loosely - this is a fast
            # canvas PREVIEW, not the actual PIL rendering) pipeline.images.
            # inpainting._fit_text()'s wrap-and-shrink idea: try
            # progressively smaller sizes until the word-wrapped block's
            # measured height fits inside the box. Runs even for an
            # explicit override - exactly like the real renderer's
            # start_size, a human-chosen size is a STARTING point, not a
            # promise to overflow the box rather than shrink (see
            # pipeline.images.inpainting._fit_text()'s own docstring).
            while size > _MIN_PREVIEW_FONT_SIZE:
                font.setPointSizeF(size)
                metrics = QFontMetricsF(font)
                needed = metrics.boundingRect(
                    QRectF(0, 0, rect.width(), 10_000), int(Qt.TextFlag.TextWordWrap), self._text
                )
                if needed.height() <= rect.height():
                    break
                size -= 1
            font.setPointSizeF(size)
            painter.setFont(font)
            painter.setPen(QPen(self.pen().color()))
            # 28.08.2026, real user report, Backlog.md 28.08.2026: "Wenn
            # ich etwas korrigiere, muss es auch genauso korrigiert werden
            # wie ich es im Viewer sehe." Before this date this was an
            # UNCONDITIONAL Qt.AlignmentFlag.AlignCenter, regardless of
            # this box's own state (there was none) and regardless of what
            # the real renderer did (nothing - it had no alignment concept
            # at all until pipeline.images.inpainting._draw_fitted_text()'s
            # `centered` parameter, same day) - every preview lied about
            # alignment, and the one hard-coded case it happened to render
            # correctly (centered) was itself never an available choice, it
            # was every box, always, whether the user wanted that or not.
            # AlignTop (new here too, not just the H-alignment half) rather
            # than AlignCenter's vertical centering - the real renderer has
            # always drawn each wrapped line starting at `region.y` and
            # stacking downward (pipeline.images.inpainting.
            # _draw_fitted_text(): `y = region.y`, then `y += line_height`
            # per line), never vertically centered within the box, so only
            # AlignTop matches it; AlignVCenter here would reintroduce the
            # exact same "preview shows something the render doesn't"
            # mismatch this whole fix exists to close, just on the other
            # axis.
            horizontal_flag = (
                Qt.AlignmentFlag.AlignHCenter if self._centered else Qt.AlignmentFlag.AlignLeft
            )
            painter.drawText(
                rect,
                int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignTop) | int(horizontal_flag),
                self._text,
            )
        finally:
            painter.restore()

    def hoverMoveEvent(self, event) -> None:
        cursor = (
            Qt.CursorShape.SizeFDiagCursor
            if self._active and self._handle_rect().contains(event.pos())
            else Qt.CursorShape.SizeAllCursor
        )
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._active and self._handle_rect().contains(event.pos()):
            self._resizing = True
            self._resize_start_scene_pos = event.scenePos()
            self._resize_start_rect = QRectF(self.rect())
            event.accept()
        else:
            super().mousePressEvent(event)
        if self._on_selected is not None:
            self._on_selected(self.row)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing:
            delta = event.scenePos() - self._resize_start_scene_pos
            new_width = max(_MIN_BOX_SIZE, self._resize_start_rect.width() + delta.x())
            new_height = max(_MIN_BOX_SIZE, self._resize_start_rect.height() + delta.y())
            self.setRect(0, 0, new_width, new_height)
        else:
            super().mouseMoveEvent(event)
        if self._on_changed is not None:
            self._on_changed(self.row)

    def mouseReleaseEvent(self, event) -> None:
        if self._resizing:
            self._resizing = False
        else:
            super().mouseReleaseEvent(event)


class _ImageCanvasView(QGraphicsView):
    """QGraphicsView that keeps the WHOLE source image fitted to the
    viewport (no manual scrolling needed to see boxes near the bottom of a
    tall infographic) and stays fitted across window/splitter resizes.

    fitInView() is only meaningful once the viewport actually HAS a size -
    calling it directly in ImageCorrectionDialog.__init__() would use
    whatever placeholder size the widget has before the layout/splitter
    has run, which is wrong. Doing it here, in resizeEvent(), means it
    naturally fires with the correct size on first show AND again on every
    later resize (e.g. the user dragging the splitter or maximizing the
    dialog) - not just once at construction time.

    Also owns "add mode" (RoadMap.md/Backlog.md 21.08.2026: a real user
    pointed out that text Tesseract never recognized at all has no box to
    correct, and asked for a way to add one by hand) - while enabled, a
    left-button drag anywhere on the canvas draws a NEW rectangle instead
    of being routed to whatever _ResizableRegionItem happens to sit under
    the cursor, so a user can draw a brand-new box even on top of/next to
    an existing one. set_add_mode(True) is a one-shot: it turns itself
    back off the moment a box is actually drawn (see on_box_drawn below),
    so the user doesn't have to remember to switch back to normal editing.
    """

    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)
        self._add_mode = False
        self._draw_origin = None
        self._draw_preview: QGraphicsRectItem | None = None
        self.on_box_drawn = None
        """Callback(x, y, width, height) - all in SCENE (source-image
        pixel) coordinates - invoked once, right after add mode turns
        itself back off, when the user finishes drawing a new box. Plain
        callable, not a Qt signal, mirroring _ResizableRegionItem's own
        on_changed/on_selected (see that class's docstring for why)."""
        self._manual_zoom = False
        """True once the user has zoomed by hand (Strg+Mausrad or the
        +/-/Fit toolbar buttons - see wheelEvent()/zoom_in()/zoom_out()/
        reset_zoom()). While set, resizeEvent() leaves the current zoom
        level alone instead of snapping back to "fit the whole image" -
        without this flag, dragging the splitter or resizing the dialog
        (e.g. maximizing it) would silently undo every zoom the user just
        made. reset_zoom() is the explicit way back to always-fit."""
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        scene = self.scene()
        if scene is not None and not scene.sceneRect().isEmpty() and not self._manual_zoom:
            self.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _zoom_by(self, factor: float) -> None:
        """Multiply the view's current scale by `factor`, clamped to
        [_MIN_VIEW_SCALE, _MAX_VIEW_SCALE] - shared by wheelEvent() and the
        +/- toolbar buttons (see ImageCorrectionDialog._on_zoom_in/out())."""
        current = self.transform().m11()
        target = current * factor
        if target < _MIN_VIEW_SCALE or target > _MAX_VIEW_SCALE:
            return
        self._manual_zoom = True
        self.scale(factor, factor)

    def zoom_in(self) -> None:
        self._zoom_by(_ZOOM_STEP)

    def zoom_out(self) -> None:
        self._zoom_by(1 / _ZOOM_STEP)

    def reset_zoom(self) -> None:
        """"Ansicht anpassen" - back to fitting the whole source image, and
        (crucially) re-enables auto-fit-on-resize until the user zooms
        again by hand."""
        self._manual_zoom = False
        scene = self.scene()
        if scene is not None and not scene.sceneRect().isEmpty():
            self.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        # Strg+Mausrad zooms (mirroring the common browser/image-editor
        # convention); a plain wheel notch is left to QGraphicsView's own
        # default handling, which scrolls/pans - a real user reported
        # having no way to get close enough to small text/boxes to correct
        # them precisely, and losing plain-scroll panning entirely (by
        # making EVERY wheel notch zoom) would have made a zoomed-in image
        # harder to navigate, not easier.
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        self._zoom_by(_ZOOM_STEP if delta > 0 else 1 / _ZOOM_STEP)
        event.accept()

    def set_add_mode(self, enabled: bool) -> None:
        self._add_mode = enabled
        if not enabled and self._draw_preview is not None:
            # Leaving add mode mid-drag (e.g. the toolbar button toggled
            # off by code, not by the user releasing the mouse) - drop the
            # half-drawn preview rather than leaving a stray item behind.
            scene = self.scene()
            if scene is not None:
                scene.removeItem(self._draw_preview)
            self._draw_preview = None
            self._draw_origin = None
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:
        if self._add_mode and event.button() == Qt.MouseButton.LeftButton:
            # event.position() (QPointF), not the deprecated event.pos()
            # (QPoint) - see this project's own fitz/PyMuPDF deprecation
            # cleanup (RoadMap.md/Backlog.md) for why deprecated Qt/PySide6
            # API is treated the same way here: fixed immediately, not left
            # for "still works for now".
            self._draw_origin = self.mapToScene(event.position().toPoint())
            self._draw_preview = QGraphicsRectItem(QRectF(self._draw_origin, self._draw_origin))
            self._draw_preview.setPen(QPen(_ACTIVE_PEN_COLOR, 2, Qt.PenStyle.DashLine))
            self.scene().addItem(self._draw_preview)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._add_mode and self._draw_preview is not None:
            current = self.mapToScene(event.position().toPoint())
            self._draw_preview.setRect(QRectF(self._draw_origin, current).normalized())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._add_mode and self._draw_preview is not None:
            rect = self._draw_preview.rect()
            self.scene().removeItem(self._draw_preview)
            self._draw_preview = None
            self._draw_origin = None
            self.set_add_mode(False)
            if rect.width() >= _MIN_BOX_SIZE and rect.height() >= _MIN_BOX_SIZE and self.on_box_drawn is not None:
                self.on_box_drawn(rect.x(), rect.y(), rect.width(), rect.height())
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ImageCorrectionDialog(QDialog):
    """One row per TextReplacement in the overview table (Original/
    Übersetzung-preview, both read-only); selecting a row loads its
    translation into the plain-text editor below for actual editing, AND
    highlights that row's box on the canvas to the left. Dragging a box on
    the canvas moves it; dragging its bottom-right corner resizes it - see
    _ResizableRegionItem. "Anwenden und speichern" re-renders the image
    from the pristine source with the (possibly edited) translations
    and/or box geometry, and overwrites `destination` in place - see
    run_image_correction_job()'s docstring for why overwriting is
    intentional here, unlike run_image_job() itself, which refuses an
    existing destination.
    """

    def __init__(
        self,
        language: LanguageManager,
        source: Path,
        destination: Path,
        replacements: list[TextReplacement],
        inpainting_backend_name: str = "box_overlay",
        obstacle_regions: list[OcrTextRegion] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.language = language
        self.source = Path(source)
        self.destination = Path(destination)
        self.replacements = replacements
        self.inpainting_backend_name = inpainting_backend_name
        # 26.08.2026 - regions the ORIGINAL job recognized but never
        # translated (skipped, or a translatable=False layout obstacle -
        # see run_image_correction_job()'s matching docstring). Passed
        # straight through to that function in _apply() - never shown as
        # an editable box on the canvas, only protects real, still-visible
        # content from being grown over when this dialog re-renders.
        self.obstacle_regions = obstacle_regions or []
        self.last_result: ImageJobResult | None = None
        self.last_corrected_replacements: list[TextReplacement] | None = None
        """Set by _apply() to the exact replacements list a successful
        "Anwenden" just wrote out - lets the caller (ui/app.py's
        _open_image_correction_dialog()) use these, not the ORIGINAL
        pre-correction replacements, as the starting point if the dialog
        is reopened - otherwise a second correction round would silently
        discard the first one's edits and start over from the machine
        translation again. Mirrors PdfCorrectionDialog.last_corrected_records."""

        self._row_text: list[str] = [replacement.translated_text for replacement in replacements]
        """Per-row CURRENT translated_text, index-aligned with
        `replacements`. Starts as each replacement's original, untouched
        text. Only ever overwritten by _flush_active_row() for a row
        _dirty actually contains - mirrors PdfCorrectionDialog._row_html."""
        self._dirty: set[int] = set()

        self._row_font_size: list[int | None] = [
            replacement.render_font_size for replacement in replacements
        ]
        self._row_bold: list[bool] = [bool(replacement.render_bold) for replacement in replacements]
        self._row_centered: list[bool] = [replacement.render_centered for replacement in replacements]
        """Per-row CURRENT font-size/bold/centered choice, index-aligned
        with `replacements` (28.08.2026, see the module docstring's
        matching entry) - mirror `_row_text` above exactly: each starts as
        whatever the replacement ALREADY had (None/False/False for a
        never-corrected region, or a previous round's render_font_size/
        render_bold/render_centered if this dialog is reopened on an
        already-corrected image - same reasoning as `render_box` seeding
        the canvas box position in the constructor loop below), and only
        `_on_font_size_changed()`/`_on_bold_toggled()`/
        `_on_centered_toggled()`/`_reset_active_font_size()` ever write to
        them afterward - loading a row into the controls (`_load_row()`)
        only READS these, it never itself counts as a change (guarded by
        `self._loading`, exactly like the plain-text editor already is).

        Deliberately three SEPARATE lists rather than one per-row dict
        (unlike `_edited_geometry`/the new `_edited_font_size`/
        `_edited_bold`/`_edited_centered` below) - these track the CURRENT
        value for every row all the time (needed so switching rows can
        restore the right controls state, same as `_row_text`), whereas
        the `_edited_*` dicts below track only which rows were actually
        TOUCHED this dialog session (needed for build_corrected_
        replacements()'s tri-state contract - see that function's
        docstring) - two genuinely different questions with two different
        natural shapes, exactly why `_row_text`/`_dirty` are already split
        the same way instead of being one structure."""
        self._edited_font_size: dict[int, int | None] = {}
        self._edited_bold: dict[int, bool] = {}
        self._edited_centered: dict[int, bool] = {}
        """Per-row font-size/bold/centered override the user actually
        CHANGED this dialog session - mirrors `_edited_geometry` exactly
        (index absent = row untouched this round, keep whatever the
        replacement's render_font_size/render_bold/render_centered already
        was). Threaded into build_corrected_replacements()'s
        edited_font_size/edited_bold/edited_centered parameters by
        _apply(). `_edited_font_size` alone can hold an explicit `None`
        value (via `_reset_active_font_size()`'s "Automatisch" button) -
        that means "the user explicitly cleared a previously-set override
        back to auto-estimate", NOT "untouched"; see that function's
        docstring for why `_edited_bold`/`_edited_centered` have no such
        "clear" value - a checkable button is only ever True/False, there
        is nothing else for it to explicitly request."""
        self._active_row: int | None = None
        self._loading = False
        self._syncing_selection = False
        """Reentrancy guard between the table and the canvas: selecting a
        table row programmatically drives _load_row() -> _sync_canvas_active(),
        and clicking a canvas box drives _on_region_item_selected() ->
        table.setCurrentCell() -> _on_row_changed() -> _load_row() again -
        this flag breaks that round-trip after the first hop instead of
        letting the two sides bounce off each other forever."""

        self._edited_geometry: dict[int, tuple[int, int, int, int]] = {}
        """Per-row (x, y, width, height) override in source-image pixel
        space, populated only for a row whose canvas box was actually
        moved/resized (see _ResizableRegionItem.geometry()) - a row never
        touched on the canvas is simply absent here, mirroring how
        _dirty/_row_text only track rows genuinely edited in the text
        editor. Threaded into build_corrected_replacements()'s
        edited_geometry parameter by _apply()."""
        self._region_items: list[_ResizableRegionItem] = []

        t = self.language.text
        self.setWindowTitle(t("image_correction.title"))
        self.resize(1200, 700)
        # A real user reported not being able to maximize this dialog at
        # all - QDialog windows don't get a maximize button by default on
        # most platforms/window managers, which matters here specifically
        # because the canvas needs all the screen space it can get for
        # precise box editing on a dense infographic.
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        layout = QVBoxLayout(self)
        hint = QLabel(t("image_correction.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        canvas_hint = QLabel(t("image_correction.canvas_hint"))
        canvas_hint.setWordWrap(True)
        layout.addWidget(canvas_hint)

        canvas_toolbar = QHBoxLayout()
        self.add_region_button = QPushButton(t("image_correction.add_region"))
        self.add_region_button.setCheckable(True)
        self.add_region_button.toggled.connect(self._on_add_region_toggled)
        canvas_toolbar.addWidget(self.add_region_button)
        # 23.08.2026, real user report: "Bei der Korrektur sieht man leider
        # den Text nicht deutlich, da ja die Übersetzung das Original
        # überlagert." - every box's translated-text PREVIEW is drawn
        # fully opaque directly over the pristine original (see
        # _ResizableRegionItem.paint()/set_show_preview()'s own docstring
        # for the exact mechanism); this toggle lets the user hide every
        # box's preview text at once to read the original underneath,
        # without losing the box outlines themselves (still needed to see
        # WHERE each region is while comparing against the original).
        self.toggle_original_button = QPushButton(t("image_correction.show_original"))
        self.toggle_original_button.setCheckable(True)
        self.toggle_original_button.toggled.connect(self._on_toggle_original_visible)
        canvas_toolbar.addWidget(self.toggle_original_button)
        canvas_toolbar.addStretch(1)
        # Zoom controls (RoadMap.md/Backlog.md 21.08.2026: a real user
        # reported having no way to zoom in on the canvas, making precise
        # placement of small text/boxes "fast unmöglich" - see
        # _ImageCanvasView.wheelEvent()/zoom_in()/zoom_out()/reset_zoom()).
        # Toolbar buttons exist alongside Strg+Mausrad for anyone without a
        # scroll wheel handy, or who'd rather click than hold a modifier.
        self.zoom_out_button = QPushButton(t("image_correction.zoom_out"))
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        self.zoom_in_button = QPushButton(t("image_correction.zoom_in"))
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        self.zoom_reset_button = QPushButton(t("image_correction.zoom_reset"))
        self.zoom_reset_button.clicked.connect(self._on_zoom_reset)
        canvas_toolbar.addWidget(self.zoom_out_button)
        canvas_toolbar.addWidget(self.zoom_in_button)
        canvas_toolbar.addWidget(self.zoom_reset_button)
        layout.addLayout(canvas_toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        self.scene = QGraphicsScene(self)
        self.view = _ImageCanvasView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.on_box_drawn = self._on_new_box_drawn
        pixmap = QPixmap(str(self.source))
        if not pixmap.isNull():
            self.scene.addPixmap(pixmap)
            self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
        # A missing/unreadable source (e.g. a dialog built in a test with
        # no real file on disk yet) leaves the scene without a background
        # image, but the boxes below are still created against it - only
        # the visual preview is degraded, not the actual correction data.
        for row, replacement in enumerate(replacements):
            # render_box (26.08.2026, see TextReplacement.render_box's
            # docstring) - if this row was already corrected in an
            # earlier round (re-opening the dialog on an already-
            # corrected image), the canvas box must start at THAT
            # position, not snap back to the original OCR position every
            # time the dialog reopens. `region` itself is used when no
            # such correction exists yet - identical to before this field
            # existed.
            box = replacement.render_box or replacement.region
            item = _ResizableRegionItem(
                row, box.x, box.y, box.width, box.height,
                text=replacement.translated_text,
                on_changed=self._on_region_item_changed, on_selected=self._on_region_item_selected,
                # Always from replacement.region (the TRUE original OCR
                # position), never `box` - mirrors report.py::
                # regions_from_replacements()'s own font_size_px field:
                # a corrected/grown box's height reflects how big the
                # human/auto-grow wanted the DRAW AREA to be, not a claim
                # about the original glyph size the estimate approximates.
                font_size_px=estimated_font_size(replacement.region),
                # 28.08.2026 - seed the preview from whatever this row's
                # _row_font_size/_row_bold/_row_centered already start as
                # (see those lists' own docstring above) so a reopened,
                # already-corrected replacement's box shows its real
                # previous choice immediately, not the plain auto-estimate/
                # left-aligned default it would otherwise start from.
                font_size_override=self._row_font_size[row],
                bold=self._row_bold[row],
                centered=self._row_centered[row],
            )
            self.scene.addItem(item)
            self._region_items.append(item)
        splitter.addWidget(self.view)

        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(len(replacements), 2, self)
        self.table.setHorizontalHeaderLabels(
            [t("image_correction.column_original"), t("image_correction.column_translation")]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        for row, replacement in enumerate(replacements):
            original_item = QTableWidgetItem(replacement.region.text)
            original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
            # Read-only PREVIEW of the translation (kept in sync by
            # _flush_active_row()) - actual editing happens in self.editor
            # below, not in this cell, so it never accepts direct input.
            translation_item = QTableWidgetItem(replacement.translated_text)
            translation_item.setFlags(translation_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, _ORIGINAL_COLUMN, original_item)
            self.table.setItem(row, _TRANSLATION_COLUMN, translation_item)
        self.table.currentCellChanged.connect(self._on_row_changed)
        right_layout.addWidget(self.table)

        editor_label = QLabel(t("image_correction.editor_label"))
        right_layout.addWidget(editor_label)

        self.editor = QPlainTextEdit(self)
        self.editor.setFixedHeight(100)
        self.editor.textChanged.connect(self._on_editor_text_changed)
        right_layout.addWidget(self.editor)

        reset_row = QHBoxLayout()
        self.reset_geometry_button = QPushButton(t("image_correction.reset_geometry"))
        self.reset_geometry_button.clicked.connect(self._reset_active_geometry)
        reset_row.addWidget(self.reset_geometry_button)
        reset_row.addStretch(1)
        right_layout.addLayout(reset_row)

        # 28.08.2026 - font size/bold/alignment per box, one shared control
        # set for whichever row is currently active (see the module
        # docstring's matching entry and _load_row()/_on_font_size_changed()/
        # _reset_active_font_size()/_on_bold_toggled()/_on_centered_toggled()
        # below) - real user report, Backlog.md 28.08.2026: "Wenn ich etwas
        # korrigiere, muss es auch genauso korrigiert werden wie ich es im
        # Viewer sehe."
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel(t("image_correction.font_size_label")))
        self.font_size_spin = QSpinBox(self)
        self.font_size_spin.setRange(_MIN_FONT_SIZE_SPIN, _MAX_FONT_SIZE_SPIN)
        # editingFinished (not valueChanged) is deliberately NOT used here -
        # valueChanged also fires for the every-single-step change a user
        # makes while dragging the spinner, which is fine: _on_font_size_
        # changed()/_row_font_size/_edited_font_size just record the latest
        # value, exactly like every keystroke in self.editor already updates
        # _row_text's live canvas preview (see _on_editor_text_changed()).
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        format_row.addWidget(self.font_size_spin)
        self.font_size_auto_button = QPushButton(t("image_correction.font_size_auto"))
        self.font_size_auto_button.clicked.connect(self._reset_active_font_size)
        format_row.addWidget(self.font_size_auto_button)
        self.bold_button = QPushButton(t("image_correction.bold"))
        self.bold_button.setCheckable(True)
        self.bold_button.toggled.connect(self._on_bold_toggled)
        format_row.addWidget(self.bold_button)
        self.centered_button = QPushButton(t("image_correction.centered"))
        self.centered_button.setCheckable(True)
        self.centered_button.toggled.connect(self._on_centered_toggled)
        format_row.addWidget(self.centered_button)
        format_row.addStretch(1)
        right_layout.addLayout(format_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.apply_button = QPushButton(t("image_correction.apply"))
        self.apply_button.clicked.connect(self._apply)
        buttons.addWidget(self.apply_button)
        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        close_box.button(QDialogButtonBox.Close).setText(t("image_correction.close"))
        buttons.addWidget(close_box)
        right_layout.addLayout(buttons)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        if replacements:
            # Not left to the currentCellChanged signal from
            # setCurrentCell() below - mirrors PdfCorrectionDialog's
            # identical reasoning.
            self._load_row(0)
            self.table.setCurrentCell(0, _TRANSLATION_COLUMN)

    def _on_row_changed(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        if current_row < 0 or current_row == self._active_row:
            return
        self._load_row(current_row)

    def _load_row(self, row: int) -> None:
        self._flush_active_row()
        self._active_row = row
        self._loading = True
        try:
            self.editor.setPlainText(self._row_text[row])
            # 28.08.2026 - same _loading guard as the editor above, so
            # populating these controls from `row`'s state never itself
            # looks like the user touching them (see _on_font_size_changed()/
            # _on_bold_toggled()/_on_centered_toggled()'s own guards). A row
            # with no font-size override yet (`_row_font_size[row] is None`)
            # still shows a NUMBER, not a blank/zero spinbox - the real
            # OCR-based estimate this row would auto-render at, purely for
            # reference (see the module docstring and _MIN_FONT_SIZE_SPIN's
            # own comment) - showing it here does NOT itself set an
            # override; only actually changing the spinbox does.
            font_size = self._row_font_size[row]
            display_size = font_size if font_size is not None else estimated_font_size(
                self.replacements[row].region
            )
            self.font_size_spin.setValue(display_size)
            self.bold_button.setChecked(self._row_bold[row])
            self.centered_button.setChecked(self._row_centered[row])
        finally:
            self._loading = False
        self._sync_canvas_active(row)

    def _sync_canvas_active(self, row: int) -> None:
        """Repaint every canvas box's pen so only `row`'s box is
        highlighted - called whenever the active row changes, from either
        side (table selection or a canvas click)."""
        for item in self._region_items:
            item.set_active(item.row == row)

    def _on_region_item_selected(self, row: int) -> None:
        """A box on the canvas was clicked (or a drag on it started) -
        drive the table's selection to match, reusing the exact same
        _on_row_changed()/_load_row() path a manual table click takes."""
        if self._syncing_selection or row == self._active_row:
            return
        self._syncing_selection = True
        try:
            self.table.setCurrentCell(row, _TRANSLATION_COLUMN)
        finally:
            self._syncing_selection = False

    def _on_region_item_changed(self, row: int) -> None:
        """A box on the canvas was moved and/or resized - record its
        current geometry as this row's override. Does NOT touch _dirty
        (that set is text-edit-only); a geometry-only change is tracked
        purely through _edited_geometry, and _apply() consults both
        independently."""
        self._edited_geometry[row] = self._region_items[row].geometry()

    def _reset_active_geometry(self) -> None:
        """Restore the active row's box to its original OcrTextRegion
        geometry, discarding any drag/resize override - the "undo" for a
        box the user moved/resized by mistake, without having to reopen
        the whole dialog. For a manually-added row (see
        _on_new_box_drawn()) this is a no-op: self.replacements[row].region
        already IS exactly the geometry it was drawn at - there is no
        earlier OCR geometry underneath to fall back to."""
        if self._active_row is None:
            return
        row = self._active_row
        self._edited_geometry.pop(row, None)
        region = self.replacements[row].region
        self._region_items[row].set_geometry(region.x, region.y, region.width, region.height)

    def _on_font_size_changed(self, value: int) -> None:
        """self.font_size_spin's valueChanged - guarded by self._loading
        exactly like _on_editor_text_changed() (see _load_row(), which sets
        the spinbox's DISPLAY value under that same guard without this
        counting as a change) so populating the spinbox for a newly loaded
        row is never mistaken for the user picking a new size. Records an
        explicit override for the ACTIVE row in both self._row_font_size
        (survives switching rows and back) and self._edited_font_size (fed
        into build_corrected_replacements() by _apply(), see that dict's
        own docstring on the constructor) - and updates the canvas preview
        immediately, mirroring how _on_editor_text_changed() live-updates
        the box's text preview on every keystroke rather than only at
        _apply() time."""
        if self._loading or self._active_row is None:
            return
        row = self._active_row
        self._row_font_size[row] = value
        self._edited_font_size[row] = value
        self._region_items[row].set_font_size_override(value)

    def _reset_active_font_size(self) -> None:
        """"Automatisch" button - clears the active row's font-size
        override back to auto-estimate, the size counterpart of
        _reset_active_geometry() above. Unlike that method, this DOES
        explicitly record the change (self._edited_font_size[row] = None,
        not a dict removal) - build_corrected_replacements()'s tri-state
        contract needs an explicit None here to distinguish "the user
        asked to clear a previously-set override" from "this row's size
        was never touched this round" (see that function's docstring;
        _edited_geometry has no such distinction because a geometry reset
        always has a real, non-None fallback - the region's own original
        position - to restore instead)."""
        if self._active_row is None:
            return
        row = self._active_row
        self._row_font_size[row] = None
        self._edited_font_size[row] = None
        self._region_items[row].set_font_size_override(None)
        self._loading = True
        try:
            self.font_size_spin.setValue(estimated_font_size(self.replacements[row].region))
        finally:
            self._loading = False

    def _on_bold_toggled(self, checked: bool) -> None:
        """self.bold_button's toggled - see _on_font_size_changed()'s
        docstring for the _loading guard/live-preview-update reasoning,
        identical here. No separate "reset to auto" control for bold (see
        the module docstring/self._edited_bold's own docstring) - toggling
        this button always records an explicit True/False override."""
        if self._loading or self._active_row is None:
            return
        row = self._active_row
        self._row_bold[row] = checked
        self._edited_bold[row] = checked
        self._region_items[row].set_bold(checked)

    def _on_centered_toggled(self, checked: bool) -> None:
        """self.centered_button's toggled - see _on_font_size_changed()'s
        docstring for the _loading guard/live-preview-update reasoning,
        identical here. `checked=True` means centered, `False` (also the
        button's/every never-touched row's default) means left-aligned -
        matches pipeline.images.inpainting.TextReplacement.render_centered's
        own default exactly."""
        if self._loading or self._active_row is None:
            return
        row = self._active_row
        self._row_centered[row] = checked
        self._edited_centered[row] = checked
        self._region_items[row].set_centered(checked)

    def _on_zoom_in(self) -> None:
        self.view.zoom_in()

    def _on_zoom_out(self) -> None:
        self.view.zoom_out()

    def _on_zoom_reset(self) -> None:
        self.view.reset_zoom()

    def _on_add_region_toggled(self, checked: bool) -> None:
        """"Neue Box hinzufügen" toggled - see _ImageCanvasView's docstring
        for the actual drag-to-draw handling; this just relays the
        checkbox state to the view and shows/clears a hint while active."""
        self.view.set_add_mode(checked)
        t = self.language.text
        self.status_label.setText(t("image_correction.add_region_hint") if checked else "")

    def _on_toggle_original_visible(self, checked: bool) -> None:
        """"Original anzeigen" toggled - hides/shows every box's
        translated-text preview at once (see _ResizableRegionItem.
        set_show_preview()'s docstring). `checked=True` means "show the
        original" -> hide the preview text, so this is inverted relative
        to set_show_preview()'s own `show` meaning."""
        for item in self._region_items:
            item.set_show_preview(not checked)

    def _on_new_box_drawn(self, x: float, y: float, width: float, height: float) -> None:
        """A user just finished drawing a brand-new box on the canvas
        (RoadMap.md/Backlog.md 21.08.2026: for text Tesseract never
        recognized at all, so there was previously no row/box to correct
        for it). Appends a new TextReplacement - an OcrTextRegion with no
        original OCR text (confidence=100.0: not an OCR result, so the
        confidence/height-outlier filters in pipeline.images.
        translate_image never applied to it in the first place, and there
        is nothing meaningful to report a confidence FOR) - and a matching
        table row/canvas box, then hands focus straight to the editor so
        the user can type the translation immediately.

        Mirrors the constructor's per-row setup (table item + canvas item)
        almost exactly, just appending one row instead of building all of
        them from `replacements` at once.
        """
        t = self.language.text
        x, y = round(x), round(y)
        width, height = max(round(width), _MIN_BOX_SIZE), max(round(height), _MIN_BOX_SIZE)
        region = OcrTextRegion(text="", x=x, y=y, width=width, height=height, confidence=100.0)
        replacement = TextReplacement(region=region, translated_text="")
        row = len(self.replacements)
        self.replacements.append(replacement)
        self._row_text.append("")
        # 28.08.2026 - keep _row_font_size/_row_bold/_row_centered index-
        # aligned with `replacements`/_row_text (see those lists' own
        # docstring in __init__) - a brand-new box starts exactly like the
        # TextReplacement just created above (render_font_size=None,
        # render_bold=None -> False, render_centered=False, its dataclass
        # defaults), i.e. auto-estimate/regular/left, same as every never-
        # corrected OCR-recognized row.
        self._row_font_size.append(None)
        self._row_bold.append(False)
        self._row_centered.append(False)

        self.table.insertRow(row)
        original_item = QTableWidgetItem(t("image_correction.manual_region_label"))
        original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
        translation_item = QTableWidgetItem("")
        translation_item.setFlags(translation_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, _ORIGINAL_COLUMN, original_item)
        self.table.setItem(row, _TRANSLATION_COLUMN, translation_item)

        item = _ResizableRegionItem(
            row, x, y, width, height, text="",
            on_changed=self._on_region_item_changed, on_selected=self._on_region_item_selected,
        )
        # A brand-new box must respect whatever the "Original anzeigen"
        # toggle is currently set to, same as every pre-existing box -
        # otherwise a box drawn WHILE the toggle hides previews would
        # start out ignoring it (only matters once the user types a
        # translation for it; see set_show_preview()'s docstring).
        item.set_show_preview(not self.toggle_original_button.isChecked())
        self.scene.addItem(item)
        self._region_items.append(item)

        self._load_row(row)
        self.table.setCurrentCell(row, _TRANSLATION_COLUMN)
        self.editor.setFocus()
        # The view already turned its OWN _add_mode back off (see
        # _ImageCanvasView.mouseReleaseEvent()) once the drag finished,
        # but the toolbar button's checked state is separate and would
        # otherwise stay visually "pressed" - setChecked(False) here re-
        # fires _on_add_region_toggled(False), which is what clears
        # status_label, so the actual "box added" message below is set
        # AFTER that, not before (or it would be immediately wiped again).
        self.add_region_button.setChecked(False)
        self.status_label.setText(t("image_correction.manual_region_added"))

    def _flush_active_row(self) -> None:
        """Write the editor's CURRENT content back into _row_text for the
        row that was active until now - but only if that row is actually
        in _dirty (see its docstring for why an untouched row must keep
        its pristine original string).
        """
        if self._active_row is None or self._active_row not in self._dirty:
            return
        row = self._active_row
        self._row_text[row] = self.editor.toPlainText()
        preview_item = self.table.item(row, _TRANSLATION_COLUMN)
        if preview_item is not None:
            preview_item.setText(self._row_text[row])

    def _on_editor_text_changed(self) -> None:
        if self._loading or self._active_row is None:
            return
        self._dirty.add(self._active_row)
        # Live-update the active row's canvas preview text as the user
        # types, not just on save - _row_text[row] itself is only updated
        # later, by _flush_active_row() (on row switch or _apply()), but
        # the box on the canvas should reflect what's on screen right now.
        self._region_items[self._active_row].set_text(self.editor.toPlainText())

    def _current_edits(self) -> dict[int, str]:
        self._flush_active_row()
        edits: dict[int, str] = {}
        for row in self._dirty:
            edits[row] = self._row_text[row]
        return edits

    def _apply(self) -> None:
        t = self.language.text
        self.apply_button.setEnabled(False)
        self.status_label.setText(t("image_correction.applying"))
        # No OCR/provider/network call is involved (see
        # run_image_correction_job()'s docstring) - fast and local enough
        # to run directly on the UI thread rather than wiring a
        # background QThreadPool worker just for this action.
        try:
            corrected_replacements = build_corrected_replacements(
                self.replacements, self._current_edits(), edited_geometry=self._edited_geometry or None,
                # 28.08.2026 - see self._edited_font_size/_edited_bold/
                # _edited_centered's own docstring in __init__ and
                # build_corrected_replacements()'s matching parameter
                # docstring for the tri-state contract. `or None` mirrors
                # `edited_geometry` immediately above exactly - an empty
                # dict (no row touched this round) becomes None, not an
                # empty-but-truthy dict, purely so a caller inspecting the
                # dict's own truthiness elsewhere can't mistake "nothing
                # touched" for "touched with an empty set of changes"; the
                # function itself treats both the same either way.
                edited_font_size=self._edited_font_size or None,
                edited_bold=self._edited_bold or None,
                edited_centered=self._edited_centered or None,
            )
            result = run_image_correction_job(
                self.source, self.destination, corrected_replacements,
                inpainting_backend_name=self.inpainting_backend_name,
                obstacle_regions=self.obstacle_regions,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not silently swallowed
            self.status_label.setText(t("image_correction.failed", error=str(exc)))
            QMessageBox.warning(self, t("image_correction.title"), t("image_correction.failed", error=str(exc)))
            return
        finally:
            self.apply_button.setEnabled(True)

        self.last_result = result
        self.last_corrected_replacements = corrected_replacements
        self.status_label.setText(
            t("image_correction.success", count=result.stats.translated, output=str(result.output_path))
        )
