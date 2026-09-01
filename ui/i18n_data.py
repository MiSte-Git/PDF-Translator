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
        "Für diese Methode wurde keine CUDA-GPU gefunden (siehe "
        "requirements-gpu.txt) - bitte eine andere Rückschreibe-Methode "
        "wählen."
    ),
    "inpainting_backend.below_recommended_vram": (
        "Nur {vram_gb:.0f} GB Grafikspeicher erkannt (empfohlen: "
        "mindestens {min_gb:.0f} GB) - läuft eventuell, aber ohne Gewähr, "
        "besonders bei großen Bildern oder vielen Textstellen gleichzeitig."
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
    # 28.08.2026 (Runde 3) - Bedienelemente für Schriftgröße/Fett/
    # Zentriert im Korrektur-Dialog (siehe TextReplacement.render_font_size/
    # render_bold/render_centered, pipeline/images/inpainting.py) - real
    # user report, Backlog.md 28.08.2026: "Wenn ich etwas korrigiere,
    # muss es auch genauso korrigiert werden wie ich es im Viewer sehe."
    "image_correction.font_size_label": "Schriftgröße:",
    "image_correction.font_size_auto": "Automatisch",
    "image_correction.bold": "Fett",
    "image_correction.centered": "Zentriert",
    "image_correction.apply": "Anwenden und speichern",
    "image_correction.close": "Schließen",
    "image_correction.applying": "Wird angewendet …",
    "image_correction.success": "{count} Region(en) aktualisiert und in {output} gespeichert.",
    "image_correction.failed": "Korrektur fehlgeschlagen: {error}",
    "image_correction.choose_file_title": "Datei zum Korrigieren wählen",
    "image_correction.choose_file_label": "Welche Datei aus diesem Lauf soll korrigiert werden?",
    "update.available": "Update verfügbar: {version}",
    "update.confirm_title": "Update installieren?",
    "update.confirm_body": (
        "Eine neue Version ({version}) ist verfügbar. Jetzt herunterladen "
        "und installieren?"
    ),
    "update.installing": "Update wird installiert …",
    "update.success_title": "Update installiert",
    "update.success_body": (
        "Das Update wurde installiert. Bitte starte die Anwendung neu, "
        "damit die Änderungen wirksam werden."
    ),
    "update.failed_title": "Update fehlgeschlagen",
    "update.failed_body": (
        "Das Update konnte nicht installiert werden: {error}\n\n"
        "Die bisher installierte Version läuft unverändert weiter."
    ),
    "menu.help": "Hilfe",
    "menu.help.hw_check": "Hardware-Test anzeigen/wiederholen …",
    "menu.help.check_updates": "Nach Updates suchen …",
    "menu.help.about": "Über …",
    "about.body": "{app_name}\nVersion {version}",
    "update.check.no_update_title": "Kein Update verfügbar",
    "update.check.no_update_body": "Du verwendest bereits die neueste Version ({version}).",
    "update.check.failed_title": "Update-Prüfung fehlgeschlagen",
    "update.check.failed_body": "Es konnte nicht nach Updates gesucht werden: {error}",
    "hw_check.title": "Hardware-Test",
    "hw_check.note": (
        "Läuft die App nicht wie erwartet (z. B. beim lokalen "
        "KI-Inpainting), kannst du hier die Hardware erneut prüfen."
    ),
    "hw_check.recheck_button": "Erneut prüfen",
    "hw_check.checking": "Prüfe Hardware …",
    "hw_check.never_checked": (
        "Noch keine Hardware-Prüfung vorhanden. Klicke auf „Erneut "
        "prüfen“, um jetzt zu prüfen."
    ),
    "hw_check.not_found": (
        "Keine CUDA-GPU gefunden (zuletzt geprüft: {checked_at}). Lokales "
        "KI-Inpainting steht auf dieser Hardware nicht zur Verfügung - "
        "Cloud-Inpainting funktioniert unabhängig davon."
    ),
    "hw_check.found_ok": (
        "{name} mit {vram_gb:.0f} GB Grafikspeicher gefunden (zuletzt "
        "geprüft: {checked_at}). Erfüllt die Empfehlung von mindestens "
        "{min_gb:.0f} GB."
    ),
    "hw_check.found_below_recommended": (
        "{name} mit {vram_gb:.0f} GB Grafikspeicher gefunden (zuletzt "
        "geprüft: {checked_at}). Liegt unter der Empfehlung von "
        "{min_gb:.0f} GB - läuft eventuell, aber ohne Gewähr, besonders "
        "bei großen Bildern oder vielen Textstellen gleichzeitig."
    ),
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
    # PDFs zusammenführen/zwischeneinfügen (01.09.2026, Backlog.md
    # 26.08.2026) - eigenständiger Dialog, siehe ui/merge_dialog.py und
    # ui/merge_job.py's Modulkommentar dazu, warum dies NICHT über
    # TranslationRequest/self.mode läuft.
    "merge.button": "PDFs zusammenführen / einfügen …",
    "merge.title": "PDFs zusammenführen / einfügen",
    "merge.intro": (
        "Quelldateien in der gewünschten Reihenfolge zusammenstellen. Pro "
        "Datei kann optional eine Seitenauswahl angegeben werden (leer = "
        "ganze Datei) - dieselbe Datei mehrfach mit unterschiedlicher "
        "Seitenauswahl hinzufügen, um sie an einer bestimmten Stelle in "
        "eine andere Datei einzufügen."
    ),
    "merge.column_file": "Datei",
    "merge.column_pages": "Seiten",
    "merge.pages_placeholder": "alle",
    "merge.pages_tooltip": (
        "Leer = ganze Datei. Sonst z. B. \"1-3,5\" oder \"6-\" (Seite 6 bis "
        "zum Ende) oder \"-4\" (Anfang bis Seite 4). \"5-3\" fügt die "
        "Seiten 5,4,3 in dieser (umgekehrten) Reihenfolge ein."
    ),
    "merge.add_files": "Dateien hinzufügen …",
    "merge.remove_selected": "Entfernen",
    "merge.move_up": "Nach oben",
    "merge.move_down": "Nach unten",
    "merge.output_file_label": "Zieldatei",
    "merge.output_placeholder": "Zieldatei wählen …",
    "merge.choose_output_file": "Speichern unter …",
    "merge.start_button": "Zusammenführen starten",
    "merge.cancel_button": "Abbrechen",
    "merge.close_button": "Schließen",
    "merge.status_running": "Verarbeite: {message}",
    "merge.status_done": "Fertig: {pages} Seite(n) aus {files} Datei(en) geschrieben.",
    "merge.status_cancelled": "Abgebrochen (Teilergebnis gespeichert): {pages} Seite(n) geschrieben.",
    "merge.status_failed": "Fehlgeschlagen: {error}",
    "merge.error_dialog_choose_files": "PDF-Dateien auswählen",
    "merge.error_dialog_choose_output": "Zieldatei wählen",
    "merge.failed_title": "Zusammenführen fehlgeschlagen",
    # "Ordner durchsuchen" (01.09.2026, ui/merge_search_dialog.py) -
    # Michael: "Ordner mit 1000 oder mehr PDFs [...] nur bestimmte von
    # ihnen zusammenführen [...] Developer Name steht im oberen
    # geschützten Teil."
    "merge_search.button": "Ordner durchsuchen …",
    "merge_search.title": "PDFs im Ordner suchen",
    "merge_search.folder_label": "Ordner",
    "merge_search.folder_placeholder": "Ordner wählen …",
    "merge_search.choose_folder": "Ordner wählen …",
    "merge_search.choose_folder_dialog_title": "Ordner zum Durchsuchen wählen",
    "merge_search.recursive_checkbox": "Inkl. Unterordner",
    "merge_search.query_label": "Suchtext (nur ICO-Kopfbereich auf Seite 1)",
    "merge_search.query_placeholder": (
        "z. B. Firmenname des Developers – leer lassen für alle PDFs im Ordner"
    ),
    "merge_search.search_button": "Suchen",
    "merge_search.cancel_button": "Abbrechen",
    "merge_search.select_all": "Alle auswählen",
    "merge_search.select_none": "Keine auswählen",
    "merge_search.take_selected": "Ausgewählte übernehmen",
    "merge_search.close_button": "Schließen",
    "merge_search.status_running": "Durchsuche: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} Treffer von {scanned} durchsuchten PDF(s).",
    "merge_search.status_done_with_errors": (
        "{matches} Treffer von {scanned} durchsuchten PDF(s) ({errors} nicht lesbar)."
    ),
    "merge_search.status_cancelled": "Abgebrochen: {matches} Treffer von {scanned} durchsuchten PDF(s).",
    "merge_search.status_failed": "Fehlgeschlagen: {error}",
    "merge_search.error_missing_folder": "Bitte zuerst einen Ordner wählen.",
    "merge_search.failed_title": "Suche fehlgeschlagen",
    # Google-Drive-Ordnersuche (01.09.2026) - Michael: "Können wir eine
    # Google Drive Ordner durchsuchen?" Umschalter im selben Dialog statt
    # eigenem Fenster (siehe ui/merge_search_dialog.py's Docstring).
    "merge_search.source_local": "Lokaler Ordner",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Drive-Ordnerlink oder -ID",
    "merge_search.drive_folder_placeholder": "Freigabelink oder Ordner-ID einfügen …",
    "merge_search.drive_resolve_button": "Prüfen",
    "merge_search.drive_folder_unresolved": "Noch nicht geprüft.",
    "merge_search.drive_folder_resolved": "Ordner „{name}“ gefunden.",
    "merge_search.drive_folder_resolve_failed": "Fehlgeschlagen: {error}",
    "merge_search.drive_cache_label": "Cache-Ordner (Downloads bleiben hier erhalten)",
    "merge_search.drive_choose_cache": "Cache-Ordner wählen …",
    "merge_search.drive_choose_cache_dialog_title": "Ordner für heruntergeladene Treffer wählen",
    "merge_search.drive_credentials_label": "Google-OAuth-Zugangsdaten (einmalig, siehe docs/google_drive_setup.md)",
    "merge_search.drive_client_id_placeholder": "Client-ID",
    "merge_search.drive_client_secret_placeholder": "Client-Secret",
    "merge_search.drive_save_credentials": "Zugangsdaten speichern",
    "merge_search.drive_credentials_saved": "Zugangsdaten gespeichert.",
    "merge_search.drive_not_configured": "Noch keine Client-ID/Client-Secret hinterlegt.",
    "merge_search.drive_configured_not_connected": "Konfiguriert, aber noch nicht verbunden.",
    "merge_search.drive_connected": "Verbunden{account}.",
    "merge_search.drive_connect_button": "Mit Google verbinden",
    "merge_search.drive_disconnect_button": "Trennen",
    "merge_search.drive_connecting": "Öffne Browser zur Anmeldung …",
    "merge_search.drive_connect_failed": "Verbindung fehlgeschlagen: {error}",
    "merge_search.drive_error_missing_folder": "Bitte zuerst einen Drive-Ordner angeben und prüfen.",
    "merge_search.drive_error_missing_cache": "Bitte zuerst einen Cache-Ordner wählen.",
    "merge_search.drive_error_not_connected": "Bitte zuerst mit Google verbinden.",
    # DOCX zusammenführen/zwischeneinfügen (01.09.2026, Michael: "Jetzt noch
    # das ganze für *.docx.") - ui/word_merge_dialog.py, mirrors merge.*
    # above; nur die Strings, die inhaltlich vom PDF-Pendant abweichen
    # (Seitenkonzept, Datei-Endung, Batching-Zusammenfassung) sind eigene
    # Keys, alles Formatunabhängige (Knöpfe, Zieldatei-Auswahl, ...) nutzt
    # dieselben merge.*-Keys weiter - wie job.* bereits für PDF/Word/PPTX
    # gemeinsam genutzt wird.
    "word_merge.button": "DOCX-Dateien zusammenführen / einfügen …",
    "word_merge.title": "DOCX-Dateien zusammenführen / einfügen",
    "word_merge.intro": (
        "Quelldateien in der gewünschten Reihenfolge zusammenstellen - immer "
        "ganze Dateien (DOCX kennt anders als PDF keine feste Seitenzahl im "
        "Dateiformat selbst). Dieselbe Datei mehrfach hinzufügen, um sie an "
        "mehreren Stellen einzufügen. Ab mehr als 100 Dateien wird "
        "automatisch in Gruppen zusammengeführt (siehe Statuszeile nach dem "
        "Lauf)."
    ),
    "word_merge.status_done": (
        "Fertig: {segments} von {files} Datei(en) übernommen"
        "{batch_suffix}{warning_suffix}."
    ),
    "word_merge.status_cancelled": (
        "Abgebrochen (Teilergebnis gespeichert): {segments} Datei(en) übernommen"
        "{batch_suffix}{warning_suffix}."
    ),
    "word_merge.status_batch_suffix": " in {batches} Gruppen",
    "word_merge.status_warning_suffix": ", {count} übersprungen (siehe unten)",
    "word_merge.warnings_title": "Übersprungene Dateien:",
    "word_merge.error_dialog_choose_files": "DOCX-Dateien auswählen",
    # "Ordner durchsuchen" für DOCX (01.09.2026, ui/word_merge_search_dialog.py) -
    # gleiche Anforderung wie bei PDF, nur der ICO-Kopfbereich ist hier NICHT
    # an "Seite 1" gebunden (DOCX hat keine Seiten im Dateiformat) sondern an
    # die Absätze vor dem Trennelement (siehe pipeline/word/docx_engine.py's
    # extract_docx_ico_header_text()).
    "word_merge_search.title": "DOCX-Dateien im Ordner suchen",
    "word_merge_search.query_label": "Suchtext (nur ICO-Kopfbereich am Dokumentanfang)",
    "word_merge_search.query_placeholder": (
        "z. B. Firmenname des Developers – leer lassen für alle DOCX-Dateien im Ordner"
    ),
    "word_merge_search.status_done": "{matches} Treffer von {scanned} durchsuchten DOCX-Datei(en).",
    "word_merge_search.status_done_with_errors": (
        "{matches} Treffer von {scanned} durchsuchten DOCX-Datei(en) ({errors} nicht lesbar)."
    ),
    "word_merge_search.status_cancelled": "Abgebrochen: {matches} Treffer von {scanned} durchsuchten DOCX-Datei(en).",
    # Geführter Bootstrapper (01.09.2026, Konzeptdiskussion siehe Projekt-
    # Doc "deployment-strategie-bootstrapper-01-09-2026.md") - eigenes
    # eigenständiges tkinter-Programm (bootstrap/), nicht Teil der Qt-App,
    # nutzt aber dieselbe DE/EN-Kataloglogik hier statt eines zweiten
    # Textkatalogs (siehe dieses Dok "Mehrsprachigkeit"-Abschnitt für die
    # Begründung). Startsprache wird nach Systemsprache vorausgewählt,
    # Fallback Englisch (nicht Deutsch) bei nicht unterstützter
    # Systemsprache - bootstrap/system_lang.py.
    "bootstrap.window_title": "PDF-Translator einrichten",
    "bootstrap.back_button": "Zurück",
    "bootstrap.next_button": "Weiter",
    "bootstrap.cancel_button": "Abbrechen",
    "bootstrap.welcome_title": "Willkommen",
    "bootstrap.welcome_text": (
        "Dieser Assistent richtet PDF-Translator auf diesem Rechner ein - "
        "ganz ohne Kommandozeile. Er lädt die benötigten Komponenten "
        "herunter und legt am Ende einen Eintrag im Anwendungsmenü an."
    ),
    "bootstrap.language_label": "Sprache",
    "bootstrap.mode_title": "Online oder lokal?",
    "bootstrap.mode_intro": (
        "Wie soll übersetzt werden? Das lässt sich später in den "
        "Einstellungen jederzeit ändern."
    ),
    "bootstrap.mode_online_label": "Online (Cloud-Anbieter)",
    "bootstrap.mode_online_desc": (
        "Übersetzung läuft über einen externen Anbieter (DeepL, Google, "
        "OpenAI oder Grok). Dafür fallen laufende Kosten pro Übersetzung "
        "an, und es wird ein eigener API-Schlüssel des jeweiligen "
        "Anbieters benötigt - dazu gleich mehr. Empfohlen, wenn keine "
        "starke Grafikkarte vorhanden ist."
    ),
    "bootstrap.mode_local_label": "Lokal (auf dieser Grafikkarte)",
    "bootstrap.mode_local_desc": (
        "Übersetzung/Bildbearbeitung läuft direkt auf diesem Rechner, "
        "keine laufenden Kosten. Braucht aber eine ausreichend starke "
        "NVIDIA-Grafikkarte - wird im nächsten Schritt geprüft - und einen "
        "größeren einmaligen Download."
    ),
    "bootstrap.gpu_checking": "Grafikkarte wird geprüft …",
    "bootstrap.gpu_ok": (
        "Gefunden: {name} mit {vram_gb:.0f} GB Grafikspeicher - das reicht."
    ),
    "bootstrap.gpu_insufficient": (
        "Gefunden: {name} mit {vram_gb:.0f} GB Grafikspeicher - empfohlen "
        "sind mindestens {min_gb:.0f} GB. Lokal wird vermutlich sehr "
        "langsam sein."
    ),
    "bootstrap.gpu_not_found": (
        "Keine unterstützte NVIDIA-Grafikkarte gefunden. Lokal ist auf "
        "diesem Rechner nicht sinnvoll nutzbar."
    ),
    "bootstrap.gpu_mac_unsupported": (
        "Der lokale Modus wird auf dem Mac aktuell nicht unterstützt. "
        "Bitte stattdessen Online wählen."
    ),
    "bootstrap.gpu_continue_local_button": "Trotzdem lokal fortfahren",
    "bootstrap.gpu_switch_online_button": "Zu Online wechseln",
    "bootstrap.install_title": "Installation läuft",
    "bootstrap.install_step_venv": "Lege Arbeitsumgebung an …",
    "bootstrap.install_step_deps": "Installiere Komponenten ({name}) …",
    "bootstrap.install_step_source": "Lade Programmcode …",
    "bootstrap.install_step_shortcut": "Lege Anwendungsmenü-Eintrag an …",
    "bootstrap.install_failed_title": "Installation fehlgeschlagen",
    "bootstrap.install_failed": "Fehlgeschlagen: {error}",
    "bootstrap.credentials_title": "API-Schlüssel einrichten",
    "bootstrap.credentials_intro": (
        "Welche Anbieter möchtest du einrichten? Das lässt sich jederzeit "
        "überspringen und später in den Einstellungen der App nachholen."
    ),
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": (
        "Schnelle Selbstbedienungs-Anmeldung. Kostenloses Kontingent "
        "vorhanden, danach kostenpflichtig."
    ),
    "bootstrap.credentials_explain_google": (
        "Braucht ein Google-Cloud-Projekt mit hinterlegter "
        "Zahlungsmethode - etwas aufwendiger einzurichten als die anderen "
        "drei Anbieter."
    ),
    "bootstrap.credentials_explain_openai": (
        "Schnelle Selbstbedienungs-Anmeldung, kostenpflichtig nach "
        "Nutzung."
    ),
    "bootstrap.credentials_explain_grok": (
        "Schnelle Selbstbedienungs-Anmeldung, kostenpflichtig nach "
        "Nutzung."
    ),
    "bootstrap.credentials_open_signup_button": "Schlüssel besorgen (öffnet Browser)",
    "bootstrap.credentials_key_label": "API-Schlüssel für {provider}",
    "bootstrap.credentials_key_placeholder": "Schlüssel einfügen …",
    "bootstrap.credentials_save_button": "Speichern",
    "bootstrap.credentials_saved": "Gespeichert.",
    "bootstrap.credentials_skip_all_button": "Später in den Einstellungen",
    "bootstrap.credentials_continue_button": "Weiter",
    "bootstrap.finish_title": "Fertig",
    "bootstrap.finish_text": (
        "PDF-Translator ist eingerichtet und im Anwendungsmenü zu finden."
    ),
    "bootstrap.finish_launch_button": "Jetzt starten",
    "bootstrap.finish_close_button": "Schließen",
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
        "No CUDA GPU was found for this method (see requirements-gpu.txt) "
        "- please choose a different rewrite method."
    ),
    "inpainting_backend.below_recommended_vram": (
        "Only {vram_gb:.0f} GB of video memory detected (recommended: at "
        "least {min_gb:.0f} GB) - may still work, but without guarantee, "
        "especially with large images or many text regions at once."
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
    # 28.08.2026 (round 3) - font-size/bold/centered controls in the
    # correction dialog (see TextReplacement.render_font_size/render_bold/
    # render_centered, pipeline/images/inpainting.py) - real user report,
    # Backlog.md 28.08.2026: "Wenn ich etwas korrigiere, muss es auch
    # genauso korrigiert werden wie ich es im Viewer sehe."
    "image_correction.font_size_label": "Font size:",
    "image_correction.font_size_auto": "Auto",
    "image_correction.bold": "Bold",
    "image_correction.centered": "Centered",
    "image_correction.apply": "Apply and save",
    "image_correction.close": "Close",
    "image_correction.applying": "Applying …",
    "image_correction.success": "{count} region(s) updated and saved to {output}.",
    "image_correction.failed": "Correction failed: {error}",
    "image_correction.choose_file_title": "Choose file to correct",
    "image_correction.choose_file_label": "Which file from this run should be corrected?",
    "update.available": "Update available: {version}",
    "update.confirm_title": "Install update?",
    "update.confirm_body": (
        "A new version ({version}) is available. Download and install it now?"
    ),
    "update.installing": "Installing update …",
    "update.success_title": "Update installed",
    "update.success_body": (
        "The update has been installed. Please restart the application for "
        "the changes to take effect."
    ),
    "update.failed_title": "Update failed",
    "update.failed_body": (
        "The update could not be installed: {error}\n\n"
        "The previously installed version keeps running unchanged."
    ),
    "menu.help": "Help",
    "menu.help.hw_check": "Show/repeat hardware test …",
    "menu.help.check_updates": "Check for updates …",
    "menu.help.about": "About …",
    "about.body": "{app_name}\nVersion {version}",
    "update.check.no_update_title": "No update available",
    "update.check.no_update_body": "You're already using the latest version ({version}).",
    "update.check.failed_title": "Update check failed",
    "update.check.failed_body": "Could not check for updates: {error}",
    "hw_check.title": "Hardware test",
    "hw_check.note": (
        "If the app isn't behaving as expected (e.g. with local AI "
        "inpainting), you can re-check the hardware here."
    ),
    "hw_check.recheck_button": "Check again",
    "hw_check.checking": "Checking hardware …",
    "hw_check.never_checked": (
        "No hardware check on record yet. Click \"Check again\" to run "
        "one now."
    ),
    "hw_check.not_found": (
        "No CUDA GPU found (last checked: {checked_at}). Local AI "
        "inpainting is not available on this hardware - Cloud inpainting "
        "works independently of this."
    ),
    "hw_check.found_ok": (
        "{name} with {vram_gb:.0f} GB of video memory found (last "
        "checked: {checked_at}). Meets the recommendation of at least "
        "{min_gb:.0f} GB."
    ),
    "hw_check.found_below_recommended": (
        "{name} with {vram_gb:.0f} GB of video memory found (last "
        "checked: {checked_at}). Below the recommendation of "
        "{min_gb:.0f} GB - may still work, but without guarantee, "
        "especially with large images or many text regions at once."
    ),
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
    "merge.button": "Merge / insert PDFs …",
    "merge.title": "Merge / insert PDFs",
    "merge.intro": (
        "Assemble source files in the order you want them merged. Each "
        "file can optionally have a page selection (empty = whole file) - "
        "add the same file twice with different page selections to insert "
        "another file at a specific point inside it."
    ),
    "merge.column_file": "File",
    "merge.column_pages": "Pages",
    "merge.pages_placeholder": "all",
    "merge.pages_tooltip": (
        "Empty = whole file. Otherwise e.g. \"1-3,5\" or \"6-\" (page 6 to "
        "the end) or \"-4\" (start to page 4). \"5-3\" inserts pages "
        "5,4,3 in that (reversed) order."
    ),
    "merge.add_files": "Add files …",
    "merge.remove_selected": "Remove",
    "merge.move_up": "Move up",
    "merge.move_down": "Move down",
    "merge.output_file_label": "Output file",
    "merge.output_placeholder": "Choose an output file …",
    "merge.choose_output_file": "Save as …",
    "merge.start_button": "Start merging",
    "merge.cancel_button": "Cancel",
    "merge.close_button": "Close",
    "merge.status_running": "Processing: {message}",
    "merge.status_done": "Done: wrote {pages} page(s) from {files} file(s).",
    "merge.status_cancelled": "Cancelled (partial result saved): wrote {pages} page(s).",
    "merge.status_failed": "Failed: {error}",
    "merge.error_dialog_choose_files": "Select PDF files",
    "merge.error_dialog_choose_output": "Choose output file",
    "merge.failed_title": "Merge failed",
    "merge_search.button": "Search a folder …",
    "merge_search.title": "Search PDFs in a folder",
    "merge_search.folder_label": "Folder",
    "merge_search.folder_placeholder": "Choose a folder …",
    "merge_search.choose_folder": "Choose folder …",
    "merge_search.choose_folder_dialog_title": "Choose a folder to search",
    "merge_search.recursive_checkbox": "Include subfolders",
    "merge_search.query_label": "Search text (ICO header on page 1 only)",
    "merge_search.query_placeholder": (
        "e.g. the developer's company name – leave empty for every PDF in the folder"
    ),
    "merge_search.search_button": "Search",
    "merge_search.cancel_button": "Cancel",
    "merge_search.select_all": "Select all",
    "merge_search.select_none": "Select none",
    "merge_search.take_selected": "Add selected",
    "merge_search.close_button": "Close",
    "merge_search.status_running": "Searching: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} match(es) out of {scanned} PDF(s) searched.",
    "merge_search.status_done_with_errors": (
        "{matches} match(es) out of {scanned} PDF(s) searched ({errors} unreadable)."
    ),
    "merge_search.status_cancelled": "Cancelled: {matches} match(es) out of {scanned} PDF(s) searched.",
    "merge_search.status_failed": "Failed: {error}",
    "merge_search.error_missing_folder": "Please choose a folder first.",
    "merge_search.failed_title": "Search failed",
    "merge_search.source_local": "Local folder",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Drive folder link or ID",
    "merge_search.drive_folder_placeholder": "Paste a share link or folder ID …",
    "merge_search.drive_resolve_button": "Check",
    "merge_search.drive_folder_unresolved": "Not checked yet.",
    "merge_search.drive_folder_resolved": "Found folder “{name}”.",
    "merge_search.drive_folder_resolve_failed": "Failed: {error}",
    "merge_search.drive_cache_label": "Cache folder (downloads are kept here)",
    "merge_search.drive_choose_cache": "Choose cache folder …",
    "merge_search.drive_choose_cache_dialog_title": "Choose a folder for downloaded matches",
    "merge_search.drive_credentials_label": "Google OAuth credentials (one-time, see docs/google_drive_setup.md)",
    "merge_search.drive_client_id_placeholder": "Client ID",
    "merge_search.drive_client_secret_placeholder": "Client secret",
    "merge_search.drive_save_credentials": "Save credentials",
    "merge_search.drive_credentials_saved": "Credentials saved.",
    "merge_search.drive_not_configured": "No Client ID/secret saved yet.",
    "merge_search.drive_configured_not_connected": "Configured, but not connected yet.",
    "merge_search.drive_connected": "Connected{account}.",
    "merge_search.drive_connect_button": "Connect to Google",
    "merge_search.drive_disconnect_button": "Disconnect",
    "merge_search.drive_connecting": "Opening browser for sign-in …",
    "merge_search.drive_connect_failed": "Connection failed: {error}",
    "merge_search.drive_error_missing_folder": "Please enter and check a Drive folder first.",
    "merge_search.drive_error_missing_cache": "Please choose a cache folder first.",
    "merge_search.drive_error_not_connected": "Please connect to Google first.",
    "word_merge.button": "Merge / insert DOCX files …",
    "word_merge.title": "Merge / insert DOCX files",
    "word_merge.intro": (
        "Assemble source files in the desired order - always whole files "
        "(unlike PDF, DOCX has no fixed page count in the file format "
        "itself). Add the same file more than once to insert it in "
        "multiple places. Above 100 files, merging happens automatically "
        "in groups (see the status line after the run)."
    ),
    "word_merge.status_done": (
        "Done: took {segments} of {files} file(s)"
        "{batch_suffix}{warning_suffix}."
    ),
    "word_merge.status_cancelled": (
        "Cancelled (partial result saved): took {segments} file(s)"
        "{batch_suffix}{warning_suffix}."
    ),
    "word_merge.status_batch_suffix": " in {batches} group(s)",
    "word_merge.status_warning_suffix": ", {count} skipped (see below)",
    "word_merge.warnings_title": "Skipped files:",
    "word_merge.error_dialog_choose_files": "Select DOCX files",
    "word_merge_search.title": "Search DOCX files in a folder",
    "word_merge_search.query_label": "Search text (ICO header at the start of the document only)",
    "word_merge_search.query_placeholder": (
        "e.g. the developer's company name – leave empty for every DOCX file in the folder"
    ),
    "word_merge_search.status_done": "{matches} match(es) out of {scanned} DOCX file(s) searched.",
    "word_merge_search.status_done_with_errors": (
        "{matches} match(es) out of {scanned} DOCX file(s) searched ({errors} unreadable)."
    ),
    "word_merge_search.status_cancelled": "Cancelled: {matches} match(es) out of {scanned} DOCX file(s) searched.",
    "bootstrap.window_title": "Set up PDF-Translator",
    "bootstrap.back_button": "Back",
    "bootstrap.next_button": "Next",
    "bootstrap.cancel_button": "Cancel",
    "bootstrap.welcome_title": "Welcome",
    "bootstrap.welcome_text": (
        "This wizard sets up PDF-Translator on this computer - no command "
        "line needed. It downloads the required components and adds an "
        "entry to your application menu at the end."
    ),
    "bootstrap.language_label": "Language",
    "bootstrap.mode_title": "Online or local?",
    "bootstrap.mode_intro": (
        "How should translation work? You can change this later in "
        "Settings at any time."
    ),
    "bootstrap.mode_online_label": "Online (cloud provider)",
    "bootstrap.mode_online_desc": (
        "Translation runs through an external provider (DeepL, Google, "
        "OpenAI, or Grok). This costs money per translation, and you'll "
        "need your own API key from that provider - more on that next. "
        "Recommended if you don't have a strong graphics card."
    ),
    "bootstrap.mode_local_label": "Local (on this graphics card)",
    "bootstrap.mode_local_desc": (
        "Translation/image editing runs directly on this computer, no "
        "ongoing costs. Needs a sufficiently strong NVIDIA graphics card "
        "though - checked in the next step - and a larger one-time "
        "download."
    ),
    "bootstrap.gpu_checking": "Checking graphics card …",
    "bootstrap.gpu_ok": "Found: {name} with {vram_gb:.0f} GB of video memory - that's enough.",
    "bootstrap.gpu_insufficient": (
        "Found: {name} with {vram_gb:.0f} GB of video memory - at least "
        "{min_gb:.0f} GB is recommended. Local mode will likely be very "
        "slow."
    ),
    "bootstrap.gpu_not_found": (
        "No supported NVIDIA graphics card found. Local mode isn't "
        "practically usable on this computer."
    ),
    "bootstrap.gpu_mac_unsupported": (
        "Local mode isn't supported on Mac yet. Please choose Online "
        "instead."
    ),
    "bootstrap.gpu_continue_local_button": "Continue with local anyway",
    "bootstrap.gpu_switch_online_button": "Switch to Online",
    "bootstrap.install_title": "Installing",
    "bootstrap.install_step_venv": "Setting up the environment …",
    "bootstrap.install_step_deps": "Installing components ({name}) …",
    "bootstrap.install_step_source": "Downloading program code …",
    "bootstrap.install_step_shortcut": "Adding application menu entry …",
    "bootstrap.install_failed_title": "Installation failed",
    "bootstrap.install_failed": "Failed: {error}",
    "bootstrap.credentials_title": "Set up API keys",
    "bootstrap.credentials_intro": (
        "Which providers would you like to set up? You can skip this and "
        "do it later in the app's Settings at any time."
    ),
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": (
        "Quick self-service sign-up. Free tier available, paid beyond "
        "that."
    ),
    "bootstrap.credentials_explain_google": (
        "Needs a Google Cloud project with a payment method on file - a "
        "bit more setup than the other three providers."
    ),
    "bootstrap.credentials_explain_openai": (
        "Quick self-service sign-up, pay per use."
    ),
    "bootstrap.credentials_explain_grok": (
        "Quick self-service sign-up, pay per use."
    ),
    "bootstrap.credentials_open_signup_button": "Get a key (opens browser)",
    "bootstrap.credentials_key_label": "API key for {provider}",
    "bootstrap.credentials_key_placeholder": "Paste key …",
    "bootstrap.credentials_save_button": "Save",
    "bootstrap.credentials_saved": "Saved.",
    "bootstrap.credentials_skip_all_button": "Later, in Settings",
    "bootstrap.credentials_continue_button": "Next",
    "bootstrap.finish_title": "Done",
    "bootstrap.finish_text": "PDF-Translator is set up and ready to find in your application menu.",
    "bootstrap.finish_launch_button": "Launch now",
    "bootstrap.finish_close_button": "Close",
}

CATALOGUES = {"de": DE, "en": EN}
