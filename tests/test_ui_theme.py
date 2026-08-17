from __future__ import annotations

from ui.theme import DARK_COLORS, LIGHT_COLORS, contrast_ratio, palette_colors

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
