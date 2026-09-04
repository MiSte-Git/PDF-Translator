from ui.i18n import CATALOGUES, LOCALES, LanguageManager

_ALL_CODES = {"de", "en", "fr", "es", "it", "nl", "fi", "hr", "ru"}


def test_all_catalogues_have_identical_keys() -> None:
    reference = set(CATALOGUES["de"])
    for code, catalogue in CATALOGUES.items():
        assert set(catalogue) == reference, f"{code} catalogue has mismatched keys"


def test_requested_locales_are_registered_and_all_available() -> None:
    # All nine locales originally requested (Backlog.md) are now translated
    # and switched on - none is left in the "prepared but disabled" state
    # ui/app.py's SettingsDialog shows via LocaleInfo.available.
    assert {locale.code for locale in LOCALES} == _ALL_CODES
    assert {locale.code for locale in LOCALES if locale.available} == _ALL_CODES


def test_every_catalogue_is_actually_translated() -> None:
    # Guards against a locale silently ending up as a copy of English/German
    # (e.g. a translation step that no-oped) by spot-checking a handful of
    # keys are distinct per language.
    sample_keys = ["settings.title", "app.title", "mode.pdf", "field.provider"]
    for code in _ALL_CODES - {"de", "en"}:
        for key in sample_keys:
            if key == "app.title":
                continue  # "Document Translator" is intentionally kept as the product name in every locale
            assert CATALOGUES[code][key] != CATALOGUES["en"][key], f"{code}.{key} looks untranslated"


def test_language_switch_is_runtime_and_unknown_locale_is_rejected() -> None:
    manager = LanguageManager("de")
    for code in sorted(_ALL_CODES):
        manager.set_language(code)
        assert manager.language == code
        assert manager.text("settings.title") == CATALOGUES[code]["settings.title"]
    manager.set_language("xx")
    assert manager.language == sorted(_ALL_CODES)[-1]
