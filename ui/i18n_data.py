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
    LocaleInfo("fr", "Français", True),
    LocaleInfo("es", "Español", True),
    LocaleInfo("it", "Italiano", True),
    LocaleInfo("nl", "Nederlands", True),
    LocaleInfo("fi", "Suomi", True),
    LocaleInfo("hr", "Hrvatski", True),
    LocaleInfo("ru", "Русский", True),
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
    "field.side_by_side": "Nebeneinander anzeigen",
    "side_by_side.checkbox": "Original und Übersetzung nebeneinander",
    "side_by_side.tooltip": (
        "Nur Word: baut den Haupttext statt des normalen, layoutgetreuen "
        "Ergebnisses als zweispaltige Vergleichstabelle (Original | "
        "Übersetzung) im Querformat auf. Kopf- und Fußzeile bleiben "
        "unverändert. Eingebettete Tabellen im Haupttext (falls vorhanden) "
        "erscheinen in dieser Ansicht nicht."
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
    # 03.09.2026 (Michael: "Können wir bei den 'geschützten Begriffen' auch
    # noch ein aus Dateien auslesen hinzufügen? [...] eine csv laden"):
    "protected.load_file": "Aus Datei laden …",
    "protected.load_file.tooltip": (
        "Begriffe aus einer CSV- oder Textdatei übernehmen (ein Begriff pro Zeile, "
        "bei CSV zählt die erste Spalte). Vorhandene Einträge bleiben erhalten, "
        "Duplikate werden übersprungen."
    ),
    "protected.loaded": "{added} neue Begriffe aus {name} übernommen ({total} in der Datei).",
    "protected.load_error": "{name} konnte nicht gelesen werden: {error}",
    "dialog.choose_protected_terms": "Begriffsliste auswählen",
    "dialog.all_files": "Alle Dateien",
    # 02.09.2026 (Michael: "Sollten die beiden Optionen [...] mit in die
    # 'Vorgang' Auswahlbox? Oder sollten wir Rahmen für Übersetzung und
    # für 'PDF/DOCX' Zusammenführen machen. So ist es ein unangenehmer
    # Mix.") - siehe ui/app.py's Kommentar über merge_box.
    "merge_box.group": "Dateien zusammenführen",
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
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} Textzeichen · {images}<br>Lokale Schätzung ({provider}): Monatsverbrauch {usage:,} / Freikontingent {free:,} Zeichen · Schätzung ${cost:.2f}<br>Lauflimit {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Live-Kontingent (DeepL, gerade abgerufen):</b> {used:,} von {limit:,} Zeichen verbraucht, {remaining:,} verbleibend.",
    "analysis.live_quota_unlimited": "<b>Live-Kontingent (DeepL, gerade abgerufen):</b> {used:,} Zeichen verbraucht, Konto meldet kein Limit.",
    "unit.pages": "Seiten", "unit.slides": "Folien", "unit.paragraphs": "Absätze", "unit.images": "Bilder",
    "warning.scan_pdf": "Bild-/Scan-PDF erkannt: OCR ist für den Dokumenttext erforderlich.",
    "warning.image_cost_unknown": "OCR-Zeichen und Bildübersetzungskosten sind erst nach der OCR bekannt.",
    "warning.image_selection_later": "Die konkrete Bildauswahl erfolgt nach der Analyse in einer späteren UI-Ausbaustufe.",
    # 03.09.2026 (Michael: "Werden bei der Kostenkontrolle die übersetzten
    # Bilder mit berechnet und weggelassen wenn diese nicht übersetzt
    # werden sollen?") - siehe ui/analysis.py::analyze_request():
    "warning.embedded_images_not_estimated": "Bildtext ist in der Schätzung nicht enthalten: eingebettete Bilder werden im Dokumentlauf derzeit noch nicht übersetzt.",
    "analysis.images.files": "{images} Bilddateien",
    "analysis.images.excluded": "{images} eingebettete Bilder (ausgeschlossen, nicht berechnet)",
    "analysis.images.included": "{selected} von {images} eingebetteten Bildern zur Übersetzung",
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
    "about.body": "<h3>{app_name}</h3><p>Version {version}</p><p>Übersetzt PDF-, Word- und PowerPoint-Dokumente sowie Bilder und behält dabei das Layout bei.</p><p>© {year} {author}<br>Lizenz: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Quellcode: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Benutzerhandbuch …",
    "manual.hint_link": "Mehr dazu im Benutzerhandbuch (Kapitel 4)",
    "manual.missing": "Das Benutzerhandbuch wurde nicht gefunden:\n{path}",
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
    "hw_check.driver_cuda_ok": (
        "Treiber unterstützt CUDA {cuda_version} - passende PyTorch-Variante: "
        "{torch_variant}."
    ),
    "hw_check.driver_cuda_too_old": (
        "Treiber unterstützt nur CUDA {cuda_version} - zu alt für lokales "
        "KI-Inpainting (mindestens 11.8 nötig). Bitte den Grafiktreiber "
        "aktualisieren."
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
    "settings.save_button": "Speichern",
    "settings.open_log": "Log-Datei öffnen …",
    "settings.session_note": "Hinweis: Die Umgebungsvariable ist in dieser Version nicht dauerhaft.",
    "settings.credentials_group": "API-Zugang",
    "settings.general_group": "Allgemein",
    "settings.env_override_warning": "Für diesen Anbieter wird aktuell ein Wert aus einer Umgebungsvariable verwendet – nicht der hier gespeicherte Schlüsselbund-Eintrag. Um den gespeicherten Schlüssel zu nutzen, muss diese Umgebungsvariable im Betriebssystem entfernt werden.",

    "settings.provider.tooltip": "Anbieter, für den unten ein Schlüssel verwaltet wird",
    "settings.provider.whatsthis": (
        "Wählt, für welchen Übersetzungsanbieter (DeepL, Google, OpenAI, "
        "Grok) Status, neuer Schlüssel und Speicherort unten gelten. "
        "Jeder Anbieter hat einen eigenen, getrennt gespeicherten "
        "Schlüssel."
    ),
    "settings.status.tooltip": "Woher der aktuell verwendete Schlüssel stammt",
    "settings.status.whatsthis": (
        "Zeigt, ob für den gewählten Anbieter gerade ein Schlüssel aus "
        "dem OS-Keyring, aus einer Umgebungsvariable oder gar keiner "
        "gefunden wird. Eine Umgebungsvariable hat immer Vorrang vor dem "
        "Keyring - siehe die Warnung weiter unten, falls das hier "
        "zutrifft."
    ),
    "settings.secret.tooltip": "Neuer API-Schlüssel für den gewählten Anbieter",
    "settings.secret.whatsthis": (
        "Hier den vom Anbieter erhaltenen API-Schlüssel einfügen und "
        "auf „Speichern“ klicken. Die Eingabe wird beim Tippen als "
        "Punkte dargestellt, aber nicht automatisch übernommen - erst "
        "der Speichern-Button schreibt sie in den gewählten Speicherort."
    ),
    "settings.target_field.tooltip": "Wo der neue Schlüssel gespeichert wird",
    "settings.target_field.whatsthis": (
        "„OS-Keyring“ ist die empfohlene, dauerhafte Wahl. "
        "„Umgebungsvariable“ gilt nur für die laufende Sitzung und ist "
        "hauptsächlich für Sonderfälle/Fehlersuche gedacht - siehe den "
        "Hinweis darunter. „Beides“ schreibt zusätzlich ebenfalls eine "
        "solche Sitzungsvariable."
    ),
    "settings.max_chars.tooltip": "Obergrenze der Zeichen pro Übersetzungslauf",
    "settings.max_chars.whatsthis": (
        "Ein Lauf, der mehr Zeichen enthält als hier eingestellt, wird "
        "mit einem Hinweis abgebrochen statt unerwartet hohe Kosten zu "
        "verursachen. Bei Bedarf hier erhöhen."
    ),
    "settings.save_key.tooltip": "Neuen Schlüssel speichern",
    "settings.save_key.whatsthis": (
        "Schreibt den oben eingegebenen Schlüssel für den gewählten "
        "Anbieter an den gewählten Speicherort. Das Eingabefeld wird "
        "danach geleert, der Status darüber aktualisiert sich."
    ),
    "settings.open_log.tooltip": "Logdatei der App öffnen",
    "settings.open_log.whatsthis": (
        "Öffnet die aktuelle Logdatei im Standardprogramm des Systems - "
        "hilfreich, um Fehlermeldungen für einen Bugreport zu kopieren, "
        "ohne einen Screenshot machen zu müssen."
    ),

    "hw_check.status.tooltip": "Ergebnis der letzten GPU-Prüfung",
    "hw_check.status.whatsthis": (
        "Zeigt, ob eine unterstützte NVIDIA-GPU mit ausreichend VRAM "
        "gefunden wurde, wann zuletzt geprüft wurde, und ob der "
        "installierte Treiber (CUDA-Version) lokales GPU-Inpainting "
        "unterstützt. Ohne passende GPU/Treiber funktioniert lokales "
        "Inpainting trotzdem - nur langsamer, auf der CPU."
    ),
    "hw_check.recheck_button.tooltip": "GPU-Prüfung jetzt erneut ausführen",
    "hw_check.recheck_button.whatsthis": (
        "Führt dieselbe Prüfung erneut aus, die auch der Installer "
        "durchgeführt hat - sinnvoll nach einem Treiber-Update oder "
        "Grafikkarten-Wechsel, ohne die App neu installieren zu müssen."
    ),

    "bootstrap.help.back_button": (
        "Zurück zum vorherigen Schritt\n\n"
        "Bereits gemachte Eingaben auf diesem und dem vorherigen Schritt "
        "bleiben dabei erhalten."
    ),
    "bootstrap.help.next_button": "Weiter zum nächsten Schritt",
    "bootstrap.help.cancel_button": (
        "Schließt diesen Assistenten\n\n"
        "Vor einer laufenden Installation wird noch einmal nachgefragt. "
        "Die Einrichtung kann jederzeit erneut gestartet werden."
    ),
    "bootstrap.help.language_combo": (
        "Sprache dieses Assistenten\n\n"
        "Wirkt sofort auf alle Bildschirme dieses Assistenten. Die "
        "eigentliche App hat später eine eigene, unabhängige "
        "Sprachauswahl."
    ),
    "bootstrap.help.mode_online_radio": (
        "Übersetzung läuft über Cloud-Anbieter (DeepL, Google, OpenAI, "
        "Grok); Bildbearbeitung nutzt hier ein einfacheres Verfahren statt "
        "KI-gestütztem Inpainting\n\n"
        "Schnellste und einfachste Installation, funktioniert auf jedem "
        "Rechner. Benötigt einen eigenen API-Schlüssel des gewählten "
        "Anbieters und eine Internetverbindung während der Übersetzung."
    ),
    "bootstrap.help.mode_local_radio": (
        "Bessere, KI-gestützte Bildbearbeitung auf dieser Grafikkarte "
        "statt des einfacheren Standardverfahrens\n\n"
        "Benötigt eine unterstützte NVIDIA-Grafikkarte mit ausreichend "
        "Videospeicher (wird im nächsten Schritt geprüft) - dafür bleiben "
        "Bilder vollständig auf diesem Rechner."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Installation trotzdem lokal fortsetzen\n\n"
        "Sinnvoll, wenn die Prüfung fälschlich fehlschlug oder ein "
        "Treiber-Update noch aussteht - lokales Verarbeiten kann danach "
        "jederzeit über Hilfe -> Hardware-Test erneut geprüft werden."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Stattdessen die Online-Variante installieren\n\n"
        "Wechselt für diese Installation auf Cloud-Anbieter, ohne "
        "Rückfrage zur Grafikkarte. Kann später jederzeit über die "
        "Einstellungen ergänzt werden."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Im nächsten Schritt einen API-Schlüssel für {provider} "
        "hinterlegen\n\n"
        "Nicht angehakte Anbieter können jederzeit später in den "
        "Einstellungen der App ergänzt werden."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Ohne Schlüssel-Eingabe fortfahren\n\n"
        "Schlüssel können jederzeit später in den Einstellungen der App "
        "nachgetragen werden - ohne sie funktioniert allerdings noch "
        "keine Übersetzung."
    ),
    "bootstrap.help.credentials_continue_button": "Weiter zur Schlüssel-Eingabe bzw. zum nächsten Anbieter",
    "bootstrap.help.credential_open_signup_button": (
        "Öffnet die Registrierungsseite dieses Anbieters im Browser\n\n"
        "Dort wird der API-Schlüssel erzeugt, der anschließend hier "
        "eingefügt wird."
    ),
    "bootstrap.help.credential_key_entry": (
        "API-Schlüssel dieses Anbieters einfügen\n\n"
        "Die Eingabe wird als Punkte dargestellt. Erst der "
        "Speichern-Button unten übernimmt sie tatsächlich."
    ),
    "bootstrap.help.credential_save_button": "Eingegebenen Schlüssel jetzt speichern",
    "bootstrap.help.finish_close_button": "Assistenten schließen, ohne die App jetzt zu starten",
    "bootstrap.help.finish_launch_button": "Assistenten schließen und die App direkt starten",
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
    "merge.sort_by_name": "Nach Name sortieren",
    "merge.sort_by_date": "Nach Datum sortieren",
    "merge.sort_by_date_tooltip": (
        "Sortiert nach dem Änderungsdatum der Datei auf der Festplatte "
        "(letzte Änderung, nicht das Erstellungsdatum)."
    ),
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
    "merge_search.scope_ico_format": "ICO Format (Kopfbereich Seite 1)",
    "merge_search.scope_header": "Header (alle Seiten)",
    "merge_search.scope_full_text": "Volltext",
    # 02.09.2026 (Michael: "Bedeutet jetzt 'ICO Format (Kopfbereich Seite
    # 1)' das auch der Header mit durchsucht wird, oder nur der
    # Kopfbereich?") - die drei Bereiche sind unabhängig voneinander und
    # überschneiden sich nicht: "ICO Format" durchsucht NUR den
    # Metadatenblock auf Seite 1, "Header" NUR den auf jeder Seite
    # wiederkehrenden oberen Bereich, "Volltext" bewusst den gesamten
    # Text inkl. beider anderen Bereiche. Wird nichts angehakt, wird auch
    # nichts durchsucht - die Checkboxen sind frei kombinierbar.
    "merge_search.scope_ico_format_tooltip": (
        "Durchsucht NUR den ICO-Metadatenblock auf Seite 1 (Developer, QSI "
        "ICO, Ausstellungsdatum, ...). Unabhängig von „Header“ unten - "
        "wenn nur diese Option angehakt ist, wird der wiederkehrende "
        "Kopfbereich auf den ANDEREN Seiten NICHT durchsucht."
    ),
    "merge_search.scope_header_tooltip": (
        "Durchsucht NUR den auf jeder Seite wiederkehrenden oberen "
        "Bereich (z. B. Firmenname/Logo-Zeile). Unabhängig von „ICO "
        "Format“ oben - eine eigene, separate Textregion, keine "
        "Erweiterung davon."
    ),
    "merge_search.scope_full_text_tooltip": (
        "Durchsucht den GESAMTEN Text auf allen Seiten, inklusive der "
        "Bereiche von „ICO Format“ und „Header“ oben."
    ),
    "merge_search.error_missing_scope": "Bitte mindestens einen Suchbereich auswählen.",
    # Datumsfilter (02.09.2026, Michael: "Können wir noch eine nach
    # Datumsbereich, von, bis, exakt einbauen.") - siehe
    # pipeline/date_extract.py und ui/merge_search_dialog.py::
    # _build_date_filter_group() für die Details. Shared von beiden
    # Such-Dialogen (PDF und Word), da die Formulierungen format-
    # unabhängig sind.
    "merge_search.date_filter_group": "Nach Datum filtern",
    "merge_search.date_source_file": "Dateidatum",
    "merge_search.date_source_document": "Datum im Dokument",
    "merge_search.date_region_ico_format": "ICO Feld (Seite 1)",
    "merge_search.date_region_header": "Header (alle Seiten)",
    "merge_search.date_region_footer": "Footer (alle Seiten)",
    "merge_search.date_format_iso": "ISO (JJJJ-MM-TT)",
    "merge_search.date_format_iso_tooltip": "Erkennt z. B. „2026-09-04“.",
    "merge_search.date_format_de": "Deutsch (TT.MM.JJJJ)",
    "merge_search.date_format_de_tooltip": "Erkennt z. B. „04.09.2026“ (auch zweistellige Jahre wie „04.09.26“).",
    # 02.09.2026 (Michael: "Bei der Datumsuche müssten noch das Format
    # 'September 4, 2026' als Auswahl dabei sein [...]") - dieses Format
    # wurde technisch bereits VOR dieser Änderung erkannt (_EN_MONTH_RE in
    # pipeline/date_extract.py deckt sowohl "September 4, 2026" als auch
    # "4. September 2026" ab, Komma optional, Tag ein- oder zweistellig) -
    # nur die Beschriftung zeigte bislang kein konkretes Beispiel dafür,
    # anders als die drei anderen Formate oben mit ihrem TT.MM.JJJJ-Muster
    # in Klammern. Jetzt mit Beispiel direkt in der Beschriftung (nicht
    # nur im Tooltip) - genau das war der eigentliche Stolperstein.
    "merge_search.date_format_en_month": "Englisch (Monatsname, z. B. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": (
        "Erkennt sowohl „September 4, 2026“ als auch „4. September 2026“ "
        "(Komma optional, Tag ein- oder zweistellig)."
    ),
    "merge_search.date_format_slash": "Schrägstrich (TT/MM/JJJJ)",
    "merge_search.date_format_slash_tooltip": "Erkennt z. B. „04/09/2026“.",
    "merge_search.date_exact_checkbox": "Exaktes Datum",
    "merge_search.date_from_label": "Von",
    "merge_search.date_to_label": "Bis",
    "merge_search.date_exact_label": "Datum",
    "merge_search.error_date_range_reversed": "„Von“ darf nicht nach „Bis“ liegen.",
    "merge_search.error_missing_date_region": "Bitte mindestens einen Bereich für die Datumssuche auswählen.",
    "merge_search.error_missing_date_format": (
        "Bitte mindestens ein Datumsformat auswählen oder ein eigenes Format eingeben."
    ),
    # 02.09.2026 (Michael: "Plus Freitext Eintrag. Also 'MMMM D, YYYY' und
    # 'MMMM DD, YYYY'. Und für den Freitext sollten eben alle gültigen
    # Formate eingebar sein, mit Beispielen.") - ein optionales Freitext-
    # Feld für ein selbst eingegebenes Format, ZUSÄTZLICH zu den festen
    # Formaten oben (nicht statt ihnen) - siehe
    # pipeline/date_extract.py::compile_custom_date_pattern() für die
    # unterstützten Platzhalter.
    "merge_search.date_custom_format_label": "Eigenes Format",
    "merge_search.date_custom_format_placeholder": "z. B. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": (
        "Eigenes Datumsformat mit diesen Platzhaltern (immer in Englisch "
        "eingeben, auch in diesem deutschen Dialog) - alle anderen "
        "Zeichen wie Leerzeichen, Kommas, Punkte oder Schrägstriche "
        "werden wörtlich gesucht:\n\n"
        "YYYY – Jahr, 4-stellig, z. B. 2026\n"
        "YY – Jahr, 2-stellig, z. B. 26\n"
        "MMMM – Monatsname, z. B. September\n"
        "MMM – Monatsname abgekürzt, z. B. Sep\n"
        "MM – Monat, 2-stellig, z. B. 09\n"
        "M – Monat, 1- oder 2-stellig, z. B. 9\n"
        "DD – Tag, 2-stellig, z. B. 04\n"
        "D – Tag, 1- oder 2-stellig, z. B. 4\n\n"
        "Beispiele:\n"
        "„MMMM D, YYYY“ findet „September 4, 2026“\n"
        "„MMMM DD, YYYY“ findet „September 04, 2026“\n"
        "„YYYY/MM/DD“ findet „2026/09/04“"
    ),
    "merge_search.error_invalid_custom_date_format": (
        "Das eigene Datumsformat ist ungültig - bitte die Platzhalter aus dem Tooltip verwenden."
    ),
    # 02.09.2026 (Michael: "wird in der Überschrift über dem Suchfeld nicht
    # die Operatoren mit angezeigt. Die Aussage 'leer = alle Dateien' ist
    # eher verwirrend und sollte dort raus.") - "leer = alle Dateien"
    # entfernt (steht bereits als klarerer Hinweis im Platzhaltertext
    # query_placeholder direkt IM leeren Feld) und die &&/||-Symbole mit
    # aufgenommen, nicht nur UND/ODER wie zuvor.
    "merge_search.query_label": "Suchtext (UND/ODER bzw. &&/|| zum Verknüpfen mehrerer Begriffe)",
    "merge_search.query_placeholder": (
        "z. B. Firmenname des Developers, oder Begriff1 UND Begriff2 – leer lassen für alle Dateien im Ordner"
    ),
    "merge_search.query_tooltip": (
        "Mehrere Suchbegriffe lassen sich mit UND und ODER verknüpfen - auch "
        "gemischt. Mit Klammern legst du fest, was zusammengehört.\n\n"
        "Beispiel: „Acme UND Vertrag“ findet nur Dateien, die BEIDE Begriffe "
        "enthalten.\n"
        "„Acme ODER Zenith“ findet Dateien mit MINDESTENS EINEM der beiden "
        "Begriffe.\n\n"
        "Gemischt mit Klammern: „StellarRussia ODER (The UND Korolev UND "
        "Directive)“ findet Dateien mit „StellarRussia“ ODER Dateien, die ALLE "
        "DREI Begriffe „The“, „Korolev“ und „Directive“ enthalten.\n\n"
        "Statt UND/ODER lassen sich auch die Zeichen && und || verwenden "
        "(gleichbedeutend, auch gemischt mit den Wörtern): „Acme && Vertrag“ "
        "ist dasselbe wie „Acme UND Vertrag“.\n\n"
        "Ohne UND/ODER wird der gesamte Text als ein einzelner Suchbegriff "
        "behandelt (wie bisher). Groß-/Kleinschreibung spielt keine Rolle."
    ),
    "merge_search.search_button": "Suchen",
    "merge_search.cancel_button": "Abbrechen",
    "merge_search.select_all": "Alle auswählen",
    "merge_search.select_none": "Keine auswählen",
    # 02.09.2026 (Michael: "Vielleicht das Ergebnis Fenster rausnehmbar
    # machen. Wäre auch besser handhabbar bei vielen Dateien.") - ein
    # Knopf öffnet die Ergebnisliste als eigenes, frei verschieb-/
    # vergrößerbares Fenster; ein zweiter Klick (oder Schließen dieses
    # Fensters) holt sie wieder in den Suchdialog zurück - siehe
    # ui/merge_search_dialog.py::_toggle_detach_results().
    "merge_search.detach_results_button": "Ergebnisliste in eigenem Fenster öffnen",
    "merge_search.reattach_results_button": "Ergebnisliste andocken",
    "merge_search.results_detached_placeholder": "Die Ergebnisliste ist in einem eigenen Fenster geöffnet.",
    "merge_search.detached_results_title_suffix": "Ergebnisse",
    # 02.09.2026 (Michael: "Die Sortierung nach Dateinamen [...] Es würde
    # reichen die Sortierung im Anzeigefenster gemacht werden könnte.") -
    # dieselben merge.sort_by_name/merge.sort_by_date/
    # merge.sort_by_date_tooltip-Schlüssel wie im Zusammenführen-Dialog
    # (ui/merge_dialog.py, Fortsetzung 12) werden hier wiederverwendet,
    # da die Formulierung ("Nach Name sortieren"/"Nach Datum sortieren")
    # dialogunabhängig ist.
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
    "merge_search.drive_load_from_file": "Aus JSON-Datei laden …",
    "merge_search.drive_load_from_file_dialog_title": "Client-Secrets-JSON von Google Cloud Console wählen",
    "merge_search.drive_load_from_file_failed": "Datei konnte nicht gelesen werden: {error}",
    "merge_search.drive_client_id_placeholder": "Client-ID",
    "merge_search.drive_client_secret_placeholder": "Client-Secret",
    "merge_search.drive_project_id_placeholder": "Projekt-ID",
    "merge_search.drive_save_credentials": "Zugangsdaten speichern",
    "merge_search.drive_credentials_saved": "Zugangsdaten gespeichert.",
    "merge_search.drive_save_failed": "Speichern fehlgeschlagen: {error}",
    "merge_search.drive_not_configured": "Noch keine Client-ID/Client-Secret/Projekt-ID hinterlegt.",
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
    # query_label/query_placeholder: seit 02.09.2026 kein eigener Schlüssel
    # mehr - siehe merge_search.query_label/query_placeholder und
    # ui/word_merge_search_dialog.py::retranslate()s Kommentar dort.
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
    "bootstrap.window_title": "Document Translator einrichten",
    "bootstrap.back_button": "Zurück",
    "bootstrap.next_button": "Weiter",
    "bootstrap.cancel_button": "Abbrechen",
    "bootstrap.cancel_title": "Installation abbrechen?",
    "bootstrap.cancel_confirm": (
        "Der Einrichtungsassistent wird geschlossen, ohne dass "
        "Document Translator fertig eingerichtet ist. Bereits angelegte "
        "Dateien werden dabei automatisch wieder entfernt. Fortfahren?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "Die Installation läuft gerade. Beim Abbrechen werden bereits "
        "angelegte Dateien automatisch wieder entfernt - in seltenen "
        "Fällen kann dabei eine gerade verwendete Datei zurückbleiben. "
        "Trotzdem abbrechen?"
    ),
    # elevated_warning_* (06.09.2026, siehe bootstrap/app.py::
    # _warn_and_exit_if_elevated): einziger Text in diesem Katalog mit
    # echten "\n"-Zeilenumbrüchen statt physisch umgebrochener Prosa -
    # dieser Text geht an ctypes' MessageBoxW (kein ttk-Label mit
    # wraplength, das selbst umbricht), läuft außerdem VOR jeder
    # tkinter-Initialisierung.
    "bootstrap.elevated_warning_title": "Document Translator Setup - Administratorrechte",
    "bootstrap.elevated_warning_text": (
        "Document Translator wurde als Administrator gestartet.\n\n"
        "Das ist nicht nötig und richtet die Installation so ein, dass "
        "sie beim normalen (nicht-administrativen) Start später nicht "
        "mehr funktioniert.\n\n"
        "Bitte dieses Fenster schließen und das Setup per normalem "
        "Doppelklick erneut starten (ohne \"Als Administrator "
        "ausführen\").\n\n"
        "Diese Meldung lässt sich mit Strg+C kopieren."
    ),
    "bootstrap.uninstall_title": "Document Translator deinstallieren",
    "bootstrap.uninstall_confirm": (
        "Document Translator inklusive aller lokal gespeicherten Einstellungen "
        "und API-Schlüssel entfernen?"
    ),
    "bootstrap.uninstall_done": "Document Translator wurde entfernt.",
    "bootstrap.welcome_title": "Willkommen",
    "bootstrap.welcome_text": (
        "Dieser Assistent richtet Document Translator auf diesem Rechner ein - "
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
        "Anbieters benötigt - dazu gleich mehr. Bildbearbeitung in "
        "eingebetteten Bildern funktioniert auch hier, nur mit einem "
        "einfacheren Verfahren statt KI-gestütztem Inpainting. Kein "
        "großer Download nötig. Empfohlen, wenn keine starke Grafikkarte "
        "vorhanden ist."
    ),
    "bootstrap.mode_local_label": "Lokal (auf dieser Grafikkarte)",
    "bootstrap.mode_local_desc": (
        "Verbessert nur die Bildbearbeitung: Text in eingebetteten Bildern "
        "wird per OCR erkannt und nach der Übersetzung mit einem KI-Modell "
        "(LaMa) auf dieser Grafikkarte neu ins Bild gezeichnet - das sieht "
        "sauberer aus als das einfachere Verfahren, das auch ohne diese "
        "Option zur Verfügung steht. Die eigentliche Textübersetzung läuft "
        "in beiden Modi über einen externen Anbieter (DeepL, Google, "
        "OpenAI oder Grok) und kostet dort wie gewohnt pro Übersetzung. "
        "Online-Anbieter lassen sich zusätzlich jederzeit in den "
        "Einstellungen einrichten - diese Option installiert also beides. "
        "Braucht eine ausreichend starke NVIDIA-Grafikkarte (wird im "
        "nächsten Schritt geprüft) und lädt einmalig ca. 2-3 GB herunter."
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
    "bootstrap.gpu_driver_too_old": (
        "Gefunden: {name}, aber der NVIDIA-Treiber ist zu alt (unterstützt "
        "nur CUDA {cuda_version}, nötig ist mindestens 11.8). Bitte den "
        "Grafiktreiber aktualisieren und den Assistenten erneut starten, "
        "oder stattdessen Online wählen."
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
    "bootstrap.open_browser_title": "Browser öffnen?",
    "bootstrap.open_browser_text": (
        "Es wird folgender Link im Standardbrowser geöffnet:\n\n"
        "{url}\n\n"
        "Bitte prüfen, ob das wirklich die erwartete Adresse ist, bevor "
        "fortgefahren wird."
    ),
    "bootstrap.credentials_key_label": "API-Schlüssel für {provider}",
    "bootstrap.credentials_key_placeholder": "Schlüssel einfügen …",
    "bootstrap.credentials_save_button": "Speichern",
    "bootstrap.credentials_saved": "Gespeichert.",
    "bootstrap.credentials_skip_all_button": "Später in den Einstellungen",
    "bootstrap.credentials_continue_button": "Weiter",
    "bootstrap.finish_title": "Fertig",
    "bootstrap.finish_text": (
        "Document Translator ist eingerichtet und im Anwendungsmenü zu finden."
    ),
    "bootstrap.finish_download_size": "Tatsächlich heruntergeladen: ca. {size_gb:.1f} GB.",
    "bootstrap.finish_launch_button": "Jetzt starten",
    "bootstrap.finish_close_button": "Schließen",

    # 07.09.2026 (Michael: "zu jedem Button, Option usw. auch ein
    # richtiger Hilfetext"): kurzer Tooltip (Hover) + ausführlicher
    # WhatsThis-Text (Hilfe -> Direkthilfe / Umschalt+F1) pro
    # Bedienelement im Hauptfenster. Wo schon ein *.tooltip existiert
    # (ico_mode/side_by_side/exclude_header/exclude_footer/
    # protected.load_file), bleibt der unverändert und wird zusätzlich
    # 1:1 als WhatsThis wiederverwendet (siehe retranslate()) - diese
    # Texte sind bereits ausführlich genug, eine zweite, nur leicht
    # andere Formulierung hätte keinen echten Mehrwert.
    "mode.tooltip": "Art des zu übersetzenden Dokuments",
    "mode.whatsthis": (
        "Bestimmt, welcher Übersetzungsablauf verwendet wird: PDF, "
        "PowerPoint/Impress, Word/Writer oder einzelne Bilder. Je nach "
        "Auswahl blenden sich weiter unten nur die dafür relevanten Felder "
        "ein, z. B. die OCR-Einstellungen nur im Modus „Bilder“."
    ),
    "source.tooltip": "Datei(en) zum Übersetzen auswählen",
    "source.whatsthis": (
        "Öffnet den Dateiauswahl-Dialog für die Quelldatei (im "
        "Bilder-Modus auch mehrere Dateien gleichzeitig). Der gewählte "
        "Dateiname erscheint anschließend links daneben."
    ),
    "source_label.tooltip": "Aktuell ausgewählte Quelldatei",
    "source_label.whatsthis": (
        "Zeigt den Namen der zuletzt über „Datei wählen …“ ausgesuchten "
        "Datei. Steht hier „Keine Datei ausgewählt“, muss zuerst eine "
        "Datei gewählt werden, bevor eine Kostenanalyse möglich ist."
    ),
    "image_mode.tooltip": "Umgang mit eingebetteten Bildern im Dokument",
    "image_mode.whatsthis": (
        "„Nicht übersetzen“ lässt eingebettete Bilder unverändert. "
        "„Einzeln auswählen“ zeigt nach der Kostenanalyse eine Liste, aus "
        "der gezielt Bilder ausgewählt werden. „Alle übersetzen“ "
        "verarbeitet automatisch jedes eingebettete Bild mit."
    ),
    "provider.tooltip": "Übersetzungsanbieter für diesen Lauf",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI oder Grok - jeweils mit eigenem "
        "API-Schlüssel, verwaltet in den Einstellungen. Fehlt für den "
        "gewählten Anbieter ein Schlüssel, erscheint direkt darunter ein "
        "Hinweis mit Link zu den Einstellungen."
    ),
    "source_lang.tooltip": "Sprachcode der Ausgangssprache, z. B. EN",
    "source_lang.whatsthis": (
        "Zweibuchstabiger Sprachcode nach ISO 639-1 (z. B. EN für "
        "Englisch, FR für Französisch). Muss zur tatsächlichen Sprache "
        "des Dokuments passen, sonst liefert der Übersetzungsanbieter "
        "falsche oder gar keine Ergebnisse."
    ),
    "target_lang.tooltip": "Sprachcode der Zielsprache, z. B. DE",
    "target_lang.whatsthis": (
        "Zweibuchstabiger Sprachcode nach ISO 639-1, in den übersetzt "
        "werden soll (z. B. DE für Deutsch, ES für Spanisch)."
    ),
    "protected.tooltip": "Begriffe, die unübersetzt bleiben sollen",
    "protected.whatsthis": (
        "Ein Begriff pro Zeile, z. B. Firmen- oder Produktnamen. Der "
        "Übersetzungsanbieter lässt diese Begriffe unangetastet. Über den "
        "Button rechts daneben lässt sich zusätzlich eine Liste aus einer "
        "Datei nachladen."
    ),
    "ocr_engine_field.tooltip": "Texterkennung (OCR) für Bilder",
    "ocr_engine_field.whatsthis": (
        "Nur im Modus „Bilder“ sichtbar. Erkennt Text in den Bildern, "
        "bevor er übersetzt und zurückgeschrieben wird. Steht eine Engine "
        "auf diesem Rechner nicht zur Verfügung, erscheint direkt "
        "darunter ein Hinweis."
    ),
    "inpainting_backend_field.tooltip": (
        "Methode zum Zurückschreiben des übersetzten Texts ins Bild"
    ),
    "inpainting_backend_field.whatsthis": (
        "Nur im Modus „Bilder“ sichtbar. „Box-Overlay“ und "
        "„CV-Inpainting“ laufen immer lokal, ohne besondere Hardware. "
        "„GPU-Inpainting“ nutzt eine lokale Grafikkarte (CUDA) für das "
        "beste Ergebnis und ist nur verfügbar, wenn PyTorch mit "
        "CUDA-Unterstützung installiert ist - andernfalls erscheint "
        "darunter ein Hinweis. Den Hardware-Status jederzeit über Hilfe "
        "-> Hardware-Test prüfen."
    ),
    "merge.tooltip": "Mehrere PDF-Dateien zusammenführen",
    "merge.whatsthis": (
        "Öffnet einen eigenen Dialog zum Zusammenführen mehrerer "
        "PDF-Dateien in eine gemeinsame Datei. Unabhängig vom Formular "
        "oben - es wird dabei nichts übersetzt."
    ),
    "word_merge.tooltip": "Mehrere Word-Dateien zusammenführen",
    "word_merge.whatsthis": (
        "Öffnet einen eigenen Dialog zum Zusammenführen mehrerer "
        "Word-Dateien in eine gemeinsame Datei. Unabhängig vom Formular "
        "oben - es wird dabei nichts übersetzt."
    ),
    "analysis.button.tooltip": "Kosten des Übersetzungslaufs schätzen",
    "analysis.button.whatsthis": (
        "Zählt die zu übersetzenden Zeichen und schätzt anhand des "
        "gewählten Anbieters die ungefähren Kosten, ohne bereits etwas zu "
        "übersetzen. Erst danach lässt sich der Haken daneben setzen und "
        "„Start“ freischalten."
    ),
    "analysis.checked.tooltip": "Geschätzte Kosten bestätigen",
    "analysis.checked.whatsthis": (
        "Muss angehakt werden, bevor „Start“ klickbar wird - eine "
        "bewusste Sicherheitsstufe, damit kein Lauf versehentlich ohne "
        "vorherigen Blick auf die geschätzten Kosten gestartet wird."
    ),
    "start.tooltip": "Übersetzungslauf starten",
    "start.whatsthis": (
        "Erst aktiv, nachdem die Kosten analysiert und bestätigt wurden. "
        "Der Fortschritt erscheint im Bereich darunter; ein laufender "
        "Lauf lässt sich über „Abbrechen“ stoppen."
    ),
    "job.cancel.tooltip": "Laufenden Übersetzungslauf abbrechen",
    "job.cancel.whatsthis": (
        "Stoppt den aktuellen Lauf so schnell wie möglich. Bereits "
        "verarbeitete Teile bleiben nicht automatisch als vollständige "
        "Datei erhalten - je nach Format kann eine unvollständige Datei "
        "zurückbleiben."
    ),
    "job.open_folder.tooltip": "Ausgabeordner öffnen",
    "job.open_folder.whatsthis": (
        "Öffnet den Datei-Explorer im Zielordner des gerade "
        "abgeschlossenen Laufs."
    ),
    "job.open_report.tooltip": "QA-Bericht zum letzten Lauf öffnen",
    "job.open_report.whatsthis": (
        "Zeigt Auffälligkeiten aus der automatischen Qualitätsprüfung des "
        "letzten Laufs, z. B. Textstellen, die möglicherweise überprüft "
        "werden sollten."
    ),
    "job.correct_translation.tooltip": "Einzelne Übersetzungen korrigieren",
    "job.correct_translation.whatsthis": (
        "Nur bei PDF-Läufen mit korrigierbaren Textblöcken sichtbar. "
        "Ermöglicht es, einzelne übersetzte Textstellen gezielt "
        "nachzubearbeiten, ohne den ganzen Lauf zu wiederholen."
    ),
    "settings.button.tooltip": "Einstellungen öffnen",
    "settings.button.whatsthis": (
        "API-Schlüssel je Anbieter (empfohlen: Keyring), das "
        "Zeichenlimit pro Lauf und der Zugriff auf die Logdatei."
    ),
    "update_hint.tooltip": "Neue Version verfügbar",
    "update_hint.whatsthis": (
        "Erscheint automatisch, wenn beim Start eine neuere Version von "
        "Document Translator gefunden wurde. Anklicken bietet die "
        "Installation der neuen Version an."
    ),
    "flag_row.whatsthis": (
        "Wechselt sofort und dauerhaft die Sprache der Bedienoberfläche "
        "selbst - nicht die Übersetzungssprachen im Formular. Die "
        "Auswahl wird sofort gespeichert."
    ),
    "menu.help.whats_this": "Direkthilfe",
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
    "field.side_by_side": "Side-by-side view",
    "side_by_side.checkbox": "Original and translation side by side",
    "side_by_side.tooltip": (
        "Word only: builds the main text as a two-column landscape "
        "comparison table (Original | Translation) instead of the normal, "
        "layout-preserving output. Header and footer stay unchanged. Any "
        "embedded tables in the main text (if present) don't appear in "
        "this view."
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
    "protected.load_file": "Load from file …",
    "protected.load_file.tooltip": (
        "Load terms from a CSV or text file (one term per line; for CSV the first "
        "column is used). Existing entries are kept, duplicates are skipped."
    ),
    "protected.loaded": "{added} new terms loaded from {name} ({total} in the file).",
    "protected.load_error": "{name} could not be read: {error}",
    "dialog.choose_protected_terms": "Select term list",
    "dialog.all_files": "All files",
    "merge_box.group": "Merge files",
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
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} text characters · {images}<br>Local estimate ({provider}): monthly usage {usage:,} / free allowance {free:,} characters · estimate ${cost:.2f}<br>Run limit {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Live quota (DeepL, just checked):</b> {used:,} of {limit:,} characters used, {remaining:,} remaining.",
    "analysis.live_quota_unlimited": "<b>Live quota (DeepL, just checked):</b> {used:,} characters used, account reports no limit.",
    "unit.pages": "pages", "unit.slides": "slides", "unit.paragraphs": "paragraphs", "unit.images": "images",
    "warning.scan_pdf": "Image/scanned PDF detected: OCR is required for the document text.",
    "warning.image_cost_unknown": "OCR characters and image translation costs are unknown until OCR completes.",
    "warning.image_selection_later": "Individual image selection will follow the analysis in a later UI iteration.",
    "warning.embedded_images_not_estimated": "Image text is not part of the estimate: embedded images are not translated by the document run yet.",
    "analysis.images.files": "{images} image files",
    "analysis.images.excluded": "{images} embedded images (excluded, not charged)",
    "analysis.images.included": "{selected} of {images} embedded images selected for translation",
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
    "about.body": "<h3>{app_name}</h3><p>Version {version}</p><p>Translates PDF, Word and PowerPoint documents as well as images while keeping the layout.</p><p>© {year} {author}<br>License: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Source code: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "User manual …",
    "manual.hint_link": "More in the user manual (chapter 4)",
    "manual.missing": "The user manual could not be found:\n{path}",
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
    "hw_check.driver_cuda_ok": (
        "Driver supports CUDA {cuda_version} - matching PyTorch build: "
        "{torch_variant}."
    ),
    "hw_check.driver_cuda_too_old": (
        "Driver supports only CUDA {cuda_version} - too old for local AI "
        "inpainting (at least 11.8 required). Please update the graphics "
        "driver."
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
    "settings.save_button": "Save",
    "settings.open_log": "Open log file …",
    "settings.session_note": "Note: the environment variable is not persistent in this version.",
    "settings.credentials_group": "API Access",
    "settings.general_group": "General",
    "settings.env_override_warning": "This provider is currently using a value from an environment variable, not the keyring entry saved here. To use the saved key, remove that environment variable at the operating-system level.",

    "settings.provider.tooltip": "Provider whose key is managed below",
    "settings.provider.whatsthis": (
        "Selects which translation provider (DeepL, Google, OpenAI, "
        "Grok) the status, new key, and storage location below apply "
        "to. Each provider has its own, separately stored key."
    ),
    "settings.status.tooltip": "Where the currently used key comes from",
    "settings.status.whatsthis": (
        "Shows whether a key was found for the selected provider in "
        "the OS keyring, in an environment variable, or not at all. An "
        "environment variable always takes priority over the keyring - "
        "see the warning further below if that applies here."
    ),
    "settings.secret.tooltip": "New API key for the selected provider",
    "settings.secret.whatsthis": (
        "Paste the API key you received from the provider here and "
        "click \"Save\". While typing it is shown as dots but not "
        "applied automatically - only the Save button writes it to the "
        "selected storage location."
    ),
    "settings.target_field.tooltip": "Where the new key is stored",
    "settings.target_field.whatsthis": (
        "\"OS keyring\" is the recommended, persistent choice. "
        "\"Environment variable\" only lasts for the current session "
        "and is mainly meant for special cases/troubleshooting - see "
        "the note below. \"Both\" also writes such a session variable "
        "in addition."
    ),
    "settings.max_chars.tooltip": "Character limit per translation run",
    "settings.max_chars.whatsthis": (
        "A run containing more characters than set here is stopped "
        "with a message instead of causing unexpectedly high costs. "
        "Increase it here if needed."
    ),
    "settings.save_key.tooltip": "Save the new key",
    "settings.save_key.whatsthis": (
        "Writes the key entered above for the selected provider to the "
        "selected storage location. The input field is cleared "
        "afterwards, and the status above updates."
    ),
    "settings.open_log.tooltip": "Open the app's log file",
    "settings.open_log.whatsthis": (
        "Opens the current log file in the system's default program - "
        "useful for copying error messages into a bug report without "
        "taking a screenshot."
    ),

    "hw_check.status.tooltip": "Result of the last GPU check",
    "hw_check.status.whatsthis": (
        "Shows whether a supported NVIDIA GPU with enough VRAM was "
        "found, when it was last checked, and whether the installed "
        "driver's CUDA version supports local GPU inpainting. Without a "
        "matching GPU/driver, local inpainting still works - just "
        "slower, on the CPU."
    ),
    "hw_check.recheck_button.tooltip": "Run the GPU check again now",
    "hw_check.recheck_button.whatsthis": (
        "Runs the same check the installer already ran - useful after a "
        "driver update or a GPU swap, without having to reinstall the "
        "app."
    ),

    "bootstrap.help.back_button": (
        "Back to the previous step\n\n"
        "Anything already entered on this and the previous step is kept."
    ),
    "bootstrap.help.next_button": "Continue to the next step",
    "bootstrap.help.cancel_button": (
        "Closes this wizard\n\n"
        "You will be asked to confirm if an install is currently "
        "running. Setup can be started again at any time."
    ),
    "bootstrap.help.language_combo": (
        "Language of this wizard\n\n"
        "Applies immediately to every screen of this wizard. The app "
        "itself has its own, independent language choice later on."
    ),
    "bootstrap.help.mode_online_radio": (
        "Translation runs through cloud providers (DeepL, Google, "
        "OpenAI, Grok); image editing uses a simpler method here instead "
        "of AI-based inpainting\n\n"
        "Fastest and simplest install, works on any machine. Needs your "
        "own API key from the chosen provider and an internet connection "
        "while translating."
    ),
    "bootstrap.help.mode_local_radio": (
        "Better, AI-powered image editing on this graphics card instead "
        "of the simpler default method\n\n"
        "Needs a supported NVIDIA graphics card with enough video memory "
        "(checked in the next step) - in return, images never leave this "
        "machine."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Continue the local install anyway\n\n"
        "Useful if the check failed incorrectly or a driver update is "
        "still pending - local processing can be re-checked at any time "
        "later via Help -> Hardware test."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Install the online variant instead\n\n"
        "Switches this install to cloud providers, no GPU question "
        "asked. Can be added later at any time via the app's settings."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Enter an API key for {provider} in the next step\n\n"
        "Unchecked providers can always be added later in the app's "
        "settings."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Continue without entering any keys\n\n"
        "Keys can always be added later in the app's settings - but no "
        "translation will work without at least one."
    ),
    "bootstrap.help.credentials_continue_button": "Continue to key entry, or to the next provider",
    "bootstrap.help.credential_open_signup_button": (
        "Opens this provider's sign-up page in your browser\n\n"
        "That's where the API key is generated, to be pasted here "
        "afterwards."
    ),
    "bootstrap.help.credential_key_entry": (
        "Paste this provider's API key here\n\n"
        "Shown as dots while typing. Only the Save button below actually "
        "applies it."
    ),
    "bootstrap.help.credential_save_button": "Save the key entered above now",
    "bootstrap.help.finish_close_button": "Close the wizard without launching the app now",
    "bootstrap.help.finish_launch_button": "Close the wizard and launch the app right away",
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
    "merge.sort_by_name": "Sort by name",
    "merge.sort_by_date": "Sort by date",
    "merge.sort_by_date_tooltip": (
        "Sorts by the file's last-modified date on disk (not its creation date)."
    ),
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
    "merge_search.scope_ico_format": "ICO format (page 1 header area)",
    "merge_search.scope_header": "Header (all pages)",
    "merge_search.scope_full_text": "Full text",
    "merge_search.scope_ico_format_tooltip": (
        "Searches ONLY the ICO metadata block on page 1 (developer, QSI "
        "ICO, issue date, ...). Independent from “Header” below - with "
        "only this option checked, the recurring header area on the "
        "OTHER pages is NOT searched."
    ),
    "merge_search.scope_header_tooltip": (
        "Searches ONLY the area that recurs at the top of every page "
        "(e.g. company name/logo line). Independent from “ICO format” "
        "above - a separate text region, not an extension of it."
    ),
    "merge_search.scope_full_text_tooltip": (
        "Searches the ENTIRE text on every page, including the areas "
        "covered by “ICO format” and “Header” above."
    ),
    "merge_search.error_missing_scope": "Please select at least one search scope.",
    "merge_search.date_filter_group": "Filter by date",
    "merge_search.date_source_file": "File date",
    "merge_search.date_source_document": "Date in document",
    "merge_search.date_region_ico_format": "ICO field (page 1)",
    "merge_search.date_region_header": "Header (all pages)",
    "merge_search.date_region_footer": "Footer (all pages)",
    "merge_search.date_format_iso": "ISO (YYYY-MM-DD)",
    "merge_search.date_format_iso_tooltip": "Matches e.g. “2026-09-04”.",
    "merge_search.date_format_de": "German (DD.MM.YYYY)",
    "merge_search.date_format_de_tooltip": "Matches e.g. “04.09.2026” (also 2-digit years like “04.09.26”).",
    # 02.09.2026 - see the German string's comment: this format already
    # matched "September 4, 2026" before this change too (_EN_MONTH_RE in
    # pipeline/date_extract.py covers both orderings, comma optional,
    # 1- or 2-digit day) - just the label gave no concrete example, unlike
    # the other three formats' bracketed pattern above.
    "merge_search.date_format_en_month": "English (month name, e.g. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": (
        "Matches both “September 4, 2026” and “4 September 2026” "
        "(comma optional, day with or without a leading zero)."
    ),
    "merge_search.date_format_slash": "Slash (DD/MM/YYYY)",
    "merge_search.date_format_slash_tooltip": "Matches e.g. “04/09/2026”.",
    "merge_search.date_exact_checkbox": "Exact date",
    "merge_search.date_from_label": "From",
    "merge_search.date_to_label": "To",
    "merge_search.date_exact_label": "Date",
    "merge_search.error_date_range_reversed": "“From” must not be after “To”.",
    "merge_search.error_missing_date_region": "Please select at least one region for the date search.",
    "merge_search.error_missing_date_format": "Please select at least one date format, or enter your own format.",
    # 02.09.2026 (Michael: "Plus Freitext Eintrag [...] für den Freitext
    # sollten eben alle gültigen Formate eingebar sein, mit Beispielen.")
    # - an optional free-text field for a user-typed format, IN ADDITION
    # to the presets above (not instead of them) - see
    # pipeline/date_extract.py::compile_custom_date_pattern() for the
    # supported placeholders.
    "merge_search.date_custom_format_label": "Custom format",
    "merge_search.date_custom_format_placeholder": "e.g. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": (
        "Custom date format using these placeholders (everything else - "
        "spaces, commas, dots, slashes, ... - is matched literally):\n\n"
        "YYYY – year, 4 digits, e.g. 2026\n"
        "YY – year, 2 digits, e.g. 26\n"
        "MMMM – month name, e.g. September\n"
        "MMM – month name, abbreviated, e.g. Sep\n"
        "MM – month, 2 digits, e.g. 09\n"
        "M – month, 1 or 2 digits, e.g. 9\n"
        "DD – day, 2 digits, e.g. 04\n"
        "D – day, 1 or 2 digits, e.g. 4\n\n"
        "Examples:\n"
        "“MMMM D, YYYY” matches “September 4, 2026”\n"
        "“MMMM DD, YYYY” matches “September 04, 2026”\n"
        "“YYYY/MM/DD” matches “2026/09/04”"
    ),
    "merge_search.error_invalid_custom_date_format": (
        "The custom date format is invalid - please use the placeholders shown in the tooltip."
    ),
    # 02.09.2026 - see the German string's comment: "empty = every file"
    # dropped (already covered, more clearly, by query_placeholder), &&/||
    # added alongside AND/OR.
    "merge_search.query_label": "Search text (combine terms with AND/OR or &&/||)",
    "merge_search.query_placeholder": (
        "e.g. the developer's company name, or term1 AND term2 – leave empty for every file in the folder"
    ),
    "merge_search.query_tooltip": (
        "Combine multiple search terms with AND and OR - even mixed. Use "
        "parentheses to group what belongs together.\n\n"
        "Example: “Acme AND contract” only finds files containing BOTH "
        "terms.\n"
        "“Acme OR Zenith” finds files containing AT LEAST ONE of the two "
        "terms.\n\n"
        "Mixed with parentheses: “StellarRussia OR (The AND Korolev AND "
        "Directive)” finds files containing “StellarRussia” OR files "
        "containing ALL THREE of “The”, “Korolev” and “Directive”.\n\n"
        "The symbols && and || also work instead of AND/OR (equivalent, "
        "even mixed with the words): “Acme && contract” is the same as "
        "“Acme AND contract”.\n\n"
        "Without AND/OR, the whole text is treated as a single search term "
        "(as before). Not case-sensitive."
    ),
    "merge_search.search_button": "Search",
    "merge_search.cancel_button": "Cancel",
    "merge_search.select_all": "Select all",
    "merge_search.select_none": "Select none",
    "merge_search.detach_results_button": "Open results in a separate window",
    "merge_search.reattach_results_button": "Dock results back",
    "merge_search.results_detached_placeholder": "The results list is open in a separate window.",
    "merge_search.detached_results_title_suffix": "Results",
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
    "merge_search.drive_load_from_file": "Load from JSON file …",
    "merge_search.drive_load_from_file_dialog_title": "Choose the client-secrets JSON from Google Cloud Console",
    "merge_search.drive_load_from_file_failed": "Could not read file: {error}",
    "merge_search.drive_client_id_placeholder": "Client ID",
    "merge_search.drive_client_secret_placeholder": "Client secret",
    "merge_search.drive_project_id_placeholder": "Project ID",
    "merge_search.drive_save_credentials": "Save credentials",
    "merge_search.drive_credentials_saved": "Credentials saved.",
    "merge_search.drive_save_failed": "Save failed: {error}",
    "merge_search.drive_not_configured": "No Client ID/secret/project ID saved yet.",
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
    # query_label/query_placeholder: no longer a separate key since
    # 02.09.2026 - see merge_search.query_label/query_placeholder.
    "word_merge_search.status_done": "{matches} match(es) out of {scanned} DOCX file(s) searched.",
    "word_merge_search.status_done_with_errors": (
        "{matches} match(es) out of {scanned} DOCX file(s) searched ({errors} unreadable)."
    ),
    "word_merge_search.status_cancelled": "Cancelled: {matches} match(es) out of {scanned} DOCX file(s) searched.",
    "bootstrap.window_title": "Set up Document Translator",
    "bootstrap.back_button": "Back",
    "bootstrap.next_button": "Next",
    "bootstrap.cancel_button": "Cancel",
    "bootstrap.cancel_title": "Cancel installation?",
    "bootstrap.cancel_confirm": (
        "The setup wizard will close without Document Translator being fully "
        "set up. Any files already created will be removed "
        "automatically. Continue?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "The installation is currently running. Cancelling will "
        "automatically remove any files already created - in rare "
        "cases a file still in use at that exact moment may be left "
        "behind. Cancel anyway?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Administrator Privileges",
    "bootstrap.elevated_warning_text": (
        "Document Translator was started as Administrator.\n\n"
        "This is not necessary and will set things up in a way that "
        "stops the app working later when started normally (without "
        "admin rights).\n\n"
        "Please close this window and start the setup again with a "
        "normal double-click (without \"Run as administrator\").\n\n"
        "This message can be copied with Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Uninstall Document Translator",
    "bootstrap.uninstall_confirm": (
        "Remove Document Translator, including all locally stored settings "
        "and API keys?"
    ),
    "bootstrap.uninstall_done": "Document Translator has been removed.",
    "bootstrap.welcome_title": "Welcome",
    "bootstrap.welcome_text": (
        "This wizard sets up Document Translator on this computer - no command "
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
        "Image editing in embedded images still works here too, just "
        "with a simpler method instead of AI-based inpainting. No large "
        "download needed. Recommended if you don't have a strong "
        "graphics card."
    ),
    "bootstrap.mode_local_label": "Local (on this graphics card)",
    "bootstrap.mode_local_desc": (
        "Improves image editing only: text embedded in images is "
        "detected via OCR and redrawn using an AI model (LaMa) on this "
        "graphics card after translation - the result looks cleaner than "
        "the simpler method already available without this option. The "
        "actual text translation still runs through an external provider "
        "(DeepL, Google, OpenAI, or Grok) in both modes, at that "
        "provider's usual per-translation cost. Online providers can "
        "still be set up any time in Settings if you want them too. "
        "Needs a sufficiently strong NVIDIA graphics card (checked in the "
        "next step) and downloads about 2-3 GB during setup."
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
    "bootstrap.gpu_driver_too_old": (
        "Found: {name}, but the NVIDIA driver is too old (supports only "
        "CUDA {cuda_version}; at least 11.8 is required). Please update "
        "the graphics driver and run this setup again, or choose Online "
        "instead."
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
    "bootstrap.open_browser_title": "Open browser?",
    "bootstrap.open_browser_text": (
        "The following link will be opened in the default browser:\n\n"
        "{url}\n\n"
        "Please check that this is really the expected address before "
        "continuing."
    ),
    "bootstrap.credentials_key_label": "API key for {provider}",
    "bootstrap.credentials_key_placeholder": "Paste key …",
    "bootstrap.credentials_save_button": "Save",
    "bootstrap.credentials_saved": "Saved.",
    "bootstrap.credentials_skip_all_button": "Later, in Settings",
    "bootstrap.credentials_continue_button": "Next",
    "bootstrap.finish_title": "Done",
    "bootstrap.finish_text": "Document Translator is set up and ready to find in your application menu.",
    "bootstrap.finish_download_size": "Actually downloaded: about {size_gb:.1f} GB.",
    "bootstrap.finish_launch_button": "Launch now",
    "bootstrap.finish_close_button": "Close",
    "mode.tooltip": "Type of document to translate",
    "mode.whatsthis": (
        "Determines which translation workflow is used: PDF, "
        "PowerPoint/Impress, Word/Writer, or individual images. Depending "
        "on the selection, only the relevant fields below are shown, e.g. "
        "the OCR settings only appear in \"Images\" mode."
    ),
    "source.tooltip": "Select the file(s) to translate",
    "source.whatsthis": (
        "Opens the file picker for the source file (in Images mode, "
        "several files at once). The chosen file name then appears to "
        "the left."
    ),
    "source_label.tooltip": "Currently selected source file",
    "source_label.whatsthis": (
        "Shows the name of the file last chosen via \"Select file …\". "
        "If it still says \"No file selected\", pick a file first before "
        "a cost analysis is possible."
    ),
    "image_mode.tooltip": "How to handle images embedded in the document",
    "image_mode.whatsthis": (
        "\"Do not translate\" leaves embedded images unchanged. \"Select "
        "individually later\" shows a list after the cost analysis from "
        "which to pick specific images. \"Translate all\" automatically "
        "processes every embedded image."
    ),
    "provider.tooltip": "Translation provider for this run",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI, or Grok - each with its own API key, "
        "managed in Settings. If no key is configured for the selected "
        "provider, a hint with a link to Settings appears right below."
    ),
    "source_lang.tooltip": "Source language code, e.g. EN",
    "source_lang.whatsthis": (
        "Two-letter ISO 639-1 language code (e.g. EN for English, FR for "
        "French). Must match the document's actual language, otherwise "
        "the translation provider returns wrong or no results."
    ),
    "target_lang.tooltip": "Target language code, e.g. DE",
    "target_lang.whatsthis": (
        "Two-letter ISO 639-1 language code to translate into (e.g. DE "
        "for German, ES for Spanish)."
    ),
    "protected.tooltip": "Terms that should stay untranslated",
    "protected.whatsthis": (
        "One term per line, e.g. company or product names. The "
        "translation provider leaves these terms untouched. The button "
        "next to the field can also load a list from a file."
    ),
    "ocr_engine_field.tooltip": "Text recognition (OCR) for images",
    "ocr_engine_field.whatsthis": (
        "Only shown in \"Images\" mode. Recognizes text in the images "
        "before it is translated and written back. If an engine is not "
        "available on this machine, a hint appears right below."
    ),
    "inpainting_backend_field.tooltip": (
        "Method for writing the translated text back into the image"
    ),
    "inpainting_backend_field.whatsthis": (
        "Only shown in \"Images\" mode. \"Box overlay\" and \"CV "
        "inpainting\" always run locally, with no special hardware "
        "required. \"GPU inpainting\" uses a local graphics card (CUDA) "
        "for the best result and is only available if PyTorch with CUDA "
        "support is installed - otherwise a hint appears below. Check "
        "the hardware status any time via Help -> Hardware test."
    ),
    "merge.tooltip": "Merge several PDF files",
    "merge.whatsthis": (
        "Opens a separate dialog for merging several PDF files into "
        "one. Independent of the form above - nothing is translated "
        "here."
    ),
    "word_merge.tooltip": "Merge several Word files",
    "word_merge.whatsthis": (
        "Opens a separate dialog for merging several Word files into "
        "one. Independent of the form above - nothing is translated "
        "here."
    ),
    "analysis.button.tooltip": "Estimate the cost of this translation run",
    "analysis.button.whatsthis": (
        "Counts the characters to be translated and estimates the "
        "approximate cost for the selected provider, without translating "
        "anything yet. Only after this can the checkbox next to it be "
        "ticked and \"Start\" enabled."
    ),
    "analysis.checked.tooltip": "Confirm the estimated cost",
    "analysis.checked.whatsthis": (
        "Must be ticked before \"Start\" becomes clickable - a "
        "deliberate safety step so no run is ever started accidentally "
        "without first looking at the estimated cost."
    ),
    "start.tooltip": "Start the translation run",
    "start.whatsthis": (
        "Only enabled after the cost has been analyzed and confirmed. "
        "Progress appears in the area below; a running job can be "
        "stopped via \"Cancel\"."
    ),
    "job.cancel.tooltip": "Cancel the running translation job",
    "job.cancel.whatsthis": (
        "Stops the current run as quickly as possible. Parts already "
        "processed are not automatically kept as a complete file - "
        "depending on the format, an incomplete file may remain."
    ),
    "job.open_folder.tooltip": "Open the output folder",
    "job.open_folder.whatsthis": (
        "Opens the file explorer in the destination folder of the run "
        "that just finished."
    ),
    "job.open_report.tooltip": "Open the QA report for the last run",
    "job.open_report.whatsthis": (
        "Shows findings from the automatic quality check of the last "
        "run, e.g. passages that may be worth reviewing."
    ),
    "job.correct_translation.tooltip": "Correct individual translations",
    "job.correct_translation.whatsthis": (
        "Only shown for PDF runs with correctable text blocks. Lets you "
        "rework individual translated passages without repeating the "
        "whole run."
    ),
    "settings.button.tooltip": "Open settings",
    "settings.button.whatsthis": (
        "API keys per provider (recommended: keyring), the character "
        "limit per run, and access to the log file."
    ),
    "update_hint.tooltip": "A new version is available",
    "update_hint.whatsthis": (
        "Appears automatically when a newer version of Document Translator "
        "was found at startup. Clicking it offers to install the new "
        "version."
    ),
    "flag_row.whatsthis": (
        "Immediately and permanently switches the language of the "
        "interface itself - not the translation languages in the form. "
        "The choice is saved right away."
    ),
    "menu.help.whats_this": "What's This?",
}



FR = {
    "app.title": "Document Translator",
    "mode.pdf": "Traduire un PDF",
    "mode.presentation": "Traduire une présentation (PowerPoint/Impress)",
    "mode.word": "Traduire un document Word/Writer",
    "mode.images": "Traduire des images individuelles",
    "source.none": "Aucun fichier sélectionné",
    "source.choose": "Sélectionner un fichier …",
    "image.none": "Ne pas traduire les images intégrées",
    "image.selected": "Sélectionner les images individuellement plus tard",
    "image.all": "Traduire toutes les images intégrées",
    "field.mode": "Opération",
    "field.source": "Source",
    "field.images": "Images du document",
    "field.provider": "Fournisseur de traduction",
    "field.source_language": "Langue source",
    "field.target_language": "Langue cible",
    "field.protected_terms": "Termes protégés",
    "field.ico_mode": "Document ICO",
    "ico_mode.checkbox": "Ne pas traduire la zone de la page 1",
    "ico_mode.tooltip": "Uniquement pour le type de document interne ICO : exclut de la traduction la zone de métadonnées en page 1 (pour Word : la zone avant la ligne de séparation ; pour PDF : détectée à l'aide de termes d'ancrage comme \"Issuer Address\"/\"Asset Matrix\") - que cette zone soit effectivement trouvée ou non. Laisser désactivé pour tous les autres documents.",
    "field.side_by_side": "Affichage côte à côte",
    "side_by_side.checkbox": "Original et traduction côte à côte",
    "side_by_side.tooltip": "Word uniquement : construit le texte principal sous forme de tableau comparatif à deux colonnes (Original | Traduction) en format paysage, au lieu du résultat normal fidèle à la mise en page. L'en-tête et le pied de page restent inchangés. Les tableaux intégrés dans le texte principal (le cas échéant) n'apparaissent pas dans cet affichage.",
    "field.exclude_header": "En-tête",
    "exclude_header.checkbox": "Ne pas traduire l'en-tête récurrent",
    "exclude_header.tooltip": "Détecte automatiquement le texte qui revient à l'identique (ou seulement avec un numéro de page différent) en haut de la plupart des pages, et l'exclut de la traduction. Si rien de correspondant n'est trouvé, rien ne change.",
    "field.exclude_footer": "Pied de page",
    "exclude_footer.checkbox": "Ne pas traduire le pied de page récurrent",
    "exclude_footer.tooltip": "Comme pour l'en-tête, mais pour le texte récurrent en bas de page (par ex. mention de copyright, numéro de page).",
    "field.ocr_engine": "Moteur OCR",
    "ocr_engine.tesseract": "Tesseract (local)",
    "ocr_engine.tesseract.unavailable": "Tesseract est introuvable sur ce système. Veuillez l'installer (voir README.md) - sans Tesseract installé, aucun texte ne peut être reconnu dans les images.",
    "ocr_engine.google_vision": "Google Cloud Vision (cloud, détection des paragraphes)",
    "ocr_engine.google_vision.unavailable": "Aucune clé API Google configurée. Renseignez-la dans les paramètres (la même clé que pour Google Translate, voir README.md) ou choisissez un autre moteur OCR.",
    "ocr_engine.paddleocr": "PaddleOCR (local, détection des paragraphes)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR n'est pas installé (voir requirements-paddleocr.txt) ou choisissez un autre moteur OCR.",
    "ocr_engine.unavailable": "Ce moteur OCR n'est pas disponible sur ce système.",
    "field.inpainting_backend": "Méthode de réécriture",
    "inpainting_backend.box_overlay": "Superposition de zone (recouvrir la surface)",
    "inpainting_backend.cv_inpainting": "Inpainting CPU classique (reconstruction de l'arrière-plan)",
    "inpainting_backend.gpu_inpainting": "Inpainting IA local (GPU, LaMa)",
    "inpainting_backend.unavailable": "Aucun GPU CUDA détecté pour cette méthode (voir requirements-gpu.txt) - veuillez choisir une autre méthode de réécriture.",
    "inpainting_backend.below_recommended_vram": "Seulement {vram_gb:.0f} Go de mémoire graphique détectés (recommandé : au moins {min_gb:.0f} Go) - cela peut fonctionner, mais sans garantie, surtout avec de grandes images ou de nombreuses zones de texte simultanées.",
    "source_language.placeholder": "facultatif / automatique",
    "protected.placeholder": "Un terme protégé par ligne",
    "protected.load_file": "Charger depuis un fichier …",
    "protected.load_file.tooltip": "Importe des termes depuis un fichier CSV ou texte (un terme par ligne ; pour un CSV, seule la première colonne est prise en compte). Les entrées existantes sont conservées, les doublons sont ignorés.",
    "protected.loaded": "{added} nouveaux termes importés depuis {name} ({total} dans le fichier).",
    "protected.load_error": "Impossible de lire {name} : {error}",
    "dialog.choose_protected_terms": "Sélectionner une liste de termes",
    "dialog.all_files": "Tous les fichiers",
    "merge_box.group": "Fusionner des fichiers",
    "config.group": "Configurer la tâche",
    "analysis.group": "Analyse et contrôle des coûts",
    "analysis.required": "Une analyse est requise avant de démarrer.",
    "analysis.button": "Analyser le document et estimer les coûts",
    "analysis.running": "Analyse en cours …",
    "analysis.checked": "Analyse et estimation des coûts vérifiées",
    "analysis.failed": "Échec de l'analyse.",
    "analysis.no_warnings": "Aucun avertissement d'analyse.",
    "analysis.within": "dans la limite",
    "analysis.exceeded": "DÉPASSÉ",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} caractères de texte · {images}<br>Estimation locale ({provider}) : usage mensuel {usage:,} / quota gratuit {free:,} caractères · estimation {cost:.2f} $<br>Limite par lancement {limit:,} : {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Quota en direct (DeepL, vient d'être récupéré) :</b> {used:,} sur {limit:,} caractères utilisés, {remaining:,} restants.",
    "analysis.live_quota_unlimited": "<b>Quota en direct (DeepL, vient d'être récupéré) :</b> {used:,} caractères utilisés, le compte ne signale aucune limite.",
    "unit.pages": "pages",
    "unit.slides": "diapositives",
    "unit.paragraphs": "paragraphes",
    "unit.images": "images",
    "warning.scan_pdf": "PDF image/scanné détecté : l'OCR est nécessaire pour le texte du document.",
    "warning.image_cost_unknown": "Le nombre de caractères OCR et le coût de traduction des images ne sont connus qu'après l'OCR.",
    "warning.image_selection_later": "La sélection précise des images se fera après l'analyse, dans une version ultérieure de l'interface.",
    "warning.embedded_images_not_estimated": "Le texte des images n'est pas inclus dans l'estimation : les images intégrées ne sont pas encore traduites lors du traitement du document.",
    "analysis.images.files": "{images} fichiers image",
    "analysis.images.excluded": "{images} images intégrées (exclues, non facturées)",
    "analysis.images.included": "{selected} sur {images} images intégrées sélectionnées pour la traduction",
    "warning.live_quota_unavailable": "Le quota en direct de DeepL n'est pas accessible actuellement (pas de clé, hors ligne, ou erreur API) - l'estimation locale est utilisée à la place.",
    "start.button": "Démarrer la traduction",
    "start.pending": "Le démarrage n'est pas encore disponible pour ce mode (voir RoadMap.md).",
    "start.ready": "Prêt à démarrer.",
    "start.blocked_running": "Un traitement est déjà en cours.",
    "start.blocked_mode": "Le démarrage n'est pas encore disponible pour ce mode (voir RoadMap.md) - seul « Traduire une présentation » est déjà connecté.",
    "start.blocked_no_analysis": "Veuillez d'abord exécuter « Analyser le document et estimer les coûts ».",
    "start.blocked_not_confirmed": "Veuillez cocher « Analyse et estimation des coûts vérifiées ».",
    "dialog.choose_output_dir": "Choisir le dossier de destination",
    "dialog.confirm_run": "Démarrer la traduction",
    "start.confirm_summary": "Environ {characters:,} caractères seront envoyés à {provider} (coût estimé : {cost:.2f} $).\nFichier de destination : {destination}\n\nDémarrer maintenant ?",
    "start.confirm_summary_images": "Environ {characters:,} caractères seront envoyés à {provider} (coût estimé : {cost:.2f} $) pour {count} image(s).\nDossier de destination : {folder}\n\nDémarrer maintenant ?",
    "job.group": "Traitement et résultat",
    "job.idle": "Aucun traitement démarré pour le moment.",
    "job.running": "Traduction en cours …",
    "job.progress_prefix": "Traitement en cours : {location}",
    "job.progress_count": "{processed} paragraphe(s) sur {total} traité(s)",
    "job.progress_count_files": "{processed} image(s) sur {total} traitée(s)",
    "job.stats_summary": "{translated} traduit(s) · {skipped} ignoré(s) · {failed} échoué(s) · {chars:,} caractères envoyés",
    "job.cancel": "Annuler",
    "job.cancel_requested": "Annulation demandée - arrêt après l'appel API en cours …",
    "job.result_summary": "Terminé : {translated} traduit(s), {skipped} ignoré(s), {failed} échoué(s), {chars:,} caractères envoyés.\nFichier de sortie : {output}\nRapport qualité : {report}",
    "job.result_summary_images": "Terminé : {files} image(s) traitée(s), {translated} zone(s) de texte traduite(s), {failed} échoué(s), {chars:,} caractères envoyés.\nDossier de sortie : {output_dir}\nChaque image dispose de son propre fichier de rapport qualité dans le dossier de sortie.",
    "job.result_cancelled_suffix": "\nRemarque : le traitement a été annulé - il s'agit d'un résultat partiel, le contenu déjà traduit a été enregistré.",
    "job.overflow_none": "Aucun nouveau risque de débordement détecté.",
    "job.overflow_count": "{count} remarque(s) de débordement dans le rapport qualité - veuillez vérifier manuellement dans PowerPoint/Impress.",
    "job.pdf_overflow_none": "Aucun bloc n'a dû être agrandi ou réduit lors de l'insertion.",
    "job.pdf_overflow_count": "{count} bloc(s) ont dû être agrandis ou réduits pour s'adapter - veuillez effectuer un contrôle ponctuel dans le PDF.",
    "job.open_folder": "Ouvrir le dossier",
    "job.open_report": "Ouvrir le rapport qualité",
    "job.open_folder_failed": "Impossible d'ouvrir le dossier.",
    "job.show_report": "Afficher le rapport qualité",
    "job.hide_report": "Masquer le rapport qualité",
    "job.report_load_error": "Impossible de charger le rapport qualité.",
    "job.correct_translation": "Corriger la traduction",
    "job.correction_starting": "Démarrage de la correction …",
    "job.correction_opened": "Fenêtre de correction ouverte - modifiez-y le texte, puis cliquez sur « Appliquer » ou « Annuler ».",
    "job.correction_applied": "Correction appliquée.",
    "job.correction_cancelled": "Correction annulée.",
    "job.correction_timeout": "Délai d'attente dépassé pour la correction - aucune réponse de la fenêtre de correction.",
    "job.correction_failed": "Échec de la correction : {error}",
    "job.correction_error": "Impossible de démarrer la correction.",
    "job.failed_title": "Échec de la traduction",
    "correction.title": "Corriger la traduction du PDF",
    "correction.hint": "Sélectionnez une ligne ci-dessous et modifiez sa traduction dans l'éditeur situé en dessous. Utilisez Gras/Italique/Souligné (ou Ctrl+B/Ctrl+I/Ctrl+U) pour ajuster la mise en forme - les lignes modifiées conservent elles aussi leur mise en forme.",
    "correction.column_page": "Page",
    "correction.column_original": "Original",
    "correction.column_translation": "Traduction",
    "correction.editor_label": "Modifier la traduction :",
    "correction.bold": "Gras",
    "correction.italic": "Italique",
    "correction.underline": "Souligné",
    "correction.bold_tooltip": "Gras (Ctrl+B)",
    "correction.italic_tooltip": "Italique (Ctrl+I)",
    "correction.underline_tooltip": "Souligné (Ctrl+U)",
    "correction.apply": "Appliquer et enregistrer",
    "correction.close": "Fermer",
    "correction.applying": "Application en cours …",
    "correction.success": "{count} bloc(s) mis à jour et enregistré(s) dans {output}.",
    "correction.failed": "Échec de la correction : {error}",
    "image_correction.title": "Corriger la traduction de l'image",
    "image_correction.hint": "Sélectionnez une ligne ci-dessous et modifiez sa traduction dans l'éditeur situé en dessous.",
    "image_correction.canvas_hint": "Dans l'image à gauche, vous pouvez déplacer la zone d'une ligne en la faisant glisser. Sélectionnez la ligne pour faire glisser son coin inférieur droit et la redimensionner. Utilisez Ctrl+molette ou les boutons de zoom pour zoomer/dézoomer sur l'image ; la fenêtre peut aussi être agrandie au maximum.",
    "image_correction.reset_geometry": "Réinitialiser la position/taille",
    "image_correction.zoom_in": "Zoomer (+)",
    "image_correction.zoom_out": "Dézoomer (−)",
    "image_correction.zoom_reset": "Ajuster la vue",
    "image_correction.add_region": "Ajouter une nouvelle zone",
    "image_correction.add_region_hint": "Faites glisser pour délimiter une zone sur l'image afin d'y ajouter une nouvelle zone avec son propre texte.",
    "image_correction.show_original": "Afficher l'original",
    "image_correction.manual_region_label": "(ajoutée manuellement, aucune détection OCR)",
    "image_correction.manual_region_added": "Nouvelle zone ajoutée - veuillez saisir la traduction dans l'éditeur.",
    "image_correction.column_original": "Original",
    "image_correction.column_translation": "Traduction",
    "image_correction.editor_label": "Modifier la traduction :",
    "image_correction.font_size_label": "Taille de police :",
    "image_correction.font_size_auto": "Automatique",
    "image_correction.bold": "Gras",
    "image_correction.centered": "Centré",
    "image_correction.apply": "Appliquer et enregistrer",
    "image_correction.close": "Fermer",
    "image_correction.applying": "Application en cours …",
    "image_correction.success": "{count} région(s) mise(s) à jour et enregistrée(s) dans {output}.",
    "image_correction.failed": "Échec de la correction : {error}",
    "image_correction.choose_file_title": "Choisir le fichier à corriger",
    "image_correction.choose_file_label": "Quel fichier de ce traitement souhaitez-vous corriger ?",
    "update.available": "Mise à jour disponible : {version}",
    "update.confirm_title": "Installer la mise à jour ?",
    "update.confirm_body": "Une nouvelle version ({version}) est disponible. La télécharger et l'installer maintenant ?",
    "update.installing": "Installation de la mise à jour …",
    "update.success_title": "Mise à jour installée",
    "update.success_body": "La mise à jour a été installée. Veuillez redémarrer l'application pour que les modifications prennent effet.",
    "update.failed_title": "Échec de la mise à jour",
    "update.failed_body": "La mise à jour n'a pas pu être installée : {error}\n\nLa version précédemment installée continue de fonctionner sans changement.",
    "menu.help": "Aide",
    "menu.help.hw_check": "Afficher/relancer le test matériel …",
    "menu.help.check_updates": "Rechercher des mises à jour …",
    "menu.help.about": "À propos …",
    "about.body": "<h3>{app_name}</h3><p>Version {version}</p><p>Traduit des documents PDF, Word et PowerPoint ainsi que des images en conservant la mise en page.</p><p>© {year} {author}<br>Licence: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Code source: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Manuel d'utilisation …",
    "manual.hint_link": "En savoir plus dans le manuel d'utilisation (chapitre 4)",
    "manual.missing": "Le manuel d'utilisation est introuvable :\n{path}",
    "update.check.no_update_title": "Aucune mise à jour disponible",
    "update.check.no_update_body": "Vous utilisez déjà la dernière version ({version}).",
    "update.check.failed_title": "Échec de la vérification des mises à jour",
    "update.check.failed_body": "Impossible de rechercher des mises à jour : {error}",
    "hw_check.title": "Test matériel",
    "hw_check.note": "Si l'application ne se comporte pas comme prévu (par ex. avec l'inpainting IA local), vous pouvez revérifier le matériel ici.",
    "hw_check.recheck_button": "Vérifier à nouveau",
    "hw_check.checking": "Vérification du matériel …",
    "hw_check.never_checked": "Aucune vérification matérielle n'a encore été effectuée. Cliquez sur « Vérifier à nouveau » pour lancer la vérification.",
    "hw_check.not_found": "Aucun GPU CUDA détecté (dernière vérification : {checked_at}). L'inpainting IA local n'est pas disponible sur ce matériel - l'inpainting cloud fonctionne indépendamment de cela.",
    "hw_check.found_ok": "{name} détecté avec {vram_gb:.0f} Go de mémoire graphique (dernière vérification : {checked_at}). Répond à la recommandation d'au moins {min_gb:.0f} Go.",
    "hw_check.found_below_recommended": "{name} détecté avec {vram_gb:.0f} Go de mémoire graphique (dernière vérification : {checked_at}). En dessous de la recommandation de {min_gb:.0f} Go - cela peut fonctionner, mais sans garantie, surtout avec de grandes images ou de nombreuses zones de texte simultanées.",
    "hw_check.driver_cuda_ok": "Le pilote prend en charge CUDA {cuda_version} - variante PyTorch correspondante : {torch_variant}.",
    "hw_check.driver_cuda_too_old": "Le pilote ne prend en charge que CUDA {cuda_version} - trop ancien pour l'inpainting IA local (11.8 minimum requis). Veuillez mettre à jour le pilote graphique.",
    "settings.button": "Paramètres …",
    "settings.title": "Paramètres",
    "settings.language": "Langue de l'interface",
    "settings.prepared": "préparé",
    "settings.provider": "Fournisseur",
    "settings.credentials": "Identifiants",
    "settings.new_key": "Nouvelle clé API",
    "settings.key_placeholder": "N'est jamais affichée ni enregistrée dans les journaux",
    "settings.storage": "Emplacement de stockage",
    "settings.environment": "Variable d'environnement (cette session uniquement)",
    "settings.keyring": "Trousseau du système",
    "settings.both": "Les deux",
    "settings.run_limit": "Limite de coût par traitement (caractères)",
    "settings.save_key": "Enregistrer/remplacer la clé API",
    "settings.save_button": "Enregistrer",
    "settings.open_log": "Ouvrir le fichier journal …",
    "settings.session_note": "Remarque : la variable d'environnement n'est pas persistante dans cette version.",
    "settings.credentials_group": "Accès API",
    "settings.general_group": "Général",
    "settings.env_override_warning": "Ce fournisseur utilise actuellement une valeur provenant d'une variable d'environnement, et non l'entrée du trousseau enregistrée ici. Pour utiliser la clé enregistrée, supprimez cette variable d'environnement au niveau du système d'exploitation.",

    "settings.provider.tooltip": "Fournisseur dont la clé est gérée ci-dessous",
    "settings.provider.whatsthis": (
        "Sélectionne le fournisseur de traduction (DeepL, Google, "
        "OpenAI, Grok) auquel s'appliquent le statut, la nouvelle clé "
        "et l'emplacement de stockage ci-dessous. Chaque fournisseur a "
        "sa propre clé, stockée séparément."
    ),
    "settings.status.tooltip": "D'où provient la clé actuellement utilisée",
    "settings.status.whatsthis": (
        "Indique si une clé a été trouvée pour le fournisseur "
        "sélectionné dans le trousseau du système, dans une variable "
        "d'environnement, ou pas du tout. Une variable d'environnement "
        "a toujours priorité sur le trousseau - voir l'avertissement "
        "plus bas si c'est le cas ici."
    ),
    "settings.secret.tooltip": "Nouvelle clé API pour le fournisseur sélectionné",
    "settings.secret.whatsthis": (
        "Collez ici la clé API reçue du fournisseur et cliquez sur "
        "« Enregistrer ». Pendant la saisie, elle s'affiche sous forme "
        "de points mais n'est pas appliquée automatiquement - seul le "
        "bouton Enregistrer l'écrit à l'emplacement de stockage "
        "sélectionné."
    ),
    "settings.target_field.tooltip": "Où la nouvelle clé est stockée",
    "settings.target_field.whatsthis": (
        "« Trousseau du système » est le choix recommandé et durable. "
        "« Variable d'environnement » ne vaut que pour la session en "
        "cours et sert surtout à des cas particuliers/du dépannage - "
        "voir la remarque ci-dessous. « Les deux » écrit en plus une "
        "telle variable de session."
    ),
    "settings.max_chars.tooltip": "Limite de caractères par exécution de traduction",
    "settings.max_chars.whatsthis": (
        "Une exécution contenant plus de caractères que la valeur "
        "définie ici est arrêtée avec un message plutôt que "
        "d'entraîner des coûts inattendus. Augmentez-la ici si besoin."
    ),
    "settings.save_key.tooltip": "Enregistrer la nouvelle clé",
    "settings.save_key.whatsthis": (
        "Écrit la clé saisie ci-dessus pour le fournisseur sélectionné "
        "à l'emplacement de stockage choisi. Le champ de saisie est "
        "ensuite vidé et le statut ci-dessus se met à jour."
    ),
    "settings.open_log.tooltip": "Ouvrir le fichier journal de l'application",
    "settings.open_log.whatsthis": (
        "Ouvre le fichier journal actuel dans le programme par défaut "
        "du système - utile pour copier des messages d'erreur dans un "
        "rapport de bug sans faire de capture d'écran."
    ),

    "hw_check.status.tooltip": "Résultat de la dernière vérification GPU",
    "hw_check.status.whatsthis": (
        "Indique si un GPU NVIDIA pris en charge avec suffisamment de "
        "VRAM a été trouvé, la date de la dernière vérification, et si "
        "la version CUDA du pilote installé prend en charge "
        "l'inpainting GPU local. Sans GPU/pilote adapté, l'inpainting "
        "local fonctionne quand même - juste plus lentement, sur le "
        "CPU."
    ),
    "hw_check.recheck_button.tooltip": "Relancer la vérification GPU maintenant",
    "hw_check.recheck_button.whatsthis": (
        "Relance la même vérification que celle effectuée par "
        "l'installateur - utile après une mise à jour de pilote ou un "
        "changement de carte graphique, sans devoir réinstaller "
        "l'application."
    ),

    "bootstrap.help.back_button": (
        "Retour à l'étape précédente\n\n"
        "Ce qui a déjà été saisi à cette étape et à la précédente est "
        "conservé."
    ),
    "bootstrap.help.next_button": "Passer à l'étape suivante",
    "bootstrap.help.cancel_button": (
        "Ferme cet assistant\n\n"
        "Une confirmation sera demandée si une installation est en "
        "cours. La configuration peut être relancée à tout moment."
    ),
    "bootstrap.help.language_combo": (
        "Langue de cet assistant\n\n"
        "S'applique immédiatement à tous les écrans de cet assistant. "
        "L'application elle-même aura plus tard son propre choix de "
        "langue, indépendant."
    ),
    "bootstrap.help.mode_online_radio": (
        "La traduction passe par des fournisseurs cloud (DeepL, Google, "
        "OpenAI, Grok) ; le traitement d'image utilise ici une méthode "
        "plus simple que l'inpainting basé sur l'IA\n\n"
        "Installation la plus rapide et la plus simple, fonctionne sur "
        "n'importe quelle machine. Nécessite votre propre clé API du "
        "fournisseur choisi et une connexion internet pendant la "
        "traduction."
    ),
    "bootstrap.help.mode_local_radio": (
        "Traitement d'image amélioré par IA sur cette carte graphique, "
        "au lieu de la méthode standard plus simple\n\n"
        "Nécessite une carte graphique NVIDIA prise en charge avec "
        "suffisamment de mémoire vidéo (vérifié à l'étape suivante) - en "
        "contrepartie, les images ne quittent jamais cette machine."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Poursuivre quand même l'installation locale\n\n"
        "Utile si la vérification a échoué à tort ou si une mise à jour "
        "de pilote est encore en attente - le traitement local peut être "
        "revérifié à tout moment via Aide -> Test matériel."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Installer plutôt la variante en ligne\n\n"
        "Bascule cette installation vers les fournisseurs cloud, sans "
        "question sur le GPU. Peut être ajouté plus tard à tout moment "
        "via les paramètres de l'application."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Saisir une clé API pour {provider} à l'étape suivante\n\n"
        "Les fournisseurs non cochés peuvent toujours être ajoutés plus "
        "tard dans les paramètres de l'application."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Continuer sans saisir aucune clé\n\n"
        "Les clés peuvent toujours être ajoutées plus tard dans les "
        "paramètres de l'application - mais aucune traduction ne "
        "fonctionnera sans au moins une clé."
    ),
    "bootstrap.help.credentials_continue_button": "Passer à la saisie de la clé, ou au fournisseur suivant",
    "bootstrap.help.credential_open_signup_button": (
        "Ouvre la page d'inscription de ce fournisseur dans le "
        "navigateur\n\n"
        "C'est là que la clé API est générée, pour être collée ici "
        "ensuite."
    ),
    "bootstrap.help.credential_key_entry": (
        "Collez ici la clé API de ce fournisseur\n\n"
        "Affichée sous forme de points pendant la saisie. Seul le bouton "
        "Enregistrer ci-dessous l'applique réellement."
    ),
    "bootstrap.help.credential_save_button": "Enregistrer maintenant la clé saisie ci-dessus",
    "bootstrap.help.finish_close_button": "Fermer l'assistant sans lancer l'application maintenant",
    "bootstrap.help.finish_launch_button": "Fermer l'assistant et lancer l'application immédiatement",
    "credentials.title": "Identifiants",
    "credentials.saved": "La clé API a été enregistrée.",
    "credential.environment": "Variable d'environnement (session)",
    "credential.keyring": "Trousseau du système",
    "credential.missing": "Non configuré",
    "provider.missing_key": "Aucune clé API configurée pour « {provider} ». <a href=\"settings\">Configurer maintenant</a>",
    "provider.missing_key_dialog": "Aucune clé API n'est configurée pour le fournisseur « {provider} ». Sans clé, chaque appel de traduction échouera.",
    "dialog.check_input": "Vérifier les entrées",
    "dialog.analysis": "Analyse",
    "dialog.choose_images": "Sélectionner des images",
    "dialog.choose_document": "Sélectionner un document",
    "merge.button": "Fusionner/insérer des PDF …",
    "merge.title": "Fusionner/insérer des PDF",
    "merge.intro": "Assemblez les fichiers sources dans l'ordre souhaité. Pour chaque fichier, vous pouvez indiquer une sélection de pages facultative (vide = fichier entier) - ajoutez plusieurs fois le même fichier avec des sélections de pages différentes pour l'insérer à un endroit précis dans un autre fichier.",
    "merge.column_file": "Fichier",
    "merge.column_pages": "Pages",
    "merge.pages_placeholder": "toutes",
    "merge.pages_tooltip": "Vide = fichier entier. Sinon, par ex. \"1-3,5\" ou \"6-\" (de la page 6 jusqu'à la fin) ou \"-4\" (du début à la page 4). \"5-3\" insère les pages 5,4,3 dans cet ordre (inversé).",
    "merge.add_files": "Ajouter des fichiers …",
    "merge.remove_selected": "Supprimer",
    "merge.move_up": "Monter",
    "merge.move_down": "Descendre",
    "merge.sort_by_name": "Trier par nom",
    "merge.sort_by_date": "Trier par date",
    "merge.sort_by_date_tooltip": "Trie selon la date de dernière modification du fichier sur le disque (pas la date de création).",
    "merge.output_file_label": "Fichier de destination",
    "merge.output_placeholder": "Choisir un fichier de destination …",
    "merge.choose_output_file": "Enregistrer sous …",
    "merge.start_button": "Démarrer la fusion",
    "merge.cancel_button": "Annuler",
    "merge.close_button": "Fermer",
    "merge.status_running": "Traitement en cours : {message}",
    "merge.status_done": "Terminé : {pages} page(s) écrite(s) à partir de {files} fichier(s).",
    "merge.status_cancelled": "Annulé (résultat partiel enregistré) : {pages} page(s) écrite(s).",
    "merge.status_failed": "Échec : {error}",
    "merge.error_dialog_choose_files": "Sélectionner des fichiers PDF",
    "merge.error_dialog_choose_output": "Choisir le fichier de destination",
    "merge.failed_title": "Échec de la fusion",
    "merge_search.button": "Rechercher dans un dossier …",
    "merge_search.title": "Rechercher des PDF dans un dossier",
    "merge_search.folder_label": "Dossier",
    "merge_search.folder_placeholder": "Choisir un dossier …",
    "merge_search.choose_folder": "Choisir un dossier …",
    "merge_search.choose_folder_dialog_title": "Choisir un dossier à parcourir",
    "merge_search.recursive_checkbox": "Inclure les sous-dossiers",
    "merge_search.scope_ico_format": "Format ICO (zone d'en-tête page 1)",
    "merge_search.scope_header": "En-tête (toutes les pages)",
    "merge_search.scope_full_text": "Texte intégral",
    "merge_search.scope_ico_format_tooltip": "Recherche UNIQUEMENT dans le bloc de métadonnées ICO de la page 1 (Developer, QSI ICO, date d'émission, ...). Indépendant du « En-tête » ci-dessous - si seule cette option est cochée, la zone d'en-tête récurrente sur les AUTRES pages n'est PAS recherchée.",
    "merge_search.scope_header_tooltip": "Recherche UNIQUEMENT dans la zone supérieure récurrente sur chaque page (par ex. la ligne nom d'entreprise/logo). Indépendant du « Format ICO » ci-dessus - une région de texte distincte, pas une extension de celle-ci.",
    "merge_search.scope_full_text_tooltip": "Recherche dans la TOTALITÉ du texte sur toutes les pages, y compris les zones « Format ICO » et « En-tête » ci-dessus.",
    "merge_search.error_missing_scope": "Veuillez sélectionner au moins une zone de recherche.",
    "merge_search.date_filter_group": "Filtrer par date",
    "merge_search.date_source_file": "Date du fichier",
    "merge_search.date_source_document": "Date dans le document",
    "merge_search.date_region_ico_format": "Champ ICO (page 1)",
    "merge_search.date_region_header": "En-tête (toutes les pages)",
    "merge_search.date_region_footer": "Pied de page (toutes les pages)",
    "merge_search.date_format_iso": "ISO (AAAA-MM-JJ)",
    "merge_search.date_format_iso_tooltip": "Reconnaît par ex. « 2026-09-04 ».",
    "merge_search.date_format_de": "Allemand (JJ.MM.AAAA)",
    "merge_search.date_format_de_tooltip": "Reconnaît par ex. « 04.09.2026 » (également les années à deux chiffres comme « 04.09.26 »).",
    "merge_search.date_format_en_month": "Anglais (nom du mois, par ex. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Reconnaît aussi bien « September 4, 2026 » que « 4 September 2026 » (virgule facultative, jour avec ou sans zéro initial).",
    "merge_search.date_format_slash": "Barre oblique (JJ/MM/AAAA)",
    "merge_search.date_format_slash_tooltip": "Reconnaît par ex. « 04/09/2026 ».",
    "merge_search.date_exact_checkbox": "Date exacte",
    "merge_search.date_from_label": "Du",
    "merge_search.date_to_label": "Au",
    "merge_search.date_exact_label": "Date",
    "merge_search.error_date_range_reversed": "« Du » ne doit pas être postérieur à « Au ».",
    "merge_search.error_missing_date_region": "Veuillez sélectionner au moins une zone pour la recherche de date.",
    "merge_search.error_missing_date_format": "Veuillez sélectionner au moins un format de date ou saisir un format personnalisé.",
    "merge_search.date_custom_format_label": "Format personnalisé",
    "merge_search.date_custom_format_placeholder": "par ex. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Format de date personnalisé utilisant ces symboles (à saisir toujours en anglais, même dans cette boîte de dialogue en français) - tous les autres caractères comme les espaces, virgules, points ou barres obliques sont recherchés littéralement :\n\nYYYY – année, 4 chiffres, par ex. 2026\nYY – année, 2 chiffres, par ex. 26\nMMMM – nom du mois, par ex. September\nMMM – nom du mois abrégé, par ex. Sep\nMM – mois, 2 chiffres, par ex. 09\nM – mois, 1 ou 2 chiffres, par ex. 9\nDD – jour, 2 chiffres, par ex. 04\nD – jour, 1 ou 2 chiffres, par ex. 4\n\nExemples :\n« MMMM D, YYYY » trouve « September 4, 2026 »\n« MMMM DD, YYYY » trouve « September 04, 2026 »\n« YYYY/MM/DD » trouve « 2026/09/04 »",
    "merge_search.error_invalid_custom_date_format": "Le format de date personnalisé n'est pas valide - veuillez utiliser les symboles indiqués dans l'infobulle.",
    "merge_search.query_label": "Texte de recherche (combinez les termes avec AND/OR ou &&/||)",
    "merge_search.query_placeholder": "par ex. le nom de la société du développeur, ou terme1 AND terme2 - laissez vide pour tous les fichiers du dossier",
    "merge_search.query_tooltip": "Plusieurs termes de recherche peuvent être combinés avec AND et OR - même mélangés. Utilisez des parenthèses pour préciser ce qui va ensemble.\n\nExemple : « Acme AND contrat » ne trouve que les fichiers contenant les DEUX termes.\n« Acme OR Zenith » trouve les fichiers contenant AU MOINS L'UN des deux termes.\n\nMélangé avec des parenthèses : « StellarRussia OR (The AND Korolev AND Directive) » trouve les fichiers contenant « StellarRussia » OR les fichiers contenant les TROIS termes « The », « Korolev » et « Directive ».\n\nÀ la place de AND/OR, vous pouvez aussi utiliser les symboles && et || (équivalents, même mélangés avec les mots) : « Acme && contrat » équivaut à « Acme AND contrat ».\n\nSans AND/OR, tout le texte est traité comme un seul terme de recherche (comme auparavant). La casse n'a pas d'importance.",
    "merge_search.search_button": "Rechercher",
    "merge_search.cancel_button": "Annuler",
    "merge_search.select_all": "Tout sélectionner",
    "merge_search.select_none": "Ne rien sélectionner",
    "merge_search.detach_results_button": "Ouvrir la liste des résultats dans une fenêtre séparée",
    "merge_search.reattach_results_button": "Réintégrer la liste des résultats",
    "merge_search.results_detached_placeholder": "La liste des résultats est ouverte dans une fenêtre séparée.",
    "merge_search.detached_results_title_suffix": "Résultats",
    "merge_search.take_selected": "Ajouter la sélection",
    "merge_search.close_button": "Fermer",
    "merge_search.status_running": "Recherche en cours : {current} ({done}/{total})",
    "merge_search.status_done": "{matches} résultat(s) sur {scanned} PDF analysé(s).",
    "merge_search.status_done_with_errors": "{matches} résultat(s) sur {scanned} PDF analysé(s) ({errors} illisible(s)).",
    "merge_search.status_cancelled": "Annulé : {matches} résultat(s) sur {scanned} PDF analysé(s).",
    "merge_search.status_failed": "Échec : {error}",
    "merge_search.error_missing_folder": "Veuillez d'abord choisir un dossier.",
    "merge_search.failed_title": "Échec de la recherche",
    "merge_search.source_local": "Dossier local",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Lien ou ID du dossier Drive",
    "merge_search.drive_folder_placeholder": "Coller le lien de partage ou l'ID du dossier …",
    "merge_search.drive_resolve_button": "Vérifier",
    "merge_search.drive_folder_unresolved": "Pas encore vérifié.",
    "merge_search.drive_folder_resolved": "Dossier « {name} » trouvé.",
    "merge_search.drive_folder_resolve_failed": "Échec : {error}",
    "merge_search.drive_cache_label": "Dossier de cache (les téléchargements y restent conservés)",
    "merge_search.drive_choose_cache": "Choisir un dossier de cache …",
    "merge_search.drive_choose_cache_dialog_title": "Choisir un dossier pour les résultats téléchargés",
    "merge_search.drive_credentials_label": "Identifiants OAuth Google (à configurer une seule fois, voir docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Charger depuis un fichier JSON …",
    "merge_search.drive_load_from_file_dialog_title": "Choisir le fichier JSON de secrets client depuis Google Cloud Console",
    "merge_search.drive_load_from_file_failed": "Impossible de lire le fichier : {error}",
    "merge_search.drive_client_id_placeholder": "ID client",
    "merge_search.drive_client_secret_placeholder": "Secret client",
    "merge_search.drive_project_id_placeholder": "ID du projet",
    "merge_search.drive_save_credentials": "Enregistrer les identifiants",
    "merge_search.drive_credentials_saved": "Identifiants enregistrés.",
    "merge_search.drive_save_failed": "Échec de l'enregistrement : {error}",
    "merge_search.drive_not_configured": "Aucun ID client/secret client/ID de projet renseigné pour l'instant.",
    "merge_search.drive_configured_not_connected": "Configuré, mais pas encore connecté.",
    "merge_search.drive_connected": "Connecté{account}.",
    "merge_search.drive_connect_button": "Se connecter à Google",
    "merge_search.drive_disconnect_button": "Déconnecter",
    "merge_search.drive_connecting": "Ouverture du navigateur pour la connexion …",
    "merge_search.drive_connect_failed": "Échec de la connexion : {error}",
    "merge_search.drive_error_missing_folder": "Veuillez d'abord indiquer et vérifier un dossier Drive.",
    "merge_search.drive_error_missing_cache": "Veuillez d'abord choisir un dossier de cache.",
    "merge_search.drive_error_not_connected": "Veuillez d'abord vous connecter à Google.",
    "word_merge.button": "Fusionner/insérer des fichiers DOCX …",
    "word_merge.title": "Fusionner/insérer des fichiers DOCX",
    "word_merge.intro": "Assemblez les fichiers sources dans l'ordre souhaité - toujours des fichiers entiers (contrairement au PDF, le format DOCX ne connaît pas de nombre de pages fixe dans le format de fichier lui-même). Ajoutez plusieurs fois le même fichier pour l'insérer à plusieurs endroits. Au-delà de 100 fichiers, la fusion se fait automatiquement par groupes (voir la ligne d'état après le traitement).",
    "word_merge.status_done": "Terminé : {segments} sur {files} fichier(s) pris en compte{batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Annulé (résultat partiel enregistré) : {segments} fichier(s) pris en compte{batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " en {batches} groupe(s)",
    "word_merge.status_warning_suffix": ", {count} ignoré(s) (voir ci-dessous)",
    "word_merge.warnings_title": "Fichiers ignorés :",
    "word_merge.error_dialog_choose_files": "Sélectionner des fichiers DOCX",
    "word_merge_search.title": "Rechercher des fichiers DOCX dans un dossier",
    "word_merge_search.status_done": "{matches} résultat(s) sur {scanned} fichier(s) DOCX analysé(s).",
    "word_merge_search.status_done_with_errors": "{matches} résultat(s) sur {scanned} fichier(s) DOCX analysé(s) ({errors} illisible(s)).",
    "word_merge_search.status_cancelled": "Annulé : {matches} résultat(s) sur {scanned} fichier(s) DOCX analysé(s).",
    "bootstrap.window_title": "Configurer Document Translator",
    "bootstrap.back_button": "Précédent",
    "bootstrap.next_button": "Suivant",
    "bootstrap.cancel_button": "Annuler",
    "bootstrap.cancel_title": "Annuler l'installation ?",
    "bootstrap.cancel_confirm": (
        "L'assistant d'installation va se fermer sans que Document Translator "
        "soit entièrement configuré. Les fichiers déjà créés seront "
        "supprimés automatiquement. Continuer ?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "L'installation est en cours. L'annuler supprimera "
        "automatiquement les fichiers déjà créés - dans de rares cas, "
        "un fichier encore utilisé à cet instant précis peut subsister. "
        "Annuler quand même ?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Droits administrateur",
    "bootstrap.elevated_warning_text": (
        "Document Translator a été démarré en tant qu'administrateur.\n\n"
        "Ce n'est pas nécessaire et cela empêchera l'application de "
        "fonctionner plus tard lors d'un démarrage normal (sans droits "
        "administrateur).\n\n"
        "Veuillez fermer cette fenêtre et relancer l'installation par un "
        "double-clic normal (sans « Exécuter en tant qu'administrateur »).\n\n"
        "Ce message peut être copié avec Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Désinstaller Document Translator",
    "bootstrap.uninstall_confirm": (
        "Supprimer Document Translator, y compris tous les paramètres et clés "
        "API stockés localement ?"
    ),
    "bootstrap.uninstall_done": "Document Translator a été supprimé.",
    "bootstrap.welcome_title": "Bienvenue",
    "bootstrap.welcome_text": "Cet assistant configure Document Translator sur cet ordinateur - sans aucune ligne de commande. Il télécharge les composants nécessaires et crée, à la fin, une entrée dans le menu des applications.",
    "bootstrap.language_label": "Langue",
    "bootstrap.mode_title": "En ligne ou local ?",
    "bootstrap.mode_intro": "Comment souhaitez-vous traduire ? Vous pourrez modifier ce choix à tout moment plus tard dans les paramètres.",
    "bootstrap.mode_online_label": "En ligne (fournisseur cloud)",
    "bootstrap.mode_online_desc": "La traduction passe par un fournisseur externe (DeepL, Google, OpenAI ou Grok). Cela entraîne des coûts récurrents par traduction, et nécessite votre propre clé API du fournisseur concerné - plus de détails juste après. Le traitement d'image sur les images intégrées fonctionne aussi ici, avec une méthode plus simple plutôt que l'inpainting basé sur l'IA. Aucun téléchargement volumineux n'est nécessaire. Recommandé si vous ne disposez pas d'une carte graphique puissante.",
    "bootstrap.mode_local_label": "Local (sur cette carte graphique)",
    "bootstrap.mode_local_desc": "Améliore uniquement le traitement d'image : le texte intégré aux images est détecté par OCR puis redessiné avec un modèle d'IA (LaMa) directement sur cette carte graphique après traduction - le résultat est plus net que la méthode plus simple disponible sans cette option. La traduction du texte proprement dite passe, dans les deux modes, par un fournisseur externe (DeepL, Google, OpenAI ou Grok), avec le coût habituel par traduction chez ce fournisseur. Des fournisseurs en ligne peuvent en plus être configurés à tout moment dans les paramètres si vous le souhaitez. Nécessite une carte graphique NVIDIA suffisamment puissante (vérifiée à l'étape suivante) et télécharge environ 2 à 3 Go une seule fois pendant l'installation.",
    "bootstrap.gpu_checking": "Vérification de la carte graphique …",
    "bootstrap.gpu_ok": "Trouvée : {name} avec {vram_gb:.0f} Go de mémoire graphique - c'est suffisant.",
    "bootstrap.gpu_insufficient": "Trouvée : {name} avec {vram_gb:.0f} Go de mémoire graphique - au moins {min_gb:.0f} Go sont recommandés. Le mode local sera probablement très lent.",
    "bootstrap.gpu_not_found": "Aucune carte graphique NVIDIA prise en charge n'a été trouvée. Le mode local n'est pas utilisable de manière pertinente sur cet ordinateur.",
    "bootstrap.gpu_driver_too_old": "Trouvée : {name}, mais le pilote NVIDIA est trop ancien (ne prend en charge que CUDA {cuda_version}, 11.8 minimum requis). Veuillez mettre à jour le pilote graphique et relancer l'assistant, ou choisir En ligne à la place.",
    "bootstrap.gpu_mac_unsupported": "Le mode local n'est actuellement pas pris en charge sur Mac. Veuillez choisir En ligne à la place.",
    "bootstrap.gpu_continue_local_button": "Continuer en local malgré tout",
    "bootstrap.gpu_switch_online_button": "Passer en ligne",
    "bootstrap.install_title": "Installation en cours",
    "bootstrap.install_step_venv": "Création de l'environnement de travail …",
    "bootstrap.install_step_deps": "Installation des composants ({name}) …",
    "bootstrap.install_step_source": "Téléchargement du code du programme …",
    "bootstrap.install_step_shortcut": "Création de l'entrée dans le menu des applications …",
    "bootstrap.install_failed_title": "Échec de l'installation",
    "bootstrap.install_failed": "Échec : {error}",
    "bootstrap.credentials_title": "Configurer les clés API",
    "bootstrap.credentials_intro": "Quels fournisseurs souhaitez-vous configurer ? Vous pouvez ignorer cette étape et la faire plus tard dans les paramètres de l'application.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Inscription rapide en libre-service. Un quota gratuit est disponible, puis payant au-delà.",
    "bootstrap.credentials_explain_google": "Nécessite un projet Google Cloud avec un moyen de paiement enregistré - un peu plus complexe à configurer que les trois autres fournisseurs.",
    "bootstrap.credentials_explain_openai": "Inscription rapide en libre-service, facturée à l'usage.",
    "bootstrap.credentials_explain_grok": "Inscription rapide en libre-service, facturée à l'usage.",
    "bootstrap.credentials_open_signup_button": "Obtenir une clé (ouvre le navigateur)",
    "bootstrap.open_browser_title": "Ouvrir le navigateur ?",
    "bootstrap.open_browser_text": (
        "Le lien suivant sera ouvert dans le navigateur par défaut :\n\n"
        "{url}\n\n"
        "Veuillez vérifier qu'il s'agit bien de l'adresse attendue avant "
        "de continuer."
    ),
    "bootstrap.credentials_key_label": "Clé API pour {provider}",
    "bootstrap.credentials_key_placeholder": "Coller la clé …",
    "bootstrap.credentials_save_button": "Enregistrer",
    "bootstrap.credentials_saved": "Enregistré.",
    "bootstrap.credentials_skip_all_button": "Plus tard, dans les paramètres",
    "bootstrap.credentials_continue_button": "Suivant",
    "bootstrap.finish_title": "Terminé",
    "bootstrap.finish_text": "Document Translator est configuré et disponible dans le menu des applications.",
    "bootstrap.finish_download_size": "Réellement téléchargé : environ {size_gb:.1f} Go.",
    "bootstrap.finish_launch_button": "Lancer maintenant",
    "bootstrap.finish_close_button": "Fermer",
    "mode.tooltip": "Type de document à traduire",
    "mode.whatsthis": (
        "Détermine le flux de traduction utilisé : PDF, PowerPoint/"
        "Impress, Word/Writer ou images individuelles. Selon le choix, "
        "seuls les champs pertinents s'affichent plus bas, par exemple "
        "les réglages OCR uniquement en mode « Images »."
    ),
    "source.tooltip": "Sélectionner le(s) fichier(s) à traduire",
    "source.whatsthis": (
        "Ouvre la boîte de dialogue de sélection de fichier pour le "
        "fichier source (plusieurs fichiers à la fois en mode Images). "
        "Le nom du fichier choisi apparaît ensuite à gauche."
    ),
    "source_label.tooltip": "Fichier source actuellement sélectionné",
    "source_label.whatsthis": (
        "Affiche le nom du fichier choisi via « Sélectionner un "
        "fichier … ». S'il indique encore « Aucun fichier sélectionné », "
        "il faut d'abord choisir un fichier avant qu'une analyse des "
        "coûts soit possible."
    ),
    "image_mode.tooltip": "Traitement des images intégrées au document",
    "image_mode.whatsthis": (
        "« Ne pas traduire » laisse les images intégrées inchangées. "
        "« Sélectionner individuellement plus tard » affiche une liste "
        "après l'analyse des coûts pour choisir des images précises. "
        "« Traduire toutes » traite automatiquement chaque image "
        "intégrée."
    ),
    "provider.tooltip": "Fournisseur de traduction pour cette exécution",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI ou Grok - chacun avec sa propre clé API, "
        "gérée dans les Paramètres. Si aucune clé n'est configurée pour "
        "le fournisseur choisi, un message avec un lien vers les "
        "Paramètres apparaît juste en dessous."
    ),
    "source_lang.tooltip": "Code de la langue source, p. ex. EN",
    "source_lang.whatsthis": (
        "Code de langue à deux lettres selon ISO 639-1 (p. ex. EN pour "
        "l'anglais, FR pour le français). Doit correspondre à la langue "
        "réelle du document, sinon le fournisseur de traduction renvoie "
        "des résultats erronés ou aucun résultat."
    ),
    "target_lang.tooltip": "Code de la langue cible, p. ex. DE",
    "target_lang.whatsthis": (
        "Code de langue à deux lettres selon ISO 639-1 vers laquelle "
        "traduire (p. ex. DE pour l'allemand, ES pour l'espagnol)."
    ),
    "protected.tooltip": "Termes à ne pas traduire",
    "protected.whatsthis": (
        "Un terme par ligne, p. ex. des noms d'entreprise ou de produit. "
        "Le fournisseur de traduction laisse ces termes inchangés. Le "
        "bouton juste à côté permet aussi de charger une liste depuis un "
        "fichier."
    ),
    "ocr_engine_field.tooltip": "Reconnaissance de texte (OCR) pour les images",
    "ocr_engine_field.whatsthis": (
        "Visible uniquement en mode « Images ». Reconnaît le texte dans "
        "les images avant qu'il ne soit traduit puis réinséré. Si un "
        "moteur n'est pas disponible sur cette machine, un message "
        "apparaît juste en dessous."
    ),
    "inpainting_backend_field.tooltip": (
        "Méthode de réinsertion du texte traduit dans l'image"
    ),
    "inpainting_backend_field.whatsthis": (
        "Visible uniquement en mode « Images ». « Superposition de "
        "boîte » et « CV Inpainting » fonctionnent toujours localement, "
        "sans matériel particulier. « GPU Inpainting » utilise une carte "
        "graphique locale (CUDA) pour le meilleur résultat et n'est "
        "disponible que si PyTorch avec support CUDA est installé - "
        "sinon un message apparaît en dessous. L'état du matériel peut "
        "être vérifié à tout moment via Aide -> Test matériel."
    ),
    "merge.tooltip": "Fusionner plusieurs fichiers PDF",
    "merge.whatsthis": (
        "Ouvre une boîte de dialogue séparée pour fusionner plusieurs "
        "fichiers PDF en un seul. Indépendant du formulaire ci-dessus - "
        "rien n'est traduit ici."
    ),
    "word_merge.tooltip": "Fusionner plusieurs fichiers Word",
    "word_merge.whatsthis": (
        "Ouvre une boîte de dialogue séparée pour fusionner plusieurs "
        "fichiers Word en un seul. Indépendant du formulaire ci-dessus - "
        "rien n'est traduit ici."
    ),
    "analysis.button.tooltip": "Estimer le coût de cette traduction",
    "analysis.button.whatsthis": (
        "Compte les caractères à traduire et estime le coût approximatif "
        "selon le fournisseur choisi, sans encore rien traduire. Ce "
        "n'est qu'ensuite que la case à cocher juste à côté peut être "
        "cochée et « Démarrer » activé."
    ),
    "analysis.checked.tooltip": "Confirmer les coûts estimés",
    "analysis.checked.whatsthis": (
        "Doit être cochée avant que « Démarrer » ne devienne cliquable - "
        "une étape de sécurité volontaire pour qu'aucune exécution ne "
        "démarre par accident sans avoir d'abord vu les coûts estimés."
    ),
    "start.tooltip": "Démarrer la traduction",
    "start.whatsthis": (
        "Activé seulement après analyse et confirmation des coûts. La "
        "progression apparaît dans la zone en dessous ; une exécution en "
        "cours peut être arrêtée via « Annuler »."
    ),
    "job.cancel.tooltip": "Annuler la traduction en cours",
    "job.cancel.whatsthis": (
        "Arrête l'exécution en cours aussi vite que possible. Les "
        "parties déjà traitées ne sont pas automatiquement conservées "
        "comme fichier complet - selon le format, un fichier incomplet "
        "peut subsister."
    ),
    "job.open_folder.tooltip": "Ouvrir le dossier de sortie",
    "job.open_folder.whatsthis": (
        "Ouvre l'explorateur de fichiers dans le dossier de destination "
        "de l'exécution qui vient de se terminer."
    ),
    "job.open_report.tooltip": "Ouvrir le rapport qualité de la dernière exécution",
    "job.open_report.whatsthis": (
        "Affiche les points relevés par le contrôle qualité automatique "
        "de la dernière exécution, par exemple des passages qu'il "
        "pourrait être utile de vérifier."
    ),
    "job.correct_translation.tooltip": "Corriger des traductions individuelles",
    "job.correct_translation.whatsthis": (
        "Visible uniquement pour les exécutions PDF avec des blocs de "
        "texte corrigibles. Permet de retravailler des passages traduits "
        "précis sans refaire toute l'exécution."
    ),
    "settings.button.tooltip": "Ouvrir les paramètres",
    "settings.button.whatsthis": (
        "Clés API par fournisseur (recommandé : trousseau), limite de "
        "caractères par exécution et accès au fichier journal."
    ),
    "update_hint.tooltip": "Une nouvelle version est disponible",
    "update_hint.whatsthis": (
        "Apparaît automatiquement lorsqu'une version plus récente de "
        "Document Translator a été trouvée au démarrage. Cliquer dessus "
        "propose d'installer la nouvelle version."
    ),
    "flag_row.whatsthis": (
        "Change immédiatement et durablement la langue de l'interface "
        "elle-même - pas les langues de traduction du formulaire. Le "
        "choix est enregistré aussitôt."
    ),
    "menu.help.whats_this": "Qu'est-ce que c'est ?",
}


ES = {
    "app.title": "Document Translator",
    "mode.pdf": "Traducir PDF",
    "mode.presentation": "Traducir presentación (PowerPoint/Impress)",
    "mode.word": "Traducir documento de Word/Writer",
    "mode.images": "Traducir imágenes individuales",
    "source.none": "Ningún archivo seleccionado",
    "source.choose": "Seleccionar archivo…",
    "image.none": "No traducir imágenes incrustadas",
    "image.selected": "Seleccionar imágenes individualmente más tarde",
    "image.all": "Traducir todas las imágenes incrustadas",
    "field.mode": "Tarea",
    "field.source": "Origen",
    "field.images": "Imágenes en el documento",
    "field.provider": "Proveedor de traducción",
    "field.source_language": "Idioma de origen",
    "field.target_language": "Idioma de destino",
    "field.protected_terms": "Términos protegidos",
    "field.ico_mode": "Documento ICO",
    "ico_mode.checkbox": "No traducir la zona de la página 1",
    "ico_mode.tooltip": "Solo para el tipo de documento interno ICO: excluye de la traducción el bloque de metadatos de la página 1 (en Word: la zona anterior a la línea separadora; en PDF: detectada mediante términos de referencia como \"Issuer Address\"/\"Asset Matrix\"), independientemente de si ese bloque se encuentra realmente. Déjelo desactivado para el resto de documentos.",
    "field.side_by_side": "Vista en paralelo",
    "side_by_side.checkbox": "Original y traducción en paralelo",
    "side_by_side.tooltip": "Solo Word: genera el texto principal como una tabla comparativa de dos columnas (Original | Traducción) en formato horizontal, en lugar del resultado normal con el diseño original. El encabezado y el pie de página no cambian. Las tablas incrustadas en el texto principal (si las hay) no aparecen en esta vista.",
    "field.exclude_header": "Encabezado",
    "exclude_header.checkbox": "No traducir el encabezado recurrente",
    "exclude_header.tooltip": "Detecta automáticamente el texto que se repite cerca de la parte superior en la mayoría de las páginas (idéntico, o solo con el número de página distinto) y lo excluye de la traducción. Si no se encuentra nada coincidente, no cambia nada.",
    "field.exclude_footer": "Pie de página",
    "exclude_footer.checkbox": "No traducir el pie de página recurrente",
    "exclude_footer.tooltip": "Igual que con el encabezado, pero para el texto que se repite cerca de la parte inferior de la página (p. ej., línea de copyright, número de página).",
    "field.ocr_engine": "Motor de OCR",
    "ocr_engine.tesseract": "Tesseract (local)",
    "ocr_engine.tesseract.unavailable": "No se encontró Tesseract en este sistema. Instálelo (véase README.md); sin Tesseract instalado no se puede reconocer texto en las imágenes.",
    "ocr_engine.google_vision": "Google Cloud Vision (nube, detección de párrafos)",
    "ocr_engine.google_vision.unavailable": "No hay ninguna clave de API de Google configurada. Introdúzcala en Ajustes (la misma clave que para Google Translate, véase README.md) o elija otro motor de OCR.",
    "ocr_engine.paddleocr": "PaddleOCR (local, detección de párrafos)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR no está instalado (véase requirements-paddleocr.txt) o elija otro motor de OCR.",
    "ocr_engine.unavailable": "Este motor de OCR no está disponible en este sistema.",
    "field.inpainting_backend": "Método de reescritura",
    "inpainting_backend.box_overlay": "Superposición de caja (cubrir la zona)",
    "inpainting_backend.cv_inpainting": "Inpainting clásico por CPU (reconstruir el fondo)",
    "inpainting_backend.gpu_inpainting": "Inpainting con IA local (GPU, LaMa)",
    "inpainting_backend.unavailable": "No se encontró ninguna GPU CUDA para este método (véase requirements-gpu.txt) - elija otro método de reescritura.",
    "inpainting_backend.below_recommended_vram": "Solo se detectaron {vram_gb:.0f} GB de memoria de vídeo (recomendado: al menos {min_gb:.0f} GB) - puede funcionar, pero sin garantía, especialmente con imágenes grandes o muchas zonas de texto a la vez.",
    "source_language.placeholder": "opcional / automático",
    "protected.placeholder": "Un término protegido por línea",
    "protected.load_file": "Cargar desde archivo…",
    "protected.load_file.tooltip": "Importa términos desde un archivo CSV o de texto (un término por línea; en CSV se usa la primera columna). Las entradas existentes se conservan y los duplicados se omiten.",
    "protected.loaded": "Se importaron {added} términos nuevos desde {name} ({total} en el archivo).",
    "protected.load_error": "No se pudo leer {name}: {error}",
    "dialog.choose_protected_terms": "Seleccionar lista de términos",
    "dialog.all_files": "Todos los archivos",
    "merge_box.group": "Combinar archivos",
    "config.group": "Configurar tarea",
    "analysis.group": "Análisis y control de costes",
    "analysis.required": "Antes de iniciar es necesario realizar un análisis.",
    "analysis.button": "Analizar documento y estimar costes",
    "analysis.running": "Analizando…",
    "analysis.checked": "He revisado el análisis y la estimación de costes",
    "analysis.failed": "Error en el análisis.",
    "analysis.no_warnings": "Sin advertencias de análisis.",
    "analysis.within": "dentro del límite",
    "analysis.exceeded": "SUPERADO",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} caracteres de texto · {images}<br>Estimación local ({provider}): uso mensual {usage:,} / cuota gratuita {free:,} caracteres · estimación ${cost:.2f}<br>Límite por ejecución {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Cuota en tiempo real (DeepL, consultada ahora):</b> {used:,} de {limit:,} caracteres consumidos, {remaining:,} restantes.",
    "analysis.live_quota_unlimited": "<b>Cuota en tiempo real (DeepL, consultada ahora):</b> {used:,} caracteres consumidos; la cuenta no indica ningún límite.",
    "unit.pages": "páginas",
    "unit.slides": "diapositivas",
    "unit.paragraphs": "párrafos",
    "unit.images": "imágenes",
    "warning.scan_pdf": "Se detectó un PDF de imagen/escaneado: se requiere OCR para el texto del documento.",
    "warning.image_cost_unknown": "Los caracteres de OCR y el coste de traducción de imágenes solo se conocen después del OCR.",
    "warning.image_selection_later": "La selección concreta de imágenes se realizará tras el análisis, en una futura versión de la interfaz.",
    "warning.embedded_images_not_estimated": "El texto de las imágenes no está incluido en la estimación: las imágenes incrustadas todavía no se traducen durante el proceso del documento.",
    "analysis.images.files": "{images} archivos de imagen",
    "analysis.images.excluded": "{images} imágenes incrustadas (excluidas, no calculadas)",
    "analysis.images.included": "{selected} de {images} imágenes incrustadas para traducir",
    "warning.live_quota_unavailable": "La cuota en tiempo real de DeepL no está disponible ahora mismo (sin clave, sin conexión o error de la API) - se utiliza la estimación local.",
    "start.button": "Iniciar traducción",
    "start.pending": "El inicio aún no está disponible para este modo (véase RoadMap.md).",
    "start.ready": "Listo para iniciar.",
    "start.blocked_running": "Ya hay una ejecución en curso.",
    "start.blocked_mode": "El inicio aún no está disponible para este modo (véase RoadMap.md) - por ahora solo «Traducir presentación» está conectado.",
    "start.blocked_no_analysis": "Ejecute primero «Analizar documento y estimar costes».",
    "start.blocked_not_confirmed": "Active la casilla «He revisado el análisis y la estimación de costes».",
    "dialog.choose_output_dir": "Seleccionar carpeta de destino",
    "dialog.confirm_run": "Iniciar traducción",
    "start.confirm_summary": "Se enviarán aproximadamente {characters:,} caracteres a {provider} (coste estimado ${cost:.2f}).\nArchivo de destino: {destination}\n\n¿Iniciar ahora?",
    "start.confirm_summary_images": "Se enviarán aproximadamente {characters:,} caracteres a {provider} (coste estimado ${cost:.2f}) para {count} imagen(es).\nCarpeta de destino: {folder}\n\n¿Iniciar ahora?",
    "job.group": "Ejecución y resultado",
    "job.idle": "Aún no se ha iniciado ninguna ejecución.",
    "job.running": "Traduciendo…",
    "job.progress_prefix": "Procesando: {location}",
    "job.progress_count": "{processed} de {total} párrafos procesados",
    "job.progress_count_files": "{processed} de {total} imágenes procesadas",
    "job.stats_summary": "{translated} traducidos · {skipped} omitidos · {failed} fallidos · {chars:,} caracteres enviados",
    "job.cancel": "Cancelar",
    "job.cancel_requested": "Cancelación solicitada - se detendrá tras la llamada a la API en curso…",
    "job.result_summary": "Listo: {translated} traducidos, {skipped} omitidos, {failed} fallidos, {chars:,} caracteres enviados.\nArchivo de salida: {output}\nInforme de control de calidad: {report}",
    "job.result_summary_images": "Listo: {files} imagen(es) procesadas, {translated} regiones de texto traducidas, {failed} fallidas, {chars:,} caracteres enviados.\nCarpeta de salida: {output_dir}\nCada imagen tiene su propio archivo de informe de control de calidad en la carpeta de salida.",
    "job.result_cancelled_suffix": "\nNota: la ejecución se canceló - este es un resultado parcial, el contenido ya traducido se ha guardado.",
    "job.overflow_none": "No se encontraron nuevos riesgos de desbordamiento.",
    "job.overflow_count": "{count} aviso(s) de desbordamiento en el informe de control de calidad - revíselo manualmente en PowerPoint/Impress.",
    "job.pdf_overflow_none": "Ningún bloque tuvo que crecer o reducirse al insertarlo.",
    "job.pdf_overflow_count": "{count} bloque(s) tuvieron que crecer o reducirse para encajar - revise el PDF mediante muestreo.",
    "job.open_folder": "Abrir carpeta",
    "job.open_report": "Abrir informe de control de calidad",
    "job.open_folder_failed": "No se pudo abrir la carpeta.",
    "job.show_report": "Mostrar informe de control de calidad",
    "job.hide_report": "Ocultar informe de control de calidad",
    "job.report_load_error": "No se pudo cargar el informe de control de calidad.",
    "job.correct_translation": "Corregir traducción",
    "job.correction_starting": "Iniciando corrección…",
    "job.correction_opened": "Ventana de corrección abierta - edite allí y luego haga clic en «Aplicar» o «Cancelar».",
    "job.correction_applied": "Corrección aplicada.",
    "job.correction_cancelled": "Corrección cancelada.",
    "job.correction_timeout": "Tiempo de espera agotado en la corrección - no hubo respuesta de la ventana de corrección.",
    "job.correction_failed": "Error en la corrección: {error}",
    "job.correction_error": "No se pudo iniciar la corrección.",
    "job.failed_title": "Error en la traducción",
    "correction.title": "Corregir traducción del PDF",
    "correction.hint": "Seleccione una fila a continuación y edite su traducción en el editor de debajo. Con Negrita/Cursiva/Subrayado (también con Ctrl+B/Ctrl+I/Ctrl+U) puede ajustar el formato - las filas editadas conservan su formato.",
    "correction.column_page": "Página",
    "correction.column_original": "Original",
    "correction.column_translation": "Traducción",
    "correction.editor_label": "Editar traducción:",
    "correction.bold": "Negrita",
    "correction.italic": "Cursiva",
    "correction.underline": "Subrayado",
    "correction.bold_tooltip": "Negrita (Ctrl+B)",
    "correction.italic_tooltip": "Cursiva (Ctrl+I)",
    "correction.underline_tooltip": "Subrayado (Ctrl+U)",
    "correction.apply": "Aplicar y guardar",
    "correction.close": "Cerrar",
    "correction.applying": "Aplicando…",
    "correction.success": "{count} bloque(s) actualizado(s) y guardado(s) en {output}.",
    "correction.failed": "Error en la corrección: {error}",
    "image_correction.title": "Corregir traducción de la imagen",
    "image_correction.hint": "Seleccione una fila a continuación y edite su traducción en el editor de debajo.",
    "image_correction.canvas_hint": "En la imagen de la izquierda puede arrastrar el cuadro de una fila para moverlo. Seleccione la fila para arrastrar su esquina inferior derecha y cambiar su tamaño. Con Ctrl+rueda del ratón o los botones de zoom puede acercar o alejar la imagen; el cuadro de diálogo también se puede maximizar.",
    "image_correction.reset_geometry": "Restablecer posición/tamaño",
    "image_correction.zoom_in": "Acercar (+)",
    "image_correction.zoom_out": "Alejar (−)",
    "image_correction.zoom_reset": "Ajustar a la vista",
    "image_correction.add_region": "Añadir nuevo cuadro",
    "image_correction.add_region_hint": "Arrastre sobre la imagen para delimitar una zona y añadir allí un nuevo cuadro con su propio texto.",
    "image_correction.show_original": "Mostrar original",
    "image_correction.manual_region_label": "(añadido manualmente, sin detección de OCR)",
    "image_correction.manual_region_added": "Nuevo cuadro añadido - introduzca la traducción en el editor.",
    "image_correction.column_original": "Original",
    "image_correction.column_translation": "Traducción",
    "image_correction.editor_label": "Editar traducción:",
    "image_correction.font_size_label": "Tamaño de fuente:",
    "image_correction.font_size_auto": "Automático",
    "image_correction.bold": "Negrita",
    "image_correction.centered": "Centrado",
    "image_correction.apply": "Aplicar y guardar",
    "image_correction.close": "Cerrar",
    "image_correction.applying": "Aplicando…",
    "image_correction.success": "{count} región(es) actualizada(s) y guardada(s) en {output}.",
    "image_correction.failed": "Error en la corrección: {error}",
    "image_correction.choose_file_title": "Seleccionar archivo para corregir",
    "image_correction.choose_file_label": "¿Qué archivo de esta ejecución desea corregir?",
    "update.available": "Actualización disponible: {version}",
    "update.confirm_title": "¿Instalar actualización?",
    "update.confirm_body": "Hay una nueva versión disponible ({version}). ¿Descargarla e instalarla ahora?",
    "update.installing": "Instalando actualización…",
    "update.success_title": "Actualización instalada",
    "update.success_body": "La actualización se ha instalado. Reinicie la aplicación para que los cambios surtan efecto.",
    "update.failed_title": "Error al actualizar",
    "update.failed_body": "No se pudo instalar la actualización: {error}\n\nLa versión instalada anteriormente sigue funcionando sin cambios.",
    "menu.help": "Ayuda",
    "menu.help.hw_check": "Mostrar/repetir prueba de hardware…",
    "menu.help.check_updates": "Buscar actualizaciones…",
    "menu.help.about": "Acerca de…",
    "about.body": "<h3>{app_name}</h3><p>Versión {version}</p><p>Traduce documentos PDF, Word y PowerPoint, así como imágenes, conservando el diseño.</p><p>© {year} {author}<br>Licencia: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Código fuente: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Manual de usuario…",
    "manual.hint_link": "Más información en el manual de usuario (capítulo 4)",
    "manual.missing": "No se encontró el manual de usuario:\n{path}",
    "update.check.no_update_title": "No hay actualizaciones disponibles",
    "update.check.no_update_body": "Ya está usando la versión más reciente ({version}).",
    "update.check.failed_title": "Error al comprobar actualizaciones",
    "update.check.failed_body": "No se pudo buscar actualizaciones: {error}",
    "hw_check.title": "Prueba de hardware",
    "hw_check.note": "Si la aplicación no funciona como se espera (por ejemplo, con el inpainting de IA local), puede volver a comprobar el hardware aquí.",
    "hw_check.recheck_button": "Comprobar de nuevo",
    "hw_check.checking": "Comprobando hardware…",
    "hw_check.never_checked": "Todavía no se ha realizado ninguna comprobación de hardware. Haga clic en «Comprobar de nuevo» para comprobarlo ahora.",
    "hw_check.not_found": "No se encontró ninguna GPU CUDA (última comprobación: {checked_at}). El inpainting de IA local no está disponible en este hardware - el inpainting en la nube funciona con independencia de esto.",
    "hw_check.found_ok": "Se encontró {name} con {vram_gb:.0f} GB de memoria de vídeo (última comprobación: {checked_at}). Cumple la recomendación de al menos {min_gb:.0f} GB.",
    "hw_check.found_below_recommended": "Se encontró {name} con {vram_gb:.0f} GB de memoria de vídeo (última comprobación: {checked_at}). Está por debajo de la recomendación de {min_gb:.0f} GB - puede funcionar, pero sin garantía, especialmente con imágenes grandes o muchas zonas de texto a la vez.",
    "hw_check.driver_cuda_ok": "El controlador admite CUDA {cuda_version} - variante de PyTorch adecuada: {torch_variant}.",
    "hw_check.driver_cuda_too_old": "El controlador solo admite CUDA {cuda_version} - demasiado antiguo para el inpainting de IA local (se requiere al menos 11.8). Actualice el controlador gráfico.",
    "settings.button": "Ajustes…",
    "settings.title": "Ajustes",
    "settings.language": "Idioma de la interfaz",
    "settings.prepared": "preparado",
    "settings.provider": "Proveedor",
    "settings.credentials": "Credenciales",
    "settings.new_key": "Nueva clave de API",
    "settings.key_placeholder": "Nunca se muestra ni se registra",
    "settings.storage": "Ubicación de almacenamiento",
    "settings.environment": "Variable de entorno (solo esta sesión)",
    "settings.keyring": "Llavero del sistema operativo",
    "settings.both": "Ambos",
    "settings.run_limit": "Límite de coste por ejecución (caracteres)",
    "settings.save_key": "Guardar/reemplazar clave de API",
    "settings.save_button": "Guardar",
    "settings.open_log": "Abrir archivo de registro…",
    "settings.session_note": "Nota: en esta versión, la variable de entorno no es permanente.",
    "settings.credentials_group": "Acceso a la API",
    "settings.general_group": "General",
    "settings.env_override_warning": "Este proveedor está usando actualmente un valor de una variable de entorno, no la entrada del llavero guardada aquí. Para usar la clave guardada, elimina esa variable de entorno a nivel del sistema operativo.",

    "settings.provider.tooltip": "Proveedor cuya clave se gestiona abajo",
    "settings.provider.whatsthis": (
        "Selecciona a qué proveedor de traducción (DeepL, Google, "
        "OpenAI, Grok) se aplican el estado, la nueva clave y la "
        "ubicación de almacenamiento de abajo. Cada proveedor tiene su "
        "propia clave, guardada por separado."
    ),
    "settings.status.tooltip": "De dónde proviene la clave usada actualmente",
    "settings.status.whatsthis": (
        "Muestra si se encontró una clave para el proveedor "
        "seleccionado en el llavero del sistema, en una variable de "
        "entorno, o si no se encontró ninguna. Una variable de entorno "
        "siempre tiene prioridad sobre el llavero; consulta el aviso "
        "más abajo si es el caso aquí."
    ),
    "settings.secret.tooltip": "Nueva clave API para el proveedor seleccionado",
    "settings.secret.whatsthis": (
        "Pega aquí la clave API obtenida del proveedor y haz clic en "
        "«Guardar». Mientras la escribes se muestra como puntos, pero "
        "no se aplica automáticamente; solo el botón Guardar la "
        "escribe en la ubicación de almacenamiento seleccionada."
    ),
    "settings.target_field.tooltip": "Dónde se guarda la nueva clave",
    "settings.target_field.whatsthis": (
        "«Llavero del sistema operativo» es la opción recomendada y "
        "permanente. «Variable de entorno» solo dura la sesión actual y "
        "está pensada sobre todo para casos especiales o depuración; "
        "consulta la nota de abajo. «Ambos» también escribe una "
        "variable de este tipo."
    ),
    "settings.max_chars.tooltip": "Límite de caracteres por ejecución de traducción",
    "settings.max_chars.whatsthis": (
        "Una ejecución con más caracteres de los establecidos aquí se "
        "detiene con un aviso en lugar de generar costes "
        "inesperadamente altos. Auméntalo aquí si es necesario."
    ),
    "settings.save_key.tooltip": "Guardar la nueva clave",
    "settings.save_key.whatsthis": (
        "Escribe la clave introducida arriba para el proveedor "
        "seleccionado en la ubicación de almacenamiento elegida. El "
        "campo se vacía después y el estado de arriba se actualiza."
    ),
    "settings.open_log.tooltip": "Abrir el archivo de registro de la aplicación",
    "settings.open_log.whatsthis": (
        "Abre el archivo de registro actual con el programa "
        "predeterminado del sistema; útil para copiar mensajes de "
        "error en un informe de errores sin hacer una captura de "
        "pantalla."
    ),

    "hw_check.status.tooltip": "Resultado de la última comprobación de GPU",
    "hw_check.status.whatsthis": (
        "Muestra si se encontró una GPU NVIDIA compatible con suficiente "
        "VRAM, cuándo se comprobó por última vez, y si la versión CUDA "
        "del controlador instalado admite el inpainting local por GPU. "
        "Sin una GPU/controlador adecuados, el inpainting local sigue "
        "funcionando, solo que más lento, en la CPU."
    ),
    "hw_check.recheck_button.tooltip": "Volver a ejecutar la comprobación de GPU ahora",
    "hw_check.recheck_button.whatsthis": (
        "Ejecuta de nuevo la misma comprobación que hizo el instalador; "
        "útil tras actualizar un controlador o cambiar de tarjeta "
        "gráfica, sin tener que reinstalar la aplicación."
    ),

    "bootstrap.help.back_button": (
        "Volver al paso anterior\n\n"
        "Lo ya introducido en este paso y en el anterior se conserva."
    ),
    "bootstrap.help.next_button": "Continuar al siguiente paso",
    "bootstrap.help.cancel_button": (
        "Cierra este asistente\n\n"
        "Se pedirá confirmación si hay una instalación en curso. La "
        "configuración se puede reiniciar en cualquier momento."
    ),
    "bootstrap.help.language_combo": (
        "Idioma de este asistente\n\n"
        "Se aplica de inmediato a todas las pantallas de este asistente. "
        "La propia aplicación tendrá más adelante su propia selección de "
        "idioma, independiente."
    ),
    "bootstrap.help.mode_online_radio": (
        "La traducción pasa por proveedores en la nube (DeepL, Google, "
        "OpenAI, Grok); el procesamiento de imágenes usa aquí un método "
        "más sencillo en lugar de inpainting basado en IA\n\n"
        "Instalación más rápida y sencilla, funciona en cualquier "
        "equipo. Requiere tu propia clave API del proveedor elegido y "
        "conexión a internet durante la traducción."
    ),
    "bootstrap.help.mode_local_radio": (
        "Procesamiento de imágenes mejorado con IA en esta tarjeta "
        "gráfica, en lugar del método estándar más sencillo\n\n"
        "Requiere una tarjeta gráfica NVIDIA compatible con suficiente "
        "memoria de vídeo (se comprueba en el siguiente paso); a cambio, "
        "las imágenes nunca salen de este equipo."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Continuar la instalación local de todos modos\n\n"
        "Útil si la comprobación falló por error o falta actualizar un "
        "controlador - el procesamiento local puede volver a "
        "comprobarse más adelante desde Ayuda -> Prueba de hardware."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Instalar en su lugar la variante en línea\n\n"
        "Cambia esta instalación a proveedores en la nube, sin "
        "preguntar por la GPU. Se puede añadir más adelante en "
        "cualquier momento desde los ajustes de la aplicación."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Introducir una clave API para {provider} en el siguiente "
        "paso\n\n"
        "Los proveedores no marcados siempre se pueden añadir más "
        "adelante en los ajustes de la aplicación."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Continuar sin introducir ninguna clave\n\n"
        "Las claves siempre se pueden añadir más adelante en los "
        "ajustes de la aplicación, pero ninguna traducción funcionará "
        "sin al menos una."
    ),
    "bootstrap.help.credentials_continue_button": "Continuar a la introducción de la clave, o al siguiente proveedor",
    "bootstrap.help.credential_open_signup_button": (
        "Abre la página de registro de este proveedor en el "
        "navegador\n\n"
        "Ahí se genera la clave API, que después se pega aquí."
    ),
    "bootstrap.help.credential_key_entry": (
        "Pega aquí la clave API de este proveedor\n\n"
        "Se muestra como puntos mientras se escribe. Solo el botón "
        "Guardar de abajo la aplica realmente."
    ),
    "bootstrap.help.credential_save_button": "Guardar ahora la clave introducida arriba",
    "bootstrap.help.finish_close_button": "Cerrar el asistente sin iniciar la aplicación ahora",
    "bootstrap.help.finish_launch_button": "Cerrar el asistente e iniciar la aplicación de inmediato",
    "credentials.title": "Credenciales",
    "credentials.saved": "La clave de API se ha guardado.",
    "credential.environment": "Variable de entorno (sesión)",
    "credential.keyring": "Llavero del sistema operativo",
    "credential.missing": "No configurado",
    "provider.missing_key": "No hay ninguna clave de API configurada para «{provider}». <a href=\"settings\">Configurar ahora</a>",
    "provider.missing_key_dialog": "No hay ninguna clave de API configurada para el proveedor «{provider}». Sin una clave, todas las llamadas de traducción fallarán.",
    "dialog.check_input": "Comprobar los datos introducidos",
    "dialog.analysis": "Análisis",
    "dialog.choose_images": "Seleccionar imágenes",
    "dialog.choose_document": "Seleccionar documento",
    "merge.button": "Combinar/insertar PDF…",
    "merge.title": "Combinar/insertar PDF",
    "merge.intro": "Reúna los archivos de origen en el orden deseado. Para cada archivo se puede indicar opcionalmente una selección de páginas (vacío = archivo completo) - añada el mismo archivo varias veces con selecciones de páginas distintas para insertarlo en un punto concreto de otro archivo.",
    "merge.column_file": "Archivo",
    "merge.column_pages": "Páginas",
    "merge.pages_placeholder": "todas",
    "merge.pages_tooltip": "Vacío = archivo completo. En caso contrario, p. ej. \"1-3,5\" o \"6-\" (de la página 6 al final) o \"-4\" (del principio a la página 4). \"5-3\" inserta las páginas 5,4,3 en ese orden (invertido).",
    "merge.add_files": "Añadir archivos…",
    "merge.remove_selected": "Quitar",
    "merge.move_up": "Subir",
    "merge.move_down": "Bajar",
    "merge.sort_by_name": "Ordenar por nombre",
    "merge.sort_by_date": "Ordenar por fecha",
    "merge.sort_by_date_tooltip": "Ordena por la fecha de modificación del archivo en el disco (última modificación, no la fecha de creación).",
    "merge.output_file_label": "Archivo de destino",
    "merge.output_placeholder": "Elegir archivo de destino…",
    "merge.choose_output_file": "Guardar como…",
    "merge.start_button": "Iniciar combinación",
    "merge.cancel_button": "Cancelar",
    "merge.close_button": "Cerrar",
    "merge.status_running": "Procesando: {message}",
    "merge.status_done": "Listo: se escribieron {pages} página(s) de {files} archivo(s).",
    "merge.status_cancelled": "Cancelado (resultado parcial guardado): se escribieron {pages} página(s).",
    "merge.status_failed": "Error: {error}",
    "merge.error_dialog_choose_files": "Seleccionar archivos PDF",
    "merge.error_dialog_choose_output": "Elegir archivo de destino",
    "merge.failed_title": "Error al combinar",
    "merge_search.button": "Buscar en carpeta…",
    "merge_search.title": "Buscar PDF en una carpeta",
    "merge_search.folder_label": "Carpeta",
    "merge_search.folder_placeholder": "Elegir carpeta…",
    "merge_search.choose_folder": "Elegir carpeta…",
    "merge_search.choose_folder_dialog_title": "Elegir carpeta donde buscar",
    "merge_search.recursive_checkbox": "Incl. subcarpetas",
    "merge_search.scope_ico_format": "Formato ICO (zona superior de la página 1)",
    "merge_search.scope_header": "Encabezado (todas las páginas)",
    "merge_search.scope_full_text": "Texto completo",
    "merge_search.scope_ico_format_tooltip": "Busca SOLO en el bloque de metadatos ICO de la página 1 (developer, QSI ICO, fecha de emisión, ...). Independiente de «Encabezado» más abajo - si solo se marca esta opción, la zona de encabezado recurrente en las DEMÁS páginas NO se busca.",
    "merge_search.scope_header_tooltip": "Busca SOLO en la zona superior que se repite en cada página (p. ej., la línea del nombre de la empresa/logotipo). Independiente de «Formato ICO» más arriba - es una región de texto propia y separada, no una extensión de aquella.",
    "merge_search.scope_full_text_tooltip": "Busca en TODO el texto de todas las páginas, incluidas las zonas de «Formato ICO» y «Encabezado» mencionadas arriba.",
    "merge_search.error_missing_scope": "Seleccione al menos un ámbito de búsqueda.",
    "merge_search.date_filter_group": "Filtrar por fecha",
    "merge_search.date_source_file": "Fecha del archivo",
    "merge_search.date_source_document": "Fecha en el documento",
    "merge_search.date_region_ico_format": "Campo ICO (página 1)",
    "merge_search.date_region_header": "Encabezado (todas las páginas)",
    "merge_search.date_region_footer": "Pie de página (todas las páginas)",
    "merge_search.date_format_iso": "ISO (AAAA-MM-DD)",
    "merge_search.date_format_iso_tooltip": "Reconoce, p. ej., «2026-09-04».",
    "merge_search.date_format_de": "Alemán (DD.MM.AAAA)",
    "merge_search.date_format_de_tooltip": "Reconoce, p. ej., «04.09.2026» (también años de dos dígitos como «04.09.26»).",
    "merge_search.date_format_en_month": "Inglés (nombre del mes, p. ej., September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Reconoce tanto «September 4, 2026» como «4. September 2026» (coma opcional, día con uno o dos dígitos).",
    "merge_search.date_format_slash": "Barra (DD/MM/AAAA)",
    "merge_search.date_format_slash_tooltip": "Reconoce, p. ej., «04/09/2026».",
    "merge_search.date_exact_checkbox": "Fecha exacta",
    "merge_search.date_from_label": "Desde",
    "merge_search.date_to_label": "Hasta",
    "merge_search.date_exact_label": "Fecha",
    "merge_search.error_date_range_reversed": "«Desde» no puede ser posterior a «Hasta».",
    "merge_search.error_missing_date_region": "Seleccione al menos una zona para la búsqueda de fechas.",
    "merge_search.error_missing_date_format": "Seleccione al menos un formato de fecha, o introduzca uno personalizado.",
    "merge_search.date_custom_format_label": "Formato personalizado",
    "merge_search.date_custom_format_placeholder": "p. ej., MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Formato de fecha personalizado con estos marcadores (introdúzcalos siempre en inglés, también en este cuadro de diálogo en español) - el resto de caracteres, como espacios, comas, puntos o barras, se buscan literalmente:\n\nYYYY – año, 4 dígitos, p. ej. 2026\nYY – año, 2 dígitos, p. ej. 26\nMMMM – nombre del mes, p. ej. September\nMMM – nombre del mes abreviado, p. ej. Sep\nMM – mes, 2 dígitos, p. ej. 09\nM – mes, 1 o 2 dígitos, p. ej. 9\nDD – día, 2 dígitos, p. ej. 04\nD – día, 1 o 2 dígitos, p. ej. 4\n\nEjemplos:\n«MMMM D, YYYY» encuentra «September 4, 2026»\n«MMMM DD, YYYY» encuentra «September 04, 2026»\n«YYYY/MM/DD» encuentra «2026/09/04»",
    "merge_search.error_invalid_custom_date_format": "El formato de fecha personalizado no es válido - use los marcadores indicados en la información sobre herramientas.",
    "merge_search.query_label": "Texto de búsqueda (combine términos con AND/OR o &&/||)",
    "merge_search.query_placeholder": "p. ej., el nombre de la empresa del developer, o término1 AND término2 - déjelo vacío para incluir todos los archivos de la carpeta",
    "merge_search.query_tooltip": "Varios términos de búsqueda se pueden combinar con AND y OR, incluso mezclados. Use paréntesis para indicar qué va junto.\n\nEjemplo: «Acme AND contrato» solo encuentra archivos que contienen AMBOS términos.\n«Acme OR Zenith» encuentra archivos que contienen AL MENOS UNO de los dos términos.\n\nMezclado con paréntesis: «StellarRussia OR (The AND Korolev AND Directive)» encuentra archivos con «StellarRussia» OR archivos que contienen los TRES términos «The», «Korolev» y «Directive».\n\nEn lugar de AND/OR también se pueden usar los símbolos && y || (equivalentes, incluso mezclados con las palabras): «Acme && contrato» es lo mismo que «Acme AND contrato».\n\nSin AND/OR, todo el texto se trata como un único término de búsqueda (como hasta ahora). No distingue mayúsculas de minúsculas.",
    "merge_search.search_button": "Buscar",
    "merge_search.cancel_button": "Cancelar",
    "merge_search.select_all": "Seleccionar todo",
    "merge_search.select_none": "No seleccionar ninguno",
    "merge_search.detach_results_button": "Abrir lista de resultados en una ventana aparte",
    "merge_search.reattach_results_button": "Volver a acoplar la lista de resultados",
    "merge_search.results_detached_placeholder": "La lista de resultados está abierta en una ventana aparte.",
    "merge_search.detached_results_title_suffix": "Resultados",
    "merge_search.take_selected": "Añadir seleccionados",
    "merge_search.close_button": "Cerrar",
    "merge_search.status_running": "Buscando: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} coincidencia(s) de {scanned} PDF(s) examinados.",
    "merge_search.status_done_with_errors": "{matches} coincidencia(s) de {scanned} PDF(s) examinados ({errors} ilegibles).",
    "merge_search.status_cancelled": "Cancelado: {matches} coincidencia(s) de {scanned} PDF(s) examinados.",
    "merge_search.status_failed": "Error: {error}",
    "merge_search.error_missing_folder": "Elija primero una carpeta.",
    "merge_search.failed_title": "Error en la búsqueda",
    "merge_search.source_local": "Carpeta local",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Enlace o ID de carpeta de Drive",
    "merge_search.drive_folder_placeholder": "Pegue el enlace para compartir o el ID de la carpeta…",
    "merge_search.drive_resolve_button": "Comprobar",
    "merge_search.drive_folder_unresolved": "Aún no comprobado.",
    "merge_search.drive_folder_resolved": "Carpeta «{name}» encontrada.",
    "merge_search.drive_folder_resolve_failed": "Error: {error}",
    "merge_search.drive_cache_label": "Carpeta de caché (las descargas se conservan aquí)",
    "merge_search.drive_choose_cache": "Elegir carpeta de caché…",
    "merge_search.drive_choose_cache_dialog_title": "Elegir carpeta para los resultados descargados",
    "merge_search.drive_credentials_label": "Credenciales de OAuth de Google (una sola vez, véase docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Cargar desde archivo JSON…",
    "merge_search.drive_load_from_file_dialog_title": "Elegir el JSON de client secrets de Google Cloud Console",
    "merge_search.drive_load_from_file_failed": "No se pudo leer el archivo: {error}",
    "merge_search.drive_client_id_placeholder": "ID de cliente",
    "merge_search.drive_client_secret_placeholder": "Secreto de cliente",
    "merge_search.drive_project_id_placeholder": "ID de proyecto",
    "merge_search.drive_save_credentials": "Guardar credenciales",
    "merge_search.drive_credentials_saved": "Credenciales guardadas.",
    "merge_search.drive_save_failed": "Error al guardar: {error}",
    "merge_search.drive_not_configured": "Todavía no se han configurado el ID de cliente, el secreto de cliente ni el ID de proyecto.",
    "merge_search.drive_configured_not_connected": "Configurado, pero aún no conectado.",
    "merge_search.drive_connected": "Conectado{account}.",
    "merge_search.drive_connect_button": "Conectar con Google",
    "merge_search.drive_disconnect_button": "Desconectar",
    "merge_search.drive_connecting": "Abriendo el navegador para iniciar sesión…",
    "merge_search.drive_connect_failed": "Error de conexión: {error}",
    "merge_search.drive_error_missing_folder": "Indique y compruebe primero una carpeta de Drive.",
    "merge_search.drive_error_missing_cache": "Elija primero una carpeta de caché.",
    "merge_search.drive_error_not_connected": "Conéctese primero con Google.",
    "word_merge.button": "Combinar/insertar archivos DOCX…",
    "word_merge.title": "Combinar/insertar archivos DOCX",
    "word_merge.intro": "Reúna los archivos de origen en el orden deseado - siempre archivos completos (a diferencia del PDF, el formato DOCX no tiene un número de página fijo). Añada el mismo archivo varias veces para insertarlo en varios puntos. A partir de más de 100 archivos, la combinación se realiza automáticamente en grupos (véase la línea de estado tras la ejecución).",
    "word_merge.status_done": "Listo: se incorporaron {segments} de {files} archivo(s){batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Cancelado (resultado parcial guardado): se incorporaron {segments} archivo(s){batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " en {batches} grupo(s)",
    "word_merge.status_warning_suffix": ", {count} omitido(s) (véase más abajo)",
    "word_merge.warnings_title": "Archivos omitidos:",
    "word_merge.error_dialog_choose_files": "Seleccionar archivos DOCX",
    "word_merge_search.title": "Buscar archivos DOCX en una carpeta",
    "word_merge_search.status_done": "{matches} coincidencia(s) de {scanned} archivo(s) DOCX examinados.",
    "word_merge_search.status_done_with_errors": "{matches} coincidencia(s) de {scanned} archivo(s) DOCX examinados ({errors} ilegibles).",
    "word_merge_search.status_cancelled": "Cancelado: {matches} coincidencia(s) de {scanned} archivo(s) DOCX examinados.",
    "bootstrap.window_title": "Configurar Document Translator",
    "bootstrap.back_button": "Atrás",
    "bootstrap.next_button": "Siguiente",
    "bootstrap.cancel_button": "Cancelar",
    "bootstrap.cancel_title": "¿Cancelar la instalación?",
    "bootstrap.cancel_confirm": (
        "El asistente de instalación se cerrará sin que Document Translator "
        "quede completamente configurado. Los archivos ya creados se "
        "eliminarán automáticamente. ¿Continuar?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "La instalación está en curso. Cancelar eliminará "
        "automáticamente los archivos ya creados - en casos raros, un "
        "archivo en uso justo en ese momento podría no eliminarse. "
        "¿Cancelar de todos modos?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Privilegios de administrador",
    "bootstrap.elevated_warning_text": (
        "Document Translator se inició como administrador.\n\n"
        "Esto no es necesario y hará que la aplicación deje de "
        "funcionar más adelante al iniciarla normalmente (sin derechos "
        "de administrador).\n\n"
        "Cierra esta ventana y vuelve a iniciar la instalación con un "
        "doble clic normal (sin \"Ejecutar como administrador\").\n\n"
        "Este mensaje se puede copiar con Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Desinstalar Document Translator",
    "bootstrap.uninstall_confirm": (
        "¿Eliminar Document Translator, incluidos todos los ajustes y claves "
        "API guardados localmente?"
    ),
    "bootstrap.uninstall_done": "Document Translator se ha eliminado.",
    "bootstrap.welcome_title": "Bienvenido",
    "bootstrap.welcome_text": "Este asistente configura Document Translator en este equipo, sin necesidad de usar la línea de comandos. Descarga los componentes necesarios y, al final, crea una entrada en el menú de aplicaciones.",
    "bootstrap.language_label": "Idioma",
    "bootstrap.mode_title": "¿En línea o local?",
    "bootstrap.mode_intro": "¿Cómo debe funcionar la traducción? Esto se puede cambiar en cualquier momento más adelante, en Ajustes.",
    "bootstrap.mode_online_label": "En línea (proveedor en la nube)",
    "bootstrap.mode_online_desc": "La traducción se realiza a través de un proveedor externo (DeepL, Google, OpenAI o Grok). Esto conlleva un coste continuo por traducción, y se necesita una clave de API propia de ese proveedor - más sobre esto a continuación. La edición de imágenes en imágenes incrustadas también funciona aquí, solo que con un método más sencillo en lugar de inpainting basado en IA. No requiere una descarga grande. Recomendado si no dispone de una tarjeta gráfica potente.",
    "bootstrap.mode_local_label": "Local (en esta tarjeta gráfica)",
    "bootstrap.mode_local_desc": "Mejora solo la edición de imágenes: el texto incrustado en imágenes se detecta mediante OCR y se vuelve a dibujar con un modelo de IA (LaMa) directamente en esta tarjeta gráfica tras la traducción - el resultado se ve más limpio que el método más sencillo disponible sin esta opción. La traducción del texto en sí sigue pasando, en ambos modos, por un proveedor externo (DeepL, Google, OpenAI o Grok), con el coste habitual por traducción de ese proveedor. Además, los proveedores en línea se pueden configurar en cualquier momento en Ajustes si lo desea. Requiere una tarjeta gráfica NVIDIA suficientemente potente (se comprobará en el siguiente paso) y descarga aproximadamente 2-3 GB una sola vez durante la instalación.",
    "bootstrap.gpu_checking": "Comprobando la tarjeta gráfica…",
    "bootstrap.gpu_ok": "Encontrada: {name} con {vram_gb:.0f} GB de memoria de vídeo - es suficiente.",
    "bootstrap.gpu_insufficient": "Encontrada: {name} con {vram_gb:.0f} GB de memoria de vídeo - se recomiendan al menos {min_gb:.0f} GB. El modo local probablemente será muy lento.",
    "bootstrap.gpu_not_found": "No se encontró ninguna tarjeta gráfica NVIDIA compatible. El modo local no se puede usar de forma práctica en este equipo.",
    "bootstrap.gpu_driver_too_old": "Encontrada: {name}, pero el controlador NVIDIA es demasiado antiguo (solo admite CUDA {cuda_version}; se requiere al menos 11.8). Actualice el controlador gráfico y vuelva a iniciar este asistente, o elija Online en su lugar.",
    "bootstrap.gpu_mac_unsupported": "El modo local no es compatible con Mac por el momento. Elija Online en su lugar.",
    "bootstrap.gpu_continue_local_button": "Continuar en local de todos modos",
    "bootstrap.gpu_switch_online_button": "Cambiar a Online",
    "bootstrap.install_title": "Instalando",
    "bootstrap.install_step_venv": "Creando el entorno de trabajo…",
    "bootstrap.install_step_deps": "Instalando componentes ({name})…",
    "bootstrap.install_step_source": "Descargando el código del programa…",
    "bootstrap.install_step_shortcut": "Creando entrada en el menú de aplicaciones…",
    "bootstrap.install_failed_title": "Error en la instalación",
    "bootstrap.install_failed": "Error: {error}",
    "bootstrap.credentials_title": "Configurar claves de API",
    "bootstrap.credentials_intro": "¿Qué proveedores desea configurar? Puede omitir este paso y hacerlo más adelante en los Ajustes de la aplicación.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Registro rápido de autoservicio. Cuenta con una cuota gratuita, y de pago a partir de ahí.",
    "bootstrap.credentials_explain_google": "Necesita un proyecto de Google Cloud con un método de pago configurado - un poco más laborioso de configurar que los otros tres proveedores.",
    "bootstrap.credentials_explain_openai": "Registro rápido de autoservicio, de pago según el uso.",
    "bootstrap.credentials_explain_grok": "Registro rápido de autoservicio, de pago según el uso.",
    "bootstrap.credentials_open_signup_button": "Obtener clave (abre el navegador)",
    "bootstrap.open_browser_title": "¿Abrir el navegador?",
    "bootstrap.open_browser_text": (
        "Se abrirá el siguiente enlace en el navegador predeterminado:\n\n"
        "{url}\n\n"
        "Por favor, comprueba que es realmente la dirección esperada "
        "antes de continuar."
    ),
    "bootstrap.credentials_key_label": "Clave de API para {provider}",
    "bootstrap.credentials_key_placeholder": "Pegar clave…",
    "bootstrap.credentials_save_button": "Guardar",
    "bootstrap.credentials_saved": "Guardado.",
    "bootstrap.credentials_skip_all_button": "Más tarde, en Ajustes",
    "bootstrap.credentials_continue_button": "Siguiente",
    "bootstrap.finish_title": "Listo",
    "bootstrap.finish_text": "Document Translator está configurado y disponible en el menú de aplicaciones.",
    "bootstrap.finish_download_size": "Descargado realmente: aprox. {size_gb:.1f} GB.",
    "bootstrap.finish_launch_button": "Iniciar ahora",
    "bootstrap.finish_close_button": "Cerrar",
    "mode.tooltip": "Tipo de documento a traducir",
    "mode.whatsthis": (
        "Determina el flujo de traducción utilizado: PDF, PowerPoint/"
        "Impress, Word/Writer o imágenes individuales. Según la "
        "selección, solo se muestran los campos relevantes más abajo, p. "
        "ej. los ajustes de OCR solo en el modo «Imágenes»."
    ),
    "source.tooltip": "Seleccionar el/los archivo(s) a traducir",
    "source.whatsthis": (
        "Abre el selector de archivos para el archivo de origen (varios "
        "archivos a la vez en modo Imágenes). El nombre del archivo "
        "elegido aparece luego a la izquierda."
    ),
    "source_label.tooltip": "Archivo de origen seleccionado actualmente",
    "source_label.whatsthis": (
        "Muestra el nombre del archivo elegido por última vez mediante "
        "«Seleccionar archivo…». Si todavía indica «Ningún archivo "
        "seleccionado», primero hay que elegir un archivo antes de poder "
        "analizar los costes."
    ),
    "image_mode.tooltip": "Tratamiento de las imágenes incrustadas en el documento",
    "image_mode.whatsthis": (
        "«No traducir» deja las imágenes incrustadas sin cambios. "
        "«Seleccionar individualmente más tarde» muestra una lista tras "
        "el análisis de costes para elegir imágenes concretas. "
        "«Traducir todas» procesa automáticamente cada imagen "
        "incrustada."
    ),
    "provider.tooltip": "Proveedor de traducción para esta ejecución",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI o Grok, cada uno con su propia clave API, "
        "gestionada en Ajustes. Si no hay clave configurada para el "
        "proveedor elegido, aparece un aviso justo debajo con un enlace "
        "a Ajustes."
    ),
    "source_lang.tooltip": "Código del idioma de origen, p. ej. EN",
    "source_lang.whatsthis": (
        "Código de idioma de dos letras según ISO 639-1 (p. ej. EN para "
        "inglés, FR para francés). Debe coincidir con el idioma real del "
        "documento; de lo contrario, el proveedor de traducción devuelve "
        "resultados incorrectos o ninguno."
    ),
    "target_lang.tooltip": "Código del idioma de destino, p. ej. DE",
    "target_lang.whatsthis": (
        "Código de idioma de dos letras según ISO 639-1 al que traducir "
        "(p. ej. DE para alemán, ES para español)."
    ),
    "protected.tooltip": "Términos que deben quedar sin traducir",
    "protected.whatsthis": (
        "Un término por línea, p. ej. nombres de empresa o de producto. "
        "El proveedor de traducción deja estos términos intactos. El "
        "botón de al lado también permite cargar una lista desde un "
        "archivo."
    ),
    "ocr_engine_field.tooltip": "Reconocimiento de texto (OCR) para imágenes",
    "ocr_engine_field.whatsthis": (
        "Solo visible en modo «Imágenes». Reconoce el texto en las "
        "imágenes antes de traducirlo y volver a insertarlo. Si un motor "
        "no está disponible en este equipo, aparece un aviso justo "
        "debajo."
    ),
    "inpainting_backend_field.tooltip": (
        "Método para reinsertar el texto traducido en la imagen"
    ),
    "inpainting_backend_field.whatsthis": (
        "Solo visible en modo «Imágenes». «Superposición de caja» y «CV "
        "Inpainting» siempre se ejecutan localmente, sin hardware "
        "especial. «GPU Inpainting» usa una tarjeta gráfica local (CUDA) "
        "para el mejor resultado y solo está disponible si PyTorch con "
        "soporte CUDA está instalado; si no, aparece un aviso debajo. El "
        "estado del hardware se puede comprobar en cualquier momento en "
        "Ayuda -> Prueba de hardware."
    ),
    "merge.tooltip": "Combinar varios archivos PDF",
    "merge.whatsthis": (
        "Abre un diálogo independiente para combinar varios archivos "
        "PDF en uno solo. Independiente del formulario de arriba: aquí "
        "no se traduce nada."
    ),
    "word_merge.tooltip": "Combinar varios archivos Word",
    "word_merge.whatsthis": (
        "Abre un diálogo independiente para combinar varios archivos "
        "Word en uno solo. Independiente del formulario de arriba: aquí "
        "no se traduce nada."
    ),
    "analysis.button.tooltip": "Estimar el coste de esta traducción",
    "analysis.button.whatsthis": (
        "Cuenta los caracteres a traducir y estima el coste aproximado "
        "según el proveedor elegido, sin traducir todavía nada. Solo "
        "después se puede marcar la casilla de al lado y habilitar "
        "«Iniciar»."
    ),
    "analysis.checked.tooltip": "Confirmar los costes estimados",
    "analysis.checked.whatsthis": (
        "Debe marcarse antes de que «Iniciar» sea pulsable: un paso de "
        "seguridad deliberado para que ninguna ejecución se inicie por "
        "accidente sin haber visto antes los costes estimados."
    ),
    "start.tooltip": "Iniciar la traducción",
    "start.whatsthis": (
        "Solo se activa después de analizar y confirmar los costes. El "
        "progreso aparece en el área de abajo; una ejecución en curso "
        "puede detenerse con «Cancelar»."
    ),
    "job.cancel.tooltip": "Cancelar la traducción en curso",
    "job.cancel.whatsthis": (
        "Detiene la ejecución actual lo antes posible. Las partes ya "
        "procesadas no se conservan automáticamente como un archivo "
        "completo; según el formato, puede quedar un archivo incompleto."
    ),
    "job.open_folder.tooltip": "Abrir la carpeta de salida",
    "job.open_folder.whatsthis": (
        "Abre el explorador de archivos en la carpeta de destino de la "
        "ejecución recién finalizada."
    ),
    "job.open_report.tooltip": "Abrir el informe de control de calidad de la última ejecución",
    "job.open_report.whatsthis": (
        "Muestra hallazgos del control de calidad automático de la "
        "última ejecución, p. ej. pasajes que podría valer la pena "
        "revisar."
    ),
    "job.correct_translation.tooltip": "Corregir traducciones individuales",
    "job.correct_translation.whatsthis": (
        "Solo visible en ejecuciones de PDF con bloques de texto "
        "corregibles. Permite retocar pasajes traducidos concretos sin "
        "repetir toda la ejecución."
    ),
    "settings.button.tooltip": "Abrir los ajustes",
    "settings.button.whatsthis": (
        "Claves API por proveedor (recomendado: llavero), el límite de "
        "caracteres por ejecución y el acceso al archivo de registro."
    ),
    "update_hint.tooltip": "Hay una nueva versión disponible",
    "update_hint.whatsthis": (
        "Aparece automáticamente cuando al iniciar se encuentra una "
        "versión más reciente de Document Translator. Al hacer clic se ofrece "
        "instalar la nueva versión."
    ),
    "flag_row.whatsthis": (
        "Cambia de inmediato y de forma permanente el idioma de la "
        "propia interfaz, no los idiomas de traducción del formulario. "
        "La elección se guarda al instante."
    ),
    "menu.help.whats_this": "¿Qué es esto?",
}


IT = {
    "app.title": "Document Translator",
    "mode.pdf": "Traduci PDF",
    "mode.presentation": "Traduci presentazione (PowerPoint/Impress)",
    "mode.word": "Traduci documento Word/Writer",
    "mode.images": "Traduci singole immagini",
    "source.none": "Nessun file selezionato",
    "source.choose": "Seleziona file...",
    "image.none": "Non tradurre le immagini incorporate",
    "image.selected": "Seleziona le immagini singolarmente in seguito",
    "image.all": "Traduci tutte le immagini incorporate",
    "field.mode": "Operazione",
    "field.source": "Origine",
    "field.images": "Immagini nel documento",
    "field.provider": "Provider di traduzione",
    "field.source_language": "Lingua di origine",
    "field.target_language": "Lingua di destinazione",
    "field.protected_terms": "Termini protetti",
    "field.ico_mode": "Documento ICO",
    "ico_mode.checkbox": "Non tradurre l'area di pagina 1",
    "ico_mode.tooltip": "Solo per il tipo di documento interno ICO: esclude dalla traduzione il blocco di metadati a pagina 1 (per Word: il blocco che precede la linea di separazione; per PDF: rilevato tramite termini di ancoraggio come \"Issuer Address\"/\"Asset Matrix\") - indipendentemente dal fatto che questo blocco venga effettivamente trovato. Per tutti gli altri documenti, lasciare disattivato.",
    "field.side_by_side": "Visualizzazione affiancata",
    "side_by_side.checkbox": "Originale e traduzione affiancati",
    "side_by_side.tooltip": "Solo Word: costruisce il testo principale come tabella di confronto a due colonne (Originale | Traduzione) in formato orizzontale, invece del normale risultato fedele al layout. Intestazione e piè di pagina restano invariati. Le eventuali tabelle incorporate nel testo principale non compaiono in questa visualizzazione.",
    "field.exclude_header": "Intestazione",
    "exclude_header.checkbox": "Non tradurre l'intestazione ricorrente",
    "exclude_header.tooltip": "Rileva automaticamente il testo che si ripete in modo identico (o che differisce solo per il numero di pagina) vicino alla parte superiore della maggior parte delle pagine e lo esclude dalla traduzione. Se non viene trovata alcuna corrispondenza, non cambia nulla.",
    "field.exclude_footer": "Piè di pagina",
    "exclude_footer.checkbox": "Non tradurre il piè di pagina ricorrente",
    "exclude_footer.tooltip": "Come per l'intestazione, ma per il testo che si ripete vicino alla parte inferiore della pagina (ad es. riga di copyright, numero di pagina).",
    "field.ocr_engine": "Motore OCR",
    "ocr_engine.tesseract": "Tesseract (locale)",
    "ocr_engine.tesseract.unavailable": "Tesseract non è stato trovato su questo sistema. Installarlo (vedere README.md) - senza Tesseract installato non è possibile riconoscere il testo nelle immagini.",
    "ocr_engine.google_vision": "Google Cloud Vision (cloud, rilevamento paragrafi)",
    "ocr_engine.google_vision.unavailable": "Nessuna chiave API di Google configurata. Impostarla nelle Impostazioni (la stessa chiave usata per Google Translate, vedere README.md) oppure scegliere un altro motore OCR.",
    "ocr_engine.paddleocr": "PaddleOCR (locale, rilevamento paragrafi)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR non è installato (vedere requirements-paddleocr.txt) oppure scegliere un altro motore OCR.",
    "ocr_engine.unavailable": "Questo motore OCR non è disponibile su questo sistema.",
    "field.inpainting_backend": "Metodo di riscrittura",
    "inpainting_backend.box_overlay": "Sovrapposizione box (copre l'area)",
    "inpainting_backend.cv_inpainting": "Inpainting CPU classico (ricostruisce lo sfondo)",
    "inpainting_backend.gpu_inpainting": "Inpainting AI locale (GPU, LaMa)",
    "inpainting_backend.unavailable": "Per questo metodo non è stata trovata alcuna GPU CUDA (vedere requirements-gpu.txt) - scegliere un altro metodo di riscrittura.",
    "inpainting_backend.below_recommended_vram": "Rilevati solo {vram_gb:.0f} GB di memoria video (consigliati: almeno {min_gb:.0f} GB) - potrebbe comunque funzionare, ma senza garanzia, specialmente con immagini grandi o molte aree di testo contemporaneamente.",
    "source_language.placeholder": "opzionale / automatico",
    "protected.placeholder": "Un termine protetto per riga",
    "protected.load_file": "Carica da file...",
    "protected.load_file.tooltip": "Importa i termini da un file CSV o di testo (un termine per riga; per i CSV viene usata la prima colonna). Le voci esistenti vengono mantenute, i duplicati vengono ignorati.",
    "protected.loaded": "{added} nuovi termini importati da {name} ({total} nel file).",
    "protected.load_error": "Impossibile leggere {name}: {error}",
    "dialog.choose_protected_terms": "Seleziona elenco termini",
    "dialog.all_files": "Tutti i file",
    "merge_box.group": "Unisci file",
    "config.group": "Configura operazione",
    "analysis.group": "Analisi e controllo dei costi",
    "analysis.required": "È necessaria un'analisi prima di avviare.",
    "analysis.button": "Analizza documento e stima i costi",
    "analysis.running": "Analisi in corso...",
    "analysis.checked": "Ho verificato l'analisi e la stima dei costi",
    "analysis.failed": "Analisi non riuscita.",
    "analysis.no_warnings": "Nessun avviso dall'analisi.",
    "analysis.within": "entro il limite",
    "analysis.exceeded": "SUPERATO",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} caratteri di testo · {images}<br>Stima locale ({provider}): consumo mensile {usage:,} / contingente gratuito {free:,} caratteri · stima ${cost:.2f}<br>Limite per esecuzione {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Contingente in tempo reale (DeepL, appena verificato):</b> {used:,} di {limit:,} caratteri utilizzati, {remaining:,} rimanenti.",
    "analysis.live_quota_unlimited": "<b>Contingente in tempo reale (DeepL, appena verificato):</b> {used:,} caratteri utilizzati, l'account non segnala alcun limite.",
    "unit.pages": "pagine",
    "unit.slides": "diapositive",
    "unit.paragraphs": "paragrafi",
    "unit.images": "immagini",
    "warning.scan_pdf": "Rilevato PDF immagine/scansionato: l'OCR è necessario per il testo del documento.",
    "warning.image_cost_unknown": "I caratteri OCR e i costi di traduzione delle immagini sono noti solo dopo l'esecuzione dell'OCR.",
    "warning.image_selection_later": "La selezione specifica delle immagini avverrà dopo l'analisi, in una versione futura dell'interfaccia.",
    "warning.embedded_images_not_estimated": "Il testo nelle immagini non è incluso nella stima: le immagini incorporate non vengono ancora tradotte durante l'elaborazione del documento.",
    "analysis.images.files": "{images} file immagine",
    "analysis.images.excluded": "{images} immagini incorporate (escluse, non conteggiate)",
    "analysis.images.included": "{selected} di {images} immagini incorporate selezionate per la traduzione",
    "warning.live_quota_unavailable": "Il contingente in tempo reale di DeepL non è al momento disponibile (nessuna chiave, offline o errore API) - viene utilizzata la stima locale.",
    "start.button": "Avvia traduzione",
    "start.pending": "L'avvio non è ancora collegato per questa modalità (vedere RoadMap.md).",
    "start.ready": "Pronto per l'avvio.",
    "start.blocked_running": "È già in corso un'esecuzione.",
    "start.blocked_mode": "L'avvio non è ancora collegato per questa modalità (vedere RoadMap.md) - al momento è collegata solo \"Traduci presentazione\".",
    "start.blocked_no_analysis": "Eseguire prima \"Analizza documento e stima i costi\".",
    "start.blocked_not_confirmed": "Attivare la casella \"Ho verificato l'analisi e la stima dei costi\".",
    "dialog.choose_output_dir": "Scegli cartella di destinazione",
    "dialog.confirm_run": "Avvia traduzione",
    "start.confirm_summary": "Verranno inviati a {provider} circa {characters:,} caratteri (costo stimato ${cost:.2f}).\nFile di destinazione: {destination}\n\nAvviare ora?",
    "start.confirm_summary_images": "Verranno inviati a {provider} circa {characters:,} caratteri (costo stimato ${cost:.2f}) per {count} immagine/i.\nCartella di destinazione: {folder}\n\nAvviare ora?",
    "job.group": "Esecuzione e risultato",
    "job.idle": "Nessuna esecuzione ancora avviata.",
    "job.running": "Traduzione in corso...",
    "job.progress_prefix": "Elaborazione: {location}",
    "job.progress_count": "{processed} di {total} paragrafi elaborati",
    "job.progress_count_files": "{processed} di {total} immagini elaborate",
    "job.stats_summary": "{translated} tradotti · {skipped} saltati · {failed} non riusciti · {chars:,} caratteri inviati",
    "job.cancel": "Annulla",
    "job.cancel_requested": "Annullamento richiesto – si interromperà dopo la chiamata API in corso...",
    "job.result_summary": "Completato: {translated} tradotti, {skipped} saltati, {failed} non riusciti, {chars:,} caratteri inviati.\nFile di output: {output}\nReport QA: {report}",
    "job.result_summary_images": "Completato: {files} immagine/i elaborate, {translated} aree di testo tradotte, {failed} non riuscite, {chars:,} caratteri inviati.\nCartella di output: {output_dir}\nOgni immagine ha un proprio file di report QA nella cartella di output.",
    "job.result_cancelled_suffix": "\nNota: l'esecuzione è stata annullata – questo è un risultato parziale, i contenuti già tradotti sono stati salvati.",
    "job.overflow_none": "Nessun nuovo rischio di overflow rilevato.",
    "job.overflow_count": "{count} avviso/i di overflow nel report QA – controllare manualmente in PowerPoint/Impress.",
    "job.pdf_overflow_none": "Nessun blocco ha dovuto crescere o ridursi durante l'inserimento.",
    "job.pdf_overflow_count": "{count} blocco/blocchi hanno dovuto crescere o ridursi per adattarsi – controllare a campione nel PDF.",
    "job.open_folder": "Apri cartella",
    "job.open_report": "Apri report QA",
    "job.open_folder_failed": "Impossibile aprire la cartella.",
    "job.show_report": "Mostra report QA",
    "job.hide_report": "Nascondi report QA",
    "job.report_load_error": "Impossibile caricare il report QA.",
    "job.correct_translation": "Correggi traduzione",
    "job.correction_starting": "Avvio della correzione...",
    "job.correction_opened": "Finestra di correzione aperta - modificare lì, quindi fare clic su \"Applica\" o \"Annulla\".",
    "job.correction_applied": "Correzione applicata.",
    "job.correction_cancelled": "Correzione annullata.",
    "job.correction_timeout": "Timeout della correzione - nessuna risposta dalla finestra di correzione.",
    "job.correction_failed": "Correzione non riuscita: {error}",
    "job.correction_error": "Impossibile avviare la correzione.",
    "job.failed_title": "Traduzione non riuscita",
    "correction.title": "Correggi traduzione PDF",
    "correction.hint": "Selezionare una riga qui sotto e modificarne la traduzione nell'editor sottostante. Con Grassetto/Corsivo/Sottolineato (anche con Ctrl+B/Ctrl+I/Ctrl+U) è possibile adattare la formattazione – anche le righe modificate mantengono la propria formattazione.",
    "correction.column_page": "Pagina",
    "correction.column_original": "Originale",
    "correction.column_translation": "Traduzione",
    "correction.editor_label": "Modifica traduzione:",
    "correction.bold": "Grassetto",
    "correction.italic": "Corsivo",
    "correction.underline": "Sottolineato",
    "correction.bold_tooltip": "Grassetto (Ctrl+B)",
    "correction.italic_tooltip": "Corsivo (Ctrl+I)",
    "correction.underline_tooltip": "Sottolineato (Ctrl+U)",
    "correction.apply": "Applica e salva",
    "correction.close": "Chiudi",
    "correction.applying": "Applicazione in corso...",
    "correction.success": "{count} blocco/blocchi aggiornati e salvati in {output}.",
    "correction.failed": "Correzione non riuscita: {error}",
    "image_correction.title": "Correggi traduzione immagine",
    "image_correction.hint": "Selezionare una riga qui sotto e modificarne la traduzione nell'editor sottostante.",
    "image_correction.canvas_hint": "Nell'immagine a sinistra è possibile trascinare il box di una riga per spostarlo. Selezionare la riga per trascinarne l'angolo in basso a destra e ridimensionarla. Usare Ctrl+rotellina del mouse o i pulsanti di zoom per ingrandire e rimpicciolire l'immagine; la finestra può anche essere massimizzata.",
    "image_correction.reset_geometry": "Ripristina posizione/dimensione",
    "image_correction.zoom_in": "Ingrandisci (+)",
    "image_correction.zoom_out": "Riduci (−)",
    "image_correction.zoom_reset": "Adatta alla vista",
    "image_correction.add_region": "Aggiungi nuovo box",
    "image_correction.add_region_hint": "Trascinare un'area sull'immagine per aggiungere lì un nuovo box con un testo proprio.",
    "image_correction.show_original": "Mostra originale",
    "image_correction.manual_region_label": "(aggiunto manualmente, nessun rilevamento OCR)",
    "image_correction.manual_region_added": "Nuovo box aggiunto - inserire la traduzione nell'editor.",
    "image_correction.column_original": "Originale",
    "image_correction.column_translation": "Traduzione",
    "image_correction.editor_label": "Modifica traduzione:",
    "image_correction.font_size_label": "Dimensione carattere:",
    "image_correction.font_size_auto": "Automatica",
    "image_correction.bold": "Grassetto",
    "image_correction.centered": "Centrato",
    "image_correction.apply": "Applica e salva",
    "image_correction.close": "Chiudi",
    "image_correction.applying": "Applicazione in corso...",
    "image_correction.success": "{count} regione/i aggiornate e salvate in {output}.",
    "image_correction.failed": "Correzione non riuscita: {error}",
    "image_correction.choose_file_title": "Scegli il file da correggere",
    "image_correction.choose_file_label": "Quale file di questa esecuzione deve essere corretto?",
    "update.available": "Aggiornamento disponibile: {version}",
    "update.confirm_title": "Installare l'aggiornamento?",
    "update.confirm_body": "È disponibile una nuova versione ({version}). Scaricarla e installarla ora?",
    "update.installing": "Installazione dell'aggiornamento in corso...",
    "update.success_title": "Aggiornamento installato",
    "update.success_body": "L'aggiornamento è stato installato. Riavviare l'applicazione affinché le modifiche abbiano effetto.",
    "update.failed_title": "Aggiornamento non riuscito",
    "update.failed_body": "Impossibile installare l'aggiornamento: {error}\n\nLa versione precedentemente installata continua a funzionare senza modifiche.",
    "menu.help": "Guida",
    "menu.help.hw_check": "Mostra/ripeti test hardware...",
    "menu.help.check_updates": "Cerca aggiornamenti...",
    "menu.help.about": "Informazioni...",
    "about.body": "<h3>{app_name}</h3><p>Versione {version}</p><p>Traduce documenti PDF, Word e PowerPoint e immagini mantenendo il layout.</p><p>© {year} {author}<br>Licenza: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Codice sorgente: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Manuale utente...",
    "manual.hint_link": "Ulteriori informazioni nel manuale utente (capitolo 4)",
    "manual.missing": "Impossibile trovare il manuale utente:\n{path}",
    "update.check.no_update_title": "Nessun aggiornamento disponibile",
    "update.check.no_update_body": "Stai già utilizzando la versione più recente ({version}).",
    "update.check.failed_title": "Verifica aggiornamenti non riuscita",
    "update.check.failed_body": "Impossibile cercare aggiornamenti: {error}",
    "hw_check.title": "Test hardware",
    "hw_check.note": "Se l'app non si comporta come previsto (ad es. con l'inpainting AI locale), qui è possibile verificare nuovamente l'hardware.",
    "hw_check.recheck_button": "Verifica di nuovo",
    "hw_check.checking": "Verifica dell'hardware in corso...",
    "hw_check.never_checked": "Nessuna verifica hardware ancora effettuata. Fare clic su \"Verifica di nuovo\" per verificare ora.",
    "hw_check.not_found": "Nessuna GPU CUDA trovata (ultima verifica: {checked_at}). L'inpainting AI locale non è disponibile su questo hardware - l'inpainting cloud funziona indipendentemente da questo.",
    "hw_check.found_ok": "Trovata {name} con {vram_gb:.0f} GB di memoria video (ultima verifica: {checked_at}). Soddisfa il requisito consigliato di almeno {min_gb:.0f} GB.",
    "hw_check.found_below_recommended": "Trovata {name} con {vram_gb:.0f} GB di memoria video (ultima verifica: {checked_at}). Al di sotto del valore consigliato di {min_gb:.0f} GB - potrebbe comunque funzionare, ma senza garanzia, specialmente con immagini grandi o molte aree di testo contemporaneamente.",
    "hw_check.driver_cuda_ok": "Il driver supporta CUDA {cuda_version} - variante PyTorch corrispondente: {torch_variant}.",
    "hw_check.driver_cuda_too_old": "Il driver supporta solo CUDA {cuda_version} - troppo obsoleto per l'inpainting AI locale (è necessario almeno 11.8). Aggiornare il driver grafico.",
    "settings.button": "Impostazioni...",
    "settings.title": "Impostazioni",
    "settings.language": "Lingua dell'interfaccia",
    "settings.prepared": "predisposto",
    "settings.provider": "Provider",
    "settings.credentials": "Credenziali",
    "settings.new_key": "Nuova chiave API",
    "settings.key_placeholder": "Mai visualizzata o registrata",
    "settings.storage": "Posizione di archiviazione",
    "settings.environment": "Variabile d'ambiente (solo questa sessione)",
    "settings.keyring": "Keyring del sistema operativo",
    "settings.both": "Entrambi",
    "settings.run_limit": "Limite di costo per esecuzione (caratteri)",
    "settings.save_key": "Salva/sostituisci chiave API",
    "settings.save_button": "Salva",
    "settings.open_log": "Apri file di log...",
    "settings.session_note": "Nota: in questa versione la variabile d'ambiente non è permanente.",
    "settings.credentials_group": "Accesso API",
    "settings.general_group": "Generale",
    "settings.env_override_warning": "Questo provider utilizza attualmente un valore proveniente da una variabile d'ambiente, non la voce del keyring salvata qui. Per usare la chiave salvata, rimuovi questa variabile d'ambiente a livello di sistema operativo.",

    "settings.provider.tooltip": "Provider la cui chiave è gestita qui sotto",
    "settings.provider.whatsthis": (
        "Seleziona a quale provider di traduzione (DeepL, Google, "
        "OpenAI, Grok) si applicano lo stato, la nuova chiave e la "
        "posizione di archiviazione qui sotto. Ogni provider ha una "
        "propria chiave, salvata separatamente."
    ),
    "settings.status.tooltip": "Da dove proviene la chiave attualmente usata",
    "settings.status.whatsthis": (
        "Mostra se per il provider selezionato è stata trovata una "
        "chiave nel keyring del sistema, in una variabile d'ambiente o "
        "nessuna delle due. Una variabile d'ambiente ha sempre la "
        "precedenza sul keyring - vedi l'avviso più sotto se è questo "
        "il caso."
    ),
    "settings.secret.tooltip": "Nuova chiave API per il provider selezionato",
    "settings.secret.whatsthis": (
        "Incolla qui la chiave API ricevuta dal provider e fai clic su "
        "«Salva». Durante la digitazione viene mostrata come puntini "
        "ma non viene applicata automaticamente - solo il pulsante "
        "Salva la scrive nella posizione di archiviazione selezionata."
    ),
    "settings.target_field.tooltip": "Dove viene salvata la nuova chiave",
    "settings.target_field.whatsthis": (
        "«Keyring del sistema operativo» è la scelta consigliata e "
        "permanente. «Variabile d'ambiente» vale solo per la sessione "
        "corrente ed è pensata soprattutto per casi particolari/"
        "risoluzione problemi - vedi la nota sotto. «Entrambi» scrive "
        "anche una variabile di questo tipo."
    ),
    "settings.max_chars.tooltip": "Limite di caratteri per esecuzione di traduzione",
    "settings.max_chars.whatsthis": (
        "Un'esecuzione con più caratteri di quanto impostato qui viene "
        "interrotta con un avviso invece di generare costi "
        "inaspettatamente alti. Aumentalo qui se necessario."
    ),
    "settings.save_key.tooltip": "Salva la nuova chiave",
    "settings.save_key.whatsthis": (
        "Scrive la chiave inserita sopra per il provider selezionato "
        "nella posizione di archiviazione scelta. Il campo viene "
        "svuotato in seguito e lo stato sopra si aggiorna."
    ),
    "settings.open_log.tooltip": "Apri il file di log dell'app",
    "settings.open_log.whatsthis": (
        "Apre il file di log corrente nel programma predefinito del "
        "sistema - utile per copiare messaggi di errore in una "
        "segnalazione di bug senza fare uno screenshot."
    ),

    "hw_check.status.tooltip": "Risultato dell'ultimo controllo GPU",
    "hw_check.status.whatsthis": (
        "Mostra se è stata trovata una GPU NVIDIA supportata con VRAM "
        "sufficiente, quando è stata effettuata l'ultima verifica e se "
        "la versione CUDA del driver installato supporta l'inpainting "
        "GPU locale. Senza una GPU/driver adeguati, l'inpainting locale "
        "funziona comunque - solo più lentamente, sulla CPU."
    ),
    "hw_check.recheck_button.tooltip": "Esegui di nuovo ora il controllo GPU",
    "hw_check.recheck_button.whatsthis": (
        "Esegue di nuovo lo stesso controllo già effettuato "
        "dall'installer - utile dopo un aggiornamento del driver o un "
        "cambio di scheda grafica, senza dover reinstallare l'app."
    ),

    "bootstrap.help.back_button": (
        "Torna al passaggio precedente\n\n"
        "Quanto già inserito in questo passaggio e nel precedente viene "
        "mantenuto."
    ),
    "bootstrap.help.next_button": "Continua al passaggio successivo",
    "bootstrap.help.cancel_button": (
        "Chiude questa procedura guidata\n\n"
        "Verrà chiesta conferma se un'installazione è in corso. La "
        "configurazione può essere riavviata in qualsiasi momento."
    ),
    "bootstrap.help.language_combo": (
        "Lingua di questa procedura guidata\n\n"
        "Si applica immediatamente a tutte le schermate di questa "
        "procedura. L'app stessa avrà in seguito una propria selezione "
        "della lingua, indipendente."
    ),
    "bootstrap.help.mode_online_radio": (
        "La traduzione passa attraverso provider cloud (DeepL, Google, "
        "OpenAI, Grok); l'elaborazione delle immagini usa qui un metodo "
        "più semplice invece dell'inpainting basato su IA\n\n"
        "Installazione più rapida e semplice, funziona su qualsiasi "
        "computer. Richiede una propria chiave API del provider scelto "
        "e una connessione internet durante la traduzione."
    ),
    "bootstrap.help.mode_local_radio": (
        "Elaborazione delle immagini migliorata con IA su questa scheda "
        "grafica, invece del metodo standard più semplice\n\n"
        "Richiede una scheda grafica NVIDIA supportata con memoria "
        "video sufficiente (verificata al passaggio successivo) - in "
        "cambio, le immagini non lasciano mai questo computer."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Continua comunque l'installazione locale\n\n"
        "Utile se il controllo è fallito per errore o se è ancora in "
        "sospeso un aggiornamento del driver - l'elaborazione locale può "
        "essere riverificata in seguito da Aiuto -> Test hardware."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Installa invece la variante online\n\n"
        "Passa questa installazione ai provider cloud, senza chiedere "
        "nulla sulla GPU. Può essere aggiunta in seguito in qualsiasi "
        "momento dalle impostazioni dell'app."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Inserire una chiave API per {provider} al passaggio "
        "successivo\n\n"
        "I provider non selezionati possono sempre essere aggiunti in "
        "seguito nelle impostazioni dell'app."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Continua senza inserire alcuna chiave\n\n"
        "Le chiavi possono sempre essere aggiunte in seguito nelle "
        "impostazioni dell'app - ma nessuna traduzione funzionerà senza "
        "almeno una."
    ),
    "bootstrap.help.credentials_continue_button": "Continua all'inserimento della chiave, o al provider successivo",
    "bootstrap.help.credential_open_signup_button": (
        "Apre la pagina di registrazione di questo provider nel "
        "browser\n\n"
        "È lì che viene generata la chiave API, da incollare qui in "
        "seguito."
    ),
    "bootstrap.help.credential_key_entry": (
        "Incolla qui la chiave API di questo provider\n\n"
        "Viene mostrata come puntini durante la digitazione. Solo il "
        "pulsante Salva sottostante la applica davvero."
    ),
    "bootstrap.help.credential_save_button": "Salva ora la chiave inserita sopra",
    "bootstrap.help.finish_close_button": "Chiudi la procedura guidata senza avviare ora l'app",
    "bootstrap.help.finish_launch_button": "Chiudi la procedura guidata e avvia subito l'app",
    "credentials.title": "Credenziali",
    "credentials.saved": "La chiave API è stata salvata.",
    "credential.environment": "Variabile d'ambiente (sessione)",
    "credential.keyring": "Keyring del sistema operativo",
    "credential.missing": "Non configurato",
    "provider.missing_key": "Nessuna chiave API configurata per \"{provider}\". <a href=\"settings\">Configura ora</a>",
    "provider.missing_key_dialog": "Per il provider \"{provider}\" non è configurata alcuna chiave API. Senza una chiave, ogni chiamata di traduzione fallirà.",
    "dialog.check_input": "Verifica dati inseriti",
    "dialog.analysis": "Analisi",
    "dialog.choose_images": "Seleziona immagini",
    "dialog.choose_document": "Seleziona documento",
    "merge.button": "Unisci/inserisci PDF...",
    "merge.title": "Unisci/inserisci PDF",
    "merge.intro": "Componi i file di origine nell'ordine desiderato. Per ogni file è possibile indicare facoltativamente una selezione di pagine (vuoto = intero file) - aggiungere lo stesso file più volte con selezioni di pagine diverse per inserirlo in un punto specifico di un altro file.",
    "merge.column_file": "File",
    "merge.column_pages": "Pagine",
    "merge.pages_placeholder": "tutte",
    "merge.pages_tooltip": "Vuoto = intero file. Altrimenti, ad es. \"1-3,5\" oppure \"6-\" (dalla pagina 6 alla fine) oppure \"-4\" (dall'inizio alla pagina 4). \"5-3\" inserisce le pagine 5,4,3 in questo ordine (inverso).",
    "merge.add_files": "Aggiungi file...",
    "merge.remove_selected": "Rimuovi",
    "merge.move_up": "Sposta su",
    "merge.move_down": "Sposta giù",
    "merge.sort_by_name": "Ordina per nome",
    "merge.sort_by_date": "Ordina per data",
    "merge.sort_by_date_tooltip": "Ordina in base alla data dell'ultima modifica del file su disco (non la data di creazione).",
    "merge.output_file_label": "File di destinazione",
    "merge.output_placeholder": "Scegli un file di destinazione...",
    "merge.choose_output_file": "Salva con nome...",
    "merge.start_button": "Avvia unione",
    "merge.cancel_button": "Annulla",
    "merge.close_button": "Chiudi",
    "merge.status_running": "Elaborazione: {message}",
    "merge.status_done": "Completato: scritte {pages} pagina/e da {files} file.",
    "merge.status_cancelled": "Annullato (risultato parziale salvato): scritte {pages} pagina/e.",
    "merge.status_failed": "Non riuscito: {error}",
    "merge.error_dialog_choose_files": "Seleziona file PDF",
    "merge.error_dialog_choose_output": "Scegli file di destinazione",
    "merge.failed_title": "Unione non riuscita",
    "merge_search.button": "Cerca in una cartella...",
    "merge_search.title": "Cerca PDF in una cartella",
    "merge_search.folder_label": "Cartella",
    "merge_search.folder_placeholder": "Scegli una cartella...",
    "merge_search.choose_folder": "Scegli cartella...",
    "merge_search.choose_folder_dialog_title": "Scegli una cartella da cercare",
    "merge_search.recursive_checkbox": "Includi sottocartelle",
    "merge_search.scope_ico_format": "Formato ICO (area di intestazione pagina 1)",
    "merge_search.scope_header": "Intestazione (tutte le pagine)",
    "merge_search.scope_full_text": "Testo completo",
    "merge_search.scope_ico_format_tooltip": "Cerca SOLO nel blocco di metadati ICO a pagina 1 (Developer, QSI ICO, data di emissione, ...). Indipendente dall'opzione \"Intestazione\" qui sotto - se è selezionata solo questa opzione, l'area di intestazione ricorrente sulle ALTRE pagine NON viene cercata.",
    "merge_search.scope_header_tooltip": "Cerca SOLO l'area che si ripete nella parte superiore di ogni pagina (ad es. riga con nome azienda/logo). Indipendente dall'opzione \"Formato ICO\" sopra - è una regione di testo separata, non un'estensione di essa.",
    "merge_search.scope_full_text_tooltip": "Cerca nell'INTERO testo su tutte le pagine, comprese le aree di \"Formato ICO\" e \"Intestazione\" sopra.",
    "merge_search.error_missing_scope": "Selezionare almeno un ambito di ricerca.",
    "merge_search.date_filter_group": "Filtra per data",
    "merge_search.date_source_file": "Data del file",
    "merge_search.date_source_document": "Data nel documento",
    "merge_search.date_region_ico_format": "Campo ICO (pagina 1)",
    "merge_search.date_region_header": "Intestazione (tutte le pagine)",
    "merge_search.date_region_footer": "Piè di pagina (tutte le pagine)",
    "merge_search.date_format_iso": "ISO (AAAA-MM-GG)",
    "merge_search.date_format_iso_tooltip": "Riconosce ad es. \"2026-09-04\".",
    "merge_search.date_format_de": "Tedesco (GG.MM.AAAA)",
    "merge_search.date_format_de_tooltip": "Riconosce ad es. \"04.09.2026\" (anche anni a due cifre come \"04.09.26\").",
    "merge_search.date_format_en_month": "Inglese (nome del mese, ad es. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Riconosce sia \"September 4, 2026\" sia \"4 September 2026\" (virgola facoltativa, giorno con o senza zero iniziale).",
    "merge_search.date_format_slash": "Barra (GG/MM/AAAA)",
    "merge_search.date_format_slash_tooltip": "Riconosce ad es. \"04/09/2026\".",
    "merge_search.date_exact_checkbox": "Data esatta",
    "merge_search.date_from_label": "Da",
    "merge_search.date_to_label": "A",
    "merge_search.date_exact_label": "Data",
    "merge_search.error_date_range_reversed": "\"Da\" non può essere successiva a \"A\".",
    "merge_search.error_missing_date_region": "Selezionare almeno un'area per la ricerca per data.",
    "merge_search.error_missing_date_format": "Selezionare almeno un formato di data oppure inserire un formato personalizzato.",
    "merge_search.date_custom_format_label": "Formato personalizzato",
    "merge_search.date_custom_format_placeholder": "ad es. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Formato di data personalizzato con questi segnaposto (da inserire sempre in inglese, anche in questa finestra in italiano) - tutti gli altri caratteri come spazi, virgole, punti o barre vengono cercati letteralmente:\n\nYYYY – anno, 4 cifre, ad es. 2026\nYY – anno, 2 cifre, ad es. 26\nMMMM – nome del mese, ad es. September\nMMM – nome del mese abbreviato, ad es. Sep\nMM – mese, 2 cifre, ad es. 09\nM – mese, 1 o 2 cifre, ad es. 9\nDD – giorno, 2 cifre, ad es. 04\nD – giorno, 1 o 2 cifre, ad es. 4\n\nEsempi:\n\"MMMM D, YYYY\" trova \"September 4, 2026\"\n\"MMMM DD, YYYY\" trova \"September 04, 2026\"\n\"YYYY/MM/DD\" trova \"2026/09/04\"",
    "merge_search.error_invalid_custom_date_format": "Il formato di data personalizzato non è valido - utilizzare i segnaposto indicati nel tooltip.",
    "merge_search.query_label": "Testo di ricerca (combina i termini con AND/OR oppure &&/||)",
    "merge_search.query_placeholder": "ad es. il nome dell'azienda dello sviluppatore, oppure termine1 AND termine2 - lasciare vuoto per tutti i file nella cartella",
    "merge_search.query_tooltip": "È possibile combinare più termini di ricerca con AND e OR - anche in modo misto. Usare le parentesi per definire cosa appartiene insieme.\n\nEsempio: \"Acme AND contratto\" trova solo i file che contengono ENTRAMBI i termini.\n\"Acme OR Zenith\" trova i file che contengono ALMENO UNO dei due termini.\n\nMisto con parentesi: \"StellarRussia OR (The AND Korolev AND Directive)\" trova i file che contengono \"StellarRussia\" OPPURE i file che contengono TUTTI E TRE i termini \"The\", \"Korolev\" e \"Directive\".\n\nAl posto di AND/OR si possono usare anche i simboli && e || (equivalenti, anche misti con le parole): \"Acme && contratto\" equivale a \"Acme AND contratto\".\n\nSenza AND/OR, l'intero testo viene trattato come un unico termine di ricerca (come in precedenza). Maiuscole e minuscole non fanno differenza.",
    "merge_search.search_button": "Cerca",
    "merge_search.cancel_button": "Annulla",
    "merge_search.select_all": "Seleziona tutto",
    "merge_search.select_none": "Deseleziona tutto",
    "merge_search.detach_results_button": "Apri elenco risultati in una finestra separata",
    "merge_search.reattach_results_button": "Aggancia di nuovo l'elenco risultati",
    "merge_search.results_detached_placeholder": "L'elenco dei risultati è aperto in una finestra separata.",
    "merge_search.detached_results_title_suffix": "Risultati",
    "merge_search.take_selected": "Aggiungi selezionati",
    "merge_search.close_button": "Chiudi",
    "merge_search.status_running": "Ricerca in corso: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} corrispondenza/e su {scanned} PDF analizzati.",
    "merge_search.status_done_with_errors": "{matches} corrispondenza/e su {scanned} PDF analizzati ({errors} illeggibili).",
    "merge_search.status_cancelled": "Annullato: {matches} corrispondenza/e su {scanned} PDF analizzati.",
    "merge_search.status_failed": "Non riuscito: {error}",
    "merge_search.error_missing_folder": "Scegliere prima una cartella.",
    "merge_search.failed_title": "Ricerca non riuscita",
    "merge_search.source_local": "Cartella locale",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Link o ID della cartella Drive",
    "merge_search.drive_folder_placeholder": "Incolla un link di condivisione o l'ID della cartella...",
    "merge_search.drive_resolve_button": "Verifica",
    "merge_search.drive_folder_unresolved": "Non ancora verificato.",
    "merge_search.drive_folder_resolved": "Cartella \"{name}\" trovata.",
    "merge_search.drive_folder_resolve_failed": "Non riuscito: {error}",
    "merge_search.drive_cache_label": "Cartella cache (i download vengono conservati qui)",
    "merge_search.drive_choose_cache": "Scegli cartella cache...",
    "merge_search.drive_choose_cache_dialog_title": "Scegli una cartella per i risultati scaricati",
    "merge_search.drive_credentials_label": "Credenziali OAuth di Google (una tantum, vedere docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Carica da file JSON...",
    "merge_search.drive_load_from_file_dialog_title": "Scegli il file JSON dei client secret da Google Cloud Console",
    "merge_search.drive_load_from_file_failed": "Impossibile leggere il file: {error}",
    "merge_search.drive_client_id_placeholder": "ID client",
    "merge_search.drive_client_secret_placeholder": "Client secret",
    "merge_search.drive_project_id_placeholder": "ID progetto",
    "merge_search.drive_save_credentials": "Salva credenziali",
    "merge_search.drive_credentials_saved": "Credenziali salvate.",
    "merge_search.drive_save_failed": "Salvataggio non riuscito: {error}",
    "merge_search.drive_not_configured": "Nessun ID client/secret/ID progetto ancora salvato.",
    "merge_search.drive_configured_not_connected": "Configurato, ma non ancora connesso.",
    "merge_search.drive_connected": "Connesso{account}.",
    "merge_search.drive_connect_button": "Connetti a Google",
    "merge_search.drive_disconnect_button": "Disconnetti",
    "merge_search.drive_connecting": "Apertura del browser per l'accesso...",
    "merge_search.drive_connect_failed": "Connessione non riuscita: {error}",
    "merge_search.drive_error_missing_folder": "Indicare e verificare prima una cartella Drive.",
    "merge_search.drive_error_missing_cache": "Scegliere prima una cartella cache.",
    "merge_search.drive_error_not_connected": "Connettersi prima a Google.",
    "word_merge.button": "Unisci/inserisci file DOCX...",
    "word_merge.title": "Unisci/inserisci file DOCX",
    "word_merge.intro": "Componi i file di origine nell'ordine desiderato - sempre file interi (a differenza del PDF, il formato DOCX non ha un numero di pagina fisso nel file stesso). Aggiungere lo stesso file più volte per inserirlo in più punti. Oltre 100 file, l'unione avviene automaticamente in gruppi (vedere la riga di stato dopo l'esecuzione).",
    "word_merge.status_done": "Completato: acquisiti {segments} di {files} file{batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Annullato (risultato parziale salvato): acquisiti {segments} file{batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " in {batches} gruppo/i",
    "word_merge.status_warning_suffix": ", {count} saltati (vedi sotto)",
    "word_merge.warnings_title": "File saltati:",
    "word_merge.error_dialog_choose_files": "Seleziona file DOCX",
    "word_merge_search.title": "Cerca file DOCX in una cartella",
    "word_merge_search.status_done": "{matches} corrispondenza/e su {scanned} file DOCX analizzati.",
    "word_merge_search.status_done_with_errors": "{matches} corrispondenza/e su {scanned} file DOCX analizzati ({errors} illeggibili).",
    "word_merge_search.status_cancelled": "Annullato: {matches} corrispondenza/e su {scanned} file DOCX analizzati.",
    "bootstrap.window_title": "Configura Document Translator",
    "bootstrap.back_button": "Indietro",
    "bootstrap.next_button": "Avanti",
    "bootstrap.cancel_button": "Annulla",
    "bootstrap.cancel_title": "Annullare l'installazione?",
    "bootstrap.cancel_confirm": (
        "La procedura guidata si chiuderà senza che Document Translator sia "
        "completamente configurato. I file già creati verranno rimossi "
        "automaticamente. Continuare?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "L'installazione è in corso. Annullare rimuoverà automaticamente "
        "i file già creati - in rari casi un file ancora in uso in quel "
        "momento potrebbe non essere rimosso. Annullare comunque?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Diritti di amministratore",
    "bootstrap.elevated_warning_text": (
        "Document Translator è stato avviato come amministratore.\n\n"
        "Non è necessario e farà sì che l'app smetta di funzionare in "
        "seguito quando avviata normalmente (senza diritti di "
        "amministratore).\n\n"
        "Chiudi questa finestra e riavvia il programma di installazione "
        "con un doppio clic normale (senza \"Esegui come "
        "amministratore\").\n\n"
        "Questo messaggio può essere copiato con Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Disinstalla Document Translator",
    "bootstrap.uninstall_confirm": (
        "Rimuovere Document Translator, comprese tutte le impostazioni e le "
        "chiavi API salvate localmente?"
    ),
    "bootstrap.uninstall_done": "Document Translator è stato rimosso.",
    "bootstrap.welcome_title": "Benvenuto",
    "bootstrap.welcome_text": "Questa procedura guidata configura Document Translator su questo computer - senza bisogno della riga di comando. Scarica i componenti necessari e alla fine crea una voce nel menu delle applicazioni.",
    "bootstrap.language_label": "Lingua",
    "bootstrap.mode_title": "Online o locale?",
    "bootstrap.mode_intro": "Come deve funzionare la traduzione? È possibile modificarlo in qualsiasi momento in seguito, nelle Impostazioni.",
    "bootstrap.mode_online_label": "Online (provider cloud)",
    "bootstrap.mode_online_desc": "La traduzione avviene tramite un provider esterno (DeepL, Google, OpenAI o Grok). Questo comporta costi correnti per ogni traduzione ed è necessaria una chiave API propria del rispettivo provider - maggiori dettagli tra poco. Anche qui l'elaborazione delle immagini incorporate funziona, ma con un metodo più semplice invece dell'inpainting basato su IA. Non richiede download di grandi dimensioni. Consigliato se non si dispone di una scheda grafica potente.",
    "bootstrap.mode_local_label": "Locale (su questa scheda grafica)",
    "bootstrap.mode_local_desc": "Migliora solo l'elaborazione delle immagini: il testo incorporato nelle immagini viene riconosciuto tramite OCR e ridisegnato con un modello IA (LaMa) direttamente su questa scheda grafica dopo la traduzione - il risultato è più pulito rispetto al metodo più semplice disponibile senza questa opzione. La traduzione del testo vero e proprio passa comunque, in entrambe le modalità, attraverso un provider esterno (DeepL, Google, OpenAI o Grok), con il consueto costo per traduzione di quel provider. I provider online possono comunque essere configurati in qualsiasi momento nelle Impostazioni, se lo si desidera. Richiede una scheda grafica NVIDIA sufficientemente potente (verificata nel passaggio successivo) e scarica una tantum circa 2-3 GB durante l'installazione.",
    "bootstrap.gpu_checking": "Verifica della scheda grafica in corso...",
    "bootstrap.gpu_ok": "Trovata: {name} con {vram_gb:.0f} GB di memoria video - sufficiente.",
    "bootstrap.gpu_insufficient": "Trovata: {name} con {vram_gb:.0f} GB di memoria video - sono consigliati almeno {min_gb:.0f} GB. La modalità locale sarà probabilmente molto lenta.",
    "bootstrap.gpu_not_found": "Nessuna scheda grafica NVIDIA supportata trovata. La modalità locale non è utilizzabile in modo pratico su questo computer.",
    "bootstrap.gpu_driver_too_old": "Trovata: {name}, ma il driver NVIDIA è troppo obsoleto (supporta solo CUDA {cuda_version}; è necessario almeno 11.8). Aggiornare il driver grafico e riavviare questa procedura, oppure scegliere Online.",
    "bootstrap.gpu_mac_unsupported": "La modalità locale non è al momento supportata su Mac. Scegliere invece Online.",
    "bootstrap.gpu_continue_local_button": "Continua comunque in locale",
    "bootstrap.gpu_switch_online_button": "Passa a Online",
    "bootstrap.install_title": "Installazione in corso",
    "bootstrap.install_step_venv": "Creazione dell'ambiente di lavoro...",
    "bootstrap.install_step_deps": "Installazione dei componenti ({name})...",
    "bootstrap.install_step_source": "Download del codice del programma...",
    "bootstrap.install_step_shortcut": "Creazione della voce nel menu delle applicazioni...",
    "bootstrap.install_failed_title": "Installazione non riuscita",
    "bootstrap.install_failed": "Non riuscito: {error}",
    "bootstrap.credentials_title": "Configura chiavi API",
    "bootstrap.credentials_intro": "Quali provider configurare? È possibile saltare questo passaggio e farlo in seguito, in qualsiasi momento, nelle Impostazioni dell'app.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Registrazione rapida in autonomia. Disponibile un livello gratuito, a pagamento oltre tale limite.",
    "bootstrap.credentials_explain_google": "Richiede un progetto Google Cloud con un metodo di pagamento registrato - configurazione leggermente più complessa rispetto agli altri tre provider.",
    "bootstrap.credentials_explain_openai": "Registrazione rapida in autonomia, a pagamento in base all'utilizzo.",
    "bootstrap.credentials_explain_grok": "Registrazione rapida in autonomia, a pagamento in base all'utilizzo.",
    "bootstrap.credentials_open_signup_button": "Ottieni una chiave (apre il browser)",
    "bootstrap.open_browser_title": "Aprire il browser?",
    "bootstrap.open_browser_text": (
        "Verrà aperto il seguente link nel browser predefinito:\n\n"
        "{url}\n\n"
        "Verifica che sia davvero l'indirizzo previsto prima di "
        "continuare."
    ),
    "bootstrap.credentials_key_label": "Chiave API per {provider}",
    "bootstrap.credentials_key_placeholder": "Incolla la chiave...",
    "bootstrap.credentials_save_button": "Salva",
    "bootstrap.credentials_saved": "Salvato.",
    "bootstrap.credentials_skip_all_button": "Più tardi, nelle Impostazioni",
    "bootstrap.credentials_continue_button": "Avanti",
    "bootstrap.finish_title": "Completato",
    "bootstrap.finish_text": "Document Translator è configurato ed è disponibile nel menu delle applicazioni.",
    "bootstrap.finish_download_size": "Effettivamente scaricato: circa {size_gb:.1f} GB.",
    "bootstrap.finish_launch_button": "Avvia ora",
    "bootstrap.finish_close_button": "Chiudi",
    "mode.tooltip": "Tipo di documento da tradurre",
    "mode.whatsthis": (
        "Determina il flusso di traduzione utilizzato: PDF, PowerPoint/"
        "Impress, Word/Writer o immagini singole. In base alla scelta, "
        "più in basso vengono mostrati solo i campi pertinenti, ad es. "
        "le impostazioni OCR solo in modalità «Immagini»."
    ),
    "source.tooltip": "Seleziona il/i file da tradurre",
    "source.whatsthis": (
        "Apre la finestra di selezione file per il file di origine (più "
        "file contemporaneamente in modalità Immagini). Il nome del "
        "file scelto appare poi a sinistra."
    ),
    "source_label.tooltip": "File di origine attualmente selezionato",
    "source_label.whatsthis": (
        "Mostra il nome del file scelto l'ultima volta tramite "
        "«Seleziona file…». Se indica ancora «Nessun file selezionato», "
        "occorre prima scegliere un file prima che sia possibile "
        "un'analisi dei costi."
    ),
    "image_mode.tooltip": "Gestione delle immagini incorporate nel documento",
    "image_mode.whatsthis": (
        "«Non tradurre» lascia invariate le immagini incorporate. "
        "«Seleziona singolarmente in seguito» mostra un elenco dopo "
        "l'analisi dei costi per scegliere immagini specifiche. "
        "«Traduci tutte» elabora automaticamente ogni immagine "
        "incorporata."
    ),
    "provider.tooltip": "Provider di traduzione per questa esecuzione",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI o Grok, ciascuno con una propria chiave "
        "API, gestita in Impostazioni. Se per il provider scelto non è "
        "configurata alcuna chiave, subito sotto appare un avviso con un "
        "link alle Impostazioni."
    ),
    "source_lang.tooltip": "Codice della lingua di origine, ad es. EN",
    "source_lang.whatsthis": (
        "Codice lingua di due lettere secondo ISO 639-1 (ad es. EN per "
        "l'inglese, FR per il francese). Deve corrispondere alla lingua "
        "reale del documento, altrimenti il provider di traduzione "
        "restituisce risultati errati o nessun risultato."
    ),
    "target_lang.tooltip": "Codice della lingua di destinazione, ad es. DE",
    "target_lang.whatsthis": (
        "Codice lingua di due lettere secondo ISO 639-1 verso cui "
        "tradurre (ad es. DE per il tedesco, ES per lo spagnolo)."
    ),
    "protected.tooltip": "Termini che devono restare non tradotti",
    "protected.whatsthis": (
        "Un termine per riga, ad es. nomi di aziende o prodotti. Il "
        "provider di traduzione lascia questi termini invariati. Il "
        "pulsante accanto permette anche di caricare un elenco da un "
        "file."
    ),
    "ocr_engine_field.tooltip": "Riconoscimento del testo (OCR) per le immagini",
    "ocr_engine_field.whatsthis": (
        "Visibile solo in modalità «Immagini». Riconosce il testo nelle "
        "immagini prima che venga tradotto e riscritto. Se un motore non "
        "è disponibile su questo computer, subito sotto appare un "
        "avviso."
    ),
    "inpainting_backend_field.tooltip": (
        "Metodo per riscrivere il testo tradotto nell'immagine"
    ),
    "inpainting_backend_field.whatsthis": (
        "Visibile solo in modalità «Immagini». «Sovrapposizione box» e "
        "«CV Inpainting» funzionano sempre localmente, senza hardware "
        "particolare. «GPU Inpainting» usa una scheda grafica locale "
        "(CUDA) per il miglior risultato ed è disponibile solo se è "
        "installato PyTorch con supporto CUDA, altrimenti sotto appare "
        "un avviso. Lo stato dell'hardware può essere verificato in "
        "qualsiasi momento tramite Guida -> Test hardware."
    ),
    "merge.tooltip": "Unisci più file PDF",
    "merge.whatsthis": (
        "Apre una finestra separata per unire più file PDF in uno solo. "
        "Indipendente dal modulo sopra: qui non viene tradotto nulla."
    ),
    "word_merge.tooltip": "Unisci più file Word",
    "word_merge.whatsthis": (
        "Apre una finestra separata per unire più file Word in uno "
        "solo. Indipendente dal modulo sopra: qui non viene tradotto "
        "nulla."
    ),
    "analysis.button.tooltip": "Stima il costo di questa traduzione",
    "analysis.button.whatsthis": (
        "Conta i caratteri da tradurre e stima il costo approssimativo "
        "in base al provider scelto, senza ancora tradurre nulla. Solo "
        "dopo è possibile spuntare la casella accanto e abilitare "
        "«Avvia»."
    ),
    "analysis.checked.tooltip": "Conferma i costi stimati",
    "analysis.checked.whatsthis": (
        "Deve essere spuntata prima che «Avvia» diventi cliccabile: un "
        "passaggio di sicurezza deliberato affinché nessuna esecuzione "
        "parta per errore senza aver prima visto i costi stimati."
    ),
    "start.tooltip": "Avvia la traduzione",
    "start.whatsthis": (
        "Si attiva solo dopo che i costi sono stati analizzati e "
        "confermati. L'avanzamento appare nell'area sottostante; "
        "un'esecuzione in corso può essere interrotta con «Annulla»."
    ),
    "job.cancel.tooltip": "Annulla la traduzione in corso",
    "job.cancel.whatsthis": (
        "Interrompe l'esecuzione corrente il più rapidamente possibile. "
        "Le parti già elaborate non vengono automaticamente conservate "
        "come file completo: a seconda del formato può rimanere un file "
        "incompleto."
    ),
    "job.open_folder.tooltip": "Apri la cartella di output",
    "job.open_folder.whatsthis": (
        "Apre l'esplora file nella cartella di destinazione "
        "dell'esecuzione appena conclusa."
    ),
    "job.open_report.tooltip": "Apri il report QA dell'ultima esecuzione",
    "job.open_report.whatsthis": (
        "Mostra le rilevazioni del controllo qualità automatico "
        "dell'ultima esecuzione, ad es. passaggi che potrebbe valere la "
        "pena controllare."
    ),
    "job.correct_translation.tooltip": "Correggi singole traduzioni",
    "job.correct_translation.whatsthis": (
        "Visibile solo per esecuzioni PDF con blocchi di testo "
        "correggibili. Permette di rielaborare singoli passaggi tradotti "
        "senza ripetere l'intera esecuzione."
    ),
    "settings.button.tooltip": "Apri le impostazioni",
    "settings.button.whatsthis": (
        "Chiavi API per provider (consigliato: keyring), il limite di "
        "caratteri per esecuzione e l'accesso al file di log."
    ),
    "update_hint.tooltip": "È disponibile una nuova versione",
    "update_hint.whatsthis": (
        "Appare automaticamente quando all'avvio viene trovata una "
        "versione più recente di Document Translator. Cliccandolo si propone "
        "di installare la nuova versione."
    ),
    "flag_row.whatsthis": (
        "Cambia immediatamente e in modo permanente la lingua "
        "dell'interfaccia stessa, non le lingue di traduzione nel "
        "modulo. La scelta viene salvata subito."
    ),
    "menu.help.whats_this": "Che cos'è?",
}


NL = {
    "app.title": "Document Translator",
    "mode.pdf": "PDF vertalen",
    "mode.presentation": "Presentatie (PowerPoint/Impress) vertalen",
    "mode.word": "Word/Writer-document vertalen",
    "mode.images": "Losse afbeeldingen vertalen",
    "source.none": "Geen bestand geselecteerd",
    "source.choose": "Bestand selecteren …",
    "image.none": "Ingesloten afbeeldingen niet vertalen",
    "image.selected": "Afbeeldingen later afzonderlijk selecteren",
    "image.all": "Alle ingesloten afbeeldingen vertalen",
    "field.mode": "Taak",
    "field.source": "Bron",
    "field.images": "Afbeeldingen in het document",
    "field.provider": "Vertaalprovider",
    "field.source_language": "Brontaal",
    "field.target_language": "Doeltaal",
    "field.protected_terms": "Beschermde termen",
    "field.ico_mode": "ICO-document",
    "ico_mode.checkbox": "Gebied op pagina 1 niet vertalen",
    "ico_mode.tooltip": "Alleen voor het interne documenttype ICO: sluit het metadatagebied op pagina 1 uit van de vertaling (bij Word: het gebied vóór de scheidingslijn; bij PDF: herkend aan ankertermen zoals \"Issuer Address\"/\"Asset Matrix\") - ongeacht of dit gebied daadwerkelijk wordt gevonden. Voor alle andere documenten uitgeschakeld laten.",
    "field.side_by_side": "Naast elkaar weergeven",
    "side_by_side.checkbox": "Origineel en vertaling naast elkaar",
    "side_by_side.tooltip": "Alleen Word: bouwt de hoofdtekst, in plaats van het normale, lay-outgetrouwe resultaat, op als een tweekolomsvergelijkingstabel (origineel | vertaling) in liggend formaat. Kop- en voettekst blijven ongewijzigd. Ingesloten tabellen in de hoofdtekst (indien aanwezig) verschijnen niet in deze weergave.",
    "field.exclude_header": "Koptekst",
    "exclude_header.checkbox": "Terugkerende koptekst niet vertalen",
    "exclude_header.tooltip": "Detecteert automatisch tekst die bovenaan de meeste pagina's identiek (of alleen met een afwijkend paginanummer) terugkeert, en sluit deze uit van de vertaling. Wordt niets passends gevonden, dan verandert er niets.",
    "field.exclude_footer": "Voettekst",
    "exclude_footer.checkbox": "Terugkerende voettekst niet vertalen",
    "exclude_footer.tooltip": "Zoals bij de koptekst, maar voor terugkerende tekst onderaan de pagina (bijv. copyrightregel, paginanummer).",
    "field.ocr_engine": "OCR-engine",
    "ocr_engine.tesseract": "Tesseract (lokaal)",
    "ocr_engine.tesseract.unavailable": "Tesseract is niet gevonden op dit systeem. Installeer het (zie README.md) - zonder geïnstalleerde Tesseract kan geen tekst in afbeeldingen worden herkend.",
    "ocr_engine.google_vision": "Google Cloud Vision (cloud, alineaherkenning)",
    "ocr_engine.google_vision.unavailable": "Geen Google-API-sleutel geconfigureerd. Stel deze in bij Instellingen (dezelfde sleutel als voor Google Translate, zie README.md) of kies een andere OCR-engine.",
    "ocr_engine.paddleocr": "PaddleOCR (lokaal, alineaherkenning)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR is niet geïnstalleerd (zie requirements-paddleocr.txt) of kies een andere OCR-engine.",
    "ocr_engine.unavailable": "Deze OCR-engine is niet beschikbaar op dit systeem.",
    "field.inpainting_backend": "Terugschrijfmethode",
    "inpainting_backend.box_overlay": "Vak-overlay (gebied bedekken)",
    "inpainting_backend.cv_inpainting": "Klassieke CPU-inpainting (achtergrond reconstrueren)",
    "inpainting_backend.gpu_inpainting": "AI-inpainting lokaal (GPU, LaMa)",
    "inpainting_backend.unavailable": "Voor deze methode is geen CUDA-GPU gevonden (zie requirements-gpu.txt) - kies een andere terugschrijfmethode.",
    "inpainting_backend.below_recommended_vram": "Er is slechts {vram_gb:.0f} GB videogeheugen gedetecteerd (aanbevolen: minimaal {min_gb:.0f} GB) - werkt mogelijk, maar zonder garantie, vooral bij grote afbeeldingen of veel tekstgebieden tegelijk.",
    "source_language.placeholder": "optioneel / automatisch",
    "protected.placeholder": "Eén beschermde term per regel",
    "protected.load_file": "Uit bestand laden …",
    "protected.load_file.tooltip": "Termen uit een CSV- of tekstbestand overnemen (één term per regel; bij CSV wordt de eerste kolom gebruikt). Bestaande items blijven behouden, duplicaten worden overgeslagen.",
    "protected.loaded": "{added} nieuwe termen overgenomen uit {name} ({total} in het bestand).",
    "protected.load_error": "{name} kon niet worden gelezen: {error}",
    "dialog.choose_protected_terms": "Termenlijst selecteren",
    "dialog.all_files": "Alle bestanden",
    "merge_box.group": "Bestanden samenvoegen",
    "config.group": "Taak configureren",
    "analysis.group": "Analyse en kostenbeheersing",
    "analysis.required": "Vóór de start is een analyse vereist.",
    "analysis.button": "Document analyseren en kosten schatten",
    "analysis.running": "Analyse wordt uitgevoerd …",
    "analysis.checked": "Ik heb de analyse en kostenschatting gecontroleerd",
    "analysis.failed": "Analyse mislukt.",
    "analysis.no_warnings": "Geen analysewaarschuwingen.",
    "analysis.within": "binnen limiet",
    "analysis.exceeded": "OVERSCHREDEN",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} tekens · {images}<br>Lokale schatting ({provider}): maandelijks verbruik {usage:,} / gratis quotum {free:,} tekens · schatting ${cost:.2f}<br>Looplimiet {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Live-quotum (DeepL, zojuist opgehaald):</b> {used:,} van {limit:,} tekens gebruikt, {remaining:,} resterend.",
    "analysis.live_quota_unlimited": "<b>Live-quotum (DeepL, zojuist opgehaald):</b> {used:,} tekens gebruikt, account meldt geen limiet.",
    "unit.pages": "pagina's",
    "unit.slides": "dia's",
    "unit.paragraphs": "alinea's",
    "unit.images": "afbeeldingen",
    "warning.scan_pdf": "Afbeeldings-/scan-PDF gedetecteerd: OCR is vereist voor de documenttekst.",
    "warning.image_cost_unknown": "OCR-tekens en kosten voor afbeeldingsvertaling zijn pas bekend na de OCR.",
    "warning.image_selection_later": "De specifieke afbeeldingsselectie volgt na de analyse in een latere versie van de gebruikersinterface.",
    "warning.embedded_images_not_estimated": "Tekst in afbeeldingen is niet in de schatting opgenomen: ingesloten afbeeldingen worden momenteel nog niet vertaald tijdens de documentverwerking.",
    "analysis.images.files": "{images} afbeeldingsbestanden",
    "analysis.images.excluded": "{images} ingesloten afbeeldingen (uitgesloten, niet in rekening gebracht)",
    "analysis.images.included": "{selected} van {images} ingesloten afbeeldingen geselecteerd voor vertaling",
    "warning.live_quota_unavailable": "Live-quotum bij DeepL is momenteel niet beschikbaar (geen sleutel, offline, of API-fout) – de lokale schatting wordt gebruikt.",
    "start.button": "Vertaling starten",
    "start.pending": "Voor deze modus is starten nog niet gekoppeld (zie RoadMap.md).",
    "start.ready": "Klaar om te starten.",
    "start.blocked_running": "Er is al een taak actief.",
    "start.blocked_mode": "Voor deze modus is starten nog niet gekoppeld (zie RoadMap.md) – alleen \"Presentatie vertalen\" is al aangesloten.",
    "start.blocked_no_analysis": "Voer eerst \"Document analyseren en kosten schatten\" uit.",
    "start.blocked_not_confirmed": "Schakel het selectievakje \"Ik heb de analyse en kostenschatting gecontroleerd\" in.",
    "dialog.choose_output_dir": "Doelmap kiezen",
    "dialog.confirm_run": "Vertaling starten",
    "start.confirm_summary": "Er worden naar schatting {characters:,} tekens naar {provider} verzonden (geschatte kosten ${cost:.2f}).\nDoelbestand: {destination}\n\nNu starten?",
    "start.confirm_summary_images": "Er worden naar schatting {characters:,} tekens naar {provider} verzonden (geschatte kosten ${cost:.2f}) voor {count} afbeelding(en).\nDoelmap: {folder}\n\nNu starten?",
    "job.group": "Taak en resultaat",
    "job.idle": "Nog geen taak gestart.",
    "job.running": "Vertaling wordt uitgevoerd …",
    "job.progress_prefix": "Verwerken: {location}",
    "job.progress_count": "{processed} van {total} alinea's verwerkt",
    "job.progress_count_files": "{processed} van {total} afbeeldingen verwerkt",
    "job.stats_summary": "{translated} vertaald · {skipped} overgeslagen · {failed} mislukt · {chars:,} tekens verzonden",
    "job.cancel": "Annuleren",
    "job.cancel_requested": "Annulering aangevraagd – wordt gestopt na de huidige API-aanroep …",
    "job.result_summary": "Klaar: {translated} vertaald, {skipped} overgeslagen, {failed} mislukt, {chars:,} tekens verzonden.\nUitvoerbestand: {output}\nQA-rapport: {report}",
    "job.result_summary_images": "Klaar: {files} afbeelding(en) verwerkt, {translated} tekstregio's vertaald, {failed} mislukt, {chars:,} tekens verzonden.\nUitvoermap: {output_dir}\nPer afbeelding staat een eigen QA-rapportbestand in de uitvoermap.",
    "job.result_cancelled_suffix": "\nOpmerking: de taak is geannuleerd – dit is een gedeeltelijk resultaat, reeds vertaalde inhoud is opgeslagen.",
    "job.overflow_none": "Geen nieuwe overlooprisico's gevonden.",
    "job.overflow_count": "{count} overloopmelding(en) in het QA-rapport – controleer dit handmatig in PowerPoint/Impress.",
    "job.pdf_overflow_none": "Geen enkel blok hoefde te groeien of te krimpen bij het invoegen.",
    "job.pdf_overflow_count": "{count} blok(ken) moest(en) groeien of krimpen om te passen – controleer dit steekproefsgewijs in de PDF.",
    "job.open_folder": "Map openen",
    "job.open_report": "QA-rapport openen",
    "job.open_folder_failed": "De map kon niet worden geopend.",
    "job.show_report": "QA-rapport weergeven",
    "job.hide_report": "QA-rapport verbergen",
    "job.report_load_error": "Het QA-rapport kon niet worden geladen.",
    "job.correct_translation": "Vertaling corrigeren",
    "job.correction_starting": "Correctie wordt gestart …",
    "job.correction_opened": "Correctievenster geopend - bewerk daar, klik vervolgens op \"Toepassen\" of \"Annuleren\".",
    "job.correction_applied": "Correctie toegepast.",
    "job.correction_cancelled": "Correctie geannuleerd.",
    "job.correction_timeout": "Time-out bij correctie - geen reactie van het correctievenster.",
    "job.correction_failed": "Correctie mislukt: {error}",
    "job.correction_error": "De correctie kon niet worden gestart.",
    "job.failed_title": "Vertaling mislukt",
    "correction.title": "PDF-vertaling corrigeren",
    "correction.hint": "Selecteer hieronder een rij en bewerk de vertaling ervan in de editor daaronder. Met Vet/Cursief/Onderstrepen (ook via Ctrl+B/Ctrl+I/Ctrl+U) kunt u de opmaak aanpassen – ook bewerkte rijen behouden daarbij hun opmaak.",
    "correction.column_page": "Pagina",
    "correction.column_original": "Origineel",
    "correction.column_translation": "Vertaling",
    "correction.editor_label": "Vertaling bewerken:",
    "correction.bold": "Vet",
    "correction.italic": "Cursief",
    "correction.underline": "Onderstrepen",
    "correction.bold_tooltip": "Vet (Ctrl+B)",
    "correction.italic_tooltip": "Cursief (Ctrl+I)",
    "correction.underline_tooltip": "Onderstrepen (Ctrl+U)",
    "correction.apply": "Toepassen en opslaan",
    "correction.close": "Sluiten",
    "correction.applying": "Wordt toegepast …",
    "correction.success": "{count} blok(ken) bijgewerkt en opgeslagen in {output}.",
    "correction.failed": "Correctie mislukt: {error}",
    "image_correction.title": "Afbeeldingsvertaling corrigeren",
    "image_correction.hint": "Selecteer hieronder een rij en bewerk de vertaling ervan in de editor daaronder.",
    "image_correction.canvas_hint": "In de afbeelding links kunt u het vak van een rij verslepen om het te verplaatsen. Selecteer de rij om aan de rechteronderhoek te slepen en het formaat te wijzigen. Met Ctrl+scrollwiel of de zoomknoppen kunt u in- en uitzoomen op de afbeelding; het dialoogvenster kan ook worden gemaximaliseerd.",
    "image_correction.reset_geometry": "Positie/grootte terugzetten",
    "image_correction.zoom_in": "Inzoomen (+)",
    "image_correction.zoom_out": "Uitzoomen (−)",
    "image_correction.zoom_reset": "Passend maken",
    "image_correction.add_region": "Nieuw vak toevoegen",
    "image_correction.add_region_hint": "Sleep een gebied in de afbeelding om daar een nieuw vak met eigen tekst toe te voegen.",
    "image_correction.show_original": "Origineel weergeven",
    "image_correction.manual_region_label": "(handmatig toegevoegd, geen OCR-herkenning)",
    "image_correction.manual_region_added": "Nieuw vak toegevoegd - voer de vertaling in de editor in.",
    "image_correction.column_original": "Origineel",
    "image_correction.column_translation": "Vertaling",
    "image_correction.editor_label": "Vertaling bewerken:",
    "image_correction.font_size_label": "Lettergrootte:",
    "image_correction.font_size_auto": "Automatisch",
    "image_correction.bold": "Vet",
    "image_correction.centered": "Gecentreerd",
    "image_correction.apply": "Toepassen en opslaan",
    "image_correction.close": "Sluiten",
    "image_correction.applying": "Wordt toegepast …",
    "image_correction.success": "{count} regio('s) bijgewerkt en opgeslagen in {output}.",
    "image_correction.failed": "Correctie mislukt: {error}",
    "image_correction.choose_file_title": "Bestand om te corrigeren selecteren",
    "image_correction.choose_file_label": "Welk bestand uit deze taak moet worden gecorrigeerd?",
    "update.available": "Update beschikbaar: {version}",
    "update.confirm_title": "Update installeren?",
    "update.confirm_body": "Er is een nieuwe versie ({version}) beschikbaar. Nu downloaden en installeren?",
    "update.installing": "Update wordt geïnstalleerd …",
    "update.success_title": "Update geïnstalleerd",
    "update.success_body": "De update is geïnstalleerd. Start de toepassing opnieuw op om de wijzigingen te laten ingaan.",
    "update.failed_title": "Update mislukt",
    "update.failed_body": "De update kon niet worden geïnstalleerd: {error}\n\nDe eerder geïnstalleerde versie blijft ongewijzigd werken.",
    "menu.help": "Help",
    "menu.help.hw_check": "Hardwaretest weergeven/herhalen …",
    "menu.help.check_updates": "Controleren op updates …",
    "menu.help.about": "Over …",
    "about.body": "<h3>{app_name}</h3><p>Versie {version}</p><p>Vertaalt PDF-, Word- en PowerPoint-documenten en afbeeldingen met behoud van de opmaak.</p><p>© {year} {author}<br>Licentie: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Broncode: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Gebruikershandleiding …",
    "manual.hint_link": "Meer hierover in de gebruikershandleiding (hoofdstuk 4)",
    "manual.missing": "De gebruikershandleiding is niet gevonden:\n{path}",
    "update.check.no_update_title": "Geen update beschikbaar",
    "update.check.no_update_body": "U gebruikt al de nieuwste versie ({version}).",
    "update.check.failed_title": "Controle op updates mislukt",
    "update.check.failed_body": "Er kon niet worden gecontroleerd op updates: {error}",
    "hw_check.title": "Hardwaretest",
    "hw_check.note": "Werkt de app niet zoals verwacht (bijvoorbeeld bij lokale AI-inpainting), dan kunt u hier de hardware opnieuw controleren.",
    "hw_check.recheck_button": "Opnieuw controleren",
    "hw_check.checking": "Hardware wordt gecontroleerd …",
    "hw_check.never_checked": "Nog geen hardwarecontrole uitgevoerd. Klik op \"Opnieuw controleren\" om nu te controleren.",
    "hw_check.not_found": "Geen CUDA-GPU gevonden (laatst gecontroleerd: {checked_at}). Lokale AI-inpainting is niet beschikbaar op deze hardware - cloud-inpainting werkt hier onafhankelijk van.",
    "hw_check.found_ok": "{name} met {vram_gb:.0f} GB videogeheugen gevonden (laatst gecontroleerd: {checked_at}). Voldoet aan de aanbeveling van minimaal {min_gb:.0f} GB.",
    "hw_check.found_below_recommended": "{name} met {vram_gb:.0f} GB videogeheugen gevonden (laatst gecontroleerd: {checked_at}). Ligt onder de aanbeveling van {min_gb:.0f} GB - werkt mogelijk, maar zonder garantie, vooral bij grote afbeeldingen of veel tekstgebieden tegelijk.",
    "hw_check.driver_cuda_ok": "Driver ondersteunt CUDA {cuda_version} - bijbehorende PyTorch-variant: {torch_variant}.",
    "hw_check.driver_cuda_too_old": "Driver ondersteunt alleen CUDA {cuda_version} - te oud voor lokale AI-inpainting (minimaal 11.8 vereist). Werk de grafische driver bij.",
    "settings.button": "Instellingen …",
    "settings.title": "Instellingen",
    "settings.language": "Interfacetaal",
    "settings.prepared": "voorbereid",
    "settings.provider": "Provider",
    "settings.credentials": "Inloggegevens",
    "settings.new_key": "Nieuwe API-sleutel",
    "settings.key_placeholder": "Wordt nooit weergegeven of gelogd",
    "settings.storage": "Opslaglocatie",
    "settings.environment": "Omgevingsvariabele (alleen deze sessie)",
    "settings.keyring": "OS-keyring",
    "settings.both": "Beide",
    "settings.run_limit": "Kostenlimiet per taak (tekens)",
    "settings.save_key": "API-sleutel opslaan/vervangen",
    "settings.save_button": "Opslaan",
    "settings.open_log": "Logbestand openen …",
    "settings.session_note": "Opmerking: de omgevingsvariabele is in deze versie niet blijvend.",
    "settings.credentials_group": "API-toegang",
    "settings.general_group": "Algemeen",
    "settings.env_override_warning": "Voor deze provider wordt momenteel een waarde uit een omgevingsvariabele gebruikt, niet de hier opgeslagen keyring-vermelding. Verwijder deze omgevingsvariabele op besturingssysteemniveau om de opgeslagen sleutel te gebruiken.",

    "settings.provider.tooltip": "Provider waarvan hieronder een sleutel wordt beheerd",
    "settings.provider.whatsthis": (
        "Bepaalt voor welke vertaalprovider (DeepL, Google, OpenAI, "
        "Grok) de status, nieuwe sleutel en opslaglocatie hieronder "
        "gelden. Elke provider heeft een eigen, apart opgeslagen "
        "sleutel."
    ),
    "settings.status.tooltip": "Waar de momenteel gebruikte sleutel vandaan komt",
    "settings.status.whatsthis": (
        "Toont of er voor de gekozen provider een sleutel is gevonden "
        "in de OS-keyring, in een omgevingsvariabele, of helemaal "
        "geen. Een omgevingsvariabele heeft altijd voorrang op de "
        "keyring - zie de waarschuwing verderop als dat hier het geval "
        "is."
    ),
    "settings.secret.tooltip": "Nieuwe API-sleutel voor de gekozen provider",
    "settings.secret.whatsthis": (
        "Plak hier de van de provider ontvangen API-sleutel en klik op "
        "\"Opslaan\". Tijdens het typen wordt deze als stippen "
        "weergegeven, maar niet automatisch toegepast - alleen de "
        "knop Opslaan schrijft hem naar de gekozen opslaglocatie."
    ),
    "settings.target_field.tooltip": "Waar de nieuwe sleutel wordt opgeslagen",
    "settings.target_field.whatsthis": (
        "\"OS-keyring\" is de aanbevolen, blijvende keuze. "
        "\"Omgevingsvariabele\" geldt alleen voor de huidige sessie en "
        "is vooral bedoeld voor bijzondere gevallen/probleemoplossing "
        "- zie de opmerking hieronder. \"Beide\" schrijft daarnaast ook "
        "zo'n sessievariabele."
    ),
    "settings.max_chars.tooltip": "Bovengrens van tekens per vertaalrun",
    "settings.max_chars.whatsthis": (
        "Een run met meer tekens dan hier ingesteld wordt met een "
        "melding gestopt in plaats van onverwacht hoge kosten te "
        "veroorzaken. Verhoog dit hier indien nodig."
    ),
    "settings.save_key.tooltip": "Nieuwe sleutel opslaan",
    "settings.save_key.whatsthis": (
        "Schrijft de hierboven ingevoerde sleutel voor de gekozen "
        "provider naar de gekozen opslaglocatie. Het invoerveld wordt "
        "daarna geleegd en de status hierboven wordt bijgewerkt."
    ),
    "settings.open_log.tooltip": "Logbestand van de app openen",
    "settings.open_log.whatsthis": (
        "Opent het huidige logbestand in het standaardprogramma van "
        "het systeem - handig om foutmeldingen in een bugreport te "
        "plakken zonder een schermafbeelding te maken."
    ),

    "hw_check.status.tooltip": "Resultaat van de laatste GPU-controle",
    "hw_check.status.whatsthis": (
        "Toont of een ondersteunde NVIDIA-GPU met voldoende VRAM is "
        "gevonden, wanneer er voor het laatst is gecontroleerd, en of "
        "de CUDA-versie van de geïnstalleerde driver lokale "
        "GPU-inpainting ondersteunt. Zonder passende GPU/driver werkt "
        "lokale inpainting nog steeds - alleen trager, op de CPU."
    ),
    "hw_check.recheck_button.tooltip": "GPU-controle nu opnieuw uitvoeren",
    "hw_check.recheck_button.whatsthis": (
        "Voert dezelfde controle opnieuw uit die ook het "
        "installatieprogramma heeft gedaan - handig na een "
        "driverupdate of het wisselen van videokaart, zonder de app "
        "opnieuw te hoeven installeren."
    ),

    "bootstrap.help.back_button": (
        "Terug naar de vorige stap\n\n"
        "Wat al is ingevuld bij deze en de vorige stap blijft bewaard."
    ),
    "bootstrap.help.next_button": "Doorgaan naar de volgende stap",
    "bootstrap.help.cancel_button": (
        "Sluit deze wizard\n\n"
        "Er wordt om bevestiging gevraagd als er een installatie loopt. "
        "De installatie kan altijd opnieuw worden gestart."
    ),
    "bootstrap.help.language_combo": (
        "Taal van deze wizard\n\n"
        "Geldt direct voor alle schermen van deze wizard. De app zelf "
        "krijgt later een eigen, onafhankelijke taalkeuze."
    ),
    "bootstrap.help.mode_online_radio": (
        "Vertalen verloopt via cloudproviders (DeepL, Google, OpenAI, "
        "Grok); beeldbewerking gebruikt hier een eenvoudigere methode "
        "in plaats van AI-gestuurde inpainting\n\n"
        "Snelste en eenvoudigste installatie, werkt op elke computer. "
        "Vereist een eigen API-sleutel van de gekozen provider en een "
        "internetverbinding tijdens het vertalen."
    ),
    "bootstrap.help.mode_local_radio": (
        "Betere, AI-gestuurde beeldbewerking op deze videokaart in "
        "plaats van de eenvoudigere standaardmethode\n\n"
        "Vereist een ondersteunde NVIDIA-videokaart met voldoende "
        "videogeheugen (wordt in de volgende stap gecontroleerd) - "
        "daarvoor blijven afbeeldingen volledig op deze computer."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Toch lokaal doorgaan met installeren\n\n"
        "Handig als de controle ten onrechte mislukte of een "
        "driverupdate nog uitstaat - lokale verwerking kan later altijd "
        "opnieuw worden gecontroleerd via Help -> Hardwaretest."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "In plaats daarvan de online variant installeren\n\n"
        "Schakelt deze installatie over naar cloudproviders, zonder "
        "vraag over de GPU. Kan later altijd worden toegevoegd via de "
        "instellingen van de app."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Bij de volgende stap een API-sleutel voor {provider} "
        "invoeren\n\n"
        "Niet-aangevinkte providers kunnen altijd later worden "
        "toegevoegd in de instellingen van de app."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Doorgaan zonder sleutels in te voeren\n\n"
        "Sleutels kunnen altijd later worden toegevoegd in de "
        "instellingen van de app - zonder minstens één sleutel werkt "
        "vertalen echter nog niet."
    ),
    "bootstrap.help.credentials_continue_button": "Doorgaan naar het invoeren van de sleutel, of naar de volgende provider",
    "bootstrap.help.credential_open_signup_button": (
        "Opent de aanmeldpagina van deze provider in de browser\n\n"
        "Daar wordt de API-sleutel aangemaakt, die daarna hier wordt "
        "geplakt."
    ),
    "bootstrap.help.credential_key_entry": (
        "Plak hier de API-sleutel van deze provider\n\n"
        "Wordt tijdens het typen als stippen weergegeven. Alleen de "
        "knop Opslaan hieronder past hem daadwerkelijk toe."
    ),
    "bootstrap.help.credential_save_button": "Sla de hierboven ingevoerde sleutel nu op",
    "bootstrap.help.finish_close_button": "Wizard sluiten zonder de app nu te starten",
    "bootstrap.help.finish_launch_button": "Wizard sluiten en de app direct starten",
    "credentials.title": "Inloggegevens",
    "credentials.saved": "API-sleutel is opgeslagen.",
    "credential.environment": "Omgevingsvariabele (sessie)",
    "credential.keyring": "OS-keyring",
    "credential.missing": "Niet ingesteld",
    "provider.missing_key": "Geen API-sleutel ingesteld voor \"{provider}\". <a href=\"settings\">Nu instellen</a>",
    "provider.missing_key_dialog": "Voor de provider \"{provider}\" is geen API-sleutel ingesteld. Zonder sleutel mislukt elke vertaalaanroep.",
    "dialog.check_input": "Invoer controleren",
    "dialog.analysis": "Analyse",
    "dialog.choose_images": "Afbeeldingen selecteren",
    "dialog.choose_document": "Document selecteren",
    "merge.button": "PDF's samenvoegen/invoegen …",
    "merge.title": "PDF's samenvoegen/invoegen",
    "merge.intro": "Stel de bronbestanden samen in de gewenste volgorde. Per bestand kan optioneel een paginaselectie worden opgegeven (leeg = hele bestand) - voeg hetzelfde bestand meerdere keren toe met een verschillende paginaselectie om het op een bepaalde plek in een ander bestand in te voegen.",
    "merge.column_file": "Bestand",
    "merge.column_pages": "Pagina's",
    "merge.pages_placeholder": "alle",
    "merge.pages_tooltip": "Leeg = hele bestand. Anders bijv. \"1-3,5\" of \"6-\" (pagina 6 tot het einde) of \"-4\" (begin tot pagina 4). \"5-3\" voegt de pagina's 5,4,3 in deze (omgekeerde) volgorde in.",
    "merge.add_files": "Bestanden toevoegen …",
    "merge.remove_selected": "Verwijderen",
    "merge.move_up": "Omhoog",
    "merge.move_down": "Omlaag",
    "merge.sort_by_name": "Sorteren op naam",
    "merge.sort_by_date": "Sorteren op datum",
    "merge.sort_by_date_tooltip": "Sorteert op de wijzigingsdatum van het bestand op schijf (laatste wijziging, niet de aanmaakdatum).",
    "merge.output_file_label": "Doelbestand",
    "merge.output_placeholder": "Doelbestand kiezen …",
    "merge.choose_output_file": "Opslaan als …",
    "merge.start_button": "Samenvoegen starten",
    "merge.cancel_button": "Annuleren",
    "merge.close_button": "Sluiten",
    "merge.status_running": "Verwerken: {message}",
    "merge.status_done": "Klaar: {pages} pagina('s) uit {files} bestand(en) geschreven.",
    "merge.status_cancelled": "Geannuleerd (gedeeltelijk resultaat opgeslagen): {pages} pagina('s) geschreven.",
    "merge.status_failed": "Mislukt: {error}",
    "merge.error_dialog_choose_files": "PDF-bestanden selecteren",
    "merge.error_dialog_choose_output": "Doelbestand kiezen",
    "merge.failed_title": "Samenvoegen mislukt",
    "merge_search.button": "Map doorzoeken …",
    "merge_search.title": "PDF's zoeken in een map",
    "merge_search.folder_label": "Map",
    "merge_search.folder_placeholder": "Map kiezen …",
    "merge_search.choose_folder": "Map kiezen …",
    "merge_search.choose_folder_dialog_title": "Map om te doorzoeken kiezen",
    "merge_search.recursive_checkbox": "Incl. submappen",
    "merge_search.scope_ico_format": "ICO-formaat (kopgebied pagina 1)",
    "merge_search.scope_header": "Header (alle pagina's)",
    "merge_search.scope_full_text": "Volledige tekst",
    "merge_search.scope_ico_format_tooltip": "Doorzoekt ALLEEN het ICO-metadatablok op pagina 1 (developer, QSI ICO, uitgiftedatum, ...). Onafhankelijk van \"Header\" hieronder - als alleen deze optie is aangevinkt, wordt het terugkerende kopgebied op de ANDERE pagina's NIET doorzocht.",
    "merge_search.scope_header_tooltip": "Doorzoekt ALLEEN het bovenste gebied dat op elke pagina terugkeert (bijv. bedrijfsnaam/logoregel). Onafhankelijk van \"ICO-formaat\" hierboven - een eigen, aparte tekstregio, geen uitbreiding daarvan.",
    "merge_search.scope_full_text_tooltip": "Doorzoekt de VOLLEDIGE tekst op alle pagina's, inclusief de gebieden van \"ICO-formaat\" en \"Header\" hierboven.",
    "merge_search.error_missing_scope": "Selecteer ten minste één zoekgebied.",
    "merge_search.date_filter_group": "Filteren op datum",
    "merge_search.date_source_file": "Bestandsdatum",
    "merge_search.date_source_document": "Datum in het document",
    "merge_search.date_region_ico_format": "ICO-veld (pagina 1)",
    "merge_search.date_region_header": "Header (alle pagina's)",
    "merge_search.date_region_footer": "Footer (alle pagina's)",
    "merge_search.date_format_iso": "ISO (JJJJ-MM-DD)",
    "merge_search.date_format_iso_tooltip": "Herkent bijv. \"2026-09-04\".",
    "merge_search.date_format_de": "Duits (DD.MM.JJJJ)",
    "merge_search.date_format_de_tooltip": "Herkent bijv. \"04.09.2026\" (ook tweecijferige jaren zoals \"04.09.26\").",
    "merge_search.date_format_en_month": "Engels (maandnaam, bijv. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Herkent zowel \"September 4, 2026\" als \"4. September 2026\" (komma optioneel, dag één- of tweecijferig).",
    "merge_search.date_format_slash": "Schuine streep (DD/MM/JJJJ)",
    "merge_search.date_format_slash_tooltip": "Herkent bijv. \"04/09/2026\".",
    "merge_search.date_exact_checkbox": "Exacte datum",
    "merge_search.date_from_label": "Van",
    "merge_search.date_to_label": "Tot",
    "merge_search.date_exact_label": "Datum",
    "merge_search.error_date_range_reversed": "\"Van\" mag niet na \"Tot\" liggen.",
    "merge_search.error_missing_date_region": "Selecteer ten minste één gebied voor de datumzoekopdracht.",
    "merge_search.error_missing_date_format": "Selecteer ten minste één datumnotatie of voer een eigen notatie in.",
    "merge_search.date_custom_format_label": "Eigen notatie",
    "merge_search.date_custom_format_placeholder": "bijv. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Eigen datumnotatie met deze plaatshouders (altijd in het Engels invoeren, ook in dit Nederlandse dialoogvenster) - alle andere tekens zoals spaties, komma's, punten of schuine strepen worden letterlijk gezocht:\n\nYYYY – jaar, 4 cijfers, bijv. 2026\nYY – jaar, 2 cijfers, bijv. 26\nMMMM – maandnaam, bijv. September\nMMM – maandnaam afgekort, bijv. Sep\nMM – maand, 2 cijfers, bijv. 09\nM – maand, 1 of 2 cijfers, bijv. 9\nDD – dag, 2 cijfers, bijv. 04\nD – dag, 1 of 2 cijfers, bijv. 4\n\nVoorbeelden:\n\"MMMM D, YYYY\" vindt \"September 4, 2026\"\n\"MMMM DD, YYYY\" vindt \"September 04, 2026\"\n\"YYYY/MM/DD\" vindt \"2026/09/04\"",
    "merge_search.error_invalid_custom_date_format": "De eigen datumnotatie is ongeldig - gebruik de plaatshouders uit de tooltip.",
    "merge_search.query_label": "Zoektekst (AND/OR resp. &&/|| om meerdere termen te combineren)",
    "merge_search.query_placeholder": "bijv. bedrijfsnaam van de developer, of term1 AND term2 – laat leeg voor alle bestanden in de map",
    "merge_search.query_tooltip": "Meerdere zoektermen kunnen worden gecombineerd met AND en OR - ook gemengd. Met haakjes bepaalt u wat bij elkaar hoort.\n\nVoorbeeld: \"Acme AND contract\" vindt alleen bestanden die BEIDE termen bevatten.\n\"Acme OR Zenith\" vindt bestanden met TEN MINSTE ÉÉN van de twee termen.\n\nGemengd met haakjes: \"StellarRussia OR (The AND Korolev AND Directive)\" vindt bestanden met \"StellarRussia\" OR bestanden die ALLE DRIE de termen \"The\", \"Korolev\" en \"Directive\" bevatten.\n\nIn plaats van AND/OR kunt u ook de tekens && en || gebruiken (gelijkwaardig, ook gemengd met de woorden): \"Acme && contract\" is hetzelfde als \"Acme AND contract\".\n\nZonder AND/OR wordt de volledige tekst als één enkele zoekterm behandeld (zoals voorheen). Hoofdlettergevoeligheid speelt geen rol.",
    "merge_search.search_button": "Zoeken",
    "merge_search.cancel_button": "Annuleren",
    "merge_search.select_all": "Alles selecteren",
    "merge_search.select_none": "Niets selecteren",
    "merge_search.detach_results_button": "Resultatenlijst in eigen venster openen",
    "merge_search.reattach_results_button": "Resultatenlijst weer vastmaken",
    "merge_search.results_detached_placeholder": "De resultatenlijst is geopend in een apart venster.",
    "merge_search.detached_results_title_suffix": "Resultaten",
    "merge_search.take_selected": "Geselecteerde overnemen",
    "merge_search.close_button": "Sluiten",
    "merge_search.status_running": "Doorzoeken: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} treffer(s) van {scanned} doorzochte PDF('s).",
    "merge_search.status_done_with_errors": "{matches} treffer(s) van {scanned} doorzochte PDF('s) ({errors} onleesbaar).",
    "merge_search.status_cancelled": "Geannuleerd: {matches} treffer(s) van {scanned} doorzochte PDF('s).",
    "merge_search.status_failed": "Mislukt: {error}",
    "merge_search.error_missing_folder": "Kies eerst een map.",
    "merge_search.failed_title": "Zoeken mislukt",
    "merge_search.source_local": "Lokale map",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Drive-maplink of -ID",
    "merge_search.drive_folder_placeholder": "Deellink of map-ID plakken …",
    "merge_search.drive_resolve_button": "Controleren",
    "merge_search.drive_folder_unresolved": "Nog niet gecontroleerd.",
    "merge_search.drive_folder_resolved": "Map \"{name}\" gevonden.",
    "merge_search.drive_folder_resolve_failed": "Mislukt: {error}",
    "merge_search.drive_cache_label": "Cachemap (downloads blijven hier bewaard)",
    "merge_search.drive_choose_cache": "Cachemap kiezen …",
    "merge_search.drive_choose_cache_dialog_title": "Map voor gedownloade treffers kiezen",
    "merge_search.drive_credentials_label": "Google OAuth-inloggegevens (eenmalig, zie docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Uit JSON-bestand laden …",
    "merge_search.drive_load_from_file_dialog_title": "Client-secrets-JSON van Google Cloud Console kiezen",
    "merge_search.drive_load_from_file_failed": "Bestand kon niet worden gelezen: {error}",
    "merge_search.drive_client_id_placeholder": "Client-ID",
    "merge_search.drive_client_secret_placeholder": "Client secret",
    "merge_search.drive_project_id_placeholder": "Project-ID",
    "merge_search.drive_save_credentials": "Inloggegevens opslaan",
    "merge_search.drive_credentials_saved": "Inloggegevens opgeslagen.",
    "merge_search.drive_save_failed": "Opslaan mislukt: {error}",
    "merge_search.drive_not_configured": "Nog geen Client-ID/client secret/project-ID ingesteld.",
    "merge_search.drive_configured_not_connected": "Geconfigureerd, maar nog niet verbonden.",
    "merge_search.drive_connected": "Verbonden{account}.",
    "merge_search.drive_connect_button": "Verbinden met Google",
    "merge_search.drive_disconnect_button": "Verbinding verbreken",
    "merge_search.drive_connecting": "Browser wordt geopend om aan te melden …",
    "merge_search.drive_connect_failed": "Verbinding mislukt: {error}",
    "merge_search.drive_error_missing_folder": "Geef en controleer eerst een Drive-map.",
    "merge_search.drive_error_missing_cache": "Kies eerst een cachemap.",
    "merge_search.drive_error_not_connected": "Maak eerst verbinding met Google.",
    "word_merge.button": "DOCX-bestanden samenvoegen/invoegen …",
    "word_merge.title": "DOCX-bestanden samenvoegen/invoegen",
    "word_merge.intro": "Stel de bronbestanden samen in de gewenste volgorde - altijd hele bestanden (DOCX kent, in tegenstelling tot PDF, geen vast aantal pagina's in het bestandsformaat zelf). Voeg hetzelfde bestand meerdere keren toe om het op meerdere plekken in te voegen. Bij meer dan 100 bestanden wordt automatisch in groepen samengevoegd (zie de statusregel na de taak).",
    "word_merge.status_done": "Klaar: {segments} van {files} bestand(en) overgenomen{batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Geannuleerd (gedeeltelijk resultaat opgeslagen): {segments} bestand(en) overgenomen{batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " in {batches} groep(en)",
    "word_merge.status_warning_suffix": ", {count} overgeslagen (zie hieronder)",
    "word_merge.warnings_title": "Overgeslagen bestanden:",
    "word_merge.error_dialog_choose_files": "DOCX-bestanden selecteren",
    "word_merge_search.title": "DOCX-bestanden zoeken in een map",
    "word_merge_search.status_done": "{matches} treffer(s) van {scanned} doorzochte DOCX-bestand(en).",
    "word_merge_search.status_done_with_errors": "{matches} treffer(s) van {scanned} doorzochte DOCX-bestand(en) ({errors} onleesbaar).",
    "word_merge_search.status_cancelled": "Geannuleerd: {matches} treffer(s) van {scanned} doorzochte DOCX-bestand(en).",
    "bootstrap.window_title": "Document Translator instellen",
    "bootstrap.back_button": "Terug",
    "bootstrap.next_button": "Volgende",
    "bootstrap.cancel_button": "Annuleren",
    "bootstrap.cancel_title": "Installatie annuleren?",
    "bootstrap.cancel_confirm": (
        "De installatiewizard wordt gesloten zonder dat Document Translator "
        "volledig is ingesteld. Reeds aangemaakte bestanden worden "
        "automatisch verwijderd. Doorgaan?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "De installatie is nu bezig. Annuleren verwijdert automatisch "
        "reeds aangemaakte bestanden - in zeldzame gevallen kan een "
        "bestand dat op dat moment nog in gebruik is, achterblijven. "
        "Toch annuleren?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Beheerdersrechten",
    "bootstrap.elevated_warning_text": (
        "Document Translator is gestart als beheerder.\n\n"
        "Dat is niet nodig en zorgt ervoor dat de app later niet meer "
        "werkt bij een normale start (zonder beheerdersrechten).\n\n"
        "Sluit dit venster en start de installatie opnieuw met een "
        "gewone dubbelklik (niet via \"Als administrator "
        "uitvoeren\").\n\n"
        "Dit bericht kan worden gekopieerd met Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Document Translator verwijderen",
    "bootstrap.uninstall_confirm": (
        "Document Translator verwijderen, inclusief alle lokaal opgeslagen "
        "instellingen en API-sleutels?"
    ),
    "bootstrap.uninstall_done": "Document Translator is verwijderd.",
    "bootstrap.welcome_title": "Welkom",
    "bootstrap.welcome_text": "Deze wizard installeert Document Translator op deze computer - volledig zonder opdrachtregel. Hij downloadt de benodigde onderdelen en maakt aan het einde een item aan in het toepassingenmenu.",
    "bootstrap.language_label": "Taal",
    "bootstrap.mode_title": "Online of lokaal?",
    "bootstrap.mode_intro": "Hoe moet er worden vertaald? U kunt dit later altijd wijzigen in Instellingen.",
    "bootstrap.mode_online_label": "Online (cloudprovider)",
    "bootstrap.mode_online_desc": "Vertaling verloopt via een externe provider (DeepL, Google, OpenAI of Grok). Hiervoor lopen doorlopende kosten per vertaling, en is een eigen API-sleutel van de betreffende provider nodig - daarover zo meteen meer. Beeldbewerking in afbeeldingen werkt ook hier, alleen met een eenvoudigere methode in plaats van AI-gestuurde inpainting. Geen grote download nodig. Aanbevolen als er geen krachtige grafische kaart aanwezig is.",
    "bootstrap.mode_local_label": "Lokaal (op deze grafische kaart)",
    "bootstrap.mode_local_desc": "Verbetert alleen de beeldbewerking: tekst in afbeeldingen wordt via OCR herkend en na vertaling met een AI-model (LaMa) opnieuw op deze grafische kaart in de afbeelding getekend - het resultaat ziet er properder uit dan de eenvoudigere methode die ook zonder deze optie beschikbaar is. De eigenlijke tekstvertaling verloopt in beide modi via een externe provider (DeepL, Google, OpenAI of Grok), tegen de gebruikelijke kosten per vertaling bij die provider. Online providers kunt u daarnaast altijd nog instellen in Instellingen, indien gewenst. Vereist een voldoende krachtige NVIDIA-grafische kaart (wordt in de volgende stap gecontroleerd) en downloadt tijdens de installatie eenmalig ca. 2-3 GB.",
    "bootstrap.gpu_checking": "Grafische kaart wordt gecontroleerd …",
    "bootstrap.gpu_ok": "Gevonden: {name} met {vram_gb:.0f} GB videogeheugen - dat is voldoende.",
    "bootstrap.gpu_insufficient": "Gevonden: {name} met {vram_gb:.0f} GB videogeheugen - aanbevolen is minimaal {min_gb:.0f} GB. Lokaal zal waarschijnlijk erg traag zijn.",
    "bootstrap.gpu_not_found": "Geen ondersteunde NVIDIA-grafische kaart gevonden. Lokaal is op deze computer niet zinvol te gebruiken.",
    "bootstrap.gpu_driver_too_old": "Gevonden: {name}, maar de NVIDIA-driver is te oud (ondersteunt alleen CUDA {cuda_version}, minimaal 11.8 is vereist). Werk de grafische driver bij en start de wizard opnieuw, of kies in plaats daarvan Online.",
    "bootstrap.gpu_mac_unsupported": "De lokale modus wordt momenteel niet ondersteund op de Mac. Kies in plaats daarvan Online.",
    "bootstrap.gpu_continue_local_button": "Toch doorgaan met lokaal",
    "bootstrap.gpu_switch_online_button": "Overschakelen naar Online",
    "bootstrap.install_title": "Installatie wordt uitgevoerd",
    "bootstrap.install_step_venv": "Werkomgeving wordt aangemaakt …",
    "bootstrap.install_step_deps": "Onderdelen worden geïnstalleerd ({name}) …",
    "bootstrap.install_step_source": "Programmacode wordt gedownload …",
    "bootstrap.install_step_shortcut": "Item in toepassingenmenu wordt aangemaakt …",
    "bootstrap.install_failed_title": "Installatie mislukt",
    "bootstrap.install_failed": "Mislukt: {error}",
    "bootstrap.credentials_title": "API-sleutels instellen",
    "bootstrap.credentials_intro": "Welke providers wilt u instellen? U kunt dit altijd overslaan en later alsnog doen in de instellingen van de app.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Snelle zelfregistratie. Gratis quotum beschikbaar, daarna betaald.",
    "bootstrap.credentials_explain_google": "Vereist een Google Cloud-project met een geregistreerde betaalmethode - iets bewerkelijker in te stellen dan de andere drie providers.",
    "bootstrap.credentials_explain_openai": "Snelle zelfregistratie, betaald naar gebruik.",
    "bootstrap.credentials_explain_grok": "Snelle zelfregistratie, betaald naar gebruik.",
    "bootstrap.credentials_open_signup_button": "Sleutel aanvragen (opent browser)",
    "bootstrap.open_browser_title": "Browser openen?",
    "bootstrap.open_browser_text": (
        "De volgende link wordt geopend in de standaardbrowser:\n\n"
        "{url}\n\n"
        "Controleer of dit echt het verwachte adres is voordat je "
        "verder gaat."
    ),
    "bootstrap.credentials_key_label": "API-sleutel voor {provider}",
    "bootstrap.credentials_key_placeholder": "Sleutel plakken …",
    "bootstrap.credentials_save_button": "Opslaan",
    "bootstrap.credentials_saved": "Opgeslagen.",
    "bootstrap.credentials_skip_all_button": "Later, in Instellingen",
    "bootstrap.credentials_continue_button": "Volgende",
    "bootstrap.finish_title": "Klaar",
    "bootstrap.finish_text": "Document Translator is ingesteld en te vinden in het toepassingenmenu.",
    "bootstrap.finish_download_size": "Daadwerkelijk gedownload: ca. {size_gb:.1f} GB.",
    "bootstrap.finish_launch_button": "Nu starten",
    "bootstrap.finish_close_button": "Sluiten",
    "mode.tooltip": "Type document dat vertaald moet worden",
    "mode.whatsthis": (
        "Bepaalt welke vertaalworkflow wordt gebruikt: PDF, PowerPoint/"
        "Impress, Word/Writer of losse afbeeldingen. Afhankelijk van de "
        "keuze worden hieronder alleen de relevante velden getoond, "
        "bijv. de OCR-instellingen alleen in de modus \"Afbeeldingen\"."
    ),
    "source.tooltip": "Bestand(en) selecteren om te vertalen",
    "source.whatsthis": (
        "Opent de bestandskiezer voor het bronbestand (in de modus "
        "Afbeeldingen ook meerdere bestanden tegelijk). De gekozen "
        "bestandsnaam verschijnt daarna links ernaast."
    ),
    "source_label.tooltip": "Momenteel geselecteerd bronbestand",
    "source_label.whatsthis": (
        "Toont de naam van het bestand dat laatst is gekozen via "
        "\"Bestand selecteren …\". Staat hier nog \"Geen bestand "
        "geselecteerd\", kies dan eerst een bestand voordat een "
        "kostenanalyse mogelijk is."
    ),
    "image_mode.tooltip": "Omgang met afbeeldingen die in het document zijn ingesloten",
    "image_mode.whatsthis": (
        "\"Niet vertalen\" laat ingesloten afbeeldingen ongewijzigd. "
        "\"Later afzonderlijk selecteren\" toont na de kostenanalyse een "
        "lijst waaruit specifieke afbeeldingen gekozen worden. \"Alles "
        "vertalen\" verwerkt automatisch elke ingesloten afbeelding."
    ),
    "provider.tooltip": "Vertaalprovider voor deze run",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI of Grok - elk met een eigen API-sleutel, "
        "beheerd in Instellingen. Ontbreekt er een sleutel voor de "
        "gekozen provider, dan verschijnt daaronder direct een melding "
        "met een link naar Instellingen."
    ),
    "source_lang.tooltip": "Taalcode van de brontaal, bijv. EN",
    "source_lang.whatsthis": (
        "Tweeletterige taalcode volgens ISO 639-1 (bijv. EN voor Engels, "
        "FR voor Frans). Moet overeenkomen met de daadwerkelijke taal "
        "van het document, anders levert de vertaalprovider onjuiste of "
        "geen resultaten."
    ),
    "target_lang.tooltip": "Taalcode van de doeltaal, bijv. DE",
    "target_lang.whatsthis": (
        "Tweeletterige taalcode volgens ISO 639-1 waarnaar vertaald moet "
        "worden (bijv. DE voor Duits, ES voor Spaans)."
    ),
    "protected.tooltip": "Termen die onvertaald moeten blijven",
    "protected.whatsthis": (
        "Eén term per regel, bijv. bedrijfs- of productnamen. De "
        "vertaalprovider laat deze termen ongemoeid. Via de knop "
        "ernaast kan ook een lijst uit een bestand worden geladen."
    ),
    "ocr_engine_field.tooltip": "Tekstherkenning (OCR) voor afbeeldingen",
    "ocr_engine_field.whatsthis": (
        "Alleen zichtbaar in de modus \"Afbeeldingen\". Herkent tekst in "
        "de afbeeldingen voordat deze wordt vertaald en teruggeschreven. "
        "Is een engine op deze computer niet beschikbaar, dan verschijnt "
        "daaronder een melding."
    ),
    "inpainting_backend_field.tooltip": (
        "Methode om de vertaalde tekst terug te schrijven in de afbeelding"
    ),
    "inpainting_backend_field.whatsthis": (
        "Alleen zichtbaar in de modus \"Afbeeldingen\". "
        "\"Box-overlay\" en \"CV-inpainting\" draaien altijd lokaal, "
        "zonder bijzondere hardware. \"GPU-inpainting\" gebruikt een "
        "lokale videokaart (CUDA) voor het beste resultaat en is alleen "
        "beschikbaar als PyTorch met CUDA-ondersteuning is "
        "geïnstalleerd - anders verschijnt daaronder een melding. De "
        "hardwarestatus is altijd te controleren via Help -> "
        "Hardwaretest."
    ),
    "merge.tooltip": "Meerdere PDF-bestanden samenvoegen",
    "merge.whatsthis": (
        "Opent een apart dialoogvenster om meerdere PDF-bestanden tot "
        "één samen te voegen. Onafhankelijk van het formulier hierboven "
        "- hier wordt niets vertaald."
    ),
    "word_merge.tooltip": "Meerdere Word-bestanden samenvoegen",
    "word_merge.whatsthis": (
        "Opent een apart dialoogvenster om meerdere Word-bestanden tot "
        "één samen te voegen. Onafhankelijk van het formulier hierboven "
        "- hier wordt niets vertaald."
    ),
    "analysis.button.tooltip": "Kosten van deze vertaalrun inschatten",
    "analysis.button.whatsthis": (
        "Telt de te vertalen tekens en schat op basis van de gekozen "
        "provider de globale kosten, zonder al iets te vertalen. Pas "
        "daarna kan het vakje ernaast worden aangevinkt en \"Starten\" "
        "worden vrijgegeven."
    ),
    "analysis.checked.tooltip": "Geschatte kosten bevestigen",
    "analysis.checked.whatsthis": (
        "Moet aangevinkt zijn voordat \"Starten\" klikbaar wordt - een "
        "bewuste veiligheidsstap zodat een run nooit per ongeluk start "
        "zonder eerst naar de geschatte kosten te hebben gekeken."
    ),
    "start.tooltip": "Vertaalrun starten",
    "start.whatsthis": (
        "Wordt pas actief nadat de kosten zijn geanalyseerd en "
        "bevestigd. De voortgang verschijnt in het gebied eronder; een "
        "lopende run kan via \"Annuleren\" worden gestopt."
    ),
    "job.cancel.tooltip": "Lopende vertaalrun annuleren",
    "job.cancel.whatsthis": (
        "Stopt de huidige run zo snel mogelijk. Al verwerkte delen "
        "blijven niet automatisch bewaard als compleet bestand - "
        "afhankelijk van het formaat kan een onvolledig bestand "
        "achterblijven."
    ),
    "job.open_folder.tooltip": "Uitvoermap openen",
    "job.open_folder.whatsthis": (
        "Opent de bestandsverkenner in de doelmap van de zojuist "
        "voltooide run."
    ),
    "job.open_report.tooltip": "QA-rapport van de laatste run openen",
    "job.open_report.whatsthis": (
        "Toont bevindingen van de automatische kwaliteitscontrole van de "
        "laatste run, bijv. passages die het waard kunnen zijn om te "
        "controleren."
    ),
    "job.correct_translation.tooltip": "Afzonderlijke vertalingen corrigeren",
    "job.correct_translation.whatsthis": (
        "Alleen zichtbaar bij PDF-runs met corrigeerbare tekstblokken. "
        "Hiermee kunnen afzonderlijke vertaalde passages gericht worden "
        "bijgewerkt, zonder de hele run te herhalen."
    ),
    "settings.button.tooltip": "Instellingen openen",
    "settings.button.whatsthis": (
        "API-sleutels per provider (aanbevolen: keyring), het "
        "tekenlimiet per run en toegang tot het logbestand."
    ),
    "update_hint.tooltip": "Er is een nieuwe versie beschikbaar",
    "update_hint.whatsthis": (
        "Verschijnt automatisch wanneer bij het opstarten een nieuwere "
        "versie van Document Translator is gevonden. Erop klikken biedt aan "
        "de nieuwe versie te installeren."
    ),
    "flag_row.whatsthis": (
        "Wijzigt onmiddellijk en blijvend de taal van de interface zelf "
        "- niet de vertaaltalen in het formulier. De keuze wordt meteen "
        "opgeslagen."
    ),
    "menu.help.whats_this": "Wat is dit?",
}


FI = {
    "app.title": "Document Translator",
    "mode.pdf": "Käännä PDF",
    "mode.presentation": "Käännä esitys (PowerPoint/Impress)",
    "mode.word": "Käännä Word/Writer-asiakirja",
    "mode.images": "Käännä yksittäiset kuvat",
    "source.none": "Ei tiedostoa valittuna",
    "source.choose": "Valitse tiedosto …",
    "image.none": "Älä käännä upotettuja kuvia",
    "image.selected": "Valitse kuvat yksitellen myöhemmin",
    "image.all": "Käännä kaikki upotetut kuvat",
    "field.mode": "Toiminto",
    "field.source": "Lähde",
    "field.images": "Asiakirjan kuvat",
    "field.provider": "Käännöspalvelu",
    "field.source_language": "Lähdekieli",
    "field.target_language": "Kohdekieli",
    "field.protected_terms": "Suojatut termit",
    "field.ico_mode": "ICO-asiakirja",
    "ico_mode.checkbox": "Ohita sivun 1 alue",
    "ico_mode.tooltip": "Vain sisäiselle ICO-asiakirjatyypille: jättää sivun 1 metadata-alueen kääntämättä (Wordissa: erottimen edellä oleva alue; PDF:ssä: tunnistetaan ankkuritermeistä, kuten \"Issuer Address\"/\"Asset Matrix\") - riippumatta siitä, löytyykö tämä alue todellisuudessa. Jätä pois käytöstä kaikissa muissa asiakirjoissa.",
    "field.side_by_side": "Rinnakkaisnäkymä",
    "side_by_side.checkbox": "Alkuperäinen ja käännös rinnakkain",
    "side_by_side.tooltip": "Vain Word: muodostaa leipätekstin normaalin, ulkoasun säilyttävän tuloksen sijaan kaksipalstaisena vertailutaulukkona (Alkuperäinen | Käännös) vaakasuuntaisena. Ylä- ja alatunniste pysyvät muuttumattomina. Leipätekstin upotetut taulukot (jos niitä on) eivät näy tässä näkymässä.",
    "field.exclude_header": "Ylätunniste",
    "exclude_header.checkbox": "Älä käännä toistuvaa ylätunnistetta",
    "exclude_header.tooltip": "Tunnistaa automaattisesti tekstin, joka toistuu identtisenä (tai vain sivunumeroltaan poikkeavana) useimpien sivujen yläosassa, ja jättää sen kääntämättä. Jos vastaavaa ei löydy, mikään ei muutu.",
    "field.exclude_footer": "Alatunniste",
    "exclude_footer.checkbox": "Älä käännä toistuvaa alatunnistetta",
    "exclude_footer.tooltip": "Sama kuin ylätunnisteessa, mutta sivun alaosassa toistuvalle tekstille (esim. tekijänoikeusrivi, sivunumero).",
    "field.ocr_engine": "OCR-moottori",
    "ocr_engine.tesseract": "Tesseract (paikallinen)",
    "ocr_engine.tesseract.unavailable": "Tesseractia ei löytynyt tästä järjestelmästä. Asenna se (katso README.md) - ilman asennettua Tesseractia kuvien tekstiä ei voida tunnistaa.",
    "ocr_engine.google_vision": "Google Cloud Vision (pilvi, kappaleentunnistus)",
    "ocr_engine.google_vision.unavailable": "Google-API-avainta ei ole määritetty. Lisää se Asetuksissa (sama avain kuin Google Translatelle, katso README.md) tai valitse toinen OCR-moottori.",
    "ocr_engine.paddleocr": "PaddleOCR (paikallinen, kappaleentunnistus)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR ei ole asennettu (katso requirements-paddleocr.txt) tai valitse toinen OCR-moottori.",
    "ocr_engine.unavailable": "Tämä OCR-moottori ei ole käytettävissä tässä järjestelmässä.",
    "field.inpainting_backend": "Takaisinkirjoitusmenetelmä",
    "inpainting_backend.box_overlay": "Laatikkopeite (peitä alue)",
    "inpainting_backend.cv_inpainting": "Klassinen CPU-inpainting (rekonstruoi tausta)",
    "inpainting_backend.gpu_inpainting": "Tekoäly-inpainting paikallisesti (GPU, LaMa)",
    "inpainting_backend.unavailable": "Tälle menetelmälle ei löytynyt CUDA-yhteensopivaa näytönohjainta (katso requirements-gpu.txt) - valitse toinen takaisinkirjoitusmenetelmä.",
    "inpainting_backend.below_recommended_vram": "Vain {vram_gb:.0f} Gt näytönohjaimen muistia havaittu (suositus: vähintään {min_gb:.0f} Gt) - saattaa silti toimia, mutta ilman takuuta, erityisesti suurten kuvien tai monien tekstikohtien yhteydessä.",
    "source_language.placeholder": "valinnainen / automaattinen",
    "protected.placeholder": "Yksi suojattu termi per rivi",
    "protected.load_file": "Lataa tiedostosta …",
    "protected.load_file.tooltip": "Tuo termejä CSV- tai tekstitiedostosta (yksi termi per rivi; CSV:ssä käytetään ensimmäistä saraketta). Nykyiset merkinnät säilyvät, kaksoiskappaleet ohitetaan.",
    "protected.loaded": "{added} uutta termiä tuotu tiedostosta {name} ({total} tiedostossa).",
    "protected.load_error": "Tiedostoa {name} ei voitu lukea: {error}",
    "dialog.choose_protected_terms": "Valitse termiluettelo",
    "dialog.all_files": "Kaikki tiedostot",
    "merge_box.group": "Yhdistä tiedostoja",
    "config.group": "Määritä tehtävä",
    "analysis.group": "Analyysi ja kustannusten hallinta",
    "analysis.required": "Analyysi vaaditaan ennen aloitusta.",
    "analysis.button": "Analysoi asiakirja ja arvioi kustannukset",
    "analysis.running": "Analyysi käynnissä …",
    "analysis.checked": "Olen tarkistanut analyysin ja kustannusarvion",
    "analysis.failed": "Analyysi epäonnistui.",
    "analysis.no_warnings": "Ei analyysivaroituksia.",
    "analysis.within": "rajoissa",
    "analysis.exceeded": "YLITETTY",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} tekstimerkkiä · {images}<br>Paikallinen arvio ({provider}): kuukausikäyttö {usage:,} / ilmainen kiintiö {free:,} merkkiä · arvio ${cost:.2f}<br>Ajoraja {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Reaaliaikainen kiintiö (DeepL, juuri tarkistettu):</b> {used:,}/{limit:,} merkkiä käytetty, {remaining:,} jäljellä.",
    "analysis.live_quota_unlimited": "<b>Reaaliaikainen kiintiö (DeepL, juuri tarkistettu):</b> {used:,} merkkiä käytetty, tili ei ilmoita rajaa.",
    "unit.pages": "sivua",
    "unit.slides": "diaa",
    "unit.paragraphs": "kappaletta",
    "unit.images": "kuvaa",
    "warning.scan_pdf": "Kuva-/skannattu PDF tunnistettu: OCR vaaditaan asiakirjan tekstille.",
    "warning.image_cost_unknown": "OCR-merkkien ja kuvien käännöskustannukset selviävät vasta OCR:n jälkeen.",
    "warning.image_selection_later": "Yksittäisten kuvien valinta lisätään analyysin jälkeen myöhemmässä käyttöliittymän kehitysvaiheessa.",
    "warning.embedded_images_not_estimated": "Kuvateksti ei sisälly arvioon: upotettuja kuvia ei vielä käännetä asiakirjan käsittelyn yhteydessä.",
    "analysis.images.files": "{images} kuvatiedostoa",
    "analysis.images.excluded": "{images} upotettua kuvaa (jätetty pois, ei laskettu mukaan)",
    "analysis.images.included": "{selected}/{images} upotetusta kuvasta valittu käännettäväksi",
    "warning.live_quota_unavailable": "DeepLin reaaliaikaista kiintiötä ei juuri nyt saada haettua (avain puuttuu, ei yhteyttä, tai API-virhe) - käytetään paikallista arviota.",
    "start.button": "Aloita käännös",
    "start.pending": "Tälle tilalle käynnistystä ei ole vielä toteutettu (katso RoadMap.md).",
    "start.ready": "Valmis aloitettavaksi.",
    "start.blocked_running": "Ajo on jo käynnissä.",
    "start.blocked_mode": "Tälle tilalle käynnistystä ei ole vielä toteutettu (katso RoadMap.md) - vain ”Käännä esitys” on toistaiseksi kytketty.",
    "start.blocked_no_analysis": "Suorita ensin ”Analysoi asiakirja ja arvioi kustannukset”.",
    "start.blocked_not_confirmed": "Valitse valintaruutu ”Olen tarkistanut analyysin ja kustannusarvion”.",
    "dialog.choose_output_dir": "Valitse kohdekansio",
    "dialog.confirm_run": "Aloita käännös",
    "start.confirm_summary": "Palveluun {provider} lähetetään arviolta {characters:,} merkkiä (arvioidut kustannukset ${cost:.2f}).\nKohdetiedosto: {destination}\n\nAloitetaanko nyt?",
    "start.confirm_summary_images": "Palveluun {provider} lähetetään arviolta {characters:,} merkkiä (arvioidut kustannukset ${cost:.2f}) {count} kuvalle.\nKohdekansio: {folder}\n\nAloitetaanko nyt?",
    "job.group": "Ajo ja tulos",
    "job.idle": "Ajoa ei ole vielä käynnistetty.",
    "job.running": "Käännös käynnissä …",
    "job.progress_prefix": "Käsitellään: {location}",
    "job.progress_count": "{processed}/{total} kappaletta käsitelty",
    "job.progress_count_files": "{processed}/{total} kuvaa käsitelty",
    "job.stats_summary": "{translated} käännetty · {skipped} ohitettu · {failed} epäonnistui · {chars:,} merkkiä lähetetty",
    "job.cancel": "Peruuta",
    "job.cancel_requested": "Peruutus pyydetty – pysäytetään käynnissä olevan API-kutsun jälkeen …",
    "job.result_summary": "Valmis: {translated} käännetty, {skipped} ohitettu, {failed} epäonnistui, {chars:,} merkkiä lähetetty.\nTulostiedosto: {output}\nQA-raportti: {report}",
    "job.result_summary_images": "Valmis: {files} kuvaa käsitelty, {translated} tekstialuetta käännetty, {failed} epäonnistui, {chars:,} merkkiä lähetetty.\nTuloskansio: {output_dir}\nJokaisella kuvalla on oma QA-raporttitiedosto tuloskansiossa.",
    "job.result_cancelled_suffix": "\nHuomio: ajo peruutettiin – tämä on osittainen tulos, jo käännetty sisältö on tallennettu.",
    "job.overflow_none": "Uusia ylivuotoriskejä ei löytynyt.",
    "job.overflow_count": "{count} ylivuotohuomautus(ta) QA-raportissa – tarkista manuaalisesti PowerPointissa/Impressissä.",
    "job.pdf_overflow_none": "Yhdenkään lohkon ei tarvinnut kasvaa tai kutistua lisäyksen yhteydessä.",
    "job.pdf_overflow_count": "{count} lohkon täytyi kasvaa tai kutistua sopiakseen – tarkista PDF pistokokein.",
    "job.open_folder": "Avaa kansio",
    "job.open_report": "Avaa QA-raportti",
    "job.open_folder_failed": "Kansiota ei voitu avata.",
    "job.show_report": "Näytä QA-raportti",
    "job.hide_report": "Piilota QA-raportti",
    "job.report_load_error": "QA-raporttia ei voitu ladata.",
    "job.correct_translation": "Korjaa käännös",
    "job.correction_starting": "Korjaus käynnistyy …",
    "job.correction_opened": "Korjausikkuna avattu - muokkaa siellä ja napsauta sitten ”Käytä” tai ”Peruuta”.",
    "job.correction_applied": "Korjaus otettu käyttöön.",
    "job.correction_cancelled": "Korjaus peruutettu.",
    "job.correction_timeout": "Korjaus aikakatkaistiin - korjausikkunasta ei saatu vastausta.",
    "job.correction_failed": "Korjaus epäonnistui: {error}",
    "job.correction_error": "Korjausta ei voitu käynnistää.",
    "job.failed_title": "Käännös epäonnistui",
    "correction.title": "Korjaa PDF-käännös",
    "correction.hint": "Valitse alta rivi ja muokkaa sen käännöstä alapuolella olevassa editorissa. Käytä lihavointia/kursiivia/alleviivausta (tai Ctrl+B/Ctrl+I/Ctrl+U) muotoilun mukauttamiseen – myös muokatut rivit säilyttävät muotoilunsa.",
    "correction.column_page": "Sivu",
    "correction.column_original": "Alkuperäinen",
    "correction.column_translation": "Käännös",
    "correction.editor_label": "Muokkaa käännöstä:",
    "correction.bold": "Lihavoitu",
    "correction.italic": "Kursivoitu",
    "correction.underline": "Alleviivattu",
    "correction.bold_tooltip": "Lihavoitu (Ctrl+B)",
    "correction.italic_tooltip": "Kursivoitu (Ctrl+I)",
    "correction.underline_tooltip": "Alleviivattu (Ctrl+U)",
    "correction.apply": "Käytä ja tallenna",
    "correction.close": "Sulje",
    "correction.applying": "Käytetään …",
    "correction.success": "{count} lohko(a) päivitetty ja tallennettu kohteeseen {output}.",
    "correction.failed": "Korjaus epäonnistui: {error}",
    "image_correction.title": "Korjaa kuvan käännös",
    "image_correction.hint": "Valitse alta rivi ja muokkaa sen käännöstä alapuolella olevassa editorissa.",
    "image_correction.canvas_hint": "Voit siirtää rivin laatikkoa vasemmalla olevassa kuvassa vetämällä. Valitse rivi ja vedä sen oikeasta alakulmasta muuttaaksesi kokoa. Käytä Ctrl+hiiren rullaa tai zoomauspainikkeita lähentääksesi/loitontaaksesi; ikkunan voi myös suurentaa koko näytölle.",
    "image_correction.reset_geometry": "Palauta sijainti/koko",
    "image_correction.zoom_in": "Lähennä (+)",
    "image_correction.zoom_out": "Loitonna (−)",
    "image_correction.zoom_reset": "Sovita näkymään",
    "image_correction.add_region": "Lisää uusi laatikko",
    "image_correction.add_region_hint": "Vedä kuvaan alue lisätäksesi sinne uuden laatikon omalla tekstillä.",
    "image_correction.show_original": "Näytä alkuperäinen",
    "image_correction.manual_region_label": "(lisätty manuaalisesti, ei OCR-osumaa)",
    "image_correction.manual_region_added": "Uusi laatikko lisätty - syötä sen käännös editoriin.",
    "image_correction.column_original": "Alkuperäinen",
    "image_correction.column_translation": "Käännös",
    "image_correction.editor_label": "Muokkaa käännöstä:",
    "image_correction.font_size_label": "Fonttikoko:",
    "image_correction.font_size_auto": "Automaattinen",
    "image_correction.bold": "Lihavoitu",
    "image_correction.centered": "Keskitetty",
    "image_correction.apply": "Käytä ja tallenna",
    "image_correction.close": "Sulje",
    "image_correction.applying": "Käytetään …",
    "image_correction.success": "{count} alue(tta) päivitetty ja tallennettu kohteeseen {output}.",
    "image_correction.failed": "Korjaus epäonnistui: {error}",
    "image_correction.choose_file_title": "Valitse korjattava tiedosto",
    "image_correction.choose_file_label": "Mikä tämän ajon tiedosto korjataan?",
    "update.available": "Päivitys saatavilla: {version}",
    "update.confirm_title": "Asennetaanko päivitys?",
    "update.confirm_body": "Uusi versio ({version}) on saatavilla. Ladataanko ja asennetaanko se nyt?",
    "update.installing": "Päivitystä asennetaan …",
    "update.success_title": "Päivitys asennettu",
    "update.success_body": "Päivitys on asennettu. Käynnistä sovellus uudelleen, jotta muutokset tulevat voimaan.",
    "update.failed_title": "Päivitys epäonnistui",
    "update.failed_body": "Päivitystä ei voitu asentaa: {error}\n\nAiemmin asennettu versio jatkaa toimintaansa muuttumattomana.",
    "menu.help": "Ohje",
    "menu.help.hw_check": "Näytä/toista laitteistotesti …",
    "menu.help.check_updates": "Tarkista päivitykset …",
    "menu.help.about": "Tietoja …",
    "about.body": "<h3>{app_name}</h3><p>Versio {version}</p><p>Kääntää PDF-, Word- ja PowerPoint-asiakirjoja sekä kuvia säilyttäen asettelun.</p><p>© {year} {author}<br>Lisenssi: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Lähdekoodi: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Käyttöohje …",
    "manual.hint_link": "Lisätietoja käyttöohjeessa (luku 4)",
    "manual.missing": "Käyttöohjetta ei löytynyt:\n{path}",
    "update.check.no_update_title": "Ei saatavilla olevia päivityksiä",
    "update.check.no_update_body": "Käytössäsi on jo uusin versio ({version}).",
    "update.check.failed_title": "Päivitysten tarkistus epäonnistui",
    "update.check.failed_body": "Päivityksiä ei voitu tarkistaa: {error}",
    "hw_check.title": "Laitteistotesti",
    "hw_check.note": "Jos sovellus ei toimi odotetusti (esim. paikallisessa tekoäly-inpaintingissa), voit tarkistaa laitteiston uudelleen täältä.",
    "hw_check.recheck_button": "Tarkista uudelleen",
    "hw_check.checking": "Tarkistetaan laitteistoa …",
    "hw_check.never_checked": "Laitteistotarkistusta ei ole vielä tehty. Napsauta ”Tarkista uudelleen” tehdäksesi sen nyt.",
    "hw_check.not_found": "CUDA-yhteensopivaa näytönohjainta ei löytynyt (viimeksi tarkistettu: {checked_at}). Paikallinen tekoäly-inpainting ei ole käytettävissä tällä laitteistolla - pilvipohjainen inpainting toimii tästä riippumatta.",
    "hw_check.found_ok": "{name} löydetty, näytönohjaimen muistia {vram_gb:.0f} Gt (viimeksi tarkistettu: {checked_at}). Täyttää suosituksen vähintään {min_gb:.0f} Gt.",
    "hw_check.found_below_recommended": "{name} löydetty, näytönohjaimen muistia {vram_gb:.0f} Gt (viimeksi tarkistettu: {checked_at}). Alle suosituksen {min_gb:.0f} Gt - saattaa silti toimia, mutta ilman takuuta, erityisesti suurten kuvien tai monien tekstikohtien yhteydessä.",
    "hw_check.driver_cuda_ok": "Ajuri tukee CUDA {cuda_version} -versiota - sopiva PyTorch-versio: {torch_variant}.",
    "hw_check.driver_cuda_too_old": "Ajuri tukee vain CUDA {cuda_version} -versiota - liian vanha paikalliseen tekoäly-inpaintingiin (vähintään 11.8 vaaditaan). Päivitä näytönohjaimen ajuri.",
    "settings.button": "Asetukset …",
    "settings.title": "Asetukset",
    "settings.language": "Käyttöliittymän kieli",
    "settings.prepared": "valmisteltu",
    "settings.provider": "Palveluntarjoaja",
    "settings.credentials": "Kirjautumistiedot",
    "settings.new_key": "Uusi API-avain",
    "settings.key_placeholder": "Ei koskaan näytetä eikä kirjata lokiin",
    "settings.storage": "Tallennuspaikka",
    "settings.environment": "Ympäristömuuttuja (vain tämä istunto)",
    "settings.keyring": "Käyttöjärjestelmän avainnippu",
    "settings.both": "Molemmat",
    "settings.run_limit": "Kustannusraja per ajo (merkkiä)",
    "settings.save_key": "Tallenna/korvaa API-avain",
    "settings.save_button": "Tallenna",
    "settings.open_log": "Avaa lokitiedosto …",
    "settings.session_note": "Huomio: ympäristömuuttuja ei säily pysyvästi tässä versiossa.",
    "settings.credentials_group": "API-käyttö",
    "settings.general_group": "Yleistä",
    "settings.env_override_warning": "Tämä palveluntarjoaja käyttää tällä hetkellä ympäristömuuttujan arvoa, ei tähän tallennettua avainnippumerkintää. Käytä tallennettua avainta poistamalla tämä ympäristömuuttuja käyttöjärjestelmätasolla.",

    "settings.provider.tooltip": "Palveluntarjoaja, jonka avainta hallitaan alla",
    "settings.provider.whatsthis": (
        "Valitsee, mihin käännöspalveluun (DeepL, Google, OpenAI, "
        "Grok) alla oleva tila, uusi avain ja tallennuspaikka "
        "kohdistuvat. Jokaisella palveluntarjoajalla on oma, erikseen "
        "tallennettu avain."
    ),
    "settings.status.tooltip": "Mistä nykyisin käytetty avain on peräisin",
    "settings.status.whatsthis": (
        "Näyttää, löytyikö valitulle palveluntarjoajalle avain "
        "käyttöjärjestelmän avainnipusta, ympäristömuuttujasta vai ei "
        "kummastakaan. Ympäristömuuttuja on aina ensisijainen "
        "avainnippuun nähden - katso varoitus alempaa, jos näin on "
        "tässä tapauksessa."
    ),
    "settings.secret.tooltip": "Uusi API-avain valitulle palveluntarjoajalle",
    "settings.secret.whatsthis": (
        "Liitä tähän palveluntarjoajalta saatu API-avain ja napsauta "
        "\"Tallenna\". Kirjoitettaessa se näkyy pisteinä, mutta ei "
        "tallennu automaattisesti - vasta Tallenna-painike kirjoittaa "
        "sen valittuun tallennuspaikkaan."
    ),
    "settings.target_field.tooltip": "Mihin uusi avain tallennetaan",
    "settings.target_field.whatsthis": (
        "\"Käyttöjärjestelmän avainnippu\" on suositeltu, pysyvä "
        "valinta. \"Ympäristömuuttuja\" pätee vain nykyiseen istuntoon "
        "ja on tarkoitettu lähinnä erikoistapauksiin/vianetsintään - "
        "katso huomautus alta. \"Molemmat\" kirjoittaa lisäksi myös "
        "tällaisen istuntomuuttujan."
    ),
    "settings.max_chars.tooltip": "Merkkien yläraja käännösajoa kohden",
    "settings.max_chars.whatsthis": (
        "Ajo, joka sisältää enemmän merkkejä kuin tähän on asetettu, "
        "pysäytetään ilmoituksella sen sijaan, että se aiheuttaisi "
        "odottamattoman suuria kustannuksia. Nosta arvoa tarvittaessa."
    ),
    "settings.save_key.tooltip": "Tallenna uusi avain",
    "settings.save_key.whatsthis": (
        "Kirjoittaa yllä syötetyn avaimen valitulle "
        "palveluntarjoajalle valittuun tallennuspaikkaan. Syöttökenttä "
        "tyhjenee sen jälkeen, ja yllä oleva tila päivittyy."
    ),
    "settings.open_log.tooltip": "Avaa sovelluksen lokitiedosto",
    "settings.open_log.whatsthis": (
        "Avaa nykyisen lokitiedoston järjestelmän oletusohjelmassa - "
        "hyödyllinen virheilmoitusten kopioimiseen vikailmoitukseen "
        "ilman kuvakaappausta."
    ),

    "hw_check.status.tooltip": "Viimeisimmän GPU-tarkistuksen tulos",
    "hw_check.status.whatsthis": (
        "Näyttää, löytyikö tuettu NVIDIA-näytönohjain, jossa on "
        "riittävästi VRAM-muistia, milloin tarkistus tehtiin viimeksi, "
        "ja tukeeko asennetun ajurin CUDA-versio paikallista "
        "GPU-inpaintingia. Ilman sopivaa näytönohjainta/ajuria "
        "paikallinen inpainting toimii silti - vain hitaammin, "
        "suorittimella (CPU)."
    ),
    "hw_check.recheck_button.tooltip": "Suorita GPU-tarkistus nyt uudelleen",
    "hw_check.recheck_button.whatsthis": (
        "Suorittaa saman tarkistuksen, jonka asennusohjelmakin teki - "
        "hyödyllinen ajuripäivityksen tai näytönohjaimen vaihdon "
        "jälkeen, ilman sovelluksen uudelleenasennusta."
    ),

    "bootstrap.help.back_button": (
        "Takaisin edelliseen vaiheeseen\n\n"
        "Tässä ja edellisessä vaiheessa jo syötetyt tiedot säilyvät."
    ),
    "bootstrap.help.next_button": "Jatka seuraavaan vaiheeseen",
    "bootstrap.help.cancel_button": (
        "Sulkee tämän ohjatun toiminnon\n\n"
        "Vahvistusta pyydetään, jos asennus on käynnissä. Asennuksen voi "
        "aloittaa uudelleen milloin tahansa."
    ),
    "bootstrap.help.language_combo": (
        "Tämän ohjatun toiminnon kieli\n\n"
        "Vaikuttaa heti kaikkiin tämän ohjatun toiminnon näyttöihin. "
        "Itse sovelluksella on myöhemmin oma, erillinen kielivalintansa."
    ),
    "bootstrap.help.mode_online_radio": (
        "Kääntäminen tapahtuu pilvipalveluntarjoajien kautta (DeepL, "
        "Google, OpenAI, Grok); kuvankäsittely käyttää täällä "
        "yksinkertaisempaa menetelmää tekoälypohjaisen inpaintingin "
        "sijaan\n\n"
        "Nopein ja yksinkertaisin asennus, toimii millä tahansa "
        "koneella. Vaatii oman API-avaimen valitulta palveluntarjoajalta "
        "ja internetyhteyden kääntämisen aikana."
    ),
    "bootstrap.help.mode_local_radio": (
        "Parempi, tekoälypohjainen kuvankäsittely tällä näytönohjaimella "
        "yksinkertaisemman oletusmenetelmän sijaan\n\n"
        "Vaatii tuetun NVIDIA-näytönohjaimen, jossa on riittävästi "
        "videomuistia (tarkistetaan seuraavassa vaiheessa) - sen sijaan "
        "kuvat eivät koskaan poistu tältä koneelta."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Jatka silti paikallista asennusta\n\n"
        "Hyödyllinen, jos tarkistus epäonnistui virheellisesti tai "
        "ajuripäivitys on vielä tekemättä - paikallinen käsittely "
        "voidaan tarkistaa uudelleen myöhemmin kohdasta Ohje -> "
        "Laitteistotesti."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Asenna sen sijaan verkkoversio\n\n"
        "Vaihtaa tämän asennuksen pilvipalveluntarjoajiin kysymättä "
        "näytönohjaimesta. Voidaan lisätä myöhemmin milloin tahansa "
        "sovelluksen asetuksista."
    ),
    "bootstrap.help.credentials_checkbox": (
        "Syötä API-avain palveluntarjoajalle {provider} seuraavassa "
        "vaiheessa\n\n"
        "Valitsemattomat palveluntarjoajat voi aina lisätä myöhemmin "
        "sovelluksen asetuksista."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Jatka syöttämättä yhtään avainta\n\n"
        "Avaimet voi aina lisätä myöhemmin sovelluksen asetuksista - "
        "ilman vähintään yhtä avainta kääntäminen ei kuitenkaan toimi."
    ),
    "bootstrap.help.credentials_continue_button": "Jatka avaimen syöttöön tai seuraavaan palveluntarjoajaan",
    "bootstrap.help.credential_open_signup_button": (
        "Avaa tämän palveluntarjoajan rekisteröitymissivun "
        "selaimessa\n\n"
        "Siellä luodaan API-avain, joka liitetään sitten tähän."
    ),
    "bootstrap.help.credential_key_entry": (
        "Liitä tämän palveluntarjoajan API-avain tähän\n\n"
        "Näkyy pisteinä kirjoitettaessa. Vasta alla oleva "
        "Tallenna-painike ottaa sen käyttöön."
    ),
    "bootstrap.help.credential_save_button": "Tallenna yllä syötetty avain nyt",
    "bootstrap.help.finish_close_button": "Sulje ohjattu toiminto käynnistämättä sovellusta nyt",
    "bootstrap.help.finish_launch_button": "Sulje ohjattu toiminto ja käynnistä sovellus heti",
    "credentials.title": "Kirjautumistiedot",
    "credentials.saved": "API-avain tallennettiin.",
    "credential.environment": "Ympäristömuuttuja (istunto)",
    "credential.keyring": "Käyttöjärjestelmän avainnippu",
    "credential.missing": "Ei määritetty",
    "provider.missing_key": "Palveluntarjoajalle ”{provider}” ei ole määritetty API-avainta. <a href=\"settings\">Määritä nyt</a>",
    "provider.missing_key_dialog": "Palveluntarjoajalle ”{provider}” ei ole määritetty API-avainta. Ilman avainta jokainen käännöskutsu epäonnistuu.",
    "dialog.check_input": "Tarkista syötteet",
    "dialog.analysis": "Analyysi",
    "dialog.choose_images": "Valitse kuvat",
    "dialog.choose_document": "Valitse asiakirja",
    "merge.button": "Yhdistä/lisää PDF-tiedostoja …",
    "merge.title": "Yhdistä/lisää PDF-tiedostoja",
    "merge.intro": "Kokoa lähdetiedostot haluttuun järjestykseen. Jokaiselle tiedostolle voi valinnaisesti määrittää sivuvalinnan (tyhjä = koko tiedosto) - lisää sama tiedosto useamman kerran eri sivuvalinnoilla lisätäksesi sen tiettyyn kohtaan toisen tiedoston sisällä.",
    "merge.column_file": "Tiedosto",
    "merge.column_pages": "Sivut",
    "merge.pages_placeholder": "kaikki",
    "merge.pages_tooltip": "Tyhjä = koko tiedosto. Muuten esim. \"1-3,5\" tai \"6-\" (sivusta 6 loppuun) tai \"-4\" (alusta sivuun 4). \"5-3\" lisää sivut 5,4,3 tässä (käänteisessä) järjestyksessä.",
    "merge.add_files": "Lisää tiedostoja …",
    "merge.remove_selected": "Poista",
    "merge.move_up": "Siirrä ylös",
    "merge.move_down": "Siirrä alas",
    "merge.sort_by_name": "Järjestä nimen mukaan",
    "merge.sort_by_date": "Järjestä päivämäärän mukaan",
    "merge.sort_by_date_tooltip": "Järjestää tiedoston viimeisimmän muokkauspäivämäärän mukaan levyllä (ei luontipäivämäärän).",
    "merge.output_file_label": "Kohdetiedosto",
    "merge.output_placeholder": "Valitse kohdetiedosto …",
    "merge.choose_output_file": "Tallenna nimellä …",
    "merge.start_button": "Aloita yhdistäminen",
    "merge.cancel_button": "Peruuta",
    "merge.close_button": "Sulje",
    "merge.status_running": "Käsitellään: {message}",
    "merge.status_done": "Valmis: kirjoitettu {pages} sivua {files} tiedostosta.",
    "merge.status_cancelled": "Peruutettu (osittainen tulos tallennettu): kirjoitettu {pages} sivua.",
    "merge.status_failed": "Epäonnistui: {error}",
    "merge.error_dialog_choose_files": "Valitse PDF-tiedostot",
    "merge.error_dialog_choose_output": "Valitse kohdetiedosto",
    "merge.failed_title": "Yhdistäminen epäonnistui",
    "merge_search.button": "Etsi kansiosta …",
    "merge_search.title": "Etsi PDF-tiedostoja kansiosta",
    "merge_search.folder_label": "Kansio",
    "merge_search.folder_placeholder": "Valitse kansio …",
    "merge_search.choose_folder": "Valitse kansio …",
    "merge_search.choose_folder_dialog_title": "Valitse etsittävä kansio",
    "merge_search.recursive_checkbox": "Sisällytä alikansiot",
    "merge_search.scope_ico_format": "ICO-muoto (sivun 1 ylätunnistealue)",
    "merge_search.scope_header": "Ylätunniste (kaikki sivut)",
    "merge_search.scope_full_text": "Koko teksti",
    "merge_search.scope_ico_format_tooltip": "Etsii VAIN sivun 1 ICO-metadatalohkosta (Developer, QSI ICO, myöntämispäivä, ...). Riippumaton alla olevasta ”Ylätunniste”-valinnasta - jos vain tämä valinta on valittuna, MUIDEN sivujen toistuvaa ylätunnistealuetta EI etsitä.",
    "merge_search.scope_header_tooltip": "Etsii VAIN jokaisella sivulla toistuvasta yläosan alueesta (esim. yrityksen nimi-/logorivi). Riippumaton yllä olevasta ”ICO-muoto”-valinnasta - erillinen, itsenäinen tekstialue, ei sen laajennus.",
    "merge_search.scope_full_text_tooltip": "Etsii KOKO tekstin kaikilta sivuilta, mukaan lukien yllä olevien ”ICO-muoto”- ja ”Ylätunniste”-valintojen alueet.",
    "merge_search.error_missing_scope": "Valitse vähintään yksi hakualue.",
    "merge_search.date_filter_group": "Suodata päivämäärän mukaan",
    "merge_search.date_source_file": "Tiedoston päivämäärä",
    "merge_search.date_source_document": "Asiakirjan päivämäärä",
    "merge_search.date_region_ico_format": "ICO-kenttä (sivu 1)",
    "merge_search.date_region_header": "Ylätunniste (kaikki sivut)",
    "merge_search.date_region_footer": "Alatunniste (kaikki sivut)",
    "merge_search.date_format_iso": "ISO (VVVV-KK-PP)",
    "merge_search.date_format_iso_tooltip": "Tunnistaa esim. ”2026-09-04”.",
    "merge_search.date_format_de": "Saksa (PP.KK.VVVV)",
    "merge_search.date_format_de_tooltip": "Tunnistaa esim. ”04.09.2026” (myös kaksinumeroiset vuodet kuten ”04.09.26”).",
    "merge_search.date_format_en_month": "Englanti (kuukauden nimi, esim. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Tunnistaa sekä muodon ”September 4, 2026” että ”4 September 2026” (pilkku valinnainen, päivä yksi- tai kaksinumeroinen).",
    "merge_search.date_format_slash": "Kauttaviiva (PP/KK/VVVV)",
    "merge_search.date_format_slash_tooltip": "Tunnistaa esim. ”04/09/2026”.",
    "merge_search.date_exact_checkbox": "Tarkka päivämäärä",
    "merge_search.date_from_label": "Alkaen",
    "merge_search.date_to_label": "Asti",
    "merge_search.date_exact_label": "Päivämäärä",
    "merge_search.error_date_range_reversed": "”Alkaen” ei saa olla myöhempi kuin ”Asti”.",
    "merge_search.error_missing_date_region": "Valitse vähintään yksi alue päivämäärähakua varten.",
    "merge_search.error_missing_date_format": "Valitse vähintään yksi päivämäärämuoto tai anna oma muoto.",
    "merge_search.date_custom_format_label": "Oma muoto",
    "merge_search.date_custom_format_placeholder": "esim. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Oma päivämäärämuoto näillä paikkamerkeillä (kirjoita aina englanniksi, myös tässä suomenkielisessä valintaikkunassa) - kaikki muut merkit, kuten välilyönnit, pilkut, pisteet tai kauttaviivat, haetaan sellaisenaan:\n\nYYYY – vuosi, 4-numeroinen, esim. 2026\nYY – vuosi, 2-numeroinen, esim. 26\nMMMM – kuukauden nimi, esim. September\nMMM – kuukauden nimi lyhennettynä, esim. Sep\nMM – kuukausi, 2-numeroinen, esim. 09\nM – kuukausi, 1- tai 2-numeroinen, esim. 9\nDD – päivä, 2-numeroinen, esim. 04\nD – päivä, 1- tai 2-numeroinen, esim. 4\n\nEsimerkkejä:\n”MMMM D, YYYY” löytää ”September 4, 2026”\n”MMMM DD, YYYY” löytää ”September 04, 2026”\n”YYYY/MM/DD” löytää ”2026/09/04”",
    "merge_search.error_invalid_custom_date_format": "Oma päivämäärämuoto on virheellinen - käytä työkaluvihjeessä näkyviä paikkamerkkejä.",
    "merge_search.query_label": "Hakuteksti (yhdistä termejä sanoilla AND/OR tai merkeillä &&/||)",
    "merge_search.query_placeholder": "esim. kehittäjän yrityksen nimi, tai termi1 AND termi2 – jätä tyhjäksi, jos haluat kaikki kansion tiedostot",
    "merge_search.query_tooltip": "Useita hakutermejä voi yhdistää sanoilla AND ja OR - myös sekaisin. Sulkeilla voit määrittää, mitkä kuuluvat yhteen.\n\nEsimerkki: ”Acme AND sopimus” löytää vain tiedostot, jotka sisältävät MOLEMMAT termit.\n”Acme OR Zenith” löytää tiedostot, joissa on VÄHINTÄÄN YKSI näistä kahdesta termistä.\n\nSekaisin sulkeiden kanssa: ”StellarRussia OR (The AND Korolev AND Directive)” löytää tiedostot, jotka sisältävät ”StellarRussia”-termin OR tiedostot, jotka sisältävät KAIKKI KOLME termiä ”The”, ”Korolev” ja ”Directive”.\n\nAND/OR-sanojen sijaan voi käyttää myös merkkejä && ja || (samamerkityksisiä, myös sekaisin sanojen kanssa): ”Acme && sopimus” on sama kuin ”Acme AND sopimus”.\n\nIlman AND/OR-sanoja koko teksti käsitellään yhtenä hakutermina (kuten ennenkin). Kirjainkoolla ei ole väliä.",
    "merge_search.search_button": "Hae",
    "merge_search.cancel_button": "Peruuta",
    "merge_search.select_all": "Valitse kaikki",
    "merge_search.select_none": "Poista kaikki valinnat",
    "merge_search.detach_results_button": "Avaa tulokset omassa ikkunassa",
    "merge_search.reattach_results_button": "Telakoi tulokset takaisin",
    "merge_search.results_detached_placeholder": "Tulosluettelo on avattu omassa ikkunassa.",
    "merge_search.detached_results_title_suffix": "Tulokset",
    "merge_search.take_selected": "Lisää valitut",
    "merge_search.close_button": "Sulje",
    "merge_search.status_running": "Etsitään: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} osumaa {scanned} tutkitusta PDF-tiedostosta.",
    "merge_search.status_done_with_errors": "{matches} osumaa {scanned} tutkitusta PDF-tiedostosta ({errors} ei luettavissa).",
    "merge_search.status_cancelled": "Peruutettu: {matches} osumaa {scanned} tutkitusta PDF-tiedostosta.",
    "merge_search.status_failed": "Epäonnistui: {error}",
    "merge_search.error_missing_folder": "Valitse ensin kansio.",
    "merge_search.failed_title": "Haku epäonnistui",
    "merge_search.source_local": "Paikallinen kansio",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Driven kansiolinkki tai -tunnus",
    "merge_search.drive_folder_placeholder": "Liitä jakolinkki tai kansiotunnus …",
    "merge_search.drive_resolve_button": "Tarkista",
    "merge_search.drive_folder_unresolved": "Ei vielä tarkistettu.",
    "merge_search.drive_folder_resolved": "Kansio ”{name}” löydetty.",
    "merge_search.drive_folder_resolve_failed": "Epäonnistui: {error}",
    "merge_search.drive_cache_label": "Välimuistikansio (lataukset säilyvät täällä)",
    "merge_search.drive_choose_cache": "Valitse välimuistikansio …",
    "merge_search.drive_choose_cache_dialog_title": "Valitse kansio ladatuille osumille",
    "merge_search.drive_credentials_label": "Googlen OAuth-kirjautumistiedot (kertaluonteinen, katso docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Lataa JSON-tiedostosta …",
    "merge_search.drive_load_from_file_dialog_title": "Valitse Google Cloud Consolen client-secrets-JSON-tiedosto",
    "merge_search.drive_load_from_file_failed": "Tiedostoa ei voitu lukea: {error}",
    "merge_search.drive_client_id_placeholder": "Asiakastunnus",
    "merge_search.drive_client_secret_placeholder": "Asiakassalaisuus",
    "merge_search.drive_project_id_placeholder": "Projektitunnus",
    "merge_search.drive_save_credentials": "Tallenna kirjautumistiedot",
    "merge_search.drive_credentials_saved": "Kirjautumistiedot tallennettu.",
    "merge_search.drive_save_failed": "Tallennus epäonnistui: {error}",
    "merge_search.drive_not_configured": "Asiakastunnusta/-salaisuutta/projektitunnusta ei ole vielä tallennettu.",
    "merge_search.drive_configured_not_connected": "Määritetty, mutta ei vielä yhdistetty.",
    "merge_search.drive_connected": "Yhdistetty{account}.",
    "merge_search.drive_connect_button": "Yhdistä Googleen",
    "merge_search.drive_disconnect_button": "Katkaise yhteys",
    "merge_search.drive_connecting": "Avataan selain kirjautumista varten …",
    "merge_search.drive_connect_failed": "Yhteys epäonnistui: {error}",
    "merge_search.drive_error_missing_folder": "Anna ja tarkista ensin Drive-kansio.",
    "merge_search.drive_error_missing_cache": "Valitse ensin välimuistikansio.",
    "merge_search.drive_error_not_connected": "Yhdistä ensin Googleen.",
    "word_merge.button": "Yhdistä/lisää DOCX-tiedostoja …",
    "word_merge.title": "Yhdistä/lisää DOCX-tiedostoja",
    "word_merge.intro": "Kokoa lähdetiedostot haluttuun järjestykseen - aina kokonaisina tiedostoina (toisin kuin PDF, DOCX-tiedostomuodolla itsellään ei ole kiinteää sivumäärää). Lisää sama tiedosto useamman kerran lisätäksesi sen useaan kohtaan. Yli 100 tiedoston kohdalla yhdistäminen tapahtuu automaattisesti ryhmissä (katso tilarivi ajon jälkeen).",
    "word_merge.status_done": "Valmis: otettu {segments}/{files} tiedostosta{batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Peruutettu (osittainen tulos tallennettu): otettu {segments} tiedostoa{batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " {batches} ryhmässä",
    "word_merge.status_warning_suffix": ", {count} ohitettu (katso alla)",
    "word_merge.warnings_title": "Ohitetut tiedostot:",
    "word_merge.error_dialog_choose_files": "Valitse DOCX-tiedostot",
    "word_merge_search.title": "Etsi DOCX-tiedostoja kansiosta",
    "word_merge_search.status_done": "{matches} osumaa {scanned} tutkitusta DOCX-tiedostosta.",
    "word_merge_search.status_done_with_errors": "{matches} osumaa {scanned} tutkitusta DOCX-tiedostosta ({errors} ei luettavissa).",
    "word_merge_search.status_cancelled": "Peruutettu: {matches} osumaa {scanned} tutkitusta DOCX-tiedostosta.",
    "bootstrap.window_title": "Määritä Document Translator",
    "bootstrap.back_button": "Takaisin",
    "bootstrap.next_button": "Seuraava",
    "bootstrap.cancel_button": "Peruuta",
    "bootstrap.cancel_title": "Peruutetaanko asennus?",
    "bootstrap.cancel_confirm": (
        "Asennusohjattu toiminto suljetaan, vaikka Document Translatoria ei "
        "ole vielä otettu täysin käyttöön. Jo luodut tiedostot poistetaan "
        "automaattisesti. Jatketaanko?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "Asennus on parhaillaan käynnissä. Peruuttaminen poistaa "
        "automaattisesti jo luodut tiedostot - harvinaisissa tapauksissa "
        "juuri sillä hetkellä käytössä ollut tiedosto voi jäädä jäljelle. "
        "Peruutetaanko silti?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Järjestelmänvalvojan oikeudet",
    "bootstrap.elevated_warning_text": (
        "Document Translator käynnistettiin järjestelmänvalvojana.\n\n"
        "Tämä ei ole tarpeen, ja se johtaa siihen, ettei sovellus enää "
        "toimi myöhemmin normaalisti käynnistettynä (ilman "
        "järjestelmänvalvojan oikeuksia).\n\n"
        "Sulje tämä ikkuna ja käynnistä asennus uudelleen tavallisella "
        "kaksoisnapsautuksella (ei \"Suorita "
        "järjestelmänvalvojana\").\n\n"
        "Tämän viestin voi kopioida painamalla Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Poista Document Translator",
    "bootstrap.uninstall_confirm": (
        "Poistetaanko Document Translator, mukaan lukien kaikki "
        "paikallisesti tallennetut asetukset ja API-avaimet?"
    ),
    "bootstrap.uninstall_done": "Document Translator on poistettu.",
    "bootstrap.welcome_title": "Tervetuloa",
    "bootstrap.welcome_text": "Tämä ohjattu toiminto määrittää Document Translatorin tälle tietokoneelle - ilman komentoriviä. Se lataa tarvittavat komponentit ja lisää lopuksi merkinnän sovellusvalikkoon.",
    "bootstrap.language_label": "Kieli",
    "bootstrap.mode_title": "Verkossa vai paikallisesti?",
    "bootstrap.mode_intro": "Miten käännös tehdään? Tätä voi muuttaa myöhemmin milloin tahansa Asetuksista.",
    "bootstrap.mode_online_label": "Verkossa (pilvipalveluntarjoaja)",
    "bootstrap.mode_online_desc": "Käännös tehdään ulkoisen palveluntarjoajan kautta (DeepL, Google, OpenAI tai Grok). Tästä aiheutuu jatkuvia kustannuksia per käännös, ja tarvitset oman API-avaimen kyseiseltä palveluntarjoajalta - lisää tästä kohta. Kuvankäsittely upotetuissa kuvissa toimii myös täällä, mutta yksinkertaisemmalla menetelmällä tekoälypohjaisen inpaintingin sijaan. Ei vaadi suurta latausta. Suositellaan, jos käytössä ei ole tehokasta näytönohjainta.",
    "bootstrap.mode_local_label": "Paikallinen (tällä näytönohjaimella)",
    "bootstrap.mode_local_desc": "Parantaa vain kuvankäsittelyä: kuviin upotettu teksti tunnistetaan OCR:llä ja piirretään käännöksen jälkeen tekoälymallilla (LaMa) suoraan tällä näytönohjaimella takaisin kuvaan - lopputulos näyttää siistimmältä kuin ilman tätä valintaa käytettävissä oleva yksinkertaisempi menetelmä. Varsinainen tekstin kääntäminen tapahtuu molemmissa tiloissa ulkoisen palveluntarjoajan kautta (DeepL, Google, OpenAI tai Grok), kyseisen palveluntarjoajan tavanomaiseen kääntänkohtaiseen hintaan. Verkkopalveluntarjoajat voi silti ottaa käyttöön milloin tahansa Asetuksista, jos niin haluat. Vaatii riittävän tehokkaan NVIDIA-näytönohjaimen (tarkistetaan seuraavassa vaiheessa) ja lataa asennuksen aikana kertaluonteisesti noin 2-3 Gt.",
    "bootstrap.gpu_checking": "Tarkistetaan näytönohjainta …",
    "bootstrap.gpu_ok": "Löydetty: {name}, näytönohjaimen muistia {vram_gb:.0f} Gt - tämä riittää.",
    "bootstrap.gpu_insufficient": "Löydetty: {name}, näytönohjaimen muistia {vram_gb:.0f} Gt - suositus on vähintään {min_gb:.0f} Gt. Paikallinen tila on todennäköisesti hyvin hidas.",
    "bootstrap.gpu_not_found": "Tuettua NVIDIA-näytönohjainta ei löytynyt. Paikallinen tila ei ole tällä tietokoneella käytännössä käyttökelpoinen.",
    "bootstrap.gpu_driver_too_old": "Löydetty: {name}, mutta NVIDIA-ajuri on liian vanha (tukee vain CUDA {cuda_version} -versiota, vähintään 11.8 vaaditaan). Päivitä näytönohjaimen ajuri ja käynnistä tämä ohjattu toiminto uudelleen, tai valitse sen sijaan Verkossa.",
    "bootstrap.gpu_mac_unsupported": "Paikallista tilaa ei vielä tueta Macissa. Valitse sen sijaan Verkossa.",
    "bootstrap.gpu_continue_local_button": "Jatka silti paikallisesti",
    "bootstrap.gpu_switch_online_button": "Vaihda verkkoon",
    "bootstrap.install_title": "Asennetaan",
    "bootstrap.install_step_venv": "Luodaan työympäristöä …",
    "bootstrap.install_step_deps": "Asennetaan komponentteja ({name}) …",
    "bootstrap.install_step_source": "Ladataan ohjelmakoodia …",
    "bootstrap.install_step_shortcut": "Lisätään sovellusvalikkomerkintää …",
    "bootstrap.install_failed_title": "Asennus epäonnistui",
    "bootstrap.install_failed": "Epäonnistui: {error}",
    "bootstrap.credentials_title": "Määritä API-avaimet",
    "bootstrap.credentials_intro": "Mitkä palveluntarjoajat haluat ottaa käyttöön? Voit ohittaa tämän ja tehdä sen myöhemmin sovelluksen Asetuksista milloin tahansa.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Nopea itsepalvelurekisteröinti. Ilmainen kiintiö saatavilla, sen jälkeen maksullinen.",
    "bootstrap.credentials_explain_google": "Vaatii Google Cloud -projektin, jossa on tallennettu maksutapa - hieman monimutkaisempi määrittää kuin muut kolme palveluntarjoajaa.",
    "bootstrap.credentials_explain_openai": "Nopea itsepalvelurekisteröinti, maksullinen käytön mukaan.",
    "bootstrap.credentials_explain_grok": "Nopea itsepalvelurekisteröinti, maksullinen käytön mukaan.",
    "bootstrap.credentials_open_signup_button": "Hanki avain (avaa selaimen)",
    "bootstrap.open_browser_title": "Avataanko selain?",
    "bootstrap.open_browser_text": (
        "Seuraava linkki avataan oletusselaimessa:\n\n"
        "{url}\n\n"
        "Tarkista, että osoite on todella oikea, ennen kuin jatkat."
    ),
    "bootstrap.credentials_key_label": "API-avain palvelulle {provider}",
    "bootstrap.credentials_key_placeholder": "Liitä avain …",
    "bootstrap.credentials_save_button": "Tallenna",
    "bootstrap.credentials_saved": "Tallennettu.",
    "bootstrap.credentials_skip_all_button": "Myöhemmin, Asetuksista",
    "bootstrap.credentials_continue_button": "Seuraava",
    "bootstrap.finish_title": "Valmis",
    "bootstrap.finish_text": "Document Translator on määritetty ja löytyy sovellusvalikosta.",
    "bootstrap.finish_download_size": "Todellisuudessa ladattu: noin {size_gb:.1f} Gt.",
    "bootstrap.finish_launch_button": "Käynnistä nyt",
    "bootstrap.finish_close_button": "Sulje",
    "mode.tooltip": "Käännettävän asiakirjan tyyppi",
    "mode.whatsthis": (
        "Määrittää käytettävän käännöskulun: PDF, PowerPoint/Impress, "
        "Word/Writer tai yksittäiset kuvat. Valinnan mukaan alla näkyvät "
        "vain siihen liittyvät kentät, esim. OCR-asetukset vain "
        "\"Kuvat\"-tilassa."
    ),
    "source.tooltip": "Valitse käännettävä(t) tiedosto(t)",
    "source.whatsthis": (
        "Avaa tiedostonvalintaikkunan lähdetiedostolle (Kuvat-tilassa "
        "myös useita tiedostoja kerralla). Valittu tiedostonimi näkyy "
        "sen jälkeen vasemmalla."
    ),
    "source_label.tooltip": "Tällä hetkellä valittu lähdetiedosto",
    "source_label.whatsthis": (
        "Näyttää viimeksi kohdasta \"Valitse tiedosto …\" valitun "
        "tiedoston nimen. Jos siinä lukee vielä \"Ei tiedostoa "
        "valittu\", valitse ensin tiedosto ennen kuin kustannusanalyysi "
        "on mahdollinen."
    ),
    "image_mode.tooltip": "Asiakirjaan upotettujen kuvien käsittely",
    "image_mode.whatsthis": (
        "\"Älä käännä\" jättää upotetut kuvat ennalleen. \"Valitse "
        "yksitellen myöhemmin\" näyttää kustannusanalyysin jälkeen "
        "luettelon, josta valitaan tietyt kuvat. \"Käännä kaikki\" "
        "käsittelee automaattisesti jokaisen upotetun kuvan."
    ),
    "provider.tooltip": "Käännöspalvelu tälle ajolle",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI tai Grok - kullakin oma API-avain, jota "
        "hallitaan Asetuksissa. Jos valitulle palveluntarjoajalle ei ole "
        "määritetty avainta, sen alle ilmestyy heti huomautus linkillä "
        "Asetuksiin."
    ),
    "source_lang.tooltip": "Lähdekielen koodi, esim. EN",
    "source_lang.whatsthis": (
        "Kaksikirjaiminen ISO 639-1 -kielikoodi (esim. EN englannille, "
        "FR ranskalle). Täytyy vastata asiakirjan todellista kieltä, "
        "muuten käännöspalvelu antaa vääriä tai ei lainkaan tuloksia."
    ),
    "target_lang.tooltip": "Kohdekielen koodi, esim. DE",
    "target_lang.whatsthis": (
        "Kaksikirjaiminen ISO 639-1 -kielikoodi, jolle käännetään (esim. "
        "DE saksalle, ES espanjalle)."
    ),
    "protected.tooltip": "Termit, joiden ei tule kääntyä",
    "protected.whatsthis": (
        "Yksi termi per rivi, esim. yritys- tai tuotenimet. "
        "Käännöspalvelu jättää nämä termit koskemattomiksi. Vierestä "
        "löytyvällä painikkeella voi myös ladata luettelon tiedostosta."
    ),
    "ocr_engine_field.tooltip": "Tekstintunnistus (OCR) kuville",
    "ocr_engine_field.whatsthis": (
        "Näkyy vain \"Kuvat\"-tilassa. Tunnistaa tekstin kuvista ennen "
        "kuin se käännetään ja kirjoitetaan takaisin. Jos moottori ei "
        "ole käytettävissä tällä koneella, sen alle ilmestyy huomautus."
    ),
    "inpainting_backend_field.tooltip": (
        "Menetelmä käännetyn tekstin kirjoittamiseksi takaisin kuvaan"
    ),
    "inpainting_backend_field.whatsthis": (
        "Näkyy vain \"Kuvat\"-tilassa. \"Laatikkopeite\" ja "
        "\"CV-inpainting\" toimivat aina paikallisesti ilman erityistä "
        "laitteistoa. \"GPU-inpainting\" käyttää paikallista "
        "näytönohjainta (CUDA) parhaan tuloksen saamiseksi, ja se on "
        "käytettävissä vain, jos CUDA-tuella varustettu PyTorch on "
        "asennettu - muuten alle ilmestyy huomautus. Laitteiston tilan "
        "voi tarkistaa milloin tahansa kohdasta Ohje -> Laitteistotesti."
    ),
    "merge.tooltip": "Yhdistä useita PDF-tiedostoja",
    "merge.whatsthis": (
        "Avaa erillisen ikkunan useiden PDF-tiedostojen yhdistämiseksi "
        "yhdeksi. Riippumaton yllä olevasta lomakkeesta - tässä ei "
        "käännetä mitään."
    ),
    "word_merge.tooltip": "Yhdistä useita Word-tiedostoja",
    "word_merge.whatsthis": (
        "Avaa erillisen ikkunan useiden Word-tiedostojen yhdistämiseksi "
        "yhdeksi. Riippumaton yllä olevasta lomakkeesta - tässä ei "
        "käännetä mitään."
    ),
    "analysis.button.tooltip": "Arvioi tämän käännösajon kustannukset",
    "analysis.button.whatsthis": (
        "Laskee käännettävät merkit ja arvioi valitun palveluntarjoajan "
        "mukaan suuntaa-antavat kustannukset kääntämättä vielä mitään. "
        "Vasta tämän jälkeen vieressä olevan valintaruudun voi rastia ja "
        "\"Aloita\" vapautuu."
    ),
    "analysis.checked.tooltip": "Vahvista arvioidut kustannukset",
    "analysis.checked.whatsthis": (
        "Täytyy rastia, ennen kuin \"Aloita\" tulee klikattavaksi - "
        "tarkoituksellinen varmistus, ettei ajoa koskaan käynnistetä "
        "vahingossa katsomatta ensin arvioituja kustannuksia."
    ),
    "start.tooltip": "Aloita käännösajo",
    "start.whatsthis": (
        "Aktivoituu vasta, kun kustannukset on analysoitu ja "
        "vahvistettu. Eteneminen näkyy alla olevalla alueella; käynnissä "
        "olevan ajon voi pysäyttää kohdasta \"Peruuta\"."
    ),
    "job.cancel.tooltip": "Peruuta käynnissä oleva käännösajo",
    "job.cancel.whatsthis": (
        "Pysäyttää nykyisen ajon mahdollisimman nopeasti. Jo käsitellyt "
        "osat eivät automaattisesti säily täydellisenä tiedostona - "
        "muodosta riippuen jäljelle voi jäädä keskeneräinen tiedosto."
    ),
    "job.open_folder.tooltip": "Avaa tulostekansio",
    "job.open_folder.whatsthis": (
        "Avaa tiedostoselaimen juuri valmistuneen ajon kohdekansiossa."
    ),
    "job.open_report.tooltip": "Avaa viimeisimmän ajon QA-raportti",
    "job.open_report.whatsthis": (
        "Näyttää viimeisimmän ajon automaattisen laadunvarmistuksen "
        "havainnot, esim. kohdat, jotka voi olla syytä tarkistaa."
    ),
    "job.correct_translation.tooltip": "Korjaa yksittäisiä käännöksiä",
    "job.correct_translation.whatsthis": (
        "Näkyy vain PDF-ajoissa, joissa on korjattavia tekstilohkoja. "
        "Mahdollistaa yksittäisten käännettyjen kohtien jälkikäsittelyn "
        "ilman koko ajon toistamista."
    ),
    "settings.button.tooltip": "Avaa asetukset",
    "settings.button.whatsthis": (
        "API-avaimet palveluntarjoajittain (suositus: avainnippu), "
        "merkkiraja ajoa kohden sekä pääsy lokitiedostoon."
    ),
    "update_hint.tooltip": "Uusi versio on saatavilla",
    "update_hint.whatsthis": (
        "Ilmestyy automaattisesti, kun käynnistyksen yhteydessä löytyy "
        "uudempi Document Translator -versio. Klikkaaminen tarjoaa uuden "
        "version asentamista."
    ),
    "flag_row.whatsthis": (
        "Vaihtaa heti ja pysyvästi käyttöliittymän oman kielen - ei "
        "lomakkeen käännöskieliä. Valinta tallentuu välittömästi."
    ),
    "menu.help.whats_this": "Mikä tämä on?",
}


HR = {
    "app.title": "Document Translator",
    "mode.pdf": "Prevedi PDF",
    "mode.presentation": "Prevedi prezentaciju (PowerPoint/Impress)",
    "mode.word": "Prevedi Word/Writer dokument",
    "mode.images": "Prevedi pojedinačne slike",
    "source.none": "Nije odabrana datoteka",
    "source.choose": "Odaberi datoteku …",
    "image.none": "Ne prevodi ugrađene slike",
    "image.selected": "Kasnije pojedinačno odaberi slike",
    "image.all": "Prevedi sve ugrađene slike",
    "field.mode": "Zadatak",
    "field.source": "Izvor",
    "field.images": "Slike u dokumentu",
    "field.provider": "Pružatelj usluge prevođenja",
    "field.source_language": "Izvorni jezik",
    "field.target_language": "Ciljni jezik",
    "field.protected_terms": "Zaštićeni pojmovi",
    "field.ico_mode": "ICO dokument",
    "ico_mode.checkbox": "Preskoči područje na 1. stranici",
    "ico_mode.tooltip": "Samo za interni tip dokumenta ICO: isključuje blok metapodataka na 1. stranici iz prijevoda (kod Worda: blok prije razdjelne crte; kod PDF-a: prepoznaje se prema sidrenim pojmovima poput \"Issuer Address\"/\"Asset Matrix\") - bez obzira na to je li taj blok stvarno pronađen. Za sve ostale dokumente ostavite isključeno.",
    "field.side_by_side": "Prikaz jedan pored drugog",
    "side_by_side.checkbox": "Original i prijevod jedan pored drugog",
    "side_by_side.tooltip": "Samo Word: glavni tekst se, umjesto uobičajenog rezultata vjernog izvornom rasporedu, izrađuje kao dvostupačna usporedna tablica (Original | Prijevod) u položenom (landscape) formatu. Zaglavlje i podnožje ostaju nepromijenjeni. Ugrađene tablice u glavnom tekstu (ako postoje) ne prikazuju se u ovom prikazu.",
    "field.exclude_header": "Zaglavlje",
    "exclude_header.checkbox": "Ne prevodi ponavljajuće zaglavlje",
    "exclude_header.tooltip": "Automatski prepoznaje tekst koji se identično (ili se razlikuje samo po broju stranice) ponavlja pri vrhu većine stranica i isključuje ga iz prijevoda. Ako se ništa odgovarajuće ne pronađe, ništa se ne mijenja.",
    "field.exclude_footer": "Podnožje",
    "exclude_footer.checkbox": "Ne prevodi ponavljajuće podnožje",
    "exclude_footer.tooltip": "Kao kod zaglavlja, samo za tekst koji se ponavlja pri dnu stranice (npr. redak s autorskim pravima, broj stranice).",
    "field.ocr_engine": "OCR alat",
    "ocr_engine.tesseract": "Tesseract (lokalno)",
    "ocr_engine.tesseract.unavailable": "Tesseract nije pronađen na ovom sustavu. Instalirajte ga (pogledajte README.md) - bez instaliranog Tesseracta tekst na slikama ne može se prepoznati.",
    "ocr_engine.google_vision": "Google Cloud Vision (cloud, prepoznavanje odlomaka)",
    "ocr_engine.google_vision.unavailable": "Nije konfiguriran Google API ključ. Unesite ga u postavkama (isti ključ kao za Google Translate, pogledajte README.md) ili odaberite drugi OCR alat.",
    "ocr_engine.paddleocr": "PaddleOCR (lokalno, prepoznavanje odlomaka)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR nije instaliran (pogledajte requirements-paddleocr.txt) ili odaberite drugi OCR alat.",
    "ocr_engine.unavailable": "Ovaj OCR alat nije dostupan na ovom sustavu.",
    "field.inpainting_backend": "Metoda prepisivanja",
    "inpainting_backend.box_overlay": "Preklapanje okvirom (prekrivanje površine)",
    "inpainting_backend.cv_inpainting": "Klasični CPU inpainting (rekonstrukcija pozadine)",
    "inpainting_backend.gpu_inpainting": "AI inpainting lokalno (GPU, LaMa)",
    "inpainting_backend.unavailable": "Za ovu metodu nije pronađen CUDA GPU (pogledajte requirements-gpu.txt) - odaberite drugu metodu prepisivanja.",
    "inpainting_backend.below_recommended_vram": "Otkriveno samo {vram_gb:.0f} GB video memorije (preporučeno: najmanje {min_gb:.0f} GB) - možda će raditi, no bez jamstva, pogotovo kod velikih slika ili više tekstualnih mjesta istovremeno.",
    "source_language.placeholder": "neobavezno / automatski",
    "protected.placeholder": "Jedan zaštićeni pojam po retku",
    "protected.load_file": "Učitaj iz datoteke …",
    "protected.load_file.tooltip": "Učitajte pojmove iz CSV ili tekstualne datoteke (jedan pojam po retku; kod CSV-a koristi se prvi stupac). Postojeći unosi ostaju sačuvani, duplikati se preskaču.",
    "protected.loaded": "{added} novih pojmova učitano iz {name} (ukupno {total} u datoteci).",
    "protected.load_error": "{name} nije moguće pročitati: {error}",
    "dialog.choose_protected_terms": "Odaberi popis pojmova",
    "dialog.all_files": "Sve datoteke",
    "merge_box.group": "Spajanje datoteka",
    "config.group": "Konfiguracija zadatka",
    "analysis.group": "Analiza i kontrola troškova",
    "analysis.required": "Prije pokretanja potrebna je analiza.",
    "analysis.button": "Analiziraj dokument i procijeni troškove",
    "analysis.running": "Analiza u tijeku …",
    "analysis.checked": "Analiza i procjena troškova pregledane",
    "analysis.failed": "Analiza nije uspjela.",
    "analysis.no_warnings": "Nema upozorenja iz analize.",
    "analysis.within": "unutar limita",
    "analysis.exceeded": "PREKORAČENO",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} znakova teksta · {images}<br>Lokalna procjena ({provider}): mjesečna potrošnja {usage:,} / besplatna kvota {free:,} znakova · procjena ${cost:.2f}<br>Limit po pokretanju {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Trenutna kvota (DeepL, upravo dohvaćeno):</b> iskorišteno {used:,} od {limit:,} znakova, preostalo {remaining:,}.",
    "analysis.live_quota_unlimited": "<b>Trenutna kvota (DeepL, upravo dohvaćeno):</b> iskorišteno {used:,} znakova, račun ne prijavljuje ograničenje.",
    "unit.pages": "stranica",
    "unit.slides": "slajdova",
    "unit.paragraphs": "odlomaka",
    "unit.images": "slika",
    "warning.scan_pdf": "Prepoznat je skenirani PDF sa slikama: za tekst dokumenta potreban je OCR.",
    "warning.image_cost_unknown": "Broj OCR znakova i trošak prijevoda slika bit će poznati tek nakon OCR-a.",
    "warning.image_selection_later": "Pojedinačni odabir slika bit će dostupan nakon analize u kasnijoj nadogradnji korisničkog sučelja.",
    "warning.embedded_images_not_estimated": "Tekst na slikama nije uključen u procjenu: ugrađene slike trenutno se još ne prevode tijekom obrade dokumenta.",
    "analysis.images.files": "{images} slikovnih datoteka",
    "analysis.images.excluded": "{images} ugrađenih slika (isključeno, ne obračunava se)",
    "analysis.images.included": "{selected} od {images} ugrađenih slika odabrano za prijevod",
    "warning.live_quota_unavailable": "Trenutna kvota kod DeepL-a trenutno nije dostupna (nema ključa, offline, ili API pogreška) - koristi se lokalna procjena.",
    "start.button": "Pokreni prijevod",
    "start.pending": "Pokretanje za ovaj način rada još nije povezano (pogledajte RoadMap.md).",
    "start.ready": "Spremno za pokretanje.",
    "start.blocked_running": "Postupak je već aktivan.",
    "start.blocked_mode": "Pokretanje za ovaj način rada još nije povezano (pogledajte RoadMap.md) - trenutno je povezano samo „Prevedi prezentaciju”.",
    "start.blocked_no_analysis": "Najprije pokrenite „Analiziraj dokument i procijeni troškove”.",
    "start.blocked_not_confirmed": "Označite kućicu „Analiza i procjena troškova pregledane”.",
    "dialog.choose_output_dir": "Odaberi ciljnu mapu",
    "dialog.confirm_run": "Pokreni prijevod",
    "start.confirm_summary": "Bit će poslano procijenjeno {characters:,} znakova pružatelju {provider} (procijenjeni trošak ${cost:.2f}).\nCiljna datoteka: {destination}\n\nPokrenuti sada?",
    "start.confirm_summary_images": "Bit će poslano procijenjeno {characters:,} znakova pružatelju {provider} (procijenjeni trošak ${cost:.2f}) za {count} slika(e).\nCiljna mapa: {folder}\n\nPokrenuti sada?",
    "job.group": "Pokretanje i rezultat",
    "job.idle": "Postupak još nije pokrenut.",
    "job.running": "Prijevod u tijeku …",
    "job.progress_prefix": "Obrada: {location}",
    "job.progress_count": "Obrađeno {processed} od {total} odlomaka",
    "job.progress_count_files": "Obrađeno {processed} od {total} slika",
    "job.stats_summary": "{translated} prevedeno · {skipped} preskočeno · {failed} neuspjelo · {chars:,} znakova poslano",
    "job.cancel": "Prekini",
    "job.cancel_requested": "Zatražen prekid – zaustavit će se nakon trenutnog API poziva …",
    "job.result_summary": "Gotovo: {translated} prevedeno, {skipped} preskočeno, {failed} neuspjelo, {chars:,} znakova poslano.\nIzlazna datoteka: {output}\nQA izvještaj: {report}",
    "job.result_summary_images": "Gotovo: obrađeno {files} slika, prevedeno {translated} tekstualnih regija, {failed} neuspjelo, {chars:,} znakova poslano.\nIzlazna mapa: {output_dir}\nZa svaku sliku u izlaznoj mapi nalazi se zasebna QA izvještajna datoteka.",
    "job.result_cancelled_suffix": "\nNapomena: postupak je prekinut – ovo je djelomičan rezultat, već prevedeni sadržaj je spremljen.",
    "job.overflow_none": "Nisu pronađeni novi rizici prelijevanja teksta.",
    "job.overflow_count": "{count} napomena o prelijevanju teksta u QA izvještaju – provjerite ručno u PowerPointu/Impressu.",
    "job.pdf_overflow_none": "Nijedan blok nije trebao rasti ili se smanjiti pri umetanju.",
    "job.pdf_overflow_count": "{count} blok/blokova moralo je rasti ili se smanjiti kako bi stalo – preporučamo provjeru na uzorku u PDF-u.",
    "job.open_folder": "Otvori mapu",
    "job.open_report": "Otvori QA izvještaj",
    "job.open_folder_failed": "Mapu nije bilo moguće otvoriti.",
    "job.show_report": "Prikaži QA izvještaj",
    "job.hide_report": "Sakrij QA izvještaj",
    "job.report_load_error": "QA izvještaj nije bilo moguće učitati.",
    "job.correct_translation": "Ispravi prijevod",
    "job.correction_starting": "Pokretanje ispravka …",
    "job.correction_opened": "Prozor za ispravak je otvoren - uredite tamo, a zatim kliknite „Primijeni” ili „Odustani”.",
    "job.correction_applied": "Ispravak primijenjen.",
    "job.correction_cancelled": "Ispravak otkazan.",
    "job.correction_timeout": "Isteklo je vrijeme za ispravak - nema odgovora iz prozora za ispravak.",
    "job.correction_failed": "Ispravak nije uspio: {error}",
    "job.correction_error": "Ispravak nije bilo moguće pokrenuti.",
    "job.failed_title": "Prijevod nije uspio",
    "correction.title": "Ispravak prijevoda PDF-a",
    "correction.hint": "Odaberite redak ispod i uredite njegov prijevod u uređivaču ispod tablice. Pomoću Podebljano/Kurziv/Podcrtano (ili Ctrl+B/Ctrl+I/Ctrl+U) možete prilagoditi oblikovanje – uređeni retci zadržavaju svoje oblikovanje.",
    "correction.column_page": "Stranica",
    "correction.column_original": "Original",
    "correction.column_translation": "Prijevod",
    "correction.editor_label": "Uredi prijevod:",
    "correction.bold": "Podebljano",
    "correction.italic": "Kurziv",
    "correction.underline": "Podcrtano",
    "correction.bold_tooltip": "Podebljano (Ctrl+B)",
    "correction.italic_tooltip": "Kurziv (Ctrl+I)",
    "correction.underline_tooltip": "Podcrtano (Ctrl+U)",
    "correction.apply": "Primijeni i spremi",
    "correction.close": "Zatvori",
    "correction.applying": "Primjenjuje se …",
    "correction.success": "{count} blok/blokova ažurirano i spremljeno u {output}.",
    "correction.failed": "Ispravak nije uspio: {error}",
    "image_correction.title": "Ispravak prijevoda slike",
    "image_correction.hint": "Odaberite redak ispod i uredite njegov prijevod u uređivaču ispod tablice.",
    "image_correction.canvas_hint": "Na slici lijevo možete povlačenjem pomaknuti okvir retka. Odaberite redak da biste povlačenjem njegovog donjeg desnog kuta promijenili veličinu. Pomoću Ctrl+kotačić miša ili gumba za zumiranje možete zumirati unutra i van; dijalog se također može maksimizirati.",
    "image_correction.reset_geometry": "Vrati poziciju/veličinu",
    "image_correction.zoom_in": "Povećaj (+)",
    "image_correction.zoom_out": "Smanji (−)",
    "image_correction.zoom_reset": "Prilagodi prikaz",
    "image_correction.add_region": "Dodaj novi okvir",
    "image_correction.add_region_hint": "Povucite područje na slici da biste tamo dodali novi okvir s vlastitim tekstom.",
    "image_correction.show_original": "Prikaži original",
    "image_correction.manual_region_label": "(ručno dodano, bez OCR prepoznavanja)",
    "image_correction.manual_region_added": "Novi okvir dodan - unesite prijevod u uređivaču.",
    "image_correction.column_original": "Original",
    "image_correction.column_translation": "Prijevod",
    "image_correction.editor_label": "Uredi prijevod:",
    "image_correction.font_size_label": "Veličina fonta:",
    "image_correction.font_size_auto": "Automatski",
    "image_correction.bold": "Podebljano",
    "image_correction.centered": "Centrirano",
    "image_correction.apply": "Primijeni i spremi",
    "image_correction.close": "Zatvori",
    "image_correction.applying": "Primjenjuje se …",
    "image_correction.success": "{count} regija/regije ažurirano i spremljeno u {output}.",
    "image_correction.failed": "Ispravak nije uspio: {error}",
    "image_correction.choose_file_title": "Odaberi datoteku za ispravak",
    "image_correction.choose_file_label": "Koju datoteku iz ovog postupka treba ispraviti?",
    "update.available": "Dostupna nadogradnja: {version}",
    "update.confirm_title": "Instalirati nadogradnju?",
    "update.confirm_body": "Dostupna je nova verzija ({version}). Preuzeti i instalirati sada?",
    "update.installing": "Instalacija nadogradnje …",
    "update.success_title": "Nadogradnja instalirana",
    "update.success_body": "Nadogradnja je instalirana. Ponovno pokrenite aplikaciju kako bi promjene stupile na snagu.",
    "update.failed_title": "Nadogradnja nije uspjela",
    "update.failed_body": "Nadogradnju nije bilo moguće instalirati: {error}\n\nPrethodno instalirana verzija nastavlja raditi nepromijenjeno.",
    "menu.help": "Pomoć",
    "menu.help.hw_check": "Prikaži/ponovi test hardvera …",
    "menu.help.check_updates": "Provjeri nadogradnje …",
    "menu.help.about": "O aplikaciji …",
    "about.body": "<h3>{app_name}</h3><p>Verzija {version}</p><p>Prevodi PDF, Word i PowerPoint dokumente te slike uz očuvanje izgleda.</p><p>© {year} {author}<br>Licenca: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Izvorni kod: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Korisnički priručnik …",
    "manual.hint_link": "Više u korisničkom priručniku (poglavlje 4)",
    "manual.missing": "Korisnički priručnik nije pronađen:\n{path}",
    "update.check.no_update_title": "Nema dostupne nadogradnje",
    "update.check.no_update_body": "Već koristite najnoviju verziju ({version}).",
    "update.check.failed_title": "Provjera nadogradnji nije uspjela",
    "update.check.failed_body": "Nije bilo moguće provjeriti nadogradnje: {error}",
    "hw_check.title": "Test hardvera",
    "hw_check.note": "Ako se aplikacija ne ponaša kako se očekuje (npr. kod lokalnog AI inpaintinga), ovdje možete ponovno provjeriti hardver.",
    "hw_check.recheck_button": "Provjeri ponovno",
    "hw_check.checking": "Provjera hardvera …",
    "hw_check.never_checked": "Još nema zabilježene provjere hardvera. Kliknite „Provjeri ponovno” za provjeru sada.",
    "hw_check.not_found": "Nije pronađen CUDA GPU (zadnja provjera: {checked_at}). Lokalni AI inpainting nije dostupan na ovom hardveru - Cloud inpainting radi neovisno o tome.",
    "hw_check.found_ok": "Pronađeno: {name} s {vram_gb:.0f} GB video memorije (zadnja provjera: {checked_at}). Zadovoljava preporuku od najmanje {min_gb:.0f} GB.",
    "hw_check.found_below_recommended": "Pronađeno: {name} s {vram_gb:.0f} GB video memorije (zadnja provjera: {checked_at}). Ispod je preporuke od {min_gb:.0f} GB - možda će raditi, no bez jamstva, pogotovo kod velikih slika ili više tekstualnih mjesta istovremeno.",
    "hw_check.driver_cuda_ok": "Upravljački program podržava CUDA {cuda_version} - odgovarajuća PyTorch inačica: {torch_variant}.",
    "hw_check.driver_cuda_too_old": "Upravljački program podržava samo CUDA {cuda_version} - prestar za lokalni AI inpainting (potrebno je najmanje 11.8). Ažurirajte upravljački program grafičke kartice.",
    "settings.button": "Postavke …",
    "settings.title": "Postavke",
    "settings.language": "Jezik sučelja",
    "settings.prepared": "pripremljeno",
    "settings.provider": "Pružatelj usluge",
    "settings.credentials": "Vjerodajnice",
    "settings.new_key": "Novi API ključ",
    "settings.key_placeholder": "Nikada se ne prikazuje niti bilježi",
    "settings.storage": "Mjesto pohrane",
    "settings.environment": "Varijabla okruženja (samo ova sesija)",
    "settings.keyring": "OS keyring",
    "settings.both": "Oboje",
    "settings.run_limit": "Ograničenje troška po pokretanju (znakova)",
    "settings.save_key": "Spremi/zamijeni API ključ",
    "settings.save_button": "Spremi",
    "settings.open_log": "Otvori log datoteku …",
    "settings.session_note": "Napomena: varijabla okruženja u ovoj verziji nije trajna.",
    "settings.credentials_group": "Pristup API-ju",
    "settings.general_group": "Općenito",
    "settings.env_override_warning": "Ovaj pružatelj trenutačno koristi vrijednost iz varijable okruženja, a ne ovdje spremljeni unos u keyringu. Da biste koristili spremljeni ključ, uklonite tu varijablu okruženja na razini operacijskog sustava.",

    "settings.provider.tooltip": "Pružatelj čiji se ključ upravlja ispod",
    "settings.provider.whatsthis": (
        "Određuje na kojeg se pružatelja usluge prevođenja (DeepL, "
        "Google, OpenAI, Grok) odnose status, novi ključ i mjesto "
        "pohrane ispod. Svaki pružatelj ima vlastiti, zasebno spremljeni "
        "ključ."
    ),
    "settings.status.tooltip": "Odakle dolazi trenutačno korišteni ključ",
    "settings.status.whatsthis": (
        "Prikazuje je li za odabranog pružatelja pronađen ključ u OS "
        "keyringu, u varijabli okruženja ili nijedan. Varijabla "
        "okruženja uvijek ima prednost pred keyringom - pogledajte "
        "upozorenje niže ako je to ovdje slučaj."
    ),
    "settings.secret.tooltip": "Novi API ključ za odabranog pružatelja",
    "settings.secret.whatsthis": (
        "Ovdje zalijepite API ključ dobiven od pružatelja i kliknite "
        "\"Spremi\". Tijekom upisivanja prikazuje se kao točke, ali se "
        "ne primjenjuje automatski - tek gumb Spremi zapisuje ga na "
        "odabrano mjesto pohrane."
    ),
    "settings.target_field.tooltip": "Gdje se novi ključ sprema",
    "settings.target_field.whatsthis": (
        "\"OS keyring\" je preporučeni, trajni izbor. \"Varijabla "
        "okruženja\" vrijedi samo za trenutačnu sesiju i uglavnom je "
        "namijenjena posebnim slučajevima/otklanjanju problema - "
        "pogledajte napomenu ispod. \"Oboje\" dodatno zapisuje i takvu "
        "varijablu sesije."
    ),
    "settings.max_chars.tooltip": "Gornja granica znakova po izvršavanju prijevoda",
    "settings.max_chars.whatsthis": (
        "Izvršavanje s više znakova nego što je ovdje postavljeno "
        "zaustavlja se s porukom umjesto da uzrokuje neočekivano "
        "visoke troškove. Po potrebi ovdje povećajte vrijednost."
    ),
    "settings.save_key.tooltip": "Spremi novi ključ",
    "settings.save_key.whatsthis": (
        "Zapisuje gore unesen ključ za odabranog pružatelja na "
        "odabrano mjesto pohrane. Polje za unos se nakon toga prazni, "
        "a status iznad se ažurira."
    ),
    "settings.open_log.tooltip": "Otvori datoteku zapisnika aplikacije",
    "settings.open_log.whatsthis": (
        "Otvara trenutačnu datoteku zapisnika u zadanom programu "
        "sustava - korisno za kopiranje poruka o pogrešci u prijavu "
        "greške bez izrade snimke zaslona."
    ),

    "hw_check.status.tooltip": "Rezultat posljednje GPU provjere",
    "hw_check.status.whatsthis": (
        "Prikazuje je li pronađena podržana NVIDIA GPU s dovoljno VRAM "
        "memorije, kada je posljednji put provjereno i podržava li CUDA "
        "verzija instaliranog upravljačkog programa lokalni GPU "
        "inpainting. Bez odgovarajuće GPU/upravljačkog programa, "
        "lokalni inpainting i dalje radi - samo sporije, na CPU-u."
    ),
    "hw_check.recheck_button.tooltip": "Ponovno pokreni GPU provjeru sada",
    "hw_check.recheck_button.whatsthis": (
        "Ponovno pokreće istu provjeru koju je izvršio i instalacijski "
        "program - korisno nakon ažuriranja upravljačkog programa ili "
        "zamjene grafičke kartice, bez potrebe za ponovnom instalacijom "
        "aplikacije."
    ),

    "bootstrap.help.back_button": (
        "Natrag na prethodni korak\n\n"
        "Ono što je već uneseno u ovom i prethodnom koraku ostaje "
        "sačuvano."
    ),
    "bootstrap.help.next_button": "Nastavi na sljedeći korak",
    "bootstrap.help.cancel_button": (
        "Zatvara ovog čarobnjaka\n\n"
        "Bit ćete zamoljeni za potvrdu ako je instalacija trenutačno u "
        "tijeku. Postavljanje se može ponovno pokrenuti u bilo kojem "
        "trenutku."
    ),
    "bootstrap.help.language_combo": (
        "Jezik ovog čarobnjaka\n\n"
        "Odmah se primjenjuje na sve zaslone ovog čarobnjaka. Sama "
        "aplikacija kasnije ima vlastiti, neovisni odabir jezika."
    ),
    "bootstrap.help.mode_online_radio": (
        "Prevođenje se odvija putem pružatelja u oblaku (DeepL, Google, "
        "OpenAI, Grok); obrada slika ovdje koristi jednostavniju metodu "
        "umjesto AI inpaintinga\n\n"
        "Najbrža i najjednostavnija instalacija, radi na bilo kojem "
        "računalu. Zahtijeva vlastiti API ključ odabranog pružatelja i "
        "internetsku vezu tijekom prevođenja."
    ),
    "bootstrap.help.mode_local_radio": (
        "Bolja, AI obrada slika na ovoj grafičkoj kartici umjesto "
        "jednostavnije zadane metode\n\n"
        "Zahtijeva podržanu NVIDIA grafičku karticu s dovoljno video "
        "memorije (provjerava se u sljedećem koraku) - zauzvrat slike "
        "nikada ne napuštaju ovo računalo."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Ipak nastavi s lokalnom instalacijom\n\n"
        "Korisno ako je provjera pogrešno neuspjela ili ažuriranje "
        "upravljačkog programa još nije obavljeno - lokalna obrada može "
        "se ponovno provjeriti kasnije putem Pomoć -> Test hardvera."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Umjesto toga instaliraj online varijantu\n\n"
        "Prebacuje ovu instalaciju na pružatelje u oblaku, bez pitanja "
        "o GPU-u. Može se dodati kasnije u bilo kojem trenutku putem "
        "postavki aplikacije."
    ),
    "bootstrap.help.credentials_checkbox": (
        "U sljedećem koraku unesite API ključ za {provider}\n\n"
        "Neoznačeni pružatelji uvijek se mogu dodati kasnije u "
        "postavkama aplikacije."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Nastavi bez unosa ijednog ključa\n\n"
        "Ključevi se uvijek mogu dodati kasnije u postavkama aplikacije "
        "- no bez barem jednog ključa prevođenje neće raditi."
    ),
    "bootstrap.help.credentials_continue_button": "Nastavi na unos ključa ili na sljedećeg pružatelja",
    "bootstrap.help.credential_open_signup_button": (
        "Otvara stranicu za registraciju ovog pružatelja u "
        "pregledniku\n\n"
        "Ondje se generira API ključ koji se zatim ovdje zalijepi."
    ),
    "bootstrap.help.credential_key_entry": (
        "Ovdje zalijepite API ključ ovog pružatelja\n\n"
        "Tijekom upisivanja prikazuje se kao točke. Tek gumb Spremi "
        "ispod ga stvarno primjenjuje."
    ),
    "bootstrap.help.credential_save_button": "Odmah spremi gore unesen ključ",
    "bootstrap.help.finish_close_button": "Zatvori čarobnjaka bez pokretanja aplikacije sada",
    "bootstrap.help.finish_launch_button": "Zatvori čarobnjaka i odmah pokreni aplikaciju",
    "credentials.title": "Vjerodajnice",
    "credentials.saved": "API ključ je spremljen.",
    "credential.environment": "Varijabla okruženja (sesija)",
    "credential.keyring": "OS keyring",
    "credential.missing": "Nije postavljeno",
    "provider.missing_key": "Nije unesen API ključ za „{provider}”. <a href=\"settings\">Postavi sada</a>",
    "provider.missing_key_dialog": "Za pružatelja „{provider}” nije unesen API ključ. Bez ključa će svaki poziv za prijevod biti neuspješan.",
    "dialog.check_input": "Provjeri unos",
    "dialog.analysis": "Analiza",
    "dialog.choose_images": "Odaberi slike",
    "dialog.choose_document": "Odaberi dokument",
    "merge.button": "Spoji/umetni PDF-ove …",
    "merge.title": "Spajanje/umetanje PDF-ova",
    "merge.intro": "Sastavite izvorne datoteke željenim redoslijedom spajanja. Za svaku datoteku po želji možete navesti odabir stranica (prazno = cijela datoteka) - istu datoteku dodajte više puta s različitim odabirom stranica kako biste je umetnuli na određeno mjesto unutar druge datoteke.",
    "merge.column_file": "Datoteka",
    "merge.column_pages": "Stranice",
    "merge.pages_placeholder": "sve",
    "merge.pages_tooltip": "Prazno = cijela datoteka. Inače npr. \"1-3,5\" ili \"6-\" (od stranice 6 do kraja) ili \"-4\" (od početka do stranice 4). \"5-3\" umeće stranice 5,4,3 tim (obrnutim) redoslijedom.",
    "merge.add_files": "Dodaj datoteke …",
    "merge.remove_selected": "Ukloni",
    "merge.move_up": "Pomakni gore",
    "merge.move_down": "Pomakni dolje",
    "merge.sort_by_name": "Sortiraj po nazivu",
    "merge.sort_by_date": "Sortiraj po datumu",
    "merge.sort_by_date_tooltip": "Sortira prema datumu zadnje izmjene datoteke na disku (nije datum stvaranja).",
    "merge.output_file_label": "Ciljna datoteka",
    "merge.output_placeholder": "Odaberite ciljnu datoteku …",
    "merge.choose_output_file": "Spremi kao …",
    "merge.start_button": "Pokreni spajanje",
    "merge.cancel_button": "Odustani",
    "merge.close_button": "Zatvori",
    "merge.status_running": "Obrada: {message}",
    "merge.status_done": "Gotovo: zapisano {pages} stranica iz {files} datoteka.",
    "merge.status_cancelled": "Otkazano (djelomičan rezultat spremljen): zapisano {pages} stranica.",
    "merge.status_failed": "Nije uspjelo: {error}",
    "merge.error_dialog_choose_files": "Odaberi PDF datoteke",
    "merge.error_dialog_choose_output": "Odaberi ciljnu datoteku",
    "merge.failed_title": "Spajanje nije uspjelo",
    "merge_search.button": "Pretraži mapu …",
    "merge_search.title": "Pretraga PDF-ova u mapi",
    "merge_search.folder_label": "Mapa",
    "merge_search.folder_placeholder": "Odaberite mapu …",
    "merge_search.choose_folder": "Odaberi mapu …",
    "merge_search.choose_folder_dialog_title": "Odaberi mapu za pretragu",
    "merge_search.recursive_checkbox": "Uklj. podmape",
    "merge_search.scope_ico_format": "ICO format (područje zaglavlja 1. stranice)",
    "merge_search.scope_header": "Zaglavlje (sve stranice)",
    "merge_search.scope_full_text": "Cjeloviti tekst",
    "merge_search.scope_ico_format_tooltip": "Pretražuje SAMO ICO blok metapodataka na 1. stranici (Developer, QSI ICO, datum izdavanja, ...). Neovisno o „Zaglavlju” ispod - ako je označena samo ova opcija, ponavljajuće zaglavlje na OSTALIM stranicama se NE pretražuje.",
    "merge_search.scope_header_tooltip": "Pretražuje SAMO područje koje se ponavlja pri vrhu svake stranice (npr. redak s nazivom tvrtke/logotipom). Neovisno o „ICO formatu” iznad - zasebna, samostalna tekstualna regija, ne proširenje toga.",
    "merge_search.scope_full_text_tooltip": "Pretražuje CJELOKUPAN tekst na svim stranicama, uključujući područja „ICO formata” i „Zaglavlja” iznad.",
    "merge_search.error_missing_scope": "Odaberite barem jedno područje pretrage.",
    "merge_search.date_filter_group": "Filtriraj po datumu",
    "merge_search.date_source_file": "Datum datoteke",
    "merge_search.date_source_document": "Datum u dokumentu",
    "merge_search.date_region_ico_format": "ICO polje (1. stranica)",
    "merge_search.date_region_header": "Zaglavlje (sve stranice)",
    "merge_search.date_region_footer": "Podnožje (sve stranice)",
    "merge_search.date_format_iso": "ISO (GGGG-MM-DD)",
    "merge_search.date_format_iso_tooltip": "Prepoznaje npr. „2026-09-04”.",
    "merge_search.date_format_de": "Njemački (DD.MM.GGGG)",
    "merge_search.date_format_de_tooltip": "Prepoznaje npr. „04.09.2026” (i dvoznamenkaste godine poput „04.09.26”).",
    "merge_search.date_format_en_month": "Engleski (naziv mjeseca, npr. September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Prepoznaje i „September 4, 2026” i „4. September 2026” (zarez nije obavezan, dan s jednom ili dvije znamenke).",
    "merge_search.date_format_slash": "Kosa crta (DD/MM/GGGG)",
    "merge_search.date_format_slash_tooltip": "Prepoznaje npr. „04/09/2026”.",
    "merge_search.date_exact_checkbox": "Točan datum",
    "merge_search.date_from_label": "Od",
    "merge_search.date_to_label": "Do",
    "merge_search.date_exact_label": "Datum",
    "merge_search.error_date_range_reversed": "„Od” ne smije biti nakon „Do”.",
    "merge_search.error_missing_date_region": "Odaberite barem jedno područje za pretragu datuma.",
    "merge_search.error_missing_date_format": "Odaberite barem jedan format datuma ili unesite vlastiti format.",
    "merge_search.date_custom_format_label": "Vlastiti format",
    "merge_search.date_custom_format_placeholder": "npr. MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Vlastiti format datuma s ovim zamjenskim znakovima (uvijek unosite na engleskom, čak i u ovom hrvatskom dijalogu) - svi ostali znakovi poput razmaka, zareza, točaka ili kosih crta pretražuju se doslovno:\n\nYYYY – godina, 4 znamenke, npr. 2026\nYY – godina, 2 znamenke, npr. 26\nMMMM – naziv mjeseca, npr. September\nMMM – skraćeni naziv mjeseca, npr. Sep\nMM – mjesec, 2 znamenke, npr. 09\nM – mjesec, 1 ili 2 znamenke, npr. 9\nDD – dan, 2 znamenke, npr. 04\nD – dan, 1 ili 2 znamenke, npr. 4\n\nPrimjeri:\n„MMMM D, YYYY” pronalazi „September 4, 2026”\n„MMMM DD, YYYY” pronalazi „September 04, 2026”\n„YYYY/MM/DD” pronalazi „2026/09/04”",
    "merge_search.error_invalid_custom_date_format": "Vlastiti format datuma nije valjan - upotrijebite zamjenske znakove iz opisa.",
    "merge_search.query_label": "Tekst pretrage (kombiniraj pojmove pomoću AND/OR ili &&/||)",
    "merge_search.query_placeholder": "npr. naziv tvrtke developera, ili pojam1 AND pojam2 – ostavite prazno za sve datoteke u mapi",
    "merge_search.query_tooltip": "Više pojmova pretrage može se povezati pomoću AND i OR - i kombinirano. Zagradama određuješ što pripada zajedno.\n\nPrimjer: „Acme AND ugovor” pronalazi samo datoteke koje sadrže OBA pojma.\n„Acme OR Zenith” pronalazi datoteke s BAREM JEDNIM od ta dva pojma.\n\nKombinirano sa zagradama: „StellarRussia OR (The AND Korolev AND Directive)” pronalazi datoteke sa „StellarRussia” OR datoteke koje sadrže SVA TRI pojma „The”, „Korolev” i „Directive”.\n\nUmjesto AND/OR mogu se koristiti i znakovi && i || (isto značenje, i kombinirano s riječima): „Acme && ugovor” isto je što i „Acme AND ugovor”.\n\nBez AND/OR, cijeli tekst tretira se kao jedan pojedinačni pojam pretrage (kao dosad). Velika/mala slova nisu bitna.",
    "merge_search.search_button": "Pretraži",
    "merge_search.cancel_button": "Odustani",
    "merge_search.select_all": "Odaberi sve",
    "merge_search.select_none": "Poništi odabir",
    "merge_search.detach_results_button": "Otvori popis rezultata u zasebnom prozoru",
    "merge_search.reattach_results_button": "Usidri rezultate natrag",
    "merge_search.results_detached_placeholder": "Popis rezultata otvoren je u zasebnom prozoru.",
    "merge_search.detached_results_title_suffix": "Rezultati",
    "merge_search.take_selected": "Preuzmi odabrane",
    "merge_search.close_button": "Zatvori",
    "merge_search.status_running": "Pretraživanje: {current} ({done}/{total})",
    "merge_search.status_done": "{matches} podudaranja od {scanned} pretraženih PDF-ova.",
    "merge_search.status_done_with_errors": "{matches} podudaranja od {scanned} pretraženih PDF-ova ({errors} nečitljivo).",
    "merge_search.status_cancelled": "Otkazano: {matches} podudaranja od {scanned} pretraženih PDF-ova.",
    "merge_search.status_failed": "Nije uspjelo: {error}",
    "merge_search.error_missing_folder": "Najprije odaberite mapu.",
    "merge_search.failed_title": "Pretraga nije uspjela",
    "merge_search.source_local": "Lokalna mapa",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Poveznica ili ID Drive mape",
    "merge_search.drive_folder_placeholder": "Umetnite poveznicu za dijeljenje ili ID mape …",
    "merge_search.drive_resolve_button": "Provjeri",
    "merge_search.drive_folder_unresolved": "Još nije provjereno.",
    "merge_search.drive_folder_resolved": "Pronađena mapa „{name}”.",
    "merge_search.drive_folder_resolve_failed": "Nije uspjelo: {error}",
    "merge_search.drive_cache_label": "Mapa za predmemoriju (preuzimanja ostaju ovdje sačuvana)",
    "merge_search.drive_choose_cache": "Odaberi mapu za predmemoriju …",
    "merge_search.drive_choose_cache_dialog_title": "Odaberi mapu za preuzete rezultate",
    "merge_search.drive_credentials_label": "Google OAuth vjerodajnice (jednokratno, pogledajte docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Učitaj iz JSON datoteke …",
    "merge_search.drive_load_from_file_dialog_title": "Odaberi client-secrets JSON iz Google Cloud Console",
    "merge_search.drive_load_from_file_failed": "Datoteku nije bilo moguće pročitati: {error}",
    "merge_search.drive_client_id_placeholder": "Client ID",
    "merge_search.drive_client_secret_placeholder": "Client Secret",
    "merge_search.drive_project_id_placeholder": "Project ID",
    "merge_search.drive_save_credentials": "Spremi vjerodajnice",
    "merge_search.drive_credentials_saved": "Vjerodajnice spremljene.",
    "merge_search.drive_save_failed": "Spremanje nije uspjelo: {error}",
    "merge_search.drive_not_configured": "Još nije spremljen Client ID/Secret/Project ID.",
    "merge_search.drive_configured_not_connected": "Konfigurirano, ali još nije povezano.",
    "merge_search.drive_connected": "Povezano{account}.",
    "merge_search.drive_connect_button": "Poveži s Googleom",
    "merge_search.drive_disconnect_button": "Prekini vezu",
    "merge_search.drive_connecting": "Otvaranje preglednika za prijavu …",
    "merge_search.drive_connect_failed": "Povezivanje nije uspjelo: {error}",
    "merge_search.drive_error_missing_folder": "Najprije unesite i provjerite Drive mapu.",
    "merge_search.drive_error_missing_cache": "Najprije odaberite mapu za predmemoriju.",
    "merge_search.drive_error_not_connected": "Najprije se povežite s Googleom.",
    "word_merge.button": "Spoji/umetni DOCX datoteke …",
    "word_merge.title": "Spajanje/umetanje DOCX datoteka",
    "word_merge.intro": "Sastavite izvorne datoteke željenim redoslijedom - uvijek cijele datoteke (za razliku od PDF-a, DOCX u samom formatu datoteke nema fiksan broj stranica). Istu datoteku dodajte više puta kako biste je umetnuli na više mjesta. Iznad 100 datoteka spajanje se automatski odvija u grupama (pogledajte statusni redak nakon postupka).",
    "word_merge.status_done": "Gotovo: preuzeto {segments} od {files} datoteka{batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Otkazano (djelomičan rezultat spremljen): preuzeto {segments} datoteka{batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " u {batches} grupa",
    "word_merge.status_warning_suffix": ", {count} preskočeno (vidi ispod)",
    "word_merge.warnings_title": "Preskočene datoteke:",
    "word_merge.error_dialog_choose_files": "Odaberi DOCX datoteke",
    "word_merge_search.title": "Pretraga DOCX datoteka u mapi",
    "word_merge_search.status_done": "{matches} podudaranja od {scanned} pretraženih DOCX datoteka.",
    "word_merge_search.status_done_with_errors": "{matches} podudaranja od {scanned} pretraženih DOCX datoteka ({errors} nečitljivo).",
    "word_merge_search.status_cancelled": "Otkazano: {matches} podudaranja od {scanned} pretraženih DOCX datoteka.",
    "bootstrap.window_title": "Postavljanje Document Translatora",
    "bootstrap.back_button": "Natrag",
    "bootstrap.next_button": "Dalje",
    "bootstrap.cancel_button": "Odustani",
    "bootstrap.cancel_title": "Prekinuti instalaciju?",
    "bootstrap.cancel_confirm": (
        "Čarobnjak za postavljanje zatvorit će se, a Document Translator "
        "neće biti u potpunosti postavljen. Već stvorene datoteke bit "
        "će automatski uklonjene. Nastaviti?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "Instalacija je trenutno u tijeku. Prekidom će se automatski "
        "ukloniti već stvorene datoteke - u rijetkim slučajevima "
        "datoteka koja se u tom trenutku koristi može ostati. Ipak "
        "prekinuti?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Administratorska prava",
    "bootstrap.elevated_warning_text": (
        "Document Translator je pokrenut kao administrator.\n\n"
        "To nije potrebno i uzrokovat će da aplikacija kasnije ne radi "
        "kada se pokrene normalno (bez administratorskih prava).\n\n"
        "Zatvorite ovaj prozor i ponovno pokrenite instalaciju običnim "
        "dvoklikom (bez \"Pokreni kao administrator\").\n\n"
        "Ova se poruka može kopirati pomoću Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Deinstaliraj Document Translator",
    "bootstrap.uninstall_confirm": (
        "Ukloniti Document Translator, uključujući sve lokalno pohranjene "
        "postavke i API ključeve?"
    ),
    "bootstrap.uninstall_done": "Document Translator je uklonjen.",
    "bootstrap.welcome_title": "Dobrodošli",
    "bootstrap.welcome_text": "Ovaj čarobnjak postavlja Document Translator na ovo računalo - bez potrebe za naredbenim retkom. Preuzima potrebne komponente i na kraju stvara stavku u izborniku aplikacija.",
    "bootstrap.language_label": "Jezik",
    "bootstrap.mode_title": "Online ili lokalno?",
    "bootstrap.mode_intro": "Kako želite da prijevod radi? To kasnije uvijek možete promijeniti u postavkama.",
    "bootstrap.mode_online_label": "Online (cloud pružatelj)",
    "bootstrap.mode_online_desc": "Prijevod se odvija putem vanjskog pružatelja (DeepL, Google, OpenAI ili Grok). Za to nastaju tekući troškovi po prijevodu, a potreban je vlastiti API ključ dotičnog pružatelja - o tome više uskoro. Obrada slika u ugrađenim slikama radi i ovdje, samo jednostavnijom metodom umjesto AI inpaintinga. Nije potrebno veliko preuzimanje. Preporučeno ako nemate snažnu grafičku karticu.",
    "bootstrap.mode_local_label": "Lokalno (na ovoj grafičkoj kartici)",
    "bootstrap.mode_local_desc": "Poboljšava samo obradu slika: tekst ugrađen u slike prepoznaje se OCR-om i nakon prijevoda ponovno se crta pomoću AI modela (LaMa) izravno na ovoj grafičkoj kartici - rezultat izgleda čišće nego jednostavnija metoda dostupna i bez ove opcije. Sam prijevod teksta u oba načina rada i dalje ide preko vanjskog pružatelja usluge (DeepL, Google, OpenAI ili Grok), uz uobičajeni trošak po prijevodu kod tog pružatelja. Online pružatelje možete dodatno postaviti u bilo kojem trenutku u postavkama ako želite. Potrebna je dovoljno snažna NVIDIA grafička kartica (provjerava se u sljedećem koraku), a tijekom instalacije jednokratno se preuzima oko 2-3 GB.",
    "bootstrap.gpu_checking": "Provjera grafičke kartice …",
    "bootstrap.gpu_ok": "Pronađeno: {name} s {vram_gb:.0f} GB video memorije - to je dovoljno.",
    "bootstrap.gpu_insufficient": "Pronađeno: {name} s {vram_gb:.0f} GB video memorije - preporučeno je najmanje {min_gb:.0f} GB. Lokalni način rada vjerojatno će biti vrlo spor.",
    "bootstrap.gpu_not_found": "Nije pronađena podržana NVIDIA grafička kartica. Lokalni način rada nije praktično upotrebljiv na ovom računalu.",
    "bootstrap.gpu_driver_too_old": "Pronađeno: {name}, ali NVIDIA upravljački program je prestar (podržava samo CUDA {cuda_version}, potrebno je najmanje 11.8). Ažurirajte upravljački program grafičke kartice i ponovno pokrenite ovaj čarobnjak, ili umjesto toga odaberite Online.",
    "bootstrap.gpu_mac_unsupported": "Lokalni način rada trenutno nije podržan na Macu. Umjesto toga odaberite Online.",
    "bootstrap.gpu_continue_local_button": "Ipak nastavi lokalno",
    "bootstrap.gpu_switch_online_button": "Prijeđi na Online",
    "bootstrap.install_title": "Instalacija u tijeku",
    "bootstrap.install_step_venv": "Postavljanje radnog okruženja …",
    "bootstrap.install_step_deps": "Instaliranje komponenti ({name}) …",
    "bootstrap.install_step_source": "Preuzimanje programskog koda …",
    "bootstrap.install_step_shortcut": "Dodavanje stavke u izbornik aplikacija …",
    "bootstrap.install_failed_title": "Instalacija nije uspjela",
    "bootstrap.install_failed": "Nije uspjelo: {error}",
    "bootstrap.credentials_title": "Postavljanje API ključeva",
    "bootstrap.credentials_intro": "Koje pružatelje želite postaviti? To možete preskočiti i naknadno obaviti u postavkama aplikacije.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Brza samostalna registracija. Dostupna besplatna kvota, nakon toga naplata.",
    "bootstrap.credentials_explain_google": "Potreban je Google Cloud projekt s pohranjenim načinom plaćanja - malo zahtjevnije postavljanje nego kod ostala tri pružatelja.",
    "bootstrap.credentials_explain_openai": "Brza samostalna registracija, naplata prema korištenju.",
    "bootstrap.credentials_explain_grok": "Brza samostalna registracija, naplata prema korištenju.",
    "bootstrap.credentials_open_signup_button": "Nabavi ključ (otvara preglednik)",
    "bootstrap.open_browser_title": "Otvoriti preglednik?",
    "bootstrap.open_browser_text": (
        "Sljedeća poveznica će se otvoriti u zadanom pregledniku:\n\n"
        "{url}\n\n"
        "Provjerite je li to doista očekivana adresa prije nego što "
        "nastavite."
    ),
    "bootstrap.credentials_key_label": "API ključ za {provider}",
    "bootstrap.credentials_key_placeholder": "Umetni ključ …",
    "bootstrap.credentials_save_button": "Spremi",
    "bootstrap.credentials_saved": "Spremljeno.",
    "bootstrap.credentials_skip_all_button": "Kasnije, u postavkama",
    "bootstrap.credentials_continue_button": "Dalje",
    "bootstrap.finish_title": "Gotovo",
    "bootstrap.finish_text": "Document Translator je postavljen i dostupan je u izborniku aplikacija.",
    "bootstrap.finish_download_size": "Stvarno preuzeto: oko {size_gb:.1f} GB.",
    "bootstrap.finish_launch_button": "Pokreni sada",
    "bootstrap.finish_close_button": "Zatvori",
    "mode.tooltip": "Vrsta dokumenta za prevođenje",
    "mode.whatsthis": (
        "Određuje koji se tijek prevođenja koristi: PDF, PowerPoint/"
        "Impress, Word/Writer ili pojedinačne slike. Ovisno o odabiru, "
        "ispod se prikazuju samo relevantna polja, npr. postavke OCR-a "
        "samo u načinu \"Slike\"."
    ),
    "source.tooltip": "Odaberi datoteku/e za prevođenje",
    "source.whatsthis": (
        "Otvara dijalog za odabir izvorne datoteke (u načinu Slike i "
        "više datoteka odjednom). Odabrani naziv datoteke zatim se "
        "prikazuje lijevo pored."
    ),
    "source_label.tooltip": "Trenutačno odabrana izvorna datoteka",
    "source_label.whatsthis": (
        "Prikazuje naziv datoteke posljednji put odabrane putem "
        "\"Odaberi datoteku …\". Ako još uvijek piše \"Nijedna datoteka "
        "nije odabrana\", prvo je potrebno odabrati datoteku prije nego "
        "što je moguća procjena troškova."
    ),
    "image_mode.tooltip": "Postupanje sa slikama ugrađenima u dokument",
    "image_mode.whatsthis": (
        "\"Ne prevodi\" ostavlja ugrađene slike nepromijenjene. "
        "\"Kasnije pojedinačno odaberi\" nakon procjene troškova "
        "prikazuje popis za odabir određenih slika. \"Prevedi sve\" "
        "automatski obrađuje svaku ugrađenu sliku."
    ),
    "provider.tooltip": "Pružatelj usluge prevođenja za ovo pokretanje",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI ili Grok - svaki sa svojim API ključem, "
        "kojim se upravlja u Postavkama. Ako za odabranog pružatelja "
        "nije postavljen ključ, odmah ispod pojavljuje se napomena s "
        "poveznicom na Postavke."
    ),
    "source_lang.tooltip": "Kôd izvornog jezika, npr. EN",
    "source_lang.whatsthis": (
        "Dvoslovni jezični kôd prema ISO 639-1 (npr. EN za engleski, FR "
        "za francuski). Mora odgovarati stvarnom jeziku dokumenta, "
        "inače pružatelj usluge prevođenja vraća pogrešne ili nikakve "
        "rezultate."
    ),
    "target_lang.tooltip": "Kôd ciljnog jezika, npr. DE",
    "target_lang.whatsthis": (
        "Dvoslovni jezični kôd prema ISO 639-1 na koji se prevodi (npr. "
        "DE za njemački, ES za španjolski)."
    ),
    "protected.tooltip": "Pojmovi koji trebaju ostati neprevedeni",
    "protected.whatsthis": (
        "Jedan pojam po retku, npr. nazivi tvrtki ili proizvoda. "
        "Pružatelj usluge prevođenja ostavlja te pojmove netaknutima. "
        "Gumb pored omogućuje i učitavanje popisa iz datoteke."
    ),
    "ocr_engine_field.tooltip": "Prepoznavanje teksta (OCR) za slike",
    "ocr_engine_field.whatsthis": (
        "Prikazano samo u načinu \"Slike\". Prepoznaje tekst na slikama "
        "prije nego što se prevede i vrati natrag. Ako alat nije "
        "dostupan na ovom računalu, odmah ispod pojavljuje se napomena."
    ),
    "inpainting_backend_field.tooltip": (
        "Metoda vraćanja prevedenog teksta natrag u sliku"
    ),
    "inpainting_backend_field.whatsthis": (
        "Prikazano samo u načinu \"Slike\". \"Prekrivanje okvirom\" i "
        "\"CV Inpainting\" uvijek rade lokalno, bez posebnog hardvera. "
        "\"GPU Inpainting\" koristi lokalnu grafičku karticu (CUDA) za "
        "najbolji rezultat i dostupan je samo ako je instaliran PyTorch "
        "s podrškom za CUDA - inače se ispod pojavljuje napomena. "
        "Stanje hardvera moguće je provjeriti u bilo kojem trenutku "
        "putem Pomoć -> Test hardvera."
    ),
    "merge.tooltip": "Spoji više PDF datoteka",
    "merge.whatsthis": (
        "Otvara zaseban dijalog za spajanje više PDF datoteka u jednu. "
        "Neovisno o obrascu iznad - ovdje se ništa ne prevodi."
    ),
    "word_merge.tooltip": "Spoji više Word datoteka",
    "word_merge.whatsthis": (
        "Otvara zaseban dijalog za spajanje više Word datoteka u jednu. "
        "Neovisno o obrascu iznad - ovdje se ništa ne prevodi."
    ),
    "analysis.button.tooltip": "Procijeni trošak ovog prijevoda",
    "analysis.button.whatsthis": (
        "Broji znakove za prevođenje i prema odabranom pružatelju "
        "procjenjuje okvirni trošak, bez stvarnog prevođenja. Tek nakon "
        "toga moguće je označiti kvačicu pored i omogućiti \"Pokreni\"."
    ),
    "analysis.checked.tooltip": "Potvrdi procijenjene troškove",
    "analysis.checked.whatsthis": (
        "Mora biti označeno prije nego \"Pokreni\" postane klikabilno - "
        "namjerni sigurnosni korak kako se pokretanje nikada ne bi "
        "slučajno pokrenulo bez prethodnog uvida u procijenjene "
        "troškove."
    ),
    "start.tooltip": "Pokreni prijevod",
    "start.whatsthis": (
        "Aktivira se tek nakon što su troškovi analizirani i "
        "potvrđeni. Napredak se prikazuje u području ispod; pokrenuto "
        "izvršavanje moguće je zaustaviti putem \"Prekini\"."
    ),
    "job.cancel.tooltip": "Prekini pokrenuti prijevod",
    "job.cancel.whatsthis": (
        "Zaustavlja trenutačno izvršavanje što je brže moguće. Već "
        "obrađeni dijelovi ne čuvaju se automatski kao potpuna datoteka "
        "- ovisno o formatu, može ostati nepotpuna datoteka."
    ),
    "job.open_folder.tooltip": "Otvori izlaznu mapu",
    "job.open_folder.whatsthis": (
        "Otvara preglednik datoteka u ciljnoj mapi upravo završenog "
        "izvršavanja."
    ),
    "job.open_report.tooltip": "Otvori QA izvještaj posljednjeg izvršavanja",
    "job.open_report.whatsthis": (
        "Prikazuje nalaze automatske provjere kvalitete posljednjeg "
        "izvršavanja, npr. dijelove koje bi vrijedilo provjeriti."
    ),
    "job.correct_translation.tooltip": "Ispravi pojedinačne prijevode",
    "job.correct_translation.whatsthis": (
        "Prikazano samo kod PDF izvršavanja s ispravljivim tekstualnim "
        "blokovima. Omogućuje naknadnu obradu pojedinačnih prevedenih "
        "dijelova bez ponavljanja cijelog izvršavanja."
    ),
    "settings.button.tooltip": "Otvori postavke",
    "settings.button.whatsthis": (
        "API ključevi po pružatelju (preporučeno: keyring), ograničenje "
        "znakova po izvršavanju i pristup datoteci zapisnika."
    ),
    "update_hint.tooltip": "Dostupna je nova verzija",
    "update_hint.whatsthis": (
        "Prikazuje se automatski kada se pri pokretanju pronađe novija "
        "verzija Document Translatora. Klik nudi instalaciju nove verzije."
    ),
    "flag_row.whatsthis": (
        "Odmah i trajno mijenja jezik samog sučelja - ne jezike "
        "prijevoda u obrascu. Odabir se odmah sprema."
    ),
    "menu.help.whats_this": "Što je ovo?",
}


RU = {
    "app.title": "Document Translator",
    "mode.pdf": "Перевести PDF",
    "mode.presentation": "Перевести презентацию (PowerPoint/Impress)",
    "mode.word": "Перевести документ Word/Writer",
    "mode.images": "Перевести отдельные изображения",
    "source.none": "Файл не выбран",
    "source.choose": "Выбрать файл…",
    "image.none": "Не переводить встроенные изображения",
    "image.selected": "Выбрать изображения позже по отдельности",
    "image.all": "Перевести все встроенные изображения",
    "field.mode": "Задача",
    "field.source": "Источник",
    "field.images": "Изображения в документе",
    "field.provider": "Поставщик перевода",
    "field.source_language": "Исходный язык",
    "field.target_language": "Целевой язык",
    "field.protected_terms": "Защищённые термины",
    "field.ico_mode": "Документ ICO",
    "ico_mode.checkbox": "Не переводить область на странице 1",
    "ico_mode.tooltip": "Только для внутреннего типа документа ICO: исключает блок метаданных на странице 1 из перевода (в Word — область перед разделительной линией; в PDF — определяется по опорным терминам, например \"Issuer Address\"/\"Asset Matrix\") — независимо от того, найден ли этот блок на самом деле. Для всех остальных документов оставьте отключённым.",
    "field.side_by_side": "Показ рядом",
    "side_by_side.checkbox": "Оригинал и перевод рядом",
    "side_by_side.tooltip": "Только для Word: вместо обычного результата с сохранением макета основной текст оформляется как двухколоночная таблица сравнения (оригинал | перевод) в альбомной ориентации. Колонтитулы остаются без изменений. Встроенные таблицы в основном тексте (если есть) в этом режиме не отображаются.",
    "field.exclude_header": "Верхний колонтитул",
    "exclude_header.checkbox": "Не переводить повторяющийся верхний колонтитул",
    "exclude_header.tooltip": "Автоматически распознаёт текст, который одинаково повторяется в верхней части большинства страниц (или отличается только номером страницы), и исключает его из перевода. Если подходящий текст не найден, ничего не меняется.",
    "field.exclude_footer": "Нижний колонтитул",
    "exclude_footer.checkbox": "Не переводить повторяющийся нижний колонтитул",
    "exclude_footer.tooltip": "Аналогично верхнему колонтитулу, но для повторяющегося текста в нижней части страницы (например, строка авторских прав, номер страницы).",
    "field.ocr_engine": "Модуль OCR",
    "ocr_engine.tesseract": "Tesseract (локально)",
    "ocr_engine.tesseract.unavailable": "Tesseract не найден в этой системе. Установите его (см. README.md) — без установленного Tesseract распознавание текста на изображениях невозможно.",
    "ocr_engine.google_vision": "Google Cloud Vision (облако, распознавание абзацев)",
    "ocr_engine.google_vision.unavailable": "Не настроен ключ API Google. Укажите его в настройках (тот же ключ, что и для Google Translate, см. README.md), либо выберите другой модуль OCR.",
    "ocr_engine.paddleocr": "PaddleOCR (локально, распознавание абзацев)",
    "ocr_engine.paddleocr.unavailable": "PaddleOCR не установлен (см. requirements-paddleocr.txt), либо выберите другой модуль OCR.",
    "ocr_engine.unavailable": "Этот модуль OCR недоступен в данной системе.",
    "field.inpainting_backend": "Метод перерисовки",
    "inpainting_backend.box_overlay": "Прямоугольник поверх (закрыть область)",
    "inpainting_backend.cv_inpainting": "Классический CPU-инпейнтинг (восстановление фона)",
    "inpainting_backend.gpu_inpainting": "ИИ-инпейнтинг локально (GPU, LaMa)",
    "inpainting_backend.unavailable": "Для этого метода не найдена GPU с поддержкой CUDA (см. requirements-gpu.txt) — выберите другой метод перерисовки.",
    "inpainting_backend.below_recommended_vram": "Обнаружено только {vram_gb:.0f} ГБ видеопамяти (рекомендуется как минимум {min_gb:.0f} ГБ) — может сработать, но без гарантии, особенно при больших изображениях или большом количестве текстовых областей одновременно.",
    "source_language.placeholder": "необязательно / автоматически",
    "protected.placeholder": "По одному защищённому термину на строку",
    "protected.load_file": "Загрузить из файла…",
    "protected.load_file.tooltip": "Загрузка терминов из CSV- или текстового файла (по одному термину на строку; для CSV используется первый столбец). Существующие записи сохраняются, дубликаты пропускаются.",
    "protected.loaded": "Добавлено новых терминов: {added} из {name} (всего в файле: {total}).",
    "protected.load_error": "Не удалось прочитать {name}: {error}",
    "dialog.choose_protected_terms": "Выбрать список терминов",
    "dialog.all_files": "Все файлы",
    "merge_box.group": "Объединение файлов",
    "config.group": "Настройка задания",
    "analysis.group": "Анализ и контроль стоимости",
    "analysis.required": "Перед началом требуется выполнить анализ.",
    "analysis.button": "Анализировать документ и оценить стоимость",
    "analysis.running": "Выполняется анализ…",
    "analysis.checked": "Анализ и оценка стоимости проверены",
    "analysis.failed": "Анализ не выполнен.",
    "analysis.no_warnings": "Предупреждений анализа нет.",
    "analysis.within": "в пределах лимита",
    "analysis.exceeded": "ПРЕВЫШЕНО",
    "analysis.summary": "<b>{units} {unit_label}</b> · {characters:,} текстовых символов · {images}<br>Локальная оценка ({provider}): расход за месяц {usage:,} / бесплатный лимит {free:,} символов · оценка ${cost:.2f}<br>Лимит на запуск {limit:,}: {limit_state}<br>{warnings}",
    "analysis.live_quota": "<b>Актуальная квота (DeepL, только что получена):</b> использовано {used:,} из {limit:,} символов, осталось {remaining:,}.",
    "analysis.live_quota_unlimited": "<b>Актуальная квота (DeepL, только что получена):</b> использовано {used:,} символов, аккаунт не сообщает об ограничении.",
    "unit.pages": "страниц",
    "unit.slides": "слайдов",
    "unit.paragraphs": "абзацев",
    "unit.images": "изображений",
    "warning.scan_pdf": "Обнаружен PDF-скан/изображение: для распознавания текста документа требуется OCR.",
    "warning.image_cost_unknown": "Количество символов OCR и стоимость перевода изображений станут известны только после OCR.",
    "warning.image_selection_later": "Точный выбор изображений будет доступен после анализа, в одной из следующих версий интерфейса.",
    "warning.embedded_images_not_estimated": "Текст на изображениях не включён в оценку: встроенные изображения пока не переводятся при обработке документа.",
    "analysis.images.files": "{images} файлов изображений",
    "analysis.images.excluded": "{images} встроенных изображений (исключены, не учитываются в стоимости)",
    "analysis.images.included": "{selected} из {images} встроенных изображений выбрано для перевода",
    "warning.live_quota_unavailable": "Актуальная квота DeepL сейчас недоступна (нет ключа, нет соединения или ошибка API) — используется локальная оценка.",
    "start.button": "Начать перевод",
    "start.pending": "Запуск для этого режима пока не реализован (см. RoadMap.md).",
    "start.ready": "Готово к запуску.",
    "start.blocked_running": "Уже выполняется другой процесс.",
    "start.blocked_mode": "Запуск для этого режима пока не реализован (см. RoadMap.md) — подключён пока только режим «Перевести презентацию».",
    "start.blocked_no_analysis": "Сначала выполните «Анализировать документ и оценить стоимость».",
    "start.blocked_not_confirmed": "Установите флажок «Анализ и оценка стоимости проверены».",
    "dialog.choose_output_dir": "Выбрать целевую папку",
    "dialog.confirm_run": "Начать перевод",
    "start.confirm_summary": "Будет отправлено примерно {characters:,} символов в {provider} (ориентировочная стоимость ${cost:.2f}).\nЦелевой файл: {destination}\n\nНачать сейчас?",
    "start.confirm_summary_images": "Будет отправлено примерно {characters:,} символов в {provider} (ориентировочная стоимость ${cost:.2f}) для {count} изображени(й).\nЦелевая папка: {folder}\n\nНачать сейчас?",
    "job.group": "Выполнение и результат",
    "job.idle": "Пока ничего не запускалось.",
    "job.running": "Выполняется перевод…",
    "job.progress_prefix": "Обработка: {location}",
    "job.progress_count": "Обработано {processed} из {total} абзацев",
    "job.progress_count_files": "Обработано {processed} из {total} изображений",
    "job.stats_summary": "переведено: {translated} · пропущено: {skipped} · ошибок: {failed} · отправлено символов: {chars:,}",
    "job.cancel": "Отмена",
    "job.cancel_requested": "Запрошена отмена — остановка после завершения текущего запроса к API…",
    "job.result_summary": "Готово: переведено {translated}, пропущено {skipped}, ошибок {failed}, отправлено символов {chars:,}.\nВыходной файл: {output}\nОтчёт QA: {report}",
    "job.result_summary_images": "Готово: обработано изображени(й) {files}, переведено текстовых областей {translated}, ошибок {failed}, отправлено символов {chars:,}.\nВыходная папка: {output_dir}\nДля каждого изображения в выходной папке создаётся отдельный файл отчёта QA.",
    "job.result_cancelled_suffix": "\nПримечание: выполнение было отменено — это частичный результат, уже переведённое содержимое сохранено.",
    "job.overflow_none": "Новых рисков переполнения не обнаружено.",
    "job.overflow_count": "{count} предупреждени(й) о переполнении в отчёте QA — проверьте вручную в PowerPoint/Impress.",
    "job.pdf_overflow_none": "Ни одному блоку не потребовалось увеличение или уменьшение при вставке.",
    "job.pdf_overflow_count": "{count} блок(ов) потребовалось увеличить или уменьшить, чтобы уместить текст — проверьте выборочно в PDF.",
    "job.open_folder": "Открыть папку",
    "job.open_report": "Открыть отчёт QA",
    "job.open_folder_failed": "Не удалось открыть папку.",
    "job.show_report": "Показать отчёт QA",
    "job.hide_report": "Скрыть отчёт QA",
    "job.report_load_error": "Не удалось загрузить отчёт QA.",
    "job.correct_translation": "Исправить перевод",
    "job.correction_starting": "Запуск исправления…",
    "job.correction_opened": "Окно исправления открыто — внесите изменения там, затем нажмите «Применить» или «Отмена».",
    "job.correction_applied": "Исправление применено.",
    "job.correction_cancelled": "Исправление отменено.",
    "job.correction_timeout": "Превышено время ожидания исправления — окно исправления не отвечает.",
    "job.correction_failed": "Исправление не выполнено: {error}",
    "job.correction_error": "Не удалось запустить исправление.",
    "job.failed_title": "Ошибка перевода",
    "correction.title": "Исправление перевода PDF",
    "correction.hint": "Выберите строку ниже и отредактируйте её перевод в редакторе под таблицей. С помощью «Жирный»/«Курсив»/«Подчёркнутый» (или Ctrl+B/Ctrl+I/Ctrl+U) можно изменить форматирование — отредактированные строки сохраняют своё форматирование.",
    "correction.column_page": "Страница",
    "correction.column_original": "Оригинал",
    "correction.column_translation": "Перевод",
    "correction.editor_label": "Редактировать перевод:",
    "correction.bold": "Жирный",
    "correction.italic": "Курсив",
    "correction.underline": "Подчёркнутый",
    "correction.bold_tooltip": "Жирный (Ctrl+B)",
    "correction.italic_tooltip": "Курсив (Ctrl+I)",
    "correction.underline_tooltip": "Подчёркнутый (Ctrl+U)",
    "correction.apply": "Применить и сохранить",
    "correction.close": "Закрыть",
    "correction.applying": "Применение…",
    "correction.success": "Обновлено блоков: {count}, сохранено в {output}.",
    "correction.failed": "Исправление не выполнено: {error}",
    "image_correction.title": "Исправление перевода изображения",
    "image_correction.hint": "Выберите строку ниже и отредактируйте её перевод в редакторе под таблицей.",
    "image_correction.canvas_hint": "На изображении слева можно перетаскиванием переместить рамку строки. Выберите строку, чтобы потянуть за её нижний правый угол и изменить размер. С помощью Ctrl+колесо мыши или кнопок масштаба можно приближать и отдалять изображение; окно также можно развернуть на весь экран.",
    "image_correction.reset_geometry": "Сбросить положение/размер",
    "image_correction.zoom_in": "Увеличить (+)",
    "image_correction.zoom_out": "Уменьшить (−)",
    "image_correction.zoom_reset": "Подогнать по размеру",
    "image_correction.add_region": "Добавить новую рамку",
    "image_correction.add_region_hint": "Выделите область на изображении, чтобы добавить там новую рамку с собственным текстом.",
    "image_correction.show_original": "Показать оригинал",
    "image_correction.manual_region_label": "(добавлено вручную, без распознавания OCR)",
    "image_correction.manual_region_added": "Добавлена новая рамка — введите перевод в редакторе.",
    "image_correction.column_original": "Оригинал",
    "image_correction.column_translation": "Перевод",
    "image_correction.editor_label": "Редактировать перевод:",
    "image_correction.font_size_label": "Размер шрифта:",
    "image_correction.font_size_auto": "Автоматически",
    "image_correction.bold": "Жирный",
    "image_correction.centered": "По центру",
    "image_correction.apply": "Применить и сохранить",
    "image_correction.close": "Закрыть",
    "image_correction.applying": "Применение…",
    "image_correction.success": "Обновлено областей: {count}, сохранено в {output}.",
    "image_correction.failed": "Исправление не выполнено: {error}",
    "image_correction.choose_file_title": "Выбрать файл для исправления",
    "image_correction.choose_file_label": "Какой файл из этого запуска нужно исправить?",
    "update.available": "Доступно обновление: {version}",
    "update.confirm_title": "Установить обновление?",
    "update.confirm_body": "Доступна новая версия ({version}). Загрузить и установить сейчас?",
    "update.installing": "Установка обновления…",
    "update.success_title": "Обновление установлено",
    "update.success_body": "Обновление установлено. Перезапустите приложение, чтобы изменения вступили в силу.",
    "update.failed_title": "Ошибка обновления",
    "update.failed_body": "Не удалось установить обновление: {error}\n\nРанее установленная версия продолжает работать без изменений.",
    "menu.help": "Справка",
    "menu.help.hw_check": "Показать/повторить проверку оборудования…",
    "menu.help.check_updates": "Проверить наличие обновлений…",
    "menu.help.about": "О программе…",
    "about.body": "<h3>{app_name}</h3><p>Версия {version}</p><p>Переводит документы PDF, Word и PowerPoint, а также изображения с сохранением макета.</p><p>© {year} {author}<br>Лицензия: <a href=\"{license_url}\">GNU GPL v3</a></p><p>Исходный код: <a href=\"{repo_url}\">GitHub</a></p>",
    "menu.help.manual": "Руководство пользователя…",
    "manual.hint_link": "Подробнее в руководстве пользователя (глава 4)",
    "manual.missing": "Руководство пользователя не найдено:\n{path}",
    "update.check.no_update_title": "Обновлений нет",
    "update.check.no_update_body": "Вы уже используете последнюю версию ({version}).",
    "update.check.failed_title": "Ошибка проверки обновлений",
    "update.check.failed_body": "Не удалось проверить наличие обновлений: {error}",
    "hw_check.title": "Проверка оборудования",
    "hw_check.note": "Если приложение работает не так, как ожидается (например, при локальном ИИ-инпейнтинге), здесь можно повторно проверить оборудование.",
    "hw_check.recheck_button": "Проверить снова",
    "hw_check.checking": "Проверка оборудования…",
    "hw_check.never_checked": "Проверка оборудования ещё не выполнялась. Нажмите «Проверить снова», чтобы выполнить её сейчас.",
    "hw_check.not_found": "GPU с поддержкой CUDA не найдена (последняя проверка: {checked_at}). Локальный ИИ-инпейнтинг недоступен на этом оборудовании — облачный инпейнтинг работает независимо от этого.",
    "hw_check.found_ok": "Найдено: {name} с {vram_gb:.0f} ГБ видеопамяти (последняя проверка: {checked_at}). Соответствует рекомендации не менее {min_gb:.0f} ГБ.",
    "hw_check.found_below_recommended": "Найдено: {name} с {vram_gb:.0f} ГБ видеопамяти (последняя проверка: {checked_at}). Меньше рекомендуемых {min_gb:.0f} ГБ — может сработать, но без гарантии, особенно при больших изображениях или большом количестве текстовых областей одновременно.",
    "hw_check.driver_cuda_ok": "Драйвер поддерживает CUDA {cuda_version} — подходящий вариант PyTorch: {torch_variant}.",
    "hw_check.driver_cuda_too_old": "Драйвер поддерживает только CUDA {cuda_version} — это слишком старая версия для локального ИИ-инпейнтинга (требуется не менее 11.8). Обновите видеодрайвер.",
    "settings.button": "Настройки…",
    "settings.title": "Настройки",
    "settings.language": "Язык интерфейса",
    "settings.prepared": "подготовлено",
    "settings.provider": "Поставщик",
    "settings.credentials": "Учётные данные",
    "settings.new_key": "Новый ключ API",
    "settings.key_placeholder": "Никогда не отображается и не записывается в журнал",
    "settings.storage": "Место хранения",
    "settings.environment": "Переменная окружения (только эта сессия)",
    "settings.keyring": "Хранилище ключей ОС",
    "settings.both": "Оба варианта",
    "settings.run_limit": "Лимит стоимости на запуск (символов)",
    "settings.save_key": "Сохранить/заменить ключ API",
    "settings.save_button": "Сохранить",
    "settings.open_log": "Открыть файл журнала…",
    "settings.session_note": "Примечание: в этой версии переменная окружения не сохраняется постоянно.",
    "settings.credentials_group": "Доступ к API",
    "settings.general_group": "Общие",
    "settings.env_override_warning": "Этот провайдер сейчас использует значение из переменной окружения, а не сохранённую здесь запись в связке ключей. Чтобы использовать сохранённый ключ, удалите эту переменную окружения на уровне операционной системы.",

    "settings.provider.tooltip": "Поставщик, чей ключ управляется ниже",
    "settings.provider.whatsthis": (
        "Определяет, к какому поставщику перевода (DeepL, Google, "
        "OpenAI, Grok) относятся статус, новый ключ и место хранения "
        "ниже. У каждого поставщика свой, отдельно сохранённый ключ."
    ),
    "settings.status.tooltip": "Откуда взят текущий используемый ключ",
    "settings.status.whatsthis": (
        "Показывает, найден ли для выбранного поставщика ключ в "
        "хранилище ключей ОС, в переменной окружения, или не найден "
        "вовсе. Переменная окружения всегда имеет приоритет над "
        "хранилищем ключей - см. предупреждение ниже, если это "
        "относится к данному случаю."
    ),
    "settings.secret.tooltip": "Новый API-ключ для выбранного поставщика",
    "settings.secret.whatsthis": (
        "Вставьте сюда API-ключ, полученный от поставщика, и нажмите "
        "«Сохранить». Во время ввода он отображается точками, но не "
        "применяется автоматически - только кнопка «Сохранить» "
        "записывает его в выбранное место хранения."
    ),
    "settings.target_field.tooltip": "Где сохраняется новый ключ",
    "settings.target_field.whatsthis": (
        "«Хранилище ключей ОС» - рекомендуемый, постоянный вариант. "
        "«Переменная окружения» действует только в течение текущего "
        "сеанса и предназначена в основном для особых случаев/отладки "
        "- см. примечание ниже. «Оба варианта» также дополнительно "
        "записывает такую переменную сеанса."
    ),
    "settings.max_chars.tooltip": "Верхний предел символов на один запуск перевода",
    "settings.max_chars.whatsthis": (
        "Запуск, содержащий больше символов, чем задано здесь, "
        "останавливается с сообщением вместо того, чтобы привести к "
        "неожиданно высоким затратам. При необходимости увеличьте "
        "значение здесь."
    ),
    "settings.save_key.tooltip": "Сохранить новый ключ",
    "settings.save_key.whatsthis": (
        "Записывает введённый выше ключ для выбранного поставщика в "
        "выбранное место хранения. Поле ввода после этого очищается, "
        "а статус выше обновляется."
    ),
    "settings.open_log.tooltip": "Открыть файл журнала приложения",
    "settings.open_log.whatsthis": (
        "Открывает текущий файл журнала в программе по умолчанию для "
        "системы - полезно для копирования сообщений об ошибках в "
        "отчёт об ошибке без создания снимка экрана."
    ),

    "hw_check.status.tooltip": "Результат последней проверки GPU",
    "hw_check.status.whatsthis": (
        "Показывает, была ли найдена поддерживаемая видеокарта NVIDIA с "
        "достаточным объёмом видеопамяти, когда была последняя проверка "
        "и поддерживает ли версия CUDA установленного драйвера "
        "локальный GPU-инпейнтинг. Без подходящей видеокарты/драйвера "
        "локальный инпейнтинг всё равно работает - просто медленнее, на "
        "процессоре (CPU)."
    ),
    "hw_check.recheck_button.tooltip": "Повторить проверку GPU сейчас",
    "hw_check.recheck_button.whatsthis": (
        "Запускает ту же проверку, что выполнял установщик - полезно "
        "после обновления драйвера или замены видеокарты, без "
        "необходимости переустанавливать приложение."
    ),

    "bootstrap.help.back_button": (
        "Назад к предыдущему шагу\n\n"
        "Всё, что уже введено на этом и предыдущем шаге, сохраняется."
    ),
    "bootstrap.help.next_button": "Перейти к следующему шагу",
    "bootstrap.help.cancel_button": (
        "Закрывает этого мастера установки\n\n"
        "Если установка сейчас выполняется, будет запрошено "
        "подтверждение. Настройку можно запустить заново в любой "
        "момент."
    ),
    "bootstrap.help.language_combo": (
        "Язык этого мастера установки\n\n"
        "Применяется сразу ко всем экранам этого мастера. У самого "
        "приложения позже будет собственный, независимый выбор языка."
    ),
    "bootstrap.help.mode_online_radio": (
        "Перевод выполняется через облачных поставщиков (DeepL, Google, "
        "OpenAI, Grok); обработка изображений здесь использует более "
        "простой метод вместо ИИ-инпейнтинга\n\n"
        "Самая быстрая и простая установка, работает на любом "
        "компьютере. Требует собственный API-ключ выбранного "
        "поставщика и подключение к интернету во время перевода."
    ),
    "bootstrap.help.mode_local_radio": (
        "Улучшенная, основанная на ИИ обработка изображений на этой "
        "видеокарте вместо более простого стандартного метода\n\n"
        "Требует поддерживаемую видеокарту NVIDIA с достаточным "
        "объёмом видеопамяти (проверяется на следующем шаге) - зато "
        "изображения никогда не покидают этот компьютер."
    ),
    "bootstrap.help.gpu_continue_local_button": (
        "Всё равно продолжить локальную установку\n\n"
        "Полезно, если проверка ошибочно завершилась неудачей или "
        "обновление драйвера ещё не выполнено - локальную обработку "
        "можно перепроверить позже через Справка -> Тест оборудования."
    ),
    "bootstrap.help.gpu_switch_online_button": (
        "Установить вместо этого онлайн-вариант\n\n"
        "Переключает эту установку на облачных поставщиков, без "
        "вопроса о видеокарте. Можно добавить позже в любой момент "
        "через настройки приложения."
    ),
    "bootstrap.help.credentials_checkbox": (
        "На следующем шаге ввести API-ключ для {provider}\n\n"
        "Неотмеченных поставщиков всегда можно добавить позже в "
        "настройках приложения."
    ),
    "bootstrap.help.credentials_skip_all_button": (
        "Продолжить, не вводя ни одного ключа\n\n"
        "Ключи всегда можно добавить позже в настройках приложения - "
        "но без хотя бы одного ключа перевод работать не будет."
    ),
    "bootstrap.help.credentials_continue_button": "Перейти к вводу ключа или к следующему поставщику",
    "bootstrap.help.credential_open_signup_button": (
        "Открывает страницу регистрации этого поставщика в браузере\n\n"
        "Там создаётся API-ключ, который затем вставляется сюда."
    ),
    "bootstrap.help.credential_key_entry": (
        "Вставьте сюда API-ключ этого поставщика\n\n"
        "Во время ввода отображается точками. Только кнопка "
        "«Сохранить» ниже действительно применяет его."
    ),
    "bootstrap.help.credential_save_button": "Сохранить введённый выше ключ сейчас",
    "bootstrap.help.finish_close_button": "Закрыть мастер установки, не запуская приложение сейчас",
    "bootstrap.help.finish_launch_button": "Закрыть мастер установки и сразу запустить приложение",
    "credentials.title": "Учётные данные",
    "credentials.saved": "Ключ API сохранён.",
    "credential.environment": "Переменная окружения (сессия)",
    "credential.keyring": "Хранилище ключей ОС",
    "credential.missing": "Не настроено",
    "provider.missing_key": "Не задан ключ API для «{provider}». <a href=\"settings\">Настроить сейчас</a>",
    "provider.missing_key_dialog": "Для поставщика «{provider}» не задан ключ API. Без ключа каждый запрос на перевод будет завершаться ошибкой.",
    "dialog.check_input": "Проверить введённые данные",
    "dialog.analysis": "Анализ",
    "dialog.choose_images": "Выбрать изображения",
    "dialog.choose_document": "Выбрать документ",
    "merge.button": "Объединить / вставить PDF…",
    "merge.title": "Объединение / вставка PDF",
    "merge.intro": "Соберите исходные файлы в нужном порядке. Для каждого файла можно необязательно указать диапазон страниц (пусто = весь файл) — чтобы вставить файл в определённое место другого файла, добавьте его несколько раз с разными диапазонами страниц.",
    "merge.column_file": "Файл",
    "merge.column_pages": "Страницы",
    "merge.pages_placeholder": "все",
    "merge.pages_tooltip": "Пусто = весь файл. Иначе, например, \"1-3,5\" или \"6-\" (страница 6 и до конца) или \"-4\" (с начала до страницы 4). \"5-3\" вставляет страницы 5,4,3 именно в этом (обратном) порядке.",
    "merge.add_files": "Добавить файлы…",
    "merge.remove_selected": "Удалить",
    "merge.move_up": "Вверх",
    "merge.move_down": "Вниз",
    "merge.sort_by_name": "Сортировать по имени",
    "merge.sort_by_date": "Сортировать по дате",
    "merge.sort_by_date_tooltip": "Сортировка по дате изменения файла на диске (дата последнего изменения, а не создания).",
    "merge.output_file_label": "Целевой файл",
    "merge.output_placeholder": "Выбрать целевой файл…",
    "merge.choose_output_file": "Сохранить как…",
    "merge.start_button": "Начать объединение",
    "merge.cancel_button": "Отмена",
    "merge.close_button": "Закрыть",
    "merge.status_running": "Обработка: {message}",
    "merge.status_done": "Готово: записано страниц {pages} из {files} файл(ов).",
    "merge.status_cancelled": "Отменено (частичный результат сохранён): записано страниц {pages}.",
    "merge.status_failed": "Сбой: {error}",
    "merge.error_dialog_choose_files": "Выбрать файлы PDF",
    "merge.error_dialog_choose_output": "Выбрать целевой файл",
    "merge.failed_title": "Ошибка объединения",
    "merge_search.button": "Искать в папке…",
    "merge_search.title": "Поиск PDF в папке",
    "merge_search.folder_label": "Папка",
    "merge_search.folder_placeholder": "Выбрать папку…",
    "merge_search.choose_folder": "Выбрать папку…",
    "merge_search.choose_folder_dialog_title": "Выбрать папку для поиска",
    "merge_search.recursive_checkbox": "Включая подпапки",
    "merge_search.scope_ico_format": "Формат ICO (область заголовка на странице 1)",
    "merge_search.scope_header": "Верхний колонтитул (все страницы)",
    "merge_search.scope_full_text": "Полный текст",
    "merge_search.scope_ico_format_tooltip": "Поиск ТОЛЬКО в блоке метаданных ICO на странице 1 (Developer, QSI ICO, дата выпуска и т. д.). Не зависит от параметра «Верхний колонтитул» ниже — если отмечен только этот параметр, повторяющаяся область заголовка на ДРУГИХ страницах поиском НЕ охватывается.",
    "merge_search.scope_header_tooltip": "Поиск ТОЛЬКО в области, повторяющейся в верхней части каждой страницы (например, строка с названием компании/логотипом). Не зависит от параметра «Формат ICO» выше — это отдельная, самостоятельная текстовая область, а не его расширение.",
    "merge_search.scope_full_text_tooltip": "Поиск по ВСЕМУ тексту на всех страницах, включая области «Формат ICO» и «Верхний колонтитул» выше.",
    "merge_search.error_missing_scope": "Выберите хотя бы одну область поиска.",
    "merge_search.date_filter_group": "Фильтр по дате",
    "merge_search.date_source_file": "Дата файла",
    "merge_search.date_source_document": "Дата в документе",
    "merge_search.date_region_ico_format": "Поле ICO (страница 1)",
    "merge_search.date_region_header": "Верхний колонтитул (все страницы)",
    "merge_search.date_region_footer": "Нижний колонтитул (все страницы)",
    "merge_search.date_format_iso": "ISO (ГГГГ-ММ-ДД)",
    "merge_search.date_format_iso_tooltip": "Распознаёт, например, «2026-09-04».",
    "merge_search.date_format_de": "Немецкий (ДД.ММ.ГГГГ)",
    "merge_search.date_format_de_tooltip": "Распознаёт, например, «04.09.2026» (а также двузначный год, например «04.09.26»).",
    "merge_search.date_format_en_month": "Английский (название месяца, например September 4, 2026)",
    "merge_search.date_format_en_month_tooltip": "Распознаёт как «September 4, 2026», так и «4 September 2026» (запятая необязательна, день из одной или двух цифр).",
    "merge_search.date_format_slash": "Через слэш (ДД/ММ/ГГГГ)",
    "merge_search.date_format_slash_tooltip": "Распознаёт, например, «04/09/2026».",
    "merge_search.date_exact_checkbox": "Точная дата",
    "merge_search.date_from_label": "С",
    "merge_search.date_to_label": "По",
    "merge_search.date_exact_label": "Дата",
    "merge_search.error_date_range_reversed": "Дата «С» не может быть позже даты «По».",
    "merge_search.error_missing_date_region": "Выберите хотя бы одну область для поиска по дате.",
    "merge_search.error_missing_date_format": "Выберите хотя бы один формат даты или укажите собственный формат.",
    "merge_search.date_custom_format_label": "Свой формат",
    "merge_search.date_custom_format_placeholder": "например, MMMM D, YYYY",
    "merge_search.date_custom_format_tooltip": "Собственный формат даты с использованием этих обозначений (вводите их всегда латиницей/по-английски, даже в этом русском диалоге) — все остальные символы, такие как пробелы, запятые, точки или слэши, ищутся буквально:\n\nYYYY — год, 4 цифры, например 2026\nYY — год, 2 цифры, например 26\nMMMM — название месяца, например September\nMMM — сокращённое название месяца, например Sep\nMM — месяц, 2 цифры, например 09\nM — месяц, 1 или 2 цифры, например 9\nDD — день, 2 цифры, например 04\nD — день, 1 или 2 цифры, например 4\n\nПримеры:\n«MMMM D, YYYY» находит «September 4, 2026»\n«MMMM DD, YYYY» находит «September 04, 2026»\n«YYYY/MM/DD» находит «2026/09/04»",
    "merge_search.error_invalid_custom_date_format": "Собственный формат даты недействителен — используйте обозначения из подсказки.",
    "merge_search.query_label": "Текст поиска (для объединения нескольких терминов используйте AND/OR или &&/||)",
    "merge_search.query_placeholder": "например, название компании застройщика, или термин1 AND термин2 — оставьте пустым для всех файлов в папке",
    "merge_search.query_tooltip": "Несколько терминов поиска можно объединять с помощью AND и OR — в том числе в сочетании друг с другом. Скобки позволяют указать, что относится друг к другу.\n\nПример: «Acme AND договор» находит только файлы, содержащие ОБА термина.\n«Acme OR Zenith» находит файлы, содержащие ХОТЯ БЫ ОДИН из двух терминов.\n\nСочетание со скобками: «StellarRussia OR (The AND Korolev AND Directive)» находит файлы с «StellarRussia» OR файлы, содержащие ВСЕ ТРИ термина «The», «Korolev» и «Directive».\n\nВместо AND/OR можно также использовать символы && и || (равнозначно, в том числе в сочетании со словами): «Acme && договор» — то же самое, что «Acme AND договор».\n\nБез AND/OR весь текст рассматривается как единый термин поиска (как и раньше). Регистр букв значения не имеет.",
    "merge_search.search_button": "Найти",
    "merge_search.cancel_button": "Отмена",
    "merge_search.select_all": "Выбрать все",
    "merge_search.select_none": "Снять выделение",
    "merge_search.detach_results_button": "Открыть список результатов в отдельном окне",
    "merge_search.reattach_results_button": "Вернуть список результатов в основное окно",
    "merge_search.results_detached_placeholder": "Список результатов открыт в отдельном окне.",
    "merge_search.detached_results_title_suffix": "Результаты",
    "merge_search.take_selected": "Добавить выбранные",
    "merge_search.close_button": "Закрыть",
    "merge_search.status_running": "Поиск: {current} ({done}/{total})",
    "merge_search.status_done": "Найдено совпадений: {matches} из {scanned} проверенных PDF-файл(ов).",
    "merge_search.status_done_with_errors": "Найдено совпадений: {matches} из {scanned} проверенных PDF-файл(ов) ({errors} не удалось прочитать).",
    "merge_search.status_cancelled": "Отменено: найдено совпадений {matches} из {scanned} проверенных PDF-файл(ов).",
    "merge_search.status_failed": "Сбой: {error}",
    "merge_search.error_missing_folder": "Сначала выберите папку.",
    "merge_search.failed_title": "Ошибка поиска",
    "merge_search.source_local": "Локальная папка",
    "merge_search.source_drive": "Google Drive",
    "merge_search.drive_folder_label": "Ссылка на папку Drive или её ID",
    "merge_search.drive_folder_placeholder": "Вставьте ссылку доступа или ID папки…",
    "merge_search.drive_resolve_button": "Проверить",
    "merge_search.drive_folder_unresolved": "Ещё не проверено.",
    "merge_search.drive_folder_resolved": "Найдена папка «{name}».",
    "merge_search.drive_folder_resolve_failed": "Сбой: {error}",
    "merge_search.drive_cache_label": "Папка кэша (загруженные файлы сохраняются здесь)",
    "merge_search.drive_choose_cache": "Выбрать папку кэша…",
    "merge_search.drive_choose_cache_dialog_title": "Выбрать папку для загруженных совпадений",
    "merge_search.drive_credentials_label": "Учётные данные Google OAuth (однократно, см. docs/google_drive_setup.md)",
    "merge_search.drive_load_from_file": "Загрузить из файла JSON…",
    "merge_search.drive_load_from_file_dialog_title": "Выбрать JSON-файл клиентских секретов из Google Cloud Console",
    "merge_search.drive_load_from_file_failed": "Не удалось прочитать файл: {error}",
    "merge_search.drive_client_id_placeholder": "ID клиента",
    "merge_search.drive_client_secret_placeholder": "Секрет клиента",
    "merge_search.drive_project_id_placeholder": "ID проекта",
    "merge_search.drive_save_credentials": "Сохранить учётные данные",
    "merge_search.drive_credentials_saved": "Учётные данные сохранены.",
    "merge_search.drive_save_failed": "Не удалось сохранить: {error}",
    "merge_search.drive_not_configured": "ID клиента/секрет клиента/ID проекта ещё не заданы.",
    "merge_search.drive_configured_not_connected": "Настроено, но соединение ещё не установлено.",
    "merge_search.drive_connected": "Подключено{account}.",
    "merge_search.drive_connect_button": "Подключиться к Google",
    "merge_search.drive_disconnect_button": "Отключить",
    "merge_search.drive_connecting": "Открытие браузера для входа…",
    "merge_search.drive_connect_failed": "Не удалось подключиться: {error}",
    "merge_search.drive_error_missing_folder": "Сначала укажите и проверьте папку Drive.",
    "merge_search.drive_error_missing_cache": "Сначала выберите папку кэша.",
    "merge_search.drive_error_not_connected": "Сначала подключитесь к Google.",
    "word_merge.button": "Объединить / вставить файлы DOCX…",
    "word_merge.title": "Объединение / вставка файлов DOCX",
    "word_merge.intro": "Соберите исходные файлы в нужном порядке — всегда целиком (в отличие от PDF, формат DOCX не имеет фиксированного числа страниц в самом файле). Чтобы вставить один и тот же файл в нескольких местах, добавьте его несколько раз. При числе файлов больше 100 объединение автоматически выполняется группами (см. строку состояния после завершения).",
    "word_merge.status_done": "Готово: обработано {segments} из {files} файл(ов){batch_suffix}{warning_suffix}.",
    "word_merge.status_cancelled": "Отменено (частичный результат сохранён): обработано файл(ов) {segments}{batch_suffix}{warning_suffix}.",
    "word_merge.status_batch_suffix": " в {batches} групп(ах)",
    "word_merge.status_warning_suffix": ", пропущено {count} (см. ниже)",
    "word_merge.warnings_title": "Пропущенные файлы:",
    "word_merge.error_dialog_choose_files": "Выбрать файлы DOCX",
    "word_merge_search.title": "Поиск файлов DOCX в папке",
    "word_merge_search.status_done": "Найдено совпадений: {matches} из {scanned} проверенных файл(ов) DOCX.",
    "word_merge_search.status_done_with_errors": "Найдено совпадений: {matches} из {scanned} проверенных файл(ов) DOCX ({errors} не удалось прочитать).",
    "word_merge_search.status_cancelled": "Отменено: найдено совпадений {matches} из {scanned} проверенных файл(ов) DOCX.",
    "bootstrap.window_title": "Настройка Document Translator",
    "bootstrap.back_button": "Назад",
    "bootstrap.next_button": "Далее",
    "bootstrap.cancel_button": "Отмена",
    "bootstrap.cancel_title": "Прервать установку?",
    "bootstrap.cancel_confirm": (
        "Мастер установки закроется, а Document Translator не будет "
        "полностью настроен. Уже созданные файлы будут удалены "
        "автоматически. Продолжить?"
    ),
    "bootstrap.cancel_confirm_installing": (
        "Установка сейчас выполняется. При прерывании уже созданные "
        "файлы будут удалены автоматически — в редких случаях файл, "
        "используемый именно в этот момент, может остаться. Всё равно "
        "прервать?"
    ),
    "bootstrap.elevated_warning_title": "Document Translator Setup - Права администратора",
    "bootstrap.elevated_warning_text": (
        "Document Translator был запущен от имени администратора.\n\n"
        "Это не требуется и приведёт к тому, что приложение позже "
        "перестанет запускаться в обычном режиме (без прав "
        "администратора).\n\n"
        "Пожалуйста, закройте это окно и запустите установку заново "
        "обычным двойным щелчком (без \"Запуск от имени "
        "администратора\").\n\n"
        "Это сообщение можно скопировать с помощью Ctrl+C."
    ),
    "bootstrap.uninstall_title": "Удалить Document Translator",
    "bootstrap.uninstall_confirm": (
        "Удалить Document Translator, включая все локально сохранённые "
        "настройки и ключи API?"
    ),
    "bootstrap.uninstall_done": "Document Translator удалён.",
    "bootstrap.welcome_title": "Добро пожаловать",
    "bootstrap.welcome_text": "Этот мастер настроит Document Translator на этом компьютере — полностью без командной строки. Он загрузит необходимые компоненты и в конце добавит запись в меню приложений.",
    "bootstrap.language_label": "Язык",
    "bootstrap.mode_title": "Онлайн или локально?",
    "bootstrap.mode_intro": "Как должен выполняться перевод? Это можно в любой момент изменить позже в настройках.",
    "bootstrap.mode_online_label": "Онлайн (облачный поставщик)",
    "bootstrap.mode_online_desc": "Перевод выполняется через внешнего поставщика (DeepL, Google, OpenAI или Grok). За это взимается плата за каждый перевод, и потребуется собственный ключ API соответствующего поставщика — подробнее об этом далее. Обработка изображений во встроенных картинках работает и здесь, только более простым способом вместо ИИ-инпейнтинга. Большая загрузка не требуется. Рекомендуется, если нет мощной видеокарты.",
    "bootstrap.mode_local_label": "Локально (на этой видеокарте)",
    "bootstrap.mode_local_desc": "Улучшает только обработку изображений: встроенный в изображения текст распознаётся с помощью OCR и после перевода перерисовывается с помощью ИИ-модели (LaMa) прямо на этой видеокарте — результат выглядит чище, чем при более простом способе, доступном и без этой опции. Сам перевод текста в обоих режимах по-прежнему выполняется через внешнего поставщика (DeepL, Google, OpenAI или Grok) по его обычным расценкам за перевод. При желании онлайн-поставщиков можно дополнительно в любое время настроить в настройках. Требуется достаточно мощная видеокарта NVIDIA (проверяется на следующем шаге), и во время установки один раз загружается около 2-3 ГБ.",
    "bootstrap.gpu_checking": "Проверка видеокарты…",
    "bootstrap.gpu_ok": "Найдено: {name} с {vram_gb:.0f} ГБ видеопамяти — этого достаточно.",
    "bootstrap.gpu_insufficient": "Найдено: {name} с {vram_gb:.0f} ГБ видеопамяти — рекомендуется не менее {min_gb:.0f} ГБ. Локальный режим, вероятно, будет работать очень медленно.",
    "bootstrap.gpu_not_found": "Поддерживаемая видеокарта NVIDIA не найдена. Локальный режим на этом компьютере практически неприменим.",
    "bootstrap.gpu_driver_too_old": "Найдено: {name}, но драйвер NVIDIA слишком старый (поддерживает только CUDA {cuda_version}, требуется не менее 11.8). Обновите видеодрайвер и запустите мастер заново, либо выберите вместо этого режим «Онлайн».",
    "bootstrap.gpu_mac_unsupported": "Локальный режим на Mac пока не поддерживается. Выберите вместо этого режим «Онлайн».",
    "bootstrap.gpu_continue_local_button": "Всё равно продолжить локально",
    "bootstrap.gpu_switch_online_button": "Переключиться на «Онлайн»",
    "bootstrap.install_title": "Установка выполняется",
    "bootstrap.install_step_venv": "Создание рабочего окружения…",
    "bootstrap.install_step_deps": "Установка компонентов ({name})…",
    "bootstrap.install_step_source": "Загрузка исходного кода программы…",
    "bootstrap.install_step_shortcut": "Добавление записи в меню приложений…",
    "bootstrap.install_failed_title": "Ошибка установки",
    "bootstrap.install_failed": "Сбой: {error}",
    "bootstrap.credentials_title": "Настройка ключей API",
    "bootstrap.credentials_intro": "Каких поставщиков вы хотите настроить? Этот шаг можно пропустить и выполнить позже в настройках приложения.",
    "bootstrap.credentials_provider_deepl": "DeepL",
    "bootstrap.credentials_provider_google": "Google Translate",
    "bootstrap.credentials_provider_openai": "OpenAI",
    "bootstrap.credentials_provider_grok": "Grok (xAI)",
    "bootstrap.credentials_explain_deepl": "Быстрая самостоятельная регистрация. Есть бесплатный лимит, далее платно.",
    "bootstrap.credentials_explain_google": "Требуется проект Google Cloud с привязанным способом оплаты — настройка немного сложнее, чем у остальных трёх поставщиков.",
    "bootstrap.credentials_explain_openai": "Быстрая самостоятельная регистрация, оплата по факту использования.",
    "bootstrap.credentials_explain_grok": "Быстрая самостоятельная регистрация, оплата по факту использования.",
    "bootstrap.credentials_open_signup_button": "Получить ключ (откроется браузер)",
    "bootstrap.open_browser_title": "Открыть браузер?",
    "bootstrap.open_browser_text": (
        "В браузере по умолчанию будет открыта следующая ссылка:\n\n"
        "{url}\n\n"
        "Проверьте, что это действительно ожидаемый адрес, прежде чем "
        "продолжить."
    ),
    "bootstrap.credentials_key_label": "Ключ API для {provider}",
    "bootstrap.credentials_key_placeholder": "Вставьте ключ…",
    "bootstrap.credentials_save_button": "Сохранить",
    "bootstrap.credentials_saved": "Сохранено.",
    "bootstrap.credentials_skip_all_button": "Позже, в настройках",
    "bootstrap.credentials_continue_button": "Далее",
    "bootstrap.finish_title": "Готово",
    "bootstrap.finish_text": "Document Translator настроен и доступен в меню приложений.",
    "bootstrap.finish_download_size": "Фактически загружено: около {size_gb:.1f} ГБ.",
    "bootstrap.finish_launch_button": "Запустить сейчас",
    "bootstrap.finish_close_button": "Закрыть",
    "mode.tooltip": "Тип документа для перевода",
    "mode.whatsthis": (
        "Определяет, какой процесс перевода используется: PDF, "
        "PowerPoint/Impress, Word/Writer или отдельные изображения. В "
        "зависимости от выбора ниже показываются только "
        "соответствующие поля, например настройки OCR - только в "
        "режиме «Изображения»."
    ),
    "source.tooltip": "Выбрать файл(ы) для перевода",
    "source.whatsthis": (
        "Открывает диалог выбора исходного файла (в режиме "
        "«Изображения» - сразу несколько файлов). Выбранное имя файла "
        "затем появляется слева."
    ),
    "source_label.tooltip": "Текущий выбранный исходный файл",
    "source_label.whatsthis": (
        "Показывает имя файла, выбранного последним через «Выбрать "
        "файл …». Если там ещё стоит «Файл не выбран», сначала нужно "
        "выбрать файл, прежде чем станет возможен анализ стоимости."
    ),
    "image_mode.tooltip": "Обработка изображений, встроенных в документ",
    "image_mode.whatsthis": (
        "«Не переводить» оставляет встроенные изображения без "
        "изменений. «Выбрать позже по отдельности» после анализа "
        "стоимости показывает список для выбора конкретных изображений. "
        "«Перевести все» автоматически обрабатывает каждое встроенное "
        "изображение."
    ),
    "provider.tooltip": "Поставщик перевода для этого запуска",
    "provider.whatsthis": (
        "DeepL, Google, OpenAI или Grok - у каждого свой API-ключ, "
        "управляемый в Настройках. Если для выбранного поставщика ключ "
        "не настроен, прямо под полем появляется подсказка со ссылкой "
        "на Настройки."
    ),
    "source_lang.tooltip": "Код исходного языка, напр. EN",
    "source_lang.whatsthis": (
        "Двухбуквенный код языка по ISO 639-1 (напр. EN для "
        "английского, FR для французского). Должен соответствовать "
        "реальному языку документа, иначе поставщик перевода вернёт "
        "неверные результаты или не вернёт их вовсе."
    ),
    "target_lang.tooltip": "Код целевого языка, напр. DE",
    "target_lang.whatsthis": (
        "Двухбуквенный код языка по ISO 639-1, на который нужно "
        "перевести (напр. DE для немецкого, ES для испанского)."
    ),
    "protected.tooltip": "Термины, которые не должны переводиться",
    "protected.whatsthis": (
        "По одному термину на строку, напр. названия компаний или "
        "продуктов. Поставщик перевода оставляет эти термины без "
        "изменений. Кнопка рядом также позволяет загрузить список из "
        "файла."
    ),
    "ocr_engine_field.tooltip": "Распознавание текста (OCR) для изображений",
    "ocr_engine_field.whatsthis": (
        "Отображается только в режиме «Изображения». Распознаёт текст "
        "на изображениях перед переводом и обратной записью. Если "
        "модуль недоступен на этом компьютере, прямо под полем "
        "появляется подсказка."
    ),
    "inpainting_backend_field.tooltip": (
        "Метод записи переведённого текста обратно в изображение"
    ),
    "inpainting_backend_field.whatsthis": (
        "Отображается только в режиме «Изображения». «Наложение "
        "прямоугольника» и «CV Inpainting» всегда работают локально, "
        "без особого оборудования. «GPU Inpainting» использует "
        "локальную видеокарту (CUDA) для лучшего результата и доступен "
        "только при установленном PyTorch с поддержкой CUDA - иначе "
        "снизу появляется подсказка. Состояние оборудования можно в "
        "любой момент проверить через Справка -> Проверка оборудования."
    ),
    "merge.tooltip": "Объединить несколько PDF-файлов",
    "merge.whatsthis": (
        "Открывает отдельный диалог для объединения нескольких "
        "PDF-файлов в один. Не зависит от формы выше - здесь ничего не "
        "переводится."
    ),
    "word_merge.tooltip": "Объединить несколько файлов Word",
    "word_merge.whatsthis": (
        "Открывает отдельный диалог для объединения нескольких файлов "
        "Word в один. Не зависит от формы выше - здесь ничего не "
        "переводится."
    ),
    "analysis.button.tooltip": "Оценить стоимость этого перевода",
    "analysis.button.whatsthis": (
        "Подсчитывает символы для перевода и оценивает примерную "
        "стоимость исходя из выбранного поставщика, пока ничего не "
        "переводя. Только после этого можно поставить галочку рядом и "
        "разблокировать «Начать»."
    ),
    "analysis.checked.tooltip": "Подтвердить оценённую стоимость",
    "analysis.checked.whatsthis": (
        "Должно быть отмечено, прежде чем «Начать» станет доступной для "
        "нажатия - осознанная мера безопасности, чтобы запуск никогда "
        "не начинался случайно без предварительного просмотра "
        "оценённой стоимости."
    ),
    "start.tooltip": "Начать перевод",
    "start.whatsthis": (
        "Становится доступной только после анализа и подтверждения "
        "стоимости. Прогресс отображается в области ниже; "
        "выполняющийся процесс можно остановить кнопкой «Отмена»."
    ),
    "job.cancel.tooltip": "Отменить выполняющийся перевод",
    "job.cancel.whatsthis": (
        "Останавливает текущий запуск как можно быстрее. Уже "
        "обработанные части не сохраняются автоматически как полный "
        "файл - в зависимости от формата может остаться неполный файл."
    ),
    "job.open_folder.tooltip": "Открыть папку с результатом",
    "job.open_folder.whatsthis": (
        "Открывает проводник в целевой папке только что завершённого "
        "запуска."
    ),
    "job.open_report.tooltip": "Открыть отчёт QA последнего запуска",
    "job.open_report.whatsthis": (
        "Показывает результаты автоматической проверки качества "
        "последнего запуска, напр. места, которые может быть стоит "
        "проверить."
    ),
    "job.correct_translation.tooltip": "Исправить отдельные переводы",
    "job.correct_translation.whatsthis": (
        "Отображается только для запусков PDF с исправляемыми "
        "текстовыми блоками. Позволяет доработать отдельные переведённые "
        "фрагменты без повторения всего запуска."
    ),
    "settings.button.tooltip": "Открыть настройки",
    "settings.button.whatsthis": (
        "API-ключи по поставщикам (рекомендуется: хранилище ключей), "
        "лимит символов на запуск и доступ к файлу журнала."
    ),
    "update_hint.tooltip": "Доступна новая версия",
    "update_hint.whatsthis": (
        "Появляется автоматически, если при запуске найдена более новая "
        "версия Document Translator. Нажатие предлагает установить новую "
        "версию."
    ),
    "flag_row.whatsthis": (
        "Немедленно и навсегда меняет язык самого интерфейса - не языки "
        "перевода в форме. Выбор сохраняется сразу же."
    ),
    "menu.help.whats_this": "Что это?",
}

CATALOGUES = {"de": DE, "en": EN, "fr": FR, "es": ES, "it": IT, "nl": NL, "fi": FI, "hr": HR, "ru": RU}
