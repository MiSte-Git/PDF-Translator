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


# --- QSS design system (26.08.2026) ------------------------------------
#
# Michael: "Das UI gefällt mir so gar nicht. [...] Es ist heller, hat
# runde Buttons usw. Unseres schaut so staubig, technisch und trocken
# aus." - traced to this app never having had a QSS stylesheet at all:
# app.py only ever built a QPalette (DARK_COLORS/LIGHT_COLORS above),
# which is exactly the flat, square, no-radius default Qt look. Asked
# to match the visual language of his other project ("Konvertierung
# Audio-Video", a separate Tauri/HTML+CSS app - different tech stack,
# not portable as code, but its tauri-app/ui/style.css IS the reference
# for the colors/radii below): warm off-white background, white cards
# with soft rounded corners, a muted warm-beige secondary button, a
# green primary action button, softly rounded inputs.
#
# SURFACE_LIGHT/SURFACE_DARK are a SEPARATE token set from DARK_COLORS/
# LIGHT_COLORS above, not a replacement - QPalette (via
# apply_explicit_palette() in ui/app.py) still governs native/unstyled
# chrome (window frame, native file/color dialogs, disabled-state
# blending), while build_stylesheet() below governs everything QSS can
# reach (QGroupBox "cards", QPushButton, QLineEdit/QTextEdit/QComboBox/
# QSpinBox, QProgressBar). Deliberately keeping both rather than
# folding one into the other: QSS cannot restyle some native dialogs at
# all, so QPalette must stay correct on its own regardless of whether
# QSS is also applied on top.
#
# Every text/background pair below is contrast-checked the same way as
# DARK_COLORS/LIGHT_COLORS - see
# tests/test_ui_theme.py::test_surface_colors_meet_wcag_aa_for_text_pairs
# - same real motivation as this file's very first paragraph: a colour
# scheme that LOOKS friendlier is worthless if it quietly repeats the
# "unreadable in some real environment" bug this file was originally
# built to fix. `accent`/`accent_hover` are deliberately the SAME hex
# in both SURFACE_LIGHT and SURFACE_DARK (unlike every other token,
# which differs between the two) - the first, brighter green tried for
# dark mode (#2f9c79) only reached 3.41:1 against white button text,
# below the 4.5:1 this module holds every other pair to; #1f7a5f (the
# light theme's own accent) reaches 5.24:1 and reads clearly on the
# dark surfaces too, so there was no reason to maintain a second value.
HEX = str

SURFACE_LIGHT: dict[str, HEX] = {
    "bg": "#f2f1ec",
    "card": "#ffffff",
    "ink": "#1c1c1c",
    "muted": "#6f6b62",
    "line": "#ddd7cc",
    "input_bg": "#fcfbf8",
    "button_bg": "#efe9dc",
    "button_hover": "#e2d7c6",
    "button_text": "#1c1c1c",
    "accent": "#1f7a5f",
    "accent_hover": "#14523f",
    "accent_text": "#ffffff",
}

SURFACE_DARK: dict[str, HEX] = {
    "bg": "#201f1c",
    "card": "#2a2924",
    "ink": "#ece9e2",
    "muted": "#a8a296",
    "line": "#423f37",
    "input_bg": "#232219",
    "button_bg": "#3a382f",
    "button_hover": "#484539",
    "button_text": "#ece9e2",
    "accent": "#1f7a5f",
    "accent_hover": "#14523f",
    "accent_text": "#ffffff",
}

# Corner radii - "card" for QGroupBox sections, "control" for buttons/
# inputs, "pill" for the progress bar track (fully rounded ends, same
# idea as tauri-app/ui/style.css's `.progress-bar { border-radius: 999px }`).
RADIUS_CARD = 14
RADIUS_CONTROL = 9
RADIUS_PILL = 999


def hex_to_rgb(value: HEX) -> RGB:
    """Parses a "#rrggbb" string into an (r, g, b) tuple - the SURFACE_*
    tokens above are stored as hex strings (the natural format for QSS),
    but contrast_ratio() works on the RGB tuples DARK_COLORS/LIGHT_COLORS
    use. This lets the exact same tested contrast_ratio() function check
    the new tokens too, instead of a second, unverified implementation -
    see test_surface_colors_meet_wcag_aa_for_text_pairs.
    """
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def surface_colors(is_dark: bool) -> dict[str, HEX]:
    return SURFACE_DARK if is_dark else SURFACE_LIGHT


