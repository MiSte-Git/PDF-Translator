"""Word-wrapping QLabel for the inline field hints in ui/app.py
(provider_hint, ocr_engine_hint, inpainting_backend_hint).

14.10.2026: once those hints got a visible border (ui/theme.py's
HINT_ERROR_STYLE/HINT_WARNING_STYLE), it showed that they were always far
taller than their text: the form sits inside a QScrollArea, and the layouts
there size a word-wrapping QLabel by its plain sizeHint(), which Qt computes
for an arbitrary narrow width (about 200 px, i.e. many short lines), instead
of by heightForWidth() at the width the label actually has. Without a border
this only showed up as unexplained extra whitespace below the field.

HintLabel reports its height for its current width instead, and asks the
layout to re-query that whenever its width changes.
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel


class HintLabel(QLabel):
    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self.wordWrap() and self.width() > 0:
            hint.setHeight(self.heightForWidth(self.width()))
        return hint

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        if self.wordWrap() and self.width() > 0:
            hint.setHeight(self.heightForWidth(self.width()))
        return hint

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.wordWrap() and event.oldSize().width() != event.size().width():
            self.updateGeometry()
