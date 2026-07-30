# Backlog

## Geplant
- [ ] Translation-Provider implementieren (DeepL, Google, OpenAI) gemäß pipeline/translation/base.py
- [ ] Pipeline-Orchestrierung (extractor → translate → reflow → engine.write)
- [ ] PySide6/Qt-UI aufbauen
- [ ] UI-Mehrsprachigkeit via Qt Linguist (.ts/.qm-Dateien) – analog zu TME, nicht vergessen
- [ ] Bildübersetzungs-Modul (OCR + Inpainting) als separater Bereich
- [ ] PyInstaller-Bundles für Releases (später, nach stabiler Kernfunktion)
- [ ] Optional: PyPI-Package

## Ideen / später bewerten
- [ ] Alternativer Ansatz zur Erwägung: PDF-Text in ein Word-Dokument schreiben und Words eingebaute Übersetzungsfunktion nutzen (evtl. günstiger als API-Kosten). Architektonisch grundlegend anders als der aktuelle TranslationProvider-Ansatz (würde das ganze Dokument übersetzen statt einzelne Text-Blöcke über die Pipeline) - müsste als alternativer End-to-End-Pfad evaluiert werden, nicht als weiterer Provider neben DeepL/Google/OpenAI.

## Zu verifizieren
- [ ] Prüfen, ob Link-Annotationen (page.get_links()) nach redact_block()/apply_redactions() auf anderen Blöcken derselben Seite technisch erhalten und weiterhin klickbar bleiben (nicht nur der Link-Text unübersetzt, sondern auch die zugrunde liegende Annotation intakt) – noch nicht getestet.
- [ ] Prüfen, ob das durch save() erzeugte PDF weiterhin durchsuchbarer Text ist (kein gerastertes/Bild-Ergebnis) – sollte durch insert_textbox() gegeben sein, aber noch nicht explizit verifiziert.

## Bekannte Einschränkungen / später prüfen
- [ ] insert_text nutzt aktuell Helvetica-Varianten (helv/hebo/heit/hebi) statt des eingebetteten Original-Fonts (block.font_name) – sinnvoller Kompromiss für den ersten Durchstich, aber bei layoutgetreuer Übersetzung kann eine abweichende Schriftart aus dem Original auffallen. Später prüfen: Font-Registrierung aus dem Original-PDF für insert_textbox.
- [ ] Zweites, seitenbreites Bild (xref=5) überlappt mit mehreren Textblöcken auf Seite 0 – vermutlich beabsichtigtes Hintergrundbild hinter Text, kein Spalten-Layout-Problem, bisher nicht untersucht. Später prüfen, ob redact_block das Hintergrundbild ungewollt betrifft.
- [ ] Inline-Formatierung (einzelnes fettes/kursives Wort mitten im Satz, nicht ganze Zeile) noch nicht an einem realen Beispiel verifiziert, da 2182 INDELEGATA.pdf keine solche Stelle enthält. Mechanismus (span-genaues HTML) unterstützt es strukturell, aber ungetestet. Bei Gelegenheit mit einem PDF verifizieren, das echte Inline-Hervorhebungen enthält.
- [ ] Google übersetzt HTML-Tag-Positionen nur "to the extent possible" (eigene Doku-Formulierung) - bei starker Wortumstellung zwischen Sprachen kann die Tag-Position leicht verrutschen. Bisher nur bei einfachen Fällen (ganze Zeile fett) getestet, nicht bei komplexeren Sätzen mit mehreren Inline-Formatierungen.

