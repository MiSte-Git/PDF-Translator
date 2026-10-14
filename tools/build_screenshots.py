"""Build the user-manual screenshots (docs/screenshots/<lang>/*.png) in every
UI language - real renderings of the app and the setup wizard, no mockups.

14.10.2026 (Michael: "Kannst Du die Screenshots in jeder Sprache
erstellen?"): before this, every manual (docs/<lang>/manual.md) showed the
German UI. Now each language gets its own set; tools/build_manual.py then
builds the PDFs from them.

Two parts, because they need different toolkits:

    python tools/build_screenshots.py app        # PySide6, offscreen
    xvfb-run -a python tools/build_screenshots.py bootstrap   # tkinter

`app` needs the normal app environment (requirements.txt). `bootstrap`
needs a Python with tkinter and an X display (Xvfb is enough) plus
ImageMagick's `import` for the window capture. Optional trailing language
codes limit the run, e.g. `... app de en`.

The script re-runs itself in an isolated environment (empty temporary HOME
and XDG dirs, null keyring backend, no *_API_KEY/*_AUTH_KEY variables), so
neither real settings, saved API keys nor a real GPU-check marker of the
machine it runs on can end up in a screenshot - every language shows the
same, reproducible "fresh install" state.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = ROOT / "docs" / "screenshots"
LANGUAGES = ("de", "en", "fr", "es", "it", "nl", "fi", "hr", "ru")
_ISOLATED_FLAG = "DOCTRANSLATOR_SCREENSHOTS_ISOLATED"

# Fictional sample for the image-correction screenshot (no real user data):
# source lines, and their translation into each manual's language. The
# English manual shows a German source translated into English, every other
# manual an English source translated into its own language.
SAMPLE_EN = ("Quarterly Report", "Revenue increased by 12%", "compared to last year.")
SAMPLE_DE = ("Quartalsbericht", "Der Umsatz stieg um 12 %", "im Vergleich zum Vorjahr.")
SAMPLE_TRANSLATIONS = {
    "de": SAMPLE_DE,
    "en": SAMPLE_EN,
    "fr": ("Rapport trimestriel", "Le chiffre d'affaires a augmenté de 12 %", "par rapport à l'année précédente."),
    "es": ("Informe trimestral", "Los ingresos aumentaron un 12 %", "en comparación con el año anterior."),
    "it": ("Relazione trimestrale", "Il fatturato è aumentato del 12 %", "rispetto all'anno precedente."),
    "nl": ("Kwartaalrapport", "De omzet steeg met 12 %", "ten opzichte van vorig jaar."),
    "fi": ("Neljännesvuosiraportti", "Liikevaihto kasvoi 12 %", "edellisvuoteen verrattuna."),
    "hr": ("Tromjesečno izvješće", "Prihod je porastao za 12 %", "u odnosu na prethodnu godinu."),
    "ru": ("Квартальный отчёт", "Выручка выросла на 12 %", "по сравнению с прошлым годом."),
}


def _isolated_rerun() -> None:
    """Re-executes this script with a throwaway HOME/XDG environment (see
    the module docstring) unless that already happened."""
    if os.environ.get(_ISOLATED_FLAG):
        return
    home = Path(tempfile.mkdtemp(prefix="doctranslator-screenshots-"))
    env = {
        key: value
        for key, value in os.environ.items()
        if not (key.endswith("_API_KEY") or key.endswith("_AUTH_KEY"))
    }
    env.update(
        {
            _ISOLATED_FLAG: "1",
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Keyring",
            "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH", "")])),
        }
    )
    sys.exit(subprocess.call([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], env=env, cwd=str(ROOT)))


# --- app (PySide6) -----------------------------------------------------------


def _sample_image(path: Path, lines: tuple[str, str, str]) -> list[tuple[int, int, int, int]]:
    """Draws the fictional source image and returns each line's box."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (480, 260), (236, 236, 230))
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 456, 236), outline=(90, 90, 90), width=1)
    fonts = [
        ImageFont.truetype("DejaVuSans.ttf", 26),
        ImageFont.truetype("DejaVuSerif.ttf", 16),
        ImageFont.truetype("DejaVuSerif.ttf", 16),
    ]
    boxes = []
    y = 44
    for text, font in zip(lines, fonts):
        left, top, right, bottom = draw.textbbox((40, y), text, font=font)
        draw.text((40, y), text, fill=(20, 20, 20), font=font)
        boxes.append((left - 2, top - 3, right - left + 4, bottom - top + 6))
        y = bottom + 18
    image.save(path)
    return boxes


def _grab(widget, path: Path) -> None:
    from PySide6.QtWidgets import QApplication

    for _ in range(5):
        QApplication.processEvents()
    path.parent.mkdir(parents=True, exist_ok=True)
    widget.grab().save(str(path))