def build_stylesheet(is_dark: bool) -> str:
    """The application-wide QSS (set via QApplication.setStyleSheet() in
    ui/app.py, right after apply_explicit_palette()) that gives every
    QGroupBox a rounded "card" look and every button/input rounded
    corners - see this section's module-level comment for the full
    reasoning and the reference project.

    Applied at the QApplication level, so it cascades to every window/
    dialog automatically (SettingsDialog, the correction dialogs, ...)
    without each of them needing their own copy - confirmed no other
    ui/*.py file sets its own conflicting QGroupBox/QPushButton
    stylesheet (a local .setStyleSheet() on a specific widget, like the
    handful of bold-hint QLabels in ui/app.py, still wins for that one
    widget over this app-wide sheet - normal Qt cascade behaviour, and
    none of those local overrides touch color/radius/padding).

    `QPushButton[cssClass="primary"]` is an opt-in selector - a button
    only gets the solid green treatment if ui/app.py explicitly sets
    that dynamic property (currently just MainWindow.start, the app's
    one primary call-to-action, mirroring tauri-app/ui/style.css's
    `button.primary`). Every other button (Analyze, Cancel, Settings,
    the dialog buttons, ...) gets the neutral secondary look - matching
    the reference, where only "Start" is green and "Abbrechen"/
    "Log-Pfad" stay muted-beige.
    """
    c = surface_colors(is_dark)
    return f"""
        QMainWindow, QDialog, QWidget {{
            background: {c['bg']};
            color: {c['ink']};
        }}

        QGroupBox {{
            background: {c['card']};
            border: 1px solid {c['line']};
            border-radius: {RADIUS_CARD}px;
            margin-top: 14px;
            padding: 16px 14px 14px 14px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 6px;
            color: {c['ink']};
        }}

        QLabel {{
            background: transparent;
            color: {c['ink']};
        }}

        QPushButton {{
            background: {c['button_bg']};
            color: {c['button_text']};
            border: none;
            border-radius: {RADIUS_CONTROL}px;
            padding: 8px 16px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {c['button_hover']};
        }}
        QPushButton:disabled {{
            color: {c['muted']};
            background: {c['button_bg']};
        }}
        QPushButton[cssClass="primary"] {{
            background: {c['accent']};
            color: {c['accent_text']};
        }}
        QPushButton[cssClass="primary"]:hover {{
            background: {c['accent_hover']};
        }}
        QPushButton[cssClass="primary"]:disabled {{
            background: {c['button_bg']};
            color: {c['muted']};
        }}

        /* Sprachumschalter-Leiste (04.09.2026) - eigene Klasse statt der
        normalen QPushButton-Regel oben: flach/randlos im Ruhezustand (die
        Flagge selbst traegt schon genug Farbe), ein farbiger Rahmen zeigt
        nur die aktuell aktive Sprache an (QToolButton::checked). */
        QToolButton[cssClass="flag"] {{
            background: transparent;
            border: 2px solid transparent;
            border-radius: 6px;
            padding: 2px;
        }}
        QToolButton[cssClass="flag"]:hover {{
            background: {c['button_hover']};
        }}
        QToolButton[cssClass="flag"]:checked {{
            border: 2px solid {c['accent']};
            background: {c['button_bg']};
        }}

        QLineEdit, QTextEdit, QComboBox, QSpinBox {{
            background: {c['input_bg']};
            color: {c['ink']};
            border: 1px solid {c['line']};
            border-radius: {RADIUS_CONTROL}px;
            padding: 6px 10px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        /* 26.08.2026 - Michael, after the first screenshot: "Es fehlen die
           Pfeile an den Auswahlboxen." Root cause: as soon as a QComboBox
           gets ANY stylesheet rule (even just border/background above),
           Qt stops drawing the native platform down-arrow entirely and
           expects the stylesheet to supply one - an empty
           QComboBox::down-arrow means no arrow at all, not the default
           one. Same applies to QSpinBox's up/down buttons below. Drawn as
           a plain CSS border-triangle (0x0 box, opposite border wide and
           colored, the other two transparent) instead of an image asset -
           no bundled icon file needed, and it recolors for free with
           `muted` in both light and dark mode. */
        QComboBox::down-arrow {{
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {c['muted']};
            margin-right: 10px;
        }}
        QComboBox::down-arrow:disabled {{
            border-top-color: {c['line']};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            border: none;
            width: 18px;
        }}
        QSpinBox::up-arrow {{
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {c['muted']};
        }}
        QSpinBox::down-arrow {{
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {c['muted']};
        }}
        QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
            color: {c['muted']};
        }}

        QCheckBox {{
            spacing: 8px;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {c['line']};
            border-radius: 4px;
            background: {c['input_bg']};
        }}
        QCheckBox::indicator:checked {{
            background: {c['accent']};
            border-color: {c['accent']};
        }}

        QProgressBar {{
            background: {c['button_bg']};
            border: none;
            border-radius: {RADIUS_PILL}px;
            height: 8px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: {c['accent']};
            border-radius: {RADIUS_PILL}px;
        }}
    """
