"""Plain-data half of the UI catalogue - split out of ui/i18n.py on
26.08.2026 so this module can be imported WITHOUT pulling in PySide6.

Why this exists: ui/i18n.py imports `PySide6.QtCore` at module level (for
LanguageManager's QObject/Signal), which meant even reading the plain
DE/EN string tables required Qt to be importable. The new webapp/ package
(local HTTP server + pywebview, see Backlog.md 26.08.2026 "lokaler Server
+ pywebview") must never import PySide6 - its process has no Qt event
loop and no reason to depend on it - so the catalogues themselves needed
to live somewhere Qt-free. LocaleInfo/LOCALES/DE/EN/CATALOGUES moved here
unchanged (byte-for-byte, only cut-and-pasted); ui/i18n.py now re-exports
them and adds only LanguageManager(QObject) on top, so every existing
import of `ui.i18n.DE`/`ui.i18n.CATALOGUES`/etc. keeps working unchanged
and the Qt app's behavior is unaffected by this split.
"""
from __future__ import annotations

from dataclasses import dataclass


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
    "field.ico_mode": "ICO-Dokument",
    "ico_mode.checkbox": "Seite-1-Bereich nicht übersetzen",
    "ico_mode.tooltip": (
        "Nur für den internen Dokumententyp ICO: schließt den Metadaten-"
        "bereich auf Seite 1 von der Übersetzung aus (bei Word: der Bereich "
        "vor der Trennlinie; bei PDF: erkannt anhand von Ankerbegriffen wie "
        "\"Issuer Address\"/\"Asset Matrix\") - unabhängig davon, ob dieser "
        "Bereich tatsächlich gefunden wird. Für alle anderen Dokumente "
        "deaktiviert lassen."
    ),
    "field.exclude_header": "Kopfzeile",
    "exclude_header.checkbox": "Wiederkehrende Kopfzeile nicht übersetzen",
    "exclude_header.tooltip": (
        "Erkennt automatisch Text, der nahe oben auf den meisten Seiten "
        "identisch (oder nur mit unterschiedlicher Seitenzahl) wiederkehrt, "
        "und schließt ihn von der Übersetzung aus. Wird nichts Passendes "
        "gefunden, ändert sich nichts."
    ),
    "field.exclude_footer": "Fußzeile",
    "exclude_footer.checkbox": "Wiederkehrende Fußzeile nicht übersetzen",
    "exclude_footer.tooltip": (
        "Wie bei der Kopfzeile, nur für wiederkehrenden Text nahe unten auf "
        "der Seite (z. B. Copyright-Zeile, Seitenzahl)."
    ),
    "field.ocr_engine": "OCR-Engine",
    "ocr_engine.tesseract": "Tesseract (lokal)",
    "ocr_engine.tesseract.unavailable": (
        "Tesseract wurde auf diesem System nicht gefunden. Bitte installieren "
        "(siehe README.md) - ohne installiertes Tesseract kann kein Text in "
        "Bildern erkannt werden."
    ),
    "ocr_engine.google_vision": "Google Cloud Vision (Cloud, Absatzerkennung)",
    "ocr_engine.google_vision.unavailable": (
        "Kein Google-API-Key konfiguriert. In den Einstellungen hinterlegen "
        "(derselbe Key wie für Google Translate, siehe README.md) oder eine "
        "andere OCR-Engine wählen."
    ),
    "ocr_engine.paddleocr": "PaddleOCR (lokal, Absatzerkennung)",
    "ocr_engine.paddleocr.unavailable": (
        "PaddleOCR ist nicht installiert (siehe requirements-paddleocr.txt) "
        "oder eine andere OCR-Engine wählen."
    ),
    # Generischer Fallback (23.08.2026) - falls jemals ein OCR-Engine-Key
    # ohne eigenen ".unavailable"-Eintrag registriert wird, siehe
    # ui/app.py::_update_ocr_engine_hint()/_start()'s ocr_engine_available()-
    # Check, die auf "ocr_engine.{key}.unavailable" mit Rückfall auf diesen
    # generischen Text zugreifen.
    "ocr_engine.unavailable": "Diese OCR-Engine ist auf diesem System nicht verfügbar.",
    "field.inpainting_backend": "Rückschreibe-Methode",
    "inpainting_backend.box_overlay": "Box-Overlay (Fläche überdecken)",
    "inpainting_backend.cv_inpainting": "Klassisches CPU-Inpainting (Hintergrund rekonstruieren)",
    "inpainting_backend.gpu_inpainting": "KI-Inpainting lokal (GPU, LaMa)",
    "inpainting_backend.unavailable": (
        "Für diese Methode wurde keine ausreichend starke CUDA-GPU gefunden "
        "(siehe requirements-gpu.txt) - bitte eine andere Rückschreibe-"
        "Methode wählen."
    ),
    "source_language.placeholder": "optional / automatisch",
    "protected.placeholder": "Ein geschützter Begriff pro Zeile",
    "config.group": "Auftrag konfigurieren",
    "analysis.group": "Analyse und Kostenkontrolle",
    "analysis.required": "Vor dem Start ist eine Analyse erforderlich.",
    "analysis.button": "Dokument analysieren und Kosten schätzen",
    "analysis.running": "Analyse läuft …",
    "analysis.checked": "Analyse und Kostenschätzung geprüft",
    "analysis.failed": "Analyse fehlgeschlagen.",
    "analysis.no_warnings": "Keine Analysewarnungen.",
    "analysis.within": "innerhalb",
    "analysis.exceeded": "ÜBERSCHRITTEN",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} Textzeichen · {images} eingebettete/Bilddateien<br>Lokale Schätzung ({provider}): Monatsverbrauch {usage:,} / Freikontingent {free:,} Zeichen · Schätzung ${cost:.2f}<br>Lauflimit {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Live-Kontingent (DeepL, gerade abgerufen):</b> {used:,} von {limit:,} Zeichen verbraucht, {remaining:,} verbleibend.",
    "analysis.live_quota_unlimited": "<b>Live-Kontingent (DeepL, gerade abgerufen):</b> {used:,} Zeichen verbraucht, Konto meldet kein Limit.",
    "unit.pages": "Seiten", "unit.slides": "Folien", "unit.paragraphs": "Absätze", "unit.images": "Bilder",
    "warning.scan_pdf": "Bild-/Scan-PDF erkannt: OCR ist für den Dokumenttext erforderlich.",
    "warning.image_cost_unknown": "OCR-Zeichen und Bildübersetzungskosten sind erst nach der OCR bekannt.",
    "warning.image_selection_later": "Die konkrete Bildauswahl erfolgt nach der Analyse in einer späteren UI-Ausbaustufe.",
    "warning.live_quota_unavailable": "Live-Kontingent bei DeepL gerade nicht abrufbar (kein Schlüssel, offline, oder API-Fehler) – es wird die lokale Schätzung verwendet.",
    "start.button": "Übersetzung starten",
    "start.pending": "Für diesen Modus ist der Start noch nicht angebunden (siehe RoadMap.md).",
    "start.ready": "Bereit zum Start.",
    "start.blocked_running": "Ein Lauf ist bereits aktiv.",
    "start.blocked_mode": "Für diesen Modus ist der Start noch nicht angebunden (siehe RoadMap.md) – nur „Präsentation übersetzen“ ist bereits verbunden.",
    "start.blocked_no_analysis": "Bitte zuerst „Dokument analysieren und Kosten schätzen“ ausführen.",
    "start.blocked_not_confirmed": "Bitte die Checkbox „Analyse und Kostenschätzung geprüft“ aktivieren.",
    "dialog.choose_output_dir": "Zielordner wählen",
    "dialog.confirm_run": "Übersetzung starten",
    "start.confirm_summary": "Es werden schätzungsweise {characters:,} Zeichen an {provider} gesendet (geschätzte Kosten ${cost:.2f}).\nZieldatei: {destination}\n\nJetzt starten?",
    "start.confirm_summary_images": "Es werden schätzungsweise {characters:,} Zeichen an {provider} gesendet (geschätzte Kosten ${cost:.2f}) für {count} Bild(er).\nZielordner: {folder}\n\nJetzt starten?",
    "job.group": "Lauf und Ergebnis",
    "job.idle": "Noch kein Lauf gestartet.",
    "job.running": "Übersetzung läuft …",
    "job.progress_prefix": "Verarbeite: {location}",
    "job.progress_count": "{processed} von {total} Absätzen verarbeitet",
    "job.progress_count_files": "{processed} von {total} Bildern verarbeitet",
    "job.stats_summary": "{translated} übersetzt · {skipped} übersprungen · {failed} fehlgeschlagen · {chars:,} Zeichen gesendet",
    "job.cancel": "Abbrechen",
    "job.cancel_requested": "Abbruch angefordert – wird nach dem laufenden API-Aufruf gestoppt …",
    "job.result_summary": "Fertig: {translated} übersetzt, {skipped} übersprungen, {failed} fehlgeschlagen, {chars:,} Zeichen gesendet.\nAusgabedatei: {output}\nQA-Bericht: {report}",
    "job.result_summary_images": "Fertig: {files} Bild(er) verarbeitet, {translated} Textregionen übersetzt, {failed} fehlgeschlagen, {chars:,} Zeichen gesendet.\nAusgabeordner: {output_dir}\nJe Bild liegt eine eigene QA-Bericht-Datei im Ausgabeordner.",
    "job.result_cancelled_suffix": "\nHinweis: Lauf wurde abgebrochen – dies ist ein Teilergebnis, bereits übersetzte Inhalte wurden gespeichert.",
    "job.overflow_none": "Keine neuen Überlaufrisiken gefunden.",
    "job.overflow_count": "{count} Überlaufhinweis(e) im QA-Bericht – bitte manuell in PowerPoint/Impress prüfen.",
    "job.pdf_overflow_none": "Kein Block musste beim Einfügen wachsen oder schrumpfen.",
    "job.pdf_overflow_count": "{count} Block/Blöcke musste(n) wachsen oder schrumpfen, um zu passen – bitte im PDF stichprobenartig prüfen.",
    "job.open_folder": "Ordner öffnen",
    "job.open_report": "QA-Bericht öffnen",
    # Bild-Modus im Webapp-Frontend (Schritt 7, 26.08.2026): pro Bild wird
    # sein eigener QA-Bericht direkt inline ein-/ausgeblendet statt extern
    # geöffnet (job.open_report/QDesktopServices bleibt der Qt-App
    # vorbehalten). "job.open_folder" (oben) wurde ursprünglich nur von
    # der Qt-App verwendet, seit der Nachbesserung vom 26.08.2026 (realer
    # Nutzer-Feedback: "Es fehlt auch noch ein Button um den Zielordner
    # ... zu öffnen.") aber auch vom Webapp-Frontend wiederverwendet -
    # siehe webapp/__main__.py::Api.open_folder() und app.js's
    # runOpenOutputFolder(). Von der Qt-App nicht verwendet,
    # genau wie schon dialog.choose_images/job.cancel usw.
    "job.open_folder_failed": "Ordner konnte nicht geöffnet werden.",
    "job.show_report": "QA-Bericht anzeigen",
    "job.hide_report": "QA-Bericht ausblenden",
    "job.report_load_error": "QA-Bericht konnte nicht geladen werden.",
    "job.correct_translation": "Übersetzung korrigieren",
    # Bild-Modus-Korrektur-Übergabe (Schritt 8, 26.08.2026, siehe
    # webapp/review_bridge.py) - der Bearbeitungs-Dialog selbst läuft in
    # einem separaten Fenster/Tab (image_translate_cli/review_server.py's
    # eigene, unveränderte Seite), diese Statuszeile begleitet nur das
    # Warten darauf hier im Hauptfenster. Von der Qt-App nicht verwendet
    # (dort blockiert stattdessen der modale ImageCorrectionDialog selbst).
    "job.correction_starting": "Korrektur wird gestartet …",
    "job.correction_opened": "Korrektur-Fenster geöffnet - dort bearbeiten, dann „Anwenden“ oder „Abbrechen“ klicken.",
    "job.correction_applied": "Korrektur angewendet.",
    "job.correction_cancelled": "Korrektur abgebrochen.",
    "job.correction_timeout": "Korrektur-Zeitüberschreitung - keine Rückmeldung aus dem Korrektur-Fenster.",
    "job.correction_failed": "Korrektur fehlgeschlagen: {error}",
    "job.correction_error": "Korrektur konnte nicht gestartet werden.",
    "job.failed_title": "Übersetzung fehlgeschlagen",
    "correction.title": "PDF-Übersetzung korrigieren",
    "correction.hint": "Wähle unten eine Zeile aus und bearbeite ihre Übersetzung im Editor darunter. Mit Fett/Kursiv/Unterstrichen (auch per Strg+B/Strg+I/Strg+U) kannst du die Formatierung anpassen – auch bearbeitete Zeilen behalten dabei ihre Formatierung.",
    "correction.column_page": "Seite",
    "correction.column_original": "Original",
    "correction.column_translation": "Übersetzung",
    "correction.editor_label": "Übersetzung bearbeiten:",
    "correction.bold": "Fett",
    "correction.italic": "Kursiv",
    "correction.underline": "Unterstrichen",
    "correction.bold_tooltip": "Fett (Strg+B)",
    "correction.italic_tooltip": "Kursiv (Strg+I)",
    "correction.underline_tooltip": "Unterstrichen (Strg+U)",
    "correction.apply": "Anwenden und speichern",
    "correction.close": "Schließen",
    "correction.applying": "Wird angewendet …",
    "correction.success": "{count} Block/Blöcke aktualisiert und in {output} gespeichert.",
    "correction.failed": "Korrektur fehlgeschlagen: {error}",
    "image_correction.title": "Bildübersetzung korrigieren",
    "image_correction.hint": "Wähle unten eine Zeile aus und bearbeite ihre Übersetzung im Editor darunter.",
    "image_correction.canvas_hint": "Im Bild links kannst Du die Box einer Zeile per Ziehen verschieben. Wähle die Zeile aus, um an ihrer unteren rechten Ecke zu ziehen und sie in der Größe zu ändern. Mit Strg+Mausrad oder den Zoom-Knöpfen kannst Du ins Bild hinein- und herauszoomen; der Dialog lässt sich auch maximieren.",
    "image_correction.reset_geometry": "Position/Größe zurücksetzen",
    "image_correction.zoom_in": "Vergrößern (+)",
    "image_correction.zoom_out": "Verkleinern (−)",
    "image_correction.zoom_reset": "Ansicht anpassen",
    "image_correction.add_region": "Neue Box hinzufügen",
    "image_correction.add_region_hint": "Ziehe im Bild einen Bereich auf, um dort eine neue Box mit eigenem Text hinzuzufügen.",
    "image_correction.show_original": "Original anzeigen",
    "image_correction.manual_region_label": "(manuell hinzugefügt, keine OCR-Erkennung)",
    "image_correction.manual_region_added": "Neue Box hinzugefügt - bitte Übersetzung im Editor eintragen.",
    "image_correction.column_original": "Original",
    "image_correction.column_translation": "Übersetzung",
    "image_correction.editor_label": "Übersetzung bearbeiten:",
    "image_correction.apply": "Anwenden und speichern",
    "image_correction.close": "Schließen",
    "image_correction.applying": "Wird angewendet …",
    "image_correction.success": "{count} Region(en) aktualisiert und in {output} gespeichert.",
    "image_correction.failed": "Korrektur fehlgeschlagen: {error}",
    "image_correction.choose_file_title": "Datei zum Korrigieren wählen",
    "image_correction.choose_file_label": "Welche Datei aus diesem Lauf soll korrigiert werden?",
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
    "provider.missing_key": "Kein API-Schlüssel für „{provider}“ hinterlegt. <a href=\"settings\">Jetzt einrichten</a>",
    "provider.missing_key_dialog": "Für den Anbieter „{provider}“ ist kein API-Schlüssel hinterlegt. Ohne Schlüssel schlägt jeder Übersetzungsaufruf fehl.",
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
    "field.ico_mode": "ICO document",
    "ico_mode.checkbox": "Skip page-1 region",
    "ico_mode.tooltip": (
        "Internal ICO document type only: excludes the page-1 metadata "
        "block from translation (Word: the block in front of the "
        "separator line; PDF: detected via anchor terms like "
        "\"Issuer Address\"/\"Asset Matrix\") - regardless of whether that "
        "block is actually found. Leave disabled for every other document."
    ),
    "field.exclude_header": "Header",
    "exclude_header.checkbox": "Don't translate recurring header",
    "exclude_header.tooltip": (
        "Automatically detects text that repeats near the top of most "
        "pages (identical, or only differing by a page number) and "
        "excludes it from translation. If nothing matching is found, "
        "nothing changes."
    ),
    "field.exclude_footer": "Footer",
    "exclude_footer.checkbox": "Don't translate recurring footer",
    "exclude_footer.tooltip": (
        "Same as the header option, for text that repeats near the bottom "
        "of the page (e.g. a copyright line, page number)."
    ),
    "field.ocr_engine": "OCR engine",
    "ocr_engine.tesseract": "Tesseract (local)",
    "ocr_engine.tesseract.unavailable": (
        "Tesseract was not found on this system. Please install it (see "
        "README.md) - text in images cannot be recognized without an "
        "installed Tesseract."
    ),
    "ocr_engine.google_vision": "Google Cloud Vision (cloud, paragraph detection)",
    "ocr_engine.google_vision.unavailable": (
        "No Google API key configured. Set one in Settings (the same key "
        "used for Google Translate, see README.md) or choose a different "
        "OCR engine."
    ),
    "ocr_engine.paddleocr": "PaddleOCR (local, paragraph detection)",
    "ocr_engine.paddleocr.unavailable": (
        "PaddleOCR is not installed (see requirements-paddleocr.txt) or "
        "choose a different OCR engine."
    ),
    "ocr_engine.unavailable": "This OCR engine is not available on this system.",
    "field.inpainting_backend": "Rewrite method",
    "inpainting_backend.box_overlay": "Box overlay (cover the area)",
    "inpainting_backend.cv_inpainting": "Classic CPU inpainting (reconstruct background)",
    "inpainting_backend.gpu_inpainting": "AI inpainting, local (GPU, LaMa)",
    "inpainting_backend.unavailable": (
        "No sufficiently strong CUDA GPU was found for this method (see "
        "requirements-gpu.txt) - please choose a different rewrite method."
    ),
    "source_language.placeholder": "optional / automatic",
    "protected.placeholder": "One protected term per line",
    "config.group": "Configure job",
    "analysis.group": "Analysis and cost control",
    "analysis.required": "Analysis is required before starting.",
    "analysis.button": "Analyze document and estimate cost",
    "analysis.running": "Analysis in progress …",
    "analysis.checked": "I reviewed the analysis and cost estimate",
    "analysis.failed": "Analysis failed.",
    "analysis.no_warnings": "No analysis warnings.",
    "analysis.within": "within limit",
    "analysis.exceeded": "EXCEEDED",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} text characters · {images} embedded/image files<br>Local estimate ({provider}): monthly usage {usage:,} / free allowance {free:,} characters · estimate ${cost:.2f}<br>Run limit {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Live quota (DeepL, just checked):</b> {used:,} of {limit:,} characters used, {remaining:,} remaining.",
    "analysis.live_quota_unlimited": "<b>Live quota (DeepL, just checked):</b> {used:,} characters used, account reports no limit.",
    "unit.pages": "pages", "unit.slides": "slides", "unit.paragraphs": "paragraphs", "unit.images": "images",
    "warning.scan_pdf": "Image/scanned PDF detected: OCR is required for the document text.",
    "warning.image_cost_unknown": "OCR characters and image translation costs are unknown until OCR completes.",
    "warning.image_selection_later": "Individual image selection will follow the analysis in a later UI iteration.",
    "warning.live_quota_unavailable": "DeepL's live quota isn't reachable right now (no key, offline, or an API error) - using the local estimate instead.",
    "start.button": "Start translation",
    "start.pending": "Execution is not yet connected for this mode (see RoadMap.md).",
    "start.ready": "Ready to start.",
    "start.blocked_running": "A run is already in progress.",
    "start.blocked_mode": "Execution is not yet connected for this mode (see RoadMap.md) - only \"Translate presentation\" is wired up so far.",
    "start.blocked_no_analysis": "Run \"Analyze document and estimate cost\" first.",
    "start.blocked_not_confirmed": "Please tick \"I reviewed the analysis and cost estimate\".",
    "dialog.choose_output_dir": "Choose output folder",
    "dialog.confirm_run": "Start translation",
    "start.confirm_summary": "About to send an estimated {characters:,} characters to {provider} (estimated cost ${cost:.2f}).\nOutput file: {destination}\n\nStart now?",
    "start.confirm_summary_images": "About to send an estimated {characters:,} characters to {provider} (estimated cost ${cost:.2f}) for {count} image(s).\nOutput folder: {folder}\n\nStart now?",
    "job.group": "Run and result",
    "job.idle": "No run started yet.",
    "job.running": "Translation running …",
    "job.progress_prefix": "Processing: {location}",
    "job.progress_count": "{processed} of {total} paragraphs processed",
    "job.progress_count_files": "{processed} of {total} images processed",
    "job.stats_summary": "{translated} translated · {skipped} skipped · {failed} failed · {chars:,} characters sent",
    "job.cancel": "Cancel",
    "job.cancel_requested": "Cancellation requested – will stop after the current API call …",
    "job.result_summary": "Done: {translated} translated, {skipped} skipped, {failed} failed, {chars:,} characters sent.\nOutput file: {output}\nQA report: {report}",
    "job.result_summary_images": "Done: {files} image(s) processed, {translated} text regions translated, {failed} failed, {chars:,} characters sent.\nOutput folder: {output_dir}\nEach image has its own QA report file in the output folder.",
    "job.result_cancelled_suffix": "\nNote: the run was cancelled – this is a partial result, already-translated content was saved.",
    "job.overflow_none": "No new overflow risks found.",
    "job.overflow_count": "{count} overflow note(s) in the QA report – please review manually in PowerPoint/Impress.",
    "job.pdf_overflow_none": "No block needed to grow or shrink while inserting.",
    "job.pdf_overflow_count": "{count} block(s) needed to grow or shrink to fit – please spot-check the PDF.",
    "job.open_folder": "Open folder",
    "job.open_report": "Open QA report",
    # Images mode in the webapp frontend (Schritt 7, 26.08.2026) - see the
    # matching German comment above for why this differs from the Qt app.
    "job.open_folder_failed": "Could not open the folder.",
    "job.show_report": "Show QA report",
    "job.hide_report": "Hide QA report",
    "job.report_load_error": "Could not load QA report.",
    "job.correct_translation": "Correct translation",
    # Images-mode correction handoff (Schritt 8, 26.08.2026) - see the
    # matching German comment above for why this differs from the Qt app.
    "job.correction_starting": "Starting correction …",
    "job.correction_opened": "Correction window opened - edit there, then click \"Apply\" or \"Cancel\".",
    "job.correction_applied": "Correction applied.",
    "job.correction_cancelled": "Correction cancelled.",
    "job.correction_timeout": "Correction timed out - no response from the correction window.",
    "job.correction_failed": "Correction failed: {error}",
    "job.correction_error": "Could not start the correction.",
    "job.failed_title": "Translation failed",
    "correction.title": "Correct PDF translation",
    "correction.hint": "Select a row below and edit its translation in the editor beneath the table. Use Bold/Italic/Underline (or Ctrl+B/Ctrl+I/Ctrl+U) to adjust formatting – edited rows keep their formatting too.",
    "correction.column_page": "Page",
    "correction.column_original": "Original",
    "correction.column_translation": "Translation",
    "correction.editor_label": "Edit translation:",
    "correction.bold": "Bold",
    "correction.italic": "Italic",
    "correction.underline": "Underline",
    "correction.bold_tooltip": "Bold (Ctrl+B)",
    "correction.italic_tooltip": "Italic (Ctrl+I)",
    "correction.underline_tooltip": "Underline (Ctrl+U)",
    "correction.apply": "Apply and save",
    "correction.close": "Close",
    "correction.applying": "Applying …",
    "correction.success": "{count} block(s) updated and saved to {output}.",
    "correction.failed": "Correction failed: {error}",
    "image_correction.title": "Correct image translation",
    "image_correction.hint": "Select a row below and edit its translation in the editor beneath the table.",
    "image_correction.canvas_hint": "In the image on the left you can drag a row's box to move it. Select the row to drag its bottom-right corner and resize it. Use Ctrl+scroll wheel or the zoom buttons to zoom in/out; the dialog can also be maximized.",
    "image_correction.reset_geometry": "Reset position/size",
    "image_correction.zoom_in": "Zoom in (+)",
    "image_correction.zoom_out": "Zoom out (−)",
    "image_correction.zoom_reset": "Fit to view",
    "image_correction.add_region": "Add new box",
    "image_correction.add_region_hint": "Drag an area on the image to add a new box with its own text there.",
    "image_correction.show_original": "Show original",
    "image_correction.manual_region_label": "(added manually, no OCR match)",
    "image_correction.manual_region_added": "New box added - enter its translation in the editor.",
    "image_correction.column_original": "Original",
    "image_correction.column_translation": "Translation",
    "image_correction.editor_label": "Edit translation:",
    "image_correction.apply": "Apply and save",
    "image_correction.close": "Close",
    "image_correction.applying": "Applying …",
    "image_correction.success": "{count} region(s) updated and saved to {output}.",
    "image_correction.failed": "Correction failed: {error}",
    "image_correction.choose_file_title": "Choose file to correct",
    "image_correction.choose_file_label": "Which file from this run should be corrected?",
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
    "provider.missing_key": "No API key configured for \"{provider}\". <a href=\"settings\">Set it up now</a>",
    "provider.missing_key_dialog": "No API key is configured for the \"{provider}\" provider. Every translation call will fail without one.",
    "dialog.check_input": "Check input",
    "dialog.analysis": "Analysis",
    "dialog.choose_images": "Select images",
    "dialog.choose_document": "Select document",
}

CATALOGUES = {"de": DE, "en": EN}
