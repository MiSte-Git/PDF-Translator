"""Explicit, contrast-tested UI colors - independent from Qt objects so the
contrast itself can be unit-tested without a display (see tests/test_ui_theme.py).

Why this exists: a reported bug showed input field text and the checkbox
essentially unreadable while the OS was in dark mode, and separately a
"clicking Start does nothing" report that was most likely a disabled button
rendered with too little contrast to look disabled. Both point to the same
root cause - this app let the desktop environment's own Qt style/palette
integration decide all colors, and at least one real-world Linux dark theme
combination produces a palette with too little contrast for this app's
widgets (readable window chrome, unreadable QLineEdit/QTextEdit/QCheckBox/
disabled QPushButton content). ui/app.py forces this palette explicitly via
QPalette instead of trusting that integration, including the QPalette.Disabled
color group so a disabled Start button is unambiguously distinguishable from
an enabled one.
"""
from __future__ import annotations

RGB = tuple[int, int, int]

DARK_COLORS: dict[str, RGB] = {
    "window": (45, 45, 45),
    "window_text": (235, 235, 235),
    "base": (24, 24, 24),
    "text": (235, 235, 235),
    "button": (66, 66, 66),
    "button_text": (235, 235, 235),
    "highlight": (37, 99, 189),
    "highlighted_text": (255, 255, 255),
    "placeholder_text": (150, 150, 150),
    "disabled_text": (120, 120, 120),
    "disabled_button": (50, 50, 50),
}

LIGHT_COLORS: dict[str, RGB] = {
    "window": (240, 240, 240),
    "window_text": (20, 20, 20),
    "base": (255, 255, 255),
    "text": (20, 20, 20),
    "button": (225, 225, 225),
    "button_text": (20, 20, 20),
    "highlight": (37, 99, 189),
    "highlighted_text": (255, 255, 255),
    "placeholder_text": (110, 110, 110),
    "disabled_text": (150, 150, 150),
    "disabled_button": (235, 235, 235),
}


def _relative_luminance(rgb: RGB) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: RGB, b: RGB) -> float:
    """WCAG 2.x contrast ratio between two RGB colors: 1.0 is no contrast
    (identical colors), 21.0 is the maximum (pure black on pure white).
    """
    la, lb = _relative_luminance(a), _relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def palette_colors(is_dark: bool) -> dict[str, RGB]:
    return DARK_COLORS if is_dark else LIGHT_COLORS
