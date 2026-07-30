# Backlog

## Geplant
- [ ] Translation-Provider implementieren (DeepL, Google, OpenAI) gemäß pipeline/translation/base.py
- [ ] Pipeline-Orchestrierung (extractor → translate → reflow → engine.write)
- [ ] PySide6/Qt-UI aufbauen
- [ ] UI-Mehrsprachigkeit via Qt Linguist (.ts/.qm-Dateien) – analog zu TME, nicht vergessen
- [ ] Bildübersetzungs-Modul (OCR + Inpainting) als separater Bereich
- [ ] PyInstaller-Bundles für Releases (später, nach stabiler Kernfunktion)
- [ ] Optional: PyPI-Package

## Zu verifizieren
- [ ] Prüfen, ob Link-Annotationen (page.get_links()) nach redact_block()/apply_redactions() auf anderen Blöcken derselben Seite technisch erhalten und weiterhin klickbar bleiben (nicht nur der Link-Text unübersetzt, sondern auch die zugrunde liegende Annotation intakt) – noch nicht getestet.
- [ ] Prüfen, ob das durch save() erzeugte PDF weiterhin durchsuchbarer Text ist (kein gerastertes/Bild-Ergebnis) – sollte durch insert_textbox() gegeben sein, aber noch nicht explizit verifiziert.

## Bekannte Einschränkungen / später prüfen
- [ ] insert_text nutzt aktuell Helvetica-Varianten (helv/hebo/heit/hebi) statt des eingebetteten Original-Fonts (block.font_name) – sinnvoller Kompromiss für den ersten Durchstich, aber bei layoutgetreuer Übersetzung kann eine abweichende Schriftart aus dem Original auffallen. Später prüfen: Font-Registrierung aus dem Original-PDF für insert_textbox.
- [ ] Zweites, seitenbreites Bild (xref=5) überlappt mit mehreren Textblöcken auf Seite 0 – vermutlich beabsichtigtes Hintergrundbild hinter Text, kein Spalten-Layout-Problem, bisher nicht untersucht. Später prüfen, ob redact_block das Hintergrundbild ungewollt betrifft.
- [ ] Bisher nur mit Platzhalter-/Original-Text getestet, noch nicht mit echten Übersetzungen aus einem Translation-Provider. Span-Text-Austausch (Original durch Übersetzung ersetzen, pro Span) ist architektonisch vorbereitet, aber noch nicht angebunden.

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
- [x] LICENSE (GPL-3.0-or-later)
- [x] README.md
- [x] CONTRIBUTING.md
- [x] .gitignore