## Erledigt
- [x] pipeline/pdf/base.py – PdfEngine Protocol, TextBlock/ImageBlock, PageInfo
- [x] pipeline/pdf/template.py – DocumentTemplate, block_overlaps()
- [x] pipeline/pdf/pymupdf_engine.py – open, get_pages, extract_blocks, extract_images, replace_image, redact_block, insert_text, save
- [x] End-to-End-Test der kompletten PdfEngine-Pipeline (open → extract_blocks → redact_block → insert_text → save) mit Platzhaltertext, gegen echtes PDF
- [x] extract_blocks: Spalten-Split-Fix (Blöcke mit Zeilen-x0-Sprung > 50pt werden getrennt, behebt Bild-Overlap bei zweispaltigem Layout)
- [x] DocumentTemplate um first_page_zones erweitert (Zone, die nur auf Seite 1 gilt, für Metadaten-Blöcke wie Domain/Issuer Address)
- [x] Testskript tests/manual_e2e_pipeline.py nutzt jetzt ein echtes DocumentTemplate (header_bbox, footer_bbox, first_page_zones) statt ohne Template zu laufen
- [x] insert_text: Absatzgrenzen erhalten (leere/space-only Zeilen im Original markieren Absatzumbrüche und werden als Leerzeile beim Einfügen erhalten, statt mit normalen Zeilenumbrüchen zu Leerzeichen kollabiert zu werden)
- [x] Höhen-Fallback in insert_text (beide Pfade: insert_textbox und insert_htmlbox) an footer_bbox/Seitenrand gedeckelt, inkl. Fix für stillen Text-Verlust beim finalen Fallback-Versuch
- [x] TextBlock/TextSpan: span-genaue Formatierung (Absatzgrenzen + gemischte Bold/Italic-Formatierung) implementiert
- [x] insert_text nutzt insert_htmlbox für Blöcke mit spans (gemischte Formatierung), insert_textbox bleibt als Fallback für spans=[]
- [x] LINE_BREAK_MARKER eingeführt: erkennt Zeilenübergänge ohne Leerzeile (z. B. fette Überschrift direkt gefolgt von Fließtext) via Bold-Wechsel- und Satzzeichen-Heuristik, erhält Zeilenumbruch ohne zusätzlichen Absatzabstand (Unterschied zu PARAGRAPH_BREAK_MARKER)
- [x] GoogleTranslateProvider implementiert (REST-Aufruf gegen Cloud Translation API v2, Auth via API-Key als Query-Parameter, da das google-cloud-translate SDK reine API-Key-Auth nicht unterstützt), inkl. Keyring-Integration über pipeline/credentials.py, live gegen echte API getestet (tests/manual_test_google_provider.py)
- [x] pipeline/translation/cost_control.py: TranslationBudgetGuard implementiert (Kostenschätzung vor Lauf, Bestätigungsabfrage, harte Zeichen-Obergrenze pro Lauf, persistentes Monats-Nutzungs-Logging) - funktioniert als transparenter Wrapper um jeden TranslationProvider, verifiziert mit Fake-Provider
- [x] Formatierungserhaltende echte Übersetzung implementiert: spans_to_html() baut HTML aus TextSpans, GoogleTranslateProvider.translate_html() nutzt Googles format="html" (übersetzt nur Text zwischen Tags, Tag-Position bleibt erhalten), TranslationBudgetGuard.translate_html() wendet dieselbe Budget-/Logging-Logik an, insert_text() nimmt übersetztes HTML direkt entgegen. Verifiziert am realen Testfall (fette Überschrift korrekt übersetzt, Formatierung erhalten).
- [x] cost_control.py provider-abhängig gemacht: PricingModel-Dataclass, TranslationBudgetGuard nimmt pricing-Parameter entgegen, Nutzungs-Logging jetzt pro Provider getrennt (Schlüssel "{provider}:{YYYY-MM}")
- [x] DeepLProvider implementiert (REST gegen DeepL API v2, Free/Pro-Endpunkt-Erkennung via ":fx"-Key-Suffix, Sprachcode-Normalisierung Groß-/Kleinschreibung, translate() + translate_html() via tag_handling=html), live gegen die echte DeepL API getestet (tests/manual_test_deepl_provider.py) - Free/Pro-Endpunkt-Erkennung und Auto-Spracherkennung funktionieren korrekt
- [x] OpenAIProvider implementiert (Chat Completions API, DEFAULT_MODEL "gpt-5-mini" nach Verifikation auf offizieller Pricing-Seite). tests/manual_test_openai_provider.py erstellt und ausgeführt: Fehlerbehandlung greift korrekt (TranslationError bei HTTP 429), der eigentliche API-Aufruf scheitert aktuell an einer temporären Kontingent-/Billing-Sperre auf OpenAI-Seite (kein Code-Problem) - finaler Live-Test mit erfolgreicher Übersetzung steht noch aus, sobald das Konto-Kontingent wieder freigeschaltet ist
- [x] GrokProvider implementiert (xAI, OpenAI-kompatible Chat Completions API, DEFAULT_MODEL "grok-4.20-0309-non-reasoning" nach Verifikation auf docs.x.ai), live getestet gegen echte API (tests/manual_test_grok_provider.py), inkl. Hinweis: source_lang bei Auto-Erkennung liefert leeren String zurück (kein natives Source-Language-Feedback bei Chat-Completions-artigen APIs, anders als Google/DeepL)
- [x] LICENSE (GPL-3.0-or-later)
- [x] README.md
- [x] CONTRIBUTING.md
- [x] .gitignore