def build_app(languages: list[str]) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    import bootstrap.paths
    import ui.app as app_module

    # Same look as a real start (ui/app.py's main()): Fusion style, the
    # explicit palette and the app-wide stylesheet. DejaVu Sans 10 pt pins the
    # font, so the screenshots do not depend on the build machine's default
    # font (DejaVu Sans is also what tools/build_manual.py sets the PDFs in).
    app.setWindowIcon(QIcon(str(app_module.APP_ICON_PATH)))
    app.setFont(QFont("DejaVu Sans", 10))
    app_module.apply_explicit_palette(app)
    from pipeline.images.inpainting import TextReplacement
    from pipeline.images.ocr import OcrTextRegion
    from ui.i18n import LanguageManager
    from ui.image_correction_dialog import ImageCorrectionDialog
    from ui.models import TranslationMode

    work = Path(tempfile.mkdtemp(prefix="doctranslator-shots-work-"))
    bootstrap.paths.language_marker_file = lambda: work / "language.json"

    for code in languages:
        out = OUT_ROOT / code
        window = app_module.MainWindow()
        window.language.set_language(code)
        # The main window restores the last mode from QSettings - which is
        # the previous language's "Bilder" screenshot from this very run.
        window.mode.setCurrentIndex(window.mode.findData(TranslationMode.PDF))
        window.image_mode.setCurrentIndex(0)  # "Eingebettete Bilder nicht übersetzen"
        window.target_lang.setText("DE" if code == "en" else code.upper())
        window.resize(880, 820)
        window.show()
        _grab(window, out / "app_01_hauptfenster.png")

        window.mode.setCurrentIndex(window.mode.findData(TranslationMode.IMAGES))
        _grab(window, out / "app_02_bilder_modus.png")
        window.close()

        language = LanguageManager(code)
        settings_dialog = app_module.SettingsDialog(QSettings(str(work / f"settings-{code}.ini"), QSettings.IniFormat), language)
        settings_dialog.show()
        _grab(settings_dialog, out / "app_03_einstellungen.png")
        settings_dialog.close()

        hw_dialog = app_module.HardwareCheckDialog(language)
        hw_dialog.show()
        _grab(hw_dialog, out / "app_04_hardware_test.png")
        hw_dialog.close()

        source_lines = SAMPLE_DE if code == "en" else SAMPLE_EN
        source = work / f"sample-{code}.png"
        boxes = _sample_image(source, source_lines)
        replacements = [
            TextReplacement(
                region=OcrTextRegion(text=text, x=x, y=y, width=w, height=h, confidence=95.0),
                translated_text=translated,
            )
            for text, translated, (x, y, w, h) in zip(source_lines, SAMPLE_TRANSLATIONS[code], boxes)
        ]
        correction = ImageCorrectionDialog(language, source, work / f"sample-{code}-out.png", replacements)
        correction.resize(1000, 650)
        correction.show()
        _grab(correction, out / "app_05_bildkorrektur.png")
        correction.close()
        print(f"app screenshots: {code}")
    app.quit()


# --- bootstrap (tkinter) -----------------------------------------------------


def build_bootstrap(languages: list[str]) -> None:
    from bootstrap.app import BootstrapApp
    from bootstrap.controller import BootstrapController

    def capture(wizard, path: Path) -> None:
        wizard.update_idletasks()
        wizard.update()
        # Same idea as the original hand-made screenshots: the window cut
        # to its content instead of the fixed default height.
        height = wizard._container.winfo_reqheight() + 4
        wizard.geometry(f"500x{height}")
        for _ in range(3):
            wizard.update_idletasks()
            wizard.update()
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["import", "-window", wizard.wm_frame(), str(path)], check=True)

    for code in languages:
        out = OUT_ROOT / code
        controller = BootstrapController(app_source_dir=ROOT)
        controller.set_language(code)
        wizard = BootstrapApp(controller)
        wizard._show_welcome()
        capture(wizard, out / "01_sprache.png")
        wizard._show_mode()
        capture(wizard, out / "02_online_lokal.png")
        wizard._show_credentials()
        capture(wizard, out / "03_api_schluessel_auswahl.png")
        wizard._show_single_credential("deepl")
        capture(wizard, out / "04_api_schluessel_eingabe.png")
        wizard._show_finish()
        capture(wizard, out / "05_fertig.png")
        wizard.destroy()
        print(f"bootstrap screenshots: {code}")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("app", "bootstrap"):
        print(__doc__)
        return 2
    part, languages = argv[0], argv[1:] or list(LANGUAGES)
    unknown = [code for code in languages if code not in LANGUAGES]
    if unknown:
        print(f"Unknown language(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    _isolated_rerun()
    sys.path.insert(0, str(ROOT))
    if part == "app":
        build_app(languages)
    else:
        build_bootstrap(languages)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
