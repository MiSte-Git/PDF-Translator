from ui.i18n import CATALOGUES, LOCALES, LanguageManager


def test_german_and_english_catalogues_have_identical_keys() -> None:
    assert set(CATALOGUES["de"]) == set(CATALOGUES["en"])


def test_requested_locales_are_registered_and_only_de_en_available() -> None:
    assert {locale.code for locale in LOCALES} == {"de", "en", "fr", "es", "it", "nl", "fi", "hr", "ru"}
    assert {locale.code for locale in LOCALES if locale.available} == {"de", "en"}


def test_language_switch_is_runtime_and_unknown_locale_is_rejected() -> None:
    manager = LanguageManager("de")
    manager.set_language("en")
    assert manager.language == "en"
    assert manager.text("settings.title") == "Settings"
    manager.set_language("ru")
    assert manager.language == "en"
