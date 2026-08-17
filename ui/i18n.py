"""Small runtime UI catalogue with prepared future locales."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class LocaleInfo:
    code: str
    native_name: str
    available: bool


LOCALES = (
    LocaleInfo("de", "Deutsch", True),
    LocaleInfo("en", "English", True),
    LocaleInfo("fr", "Français", False),
    LocaleInfo("es", "Español", False),
    LocaleInfo("it", "Italiano", False),
    LocaleInfo("nl", "Nederlands", False),
    LocaleInfo("fi", "Suomi", False),
    LocaleInfo("hr", "Hrvatski", False),
    LocaleInfo("ru", "Русский", False),
)


DE = {
    "app.title": "Document Translator",
    "mode.pdf": "PDF übersetzen",
    "mode.presentation": "Präsentation (PowerPoint/Impress) übersetzen",
    "mode.word": "Word/Writer übersetzen",
    "mode.images": "Einzelne Bilder übersetzen",
    "source.none": "Keine Datei gewählt",
    "source.choose": "Datei auswählen …",
    "image.none": "Eingebettete Bilder nicht übersetzen",
    "image.selected": "Bilder später einzeln auswählen",
    "image.all": "Alle eingebetteten Bilder übersetzen",
    "field.mode": "Vorgang",
    "field.source": "Quelle",
    "field.images": "Bilder im Dokument",
    "field.provider": "Übersetzungsanbieter",
    "field.source_language": "Ausgangssprache",
    "field.target_language": "Zielsprache",
    "field.protected_terms": "Geschützte Begriffe",
    "source_language.placeholder": "optional / automatisch",
    "protected.placeholder": "Ein geschützter Begriff pro Zeile",
    "analysis.group": "Analyse und Kostenkontrolle",
    "analysis.required": "Vor dem Start ist eine Analyse erforderlich.",
    "analysis.button": "Dokument analysieren und Kosten schätzen",
    "analysis.running": "Analyse läuft …",
    "analysis.checked": "Analyse und Kostenschätzung geprüft",
    "analysis.failed": "Analyse fehlgeschlagen.",
    "analysis.no_warnings": "Keine Analysewarnungen.",
    "analysis.within": "innerhalb",
    "analysis.exceeded": "ÜBERSCHRITTEN",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} Textzeichen · {images} eingebettete/Bilddateien<br>Monatsverbrauch {usage:,} / Freikontingent {free:,} Zeichen · Schätzung ${cost:.2f}<br>Lauflimit {limit:,}: {limit_state}<br>{warnings}",
    "unit.pages": "Seiten", "unit.slides": "Folien", "unit.paragraphs": "Absätze", "unit.images": "Bilder",
    "warning.scan_pdf": "Bild-/Scan-PDF erkannt: OCR ist für den Dokumenttext erforderlich.",
    "warning.image_cost_unknown": "OCR-Zeichen und Bildübersetzungskosten sind erst nach der OCR bekannt.",
    "warning.image_selection_later": "Die konkrete Bildauswahl erfolgt nach der Analyse in einer späteren UI-Ausbaustufe.",
    "start.button": "Übersetzung starten",
    "start.pending": "Die Ausführung wird im nächsten Implementierungsschritt angebunden.",
    "settings.button": "Einstellungen …",
    "settings.title": "Einstellungen",
    "settings.language": "Oberflächensprache",
    "settings.prepared": "vorbereitet",
    "settings.provider": "Anbieter",
    "settings.credentials": "Zugangsdaten",
    "settings.new_key": "Neuer API-Schlüssel",
    "settings.key_placeholder": "Wird nie angezeigt oder protokolliert",
    "settings.storage": "Speicherort",
    "settings.environment": "Umgebungsvariable (nur diese Sitzung)",
    "settings.keyring": "OS-Keyring",
    "settings.both": "Beides",
    "settings.run_limit": "Kostenlimit pro Lauf (Zeichen)",
    "settings.save_key": "API-Schlüssel speichern/ersetzen",
    "settings.session_note": "Hinweis: Die Umgebungsvariable ist in dieser Version nicht dauerhaft.",
    "credentials.title": "Zugangsdaten",
    "credentials.saved": "API-Schlüssel wurde gespeichert.",
    "credential.environment": "Umgebungsvariable (Sitzung)", "credential.keyring": "OS-Keyring", "credential.missing": "Nicht eingerichtet",
    "dialog.check_input": "Eingaben prüfen",
    "dialog.analysis": "Analyse",
    "dialog.choose_images": "Bilder auswählen",
    "dialog.choose_document": "Dokument auswählen",
}

EN = {
    "app.title": "Document Translator",
    "mode.pdf": "Translate PDF",
    "mode.presentation": "Translate presentation (PowerPoint/Impress)",
    "mode.word": "Translate Word/Writer document",
    "mode.images": "Translate individual images",
    "source.none": "No file selected",
    "source.choose": "Select file …",
    "image.none": "Do not translate embedded images",
    "image.selected": "Select images individually later",
    "image.all": "Translate all embedded images",
    "field.mode": "Task",
    "field.source": "Source",
    "field.images": "Images in document",
    "field.provider": "Translation provider",
    "field.source_language": "Source language",
    "field.target_language": "Target language",
    "field.protected_terms": "Protected terms",
    "source_language.placeholder": "optional / automatic",
    "protected.placeholder": "One protected term per line",
    "analysis.group": "Analysis and cost control",
    "analysis.required": "Analysis is required before starting.",
    "analysis.button": "Analyze document and estimate cost",
    "analysis.running": "Analysis in progress …",
    "analysis.checked": "I reviewed the analysis and cost estimate",
    "analysis.failed": "Analysis failed.",
    "analysis.no_warnings": "No analysis warnings.",
    "analysis.within": "within limit",
    "analysis.exceeded": "EXCEEDED",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} text characters · {images} embedded/image files<br>Monthly usage {usage:,} / free allowance {free:,} characters · estimate ${cost:.2f}<br>Run limit {limit:,}: {limit_state}<br>{warnings}",
    "unit.pages": "pages", "unit.slides": "slides", "unit.paragraphs": "paragraphs", "unit.images": "images",
    "warning.scan_pdf": "Image/scanned PDF detected: OCR is required for the document text.",
    "warning.image_cost_unknown": "OCR characters and image translation costs are unknown until OCR completes.",
    "warning.image_selection_later": "Individual image selection will follow the analysis in a later UI iteration.",
    "start.button": "Start translation",
    "start.pending": "Execution will be connected in the next implementation step.",
    "settings.button": "Settings …",
    "settings.title": "Settings",
    "settings.language": "Interface language",
    "settings.prepared": "prepared",
    "settings.provider": "Provider",
    "settings.credentials": "Credentials",
    "settings.new_key": "New API key",
    "settings.key_placeholder": "Never displayed or logged",
    "settings.storage": "Storage",
    "settings.environment": "Environment variable (this session only)",
    "settings.keyring": "OS keyring",
    "settings.both": "Both",
    "settings.run_limit": "Cost limit per run (characters)",
    "settings.save_key": "Save/replace API key",
    "settings.session_note": "Note: the environment variable is not persistent in this version.",
    "credentials.title": "Credentials",
    "credentials.saved": "API key was saved.",
    "credential.environment": "Environment variable (session)", "credential.keyring": "OS keyring", "credential.missing": "Not configured",
    "dialog.check_input": "Check input",
    "dialog.analysis": "Analysis",
    "dialog.choose_images": "Select images",
    "dialog.choose_document": "Select document",
}

CATALOGUES = {"de": DE, "en": EN}


class LanguageManager(QObject):
    changed = Signal(str)

    def __init__(self, language: str = "de") -> None:
        super().__init__()
        self.language = language if language in CATALOGUES else "de"

    def set_language(self, language: str) -> None:
        if language not in CATALOGUES or language == self.language:
            return
        self.language = language
        self.changed.emit(language)

    def text(self, key: str, **values: object) -> str:
        template = CATALOGUES[self.language].get(key, DE.get(key, key))
        return template.format(**values) if values else template
