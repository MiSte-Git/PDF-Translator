from __future__ import annotations

from ui.theme import (
    DARK_COLORS,
    LIGHT_COLORS,
    RADIUS_CARD,
    RADIUS_CONTROL,
    RADIUS_PILL,
    SURFACE_DARK,
    SURFACE_LIGHT,
    build_stylesheet,
    contrast_ratio,
    hex_to_rgb,
    palette_colors,
    surface_colors,
)

# WCAG 2.x "AA" minimum for normal-sized text/UI content.
_MIN_CONTRAST = 4.5


def test_palette_colors_selects_dark_or_light() -> None:
    assert palette_colors(True) is DARK_COLORS
    assert palette_colors(False) is LIGHT_COLORS


def test_contrast_ratio_is_symmetric_and_maximal_for_black_on_white() -> None:
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == contrast_ratio((255, 255, 255), (0, 0, 0))
    assert round(contrast_ratio((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert contrast_ratio((10, 10, 10), (10, 10, 10)) == 1.0


def test_dark_and_light_palettes_meet_wcag_aa_for_text_pairs() -> None:
    for colors in (DARK_COLORS, LIGHT_COLORS):
        # Input fields (QLineEdit/QTextEdit) and the checkbox render text on
        # "base"; regular labels/checkbox indicator surroundings render on
        # "window"; buttons render on "button" - the exact widgets the
        # reported bug affected.
        assert contrast_ratio(colors["base"], colors["text"]) >= _MIN_CONTRAST
        assert contrast_ratio(colors["window"], colors["window_text"]) >= _MIN_CONTRAST
        assert contrast_ratio(colors["button"], colors["button_text"]) >= _MIN_CONTRAST
        assert contrast_ratio(colors["highlight"], colors["highlighted_text"]) >= _MIN_CONTRAST


def test_disabled_state_stays_visible_but_clearly_distinguishable() -> None:
    for colors in (DARK_COLORS, LIGHT_COLORS):
        # Disabled text must still be legible (not invisible)...
        assert contrast_ratio(colors["window"], colors["disabled_text"]) >= 2.0
        # ...but visibly weaker than fully-enabled text, so a disabled Start
        # button cannot be mistaken for an enabled one (the likely cause of
        # "clicking Start does nothing").
        assert contrast_ratio(colors["window"], colors["disabled_text"]) < contrast_ratio(
            colors["window"], colors["window_text"]
        )


def test_hex_to_rgb_parses_hash_prefixed_hex() -> None:
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#ffffff") == (255, 255, 255)
    assert hex_to_rgb("#1f7a5f") == (0x1F, 0x7A, 0x5F)


def test_surface_colors_selects_dark_or_light() -> None:
    assert surface_colors(True) is SURFACE_DARK
    assert surface_colors(False) is SURFACE_LIGHT


def test_surface_colors_meet_wcag_aa_for_text_pairs() -> None:
    # Same idea as test_dark_and_light_palettes_meet_wcag_aa_for_text_pairs
    # above, for the new "card" design system (26.08.2026, see ui/theme.py's
    # module comment above SURFACE_LIGHT/SURFACE_DARK): a friendlier-looking
    # colour scheme is worthless if it quietly reintroduces the
    # "unreadable in some real environment" bug this file exists to catch.
    pairs = (
        ("ink", "card"),  # QGroupBox body text on the card background
        ("ink", "bg"),  # QLabel text directly on the window background
        ("muted", "card"),  # disabled/secondary text on a card
        ("muted", "bg"),  # disabled/secondary text on the window
        ("button_text", "button_bg"),  # default QPushButton
        ("button_text", "button_hover"),  # default QPushButton, hovered
        ("accent_text", "accent"),  # the primary ("Start") button
        ("accent_text", "accent_hover"),  # the primary button, hovered
        ("ink", "input_bg"),  # QLineEdit/QTextEdit/QComboBox/QSpinBox text
    )
    for colors in (SURFACE_LIGHT, SURFACE_DARK):
        for fg, bg in pairs:
            ratio = contrast_ratio(hex_to_rgb(colors[fg]), hex_to_rgb(colors[bg]))
            assert ratio >= _MIN_CONTRAST, f"{fg} on {bg}: {ratio:.2f} < {_MIN_CONTRAST}"


def test_surface_light_and_dark_share_the_same_accent() -> None:
    # Deliberate, not an oversight - see the module comment above
    # SURFACE_LIGHT/SURFACE_DARK for why a dark-mode-specific accent was
    # rejected (it failed the contrast bar above).
    assert SURFACE_LIGHT["accent"] == SURFACE_DARK["accent"]
    assert SURFACE_LIGHT["accent_hover"] == SURFACE_DARK["accent_hover"]


def test_build_stylesheet_returns_qss_for_both_modes() -> None:
    for is_dark in (True, False):
        qss = build_stylesheet(is_dark)
        assert isinstance(qss, str)
        assert qss.strip()
        # Structural markers: every widget class this design system touches
        # must actually be selected somewhere in the sheet.
        for selector in (
            "QGroupBox",
            "QPushButton",
            'QPushButton[cssClass="primary"]',
            "QLineEdit",
            "QComboBox::down-arrow",
            "QSpinBox::up-arrow",
            "QSpinBox::down-arrow",
            "QCheckBox::indicator",
            "QProgressBar",
        ):
            assert selector in qss
        # The radii actually get used, not just declared.
        assert f"{RADIUS_CARD}px" in qss
        assert f"{RADIUS_CONTROL}px" in qss
        assert f"{RADIUS_PILL}px" in qss


def test_build_stylesheet_differs_between_light_and_dark() -> None:
    assert build_stylesheet(True) != build_stylesheet(False)
