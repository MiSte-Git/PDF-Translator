"""i18n-Abdeckung fuer die Bootstrapper-Tooltips (bootstrap/app.py's
_Tooltip/_tip - siehe deren Docstrings fuer die Begruendung, warum
tkinter anders als die Qt-App keine Trennung Tooltip/WhatsThis kennt).

07.09.2026 (Michael: "Ausserdem haette ich noch gerne zu jeder Option in
der App eine klare Nutzerfreundliche Tooltip und eine Hilfe. [...] Alles
auf einmal."): deckt den Installer-Assistenten ab, den letzten der drei
GUI-Bereiche (Hauptfenster, Settings-/Hardware-Test-Dialog, Installer).

Bewusst OHNE tkinter-Import/Widget-Instanziierung - bootstrap/app.py's
eigener Modul-Docstring erklaert, dass dieses Modul absichtlich nicht
direkt ueber Unit-Tests, sondern ueber den echten PyInstaller-Build pro
Betriebssystem abgedeckt wird (tkinter/Xvfb sind in der normalen
Test-Umgebung nicht zuverlaessig vorhanden). Die eigentliche
Tooltip-Verdrahtung (welches Widget welchen Schluessel bekommt) wurde
stattdessen manuell mit echtem Tk-Rendering unter Xvfb in allen 9
Sprachen ueber 5 Bildschirme (Willkommen, Modus, Zugangsdaten,
Einzel-Zugangsdatum, Abschluss) verifiziert - dieser Test deckt nur den
tkinter-freien Teil ab: dass die i18n-Werte selbst vollstaendig,
uebersetzt und formatierbar sind.
"""

from __future__ import annotations

from ui.i18n_data import CATALOGUES

NEW_KEYS = [
    "bootstrap.help.back_button",
    "bootstrap.help.next_button",
    "bootstrap.help.cancel_button",
    "bootstrap.help.language_combo",
    "bootstrap.help.mode_online_radio",
    "bootstrap.help.mode_local_radio",
    "bootstrap.help.gpu_continue_local_button",
    "bootstrap.help.gpu_switch_online_button",
    "bootstrap.help.credentials_checkbox",
    "bootstrap.help.credentials_skip_all_button",
    "bootstrap.help.credentials_continue_button",
    "bootstrap.help.credential_open_signup_button",
    "bootstrap.help.credential_key_entry",
    "bootstrap.help.credential_save_button",
    "bootstrap.help.finish_close_button",
    "bootstrap.help.finish_launch_button",
]


def test_bootstrap_help_keys_translated_for_all_nine_locales() -> None:
    assert len(NEW_KEYS) == 16
    for code, catalogue in CATALOGUES.items():
        for key in NEW_KEYS:
            assert key in catalogue, f"{code}: missing key {key}"
            assert catalogue[key].strip(), f"{code}: empty value for {key}"


def test_credentials_checkbox_key_is_formattable_with_provider_placeholder() -> None:
    for code, catalogue in CATALOGUES.items():
        template = catalogue["bootstrap.help.credentials_checkbox"]
        rendered = template.format(provider="DeepL")
        assert "DeepL" in rendered, f"{code}: {{provider}} placeholder did not substitute"
        assert "{provider}" not in rendered


def test_bootstrap_help_texts_are_not_accidentally_english_copies() -> None:
    # Spot-check: guards against a translation step silently no-oping for
    # a couple of the longer, more distinctive keys.
    sample_keys = ["bootstrap.help.mode_online_radio", "bootstrap.help.credential_key_entry"]
    for code in set(CATALOGUES) - {"de", "en"}:
        for key in sample_keys:
            assert CATALOGUES[code][key] != CATALOGUES["en"][key], f"{code}.{key} looks untranslated"
