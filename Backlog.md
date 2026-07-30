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
- [ ] insert_bbox-Fix (führende Leerzeilen wurden bei block.bbox.y0 mit eingerechnet und verschoben den eingefügten Text nach oben) wurde nur an EINEM konkreten Fall verifiziert (Virelicon-Titelzeile, Seite 0). Noch nicht geprüft: ob andere Blöcke mit führenden Leerzeilen an anderen Stellen im Dokument (nicht nur Seite 0) korrekt behandelt werden, und ob der volle 3-Provider-Test (Google/DeepL/Grok × beide PDFs, 6 Dateien) mit dem finalen Stand (Anker-Split + insert_bbox-Fix zusammen) noch aussteht.
- [ ] Beide Fixes (insert_bbox für Redaction, Underline-Erhalt) bisher nur an 1526 Virelicon.pdf verifiziert, noch nicht an 2182 INDELEGATA.pdf oder anderen PDFs gegengeprüft. Vollständiger 3-Provider-Test (Google/DeepL/Grok × beide PDFs) mit allen aktuellen Fixes steht noch aus.

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
- [x] Anker-Text-basierter Split für Seite-1-Metadaten implementiert (FIRST_PAGE_ANCHOR_TERMS = ["Issuer Address", "Asset Matrix"] in pymupdf_engine.py, _split_first_page_metadata()): trennt auf Seite 0 einen zusammenhängenden Block an der ersten Anker-Zeile in einen untranslatable Metadaten-Teil (inkl. mehrfacher Anker-Chunks, z. B. Issuer Address + Asset Matrix hintereinander) und einen translatable Teil danach. Verifiziert an 2182 INDELEGATA.pdf und 1526 Virelicon.pdf. DocumentTemplate.first_page_zones bleibt als alternativer/abwärtskompatibler Mechanismus bestehen, first_page_zones=None reicht jetzt aus.
- [x] TextBlock.insert_bbox ergänzt (pipeline/pdf/base.py): separates Feld für die beim Einfügen tatsächlich verwendete Ziel-Box, getrennt von block.bbox (das weiterhin die volle Zeilen-Union für Overlap-Checks bleibt). Behebt Bug: Blöcke mit führenden Leerzeilen (die _build_text_spans() beim HTML-Aufbau verwirft) wurden bisher zu weit oben eingefügt, da block.bbox.y0 die verworfenen Leerzeilen mit einrechnete. insert_text() nutzt jetzt insert_bbox or bbox. Verifiziert an 1526 Virelicon.pdf (Titelzeile saß vorher bei y=249, überlappte eine Trennlinie bei y=259; jetzt korrekt bei y=292.5, unterhalb der Linie).
- [x] redact_block() nutzt jetzt block.insert_bbox or block.bbox statt immer block.bbox als Redaction-Fläche (pipeline/pdf/pymupdf_engine.py). Behebt Bug: bei Blöcken mit führenden Leerzeilen wurde die weiße Redaction-Fläche zu groß gezogen und überdeckte benachbarte Vektor-Elemente (z. B. Trennlinien), obwohl diese unverändert erhalten bleiben sollten. Verifiziert an 1526 Virelicon.pdf: Trennlinie bei y≈259 bleibt jetzt exakt erhalten.
- [x] Unterstreichung (Underline) wird jetzt erfasst und übersetzt erhalten: TextSpan um underline-Feld erweitert, _build_text_spans() liest char_flags Bit 1 via TEXT_COLLECT_STYLES-Flag (page.get_text("dict", ...)) aus, spans_to_html() umschließt entsprechenden Text mit <u>...</u>. insert_htmlbox() rendert das als gezeichnete Linie unter dem Text (nicht mehr als Font-Flag) - funktional korrekt, aber anderes Kodierungsdetail als im Original, worth noting. Verifiziert an 1526 Virelicon.pdf (beide übersetzten Überschriften jetzt sichtbar unterstrichen).
- [x] LICENSE (GPL-3.0-or-later)
- [x] README.md
- [x] CONTRIBUTING.md
- [x] .gitignore
