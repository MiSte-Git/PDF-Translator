# Backlog

> Technisches Detailarchiv für untersuchte Einzelfälle und historische
> Implementierungsentscheidungen. Die aktuelle projektweite Priorisierung und
> Abnahmekriterien stehen in [RoadMap.md](RoadMap.md). Bei abweichender
> Priorisierung ist die Roadmap maßgeblich.

## Geplant
- [x] Realen Live-Lauf des PPTX-UI-Auftragsablaufs über das UI durchführen -
  vom Nutzer am 17.08.2026 selbst ausgeführt und als unauffällig bestätigt
  (mit Google statt DeepL, siehe RoadMap.md Phase 1). PPTX-Teil des
  ursprünglichen Hauptfokus damit abgeschlossen.
- [x] DOCX über denselben Auftragsablauf (ui/pptx_job.py als Vorlage)
  angebunden - siehe "Erledigt" unten für Details. Noch offen: ein echter
  Live-Lauf gegen ein reales Dokument über das UI (bisher nur automatisiert
  mit Fake-Provider gegen die neue Fixture getestet).
- [x] Explizite "ICO-Dokument"-Option im UI ergänzt (17.08.2026, nur
  Word-Modus) - siehe "Erledigt" unten für Details. PDF-Gegenstück bewusst
  noch offen, da der direkte PDF-Pfad insgesamt noch nicht ans UI
  angebunden ist (RoadMap.md Phase 2/PDF).
- [x] Duplikat-Text-Bug im Redact/Insert-Pfad reproduziert und Fix
  verifiziert (17.08.2026) - siehe "Erledigt" unten für Details.
- [x] Direkten PDF-Pfad über dasselbe Auftragsmodell wie PPTX/Word
  angebunden (17.08.2026, ui/pdf_job.py als Vorlage: ui/word_job.py) -
  siehe "Erledigt" unten für Details. Noch offen: ein echter Live-Lauf
  gegen ein reales PDF über das UI (bisher nur automatisiert mit
  Fake-Provider gegen die neue Fixture getestet), sowie die produktive
  Entscheidung/Dokumentation, WANN der direkte PDF-Pfad statt eines
  vorhandenen Word-Originals eingesetzt wird (RoadMap.md Phase 2/PDF) -
  das ist eine Priorisierungs-/Prozessfrage für den Batch-Betrieb
  (ico_translate/), nicht für die interaktive Desktop-UI, wo der Nutzer
  den Modus ohnehin manuell pro Datei wählt.
- [x] Die im PDF-Abschnitt von RoadMap.md Phase 2/PDF offenen Detailfragen
  (Link-Annotationen nach Redaction, Durchsuchbarkeit/Copy-Paste-Qualität,
  Leerzeilen/Underline/Inline-Formatierung, Glyphen-Verlust + Font-Erhalt,
  fi-Ligatur, Redaction über Hintergrundbildern/überlagerten Blöcken) der
  Reihe nach untersucht (17.08.2026) - siehe "Erledigt" unten für Details.
  Vier reale Bugs behoben, zwei Punkte als in Ordnung verifiziert, ein
  Punkt (fi-Ligatur) als aktuell nicht sinnvoll behebbar dokumentiert, ein
  Punkt (Font-Erhalt) als offene Architekturentscheidung bestätigt. **Der
  Strukturteil des neuen Hauptfokus ist erledigt** (17.08.2026, siehe
  "Erledigt" unten: voller Lauf gegen die echte "1526 VIRELICON.pdf" mit
  Platzhaltertext, 0 Fehler) - **offen bleibt nur noch der eigentliche
  Übersetzungsschritt mit einem echten Provider** (DeepL/Google/OpenAI/
  Grok), da in dieser Cloud-Sitzung keine API-Zugangsdaten hinterlegt
  sind. Entscheidung (17.08.2026): dieser Schritt läuft, wie zuvor beim
  PPTX-Live-Lauf, vom Nutzer selbst über die lokale Desktop-UI (dort
  bereits mit Zugangsdaten eingerichtet), nicht mit einem in die
  Cloud-Sitzung eingegebenen API-Key. Ursprünglicher Hauptfokus-Rahmen
  weiterhin gültig: ein echter
  Live-Lauf gegen ein reales PDF-Dokument über einen echten Provider
  (analog zum PPTX-Live-Lauf) - keine der obigen
  Detailfragen blockiert das mehr. Details und Reihenfolge:
  [RoadMap.md](RoadMap.md).
- [x] **Word-Grundpfad:** Umstieg auf Word-basierte Übersetzung wurde umgesetzt,
  da der direkte PDF-Redact/Insert-Pfad weiterhin einen offenen
  Duplikat-Text-Bug hat und für 2191/2196 PDFs Word-Originale existieren. Die
  Struktur-Analyse an 6 Dokumenten (1526 Virelicon + 5 Stichproben: 2210
  INERTIARA, 2181 ARCTHRESHOLD, 2173 NULLARISLOOM, 2156 FRICTURA, 2130
  SOMAGRAMMA) wurde generisch bestätigt:
  - Header (header2.xml, aktiv) / Footer (footer1.xml) identisch auf jeder Seite, PAGE-Feld für Seitenzahl
  - Metadatenblock Seite 1 variabler Länge, zuverlässig begrenzt durch straightConnector1-Trennstrich-Shape (mc:AlternateContent) statt fixer Absatzzahl
  - Ersetzungslogik muss auf Run-Ebene arbeiten (Bilder stehen teils im selben Absatz wie übersetzbarer Text)
  - Protected-Terms-Prüfung (Entwicklername, ICO-Name, "QSI") muss auch innerhalb von `<w:hyperlink>`-Runs greifen, nicht nur in normalem Fließtext
  - Word-Lese-/Schreib-Pfad ist seitdem fertig implementiert, siehe "Erledigt" unten
- [ ] Optionalen Export übersetzter Word-Dokumente nach PDF implementieren und
  getrennt vom verlustarmen DOCX-Writeback prüfen.
- [x] Duplikat-Quellenregel für Stapelverarbeitung umsetzen: bei den 7 "(LS)"-Paaren (HARMONICJ, MNEMOSYNE, CONTINUUM, AXIOMCRADLE, WOUNDS, ONEPERCENT, SILENCE) Standardversion als Quelle verwenden, außer bei **MNEMOSYNE** → dort (LS)-Version (enthält ~35 zusätzliche Absätze, die die Standardversion nicht hat; die übrigen 6 Paare sind inhaltlich identisch, nur XML-Formatierungsartefakte als Unterschied) - umgesetzt über ico_translate/source_manifest.json (siehe "Erledigt" unten), nicht über eine hartkodierte Regel im Code.
- [x] Translation-Provider DeepL, Google, OpenAI und Grok gemäß
  pipeline/translation/base.py implementieren.
- [x] Pipeline-Orchestrierung für den Word-Pfad als ico_translate/batch.py
  umgesetzt; der direkte PDF-Pfad bleibt bis zur Klärung seiner offenen
  Qualitätsbefunde eingeschränkt.
- [x] PySide6/Qt-UI-Grundgerüst mit expliziter Moduswahl, Dokumentanalyse,
  Kostenübersicht und Einstellungsdialog aufgebaut.
- [ ] UI vollständig übersetzungsfähig machen: PPTX, DOCX, PDF und Bilder an
  den gemeinsamen Start-/Fortschritts-/Abbruchablauf anbinden.
- [x] UI-Mehrsprachigkeitsbasis mit deutschen und englischen Python-Katalogen
  und Umschaltung ohne Neustart umgesetzt; Französisch, Spanisch, Italienisch,
  Niederländisch, Finnisch, Kroatisch und Russisch sind vorbereitet.
- [ ] Weitere UI-Sprachkataloge befüllen und später bewerten, ob eine Migration
  auf Qt Linguist (`.ts`/`.qm`) gegenüber den bestehenden Python-Katalogen
  sinnvoll ist.
- [x] PPTX-OOXML-Grundengine mit verlustarmem Roundtrip, minimalem
  `<a:t>`-Writeback, Format-Inventar, Footer-Schutz und Überlauferkennung
  umgesetzt.
- [ ] PPTX-Live-Übersetzung produktiv im UI verdrahten und anschließend nicht
  unterstützte Inhalte (SmartArt, Charts, Notizen, Master/Layout, OLE und
  Bildtext) schrittweise katalogisieren beziehungsweise freigeben.
- [ ] Bildübersetzungs-Modul (OCR + Inpainting) als separater Bereich
- [ ] PyInstaller-Bundles für Releases (später, nach stabiler Kernfunktion)
- [ ] Optional: PyPI-Package

## Ideen / später bewerten

- Einheitliches Plugin-/Adaptermodell für weitere Dokumenttypen erst nach dem
  stabilen gemeinsamen Auftragsmodell bewerten.
- Automatische Layoutänderungen nur als separate, explizit aktivierte Phase mit
  Vorher-/Nachher-QA untersuchen.
- Deployment-Lösung (18.08.2026, Michael): installierbare/Standalone-Version
  für Linux/Windows/macOS gewünscht, dazu eine Tablet-taugliche Version für
  iPadOS - explizit erst als Diskussion, keine Umsetzung. Zentrale Spannung:
  gewünschte Größe "keine hunderte MB, erst recht keine GB" steht im
  Widerspruch zu GPU-Inpainting (PyTorch, mehrere hundert MB bis GB) und dem
  Tesseract-Sprachpaket-Bedarf; iPadOS hat keinen realistischen nativen Pfad
  für den aktuellen PySide6/Tesseract-Stack. Noch offen/ungeklärt: Web-App
  (Python-Pipeline bleibt, neues dünnes Frontend, würde iPad "gratis"
  mitlösen und die Größenfrage clientseitig auflösen, braucht aber Hosting/
  andere Zugangsdaten-Architektur) vs. native Installer (PyInstaller/
  Briefcase o. ä., überschaubarer Aufwand, aber iPad bleibt ungelöst und
  GPU-Backend muss aus dem Basis-Paket ausgeschlossen werden) vs. Hybrid.

  **Entscheidung (18.08.2026, Michael):** native Installer/Standalone-Route,
  keine Web-App (iPad damit vorerst zurückgestellt). Schwere/optionale
  Abhängigkeiten (Tesseract, PyTorch fürs GPU-Backend) sollen NICHT im
  Installer mitgeliefert, sondern bei Bedarf vor Ort separat installiert
  werden - genau das Muster, das requirements-gpu.txt für GPU-Inpainting
  schon heute vorsieht, jetzt auch für die Standalone-Distribution gedacht.
  Wichtige praktische Einschränkung, noch mit Michael zu klären: PyInstaller/
  Briefcase bauen NICHT plattformübergreifend - ein Windows-Installer muss
  auf echtem Windows gebaut werden, ein macOS-Installer auf echtem macOS;
  aus dieser (Linux-)Sandbox lässt sich verlässlich nur der Linux-Build
  erstellen/testen. Noch offen: ob Michael die Windows/macOS-Builds selbst
  auf seinen Geräten ausführt, oder ob langfristig eine CI-Pipeline
  (z. B. GitHub Actions mit Runnern je Betriebssystem) das übernehmen soll.
  Umsetzung noch nicht begonnen.

## Zu verifizieren
- [ ] Word-Pfad: PAGE-Feld in footer1.xml sollte sich bei Neuberechnung automatisch aktualisieren, auch wenn das übersetzte Dokument länger wird als das Original - noch nicht an einem tatsächlich länger werdenden Dokument verifiziert (Word aktualisiert Felder nicht immer automatisch beim programmatischen Schreiben, ggf. muss ein Feld-Update erzwungen werden)
- [x] Prüfen, ob Link-Annotationen (page.get_links()) nach redact_block()/apply_redactions() auf anderen Blöcken derselben Seite technisch erhalten und weiterhin klickbar bleiben (nicht nur der Link-Text unübersetzt, sondern auch die zugrunde liegende Annotation intakt) – war tatsächlich ein realer Bug, jetzt behoben, siehe "Erledigt" unten (17.08.2026, Punkt 1).
- [x] Prüfen, ob das durch save() erzeugte PDF weiterhin durchsuchbarer Text ist (kein gerastertes/Bild-Ergebnis) – bestätigt in Ordnung, mit einer Ausnahme (fi-Ligatur), siehe "Erledigt" unten (17.08.2026, Punkte 2 und 5).
- [ ] insert_bbox-Fix (führende Leerzeilen wurden bei block.bbox.y0 mit eingerechnet und verschoben den eingefügten Text nach oben) wurde nur an EINEM konkreten Fall verifiziert (Virelicon-Titelzeile, Seite 0). Noch nicht geprüft: ob andere Blöcke mit führenden Leerzeilen an anderen Stellen im Dokument (nicht nur Seite 0) korrekt behandelt werden, und ob der volle 3-Provider-Test (Google/DeepL/Grok × beide PDFs, 6 Dateien) mit dem finalen Stand (Anker-Split + insert_bbox-Fix zusammen) noch aussteht.
- [ ] Beide Fixes (insert_bbox für Redaction, Underline-Erhalt) bisher nur an 1526 Virelicon.pdf verifiziert, noch nicht an 2182 INDELEGATA.pdf oder anderen PDFs gegengeprüft. Vollständiger 3-Provider-Test (Google/DeepL/Grok × beide PDFs) mit allen aktuellen Fixes steht noch aus.
- [x] Gemeldeter Bug "Highlight-Fläche im Output-PDF vom Text losgelöst/falsch positioniert" (ursprünglich mit echter DeepL-Übersetzung auf 3 von 34 highlighted Sub-Blöcken bestätigt, Seite 1/5/6) ist behoben, in zwei Teilen (pipeline/pdf/pymupdf_engine.py):
  1. _line_is_highlighted()/_associated_highlight_extent() nutzen jetzt _HIGHLIGHT_LINE_TOLERANCE=1.5pt (Mindest-Overlap-Höhe statt reiner `>0`-Überlappung), behebt die Fehlklassifizierung von Attributionszeilen, die nur hauchdünn (<0.01pt) an ein Highlight-Rechteck grenzen. Erneuter Lauf von tests/manual_diagnose_highlight_pages_real.py: alle 3 bekannten Versatz-Fälle verschwunden (0 Versatz auf allen 7 Seiten), Blockzahl steigt wie erwartet (mehr, feiner geschnittene Sub-Blöcke, z. B. Seite 2: 11→22).
  2. Neu: _grow_highlight_if_needed() (aufgerufen aus insert_text()) erkennt, wenn der tatsächlich eingefügte Text eines highlighted Blocks höher (oder breiter, falls auch Width-Widen griff) wird als das Original-Highlight-Rechteck, und zeichnet per page.draw_rect() eine neue, größere Fläche in _HIGHLIGHT_FILL_COLOR VOR dem erneuten Text-Insert (Ablauf: Text einmal einfügen zum Messen → falls zu groß: weiß redigieren → größere Fläche zeichnen → Text erneut einfügen). Mit echten DeepL-Übersetzungen (Seiten 0-6) kam dieser Pfad nicht zum Tragen (keine Seite brauchte echtes Wachstum), aber gezielt mit einem 7x überlangen Platzhalter erzwungen und per Screenshot (tests/output/highlight_growth_test.png) visuell verifiziert: Fläche wächst korrekt in Höhe UND Breite, Text bleibt vollständig lesbar über der Fläche, keine weißen Lücken, ursprüngliche Rechtecke anderer Blöcke bleiben unangetastet (29/29 erhalten).
- [ ] Neu entdeckt (tests/manual_diagnose_highlight_pages.py, Seite 5): Ein Bullet-Symbol im Original (Private-Use-Area-Codepoint U+F086, ähnlich Wingdings) hat im Sans-Serif-Fallback-Font von insert_htmlbox()/insert_textbox() kein Glyph und wird im Output als fehlendes Zeichen (NUL/Tofu) statt des Original-Symbols dargestellt. Unabhängig vom Highlight-Bug, noch nicht behoben. Ein andersartiger, aber verwandter Glyphen-Verlust (reine Unicode-Zeichen aus nicht-lateinischen Schriften im reinen Textpfad) wurde am 17.08.2026 gefunden und behoben, siehe "Erledigt" unten (Punkt 4) - dieser Symbol-/PUA-Font-Fall bleibt davon unberührt offen.
- [x] Neu entdeckt (tests/manual_diagnose_highlight_pages.py): insert_htmlbox() ersetzt "fi" durch die Ligatur "ﬁ" (U+FB01) im gerenderten Output-Text - rein kosmetisch/Font-Rendering, aber macht exakte Substring-Suche (Textsuche, Copy-Paste-Vergleich) nach Wörtern mit "fi" im fertigen PDF unzuverlässig. Kontrollierbarkeit geprüft (17.08.2026) - vier Gegenmaßnahmen versucht, keine hat funktioniert, siehe "Erledigt" unten (Punkt 5) für Details und Bewertung als aktuell nicht sinnvoll behebbar.
- [x] Behoben: Kollisionsschutz (vorher nur block.highlighted==True) gilt jetzt für ALLE Blöcke, plus automatisches Anomalie-Logging (pipeline/pdf/pymupdf_engine.py):
  1. _insert_html_text()/_insert_plain_text() nutzen jetzt einheitlich EINE Wachstumslogik (try_grow(): Höhe in Ein-Zeilen-Schritten via _estimate_line_height(), dann Breite, beides kollisionssicher) für jeden Block, nicht mehr nur für highlighted - die alte Breite-zuerst-Verdopplungslogik für nicht-highlighted Blöcke wurde komplett entfernt (Code dadurch auch kürzer: nur noch eine try_grow()-Closure statt zwei Varianten je Funktion). _collision_aware_max_y1() wird jetzt unconditional in insert_text() aufgerufen. Grund für die ursprüngliche Beschränkung auf highlighted (die farbige Fläche wächst ohnehin mit, kein Spaltenbreiten-Konflikt) im Docstring festgehalten, aber das eigentliche Kollisionsrisiko (Hineinwachsen in den nächsten Block) ist unabhängig davon real - siehe tests/manual_diagnose_text_duplication.py.
  2. Neu: log_growth_anomaly()/PyMuPdfEngine._log_growth_anomalies() schreiben strukturierte JSONL-Einträge nach tests/output/growth_anomalies.jsonl (Seite, bbox, Blocktext gekürzt, Ereignistyp, relevante Zahlen) bei drei Ereignissen: Kollisionskappung (nur wenn tatsächlich gewachsen wurde - erster Versuch hatte hier einen False-Positive-Bug, der Blöcke meldete, die nie wuchsen, aber zufällig schon nah an der Kollisionsgrenze lagen; behoben durch Vergleich gegen einen vor dem Insert-Versuch genommenen original_rect-Snapshot statt block.bbox), finale Schriftgröße ≤8pt UND kleiner als die Original-Schriftgröße (verhindert Fehlalarm bei Dokumenten mit von Haus aus kleiner Schrift), finale Höhe >2x Original-bbox-Höhe. Läuft als Teil der normalen Pipeline (insert_text()), nicht nur in Testskripten.
  3. Verifiziert: der bekannte Kollisionsfall (Seite 4/Index, erzwungener langer Text) wächst jetzt korrekt nur bis zur Grenze (Text endet bei y=715.5, Nachbarblock beginnt bei y=718.5) statt hineinzuragen, mit passenden Log-Einträgen (growth_capped_by_collision + small_final_font). Echte DeepL-Übersetzung auf allen 14 Seiten von 1526 Virelicon.pdf: 91 Blöcke, 0 Fehler, 26 growth_capped_by_collision + 2 excessive_height_growth + 27 small_final_font-Einträge, alle stichprobenartig als plausibel bestätigt (kurze highlighted Ein-Zeiler/Attributionszeilen dicht vor dem nächsten Block). Regressionscheck 2182 INDELEGATA.pdf (kein Highlight-Feature): nur 1 Anomalie-Eintrag (ein großer Absatz, der leicht wächst und nahe am Seitenende/nächsten Block gekappt wird) - kein False Positive. Zwei volle 14-Seiten/6-Block-Platzhaltertext-Regressionsläufe (beide PDFs): 0 neue Abstürze.
- [x] Zwei gezielte Fixes für die in tests/output/manual_diagnose_highlight_regression_output.txt gefundenen Probleme (schmale weiße Lücke im Highlight-Band, zu kleine Schrift), beide in pipeline/pdf/pymupdf_engine.py:
  1. redact_block() redigiert bei block.highlighted==True jetzt in der vollen Breite der zugehörigen Original-Highlight-Rechtecke (_associated_highlight_extent()), nicht mehr nur in der (oft sehr schmalen) Block-bbox-Breite - behebt den "Text auf weißem Fleck, umgeben von ungenutztem Blau" Effekt.
  2. _insert_html_text()/_insert_plain_text() versuchen bei highlighted Blöcken jetzt Flächen-Wachstum VOR Schriftverkleinerung (neue try_grow_height_first()-Helfer in beiden) - vorher fielen kurze Ein-Zeilen-Blöcke (z. B. "Ra", "Vater") sofort auf 6pt (_MIN_FONT_SIZE), obwohl Wachstum die bessere Lösung gewesen wäre. Wichtige Erkenntnis dabei: Höhen-Wachstum muss VOR Breiten-Wachstum versucht werden (nicht wie beim alten, weiterhin für nicht-highlighted Blöcke genutzten try_grow()) - sonst bläht ein reines Höhen-Defizit (z. B. bei einem einzelnen kurzen Wort wie "Ra") die Box unnötig bis zum Seitenrand in der Breite auf, bevor Höhenwachstum überhaupt versucht wird. _grow_highlight_if_needed()s Breitenberechnung nutzt jetzt ebenfalls original_extent (nicht mehr nur block.bbox) als Basis, sonst reproduzierte sie denselben Schmal-Fehler erneut. Verifiziert mit echter DeepL-Übersetzung (tests/manual_verify_highlight_fixes.py) an Seite 3 (page_index 2): Highlight-Fläche und Text stimmen jetzt überein (Screenshots tests/output/verify_zoom_*.png), 9/12 highlighted Blöcke bleiben bei voller 11pt-Schriftgröße (vorher 6/13 auf dem 6pt-Boden).
  3. [x] Behoben: Das grobe Verdopplungs-Wachstum (28.9pt → 88.9pt für nur eine zusätzliche Zeile) und die fehlende Kollisionsprüfung gegen den nächsten Block wurden gefixt (pipeline/pdf/pymupdf_engine.py):
     - _insert_html_text()s try_grow_height_first() wächst jetzt in festen Ein-Zeilen-Schritten (neue _estimate_line_height(): block.bbox-Höhe / eigene Zeilenzahl, d. h. direkt aus dem Dokument abgeleitet statt geraten - für die üblichen highlighted Ein-Zeiler ist das schlicht die eigene bbox-Höhe, ~13-15pt in diesem Dokument bei 11pt Schrift) statt in Verdopplungsschritten (_insert_plain_text()s Pendant brauchte das nicht, da insert_textbox() bereits ein exaktes Deficit liefert).
     - Neue _next_block_y0()/PyMuPdfEngine._collision_aware_max_y1(): ermittelt aus der bereits von extract_blocks() gecachten Original-Blockliste der Seite (neuer self._page_blocks_cache) den nächstgelegenen Block darunter in derselben Spalte (x-Overlap) und kappt das Wachstums-Maximum (max_y1) _HIGHLIGHT_COLLISION_MARGIN=3pt davor. insert_text() nutzt das jetzt für highlighted Blöcke statt des reinen Footer-/Seitenrand-Caps; nicht-highlighted Blöcke unverändert.
     - Verifiziert (tests/manual_verify_highlight_fixes.py) am genau diesem Fall (Seite 3/page_index 2, Block "This One Light concept...", nur 1.9pt Abstand zum nächsten Block "- PQ to Ivan"): wächst jetzt gar nicht mehr (Kappung bei ~0pt verfügbarem Raum), fällt stattdessen korrekt auf Schriftverkleinerung zurück (8pt statt Kollision). Programmatischer Check über alle 12 highlighted Blöcke auf der Seite: 0 Kollisionen mit dem jeweils nächsten Block. Regressionslauf über alle 14 Seiten mit Platzhaltertext: keine neuen Abstürze.

## Bekannte Einschränkungen / später prüfen
- [ ] Word-Pfad: DeepL verschiebt an vereinzelten `<br/>`-Grenzen Textinhalt oder verschmilzt zwei durch `<br/><br/>` getrennte Fragmente zu einem durchgehenden Satz (Gesamt-Break-Anzahl bleibt dabei gleich, nur die Position/Zuordnung ändert sich) - führt zu einzelnen fehlenden Leerzeichen an Satzgrenzen (z. B. "...hatInertiara – das lässt..."). Der proaktive §§SP§§-Marker behebt den Fall "Leerzeichen an stabiler Break-Grenze verloren" zuverlässig, aber nicht diesen Verschmelzungsfall - eine zuverlässige Erkennung bräuchte einen Adjazenz-Abgleich (welche Wortpaare vorher durch einen Break getrennt waren), was als unscharfe Heuristik mit hohem Fehlerpotenzial bewusst nicht umgesetzt wurde. `html_to_paragraph()` loggt abweichende Break-Gesamtzahlen (echte Verschmelzungen mit Zahlenreduktion) nach tests/output/word_break_anomalies.jsonl, erfasst aber reine Verschiebungen ohne Zahlenänderung nicht. Rein kosmetisch, keine Struktur-/Marker-Beschädigung.
- [ ] Word-Pfad: footer1.xml wickelt seinen Inhalt in ein `<w:sdt>` (Content Control) statt direkter `<w:p>`-Kinder - get_header_footer_paragraphs() liefert für den Footer daher aktuell einen leeren Absatz (Text nicht sichtbar). Für die bisherige Aufgabe folgenlos, da der Footer ohnehin unangetastet bleibt, aber relevant, falls Footer-Inhalt (z. B. für die PAGE-Feld-Verifikation) später gelesen/verändert werden muss.
- [ ] Google Cloud Translation API v2 (GoogleTranslateProvider) hat keinen Formality-Parameter - anders als DeepL (formality="less") kann bei Google die informelle Du-Form nicht technisch erzwungen werden. Für Google-Übersetzungen bleibt das Registerergebnis (Du/Sie) dem Modell/der API überlassen und ist nicht kontrollierbar.
- [ ] insert_text nutzt aktuell Helvetica-Varianten (helv/hebo/heit/hebi) statt des eingebetteten Original-Fonts (block.font_name) – sinnvoller Kompromiss für den ersten Durchstich, aber bei layoutgetreuer Übersetzung kann eine abweichende Schriftart aus dem Original auffallen. Später prüfen: Font-Registrierung aus dem Original-PDF für insert_textbox. Erneut bestätigt (17.08.2026, siehe "Erledigt" unten Punkt 4) - weiterhin offene Architekturentscheidung, kein neuer Befund. Der davon unabhängige, ECHTE Datenverlust bei nicht-lateinischen Schriften im reinen Textpfad wurde im Zuge dieser Prüfung gefunden und behoben.
- [x] Zweites, seitenbreites Bild (xref=5) überlappt mit mehreren Textblöcken auf Seite 0 – vermutlich beabsichtigtes Hintergrundbild hinter Text, kein Spalten-Layout-Problem, bisher nicht untersucht. Später prüfen, ob redact_block das Hintergrundbild ungewollt betrifft. Geprüft (17.08.2026, siehe "Erledigt" unten Punkt 6) - unbedenklich: apply_redactions() blankt nur den redigierten Ausschnitt, Bild und Rest bleiben erhalten.
- [ ] Inline-Formatierung (einzelnes fettes/kursives Wort mitten im Satz, nicht ganze Zeile) noch nicht an einem realen Beispiel verifiziert, da 2182 INDELEGATA.pdf keine solche Stelle enthält. Mechanismus (span-genaues HTML) unterstützt es strukturell, aber ungetestet. Bei Gelegenheit mit einem PDF verifizieren, das echte Inline-Hervorhebungen enthält. Synthetisch verifiziert (17.08.2026, siehe "Erledigt" unten Punkt 3, tests/test_pdf_formatting_roundtrip.py) - der Vorbehalt "an einem realen Beispiel" bleibt bestehen.
- [ ] Google übersetzt HTML-Tag-Positionen nur "to the extent possible" (eigene Doku-Formulierung) - bei starker Wortumstellung zwischen Sprachen kann die Tag-Position leicht verrutschen. Bisher nur bei einfachen Fällen (ganze Zeile fett) getestet, nicht bei komplexeren Sätzen mit mehreren Inline-Formatierungen.
- [ ] Attributionszeile ohne eigenes Highlight-Rechteck (z. B. wenn ihr Rechteck knapp davor endet) landet beim nicht-highlighted Sub-Block statt beim zugehörigen Zitat - akzeptierte Einschränkung von _split_by_highlight() (pipeline/pdf/pymupdf_engine.py), nicht gelöst.

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
- [x] OpenAIProvider über die Chat-Completions-API implementiert; aktuelles
  `DEFAULT_MODEL` ist `gpt-5.6-terra`. Fehlerbehandlung und modellabhängiger
  Temperature-Parameter sind mit gemockten Requests geprüft. Ein erfolgreicher
  aktueller Live-Test bleibt abhängig vom verfügbaren Konto-Kontingent.
- [x] GrokProvider implementiert (xAI, OpenAI-kompatible Chat Completions API, DEFAULT_MODEL "grok-4.20-0309-non-reasoning" nach Verifikation auf docs.x.ai), live getestet gegen echte API (tests/manual_test_grok_provider.py), inkl. Hinweis: source_lang bei Auto-Erkennung liefert leeren String zurück (kein natives Source-Language-Feedback bei Chat-Completions-artigen APIs, anders als Google/DeepL)
- [x] Anker-Text-basierter Split für Seite-1-Metadaten implementiert (FIRST_PAGE_ANCHOR_TERMS = ["Issuer Address", "Asset Matrix"] in pymupdf_engine.py, _split_first_page_metadata()): trennt auf Seite 0 einen zusammenhängenden Block an der ersten Anker-Zeile in einen untranslatable Metadaten-Teil (inkl. mehrfacher Anker-Chunks, z. B. Issuer Address + Asset Matrix hintereinander) und einen translatable Teil danach. Verifiziert an 2182 INDELEGATA.pdf und 1526 Virelicon.pdf. DocumentTemplate.first_page_zones bleibt als alternativer/abwärtskompatibler Mechanismus bestehen, first_page_zones=None reicht jetzt aus.
- [x] TextBlock.insert_bbox ergänzt (pipeline/pdf/base.py): separates Feld für die beim Einfügen tatsächlich verwendete Ziel-Box, getrennt von block.bbox (das weiterhin die volle Zeilen-Union für Overlap-Checks bleibt). Behebt Bug: Blöcke mit führenden Leerzeilen (die _build_text_spans() beim HTML-Aufbau verwirft) wurden bisher zu weit oben eingefügt, da block.bbox.y0 die verworfenen Leerzeilen mit einrechnete. insert_text() nutzt jetzt insert_bbox or bbox. Verifiziert an 1526 Virelicon.pdf (Titelzeile saß vorher bei y=249, überlappte eine Trennlinie bei y=259; jetzt korrekt bei y=292.5, unterhalb der Linie).
- [x] redact_block() nutzt jetzt block.insert_bbox or block.bbox statt immer block.bbox als Redaction-Fläche (pipeline/pdf/pymupdf_engine.py). Behebt Bug: bei Blöcken mit führenden Leerzeilen wurde die weiße Redaction-Fläche zu groß gezogen und überdeckte benachbarte Vektor-Elemente (z. B. Trennlinien), obwohl diese unverändert erhalten bleiben sollten. Verifiziert an 1526 Virelicon.pdf: Trennlinie bei y≈259 bleibt jetzt exakt erhalten.
- [x] Unterstreichung (Underline) wird jetzt erfasst und übersetzt erhalten: TextSpan um underline-Feld erweitert, _build_text_spans() liest char_flags Bit 1 via TEXT_COLLECT_STYLES-Flag (page.get_text("dict", ...)) aus, spans_to_html() umschließt entsprechenden Text mit <u>...</u>. insert_htmlbox() rendert das als gezeichnete Linie unter dem Text (nicht mehr als Font-Flag) - funktional korrekt, aber anderes Kodierungsdetail als im Original, worth noting. Verifiziert an 1526 Virelicon.pdf (beide übersetzten Überschriften jetzt sichtbar unterstrichen).
- [x] pipeline/translation/protected_terms.py: derive_protected_term() (leitet aus einem Dateinamen wie "1526 VIRELICON.pdf" den zu schützenden Begriff ab, z. B. "VIRELICON") sowie protect_terms()/restore_terms() (ersetzen Begriffe case-insensitiv an Wortgrenzen durch §§N§§-Platzhalter vor der Übersetzung und stellen die ursprünglich gefundene Schreibweise danach wieder her, auch innerhalb von HTML-Tags). In allen vier Providern (Google/DeepL/OpenAI/Grok) an translate_html() als optionaler protected_terms-Parameter angebunden (Default None, abwärtskompatibel). Getestet mit tests/manual_test_protected_terms.py.
- [x] Du-Form (informelle Anrede) für Übersetzungen: DeepLProvider setzt formality="less" in translate()/translate_html(), aber nur für Zielsprachen aus der bekannten Formality-Unterstützungsliste (_FORMALITY_SUPPORTED_TARGET_LANGS), sonst wird der Parameter weggelassen. OpenAIProvider/GrokProvider bekommen eine explizite Anweisung im System-Prompt (Du/Sie, tu/vous, tú/usted etc. - immer informell), promptbasiert statt API-erzwungen. GoogleTranslateProvider kann das technisch nicht (siehe Bekannte Einschränkungen).
- [x] Highlighted Zitat-Blöcke (hellblauer Hintergrund, fill=rgb(0.871, 0.918, 0.965)) werden in extract_blocks() jetzt anhand der Drawing-Füllfarbe automatisch erkannt und in eigene Sub-Blöcke gesplittet: _get_highlight_rects() sammelt die passenden gefüllten Rechtecke pro Seite, _line_is_highlighted() prüft vertikalen Overlap pro Zeile, _split_by_highlight() teilt eine Zeilengruppe an highlighted/nicht-highlighted-Wechseln (eine einzelne Leerzeile zwischen zwei gleich-highlighted Abschnitten löst keinen Split aus). TextBlock.highlighted (neues Feld, Default False) markiert die Zugehörigkeit rein informativ - translatable bleibt unberührt. Verifiziert am bekannten Testfall (1526 Virelicon.pdf, Seite 1, ehemals ein Block mit "- PQ"/"- PQ"/"- Ivan" gemischt): splittet jetzt korrekt in 4 Sub-Blöcke (False/True/False/True), Leerzeile zwischen Zitatkörper und "- PQ"-Attribution bleibt wie erwartet ohne Extra-Split im True-Abschnitt.
- [x] OpenAIProvider: temperature-Parameter wird jetzt nur noch gesendet, wenn das konfigurierte Modell ihn unterstützt (_model_supports_temperature(), Präfixliste o1/o3/gpt-5) - behebt HTTP 400 ("Unsupported value: 'temperature' does not support 0.1 with this model. Only the default (1) value is supported.") bei Reasoning-Modellen, statt einen falschen Wert zu erzwingen. DEFAULT_MODEL auf "gpt-5.6-terra" aktualisiert (fällt weiterhin unter den gpt-5-Präfix, temperature bleibt also weggelassen - verifiziert). Alle vier Provider (Google/DeepL/OpenAI/Grok) bekommen zusätzlich eine einheitliche model_name-Property (bei OpenAI/Grok das konfigurierte Chat-Completions-Modell, bei Google/DeepL ein fester API-Bezeichner mangels wählbarem Modell) für die Anzeige in tools/compare_providers.py. Verifiziert mit gemocktem requests.post (kein echter API-Call): temperature fehlt im Request-Body für gpt-5.6-terra, bleibt für z. B. gpt-4o-mini erhalten.
- [x] pipeline/pdf/template.py: DocumentTemplate um to_dict()/from_dict() sowie Modulfunktionen save_json()/load_json() ergänzt (verlustfreie JSON-Serialisierung aller vier Felder, roundtrip-getestet). Bestehende direkte Instanziierung (z. B. tests/manual_e2e_pipeline.py TEMPLATE) bleibt unverändert nutzbar. Neu: templates/virelicon.json - konkretes, dokumentspezifisches Template für 1526 VIRELICON.pdf (kein projektweiter Anspruch), ermittelt durch Struktur-Untersuchung des echten PDFs (byte-identisch zur G:\...\1526 Virelicon.pdf-Referenz, per SHA-256 verifiziert): header_bbox deckt den auf allen 14 Seiten wiederkehrenden "Developer: StellarRussia / QSI ICO: VIRELICON..."-Header ab (den der reine FIRST_PAGE_ANCHOR_TERMS-Ankertext-Split NICHT erfasst, da diese Zeile in einem eigenen Block ohne Anker-Begriff sitzt), footer_bbox den wiederkehrenden Footer (Seitenzahl + Copyright), first_page_zones den restlichen Seite-1-Metadatenblock (Datum, ICO Telegram Write Up, Domain, Issuer Address, Asset Matrix) bis knapp unter die Titel-Block-bbox (239.08pt, wegen führender Leerzeilen im Titel-Block - eine größere Zone hätte den Titel fälschlich mit ausgeschlossen). Verifiziert mit tests/manual_verify_virelicon_template.py: 5 nicht-übersetzbare Blöcke auf Seite 0 (Header, 2x first_page_zone, 2x Footer), Titel "The Virelicon Prism..." bleibt korrekt übersetzbar, Header+Footer auf allen 14 Seiten korrekt ausgeschlossen.
- [x] tools/compare_providers.py: neues Vergleichs-Tool, übersetzt eine PDF mit allen vier Providern (Google/DeepL/OpenAI/Grok) blockweise und schreibt die Ergebnisse nebeneinander - als Word-Dokument (Standard) oder Markdown (--output *.md, oder automatischer Fallback falls python-docx fehlt). Nutzt PyMuPdfEngine.extract_blocks() (nur translatable=True, leere/rein numerische/symbolische Blöcke übersprungen), denselben protected_terms-Platzhalterschutz wie der Hauptpfad, und DocumentTemplate.load_json() für --template. Provider-Fehler (TranslationError) brechen den Lauf nicht ab, sondern werden pro Block/Provider als "[Nicht verfügbar: ...]" vermerkt und am Ende als Statistik ausgegeben. docx-Ausgabe: pro Block keep_with_next=True auf allen Absätzen außer dem letzten (verhindert willkürliches Auseinanderreißen eines Blocks durch einen Seitenumbruch, ohne einen erzwungenen Umbruch pro Block), horizontale Trennlinie (echter w:pBdr-Absatzrahmen) zwischen den Blöcken, plus Kopfbereich vor dem ersten Block (Quelldatei, Laufzeitpunkt, pro Provider der exakte model_name, aus den Provider-Instanzen ausgelesen statt hartkodiert). Getestet mit Fake-Providern (kein echter API-Call): Block-Erkennung, Platzhalterschutz-Pfad, Markdown-/docx-Struktur, keep_with_next-Flags, Trennlinie, ImportError→Markdown-Fallback.
- [x] Word-Lese-/Schreib-Pfad end-to-end implementiert und gegen 2210 INERTIARA.docx verifiziert (mehrere Prompts, pipeline/word/):
  - pipeline/word/base.py: WordRun (text, translatable, is_image, is_hyperlink, hyperlink_target, bold/italic/underline), WordParagraph, WordEngine-Protocol (analog zu PdfEngine), BREAK_MARKER-Konstante als eigener WordRun bei `<w:br/>` (Pendant zu PARAGRAPH_BREAK_MARKER/LINE_BREAK_MARKER im PDF-Pfad)
  - pipeline/word/docx_engine.py: DocxEngine liest document.xml + document.xml.rels via lxml, erkennt Metadatenblock über straightConnector1-Anker (mc:AlternateContent), Bild-Runs (rekursiver `_walk_run()`, überspringt mc:Fallback-Duplikate konsequent), Hyperlink-Runs mit aufgelöstem Ziel. get_header_footer_paragraphs() liest header2.xml/footer1.xml, translatable=False (Anforderung 1). replace_paragraph_runs()/replace_header_footer_paragraph() ersetzen Runs eines Absatzes im XML-Baum, Bild-Runs werden 1:1 aus dem Original-Baum wiederverwendet statt neu gebaut, w:t immer mit xml:space="preserve". save() schreibt das komplette Zip-Package neu, alle unveränderten Teile (Header/Footer sofern nicht geändert, Bilder, rels, Styles etc.) byte-identisch übernommen; verifiziert per Regressionscheck (17 unveränderte Absätze, word/media/ unverändert, python-docx öffnet die Datei anstandslos) und overwrite-Schutz (FileExistsError ohne overwrite=True)
  - pipeline/word/html_bridge.py: paragraph_to_html()/html_to_paragraph() als Brücke zu translate_html() der bestehenden Provider. Echte Pseudo-Tags (`<img data-run="n"/>`, `<br/>`, `<a data-run="n">`) statt reiner Text-Platzhalter - Umstellung nötig, weil erste Version mit §§IMG:n§§/§§BR§§-Text-Markern bei DeepL und Google nachweislich beschädigt wurde (DeepL vermischte Marker mit protected_terms-Platzhaltern, Google verschluckte Zeichen bei aufeinanderfolgenden Markern), Tags dagegen bei allen vier Providern (DeepL/Google/OpenAI/Grok) zuverlässig erhalten blieben. Validierung gegen Bild-/Hyperlink-Verlust wirft ValueError; §§SP§§-Marker sichert Leerzeichen an `<br/>`-Grenzen proaktiv ab (ersetzt vorhandenes Leerzeichen vor Übersetzung, kein Nachträglich-Raten). protect_terms()/restore_terms() im vollen Fluss (auch als Hyperlink-Anzeigetext) verifiziert.
  - tests/manual_translate_full_document.py: übersetzt ein komplettes Dokument (translatable-Absätze im Hauptteil, Header/Footer korrekt ausgeschlossen), Kurzreport (übersetzt/übersprungen/fehlgeschlagen, Zeichenanzahl, Kostenschätzung, Laufzeit). Echter Lauf gegen 2210 INERTIARA.docx visuell in LibreOffice geprüft: Header/Footer/Metadatenblock/ICO-Name korrekt unübersetzt, Bild und Layout unauffällig.
  - Bug gefunden und gefixt: Trennstrich-Bild-Run sitzt verschachtelt in mc:AlternateContent/mc:Choice statt direkt als `<w:r>`-Kind - replace_paragraph_runs() suchte ursprünglich nur flach und stürzte ab, jetzt nutzt auch die Schreibrichtung den rekursiven `_walk_run()`.
- [x] Duplikat-/Quellen-Tracking für die Stapelverarbeitung: ico_translate/ als eigene Anwendungsschicht über der generischen Engine gebaut (pipeline/word/, pipeline/pdf/, pipeline/translation/ bleiben ordner-/ICO-unabhängig wiederverwendbar). Statt hartkodierter Auswahlregeln im Code: ico_translate/source_manifest.json als versioniertes, dauerhaftes Manifest (Dokumentnummer -> genehmigte Datei(en) + mtime/sha256 + optionale "excluded"-Liste für bewusst nicht gewählte Duplikat-Verlierer, die physisch im Ordner bleiben). ico_translate/manifest.py: scan_folder() (nutzt discover_documents()), diff_against_manifest() klassifiziert jede Nummer in auto_approved (neu, eindeutig - automatisch übernommen)/unchanged/changed (Datei geändert, mtime-Vorfilter + Hash-Bestätigung)/new_duplicate (neue Mehrfach-Gruppe, classify_group()-Vorschlag aber keine Auto-Entscheidung)/missing. ico_translate/cli.py: `scan` (Exit-Code 1 bei offenen Unstimmigkeiten) + `approve <nummer> <dateien> [--exclude ...] [--note ...]` für die manuelle Klärung. Alle 23 Mehrfach-Kandidaten-Gruppen im echten Ordner (2169 Dokumentnummern, davon 2146 einfach) einmalig manuell geklärt und ins Manifest übernommen (7 (LS)-Paare, davon MNEMOSYNE mit umgekehrter Regel/(LS)-Version gewinnt, die übrigen 6 mit Nicht-(LS) gewinnt; 6 unabhängige Dokumentpaare unter gleicher Nummer, teils mit einem der (LS)-Paare unter derselben Nummer kombiniert, z. B. 1440 TRUTHSEEK+WOUNDS/WOUNDS (LS) excluded; 6 "ohne Klammer-Nummer gewinnt"-Fälle; 6 explizite Einzelfälle wie 1746 NOOVIAN Updated/1772 SVAULT Follow Up) - finaler Scan bestätigt 0 Unstimmigkeiten bei 2175 approved + 21 excluded Dateien. Künftige Ordner-Änderungen (neue Dokumente, geänderte/neue Duplikate) werden beim nächsten `scan` automatisch als Unstimmigkeit erkannt statt stillschweigend falsch verarbeitet.
- [x] Batch-Orchestrierung fuer den Word-Pfad: pipeline/word/translate_document.py extrahiert tests/manual_translate_full_document.py's bisherige Einzeldokument-Uebersetzungslogik (paragraph_to_html -> protect_terms -> translate_html -> restore_terms -> html_to_paragraph -> replace_paragraph_runs()/replace_header_footer_paragraph()) in translate_document() + TranslationStats (uebersetzt/uebersprungen/fehlgeschlagen je body/header/footer), sodass das bisherige Einzeldokument-Skript und der neue Batch-Lauf dieselbe Logik nutzen. ico_translate/batch.py: run_batch() iteriert ueber alle "approved" Manifest-Dateien (jede Datei jeder Nummer einzeln - eine unabhaengige Mehrfach-Nummer wie 1440 erzeugt automatisch mehrere Ausgabedateien), Namensschema "<Nummer> <ICO-Name>_<Zielsprache-Code>.docx" (Anforderung 8), TranslationBudgetGuard.confirm_run() EINMAL fuer die gesamte geplante Zeichenmenge vor dem ersten echten API-Call (collect_translatable_texts() scannt alle Dokumente vorab, ohne zu uebersetzen), ein fehlschlagendes Einzeldokument (Oeffnen/Uebersetzen/Speichern) wird abgefangen, nach tests/output/ico_batch_errors.jsonl geloggt (Traceback inklusive) und uebersprungen statt den Lauf abzubrechen. `limit`/`only_numbers` fuer Testlaeufe auf einer Teilmenge. cost_control.py um OPENAI_PRICING/GROK_PRICING (grobe Naeherung, da beide token- statt zeichenbasiert abgerechnet werden) und TranslationBudgetGuard.provider_name ergaenzt. ico_translate/cli.py: neuer Subcommand `translate --target-lang --provider {deepl,google,openai,grok} --output-dir [--limit] [--only] [--dry-run] [--yes]`; `--root`/`--manifest` funktionieren jetzt sowohl vor als auch nach dem Subcommand-Namen (argparse-Subparser-Fallstrick: ohne default=SUPPRESS auf der Subparser-Kopie ueberschreibt deren eigener Default sonst stillschweigend einen vor dem Subcommand gesetzten Wert). Echter 3-Dokumente-Testlauf (--only 1440,2210 --limit 3, DeepL) bestaetigt: 1440 TRUTHSEEK + 1440 WOUNDS als zwei separate Ausgabedateien aus der unabhaengigen Mehrfach-Gruppe, 0 fehlgeschlagen. Zweiter Testlauf mit einer bewusst kaputten Manifest-Datei (nicht existierende Datei) bestaetigt den Fehlerpfad; dabei zusaetzlich einen echten, bis dahin unbekannten Fall gefunden (nicht behoben, nur beobachtet): DeepL liess bei "1868 SILENCE.docx" einen Hyperlink-Tag beim Uebersetzen verschwinden, was html_to_paragraph()s _validate_tags() korrekt als ValueError meldet - genau wie erhofft nur geloggt und uebersprungen, der Lauf lief mit dem naechsten Dokument weiter (1868 VALCYRON erfolgreich uebersetzt). Bekannte Einschraenkung (seither behoben, siehe naechster Eintrag): der Schutzbegriff/ICO-Name fuer die Ausgabe-Dateinamen kam aus derive_protected_term() auf dem QUELL-Dateinamen statt aus dem Dokument selbst - bei den wenigen approved Dateien mit Revisions-Suffix (z. B. "1854 MNEMOSYNE (LS).docx", "1746 NOOVIAN Updated Declas.docx") landete dieser Suffix unveraendert im Schutzbegriff UND im Ausgabedateinamen, obwohl er im eigentlichen Dokumenttext nicht vorkommt - der Schutzbegriff griff dort also nicht.
- [x] Schutzbegriff-Bug behoben (Anforderung 4, "ICO-Namen werden nie uebersetzt"): pipeline/word/source_selection.py's aehnlich benanntes document_ico_name() ist trotz des Namens ebenfalls rein dateinamenbasiert (raet nur, oeffnet das Dokument nie) - die tatsaechlich inhaltsbasierte Extraktion ("QSI ICO: X" aus dem Header) gab es bereits als private _find_developer_and_ico()-Hilfsfunktion in pipeline/word/duplicate_analysis.py, aber nur intern ueber _analyze_one()/analyze_candidate_group() erreichbar. Neu: read_ico_name(engine) in duplicate_analysis.py als oeffentliche Funktion, die denselben Header-Text eines BEREITS GEOEFFNETEN DocxEngine ausliest (kein zweites Oeffnen der Datei noetig) - liefert None, wenn kein "QSI ICO:"-Feld im Header gefunden wird. ico_translate/batch.py: resolve_ico_name() nutzt das jetzt als primaere Quelle fuer Schutzbegriff UND Ausgabedateiname; nur wenn read_ico_name() None liefert, faellt es auf derive_protected_term() (Dateiname) zurueck, mit Logging nach tests/output/ico_protected_term_fallbacks.jsonl (neues BatchResult.protected_term_fallbacks-Feld, im CLI-Kurzreport sichtbar) - ein Dokument laeuft nie mehr unbemerkt mit einem schwaecheren Schutzbegriff. Verifiziert an allen 4 bekannten Problemfaellen (1854 MNEMOSYNE (LS), 1746 NOOVIAN Updated Declas, 1750 ANEMNESIS updated, 1772 SVAULT Follow Up): read_ico_name() liefert jetzt ueberall den reinen Namen ohne Suffix. Echter Batch-Lauf gegen alle 4: 2 erfolgreich (1750/1772), im uebersetzten Text 21x "ANEMNESIS" bzw. 3x "SVAULT" unveraendert bestaetigt; die anderen 2 (1746/1854) trafen den bereits bekannten, unabhaengigen DeepL-Hyperlink-Drop-Bug (siehe vorheriger Eintrag) - korrekt geloggt/uebersprungen, keine Regression durch diese Aenderung. Fallback-Pfad zusaetzlich synthetisch verifiziert (kein echtes Dokument im Bestand hat einen fehlenden Header). Regressionscheck (--only 1440,2210 --limit 3) liefert identische Zahlen wie vor der Aenderung.
- [x] LICENSE (GPL-3.0-or-later)
- [x] README.md
- [x] CONTRIBUTING.md
- [x] .gitignore
- [x] Produktiver PPTX-DeepL-Lauf an den Startknopf im UI angebunden (RoadMap.md
  Phase 1, alle Checkbox-Punkte außer dem realen Live-Lauf umgesetzt):
  - pipeline/presentation/translate_presentation.py: translate_presentation()
    um `should_cancel` (Callable[[], bool], vor jedem Absatz UND vor jedem
    Container geprüft - also immer zwischen zwei API-Aufrufen, nie mittendrin)
    und `stats_callback` (nach jedem Absatzergebnis mit dem aktuellen
    PresentationTranslationStats aufgerufen) erweitert. PresentationTranslationStats
    hat ein neues `cancelled`-Feld und eine `paragraphs_processed`-Property
    (Summe aus translated/skipped/failed) als Fortschrittszähler für Aufrufer.
    Bei Abbruch bricht die äußere UND die innere Schleife sauber ab (vorheriger
    Entwurf hätte nur die innere Schleife verlassen und mit dem nächsten
    Container weitergemacht - im Test abgefangen).
  - Neu: ui/pptx_job.py - Qt-unabhängige Auftragsorchestrierung, direkt
    unit-testbar. `safe_destination()` hängt immer den Zielsprachcode an den
    Dateinamen an und erhöht bei Kollision einen Zähler ("Deck_DE.pptx",
    "Deck_DE (2).pptx", ...), verglichen wird zusätzlich gegen den aufgelösten
    Quellpfad. `run_presentation_job()` prüft Ziel==Quelle bzw. Ziel existiert
    bereits VOR dem Öffnen der Engines/vor jedem API-Aufruf (DestinationConflictError,
    getestet: 0 API-Aufrufe beim Fehlerfall). Öffnet die Quelle zweimal (baseline
    für den Überlaufvergleich, ein zweites Mal als tatsächlich übersetzte
    Arbeitskopie), da PptxEngine.compare_overflow() ein unverändertes zweites
    Engine-Objekt erwartet. Baut den Provider über PROVIDER_FACTORIES (alle
    vier bereits implementierten Provider: deepl/google/openai/grok - Phase 1
    nennt nur DeepL, die anderen drei kosten aber keinen Zusatzaufwand, da sie
    translate_html() bereits implementieren; DeepL bleibt der einzige mit Live-
    Test verifizierte Pfad, siehe unten), wrapped ihn in TranslationBudgetGuard
    (harte Zeichenobergrenze, siehe pipeline/translation/cost_control.py -
    bestehender Mechanismus, unverändert). `_build_qa_report()` erzeugt eine
    Textdatei "<Ausgabedatei>_qa_report.txt" mit Quelle/Ziel/Anbieter/Sprache,
    übersetzt/übersprungen/fehlgeschlagen/gesendete Zeichen, bei Abbruch einem
    expliziten Teilergebnis-Hinweis, der technischen Fehlerliste (ohne
    Zugangsdaten - Provider-Fehlermeldungen enthalten laut Code-Review nie den
    API-Key), allen Überlaufrisiken gegenüber dem Original (Folie, Shape,
    geschätzte/verfügbare Zeilen - rein informativ zur manuellen Prüfung,
    keine automatische Umformatierung) und der Liste bewusst nicht
    unterstützter Inhaltstypen aus PptxEngine.capability_catalog().
  - Neu: ui/workers.py::PresentationTranslationWorker (QRunnable) - Abbruch
    ist kooperativ über ein threading.Event (`request_cancel()` setzt es nur,
    der laufende API-Aufruf wird nie unterbrochen). Snapshot-Kopie der Stats
    (`_copy_stats()`) vor jedem Signal-Emit, damit die Qt-Queued-Connection
    über den Thread hinweg nie einen später mutierten Zustand zeigt.
  - ui/app.py: `_start()` fragt vor dem ersten API-Aufruf einen Zielordner
    (QFileDialog) und zeigt danach eine explizite Kostenbestätigung
    (QMessageBox mit Zeichenzahl/Kostenschätzung/Zieldatei aus der bereits
    vorliegenden Analyse) - erst danach wird der Worker gestartet. Startknopf
    ist bewusst nur für TranslationMode.PRESENTATION aktivierbar
    (_EXECUTABLE_MODES); PDF/Word/Bilder bleiben mit Tooltip-Hinweis auf
    RoadMap.md deaktiviert, um nicht fälschlich fertig zu wirken. Neues
    Lauf-/Ergebnis-Panel zeigt während des Laufs die aktuelle Position
    (Folie/Shape/Absatz aus progress_callback) und einen Fortschrittsbalken
    aus stats_callback; nach Abschluss Kurzstatistik, Ausgabedatei, QA-Bericht-
    Pfad, Anzahl Überlaufhinweise sowie Buttons zum Öffnen des Zielordners und
    des QA-Berichts (QDesktopServices). Laufende Jobs sperren Modus-/Quell-/
    Anbieterauswahl und die Einstellungen, damit während eines Laufs nichts
    verändert wird, das der Job noch liest.
  - pipeline/translation/base.py-Fehlerpfad geprüft: TranslationError-Texte
    aller vier Provider (DeepL/Google/OpenAI/Grok) enthalten nur HTTP-Status/
    Message bzw. str(exc), nie den API-Key - Fehleranzeige im UI (QMessageBox
    + `logging.error()`) und im QA-Bericht sind damit ohne Zusatzaufwand
    zugangsdatenfrei.
  - Neue i18n-Schlüssel in DE/EN ergänzt (job.*, dialog.choose_output_dir,
    dialog.confirm_run, start.confirm_summary, start.ready) - Gleichheit der
    beiden Kataloge bleibt über tests/test_ui_i18n.py abgesichert.
  - Getestet (tests/test_pptx_job.py, Fake-HTML-Provider wie schon in
    tests/test_pptx_translation_bridge.py, 7 neue Tests, alle grün):
    safe_destination()-Kollisionsvermeidung, erfolgreicher Lauf inkl. QA-
    Bericht-Inhalt, Ziel-existiert-bereits UND Ziel==Quelle lösen
    DestinationConflictError VOR jedem API-Aufruf aus (Call-Zähler geprüft),
    Abbruch nach dem ersten API-Aufruf liefert ein klar als abgebrochen
    markiertes Teilergebnis mit bereits übersetztem Absatz, stats_callback
    liefert für jeden der 6 Testabsätze eine monoton steigende Momentaufnahme,
    zu kleines Zeichenlimit lässt alle Absätze kontrolliert über
    BudgetExceededError fehlschlagen statt den Lauf abzubrechen. Zusätzlich
    manuell (ohne pytest) MainWindow mit `QT_QPA_PLATFORM=offscreen`
    konstruiert und Analyse- und Job-Abschluss-Pfad durchgespielt (DE und EN) -
    keine Attributfehler, Startknopf korrekt nur nach Analyse+Bestätigung im
    PRESENTATION-Modus aktiv.
  - Neu: tests/manual_e2e_pptx_ui_translation.py - ruft exakt denselben Pfad
    wie der Startknopf auf (run_presentation_job()) gegen ein reales
    Dokument über die echte DeepL-API; überspringt sich selbst kontrolliert,
    wenn kein DeepL-Schlüssel verfügbar ist oder die Datei fehlt (wie die
    bestehenden manual_*.py-Skripte). **Noch nicht ausgeführt:** Das in der
    RoadMap referenzierte reale 19-Folien-Testdokument
    ("OPRES ES Hub Quorum Activation Call Presentation.pptx") lag zu Beginn
    dieser Änderung im Projektwurzelverzeichnis, war beim Zurückschreiben der
    Änderungen aber nicht mehr vorhanden - der Live-Lauf inkl. Sichtprüfung
    des bekannten Sonderfalls auf Folie 11 steht daher noch aus, sobald die
    Datei wieder verfügbar ist und ein DeepL-Schlüssel konfiguriert ist.
  - Bewusst nicht Teil dieser Änderung (folgt mit Phase 2 laut RoadMap.md):
    DOCX- und PDF-Pfad über denselben Auftragsablauf, Warteschlange/
    Stapelverarbeitung mehrerer Aufträge, dediziertes Logfile (aktuell
    Standard-`logging`, kein eigenes Dateihandler-Setup).
- [x] Erster echter UI-Test durch den Nutzer (reales 19-Folien-Dokument, Skript
  aus dem vorigen Punkt) deckte zwei echte Anschlussprobleme auf, beide behoben:
  - **Startknopf blieb ohne erkennbaren Grund ausgegraut:** Ursache war NICHT
    ein Logikfehler in `_update_start_state()` (an einem durchgespielten
    Analyse->Bestätigen-Ablauf mit `QT_QPA_PLATFORM=offscreen` bestätigt
    korrekt), sondern dass der einzige Hinweis auf den fehlenden Zustand ein
    Tooltip war, der beim bloßen Hinsehen nicht auffällt. ui/app.py bekommt
    ein neues `start_hint`-QLabel unter den Start-/Analysieren-Buttons, das
    IMMER sichtbar den exakten blockierenden Grund zeigt (`_start_blocked_reason()`:
    kein unterstützter Modus / keine Analyse / nicht bestätigt / Lauf bereits
    aktiv), nicht nur beim Hover. `_invalidate_analysis()` ruft jetzt
    `_update_start_state()` statt Felder doppelt manuell zu setzen, damit
    Knopf-Zustand und Hinweistext nie auseinanderlaufen können. Vier neue
    i18n-Schlüssel (start.blocked_running/mode/no_analysis/not_confirmed) in
    DE/EN. Falls sich das konkrete Szenario des Nutzers dennoch wiederholt,
    zeigt der jetzt sichtbare Text direkt, welche der vier Bedingungen fehlt.
  - **Nutzerfrage:** ob sich der tatsächliche Kontingentstand bei den Anbietern
    auslesen lässt (wie auf der DeepL-Website nach Login sichtbar), statt nur
    lokal zu schätzen - Recherche (17.08.2026) bestätigt: DeepL bietet dafür
    `GET /v2/usage` mit demselben API-Key an (kein separates Login nötig,
    liefert `character_count`/`character_limit` der aktuellen Abrechnungsperiode,
    laut developers.deepl.com für Free- und Pro-Keys gleichermaßen). Dieselbe
    Recherche bestätigt außerdem die Beobachtung des Nutzers zum DeepL-Kontingent:
    das alte "DeepL API Free" (500.000 Zeichen/Monat, erneuert sich) wird laut
    support.deepl.com nicht mehr neu verkauft - neue kostenlose Konten erhalten
    stattdessen ein einmaliges, sich NICHT erneuerndes 1.000.000-Zeichen-Kontingent
    (Developer-Plan). Das erklärt vermutlich den "Quota exceeded"-Fehler (HTTP 456)
    im QA-Bericht des Nutzers nach nur 2.055 gesendeten Zeichen: die lokale
    Schätzung in `pipeline/translation/cost_control.py` nahm bisher fälschlich
    für jeden DeepL-Key eine monatliche Erneuerung an.
    - Neu: `DeepLProvider.get_usage()` (pipeline/translation/deepl_provider.py)
      - GET auf `<api_url ohne /translate>/usage`, liefert
      `{"character_count": int, "character_limit": int | None}`
      (`character_limit=None`, wenn der Account laut DeepL kein Limit hat).
      Getestet mit gemocktem `requests.get` (tests/test_deepl_usage.py, 3 Tests:
      Free-Endpunkt, Pro-Endpunkt/kein Limit, TranslationError ohne Zugangsdaten).
    - `ui/analysis.py::_cost()` ruft `get_usage()` jetzt für Provider "deepl" auf
      und nutzt bei Erfolg den ECHTEN verbleibenden Freibetrag statt der lokalen
      `get_month_usage()`-Schätzung für die Kostenschätzung; scheitert der
      Live-Check (kein Schlüssel, offline, API-Fehler), fällt es transparent
      auf die alte lokale Schätzung zurück und hängt eine neue Warnung
      ("warning.live_quota_unavailable") an, statt die Analyse abzubrechen.
      Für alle anderen Provider wird `get_usage()` gar nicht erst aufgerufen.
      `CostSummary` (ui/models.py) um `live_usage_available`/
      `live_characters_used`/`live_character_limit` erweitert. Im UI erscheint
      bei Erfolg eine zusätzliche, deutlich als "Live" markierte Zeile mit
      Ist-Verbrauch/Limit/Rest (ui/i18n.py: analysis.live_quota[_unlimited],
      warning.live_quota_unavailable, DE/EN). Getestet
      (tests/test_analysis_live_quota.py, 4 Tests, DeepLProvider gemockt):
      Live-Wert wird übernommen, unbegrenzter Account rechnet nichts als
      "über dem Freikontingent" an, Fallback bei fehlgeschlagenem Live-Check,
      und dass für einen Nicht-DeepL-Provider gar kein Live-Aufruf versucht wird.
    - Recherchiert, aber NICHT umgesetzt: Google Cloud Translation und OpenAI
      haben keinen einfachen, nur mit dem bereits gespeicherten API-Key
      abfragbaren Kontingent-Endpunkt - Google verlangt dafür IAM-/OAuth-Zugriff
      auf ein GCP-Projekt (Cloud Monitoring/Service Usage API), OpenAI eine
      separate Admin-/Organisations-Berechtigung statt eines normalen Projekt-
      Schlüssels (die OpenAI-Community fordert einen einfacheren Endpunkt
      selbst noch als Feature, siehe Quellen). Grok/xAI nicht recherchiert.
      Eine Umsetzung würde das bisherige "ein API-Key pro Provider"-Modell in
      Einstellungen erweitern - als eigener Punkt für Phase 7 vorzumerken,
      falls gewünscht.
    - Quellen: developers.deepl.com/api-reference/usage-and-quota,
      support.deepl.com/hc/en-us/articles/360021200939-DeepL-API-plans,
      community.openai.com/t/add-api-endpoint-to-check-remaining-credits-or-balance-on-openai-account/1365221
- [x] Drei vom Nutzer nach dem ersten UI-Sichttest gemeldete Bugs behoben
  (Dunkelmodus-Kontrast, veraltete Kostenschätzung, Startknopf reagiert
  nicht):
    - **Dunkelmodus-Kontrast:** Checkbox und Textfelder (QLineEdit/QTextEdit)
      waren unter einem aktiven Linux-Dunkelmodus-Theme praktisch unlesbar,
      weil die App bisher komplett der eigenen Qt-Style-/Palette-Integration
      des Desktops vertraute statt eigene Farben zu setzen - mindestens eine
      reale Kombination liefert dabei zu wenig Kontrast für diese Widgets.
      Neu: `ui/theme.py` (kein Qt-Import, daher ohne Display testbar) mit
      WCAG-2.x-Kontrastformel (`contrast_ratio()`, `_relative_luminance()`)
      und zwei kontrastgeprüften Palettensätzen (`DARK_COLORS`/
      `LIGHT_COLORS`), `ui/app.py::apply_explicit_palette()` erkennt anhand
      der vom Desktop *geerbten* Palette-Helligkeit Hell/Dunkel und setzt
      dann eine explizite `QPalette` (inkl. `QPalette.Disabled`-Farbgruppe,
      damit ein deaktivierter Startknopf eindeutig als deaktiviert erkennbar
      bleibt statt nur schlecht sichtbar zu sein) - ein helles Desktop-Theme
      wird dabei unangetastet gelassen. Getestet (tests/test_ui_theme.py, 4
      Tests): alle Text/Hintergrund-Paare (Eingabefelder, Fenster, Buttons,
      Auswahl-Highlight) erreichen WCAG-AA (>= 4.5:1) in beiden Paletten;
      deaktivierter Text bleibt lesbar (>= 2.0:1), aber immer klar schwächer
      als aktivierter Text. Ursprüngliche Highlight-Farbe (61,132,224) schaffte
      nur 3.77:1 gegen Weiß und wurde durch (37,99,189) ersetzt (5.84:1).
    - **Veraltete Kostenschätzung / falsche Analyse je nach Modus:** Ursache
      war ein subtiler PySide6-Fallstrick, unabhängig vom Dunkelmodus-Fund,
      aber vom selben Sichttest aufgedeckt. `TranslationMode`/
      `EmbeddedImageMode` sind `str, Enum`-Mixins; wird ein Member per
      `QComboBox.addItem(text, member)` als userData gespeichert und über
      `currentData()` wieder ausgelesen, liefert PySide6 (Rundreise durch
      QVariant) einen reinen `str` zurück - NICHT die ursprüngliche
      Enum-Instanz. `==`/`!=` und Hash-/Set-Vergleiche bleiben davon
      unberührt, aber jeder `is`/`is not`-Vergleich gegen die Enum-Konstante
      schlägt seitdem still und dauerhaft fehl. Reproduziert:
      ```
      combo.addItem("", TranslationMode.PRESENTATION); combo.setCurrentIndex(0)
      combo.currentData() is TranslationMode.PRESENTATION   # False
      combo.currentData() == TranslationMode.PRESENTATION   # True
      ```
      Das erklärte die vom Nutzer gemeldete falsche Analyse ("1 Bilder / 0
      Textzeichen" für eine echte .pptx-Datei im Präsentations-Modus): die
      `is`-Verzweigungskette in `analyze_request()` (ui/analysis.py) fiel
      dadurch immer in den Bilder-/else-Zweig, unabhängig vom tatsächlich
      gewählten Modus - die angezeigte Kostenschätzung passte deshalb nicht
      zur echten Datei. Alle betroffenen Vergleiche in `ui/app.py` (Zeilen
      ~260, ~272, ~371), `ui/analysis.py` (Zeilen ~102, ~105, ~121, ~129,
      ~142, ~143) und `ui/models.py` (Zeile ~45) von `is`/`is not` auf
      `==`/`!=` umgestellt; zusätzlich baut `ui/app.py::MainWindow._request()`
      den `TranslationRequest` jetzt mit expliziter Rückkonvertierung
      (`TranslationMode(self.mode.currentData())`,
      `EmbeddedImageMode(self.image_mode.currentData())`), damit ab der
      UI-Grenze wieder echte Enum-Singletons im restlichen Code ankommen.
    - **Startknopf reagiert auf Klick nicht:** derselbe Fallstrick, konkreter
      Fall: `MainWindow._start()` prüfte bisher
      `if self.mode.currentData() is not TranslationMode.PRESENTATION: return`
      - diese Bedingung war wegen des Enum-Fallstricks immer wahr, der
      Startknopf brach also bei jedem Klick sofort und ohne jede Meldung ab,
      egal welcher Modus gewählt war. Jetzt `!=` statt `is not` - der Klick
      erreicht damit wieder den Ordnerauswahl-Dialog.
    - Neuer Regressionstest tests/test_ui_enum_identity.py (3 Tests, echte
      QComboBox statt Mock): dokumentiert das PySide6-Verhalten selbst (damit
      ein künftiges PySide6-Update hier auffällt statt als mysteriöser
      UI-Bug), prüft dass ein aus einer QComboBox-Auswahl gebauter
      TranslationRequest im Präsentations-Modus tatsächlich die
      Folien-/Zeichen-Zweige von analyze_request() nimmt (nicht den
      Bilder-Fallback), und reproduziert die konkrete Bedingung aus
      `_start()` als eigenständige Prüfung. Zusätzlich in derselben Runde
      behoben: `ui/app.py::_invalidate_analysis()` zeigte bei Moduswechsel
      bisher noch die Zahlen der vorherigen Analyse an, obwohl `last_result`
      bereits intern zurückgesetzt war - setzt jetzt sofort
      "Analyse erforderlich" beim Invalidieren.
    - Gesamter Testlauf nach der Änderung: 43 passed, 1 skipped
      (`QT_QPA_PLATFORM=offscreen python3 -m pytest -q`).
    - Noch offen (externe Rahmenbedingung, kein Bug): der DeepL-Live-
      Kontingent-Check des Nutzers zeigte zum Zeitpunkt des Sichttests
      500.000 von 500.000 Zeichen verbraucht (0 verbleibend) - passend zum
      vom Nutzer selbst auf der DeepL-Website abgelesenen Stand
      ("Genutzte Zeichen" 498.765). Ein echter Testlauf gegen den 19-Folien-
      Datensatz schlägt deshalb aktuell mit "Quota exceeded" fehl, bis das
      Konto entweder ein neues Kontingent bekommt oder ein anderer
      Account/Provider verwendet wird - unabhängig vom oben beschriebenen
      Startknopf-Fix.
- [x] Fortschrittsanzeige während des Laufs behoben ("Das UI zeigt keinen
  klaren Status während des Laufs an. Man weiss nicht ob etwas im
  Hintergrund passiert."). Ursache: `ui/app.py::_job_stats()` setzte den
  Fortschrittsbalken bisher mit
  `setRange(0, max(stats.paragraphs_processed, 1)); setValue(stats.paragraphs_processed)`
  - das Maximum wurde also bei jedem Update auf den AKTUELLEN
  verarbeiteten Stand gesetzt, wodurch der Balken unabhängig vom
  tatsächlichen Fortschritt permanent bei 100% stand (genau das im
  Screenshot des Nutzers zu sehende Bild, mitten im Lauf). Zusätzlich zeigte
  der Statustext während des Laufs nur die aktuell verarbeitete Position
  ("Verarbeite: ppt/slides/slide8.xml..."), aber keine laufenden
  Zähler - ob sich etwas tut, war daher nicht erkennbar.
    - Neu: `pipeline/presentation/translate_presentation.py::total_paragraph_count(engine)`
      ermittelt die Gesamtzahl aller Absätze (übersetzbar oder nicht) vorab,
      ohne API-Aufruf, durch dieselbe Container-Traversierung, die
      `translate_presentation()` intern nutzt.
      `ui/pptx_job.py::run_presentation_job()` bekommt einen neuen optionalen
      `total_callback`-Parameter, der genau einmal - vor dem ersten
      API-Aufruf - mit dieser Gesamtzahl aufgerufen wird.
      `ui/workers.py::TranslationSignals` bekommt ein neues `total`-Signal,
      das `PresentationTranslationWorker` an `total_callback` durchreicht.
    - `ui/app.py`: neuer Handler `_job_total(total)` schaltet den
      Fortschrittsbalken von unbestimmt (kurzes Intervall, solange die
      Gesamtzahl noch nicht bekannt ist) auf einen echten, determinierten
      Balken (`setRange(0, total)`) um; `_job_stats()` setzt danach nur noch
      `setValue(...)`, ohne das Maximum zu verändern. Neuer kombinierter
      Statustext über `_update_job_status()`: zeigt weiterhin die aktuelle
      Position (`job.progress_prefix`), zusätzlich jetzt "{X} von {Y}
      Absätzen verarbeitet" (neuer Schlüssel `job.progress_count`, DE/EN)
      sowie laufende Zähler übersetzt/übersprungen/fehlgeschlagen/Zeichen
      (`job.stats_summary` - dieser Schlüssel existierte bereits in
      `ui/i18n.py`, war aber nie tatsächlich an eine Stelle im UI
      angeschlossen; jetzt live während des Laufs sichtbar statt erst im
      Endergebnis).
    - Getestet: neuer Test
      `tests/test_pptx_job.py::test_total_callback_reports_paragraph_count_before_first_api_call`
      bestätigt, dass `total_callback` genau einmal mit der korrekten
      Absatzzahl (6, Fixture) aufgerufen wird, und zwar BEVOR
      `provider.translate_html()` auch nur ein einziges Mal aufgerufen
      wurde (Regressionsschutz gegen die alte "Balken zeigt immer 100%
      an"-Situation). Gesamter Testlauf: 44 passed, 1 skipped.
- [x] Warnung bei fehlendem API-Schlüssel für den gewählten Provider ("Wenn
  ich einen neuen Provider auswähle und es keine API Keys gibt, kommt keine
  Warnung ausser im QA-Bericht"). Bisher gab es dafür überhaupt keine
  UI-Rückmeldung - ein fehlender Schlüssel fiel erst nach einem kompletten,
  bereits durchgelaufenen Übersetzungslauf auf (jeder Absatz einzeln als
  fehlgeschlagen im QA-Bericht), analog zum vorher behobenen
  Live-Kontingent-Fall.
    - Neu: `ui/app.py::MainWindow.provider_hint` - ein Label direkt unter dem
      Anbieter-Auswahlfeld im Formular, das sofort bei jeder Auswahländerung
      (`provider.currentTextChanged`) über `credential_status()`
      (ui/settings.py, bereits vorhanden, bisher nur im Einstellungsdialog
      genutzt) prüft, ob ein Schlüssel hinterlegt ist. Fehlt einer, erscheint
      ein fett hervorgehobener Hinweistext mit eingebettetem Link ("Jetzt
      einrichten"), der den Einstellungsdialog direkt mit dem betroffenen
      Anbieter vorausgewählt öffnet (`SettingsDialog` bekommt dafür einen
      neuen optionalen `initial_provider`-Parameter). Ist ein Schlüssel
      vorhanden, bleibt das Label leer/unsichtbar.
    - Zusätzliche Absicherung beim Startknopf: `MainWindow._start()` prüft
      `credential_status()` jetzt selbst noch einmal, BEVOR der
      Ausgabeordner-Dialog überhaupt geöffnet wird - fehlt der Schlüssel,
      erscheint eine Warnmeldung (mit Direktlink in die Einstellungen)
      und der Lauf wird gar nicht erst gestartet, statt erst nach einem
      kompletten, zum Scheitern verurteilten Durchlauf über alle Absätze zu
      scheitern.
    - Bug nebenbei vermieden, nicht nur behoben: `QPushButton.clicked` sendet
      ein bool-Argument ("checked"); da `_open_settings()` jetzt einen
      optionalen `preselect_provider`-Parameter hat, hätte eine direkte
      `clicked.connect(self._open_settings)`-Verbindung dieses bool
      versehentlich als `preselect_provider` durchgereicht (klassischer
      PySide/PyQt-Fallstrick, verwandt mit dem bereits dokumentierten
      QComboBox/QVariant-Fallstrick weiter oben) - die Verbindung nutzt jetzt
      ein Lambda ohne Argumente.
    - Getestet (tests/test_ui_provider_credentials.py, 2 Tests, echtes
      MainWindow + echte QComboBox/QMessageBox/QFileDialog, keine Mocks auf
      Modulebene): Hinweistext erscheint/verschwindet korrekt beim
      Providerwechsel; ein Startversuch mit fehlendem Schlüssel zeigt die
      Warnung und erreicht nachweislich NICHT den Ausgabeordner-Dialog
      (`QFileDialog.getExistingDirectory` schlägt den Test fehl, falls
      aufgerufen), kein Worker wird gestartet. Gesamter Testlauf: 46 passed,
      1 skipped.
- [x] Nutzerfrage geklärt: "Es wird auch bei Google ein Freikontigent von
  500.000 angezeigt - gilt das nicht nur für DeepL?" Geprüft (kein Bug):
  `ui/analysis.py::PRICING` bildet Anbieter bereits korrekt getrennt ab
  (`GOOGLE_PRICING`/`DEEPL_PRICING`/`OPENAI_PRICING`/`GROK_PRICING`, je
  eigene `free_tier_chars_per_month`), keine gemeinsame/verwechselte
  Konstante. Die 500.000 für Google sind kein Kopierfehler von DeepL,
  sondern laut offizieller Google-Cloud-Preisseite (cloud.google.com/
  translate/pricing, abgerufen 2026) tatsächlich Googles eigenes
  Freikontingent für Cloud Translation - Basic (v2): ein monatlich
  wiederkehrendes 10-USD-Guthaben, das bei 20 USD/Million Zeichen genau
  500.000 Zeichen/Monat entspricht - unabhängig von DeepL, nur zufällig
  derselbe Zahlenwert. Unterschied zu beachten: Googles Kontingent erneuert
  sich nachweislich jeden Monat, während neu registrierte DeepL-Konten
  laut vorherigem Fund stattdessen ein einmaliges, nicht erneuerndes
  1.000.000-Zeichen-Kontingent bekommen (bestehende ":fx"-Altkonten wie das
  des Nutzers behalten das monatliche 500.000-Modell, siehe DeepL-Eintrag
  weiter oben) - für Google gibt es (siehe dortiger Backlog-Eintrag) keinen
  vergleichbaren Live-Abrufweg über den reinen API-Key, die Zahl bleibt
  dort also immer die lokale, unverifizierte Schätzung.
    - Kleine Klarstellung im UI ergänzt, damit dieselbe Frage nicht wieder
      aufkommt: die Zeile heißt jetzt "Lokale Schätzung ({provider}): ..."
      statt nur "Lokale Schätzung: ..." (ui/i18n.py: `analysis.summary`,
      DE/EN; `ui/app.py::_show_analysis()` übergibt `provider=result.cost.provider`)
      - macht auf einen Blick sichtbar, dass die Zahl je nach gewähltem
      Anbieter unterschiedlich sein kann/ist, statt wie ein pauschaler,
      immer gleicher Wert zu wirken. Gesamter Testlauf: 46 passed, 1 skipped.
    - Quelle: cloud.google.com/translate/pricing (Cloud Translation - Basic
      (v2): erste 500.000 Zeichen/Monat frei als 10-USD-Guthaben, danach
      20 USD pro Million Zeichen bis 1 Mrd. Zeichen/Monat).
- [x] Nutzerfrage geklärt + Bug behoben: "Sollte ein Providerwechsel die
  Analyse/Kostenschätzung und das Ergebnisfeld leeren, oder erst ein neuer
  Lauf?" Antwort: Analyse/Kostenschätzung ja, sofort - der Anbieter bestimmt
  Preis, Freikontingent und ob die Live-Kontingent-Zeile überhaupt gilt
  (nur DeepL); eine stehen gebliebene Schätzung eines anderen Anbieters wäre
  falsch UND über die Checkbox trotzdem bestätigbar gewesen. Das "Lauf und
  Ergebnis"-Feld (letzter abgeschlossener Lauf) dagegen bewusst NICHT - das
  dokumentiert ein bereits abgeschlossenes, weiterhin wahres Ergebnis
  (Ausgabedatei, QA-Bericht) und wird schon bisher erst beim nächsten
  tatsächlichen Start überschrieben (`MainWindow._start()`, unverändert) -
  entspricht dem bereits etablierten Verhalten bei Moduswechsel/neuer
  Quelldatei (`_mode_changed()`/`_choose_sources()`), die ebenfalls nur die
  Analyse zurücksetzen, nicht das Ergebnisfeld.
    - Bug dabei gefunden: Der Provider-ComboBox fehlte diese Verknüpfung
      komplett - eine bereits geprüfte und bestätigte (Checkbox aktiv)
      Analyse blieb nach einem Providerwechsel unverändert sichtbar,
      inklusive einer ggf. nicht mehr zutreffenden DeepL-Live-Kontingent-
      Zeile für einen inzwischen gewählten anderen Anbieter. Vermutlich beim
      Anlegen des Warnhinweis-Labels in der vorherigen Runde übersehen (der
      Provider-Wechsel-Handler wurde damals neu angelegt, aber nur an den
      Warnhinweis angebunden, nicht an `_invalidate_analysis()`).
    - Fix: `ui/app.py` - neuer Handler `_provider_changed()` bündelt beide
      Reaktionen auf `provider.currentTextChanged` (Warnhinweis
      aktualisieren + `_invalidate_analysis()` aufrufen) anstelle der
      bisherigen Direktverbindung nur auf den Warnhinweis.
    - Getestet: neuer Test
      `tests/test_ui_provider_credentials.py::test_switching_provider_invalidates_current_analysis`
      bestätigt, dass nach einem Providerwechsel `last_result` zurückgesetzt,
      die Bestätigen-Checkbox deaktiviert/entmarkiert und das Ergebnisfeld
      wieder auf "Analyse erforderlich" steht. Gesamter Testlauf: 47 passed,
      1 skipped.
- [x] **DOCX über denselben UI-Auftragsablauf wie PPTX angebunden**
  (RoadMap.md Phase 2/Word) - nach Nutzerentscheidung, den PPTX-Hauptfokus
  als abgeschlossen zu betrachten (eigener Live-Test mit Google bestätigt),
  war dies der nächste Punkt der empfohlenen Reihenfolge.
    - **Gemeinsame, formatunabhängige Bausteine ausgelagert:** neu
      `ui/document_job_common.py` (`PROVIDER_FACTORIES`, `build_provider()`,
      `DestinationConflictError`, `safe_destination()`) - vorher nur in
      `ui/pptx_job.py` definiert. `ui/pptx_job.py` importiert diese jetzt
      von dort und reicht sie unverändert weiter (`from ui.document_job_common
      import ...`), damit jeder bestehende `from ui.pptx_job import
      DestinationConflictError, safe_destination, ...`-Aufrufer (ui/app.py,
      ui/workers.py, tests/test_pptx_job.py, tests/manual_e2e_pptx_ui_translation.py)
      unverändert weiterfunktioniert. Bewusst NICHT eine gemeinsame
      "Dokument-Job"-Abstraktion für den gesamten Ablauf: PPTX' Überlauf-
      risiko-Vergleich (feste Textbox-Größe) hat keine sinnvolle Entsprechung
      bei DOCX (fließt automatisch um), Word hat dafür stattdessen die
      Break-Marker-Anomalie-Prüfung - beide Job-Module bleiben eigenständig
      und spiegeln sich nur in Struktur/Namensgebung, siehe Modul-Docstrings.
    - **pipeline/word/translate_document.py erweitert** (bisher ohne
      Abbruch-/Live-Fortschritts-Unterstützung, im Gegensatz zum
      PPTX-Pendant `translate_presentation()`):
      - Neu: `should_cancel`-Parameter, vor jedem Absatz geprüft (Hauptteil-
        Schleife, dann Kopf-/Fußzeilen-Schleife) - genau dasselbe
        kooperative Abbruch-Verhalten wie bei `translate_presentation()`
        (zwischen, nie während eines API-Aufrufs). Neues
        `TranslationStats.cancelled`-Feld.
      - Neu: `stats_callback`-Parameter, nach jedem Absatz mit
        abgeschlossenem Ergebnis aufgerufen (übersetzt/übersprungen/
        fehlgeschlagen) - treibt die Live-Fortschrittsanzeige im UI, ohne
        dass der Aufrufer selbst mitzählen muss.
      - Neu: `TranslationStats.errors: list[str]` - Absatz-/Kopf-/
        Fußzeilen-Fehler wurden bisher nur über `progress_callback`
        durchgereicht und dann verworfen (nicht in `stats` gespeichert);
        jetzt wie bei `PresentationTranslationStats.errors` gesammelt
        (`"body:{index}: {ExceptionType}: {message}"` bzw.
        `"header:{index}: ..."`/`"footer:{index}: ..."`), damit der
        QA-Bericht (siehe unten) sie auflisten kann, ohne Zugangsdaten
        preiszugeben (TranslationError-Meldungen enthalten ohnehin nie
        welche - dieselbe bereits für PPTX geltende Garantie).
      - Neu: `TranslationStats.processed`-Property (Summe aus
        `translated`/`skipped`/`failed`) sowie an
        `PresentationTranslationStats` neu ergänzte, rein additive
        Alias-Properties `translated`/`skipped`/`failed`/`processed`
        (delegieren an die bestehenden `paragraphs_*`-Felder) - lässt
        `ui/app.py`s Job-Status-Code (`_job_stats()`/`_update_job_status()`/
        `_show_job_result()`) beide Stats-Typen über dieselben
        Attributnamen lesen, ohne an jeder Stelle `isinstance()` zu
        verzweigen. Die ursprünglichen, format-eigenen Feldnamen
        (`paragraphs_translated` bzw. `body_translated`/...) bleiben
        unverändert die primären, von bestehenden Aufrufern (u. a.
        ico_translate/batch.py) weiterhin genutzten Namen.
      - Neu: `total_paragraph_count(engine)` (Hauptteil- + Kopf-/Fußzeilen-
        Absätze, ohne API-Aufruf) - Wort-Pendant zu
        `translate_presentation.total_paragraph_count()`, treibt denselben
        determinierten Fortschrittsbalken wie beim PPTX-Job.
    - **Neu: `ui/word_job.py`** (`run_word_job()`, `WordJobResult`) - spiegelt
      `ui/pptx_job.py::run_presentation_job()` strukturell (Zielkonflikt-
      Prüfung vor jedem API-Aufruf, Kosten-Guard, `total_callback` einmalig
      vor dem ersten Aufruf, QA-Bericht neben der Ausgabedatei). QA-Bericht
      enthält statt eines Überlaufvergleichs (den es für DOCX nicht gibt):
      Hauptteil-/Kopf-/Fußzeilen-Aufschlüsselung, `new_break_anomalies`
      (bereits vorhandene, bisher ungenutzte `<br/>`-Zähl-Abweichungs-
      Erkennung aus `html_bridge.py` - jetzt sichtbar statt nur in einer
      Log-Datei verborgen), Fehlerliste, und einen expliziten Hinweis auf
      die offene, noch nicht automatisiert geprüfte PAGE-Feld-Frage
      (RoadMap.md Phase 2/Word) statt diese Einschränkung stillschweigend
      zu verschweigen.
    - **ui/workers.py:** neue `WordTranslationWorker`-Klasse, spiegelt
      `PresentationTranslationWorker` 1:1 (identische Konstruktor-Signatur,
      dieselbe `TranslationSignals`-Klasse) - ruft nur `run_word_job()`
      statt `run_presentation_job()` auf. Neuer `_copy_word_stats()`-Helfer
      (Pendant zu `_copy_stats()`) snapshotet `TranslationStats` vor dem
      Überqueren der Qt-Signal-/Thread-Grenze.
    - **ui/app.py:** `_EXECUTABLE_MODES` um `TranslationMode.WORD` erweitert
      (vorher nur `PRESENTATION`) - der direkte PDF-Modus bleibt bewusst
      weiterhin blockiert (`start.blocked_mode`), bis seine offenen
      Qualitätsbefunde geklärt sind. `_start()` wählt jetzt
      `WordTranslationWorker` oder `PresentationTranslationWorker` je nach
      `request.mode` - der gesamte restliche Ablauf (Zugangsdaten-Prüfung,
      Zielordner-Dialog, Kostenbestätigung, Fortschritt, Abbruch, Ergebnis-
      anzeige, Ordner-/Bericht-öffnen-Buttons) ist identisch für beide
      Modi und war es schon vorher (baut auf den bereits vorhandenen,
      formatunabhängig beschrifteten "Lauf und Ergebnis"-Widgets auf).
      `_job_stats()`/`_update_job_status()`/`_show_job_result()` nutzen
      jetzt die neuen formatunabhängigen `.processed`/`.translated`/
      `.skipped`/`.failed`-Aliase statt der PPTX-spezifischen
      `paragraphs_*`-Namen; die Überlauf-Zeile im Ergebnistext erscheint
      weiterhin nur für `PresentationJobResult` (`isinstance`-Prüfung) -
      für DOCX würde "Keine neuen Überlaufrisiken gefunden" fälschlich
      einen durchgeführten Check suggerieren, den es für DOCX nicht gibt.
    - **Neue Test-Fixture `tests/fixtures/representative.docx`:** es gab
      bisher keine automatisierte DOCX-Fixture (der Word-Pfad wurde bislang
      ausschließlich manuell gegen echte, nicht im Repo enthaltene
      ICO-Dokumente verifiziert, siehe ältere Einträge oben). Erzeugt mit
      python-docx (Kopf-/Fußzeile + 3 Hauptteil-Absätze, davon einer leer)
      und anschließend gezielt nachbearbeitet: `DocxEngine` erwartet
      hartkodiert `word/header2.xml`/`word/footer1.xml`
      (siehe `pipeline/word/docx_engine.py::_HEADER_PATH`/`_FOOTER_PATH` -
      dokumentierte Vereinfachung, keine allgemeine Mehrabschnitts-Auflösung
      über die Section-Relationship), python-docx erzeugt bei einem
      Ein-Abschnitt-Dokument aber `header1.xml` (Footer trifft mit
      `footer1.xml` zufällig bereits den erwarteten Namen) - die Kopfzeilen-
      Datei sowie ihr Verweis in `[Content_Types].xml` und
      `word/_rels/document.xml.rels` wurden deshalb nach der Erzeugung
      innerhalb des Zip-Archivs umbenannt/angepasst. Verifiziert: `DocxEngine`
      liest die Fixture korrekt (3 Hauptteil-Absätze, 2 Kopf-/Fußzeilen-
      Absätze, alle korrekt als übersetzbar/nicht übersetzbar markiert).
    - Getestet: `tests/test_word_job.py` (7 Tests, spiegelt
      `tests/test_pptx_job.py`) - Grundlauf inkl. QA-Bericht-Inhalt,
      Zielkonflikt-Ablehnung (Ziel existiert bereits / Ziel == Quelle) ohne
      jeden API-Aufruf, Abbruch zwischen API-Aufrufen mit korrektem
      Teilergebnis, `stats_callback`-Inkremente, `total_callback` bereits
      vor dem ersten API-Aufruf gemeldet (Regressionsschutz gegen dieselbe
      "Balken zeigt immer 100%"-Klasse von Bug wie beim PPTX-Fund weiter
      oben), Budget-Limit-Durchsetzung. `tests/test_ui_word_mode.py`
      (3 Tests, echtes `MainWindow`, `QThreadPool.start()` abgefangen statt
      wirklich auf einem Hintergrund-Thread zu laufen): bestätigt, dass
      `_start()` für Word-Modus tatsächlich einen `WordTranslationWorker`
      und für Präsentations-Modus weiterhin einen `PresentationTranslationWorker`
      erzeugt (parametrisierter Test gegen beide Fälle), sowie dass
      Word-Modus nicht mehr als `start.blocked_mode` blockiert gilt.
      Gesamter Testlauf: 57 passed, 1 skipped.
    - Noch offen (siehe RoadMap.md Phase 2/Word): ein echter Live-Lauf des
      DOCX-UI-Pfads gegen ein reales Dokument über einen echten Provider
      steht noch aus (bisher nur mit Fake-Provider gegen die neue Fixture
      automatisiert getestet, analog zum PPTX-Pfad vor dessen jetzt
      erfolgtem Live-Test).

- [x] Explizite "ICO-Dokument"-Option im UI ergänzt (17.08.2026), als Antwort
  auf einen bislang unangetasteten Schwachpunkt: `DocxEngine._has_separator_shape()`
  lief bis dahin bei JEDEM `.open()`-Aufruf unbedingt mit - jedes DOCX, das
  zufällig eine ähnliche Trennform enthielt, hätte ohne jede Warnung einen
  Teil von Seite 1 unübersetzt gelassen. Der Nutzer bestätigte, dass dieser
  Sonderfall (Metadatenbereich auf Seite 1 nicht übersetzen) nur für einen
  bestimmten internen Dokumententyp gilt, den er "ICO" nennt - genau die
  Dokumente, die dieses Projekt ohnehin schon bearbeitet (siehe die
  ico_translate/-Einträge weiter oben).
    - `pipeline/word/docx_engine.py`: `DocxEngine.open()` bekommt einen neuen
      Parameter `ico_mode: bool = False`. Der Scan nach der Trennform läuft
      jetzt nur noch, wenn `ico_mode=True` explizit übergeben wird; sonst
      bleiben alle Hauptteil-Absätze `translatable=True`, unabhängig davon,
      ob eine Trennform zufällig vorhanden ist. `self.separator_found`
      bleibt wie zuvor verfügbar (jetzt: "wurde bei aktivem ico_mode
      gefunden?").
    - Zwei bestehende, von diesem Default-Wechsel betroffene Aufrufer
      korrigiert, damit ihr bisheriges (für ihren jeweiligen Zweck
      korrektes) Verhalten erhalten bleibt: `ui/analysis.py` (Kostenschätzung
      im Word-Modus) übergibt jetzt `ico_mode=request.ico_mode` - sonst
      hätte die Kostenschätzung vor dem Lauf nicht mehr zum tatsächlichen
      Lauf gepasst. `pipeline/word/duplicate_analysis.py::_analyze_one()`
      (Duplikat-Kandidaten-Heuristik, die per Definition ausschließlich
      ICO-Dokumente vergleicht) übergibt jetzt explizit `ico_mode=True`, um
      seine bisherige Metadaten-/Textkörper-Trennung für die
      Ähnlichkeitsanalyse unverändert beizubehalten.
    - `ui/word_job.py`: `run_word_job()` bekommt denselben `ico_mode`-Parameter
      (Default `False`) und reicht ihn an `DocxEngine.open()` durch. Der
      QA-Bericht bekommt einen neuen Kopfabschnitt, der den tatsächlichen
      Ausgang klar benennt: "ICO-Modus: aktiv" (+ Bestätigung, dass der
      Metadatenbereich ausgeschlossen wurde) bei Treffer, eine deutliche
      Warnung bei `ico_mode=True` aber `separator_found=False` ("bitte
      prüfen, ob dieses Dokument wirklich vom internen Typ ICO ist"), oder
      "ICO-Modus: nicht aktiv" im Normalfall.
    - `ui/models.py`: `TranslationRequest` um `ico_mode: bool = False`
      erweitert. `ui/app.py`: neue Checkbox (Zeile "ICO-Dokument" im
      Formular, per `QFormLayout.setRowVisible()` nur im Word-Modus
      sichtbar/aktiv - kein PPTX-Äquivalent, da PPTX keinen entsprechenden
      Sonderfall hat) mit Tooltip, der den Override-Charakter erklärt
      (erzwingt den Ausschluss unabhängig vom Ergebnis der automatischen
      Erkennung). Beim Verlassen des Word-Modus wird die Checkbox
      automatisch zurückgesetzt, damit ein versehentlich aktivierter Zustand
      nicht stillschweigend in einen Auftrag für einen anderen Modus
      übernommen wird (`MainWindow._mode_changed()`). Während eines
      laufenden Auftrags gesperrt wie die übrigen Eingabefelder
      (`_set_running()`).
    - `ui/workers.py`: `WordTranslationWorker` bekommt denselben
      `ico_mode`-Parameter (Default `False`) und reicht ihn an
      `run_word_job()` durch - bewusst NICHT auf
      `PresentationTranslationWorker` übertragen (siehe deren Docstrings):
      `ui/app.py::_start()` übergibt `ico_mode` deshalb nur als zusätzliches
      Schlüsselwortargument, wenn der gewählte Modus tatsächlich Word ist,
      statt beide Worker-Konstruktoren künstlich symmetrisch zu halten.
    - Neue Test-Fixture `tests/fixtures/representative_ico.docx`: wie
      `representative.docx`, plus ein vorangestellter Metadaten-Absatz
      ("ICO Metadata: Issuer XYZ") gefolgt von einem Absatz mit der
      straightConnector1-Trennform (`<a:prstGeom prst="straightConnector1">`
      in einem minimalen DrawingML-Fragment) - erstmals automatisierte
      Testabdeckung für `_has_separator_shape()`/die Trennform-Erkennung
      selbst, vorher nur manuell gegen echte ICO-Dokumente verifiziert.
    - Getestet: `tests/test_word_job.py` (3 neue Tests) - `ico_mode=True`
      mit gefundener Trennform lässt den Metadaten-Absatz unverändert
      (geprüft direkt am geschriebenen `word/document.xml` der
      Ausgabedatei, nicht nur über Zähler, da der Trennform-Absatz selbst
      wegen seines `<w:drawing>` unabhängig von `ico_mode` als "übersetzt"
      gezählt wird - ein bereits vor dieser Änderung bestehendes,
      unverändertes Detailverhalten); `ico_mode=False` übersetzt denselben
      Metadaten-Absatz trotz vorhandener Trennform ganz normal;
      `ico_mode=True` ohne gefundene Trennform (gegen die alte Fixture ohne
      Trennform) übersetzt das gesamte Dokument wie zuvor und meldet die
      Warnung im QA-Bericht. `tests/test_ui_word_mode.py` (3 neue Tests) -
      Checkbox nur im Word-Modus sichtbar/aktiv und wird beim Moduswechsel
      zurückgesetzt, `_request()` übernimmt den Checkbox-Zustand korrekt,
      `_start()` reicht `ico_mode` tatsächlich an den erzeugten
      `WordTranslationWorker` durch. Gesamter Testlauf: 63 passed, 1 skipped.
    - Bewusst NICHT umgesetzt: das PDF-Gegenstück. Die zugrundeliegende
      Erkennung existiert dort bereits (`FIRST_PAGE_ANCHOR_TERMS`/
      `_split_first_page_metadata()` bzw. `DocumentTemplate.first_page_zones`/
      `templates/virelicon.json`), läuft aber ebenfalls automatisch statt
      user-gesteuert - wird erst sinnvoll nachrüstbar, sobald der direkte
      PDF-Pfad überhaupt ans UI angebunden ist (RoadMap.md Phase 2/PDF). Der
      Duplikat-Text-Bug, der das bisher blockiert hatte, ist jetzt behoben
      (17.08.2026, siehe unten) - die PDF-UI-Anbindung selbst steht aber
      weiterhin aus.

- [x] Duplikat-Text-Bug im Redact/Insert-Pfad reproduziert und Fix verifiziert
  (17.08.2026, RoadMap.md Phase 2/PDF). Ausgangslage: `tests/manual_diagnose_text_duplication.py`
  (nur mit der echten, vertraulichen "1526 Virelicon.pdf" plus einem echten
  DeepL-Aufruf lauffähig, deshalb weder hier noch in CI ausführbar) hatte
  ursprünglich drei Symptome gemeldet: (1) Textduplikation - nach einem
  Textabschnitt erscheint ein abgeschnittener Rest DESSELBEN Texts erneut,
  (2) unerklärte Suffixe an Zuschreibungszeilen, (3) verlorene
  Bold/Underline-Formatierung + verschmolzene Überschrift/Bullet-Zeile +
  wachsende Lücken zwischen Bullet-Blöcken. Diese Session hat sich
  ausschließlich auf (1) konzentriert (das vom Nutzer benannte "Duplikat
  Text"-Problem) - (2) und (3) bleiben offen/unverifiziert, siehe
  RoadMap.md.
    - Analyse: laut Code-Kommentaren in `pipeline/pdf/pymupdf_engine.py`
      (`_insert_html_text()`, `PyMuPdfEngine._collision_aware_max_y1()`)
      wurde der naheliegendste Mechanismus für (1) - ein Block wächst beim
      Einfügen der Übersetzung ungeprüft in die Zeile des NÄCHSTEN Blocks
      hinein, dessen später eigener Redact/Insert-Durchlauf das Überwachsene
      dann nicht mit erfasst - bereits VOR dieser Session behoben: der
      Kollisionsschutz (`_next_block_y0()`/`_collision_aware_max_y1()`, mit
      spaltenbewusstem x-Overlap-Check) gilt inzwischen für ALLE Blöcke, nicht
      mehr nur für `block.highlighted` (siehe die frühere "Kollisionsschutz"-
      Eintragsgruppe weiter oben in dieser Datei). Diese Session hat den Fix
      NICHT erneut verändert, sondern gezielt geprüft, ob er das gemeldete
      Symptom tatsächlich beseitigt - das war bisher nur über Verdacht/
      Analogieschluss ("almost certainly the actual cause", Code-Kommentar)
      dokumentiert, nie an einer konkreten Duplikations-Reproduktion bestätigt.
    - Eigene Reproduktion (ohne die reale Datei, da nicht verfügbar): drei
      synthetische PDFs direkt mit PyMuPDF gebaut (echter gezeichneter Text,
      also von `extract_blocks()` genuin erkannte `TextBlock`s, keine
      handgebauten Objekte), durch den echten Produktionscode
      (`PyMuPdfEngine.redact_block()`/`insert_text()`) mit absichtlich stark
      überlangen HTML-"Übersetzungen" (Platzhalter, analog zum bestehenden
      Projekt-Muster aus `tests/manual_test_highlight_growth.py`s
      "7x überlanger Platzhalter") geschickt, dann die finale Seite per
      `page.get_text()` auf das exakte gemeldete Fehlerbild geprüft
      (Original-Englisch übersteht die Redaction nicht; jede Übersetzung
      erscheint exakt so oft wie im Input vorgegeben, nie öfter):
      1. Moderater Overflow bei zwei eng benachbarten (16.5pt Abstand),
         nicht-highlighted Blöcken - wächst korrekt bis zur Kollisionsgrenze
         (bestätigt über den `growth_capped_by_collision`-Log-Eintrag), keine
         Duplikation, kein Englisch-Rest.
      2. Extremer Overflow (40x wiederholter Platzhaltersatz), der selbst bei
         Schriftverkleinerung bis `_MIN_FONT_SIZE` nicht passt und den
         `scale_low=0`-Fallback erzwingt - ebenfalls sauber (PyMuPDFs
         Auto-Skalierung darf dabei legitim einen Teil des Textes weglassen,
         das ist kein Duplikations-Bug, aber die Anzahl darf nie GRÖSSER als
         die Eingabe sein - genau das wird geprüft).
      3. Highlighted-Zitat-Block, dessen Übersetzung länger als die
         ursprüngliche Highlight-Fläche ist und `_grow_highlight_if_needed()`s
         Redact-dann-Neuzeichnen-dann-Neueinfügen-Pfad auslöst (der einzige
         Fall im Code, der für denselben Block absichtlich einen ZWEITEN
         `insert_text()`-Aufruf macht) - ebenfalls sauber.
      Alle drei Fälle: kein Rest des englischen Originaltexts nach der
      Redaction, jede Übersetzung erscheint exakt so oft wie vorgegeben.
    - Neu: `tests/test_pdf_redact_insert_collision.py` (3 Tests, erste
      automatisierte Testabdeckung für `PyMuPdfEngine` überhaupt - vorher
      ausschließlich über manuelle Skripte gegen echte/vertrauliche
      Dokumente verifiziert) - baut sich jede synthetische PDF selbst
      (`fitz.open()` + `insert_textbox()`/`draw_rect()`), isoliert
      `_GROWTH_ANOMALY_LOG_PATH` per `monkeypatch` auf einen `tmp_path`
      (sonst gemeinsamer, testlaufübergreifender Log-Pfad → Flakiness),
      und prüft direkt am gespeicherten Ausgabe-PDF. Gesamter Testlauf:
      66 passed, 1 skipped.
    - Bewusst NICHT geprüft: die real gemeldeten Symptome (2) und (3) oben
      (Zuschreibungs-Suffixe, Bold/Underline-Verlust + Bullet-Lücken) - diese
      wurden in der ursprünglichen Diagnose als von (1) unabhängige,
      separate Befunde behandelt und sind hier nicht adressiert. Ebenso
      NICHT geprüft: eine finale Bestätigung gegen die tatsächliche
      "1526 VIRELICON.pdf" mit einem echten Provider-Aufruf, wie es
      `tests/manual_diagnose_text_duplication.py` ursprünglich vorsah -
      diese Datei ist in dieser Umgebung nicht verfügbar; sobald sie
      wieder zugänglich ist, wäre ein realer Lauf dieses Skripts der letzte
      Bestätigungsschritt, ist aber angesichts der synthetischen
      Reproduktion oben nicht mehr als Blocker für die weitere PDF-Arbeit
      zu werten.

- [x] Direkte PDF-Pipeline an den gemeinsamen UI-Auftragsablauf angebunden
  (17.08.2026, RoadMap.md Phase 2/PDF) - der letzte der drei ursprünglichen
  Dokumenttypen (nach PPTX und DOCX). Gebaut nach dem exakt gleichen
  Muster, jetzt zum dritten Mal angewendet.
    - Neu: `pipeline/pdf/translate_pdf.py` - bisher gab es KEINE
      wiederverwendbare Übersetzungsschleife für PDF überhaupt, nur
      Inline-Code in `tools/compare_providers.py` und diversen
      `tests/manual_translate_*.py`-Skripten, alle nach demselben Muster:
      ERST alle Blöcke übersetzen (alles-oder-nichts pro Anbieter, keine
      Fortschritts-/Abbruchunterstützung), DANN erst redigieren/einfügen.
      Für den UI-Auftragsablauf (Fortschrittsbalken, Abbrechen-Knopf,
      Teilergebnis bei Abbruch) war das nicht brauchbar - `translate_pdf()`
      verschachtelt stattdessen pro Block: übersetzen → redigieren →
      einfügen → Stats melden, exakt nach demselben Muster wie
      `translate_presentation()`/`translate_document()` (kooperative
      Abbruchprüfung NUR zwischen API-Aufrufen, ein fehlgeschlagener Block
      wird übersprungen statt den ganzen Lauf abzubrechen - dieselbe
      "skip, don't abort"-Politik). `total_block_count()` (Pendant zu
      `total_paragraph_count()`) sammelt vorab über `engine.get_pages()`/
      `extract_blocks()` die Gesamtzahl, bevor irgendein API-Aufruf
      stattfindet - wichtig für denselben "Balken zeigt sonst immer
      100%"-Bug, der bei PPTX/Word schon einmal gefunden wurde.
    - `PdfTranslationStats` (translated/skipped/failed/chars_sent/
      cancelled/errors wie bei den anderen beiden Formaten) plus ein
      PDF-eigenes Feld: `overflow_blocks` - Anzahl der Blöcke, bei denen
      `insert_text()` `False` zurückgab (siehe `pipeline/pdf/
      pymupdf_engine.py`: der Text wurde zwar garantiert eingefügt, aber
      nicht "sauber" bei der Originalgröße, sondern über Wachstum/
      Schrumpfung/Force-Fit). Kein Fehler, aber ein eigenes drittes
      Risikoprofil neben PPTX' Überlaufrisiko (feste Textbox-Größe) und
      Words PAGE-Feld-Risiko (automatischer Reflow) - im QA-Bericht und im
      UI-Statustext separat ausgewiesen (`job.pdf_overflow_none`/
      `job.pdf_overflow_count` in `ui/i18n.py`).
    - Neu: `ui/pdf_job.py` (`PdfJobResult`, `run_pdf_job()`) - spiegelt
      `ui/word_job.py` exakt (Zielkonflikt-Prüfung vor jedem API-Aufruf,
      `TranslationBudgetGuard`-Kapselung, `total_callback` vor dem ersten
      API-Aufruf, deutschsprachiger QA-Bericht). Kein `DocumentTemplate`
      wird übergeben (header_bbox/footer_bbox/first_page_zones bleiben
      unbesetzt) - nur der automatische, templatefreie
      `FIRST_PAGE_ANCHOR_TERMS`-Split gilt; ein `ico_mode`-Äquivalent wie
      bei Word gibt es bewusst noch nicht (RoadMap.md Phase 2/PDF, "Nach
      Anbindung" vorgemerkt). Der QA-Bericht katalogisiert ausdrücklich die
      weiterhin offenen PDF-Detailfragen (Link-Annotationen, Durchsuchbar-
      keit, Glyphen/Ligaturen, Font-Erhalt) statt sie zu verschweigen.
    - `ui/workers.py`: `PdfTranslationWorker` (+ `_copy_pdf_stats()`)
      spiegelt `WordTranslationWorker`/`PresentationTranslationWorker`
      exakt, ohne `ico_mode`-Parameter (kein PDF-Äquivalent bisher).
    - `ui/app.py`: `_EXECUTABLE_MODES` um `TranslationMode.PDF` erweitert.
      Die Worker-Auswahl in `_start()` war bisher ein zweiseitiges
      `if/else` (PPTX vs. "sonst Word") - das hätte PDF beim Hinzufügen
      unbemerkt auf `WordTranslationWorker` geroutet. Umgestellt auf ein
      Dict-Lookup (`{TranslationMode.X: WorkerCls, ...}[request.mode]`),
      das bei einem künftigen vierten Modus mit einem klaren `KeyError`
      statt einem stillen Fehlrouting ausfällt. Neuer `elif
      isinstance(result, PdfJobResult)`-Zweig in `_show_job_result()` für
      die `overflow_blocks`-Anzeige (Pendant zum PPTX-Überlaufrisiko-
      Zweig). Nebenbei behoben: `_job_failed()`s Log-Meldung war seit der
      DOCX-Anbindung fälschlich fest auf "PPTX-Übersetzungslauf
      fehlgeschlagen" verdrahtet, unabhängig vom tatsächlichen Modus -
      jetzt formatneutral.
    - Neue Test-Fixture `tests/fixtures/representative.pdf`: ein
      übersetzbarer Absatz plus ein linkannotierter Absatz
      (`translatable=False`, da `PyMuPdfEngine.extract_blocks()` jeden
      Block ausschließt, der eine Link-Annotation überlappt) - erste
      automatisierte Testabdeckung für den kompletten `ui/pdf_job.py`-
      Auftragsablauf.
    - Getestet: `tests/test_pdf_job.py` (7 Tests, spiegelt
      `tests/test_word_job.py`) - Grundlauf inkl. QA-Bericht-Inhalt,
      Zielkonflikt-Ablehnung (Ziel existiert bereits / Ziel == Quelle) ohne
      jeden API-Aufruf, Abbruch mit korrektem Teilergebnis,
      `stats_callback`-Inkremente, `total_callback` bereits vor dem ersten
      API-Aufruf gemeldet, Budget-Limit-Durchsetzung.
      `tests/test_ui_word_mode.py` (2 neue Tests, Datei deckt inzwischen
      alle drei ausführbaren Modi ab, nicht mehr nur Word) - bestätigt,
      dass `_start()` für PDF-Modus tatsächlich einen
      `PdfTranslationWorker` erzeugt (dritter Fall im bereits
      parametrisierten Dispatch-Test) und dass PDF-Modus nicht mehr als
      `start.blocked_mode` blockiert gilt. Gesamter Testlauf: 75 passed,
      1 skipped.
    - Noch offen (siehe RoadMap.md Phase 2/PDF): ein echter Live-Lauf des
      PDF-UI-Pfads gegen ein reales Dokument über einen echten Provider
      steht noch aus (analog zum bereits erledigten PPTX-Live-Lauf und dem
      weiterhin ausstehenden Word-Live-Lauf); außerdem bleiben die
      zahlreichen, im PDF-Abschnitt der Roadmap aufgelisteten
      Detailqualitätsfragen unverändert offen - diese Session hat sie NICHT
      angefasst, nur dafür gesorgt, dass sie im QA-Bericht sichtbar
      bleiben statt die UI-Anbindung auf ihre vollständige Klärung warten
      zu lassen.

- [x] Alle sechs im PDF-Abschnitt von RoadMap.md Phase 2/PDF verbliebenen
  Detailfragen der Reihe nach untersucht, wo machbar mit Fix und
  permanenter, dateiunabhängiger Regressionsabdeckung (17.08.2026, wie vom
  Nutzer angefragt: "alle nacheinander prüfen", Glyphen-Verlust und
  Font-Erhalt kombiniert als eine Architekturfrage). Vier reale Bugs
  gefunden und behoben, zwei Punkte als grundsätzlich in Ordnung
  verifiziert, ein Punkt als real und aktuell NICHT sinnvoll behebbar
  bestätigt, ein Punkt als offene Architekturentscheidung bestätigt.
  Gesamter Testlauf am Ende: 93 passed, 1 skipped (vorher 75 passed, 1
  skipped - 18 neue Tests in 5 neuen Dateien). Im Einzelnen:

  1. **Link-Annotationen nach Redaction (behoben).** Löst die offene
     Prüffrage aus Zeile 89 im Abschnitt "Zu verifizieren" oben ab.
     Direkt reproduziert: `page.apply_redactions()` löscht kommentarlos
     JEDE Annotation, deren Rechteck die redigierte Fläche berührt -
     auch Link-Annotationen, die zu einem völlig anderen, nicht
     redigierten Block gehören und nur zufällig räumlich in der Nähe
     liegen (z. B. wenn ein Block wächst oder das Layout eng ist). Da
     ein Link-Block per `extract_blocks()` immer `translatable=False`
     ist, wird der Link selbst NIE direkt redigiert - der Verlust
     passiert ausschließlich als Nebenwirkung der Redaction eines
     ANDEREN Blocks.
       - Erster Lösungsansatz verworfen, BEVOR er verdrahtet wurde: pro
         `redact_block()`-Aufruf sofort per `get_links()`-Vorher/Nachher-
         Vergleich wiederherstellen. Direkt widerlegt: ein per
         `page.insert_link()` wiederhergestellter Link ist für
         `get_links()` im REST derselben laufenden Session unsichtbar
         (nur nach `save()`+Neuöffnen wieder sichtbar) - eine SPÄTERE,
         zweite Redaction, die denselben Link erneut trifft, zerstört
         ihn erneut, ohne dass ein Vorher/Nachher-Vergleich das erkennen
         könnte (beide Messungen zeigen `[]`). Direkt reproduziert und
         verifiziert, bevor der fehlerhafte Ansatz verworfen wurde.
       - Tatsächlicher Fix: `PyMuPdfEngine.open()` liest jetzt einmalig,
         vor jeder Redaction, alle Links jeder Seite in
         `self._original_links`. `save()` gleicht unmittelbar vor dem
         eigentlichen Schreiben einmalig ab und stellt per
         `page.insert_link()` alles wieder her, was im Snapshot war,
         aber jetzt fehlt (`PyMuPdfEngine._restore_missing_links()`,
         `_link_identity()` für den Abgleich ohne `xref`/`id`, die die
         ursprüngliche, bereits gelöschte Annotation identifizieren und
         beim Wiedereinfügen zu einem `KeyError` tief in PyMuPDFs
         eigener ID-Kollisionsprüfung führen würden). Läuft nur EINMAL
         pro Dokument, nicht pro Redaction - immun gegen das
         Sichtbarkeitsproblem oben.
       - Neu: `tests/test_pdf_link_preservation.py` (4 Tests) - dokumentiert
         das Sichtbarkeitsproblem direkt, belegt den unbehandelten Bug als
         Baseline, und verifiziert sowohl den Wiederherstellungsfall als
         auch den Fall, dass ein nie betroffener Link nicht versehentlich
         doppelt eingefügt wird.

  2. **Durchsuchbarkeit/Copy-Paste-Qualität (verifiziert, ein bestätigter
     Sonderfall).** Löst die offene Prüffrage aus Zeile 90 oben ab.
     Grundsätzlich in Ordnung: Umlaute, Akzente und normale Sonderzeichen
     (getestet u. a. "Ärger über großße Straßen") werden korrekt
     eingefügt UND sind per `page.search_for()` wiederauffindbar. Die
     eine bestätigte Ausnahme ist die `fi`-Ligatur-Problematik, siehe
     Punkt 5 unten (beide Punkte teilen dieselbe Ursache und wurden
     gemeinsam untersucht).

  3. **Leerzeilen/Underline/Inline-Formatierung (verifiziert, keine
     Regression gefunden).** `spans_to_html()` (Absatz-/Zeilenumbruch-
     Marker, `<u>`/`<b>`/`<i>`-Verschachtelung, HTML-Escaping) hatte
     bisher KEINE direkte Testabdeckung. Per Direkttest bestätigt:
     Unterstreichung/Fett/Kursiv überstehen den vollen
     `redact_block()`/`insert_text()`/`save()`-Rundlauf UND sind über
     eine erneute `extract_blocks()`-Extraktion des Ergebnis-PDFs korrekt
     wiedererkennbar (wichtiger methodischer Fallstrick dabei: ein
     Ad-hoc-Test gegen `page.get_text("dict")` OHNE die projekteigenen
     `_EXTRACT_FLAGS` - siehe Kommentar oben in
     `pipeline/pdf/pymupdf_engine.py` - lieferte zunächst fälschlich
     `char_flags` ohne Underline-Bit; erst mit `flags=_EXTRACT_FLAGS`
     stimmt der Befund). Neu: `tests/test_pdf_formatting_roundtrip.py`
     (6 Tests: `spans_to_html()` isoliert plus ein voller
     Engine-Rundlauf). Vorbehalt aus der Roadmap-Formulierung ("an
     mehreren realen Dokumenten und Providern") bleibt bestehen - diese
     Abdeckung ist synthetisch, kein Mehrfach-Dokument/Mehrfach-Provider-
     Test.

  4. **Glyphen-Verlust + Font-Erhalt, kombiniert wie vom Nutzer gewünscht
     (Glyphen-Verlust-Teil behoben, Font-Erhalt-Teil als offene
     Architekturfrage bestätigt).** Font-Erhalt: bestätigt (Codesuche),
     dass `TextBlock.font_name` nirgends in `pymupdf_engine.py` zur
     Einfügung gelesen wird - Einfügung nutzt immer entweder die
     Base-14-Helvetica-Varianten (`_FONT_VARIANTS`, reiner Textpfad) oder
     CSS `font-family: sans-serif` (HTML/Story-Pfad), unabhängig von der
     tatsächlichen Schrift des Originaldokuments. Bestätigt bereits
     dokumentierte Einschränkung (Zeile 114 oben) erneut, kein neuer
     Fix - Font-Extraktion/-Einbettung ist eine Projektentscheidung, kein
     chirurgischer Patch.
       - Glyphen-Verlust: beim Untersuchen des Font-Erhalt-Punkts direkt
         reproduziert, dass der reine Textpfad (`_insert_plain_text()`,
         erreichbar wenn `block.spans` leer ist - laut Docstring nur
         "backward compatibility", in der Praxis über `translate_pdf()`
         aktuell NICHT erreichbar, da echte Blöcke immer Spans haben,
         aber ungeschützt, falls sich das je ändert) nicht-lateinische
         Schriften kommentarlos durch "?" ersetzt: Kyrillisch/
         Griechisch/CJK wurden vollständig zu Fragezeichen, während
         `insert_text()` trotzdem `True` zurückgab (kein Fehler, kein
         Signal). Ursache: die Base-14-Helvetica-Varianten sind auf
         WinAnsiEncoding fixiert. Der HTML/Story-Pfad (verwendet, wann
         immer `block.spans` nicht leer ist - also der reale
         Produktionspfad) wurde im direkten Vergleich getestet und
         übersteht denselben Text fehlerfrei (MuPDFs automatischer
         Unicode-Font-Fallback). Fix: `insert_text()` leitet reinen Text
         mit einem Zeichen außerhalb von WinAnsiEncoding jetzt über den
         HTML/Story-Pfad um, statt ihn über `insert_textbox()` still zu
         beschädigen (`_plain_text_needs_unicode_fallback()`,
         `_plain_text_to_html()`, beide in `pipeline/pdf/pymupdf_engine.py`
         - Letztere teilt sich die Absatz-Regruppierungslogik mit
         `_insert_plain_text()` über die neue, aus beiden extrahierte
         `_regroup_paragraphs()`). Neu: `tests/test_pdf_glyph_preservation.py`
         (4 Tests). Wichtiger Vorbehalt: dieser Fix betrifft NICHT die in
         Zeile 96 unten dokumentierte, andersartige Symbol-/Private-Use-
         Area-Glyphen-Lücke (z. B. Wingdings-artige Bullet-Zeichen wie
         U+F086) - das ist ein Font-Glyph-Problem, kein
         Unicode-Encoding-Problem, und bleibt unverändert offen.

  5. **`fi`-Ligatur bei Textsuche/Copy-Paste (bestätigt, aktuell NICHT
     sinnvoll behebbar).** Löst die offene Frage aus Zeile 97 unten ab
     ("noch nicht geprüft, ob das kontrollierbar ist"). Direkt
     reproduziert: der HTML/Story-Pfad (`insert_htmlbox()`) ersetzt
     `office`/`fine`/`film`/`fluffy`/`first` kommentarlos durch
     `oﬃce`/`ﬁne`/`ﬁlm`/`ﬂuﬀy`/`ﬁrst` (OpenType-"liga"-Feature) - Suche
     UND Kopieren liefern danach die falschen Codepoints. Vier
     Gegenmaßnahmen geprüft, KEINE hat funktioniert: CSS
     `font-variant-ligatures: none`, CSS `font-feature-settings: "liga"
     0, ...` (beide von MuPDFs CSS-Engine ignoriert), explizite
     Font-Familien wie "Helvetica"/"Arial"/"Times" statt "sans-serif"
     (ligiert weiterhin - nur "monospace" nicht, für echten Fließtext
     unbrauchbar), sowie Zero-Width-Non-Joiner (U+200C) zwischen den
     betroffenen Buchstaben (verhindert die Ligatur zwar, aber die
     Base-14-Schrift im Story-Rendering hat dafür kein Nullbreite-Glyph
     und zeigt stattdessen eine sichtbare Lücke - visuell inakzeptabel).
     Ein sauberer Fix bräuchte entweder nachträgliche
     ToUnicode-CMap-Chirurgie an den Ligatur-Glyphen (invasiv,
     MuPDF-Versions-fragil, nicht versucht) oder einen kompletten
     Ersatz des HTML/Story-Einfügepfads durch manuelles
     Span-für-Span-`insert_textbox()` (eigene Projektentscheidung, siehe
     Punkt 4 oben zu Font-Erhalt - hängt strukturell zusammen). Neu:
     `tests/test_pdf_ligature_limitation.py` (2 Tests) - schreibt den
     AKTUELLEN (fehlerhaften) Zustand exekutierbar fest, damit ein
     künftiges MuPDF-Upgrade, das das behebt, hier auffällt statt
     stillschweigend unbemerkt zu bleiben.

  6. **Redaction über Hintergrundbildern/überlagerten Textblöcken
     (Hintergrundbild-Teil verifiziert als unbedenklich, überlagerte-
     Blöcke-Teil als realer Bug gefunden und behoben).** Löst die offene
     Vermutung aus Zeile 115 unten ab ("Später prüfen, ob redact_block
     das Hintergrundbild ungewollt betrifft").
       - Hintergrundbilder: `page.apply_redactions()`s Default
         `images=2` ("blank out overlapping image parts") wurde direkt
         geprüft - nur der tatsächlich redigierte Rechteck-Ausschnitt
         eines Bildes wird weiß, der Rest des Bildes UND das Bildobjekt
         selbst bleiben vollständig erhalten. Genau das gewünschte
         Verhalten, kein Bug.
       - Überlagerte Blöcke: real und direkt reproduziert. Der
         Kollisionsschutz (`_next_block_y0()`/
         `PyMuPdfEngine._collision_aware_max_y1()`, siehe die frühere
         "Kollisionsschutz"-Eintragsgruppe weiter oben) prüfte bei einem
         `block.highlighted`-Block bisher NUR gegen dessen eigene,
         schmale Text-bbox - obwohl `_grow_highlight_if_needed()`s
         tatsächliche Neuzeichnung der vergrößerten Highlight-Fläche
         (anders als deren eigentlicher Redact-Schritt, der schmal
         bleibt) die VOLLE Breite des zugehörigen Highlight-Rechtecks
         nutzt (siehe `redact_block()`s Docstring). Ein Block, der
         außerhalb der schmalen bbox, aber innerhalb der breiten
         Highlight-Spalte liegt, war für die Kollisionsprüfung
         unsichtbar - nichts deckelte das Höhenwachstum, bevor die
         vergrößerte Highlight-Fläche direkt über diesen Nachbarblock
         gemalt wurde. Konkret reproduziert: ein kurzes, highlightetes
         Zitat mit einer absichtlich sehr langen Übersetzung malte eine
         hellblaue Fläche über einen unbeteiligten Block seitlich davon
         (Pixel-Stichprobe an dessen Position matchte exakt
         `_HIGHLIGHT_FILL_COLOR`, obwohl der Text laut `get_text()`
         technisch noch "vorhanden" war - nur optisch begraben). Fix:
         `_next_block_y0()` bekommt einen optionalen `x_range`-Parameter;
         `_collision_aware_max_y1()` übergibt für highlightete Blöcke die
         breite `_associated_highlight_extent()`-Spanne statt der
         schmalen `block.bbox`. Nach dem Fix wird das Wachstum korrekt
         vor dem Nachbarblock gekappt (verifiziert: Pixel an dessen
         Position bleibt weiß, nicht mehr Highlight-Farbe) - der
         highlightete Block fällt stattdessen auf den bestehenden
         Schriftverkleinerungs-/Forced-Fallback-Pfad zurück, statt einen
         fremden Block zu überdecken. Neu:
         `tests/test_pdf_overlay_collision.py` (2 Tests: Kollisionsfall
         plus Hintergrundbild-Kontrolltest).

- [x] Erster voller Strukturlauf gegen die echte, vertrauliche
  "1526 VIRELICON.pdf" seit sie in dieser Umgebung verfügbar ist
  (17.08.2026) - bisher stand diese Datei in dieser Sitzung nie zur
  Verfügung (siehe mehrere ältere "nicht verfügbar"-Vermerke oben, u. a.
  beim Duplikat-Text-Bug), der Nutzer hat sie jetzt bereitgestellt.
  **Kein echter Übersetzungslauf** - in dieser Cloud-Sitzung sind keine
  Provider-API-Zugangsdaten hinterlegt (`keyring`-Backend meldet
  `fail`, keine Umgebungsvariablen gesetzt), daher mit einem
  Platzhalter-Provider statt DeepL/Google/OpenAI/Grok gelaufen -
  übersetzt absichtlich deutlich länger als das Original (Präfix
  `[DE-PLATZHALTER-N]` + zwei zusätzliche Füllsätze pro Block), um
  Wachstum/Schrumpfung mindestens so stark wie eine reale Übersetzung
  zu erzwingen. Dokument: 14 Seiten, 142 Blöcke (133 übersetzbar, 9
  übersprungen), 54 highlightete Blöcke, 11 echte Link-Annotationen auf
  7 Seiten.
    - Vollständiger `translate_pdf()`-Lauf über alle 14 Seiten: 133
      übersetzt, 9 übersprungen, 0 fehlgeschlagen, keine Exceptions.
      129/133 Blöcke mit Overflow (erwartet bei diesem absichtlich
      überlangen Platzhalter).
    - Link-Erhalt (der in dieser Session neu gebaute Fix, siehe oben):
      alle 11 Links auf allen 7 betroffenen Seiten nach dem vollen Lauf
      exakt erhalten (Vorher-/Nachher-Zählung pro Seite identisch) - die
      erste Verifikation dieses Fixes an einem echten Dokument statt nur
      synthetischen Fixtures.
    - Kollisionsschutz für überlagerte Blöcke (ebenfalls neu in dieser
      Session): 280 Wachstums-Anomalie-Log-Einträge (88
      `growth_capped_by_collision`, 115 `small_final_font`, 77
      `excessive_height_growth` - plausibel angesichts des absichtlich
      überlangen Platzhalters), keine sichtbar über einen Nachbarblock
      gemalte Highlight-Fläche in den geprüften Stichproben.
    - Visuelle Stichprobe (Seiten 0, 3, 6 als PNG gerendert und
      angesehen): Formatierung (fett/kursiv/unterstrichen/Bullet-Punkte),
      beide echten Hyperlinks (blau/unterstrichen, unverändert) und die
      highlighteten Zitat-Flächen sehen alle korrekt aus, keine
      sichtbaren Überlappungen oder verlorenen Inhalte. Eine kosmetische
      Beobachtung (kein neuer Bug): ein sehr schmaler Attributions-Block
      ("- Ivan", ca. 33pt eigene Spaltenbreite, direkt neben einem
      großen eingebetteten Chat-Screenshot) wickelt den stark
      überlangen Platzhaltertext sichtbar eng um sich selbst - Inhalt
      per `get_text()` auf vollständig geprüft (kein Abschneiden), rein
      optisch eng. Deckt sich mit der bereits dokumentierten,
      akzeptierten Einschränkung für kurze Ein-Zeiler/Attributionszeilen
      unter starkem künstlichem Overflow (siehe die "Kollisionsschutz"-
      Einträge weiter oben) - unter einer realen, typischerweise nur
      moderat längeren Übersetzung dürfte das deutlich schwächer
      ausfallen. Emoji im Originaltext (🔴, 💯) werden vom
      Sans-Serif-Fallback-Font durch ein generisches Ersatzsymbol
      dargestellt statt zu verschwinden - vorbestehendes Verhalten,
      nicht Teil dieser Session.
    - Verarbeitete Datei und Zwischenstände (Platzhalter-Ausgabe-PDF,
      gerenderte PNGs, Anomalie-Log) wurden NICHT dauerhaft abgelegt
      oder an den Nutzer verschickt (vertrauliches Dokument, siehe
      Projekt-Konvention) - nur lokal in dieser Sitzung geprüft und
      danach aufgeräumt.
    - Offen: der eigentliche Übersetzungsschritt mit einem echten
      Provider gegen dieses Dokument steht noch aus - dafür werden in
      dieser Cloud-Sitzung Provider-Zugangsdaten benötigt, die hier
      nicht hinterlegt sind (siehe RoadMap.md).

- [x] Echter Live-Lauf des PDF-UI-Pfads gegen "1526 VIRELICON.pdf" über
  einen echten Provider (Google, lokal beim Nutzer über die Desktop-App
  ausgeführt) durchgeführt und drei vom Nutzer per Screenshot gemeldete
  Bugs root-caused und behoben (17.08.2026). Löst den oben als offen
  markierten "echter Live-Lauf"-Punkt ab. Ablauf dieser Session: zunächst
  ein lokaler `ModuleNotFoundError: No module named 'fitz'` (PyMuPDF war
  in der aktiven pyenv-Umgebung trotz `requirements.txt`-Eintrag nicht
  installiert - kein Code-Bug, behoben mit `pip install -r
  requirements.txt`), danach eine Verwechslung bei der
  API-Key-Speicherung (Nutzer hatte "Umgebungsvariable (Sitzung)" statt
  "OS-Keyring"/"Beides" gewählt - `ui/settings.py::save_credential()`
  speichert für `target="environment"` bewusst nur in `os.environ`,
  sitzungsgebunden; kein Bug, vom Nutzer selbst bestätigt nach kurzer
  Rückfrage). Danach der eigentliche Live-Lauf, drei Bugs gemeldet:

  1. **Header wurde mitübersetzt.** Root Cause: `ui/pdf_job.py::
     run_pdf_job()` hat bis dahin NIE ein `DocumentTemplate` an
     `PyMuPdfEngine` übergeben - weder das seit längerem vorhandene,
     dokumentspezifische `templates/virelicon.json` (das kein UI-Pfad
     je geladen hat) noch irgendeine automatische Erkennung. Der
     Ausschlussmechanismus selbst (`header_bbox`/`footer_bbox` in
     `PyMuPdfEngine.extract_blocks()`) existierte und funktionierte
     bereits - er wurde vom direkten PDF-UI-Pfad schlicht nie benutzt.
     Rückfrage an den Nutzer (AskUserQuestion): vorhandene Vorlage
     einfach laden, oder generische Erkennung samt UI-Checkbox bauen?
     Antwort: **"Checkbox Ja/Nein im UI"** - generisch, nicht an dieses
     eine Dokument gebunden. Umgesetzt:
       - Neu `pipeline/pdf/template.py::detect_header_footer_zones()`:
         erkennt wiederkehrende Kopf-/Fußzeilen rein generisch über eine
         Kombination aus Text-Wiederholung (Ziffern werden vor dem
         Vergleich maskiert, damit z. B. "Page 3 of 14" über Seiten
         hinweg noch als identisch erkannt wird - `_normalize_for_
         repetition()`) UND Positions-Wiederholung across Seiten, mit
         konfigurierbarem `zone_fraction` (wie weit oben/unten auf der
         Seite gesucht wird) und `min_page_fraction` (wie viel Anteil der
         Seiten die Wiederholung zeigen muss). Kein dokumentspezifischer
         Code, keine Abhängigkeit von `templates/virelicon.json`. Neue
         Tests: `tests/test_pdf_header_footer_detection.py` (6 Tests:
         Erkennung inkl. Seitenzahl-Handling, Fließtext wird nicht
         fälschlich erkannt, keine Wiederholung → `None`, Wiederholung
         unter der Schwelle → `None`, End-to-End-Ausschluss über
         `PyMuPdfEngine(template=...)`, Randfall leeres Dokument).
       - Durchgereicht als zwei unabhängige, PDF-only-Checkboxen
         ("Header ausschließen"/"Footer ausschließen") durch den
         kompletten Stack, jeweils spiegelnd wie `ico_mode` bereits für
         Word verdrahtet ist:
         `ui/pdf_job.py::run_pdf_job()` bekommt `exclude_header`/
         `exclude_footer` (Default `False`) - bei Bedarf wird VOR dem
         eigentlichen Lauf ein zweites, wegwerfbares `PyMuPdfEngine()`
         ohne Template geöffnet, nur um `detect_header_footer_zones()`
         aufzurufen (`extract_blocks()` ist rein lesend, stört den
         echten Lauf nicht), das Ergebnis fließt in ein neu gebautes
         `DocumentTemplate`, mit dem dann die ECHTE Engine konstruiert
         wird (Template kann nicht nachträglich auf eine schon
         benutzte Engine-Instanz gesetzt werden, da `extract_blocks()`
         pro Seite cached). Der QA-Bericht nennt jetzt explizit, ob
         Header/Footer-Ausschluss aktiv war UND ob dabei wirklich etwas
         erkannt wurde (kein stilles "nichts passiert").
         `ui/workers.py::PdfTranslationWorker` reicht beide Flags durch.
         `ui/models.py::TranslationRequest` bekommt `exclude_header`/
         `exclude_footer` (Default `False`, dokumentiert analog zu
         `ico_mode`). `ui/app.py`: zwei neue `QCheckBox` (`self.
         exclude_header`, `self.exclude_footer`), PDF-only sichtbar
         (`_mode_changed()`, spiegelt `ico_mode`s Word-only-Logik exakt
         inkl. Zurücksetzen beim Moduswechsel), in `_request()`/
         `_start()` verdrahtet. `ui/i18n.py`: neue DE/EN-Texte
         (`field.exclude_header`/`exclude_header.checkbox`/`exclude_
         header.tooltip` und Footer-Pendants).
       - Neue UI-Regressionstests in `tests/test_ui_word_mode.py` (3
         Tests, spiegeln die vorhandenen `ico_mode`-Tests exakt):
         Sichtbarkeit nur im PDF-Modus inkl. Reset beim Moduswechsel,
         `_request()` trägt beide Flags korrekt, `PdfTranslationWorker`
         erhält beide Flags aus dem Request.

  2. **Markierter (blau hinterlegter) Block am Seitenende (Seite 1):
     übersetzter Text schwebte über einer leeren Markierungs-Box statt
     darin.** Anhand der echten Ausgabedatei (vom Nutzer bereitgestellter
     Pfad `tests/output/1526 VIRELICON_DE.pdf`, zusammen mit der echten
     Quelldatei `1526 VIRELICON.pdf`) rendergenau nachvollzogen (Vorher/
     Nachher-PNG-Ausschnitte des Seitenendes verglichen). Root Cause in
     `PyMuPdfEngine._next_block_y0()`: die Funktion sucht den "nächsten
     Block darunter" durch Vergleich `other.bbox[1] > by0` (Oberkante des
     Kandidaten größer als die EIGENE Oberkante des wachsenden Blocks).
     In diesem Dokument enden zwei UNTERSCHIEDLICHE, separat extrahierte
     PDF-Blöcke ("So Creator yearned for purity..." und, direkt
     anschließend auf DERSELBEN Zeile, separat formatiert, "2 ways:") auf
     derselben visuellen Zeile - der kurze Block "2 ways:" hat also eine
     eigene Oberkante (`bbox[1]`), die INNERHALB der Y-Spanne des langen
     Blocks liegt, nicht darunter. Der alte Vergleich hielt "2 ways:"
     trotzdem für "den nächsten Block darunter" und kappte `max_y1` des
     langen Blocks auf einen Wert UNTER dessen eigener ursprünglicher
     Unterkante (`bbox[3]`) - der Block durfte sich also nicht nur nicht
     vergrößern, sein nutzbarer Bereich wurde sogar kleiner als im
     Original. Die übersetzte (deutlich längere) Textmenge passte dort
     nicht hinein; da die tatsächlich benötigte Höhe wegen der Kappung
     nie über die ursprüngliche Highlight-Fläche hinausging, hat
     `_grow_highlight_if_needed()` (die die Markierungsfarbe bei Bedarf
     nachzeichnet) korrekterweise NICHTS getan - mit dem Ergebnis, dass
     die per `redact_block()` weiß übermalte Original-Markierungsfläche
     leer blieb, während der Text (durch den regulären Fit-Fallback,
     nicht durch die Highlight-Logik) irgendwo in der Nähe, aber ohne
     zugehörigen farbigen Hintergrund landete. Fix: Vergleich in
     `_next_block_y0()` auf `other.bbox[1] >= by1` (eigene UNTERKANTE)
     umgestellt - ein Block auf derselben Zeile zählt jetzt korrekt nicht
     mehr als "darunter". Geprüft, dass die bestehenden, gezielt für den
     ÄHNLICHEN, aber verschiedenen Kollisionsfall aus einer früheren
     Session gebauten Tests (`tests/test_pdf_overlay_collision.py`,
     `tests/test_pdf_redact_insert_collision.py` - dort liegen die
     Blöcke echt untereinander, nicht auf derselben Zeile) weiterhin
     bestehen. Neue, gezielte Regressionsabdeckung in
     `tests/test_pdf_same_row_sibling_collision.py` (synthetisches PDF,
     Aufbau spiegelt `tests/test_pdf_overlay_collision.py`; 2 Tests -
     einer prüft `_collision_aware_max_y1()` direkt, einer den
     kompletten Redact/Insert/Save-Pfad per Pixel-Stichprobe an der
     gewachsenen Fläche) - beide Tests per Revert-Probe bestätigt
     fehlschlagend gegen den alten Vergleich.

  3. **Erster Absatz auf Seite 2 gar nicht bzw. nur teilweise
     übersetzt.** Ebenfalls anhand der echten Ausgabedatei rendergenau
     nachvollzogen. Root Cause in `PyMuPdfEngine.extract_blocks()`:
     `translatable` wurde bislang mit `not any(block_overlaps(bbox,
     link_bbox) for link_bbox in link_bboxes)` auf der GESAMTEN
     Block-Bbox berechnet - sobald IRGENDEINE Zeile eines Blocks eine
     Link-Annotation überlappte, wurde der komplette (potenziell
     mehrzeilige) Block non-translatable. In diesem Dokument sitzt mitten
     in einem 6-zeiligen Absatz auf Seite 2 eine einzelne, per Link
     zitierte Telegram-Post-Zeile ("Divide ➔ ...") - das hat bisher den
     kompletten umgebenden Absatz von der Übersetzung ausgeschlossen,
     nicht nur diese eine Zeile. Per Konstruktion bereits korrekt und
     bewusst so gewollt (siehe `tests/fixtures/representative.pdf`s
     Kommentar weiter oben in dieser Datei): ein Block, der WIRKLICH nur
     aus Link-Text besteht, soll komplett ausgeschlossen bleiben - das
     Problem war die fehlende Granularität für einen Block, der NUR
     TEILWEISE eine Link-Zeile enthält. Fix, spiegelt die bestehende
     `_split_by_highlight()`/`_line_is_highlighted()`-Architektur exakt:
     neue `_split_by_link()`/`_line_overlaps_link()` in
     `pipeline/pdf/pymupdf_engine.py` zerlegen einen (bereits nach
     Highlight-Status aufgeteilten) Zeilenlauf zusätzlich in Link-/
     Nicht-Link-Läufe, bevor `translatable` bestimmt wird - nur die
     tatsächlich linküberlappende(n) Zeile(n) werden als eigener,
     separater `translatable=False`-Block ausgegeben, der Rest des
     ursprünglichen Absatzes bleibt ein normaler, übersetzbarer Block.
     `_line_overlaps_link()` prüft (anders als `_line_is_highlighted()`,
     die nur vertikal prüft, weil eine Highlight-Fläche immer die volle
     Zeilenbreite abdeckt) echte 2D-Überlappung, MIT Toleranz
     (`_LINK_OVERLAP_TOLERANCE`, Pendant zu `_HIGHLIGHT_LINE_TOLERANCE`):
     im echten Dokument saß eine völlig unbeteiligte Zeile ("this
     confirms doubt was always...") nur 0,02pt unterhalb eines fremden,
     benachbarten Link-Rechtecks - ohne Toleranz hätte allein dieser
     Rundungsfehler (bei einem exakten, toleranzfreien Rechteck-
     Überlappungstest) die Zeile mit ausgeschlossen; mit Toleranz bleibt
     sie korrekt übersetzbar. Verifiziert, dass der ursprüngliche
     Anwendungsfall (Block besteht komplett aus Link-Text, z. B.
     `tests/fixtures/representative.pdf`) unverändert vollständig
     non-translatable bleibt - der Split ändert daran nichts, weil dort
     jede Zeile überlappt. Docstring von `extract_blocks()` entsprechend
     aktualisiert (beschreibt jetzt den Highlight-Split UND den
     nachgelagerten Link-Split). Neue Regressionsabdeckung in
     `tests/test_pdf_link_line_split.py` (3 Tests: Link auf nur einer
     Zeile schließt nur diese Zeile aus statt des ganzen Absatzes;
     0,05pt-Rundungs-Sliver an einer Zeilengrenze schließt die
     Nachbarzeile NICHT versehentlich mit aus; ein Block, der komplett
     aus Link-Text besteht, bleibt weiterhin komplett ausgeschlossen).

  Alle drei Fixes zusätzlich End-to-End gegen die echte, vertrauliche
  "1526 VIRELICON.pdf" mit einem Fake-Provider verifiziert (absichtlich
  lange Platzhalterübersetzungen, um Wachstum zu erzwingen) und die
  betroffenen Seiten als PNG vor/nach gerendert und visuell verglichen -
  in allen drei Fällen sieht das Ergebnis jetzt sichtbar korrekt aus
  (Markierungsfläche wächst korrekt mit dem Text mit; der vormals
  übersprungene Absatz auf Seite 2 wird jetzt bis auf die eine
  Link-Zeile vollständig übersetzt). Gerenderte PNGs und die
  Platzhalter-Ausgabedatei wurden NICHT dauerhaft abgelegt oder verschickt
  (vertrauliches Dokument, siehe Projekt-Konvention) - nur lokal in
  dieser Sitzung geprüft und danach aufgeräumt. Gesamter Testlauf am
  Ende: 107 passed, 1 skipped (vorher 99 passed, 1 skipped - 5 neue Tests
  in `tests/test_pdf_same_row_sibling_collision.py` (2) und
  `tests/test_pdf_link_line_split.py` (3), plus 3 neue Tests in
  `tests/test_ui_word_mode.py`).

- **Zwei weitere reale Formatierungsbugs, Seite 2 derselben
  "1526 VIRELICON.pdf" (18.08.2026):** Vom Nutzer beim Vergleich von
  Original und übersetzter Ausgabedatei entdeckt ("Was ist den mit den
  Format Unterschieden auf der Seite 2 in der unteren Hälfte...").

  4. **Mehrere kurze, einzeilige Blöcke landeten in sichtbar kleinerer
     Schrift als ihre Nachbarn** - bis hinunter zu `_MIN_FONT_SIZE`
     (6pt) gegenüber dem üblichen ~11pt-Fließtext. Erste Erklärung
     (Original-Boxen seien an dieser Stelle ungewöhnlich knapp bemessen)
     war falsch und wurde vom Nutzer zurecht zurückgewiesen: "Knapp
     schaut es für mich nicht aus. Der Text im Original ist an der
     besagten Stelle genau in der nächsten Zeile." Erneute Prüfung
     bestätigte das - die betroffenen Original-Boxen sind ganz normale,
     einzeilige Blöcke ohne jede Besonderheit. Tatsächliche Root Cause
     in `PyMuPdfEngine._insert_html_text()`s CSS: `spans_to_html()`
     verpackt JEDEN Absatz in `<p>...</p>`, auch einen einzeiligen Block
     ganz ohne echten Absatzumbruch, und PyMuPDFs Story-/CSS-Engine
     reserviert für ein `<p>`-Element automatisch zusätzlichen Rand-/
     Zeilenhöhenraum, den `try_grow()`s Wachstumslogik
     (`_estimate_line_height()`-basierte Höhenschritte, dann Breite)
     nicht kennt und folglich nicht ausgleicht. Direkt reproduziert
     (`tests/test_pdf_paragraph_css_reset.py::
     test_longer_translation_of_a_short_line_does_not_shrink_the_font`):
     ein einzeiliger Block nahe der Seitenecke unten rechts (bewusst so
     platziert, dass nur wenig Wachstumsspielraum in beiden Achsen
     bleibt - ~10pt Höhe bis `_max_rect_y1()`s Fuß-/Seitenrandgrenze,
     ~44pt Breite bis `max_x1`, spiegelt damit die reale, kollisions-
     bzw. randnahe Lage der betroffenen echten Blöcke) - eine nur
     geringfügig längere deutsche Übersetzung passte ohne den Fix
     NICHT bei der Originalschriftgröße (schrumpfte auf 10pt), obwohl
     rechnerisch nach Wachstum genug Platz vorhanden gewesen wäre; mit
     dem Fix passt exakt derselbe Fall unverändert bei voller
     Originalgröße (11pt). Ohne diese gezielt eng bemessene Platzierung
     bleibt selbst ein unreparierter Aufruf unauffällig, weil
     `try_grow()` auf einer großzügigen Seite fast immer genug
     Spielraum findet, um trotz des unnötig reservierten `<p>`-Raums
     noch zu passen - das reservierte Extra-Padding kostet dann nur
     ungenutzten Spielraum, nicht Schriftgröße; erst wenn dieser
     Spielraum selbst schon knapp ist (wie in der realen Datei, an
     einer Blockgrenze/Seitenunterkante), macht der Unterschied den
     entscheidenden Ausschlag zwischen Passen und Schrumpfen. Fix: neue
     `_insert_html_css()`-Hilfsfunktion mit `p {margin:0;
     line-height:1;}` (räumt den reservierten Platz komplett ab) plus
     `p + p {margin-top: {fontsize * 0.8}pt;}` (`_PARAGRAPH_GAP_RATIO`;
     nur zwischen zwei tatsächlich aufeinanderfolgenden `<p>`-
     Geschwistern innerhalb eines Blocks, stellt gezielt einen echten
     Mehrfach-Absatzabstand wieder her, ohne den einzeiligen Fall zu
     beeinträchtigen). Ein erster Versuch mit blankem `margin:0` ohne
     Geschwister-Regel brach den bestehenden Absatzabstand-Roundtrip-
     Test in `tests/test_pdf_formatting_roundtrip.py` (Abstand zwischen
     zwei echten Absätzen wurde unkenntlich) - mit der Geschwister-Regel
     besteht dieser Test weiterhin unverändert. Beide Callsites in
     `_insert_html_text()` (Fit-Prüfung und finaler erzwungener Insert)
     auf `_insert_html_css()` umgestellt. Regressionsabdeckung in
     `tests/test_pdf_paragraph_css_reset.py` (2 Tests: keine Schrumpfung
     bei knapp bemessenem Wachstumsspielraum; echter Mehrfach-
     Absatzabstand innerhalb eines Blocks bleibt klar sichtbar, > 3pt
     Lücke) - beide Tests per Revert-Probe bestätigt fehlschlagend, wenn
     `_insert_html_css()` durch den alten reinen `body {...}`-CSS-String
     ohne `p`-Reset ersetzt wird.

  5. **Markierte (blau hinterlegte) Blöcke verloren nach der Übersetzung
     ihren farbigen Hintergrund** - betraf ALLE markierten Blöcke außer
     dem einen, der gar nicht übersetzt wurde (Symptom 3 oben, vor dem
     Link-Split-Fix). Vom Nutzer präzise beschrieben: "Der Block mit
     'Does this prisma have a shape?...' in der Übersetzung [ist] auch
     nicht blau hinterlegt... Es scheint das das Blau irgendwo im
     Hintergrund ist, da man am unteren Rand der Boxen einen dünnen
     blauen Strich sieht, als wenn eine weisse Box mit Text drüber
     liegt." Root Cause in `PyMuPdfEngine.redact_block()`: die bisherige
     (in einer früheren Session eingeführte, aber nie direkt geprüfte)
     Annahme war, dass die als Seiteninhalt HINTER dem Blocktext
     gezeichnete Original-Markierungsfläche `redact_block()`s
     Weiß-Redaction unbeschadet übersteht und nur bei tatsächlichem
     Höhenwachstum (`_grow_highlight_if_needed()`) neu gezeichnet werden
     muss. Direkt widerlegt: `page.add_redact_annot(rect, fill=(1,1,1))`
     übermalt sein GESAMTES Rechteck weiß, unabhängig vom
     darunterliegenden Vektorinhalt und unabhängig von
     `apply_redactions()`s `graphics`-Parameter (der nur steuert, ob
     Vektorgrafik INNERHALB des Rechtecks vor dem Redigieren entfernt
     wird, nicht ob die Weißfüllung selbst etwas ausspart) - jeder
     redigierte markierte Block verlor also seinen Hintergrund, nicht
     nur wachsende; `_grow_highlight_if_needed()` lief aber ausschließ-
     lich im Wachstumsfall und stellte die Farbe entsprechend auch nur
     dann wieder her, was den viel häufigeren "passt ohne Wachstum"-Fall
     komplett ohne Hintergrund-Redraw ließ. Die vom Nutzer beschriebene
     dünne blaue Randlinie erklärt sich dadurch, dass eine gezeichnete
     Markierungsfläche in ihren eigenen Rechteckgrenzen unabhängig von
     der (nur aus Textglyphen abgeleiteten) `block.bbox` ist - reicht sie
     etwas über die (nur breitenweit verbreiterte) Redaction-Fläche
     hinaus, übersteht genau dieser Überstand unverändert, während der
     Rest weiß wird. Fix: `redact_block()` zeichnet die Markierungsfarbe
     jetzt unmittelbar nach der Weiß-Redaction unbedingt neu, über die
     volle `_associated_highlight_extent()` (beide Achsen - bisher wurde
     `_associated_highlight_extent()` in `redact_block()` nur für die
     Breiten-Verbreiterung der Redaction-Fläche selbst verwendet, nicht
     für einen Neuanstrich) - jeder markierte Block startet damit ab
     sofort, noch vor jeder Texteinfügung, von einer korrekt eingefärb-
     ten Ausgangslage; `_grow_highlight_if_needed()`s Docstring
     entsprechend korrigiert (beschreibt nicht mehr fälschlich, dass die
     Originalfläche "einfach übersteht"). Testaufbau mit Bedacht: die
     erste Testversion (Text "Quote line here.") bestand auch bei
     manuell zurückgesetztem Fix, weil dieser Text zufällig zusätzlich
     `insert_text()`s eigenen, unabhängigen Wachstumspfad auslöste (durch
     einen Font-Metrik-Unterschied zwischen der `insert_textbox()`-
     basierten Test-Fixture und dem produktiven `insert_htmlbox()`-Pfad),
     der seinerseits die Farbe über `_grow_highlight_if_needed()`
     wiederherstellte und damit den eigentlich zu prüfenden Codepfad
     verdeckte - behoben durch bewusst kürzeren Text (`<p>Q.</p>`), der
     garantiert ohne jedes Wachstum passt (`fit=True` geprüft) und damit
     den No-Growth-Fall sauber isoliert. Regressionsabdeckung in
     `tests/test_pdf_highlight_background_persists.py` (2 Tests: markier-
     ter Block ohne nötiges Wachstum behält seinen Hintergrund
     vollständig - inklusive einer Fixture, bei der die gezeichnete
     Markierungsfläche bewusst etwas über die Text-Bbox hinausragt, um
     genau das vom Nutzer beschriebene Randlinien-Symptom zu erfassen;
     unmarkierte Blöcke bleiben unverändert weiß) - per Revert-Probe
     bestätigt fehlschlagend gegen die alte `redact_block()`-Fassung
     ohne den Neuanstrich.

  Beide Fixes zusätzlich gemeinsam gegen die echte, vertrauliche
  "1526 VIRELICON.pdf" verifiziert: ein kombiniertes Test-Rendering aus
  echtem Quelldokument plus echtem extrahiertem deutschem
  Übersetzungstext für mehrere betroffene Blöcke ("Shape in form", "IS a
  thingy", "Which makes perfect", "Does this prism have a shape") zeigt
  durchgängig volle Originalschriftgröße (11.04pt) und vollständigen,
  lückenlosen blauen Hintergrund. Gerenderte Vergleichsbilder und die
  daraus abgeleiteten Zwischendateien wurden NICHT dauerhaft abgelegt
  oder verschickt (vertrauliches Dokument, siehe Projekt-Konvention) -
  nur lokal in dieser Sitzung geprüft und danach aufgeräumt. Gesamter
  Testlauf am Ende: 111 passed, 1 skipped (vorher 107 passed, 1 skipped
  - 4 neue Tests in 2 neuen Dateien:
  `tests/test_pdf_paragraph_css_reset.py` (2),
  `tests/test_pdf_highlight_background_persists.py` (2)).

- **Symbol-/Private-Use-Font-Glyphen behoben (18.08.2026):** Löst den seit
  Zeile 110 unten offenen Befund. Direkt reproduziert (ohne die echte
  Datei, da hierfür kein extrahierter Wingdings-Font nötig ist - ein
  manuell auf einen PUA-Codepoint gesetzter `TextSpan` genügt, um exakt
  den produktiven `redact_block()`/`insert_text()`-Pfad zu treffen):
  ein Symbol-Font-Zeichen (z. B. ein Wingdings-Bullet, Codepoint U+F086,
  wie in der echten Datei auf Seite 5 gefunden) geht beim Wiedereinfügen
  über `page.insert_htmlbox()` mit CSS `font-family: sans-serif`
  vollständig verloren - nicht als sichtbare Tofu-Box, sondern komplett
  unsichtbar: der extrahierte Output-Text enthielt an der Stelle einen
  rohen NUL-Codepoint (`\x00`), und das gerenderte Bild zeigte an der
  Position schlicht eine Lücke, kein Ersatzzeichen. Ursache: der
  Sans-Serif-Fallback-Font (in dieser Umgebung "NimbusSans-Regular")
  kennt naturgemäß kein Glyph für einen Font-spezifischen
  Private-Use-Area-Codepoint - dieser hat außerhalb des exakten
  Symbol-Fonts, der ihn definiert, keine Bedeutung. Fix in neuer
  `_replace_unsupported_glyphs()`/`_is_private_use_char()`
  (`pipeline/pdf/pymupdf_engine.py`): jedes Zeichen in den drei
  Private-Use-Area-Bereichen (BMP U+E000-U+F8FF sowie die beiden
  Supplementary-Bereiche) wird im finalen HTML-Inhalt - egal ob aus
  `translated_html` (Provider-Antwort) oder aus dem unübersetzten
  `spans_to_html()`-Fallback - durch ein sichtbares Platzhalterzeichen
  ("□", WHITE SQUARE) ersetzt, das im Fallback-Font nachweislich
  existiert (per Direkttest bestätigt: passendes Glyph vorhanden, kein
  erneuter Tofu-Verlust). Bewusst KEIN Rateversuch auf ein spezifisches
  Unicode-Äquivalent (z. B. "•" für "es ist wahrscheinlich ein Bullet") -
  ohne den Original-Font einzubetten (siehe unten, weiterhin offene
  Architekturfrage) lässt sich nicht zuverlässig bestimmen, welches
  Symbol ein PUA-Codepoint tatsächlich darstellt, und ein falsch
  geratenes Symbol wäre irreführender als ein ehrlicher, klar erkennbarer
  Platzhalter. Jede Ersetzung wird zusätzlich per `log_growth_anomaly()`
  protokolliert (neues Event `unsupported_symbol_glyph`,
  `tests/output/growth_anomalies.jsonl`) - entspricht dem in der Roadmap
  festgehaltenen Prinzip "Nicht unterstützte Inhalte werden sichtbar
  katalogisiert". Beide Aufrufstellen in `_insert_html_text()` (Fit-
  Prüfung und finaler erzwungener Insert) betroffen, da beide auf
  demselben `content_html` operieren - ein einziger Ersetzungspunkt genau
  dort deckt automatisch auch den Plain-Text-Backward-Compatibility-Pfad
  ab, da `_plain_text_needs_unicode_fallback()` (Zeile 128 unten) jedes
  Zeichen mit `ord(ch) > 255` - PUA-Codepoints eingeschlossen - ohnehin
  schon über den HTML/Story-Pfad umleitet, bevor es dort ankommen könnte.
  Regressionsabdeckung in `tests/test_pdf_symbol_glyph_placeholder.py`
  (5 Tests: Codepoint-Bereichserkennung für alle drei PUA-Zonen,
  Ersetzung inklusive Zählung, unveränderter gewöhnlicher Text, voller
  Redact/Insert/Save-Rundlauf ohne NUL-Symptom UND mit protokolliertem
  Anomalie-Eintrag, Kontrollfall ohne Symbol-Inhalt bleibt unprotokolliert
  und unverändert) - der entscheidende Rundlauf-Test per Revert-Probe
  bestätigt fehlschlagend (`\x00` weiterhin im Output), wenn die
  Ersetzung aus `_insert_html_text()` entfernt wird. Gesamter Testlauf am
  Ende: 116 passed, 1 skipped (vorher 111 passed, 1 skipped - 5 neue
  Tests).

- **Originalfont-Einbettung/-Wiederverwendung: kleine Verbesserung
  umgesetzt (18.08.2026).** Löst den seit Zeile 128 oben offenen Befund
  teilweise. Nutzer-Entscheidung (nach Abwägung der Alternativen -
  vollständige Font-Einbettung wurde bewusst ALS ZU GROSS für einen
  einzelnen Fix verworfen, siehe unten): statt echte Font-Einbettung
  umzusetzen (Original-Font-Programm aus dem Quell-PDF extrahieren,
  subsetten und einbetten - deutlich größeres Vorhaben mit Bold/Italic-
  Varianten-Matching und Lizenzfragen, bleibt bewusst zurückgestellt und
  weiterhin offene Architekturentscheidung), wird `block.font_name`
  jetzt wenigstens grob auf eine CSS-Generic-Family abgebildet statt
  immer unbedingt "sans-serif" zu verwenden. Neu in
  `pipeline/pdf/pymupdf_engine.py`: `_resolve_css_font_family()` prüft
  `block.font_name` (case-insensitiv) gegen zwei feste Keyword-Listen
  (`_SERIF_FONT_NAME_KEYWORDS`: Times, Georgia, Garamond, Cambria,
  Palatino, Minion, Caslon, Baskerville, Constantia, Cochin, Didot,
  Plantin, Bookman, Book Antiqua, Century, Goudy, Sabon, "serif";
  `_MONOSPACE_FONT_NAME_KEYWORDS`: Courier, Consolas, Menlo, Monaco,
  "mono", Typewriter, Lucida Console, Andale Mono) und liefert "serif",
  "monospace" oder unverändert "sans-serif" (`_DEFAULT_CSS_FONT_FAMILY`)
  für jeden nicht erkannten Namen - inklusive Symbol-/Icon-Fonts wie
  "Wingdings", die ohnehin keine Prosa-Schriftart sind. `_insert_html_css()`
  nimmt jetzt einen `font_family`-Parameter (Default weiterhin
  "sans-serif", damit bestehende Aufrufer ohne Angabe unverändert
  funktionieren) statt den String hart zu kodieren; beide Aufrufstellen
  in `_insert_html_text()` (Fit-Prüfung und finaler erzwungener Insert)
  lösen `font_family` einmal zu Beginn über `_resolve_css_font_family(
  block.font_name)` auf. Direkt reproduziert, dass die CSS-Generic-Family
  tatsächlich einen ANDEREN, vom PyMuPDF Story-Renderer tatsächlich
  gezeichneten Font ergibt, nicht nur eine angeforderte, aber ignorierte
  Einstellung: in dieser Umgebung löst "serif" zu "CharisSIL" auf,
  "monospace" zu "NimbusMonoPS-Regular", "sans-serif"/Default zu
  "NimbusSans-Regular" - drei tatsächlich unterschiedliche Fonts.
  Ausdrücklich KEINE echte Font-Wiedergabe - nur eine grobe, aber
  deutlich näher am Original liegende Familienwahl. Regressionsabdeckung
  in `tests/test_pdf_font_family_heuristic.py` (4 Tests:
  Serif-Namenserkennung, Monospace-Namenserkennung, Sans-Serif-/
  Default-Fallback inklusive Symbol-Font-Namen, voller Redact/Insert/
  Save-Rundlauf, der bestätigt, dass ein als Serif markierter Block
  tatsächlich einen ANDEREN gerenderten Font bekommt als ein
  Default-Block auf derselben Pipeline - bewusst ohne den konkreten
  Fontnamen hart zu kodieren, da das ein PyMuPDF-internes
  Implementierungsdetail ist) - der entscheidende Rundlauf-Test per
  Revert-Probe bestätigt fehlschlagend (beide Blöcke landen wieder beim
  selben Font), wenn die `font_family`-Weitergabe aus
  `_insert_html_text()` entfernt wird. Gesamter Testlauf am Ende: 120
  passed, 1 skipped (vorher 116 passed, 1 skipped - 4 neue Tests).

- **"PDF-Übersetzung korrigieren" - manuelle Nachbearbeitung im UI
  (18.08.2026):** Auslöser: der Nutzer fand im Live-Lauf gegen "1526
  VIRELICON.pdf" eine echte Fehlübersetzung - "Manuel" (Sprecher einer
  Zitat-Zuschreibungszeile) kam als "Handbuch" zurück. Diskussion mit dem
  Nutzer klärte zwei verworfene Alternativen, bevor die tatsächliche
  Lösung feststand:
  1. PDF grundsätzlich über ein Word-Zwischenformat übersetzen, damit der
     Nutzer von Hand korrigieren und selbst als PDF exportieren kann.
     Verworfen: ein PDF kennt nur Positionen/Glyphen, keine
     Dokumentstruktur - eine PDF-zu-Word-Rekonstruktion (Layout, Spalten,
     Markierungsboxen, Links, Kopf-/Fußzeilen) ist ein deutlich
     schwierigeres, verlustträchtigeres Problem als das direkte
     In-Place-Bearbeiten, das diese Engine bereits beherrscht - hätte
     vermutlich neue Bugs eingeführt statt welche zu vermeiden. Für
     Dokumente, die BEREITS als Word-Datei vorliegen (wie sich
     herausstellte: bei "1526 VIRELICON.pdf" der Fall), existiert der
     gewünschte Weg schon - die bestehende DOCX-Pipeline. Für PDFs ohne
     Word-Original (der eigentliche Anwendungsfall dieses Tools) bleibt
     der direkte PDF-Pfad nötig.
  2. Geschützte Begriffe (`pipeline/translation/protected_terms.py`, seit
     Projektbeginn vorhanden, `protect_terms()`/`restore_terms()`, per
     Wortgrenzen-Regex case-insensitiv, bereits vollständig durch alle
     drei Formate verdrahtet: PDF `translate_pdf.py`, Word, PPTX) hätte
     "Manuel" pauschal von der Übersetzung ausschließen können. Nutzer
     wies zurecht darauf hin, dass das ein globaler Holzhammer ist -
     falsch für ein Wort, das mal Name, mal echtes Übersetzungswort sein
     kann. Bleibt trotzdem die richtige Lösung für Begriffe, die IMMER
     Namen sind (z. B. wiederkehrende Sprecher in dieser Datei).

  Tatsächliche Lösung: eine gezielte Korrektur-Tabelle im UI, die
  ausdrücklich KEIN neuer PDF-Editor ist, sondern dieselbe
  redact_block()/insert_text()-Maschinerie wiederverwendet, die
  translate_pdf() ohnehin schon für die Erstübersetzung nutzt. Zwei
  Nutzer-Entscheidungen vorab per Rückfrage geklärt: (a) "Anwenden"
  überschreibt die bestehende Übersetzungsdatei, statt immer eine neue
  anzulegen - Charakter "Entwurf verfeinern", nicht "neue Quelle
  schützen"; (b) die Tabelle öffnet sich über einen expliziten Knopf,
  nicht automatisch nach jedem Lauf.

  Architektur, Datei für Datei:
  - `pipeline/pdf/pymupdf_engine.py`: neue `html_to_plain_text()` -
    Inverse von `spans_to_html()`/einer Provider-HTML-Antwort: `</p><p>`
    zwischen echten Geschwister-Absätzen wird zu einer Leerzeile,
    `<br/>` zu einem einfachen Zeilenumbruch, jedes verbleibende
    `<p>`/`<u>`/`<b>`/`<i>` wird entfernt (verliert die Formatierung
    selbst, nicht nur ihre optische Markierung - bewusst, siehe unten),
    HTML-Entities werden zuletzt entschärft. Direkt gegen mehrere Fälle
    verifiziert (verschachtelte Tags, Absatzumbrüche, `&amp;`-Entities).
  - `pipeline/pdf/translate_pdf.py`:
    - Neue `TranslatedBlockRecord`-Dataclass (page_index, block_index,
      original_text, translated_html) mit `display_text`-Property
      (ruft `html_to_plain_text()` auf).
    - `PdfTranslationStats` bekommt ein neues Feld `blocks: list[
      TranslatedBlockRecord] = field(default_factory=list)` - rein
      additiv (per Revert-Probe bestätigt: kein bestehender Test bricht,
      weil keiner Positions- oder Exakt-Gleichheits-Vergleiche auf dem
      gesamten Dataclass macht). `translate_pdf()`s Hauptschleife hängt
      nach jedem erfolgreich übersetzten Block (nur der `block.spans`-
      Zweig, siehe unten) einen Record an.
    - Neue `apply_pdf_corrections(engine, records) -> PdfTranslationStats`:
      spielt eine Record-Liste OHNE jeden Provider-/Netzwerkaufruf gegen
      `engine` ein - `engine` MUSS frisch auf der unangetasteten
      Quelldatei geöffnet sein, nie auf der bereits übersetzten (Docstring
      erklärt ausführlich warum: ein zweiter `redact_block()`-Aufruf auf
      der ursprünglichen `block.bbox` würde einen Bereich, den der ERSTE
      Durchlauf über die Originalgröße hinaus gewachsen hat, nicht mehr
      vollständig abdecken - Reste der ersten Übersetzung blieben stehen).
      Records werden nach Seite gruppiert, `extract_blocks()` (cached pro
      Seite) wird dadurch nur einmal pro Seite statt einmal pro Record
      aufgerufen.
    - Neue `build_corrected_records(records, edited_texts) -> list[
      TranslatedBlockRecord]`: eine Zeile gilt als unbearbeitet - und
      wird UNVERÄNDERT (identisches Objekt) durchgereicht -, wenn ihr
      aktueller Text noch exakt `record.display_text` entspricht; nur
      eine tatsächlich geänderte Zeile bekommt neues HTML über die
      bereits bestehende `_plain_text_to_html()`. Bewusster Kompromiss:
      eine bearbeitete Zeile verliert dadurch ihre Inline-Formatierung
      (fett/kursiv/unterstrichen) - Korrektheit des Wortlauts wiegt
      schwerer als Formatierungserhalt für eine Zeile, die der Nutzer
      ohnehin von Hand fixen musste; eine UNBEARBEITETE Zeile behält ihr
      Original-HTML und damit ihre Formatierung exakt.
  - `ui/pdf_job.py`: neue `run_pdf_correction_job(source, destination,
    records, exclude_header=False, exclude_footer=False)` - spiegelt
    `run_pdf_job()`s Template-Rekonstruktion (`detect_header_footer_
    zones()`) exakt, damit `extract_blocks()` bei der Korrektur
    dieselbe Block-Liste/-Reihenfolge liefert wie beim Erstlauf (sonst
    würden die `page_index`/`block_index`-Indizes ins Leere zeigen).
    Anders als `run_pdf_job()` fehlt bewusst die
    Existiert-bereits-Sperre für `destination` (Nutzer-Entscheidung
    "überschreiben", siehe oben) - nur der Quelle-gleich-Ziel-Schutz
    bleibt. Eigener, kompakter QA-Bericht (`_build_correction_qa_report()`)
    ersetzt den ursprünglichen (gleicher Dateiname).
  - `ui/workers.py`: `_copy_pdf_stats()` (Zwischenkopie für die
    Qt-Thread-Grenze bei Live-Fortschritt) um `list(stats.blocks)`
    ergänzt - sonst wäre das neue Feld auf dem Zwischenstand verloren
    gegangen (wenngleich nur der FINALE, per `finished`-Signal
    übertragene Stand für die Korrektur-Tabelle zählt).
  - `ui/correction_dialog.py` (neu): `PdfCorrectionDialog` - `QTableWidget`
    mit Spalten Seite/Original (read-only)/Übersetzung (editierbar),
    "Anwenden und speichern"-Knopf. Läuft bewusst SYNCHRON auf dem
    UI-Thread statt über `QThreadPool` wie die eigentlichen
    Übersetzungs-Worker - hier gibt es keinerlei Netzwerkaufruf mehr
    (jeder Record trägt sein finales `translated_html` schon in sich),
    ein eigener Worker/Signals-Umweg wäre unnötiger Aufwand für eine
    ohnehin schnelle, rein lokale Operation. Bei Erfolg werden sowohl
    `last_result` (das `PdfJobResult`) als auch `last_corrected_records`
    (die tatsächlich geschriebene Record-Liste) gesetzt - Letzteres
    eigens deshalb, weil `apply_pdf_corrections()`s zurückgegebene
    `PdfTranslationStats.blocks` per Vertrag LEER bleibt (siehe deren
    Docstring) und daher NICHT als neue Grundlage für einen zweiten
    Korrektur-Durchgang taugt.
  - `ui/app.py`: neuer, standardmäßig unsichtbarer
    `correct_translation_button` neben `open_folder_button`/
    `open_report_button` - sichtbar nur nach einem PDF-Lauf mit
    tatsächlich vorhandenen `stats.blocks` (per Revert-Probe bestätigt:
    ohne die `isinstance(...)  and bool(stats.blocks)`-Bedingung bleibt
    der Knopf in den entsprechenden Tests fälschlich sichtbar/unsichtbar).
    `_start()` merkt sich zusätzlich `_job_source_path`/
    `_job_exclude_header`/`_job_exclude_footer` für den späteren
    Korrektur-Aufruf (die eigentliche Quelldatei wird von `translate_pdf()`
    selbst nie verändert, bleibt also für einen zweiten Durchlauf
    verfügbar). `_open_correction_dialog()` übernimmt nach einem
    erfolgreichen "Anwenden" bewusst `dialog.last_corrected_records`
    (nicht das leere `stats.blocks` des Korrektur-Ergebnisses) als neue
    `blocks`-Grundlage - sonst würde ein erneutes Öffnen der Tabelle die
    gerade gespeicherte Korrektur stillschweigend verwerfen und wieder
    bei der ursprünglichen Maschinenübersetzung anfangen (per
    Revert-Probe bestätigt).

  Bekannte, dokumentierte Einschränkung: nur der `block.spans`-Pfad
  (HTML/Story) wird als `TranslatedBlockRecord` erfasst - der einzige,
  den echte Produktionsblöcke je durchlaufen (siehe `insert_text()`s
  Docstring, mehrfach in dieser Datei bestätigt); der reine
  Text-Fallback-Pfad (leere `block.spans`) ist nicht über diese Tabelle
  korrigierbar, aber auch praktisch nicht erreichbar - keine echte
  Einschränkung, nur der Vollständigkeit halber dokumentiert.

  Regressionsabdeckung, drei neue Dateien:
  `tests/test_pdf_translation_corrections.py` (6 Tests: `html_to_plain_
  text()`-Fälle, `translate_pdf()` befüllt `stats.blocks` korrekt,
  `build_corrected_records()` baut nur bearbeitete Zeilen neu,
  ignoriert fehlende Keys, voller Korrektur-Rundlauf behebt den
  bearbeiteten Block UND erhält die Fett-Formatierung des unbearbeiteten
  - inklusive der `apply_pdf_corrections()`-eigenen Voraussetzung "frische
  Engine auf der Quelle"); `tests/test_pdf_correction_job.py` (3 Tests:
  `run_pdf_correction_job()` überschreibt die bestehende Ausgabedatei
  tatsächlich mit dem korrigierten Text, verweigert Quelle=Ziel, hat
  nachweislich keinen Provider-Parameter); `tests/test_ui_pdf_correction.py`
  (5 Tests, Qt-Ebene mit `QT_QPA_PLATFORM=offscreen`: Korrektur-Knopf
  sichtbar/unsichtbar je nach `stats.blocks`, unsichtbar für Nicht-PDF-
  Ergebnisse, voller End-to-End-Durchlauf über die echte Dialog-Klasse
  mit gemocktem `exec()` - simuliert Zelleneingabe + Anwenden-Klick statt
  eine echte blockierende Modal-Schleife zu öffnen -, unbearbeitete Zeile
  bleibt HTML-identisch). Alle drei entscheidenden Verhaltensänderungen
  (Block-Erfassung in `translate_pdf()`, Knopf-Sichtbarkeit, Records-
  Weitergabe bei erneutem Öffnen) per Revert-Probe bestätigt fehlschlagend
  ohne den jeweiligen Fix. Gesamter Testlauf am Ende: 134 passed, 1
  skipped (vorher 120 passed, 1 skipped - 14 neue Tests in 3 neuen
  Dateien).

  **Nachtrag - Rich-Text-Editor statt Klartext (18.08.2026):** Der obige
  Kompromiss ("eine bearbeitete Zeile verliert ihre Inline-Formatierung")
  wurde dem Nutzer erklärt, als er nachfragte, warum eine Korrektur die
  Formatierung kostet. Seine Antwort war eindeutig: "Ein Rich-Text-Editor
  ist wichtig für mich." Umgesetzt statt weiter dokumentiert:
  - `ui/rich_text.py` (neu): das einzige Modul im Projekt, das
    Qt-Rich-Text-Klassen (`QFont`, `QTextDocument`) importieren darf -
    dieselbe Trennung wie `pymupdf_engine.py`s fitz-Exklusivität, damit
    die Pipeline-Schicht UI-Framework-unabhängig bleibt.
    `qt_document_to_project_html()` läuft ein `QTextDocument` Block für
    Block (= Absatz) und Fragment für Fragment (= zusammenhängender
    Formatierungslauf) ab und baut daraus dasselbe minimale
    `<p>`/`<br/>`/`<u>`/`<i>`/`<b>`-Markup, das `spans_to_html()` schon
    erzeugt (Fett über `fontWeight() >= QFont.Weight.Bold`, dieselbe
    Zwei-Zustände-Logik wie der Fett-Knopf selbst setzt). Bewusst NICHT
    `QTextDocument.toHtml()`/`toMarkdown()` verwendet - beide erzeugen ein
    volles, verbose HTML-Dokument (Styles, Fonts, `<html><body>`-Hülle),
    das mit dem schmalen Tag-Set nichts zu tun hat, das
    `PyMuPdfEngine.insert_text()` erwartet. Die umgekehrte Richtung
    (Laden) braucht keine eigene Konvertierung: `QTextEdit.setHtml()`
    versteht das schmale Tag-Set direkt, da es eine strikte Teilmenge von
    Qt's eigenem unterstützten HTML4-Dialekt ist.
  - `pipeline/pdf/translate_pdf.py`: neue
    `build_corrected_records_from_html(records, edited_html)` - Pendant
    zu `build_corrected_records()`, nimmt aber bereits fertiges
    Projekt-HTML entgegen (aus `qt_document_to_project_html()`) statt
    Klartext, also ohne den verlustbehafteten `_plain_text_to_html()`-
    Umweg. `edited_html` enthält NUR Zeilen, die der Dialog als
    tatsächlich bearbeitet erkannt hat (siehe unten) - eine fehlende
    (page_index, block_index)-Kombination wird unverändert (identisches
    Objekt) durchgereicht, exakt wie beim Klartext-Pendant. Die alte
    Funktion bleibt bestehen (eigene Tests, möglicher künftiger
    Datei-/CLI-Korrekturweg), wird vom Dialog seitdem aber nicht mehr
    aufgerufen - im Docstring vermerkt, damit das nicht wie eine
    vergessene Altlast aussieht.
  - `ui/correction_dialog.py`: von "Zelle direkt editierbar" auf
    Master-Detail umgebaut. Die Tabelle zeigt Seite/Original/Übersetzung
    nur noch als Nur-Lese-Vorschau (aktualisiert beim Zeilenwechsel/
    Anwenden); die eigentliche Bearbeitung passiert in einem separaten
    `QTextEdit` darunter mit drei Umschalt-Knöpfen (Fett/Kursiv/
    Unterstrichen), die `QTextEdit.mergeCurrentCharFormat()` aufrufen -
    laut Qt-Dokumentation wirkt das automatisch auf eine vorhandene
    Selektion oder, ohne Selektion, auf ab jetzt neu getippten Text; ein
    manuelles Cursor-`mergeCharFormat()` daneben ist dafür NICHT nötig
    (erste Version hatte das überflüssigerweise, vereinfacht).
    Zeilenwechsel-Tracking: `_row_html` (aktueller HTML-Stand je Zeile,
    startet identisch mit dem Original), `_dirty` (Set der Zeilen, die
    das `textChanged`-Signal WÄHREND echter Bearbeitung gesehen hat - ein
    `_loading`-Guard blendet das programmatische `setHtml()` beim
    Zeilenwechsel selbst aus). `_flush_active_row()` schreibt den
    Editor-Inhalt nur für eine als dirty markierte Zeile zurück in
    `_row_html`; `_apply()`s `_current_edits()` nimmt ohnehin nur dirty
    Zeilen in `edited_html` auf - zwei unabhängige Sperren mit
    überlappendem, aber nicht identischem Zweck (siehe Testabschnitt
    unten für den Unterschied).
  - i18n (`ui/i18n.py`): `correction.hint` umformuliert (Formatierung
    geht bei einer Korrektur NICHT mehr verloren), plus drei neue Keys
    `correction.editor_label`/`correction.bold`/`correction.italic`/
    `correction.underline` (DE/EN-Parität weiterhin per Set-Vergleich
    bestätigt).

  Bewusst NICHT gebaut, um den Umfang beherrschbar zu halten: Tastatur-
  kürzel (Strg+B/K/U) für die Formatierungs-Knöpfe - nur Klick auf die
  Toolbar-Knöpfe. Bei Bedarf leicht nachrüstbar (`QShortcut` auf den
  Editor), aber nicht Teil dieser Runde.

  Regressionsabdeckung: `tests/test_pdf_rich_text_corrections.py` (neu,
  12 Tests) - `qt_document_to_project_html()` gegen Klartext-Rundlauf,
  Fett/Kursiv+Unterstrichen-Kombination (Tag-Verschachtelung exakt wie
  `spans_to_html()`: `<u>` innen, `<i>` außen, `<b>` außerhalb davon),
  Teilselektion (genau der reale "nur ein Wort fett machen"-Fall),
  Mehrfach-Absätze, weicher Zeilenumbruch (Shift+Enter, U+2028) wird zu
  `<br/>`, HTML-Sonderzeichen werden escaped, leerer Editor ergibt
  Leerstring; `build_corrected_records_from_html()` mit fehlendem/
  vorhandenem/nicht-passendem Key; ein End-to-End-Test durch den ECHTEN
  `PdfCorrectionDialog` (nicht nur die Konvertierungsfunktion isoliert),
  der "Manuel" korrigiert UND fett setzt, während ein unberührter fett
  formatierter zweiter Block seine Formatierung behält - Prüfung direkt
  an den im gespeicherten PDF tatsächlich verwendeten Font-Namen
  (`"bold" in span["font"].lower()`), nicht nur am reinen Text.
  `tests/test_ui_pdf_correction.py` erweitert (jetzt 6 Tests): der
  bestehende End-to-End-Test bearbeitet jetzt den Editor statt eine
  Tabellenzelle direkt zu setzen; ein neuer, gezielter Test prüft NUR
  `_flush_active_row()`s eigene Dirty-Prüfung isoliert (Zeile 1 laden,
  ohne Bearbeitung zu Zeile 2 wechseln, `_row_html[0] is original_html`
  prüfen) - per Revert-Probe bestätigt fehlschlagend ohne diese Prüfung,
  UND zugleich bestätigt, dass eine schwächere `==`-Prüfung auf dem
  End-to-End-Ergebnis diese konkrete Regression NICHT gefangen hätte
  (der Qt-Roundtrip erzeugt für unformatierten Text zufällig denselben
  String - `_current_edits()`s eigene Dirty-Prüfung schützt das
  Endergebnis unabhängig davon bereits vollständig; nur die
  Objektidentitätsprüfung auf `_row_html` selbst deckt eine Regression in
  `_flush_active_row()`s eigener Sperre auf). Gesamter Testlauf am Ende:
  147 passed, 1 skipped (vorher 134 passed, 1 skipped - 13 neue Tests,
  davon 12 in einer neuen Datei).

  **Nachtrag 2 - Tastaturkürzel (18.08.2026):** Direkter Folgewunsch nach
  dem Rich-Text-Editor: "GErne noch die Tastaturkürzel mit einbauen."
  Ergänzt statt eines eigenen Kürzel-Schemas die Qt-Standardbindungen
  `QKeySequence.StandardKey.Bold/Italic/Underline` (Strg+B/I/U auf
  diesem Linux-Desktop, plattformgerecht z. B. Cmd auf macOS) - dieselbe
  Bindung, die jeder andere Rich-Text-Editor (Word, LibreOffice, Qt's
  eigenes Richtext-Beispiel) verwendet, statt etwas Eigenes zu erfinden.
  - `ui/correction_dialog.py`: drei `QShortcut`-Instanzen auf
    `self.editor` mit `Qt.ShortcutContext.WidgetShortcut` (feuern nur bei
    Fokus im Editor, nicht global im ganzen Dialog). Ein `QShortcut` hat
    selbst keinen Checked-Zustand wie ein `QPushButton` - die drei neuen
    `_shortcut_toggle_bold/italic/underline()`-Handler flippen den
    jeweiligen Toolbar-Knopf deshalb zuerst manuell und rufen danach
    dieselbe bestehende `_toggle_*()`-Logik auf, exakt wie ein echter
    Mausklick auf den Knopf. Zusätzlich Tooltips auf den drei Knöpfen
    ("Fett (Strg+B)" usw.).
  - `ui/i18n.py`: drei neue Tooltip-Keys (`correction.bold_tooltip` etc.,
    DE/EN-Parität bestätigt), `correction.hint` erwähnt die Kürzel jetzt.
  Regressionsabdeckung: vier neue Tests in
  `tests/test_ui_pdf_correction.py` - Key-Binding-Check (die drei
  `QShortcut`s sind tatsächlich an `QKeySequence.StandardKey.Bold/
  Italic/Underline` gebunden, nicht an eine hart codierte, potenziell
  plattformfalsche Tastenkombination), Bold-Handler inkl. Zurück-Toggle
  bei zweitem Aufruf, Kursiv/Unterstrichen-Handler (mit Bestätigung, dass
  der jeweils andere Knopf unberührt bleibt), End-to-End-Test bis ins
  tatsächlich gespeicherte PDF (`<b>` im übernommenen `translated_html`).
  Per Revert-Probe bestätigt: mit den drei `_shortcut_toggle_*()`-
  Methoden auf No-Ops reduziert schlagen genau die drei
  Verhaltens-Tests fehl, während der reine Key-Binding-Test korrekt grün
  bleibt (er prüft nur die Bindung, nicht das Verhalten - erwartungs-
  gemäß unberührt von dieser Änderung). Gesamter Testlauf am Ende: 151
  passed, 1 skipped (vorher 147 passed, 1 skipped - 4 neue Tests).

- **"ICO-Dokument"-Konzept für PDF nachgerüstet (18.08.2026):** Auf
  ausdrücklichen Nutzerwunsch ("ICO-Dokument auf alle Fälle nachrüsten")
  das für Word bereits bestehende `ico_mode`-Konzept (siehe oben,
  Eintrag zu `DocxEngine.open(ico_mode=...)`) 1:1 auf PDF übertragen.

  **Auslöser/Motivation:** `_split_first_page_metadata()` in
  `pipeline/pdf/pymupdf_engine.py` (Trennung von Seite-0-Zeilengruppen an
  `FIRST_PAGE_ANCHOR_TERMS = ["Issuer Address", "Asset Matrix"]`) lief
  bis dahin für JEDES PDF unbedingt mit - dieselbe Fehlerklasse, die
  `DocxEngine`s `ico_mode` für Word schon verhindert: ein PDF, das
  zufällig eine dieser Zeilen aus anderem Grund enthält, ohne
  tatsächlich ein "ICO-Dokument" zu sein, hätte ohne Vorwarnung einen
  Teil von Seite 1 unübersetzt gelassen.

  **Architektur (Datei für Datei):**
  - `pipeline/pdf/pymupdf_engine.py`: `__init__` bekommt `self._ico_mode
    = False` und `self.first_page_metadata_found = False` (Pendant zu
    `DocxEngine.separator_found`, exakt so benannt/dokumentiert).
    `open(path, ico_mode=False)` nimmt den neuen Parameter, setzt
    `self._ico_mode` und setzt `first_page_metadata_found` bei jedem
    `open()` frisch zurück. `extract_blocks()`s Gating-Bedingung für die
    Seite-0-Sondertrennung wurde von `if page_index == 0` auf `if
    page_index == 0 and self._ico_mode` verschärft; ein neues
    `found_metadata_split`-Flag wird während der Blockschleife gesetzt
    und am Ende (nur für `page_index == 0`) nach
    `self.first_page_metadata_found` übernommen. `extract_blocks()`
    cached zwar `self._page_blocks_cache`, liest ihn aber nie zum
    Überspringen der Neuberechnung - jeder Aufruf (auch mehrfach pro
    Seite, z. B. einmal über `total_block_count()`, einmal über
    `translate_pdf()`s Blocksammlung) berechnet `first_page_metadata_found`
    daher zuverlässig neu.
  - `ui/pdf_job.py`: `run_pdf_job(..., ico_mode=False)` reicht den
    Schalter an `engine.open()` durch. `_build_qa_report()` bekommt
    `ico_mode`/`first_page_metadata_found` als Parameter und exakt
    dieselbe dreistufige Meldung wie beim Word-Pendant: aktiv & etwas
    gefunden → Metadatenbereich wurde ausgeschlossen; aktiv & nichts
    gefunden → Warnhinweis, ob das Dokument wirklich vom erwarteten
    ICO-Typ ist; nicht aktiv → normaler Hinweis auf vollständige
    Übersetzung.
  - `ui/workers.py` (`PdfTranslationWorker`) und `ui/analysis.py` (PDF-
    Zweig ruft `engine.open(..., ico_mode=request.ico_mode)`, damit
    Kostenschätzung und tatsächlicher Lauf denselben Zustand sehen -
    Kommentar spiegelt den bereits vorhandenen Word-Kommentar an
    derselben Stelle) entsprechend angepasst.
  - `ui/i18n.py`: `ico_mode.tooltip` (DE/EN) von einer rein
    Word-spezifischen Beschreibung (Trennform-Erkennung) auf eine
    formatneutrale Formulierung umgeschrieben, die beide Mechanismen
    (Word-Trennform, PDF-Ankerbegriffe) abdeckt.
  - `ui/app.py`: bewusst KEINE zweite, PDF-eigene Checkbox - stattdessen
    dieselbe `TranslationRequest.ico_mode`/`self.ico_mode`-Checkbox
    wiederverwendet, da `TranslationRequest.ico_mode` schon vorher ein
    generisches (nicht Word-spezifisches) Dataclass-Feld war und nur die
    UI-Sichtbarkeit Word-only gegated hatte. `_mode_changed()` berechnet
    jetzt sowohl `is_word` als auch `is_pdf` und zeigt die Checkbox bei
    `is_word or is_pdf`; zurückgesetzt (unchecked) wird sie nur beim
    Wechsel in einen Modus, der KEINES von beiden ist (Präsentation/
    Bilder) - ein Wechsel Word↔PDF behält den Haken bewusst bei, da
    beide Formate das Konzept unterstützen. `_start()`s PDF-Zweig reicht
    `ico_mode` zusätzlich zu `exclude_header`/`exclude_footer` an den
    Worker durch.

  **Testfixture-Besonderheit:** Die synthetischen Test-PDFs in
  `tests/test_pdf_ico_mode.py` bauen ihre Seite-0-Zeilen über
  `page.insert_text()` einzeln bei manuell kontrollierten,
  gleichmäßig verteilten y-Koordinaten auf (inklusive eines echten
  `" "`-Strings als "Leerzeile") statt über
  `page.insert_textbox(..., "\n\n")`. Per direkter Untersuchung
  bestätigt: `insert_textbox()` erzeugt bei einer Leerzeilen-Lücke ZWEI
  getrennte rohe PyMuPDF-Blöcke, während `_split_first_page_metadata()`
  nur Zeilen INNERHALB eines einzigen Blocks sieht - die reale,
  vertrauliche "1526 VIRELICON.pdf", für die dieser Mechanismus
  ursprünglich gebaut wurde, hat Metadatenzeile, Adresszeile, Leerzeile
  und Titelzeile alles in einem einzigen PyMuPDF-Block. Nur
  `insert_text()` pro Zeile reproduziert diese Ein-Block-Form korrekt.

  **Testabdeckung:** `tests/test_pdf_ico_mode.py` (neu, 8 Tests) -
  Engine-Ebene: `ico_mode=False` lässt Metadaten übersetzbar,
  `ico_mode=True` trennt und markiert non-translatable,
  `ico_mode=True` ohne passenden Ankerbegriff findet nichts, Sonderfall
  gilt nur für Seite 0 (nicht für spätere Seiten), erneutes `open()`
  setzt Zustand zuverlässig zurück. Job-Ebene: `ico_mode=True` mit Fund
  (Metadaten bleiben im Output unverändert/unübersetzt, QA-Bericht
  nennt es), `ico_mode=False` (alles inklusive Metadaten wird
  übersetzt), `ico_mode=True` ohne Fund (QA-Warnung). Zusätzlich
  `tests/test_ui_word_mode.py` erweitert:
  `test_ico_mode_checkbox_visible_for_word_and_pdf_modes` (umbenannt von
  der vorherigen Word-only-Version, prüft jetzt Sichtbarkeit/Erhalt über
  Word→PDF UND Reset bei Präsentation) sowie neu
  `test_pdf_worker_receives_ico_mode_from_request` (PDF-Pendant zum
  bestehenden Word-Test).

  Jede einzelne Änderung per Revert-Probe verifiziert (Engine-Gating in
  `extract_blocks()`, QA-Bericht-Meldungsblock in `_build_qa_report()`,
  UI-Sichtbarkeitslogik in `_mode_changed()` - jeweils gezielt auf den
  alten/fehlenden Zustand zurückgebaut, erwarteter Testfehler bestätigt,
  aus Backup wiederhergestellt, `diff` bestätigt byte-genaue
  Wiederherstellung, danach Gesamtsuite erneut grün). Gesamter Testlauf
  am Ende: 160 passed, 1 skipped (vorher 151 passed, 1 skipped - 9 neue
  Tests, davon 8 in einer neuen Datei).

- **Bildübersetzung/OCR - Pipeline-Fundament (18.08.2026):** Erster
  Umsetzungsblock von RoadMap.md Phase 3, auf ausdrücklichen Nutzerwunsch
  ("Wie wollen wir die Bild Übersetzung angehen?"). UI-Anbindung folgt
  als eigener, noch offener Punkt - siehe RoadMap.md.

  **Architektur:** Zwei neue Backend-Abstraktionen nach dem Vorbild von
  `pipeline/translation/base.py::TranslationProvider`:
  - `pipeline/images/ocr.py`: `OcrEngine`-Protocol (`recognize(image_path,
    language) -> list[OcrTextRegion]`), `OcrTextRegion`
    (text/x/y/width/height/confidence, Pixelkoordinaten wie
    Pillow/OpenCV/PyMuPDF sie ohnehin verwenden), `TesseractOcrEngine`
    (pytesseract, lazy import) und `tesseract_available()`
    (`shutil.which("tesseract")`, analog zu
    `ui/settings.py::credential_status()`).
    `_group_words_into_lines()`: `pytesseract.image_to_data()` liefert
    eine Zeile PRO WORT, gruppiert nach `(block_num, par_num, line_num)`
    - direkt experimentell bestätigt, dass die Einfügereihenfolge des
    dict schon der Lesereihenfolge entspricht (kein zusätzliches
    Sortieren nötig), weil `image_to_data()` selbst block-/zeilenweise
    iteriert.
  - `pipeline/images/inpainting.py`: `InpaintingBackend`-Protocol
    (`apply(image_path, replacements, output_path)`), `TextReplacement`
    (Region + übersetzter Text). Zwei Implementierungen:
    `BoxOverlayBackend` (Fläche mit einer aus einem Ring AUSSERHALB der
    Box gemittelten Umgebungsfarbe übermalen - bewusst kein einzelner
    Randpixel, da der sonst versehentlich einen Buchstaben-Rest treffen
    kann; Kontrastfarbe für den neuen Text per ITU-R-BT.601-
    Luminanzformel) und `CvInpaintingBackend` (`cv2.inpaint()`, Telea-
    Algorithmus, klassisch ohne KI-Modell - Hintergrundfarbe für den
    neuen Text wird hier aus dem bereits REKONSTRUIERTEN Bereich selbst
    gemittelt, nicht aus einem Außenring, da die Fläche nach dem
    Inpainting selbst schon ein gültiger Hintergrund ist). Ein
    Gradienten-Test bestätigt den konkreten Unterschied zwischen beiden:
    nach `CvInpaintingBackend` unterscheiden sich linker und rechter Rand
    der ersetzten Fläche noch messbar (Farbverlauf wird fortgesetzt),
    während eine reine Box-Overlay-Füllung beide Ränder auf dieselbe
    Flächenfarbe abbilden würde.
  - `pipeline/images/translate_image.py::translate_image()`: kompletter
    Durchlauf (OCR einmal vorab -> pro Region übersetzen -> alle
    Ersetzungen am Ende in EINEM `InpaintingBackend.apply()`-Aufruf
    zurückschreiben), spiegelt `translate_pdf()`/`translate_document()`
    (Fortschritts-/Abbruch-/Stats-Callbacks, ein fehlschlagender Block
    bricht nicht den ganzen Lauf ab). Strukturunterschied zu den anderen
    drei Formaten: es gibt kein einzelnes, in-place mutierbares
    Dokumentobjekt zum Redact/Insert - deshalb schreibt ein Abbruch
    trotzdem eine Ausgabedatei (mit allem bis zum Abbruchpunkt
    Übersetzten), statt wie bei PDF/Word/PPTX ein sauberes Teilergebnis
    mitten im Dokument zu hinterlassen.
  - `ui/image_job.py::run_image_job()`: Job-Ablauf analog zu
    `run_pdf_job()` (Zieldatei-Konfliktprüfung, `TranslationBudgetGuard`-
    Einbindung, QA-Bericht). Verarbeitet genau EIN Bild pro Aufruf - ein
    Mehrdatei-Batch (von `TranslationMode.IMAGES` ausdrücklich erlaubt)
    wäre mehrere `run_image_job()`-Aufrufe; diese Schleife existiert im
    UI noch nicht (siehe RoadMap.md, "Noch offen").
  - `ui/document_job_common.py`: `OCR_ENGINE_FACTORIES`/
    `INPAINTING_BACKEND_FACTORIES` (aktuell `{"tesseract": ...}` bzw.
    `{"box_overlay": ..., "cv_inpainting": ...}`) plus
    `build_ocr_engine()`/`build_inpainting_backend()`/
    `ocr_engine_available()`, exakt nach dem Muster von
    `PROVIDER_FACTORIES`/`build_provider()`. Bewusst hier statt in
    `pipeline/images/` platziert, damit die geplante Einbettung derselben
    Auswahl in PDF/Word/PPTX (RoadMap.md, noch offen) dieselbe,
    bereits geteilte Stelle importieren kann statt in `ui/image_job.py`
    nachzuschlagen.
  - `requirements-ocr.txt` um `opencv-python-headless` erweitert
    (headless: keine GUI-Abhängigkeiten nötig, PySide6 bringt die
    Desktop-UI bereits über einen eigenen Weg mit).

  **Testfixture-Besonderheit:** Alle synthetischen Test-Bilder (OCR-,
  Inpainting- und Job-Tests) werden mit einem echten TrueType-Font
  (DejaVuSans) statt Pillows eingebautem Bitmap-Default-Font gezeichnet -
  direkt experimentell bestätigt, dass der Default-Font "Hello World" zu
  einem einzigen, von Tesseract nicht mehr trennbaren "Helloworld"
  zusammenzieht (zu klein/eng für echten Zeichenabstand), während
  DejaVuSans bei normaler Textgröße beide Wörter zuverlässig mit hoher
  Konfidenz einzeln erkennt.

  **Testabdeckung:** 38 neue Tests über sechs neue Dateien -
  `tests/test_image_ocr.py` (5, inkl. Zeilen-Gruppierung end-to-end
  gegen echtes Tesseract), `tests/test_image_inpainting.py` (8, Box-
  Overlay inkl. Hintergrundfarbe-Sampling-Unittest und einem echten
  OCR-Rundlauf gegen die Ausgabedatei), `tests/test_image_cv_inpainting.py`
  (6, inkl. des Gradienten-Vergleichstests oben), `tests/test_translate_image.py`
  (6, Fehlerbehandlung pro Region, Abbruchverhalten, geschützte Begriffe),
  `tests/test_document_job_common.py` (7, Factories/Verfügbarkeitsprüfung),
  `tests/test_image_job.py` (6, Zieldatei-Konflikte, QA-Bericht-Inhalt,
  Backend-Auswahl). Jede Kernmechanik einzeln per Revert-Probe verifiziert
  (siehe Architektur-Absätze oben für welche) - jeweils gezielt auf den
  fehlerhaften/fehlenden Zustand zurückgebaut, erwarteter Testfehler
  bestätigt, aus Backup wiederhergestellt, `diff` bestätigt byte-genaue
  Wiederherstellung, danach Gesamtsuite erneut grün. Gesamter Testlauf am
  Ende: 198 passed, 1 skipped (vorher 160 passed, 1 skipped).

- **Bildübersetzung/OCR - Mehrdatei-Batch und UI-Anbindung (18.08.2026):**
  Zweiter Umsetzungsblock von RoadMap.md Phase 3, direkt auf das
  Pipeline-Fundament (siehe Eintrag oben) aufbauend. Klärt beide dort als
  "Noch offen" markierten Punkte: die Mehrdatei-Verarbeitung (Nutzer
  entschied sich für "Nacheinander, alle automatisch") und die echte
  UI-Anbindung in `ui/app.py`.

  **Mehrdatei-Batch:**
  - `ui/image_job.py::run_image_batch_job()`: Schleife über alle
    ausgewählten Dateien, ruft `run_image_job()` pro Datei auf (eigene
    Zieldatei via `safe_destination()`, kollisionssicher auch gegen
    bereits in diesem Lauf geschriebene Dateien desselben Batches).
    Abbruch wird ZWISCHEN Dateien geprüft (nie mitten in einer Datei -
    das übernimmt weiterhin `translate_image()`s eigene, feinere
    Abbruchprüfung pro Textregion) - beide Abbruchpunkte sind im
    Docstring bewusst als zwei unterschiedliche Ebenen dokumentiert.
    Bekannte, dokumentierte Vereinfachung: `max_chars_per_run` gilt PRO
    DATEI (jeder `run_image_job()`-Aufruf baut einen frischen
    `TranslationBudgetGuard`), nicht gemeinsam über den ganzen Batch wie
    bei einem mehrseitigen PDF - eine Umstellung darauf würde eine
    Änderung an `run_image_job()`s Signatur brauchen (bereits
    umschlossenen Provider annehmen statt selbst neu zu umschließen),
    hier bewusst als Vereinfachung für den ersten Wurf zurückgestellt.
  - `ImageBatchStats`/`ImageBatchJobResult`: duck-typen dieselben
    `.processed`/`.translated`/`.skipped`/`.failed`/`.chars_sent`/
    `.cancelled`-Felder wie `PresentationTranslationStats`/
    `WordTranslationStats`/`PdfTranslationStats`, damit `ui/app.py`s
    `_job_stats()`/`_update_job_status()` ohne Modus-Verzweigung
    funktionieren. `processed`/`files_total` zählen Dateien, nicht
    Textregionen - der Fortschrittsbalken bewegt sich pro fertiger
    Datei, während `progress_callback` weiterhin die Detailzeile pro
    Region innerhalb der aktuellen Datei zeigt.
  - `ui/workers.py::ImageTranslationWorker`: einziger Worker mit
    strukturell anderer Signatur als die übrigen drei (`sources: list[
    Path]` + ein `output_dir` statt `source`/`destination`), da
    `TranslationMode.IMAGES` der einzige Modus ist, dessen
    `TranslationRequest` mehrere Quelldateien gleichzeitig erlaubt.

  **UI-Anbindung (`ui/app.py`):**
  - Zwei neue, nur für `TranslationMode.IMAGES` sichtbare Dropdowns
    (OCR-Engine, Rückschreibe-Backend), gespeist direkt aus
    `OCR_ENGINE_FACTORIES`/`INPAINTING_BACKEND_FACTORIES` statt
    hartkodierter Listen - ein künftiges drittes Backend (Cloud-OCR,
    GPU-/Cloud-Inpainting) erscheint automatisch im Dropdown, sobald es
    dort registriert ist. `_update_ocr_engine_hint()` spiegelt
    `_update_provider_credential_hint()`s Muster: die
    Verfügbarkeitsprüfung (`ocr_engine_available()`) läuft proaktiv bei
    jeder Auswahl/jedem Moduswechsel, nicht erst beim Start.
  - `_start()`: fail-fast-Warnung, falls die gewählte OCR-Engine nicht
    verfügbar ist (analog zur bestehenden Prüfung auf fehlende
    Zugangsdaten) - vor jeder Ordnerauswahl, nicht erst nach einem
    halben, fehlgeschlagenen Lauf. Für IMAGES-Modus wird jetzt EIN
    `ImageTranslationWorker` mit ALLEN ausgewählten Quelldateien gebaut
    (`list(request.source_paths)`), nicht mehr nur `source_paths[0]` -
    das war die im Pipeline-Fundament-Eintrag oben dokumentierte,
    bewusst offen gelassene Lücke. Der gewählte Zielordner wird für
    IMAGES direkt als `output_dir` verwendet statt über
    `safe_destination()` in eine einzelne Zieldatei aufgelöst zu werden.
  - `_show_job_result()`/`_open_output_folder()`/`_open_qa_report()`:
    neue `isinstance(result, ImageBatchJobResult)`-Zweige, da dieser
    Ergebnistyp einen `output_dir` statt eines einzelnen
    `output_path`/`qa_report_path` hat (ein QA-Bericht PRO Bild, alle im
    selben Ordner) - der "QA-Bericht öffnen"-Button wird für diesen Typ
    ausgeblendet statt eine beliebige der mehreren Berichtsdateien zu
    öffnen.
  - `ui/analysis.py`: der bisherige IMAGES-Platzhalter (immer 0 Zeichen,
    nur eine Warnung) wurde durch einen echten Tesseract-OCR-Lauf über
    alle ausgewählten Dateien ersetzt (gated durch
    `ocr_engine_available()`, mit Fallback auf dieselbe Warnung bei
    nicht verfügbarer Engine oder einem einzelnen nicht dekodierbaren
    Bild). Grund: sobald der IMAGES-Modus über den Start-Button
    tatsächlich lauffähig wurde, hätte eine stets $0.00 zeigende
    Kostenschätzung RoadMap.mds Leitprinzip "Vor jedem kostenpflichtigen
    Lauf erfolgen Analyse, Kostenschätzung und ausdrückliche
    Bestätigung" verletzt.
  - `ui/i18n.py`: neue Schlüssel `field.ocr_engine`,
    `ocr_engine.tesseract`, `ocr_engine.unavailable`,
    `field.inpainting_backend`, `inpainting_backend.box_overlay`,
    `inpainting_backend.cv_inpainting`, `start.confirm_summary_images`,
    `job.progress_count_files`, `job.result_summary_images` - jeweils in
    DE und EN, DE/EN-Schlüsselparität durch den bestehenden
    `test_ui_i18n.py`-Test abgesichert.

  **Testabdeckung:** `tests/test_image_batch_job.py` (6 Tests für
  `run_image_batch_job()`: jede Datei verarbeitet, Dateinamenkollisionen
  vermieden, Abbruch zwischen Dateien, kumulative Stats, funktioniert
  auch für genau eine Datei) plus `tests/test_ui_images_mode.py` (7
  Tests, spiegelt `tests/test_ui_word_mode.py`s Muster: Modus nicht mehr
  blockiert, Zeilen-Sichtbarkeit der neuen Dropdowns, `_request()` trägt
  die neuen Felder, Worker-Dispatch mit ALLEN Quelldateien statt nur der
  ersten, Fail-fast-Warnung bei fehlender OCR-Engine, dateibasierte
  Fortschrittsformulierung, Ergebnisdarstellung ohne QA-Bericht-Button).
  Kern-Mechanik (Batch-Dispatch: ein Worker für den ganzen Batch statt
  nur `source_paths[0]`) per Revert-Probe verifiziert: gezielt auf
  `[request.source_paths[0]]` zurückgebaut, erwarteter Testfehler
  bestätigt (Assertion zeigt nur 1 statt 3 erwarteter Quelldateien), aus
  Backup wiederhergestellt, `diff` bestätigt byte-genaue
  Wiederherstellung, danach Gesamtsuite erneut grün. Zusätzlich per
  eigenständigem Offscreen-Qt-Smoketest (`QT_QPA_PLATFORM=offscreen`)
  verifiziert, dass die neuen Formularzeilen bei Moduswechsel korrekt
  ein-/ausgeblendet werden und `_request()` die Dropdown-Auswahl korrekt
  überträgt. Gesamter Testlauf am Ende: 212 passed, 1 skipped (vorher
  198 passed, 1 skipped).

- **Bildübersetzung/OCR - GPU-Inpainting-Backend (LaMa) (18.08.2026):**
  Dritter Umsetzungsblock von RoadMap.md Phase 3, direkt im Anschluss an
  Fundament und Mehrdatei-Batch/UI-Anbindung (siehe die beiden Einträge
  oben). Auf ausdrücklichen Nutzerwunsch ("Also beides CPU und
  GPU-Inpainting umsetzen") als viertes Rückschreibe-Backend neben
  Box-Overlay/CvInpaintingBackend hinzugefügt.

  **Architektur:** `pipeline/images/inpainting.py::GpuInpaintingBackend`
  nutzt das vortrainierte LaMa-Modell (Large-Mask-Inpainting,
  https://github.com/advimman/lama) über die leichtgewichtige
  `simple-lama-inpainting`-Wrapper-Bibliothek (`SimpleLama(image, mask)
  -> Image`, API per WebFetch gegen das GitHub-Repo verifiziert statt
  aus dem Gedächtnis angenommen - Konstruktor nimmt ein
  `torch.device`-Argument, hier immer explizit `"cuda"`, nie die eigene
  Default-Logik der Bibliothek). Neue optionale `requirements-gpu.txt`
  (getrennt von `requirements-ocr.txt`, da PyTorch eine deutlich
  größere, GPU-spezifische Installation ist, inkl. Hinweis auf die
  CUDA-spezifische Installationsanleitung unter pytorch.org statt eines
  einfachen "pip install torch").
  - `gpu_inpainting_available(min_vram_gb=GPU_MIN_VRAM_GB)`: prüft VOR
    jedem Lauf (mirrors `tesseract_available()`) PyTorch-Importierbarkeit,
    `torch.cuda.is_available()` und
    `torch.cuda.get_device_properties(0).total_memory` gegen einen
    Mindest-VRAM-Schwellwert (4 GB, dokumentierter, nicht hart validierter
    Wert). Jede Ausnahme bei der Geräte-Abfrage (Treiber-Mismatch, kein
    Gerät Index 0, ...) wird als "nicht verfügbar" behandelt statt die
    Prüfung selbst crashen zu lassen. Bewusst KEIN automatischer
    CPU-Fallback: eine reine CPU-LaMa-Inferenz wäre so viel langsamer,
    dass sie den Zweck eines GPU-Backends unterlaufen würde - eine nicht
    ausreichende GPU wird stattdessen als nicht verfügbar gemeldet, damit
    der Nutzer manuell auf Cloud-Inpainting wechseln kann.
  - `_build_inpainting_mask()`: baut die für LaMa erwartete
    Binärmaske (255 = zu entfernender/rekonstruierender Bereich) aus den
    OCR-Bounding-Boxes, mit `padding`-Pixeln Rand (Standard 4) um jede
    Region, geclampt an die Bildgrenzen - der Rand deckt anti-aliasierte
    Buchstabenkanten ab, die die OCR-Box knapp verfehlt hat.
  - `_get_lama_model()`/`_LAMA_MODEL_CACHE`: das geladene Modell wird
    modul-weit gecached (nicht pro `GpuInpaintingBackend()`-Instanz, da
    `build_inpainting_backend()` für jeden `run_image_job()`-Aufruf eine
    neue Instanz baut) - ein Mehrdatei-Batch lädt/downloaded die
    mehrere-hundert-MB-Gewichte dadurch nur einmal pro Prozess, nicht pro
    Datei. `simple-lama-inpainting` selbst unterstützt eine
    `LAMA_MODEL`-Umgebungsvariable für lokal vorab bereitgestellte
    Gewichte - relevant für eine spätere Standalone-Version ohne
    Internetzugriff zur Laufzeit (siehe requirements-gpu.txt).
  - `apply()`: Fail-fast-Guard ganz am Anfang (wirft `InpaintingError`,
    bevor überhaupt `torch`/`simple_lama_inpainting` importiert wird,
    falls `gpu_inpainting_available()` False meldet) als zweite
    Verteidigungslinie zusätzlich zum UI-seitigen Check. Text wird nach
    dem Inpainting exakt wie bei `CvInpaintingBackend` zurückgeschrieben
    (Kontrastfarbe aus dem bereits REKONSTRUIERTEN Bereich selbst
    gesampelt, siehe `_average_region_color()`).
  - `ui/document_job_common.py`: neue `inpainting_backend_available()`
    (analog zu `ocr_engine_available()` - Box-Overlay/
    CvInpaintingBackend immer verfügbar, `"gpu_inpainting"` delegiert an
    `gpu_inpainting_available()`), `"gpu_inpainting"` in
    `INPAINTING_BACKEND_FACTORIES` registriert.
  - `ui/app.py`: drittes Element im Rückschreibe-Dropdown (automatisch
    aus `INPAINTING_BACKEND_FACTORIES` befüllt, kein Code-Änderungsbedarf
    dafür), neuer `inpainting_backend_hint`-Hinweistext
    (`_update_inpainting_backend_hint()`, spiegelt
    `_update_ocr_engine_hint()`s Muster 1:1), Fail-fast-Warnung in
    `_start()` analog zur bestehenden OCR-Engine-Prüfung. Neue
    i18n-Schlüssel `inpainting_backend.gpu_inpainting`/
    `inpainting_backend.unavailable` (DE+EN, Parität durch bestehenden
    Test abgesichert).

  **Testabdeckung ohne echte GPU/PyTorch-Installation:** Diese
  Cloud-Sandbox hat keine CUDA-GPU (siehe RoadMap.md Phase 3) - PyTorch
  wurde deshalb bewusst NICHT installiert (spart eine ~500+ MB Installation,
  die ohnehin nur den bereits feststehenden "nicht verfügbar"-Pfad testen
  würde). Stattdessen wird für die Verfügbarkeitsprüfung ein minimales
  Fake-`torch`-Modul über `monkeypatch.setitem(sys.modules, "torch",
  ...)` injiziert (Standardtechnik für Import-Mocking ohne die reale
  Abhängigkeit) - deckt alle fünf Verzweigungen von
  `gpu_inpainting_available()` ab (PyTorch fehlt komplett - über
  `sys.modules["torch"] = None`, was `import torch` wie bei einem
  fehlenden Paket ImportError werfen lässt -, CUDA nicht verfügbar, zu
  wenig VRAM, Geräte-Abfrage wirft eine Exception, ausreichend VRAM).
  `_build_inpainting_mask()` ist reine PIL-Logik und komplett ohne
  PyTorch getestet (Padding, Clamping an Bildgrenzen, leere
  Ersetzungsliste). `GpuInpaintingBackend.apply()`s Fail-fast-Guard ist
  ebenfalls ohne PyTorch testbar (er wirft, bevor er `torch` überhaupt zu
  importieren versucht). Ein echter Ende-zu-Ende-Testfall
  (`test_apply_end_to_end_on_a_real_gpu`) existiert im Code, wird aber
  automatisch übersprungen (`@pytest.mark.skipif(not
  gpu_inpainting_available(), ...)`) und dient als die eigentliche
  Regressionsabsicherung für einen künftigen Lauf auf der GPU-Maschine
  des Nutzers - Muster identisch zu jeder anderen "braucht echte
  Hardware/einen Live-Account"-Funktion in diesem Projekt.

  15 neue Tests über zwei Dateien (`tests/test_image_gpu_inpainting.py`:
  10, davon 9 laufend + 1 automatisch übersprungen; `tests/
  test_document_job_common.py`: 5 zusätzliche für
  `inpainting_backend_available()`/die erweiterte
  `build_inpainting_backend()`-Parametrisierung) plus 3 neue UI-Tests in
  `tests/test_ui_images_mode.py` (Dropdown bietet GPU-Inpainting an,
  Hinweistext nur bei nicht verfügbarem Backend sichtbar, Fail-fast-
  Warnung blockiert den Start). Kern-Mechanik (VRAM-Schwellwertvergleich
  in `gpu_inpainting_available()`) per Revert-Probe verifiziert: gezielt
  auf `return True` (Schwellwert-Vergleich komplett ignoriert)
  zurückgebaut, erwarteter Testfehler bestätigt (die
  Zu-wenig-VRAM-Testfall schlägt fehl), aus Backup wiederhergestellt,
  `diff` bestätigt byte-genaue Wiederherstellung, danach Gesamtsuite
  erneut grün. Gesamter Testlauf am Ende: 229 passed, 2 skipped (vorher
  212 passed, 1 skipped).

- **Bildübersetzung/OCR - GPU-Inpainting live verifiziert, zwei
  Installationsprobleme gefixt (18.08.2026):** Direkte Fortsetzung des
  GPU-Inpainting-Eintrags oben - Michael hat die neuen Abhängigkeiten
  installiert und die Suite auf seiner eigenen Maschine laufen lassen,
  wodurch `test_apply_end_to_end_on_a_real_gpu` zum ersten Mal wirklich
  ausgeführt (nicht übersprungen) wurde: PASSED, echter LaMa-
  Gewichte-Download plus echte GPU-Inferenz bestätigt. Der in RoadMap.md
  offen gelassene "muss auf echter Hardware verifiziert werden"-Punkt
  ist damit geschlossen.

  **Problem 1 - Paketkonflikt durch `simple-lama-inpainting`s eigene
  Abhängigkeitsangaben:** Ein naiver `pip install -r
  requirements-gpu.txt` in Michaels NICHT isolierter (kein venv)
  Python-Umgebung installierte zusätzlich zum bereits vorhandenen
  `opencv-python-headless` (aus `requirements-ocr.txt`) das GUI-Paket
  `opencv-python` (`simple-lama-inpainting`s eigene Abhängigkeitsangabe)
  - beide belegen dasselbe `cv2`-Modul, ein von den opencv-python-
  Maintainern selbst als problematisch dokumentiertes Setup. Gleichzeitig
  wurden numpy (auf `<2.0.0`) und Pillow (auf `<10.0.0`) heruntergestuft,
  was mit `opencv-python-headless`s eigener Anforderung (`numpy>=2`)
  sowie einem projektfremden, in derselben geteilten Umgebung installierten
  Paket (scikit-image, braucht `pillow>=10.1`) kollidierte. Der naheliegende
  Reparaturschritt `pip uninstall opencv-python` hat es noch schlimmer
  gemacht: opencv-python und opencv-python-headless teilen sich
  Installationspfade im `cv2`-Verzeichnis, daher hat das Uninstall die
  tatsächlichen `cv2`-Dateien von `opencv-python-headless` mitgerissen
  (nur noch dessen Paket-Metadaten blieben übrig) - `import cv2` schlug
  danach komplett fehl. Endgültig behoben über
  `pip install --force-reinstall --no-deps opencv-python-headless`
  (stellt die tatsächlichen Dateien sauber wieder her) plus
  `pip install "numpy>=2,<2.3.0"`.

  `requirements-gpu.txt` wurde daraufhin grundlegend überarbeitet: die
  empfohlene Installation ist jetzt explizit
  `pip install --no-deps simple-lama-inpainting` statt eines naiven
  `pip install -r requirements-gpu.txt` für dieses Paket - durch direkte
  Quellcode-Prüfung des GitHub-Repos verifiziert (nicht angenommen),
  dass `simple-lama-inpainting` nur torch, numpy, PIL und cv2 für reine
  Array-/Resize-Operationen importiert, keine GUI-Funktionen -
  `opencv-python-headless` deckt das vollständig ab, die von
  `simple-lama-inpainting` sonst mitinstallierten `fire`/`six`/
  `termcolor` gehören nur zu seinem (hier nie benutzten) CLI-Tool. Die
  Datei enthält jetzt außerdem einen expliziten
  Troubleshooting-Abschnitt für genau diesen Konfliktfall, inklusive der
  Force-Reinstall-Reparaturbefehle, für den Fall, dass jemand anders
  denselben Weg naiv geht.

  **Problem 2 - Pillow-Versionsinkompatibilität in drei Tests:**
  `tests/test_image_cv_inpainting.py`/`tests/test_image_inpainting.py`
  nutzten `Image.get_flattened_data()` für Pixel-für-Pixel-Vergleiche -
  eine Methode, die nur in sehr neuen Pillow-Versionen existiert (in der
  Cloud-Sandbox dieser Session vorhanden, auf Michaels durch Problem 1
  auf 9.5.0 heruntergestufter Installation nicht: `AttributeError:
  get_flattened_data`). Auf `.tobytes()` umgestellt - eine seit
  praktisch jeder Pillow-Version stabile Methode für denselben Zweck
  (Rohbyte-Vergleich statt Tupel-Liste, sogar effizienter). Allgemeine
  Lehre für künftige Tests: keine sehr neuen/wenig verbreiteten
  API-Methoden in Test-Hilfsfunktionen verwenden, wenn eine ebenso
  geeignete, breiter kompatible Alternative existiert - ein Test, der
  nur in der Entwicklungsumgebung läuft, aber beim ersten Einsatz in
  einer anderen (älteren) Umgebung bricht, verfehlt seinen Zweck als
  Regressionsschutz.

  Kein Produktionscode betroffen - beide Probleme lagen ausschließlich
  in der Installationsanleitung (`requirements-gpu.txt`) bzw. in
  Testcode. Testlauf auf Michaels Maschine am Ende: 230 passed, 1
  skipped (verbleibender Skip: DeepL-Live-Kontingent-Test ohne
  konfigurierten Schlüssel, nicht GPU-bezogen) - gegenüber der
  Sandbox-Baseline von 229 passed, 2 skipped bedeutet das genau EINEN
  zusätzlichen echten Testdurchlauf: `test_apply_end_to_end_on_a_real_gpu`.

- **Bildübersetzung/OCR - manueller Korrektur-Dialog implementiert
  (18.08.2026):** Auf Michaels expliziten Wunsch ("Sollten wir nicht
  zuerst den Korrektur Dialog einbauen? Den brauchen wir ja überall.")
  VOR Cloud-Inpainting und der Einbettung von Bildübersetzung in PDF/
  Word/PPTX gebaut - das Korrektur-Muster wird in all diesen Fällen
  gebraucht und sollte einmal ordentlich stehen statt mehrfach neu
  erfunden zu werden. Direkt nach `ui/correction_dialog.py::PdfCorrectionDialog`
  entworfen, mit denselben drei Schichten (Datenmodell → Job-Funktion →
  Qt-Dialog → App-Anbindung), aber überall dort vereinfacht, wo Bild-
  Rückschreibung tatsächlich weniger kann/braucht als PDF-Text-Einfügung.

  **Datenschicht (`pipeline/images/translate_image.py`):**
  `ImageTranslationStats` bekam ein neues Feld `replacements:
  list[TextReplacement]` - genau die Liste, die am Ende an
  `InpaintingBackend.apply()` übergeben wird, gefüllt im selben Zug wie
  `translated`/`failed` (nur ERFOLGREICH übersetzte Regionen landen
  darin, exakt wie `PdfTranslationStats.blocks`' Vertrag - ein neuer Test
  `test_translate_image_replacements_only_include_successful_regions`
  bestätigt das explizit anhand eines simulierten Anbieterfehlers für
  eine von zwei Regionen). Dazu `build_corrected_replacements(replacements,
  edited_texts: dict[int, str])` als Bild-Gegenstück zu
  `build_corrected_records_from_html()` - da `TextReplacement.translated_text`
  ein reiner `str` ist (kein Rich-Text-HTML wie bei PDF), ist der
  Schlüssel schlicht der Listenindex (Zeilenposition in der
  Korrekturtabelle) statt eines (Seite, Block)-Tupels, weil eine
  Bilddatei kein Seitenkonzept hat. Nur Zeilen, deren Text sich
  tatsächlich geändert hat, bekommen ein neues `TextReplacement`-Objekt;
  alle anderen werden 1:1 (Objektidentität) durchgereicht.

  **Job-Schicht (`ui/image_job.py`):** `ImageJobResult` bekam ein neues
  Pflichtfeld `source_path` (vorher fehlte diese Information komplett) -
  nötig, weil ein Batch-Lauf mehrere Dateien übersetzt und der
  Korrektur-Dialog pro Datei die passende PRISTINE Quelle braucht, nicht
  die schon übersetzte (siehe `run_image_correction_job()`s Docstring für
  die Begründung, warum eine bereits übersetzte Datei als "Quelle" für
  eine zweite Rückschreibe-Runde stehenbleibende Reste der ersten
  Übersetzung hinterlassen könnte). `run_image_correction_job(source,
  destination, replacements, inpainting_backend_name="box_overlay")`
  spiegelt `run_pdf_correction_job()`s Vertrag: kein OCR-/Provider-/
  Netzwerk-Aufruf, `destination` darf/soll bereits existieren (wird
  überschrieben statt eines `DestinationConflictError`s), nur der
  Quelle-gleich-Ziel-Schutz bleibt bestehen. Baut intern ein neues
  `ImageTranslationStats`-Objekt (da `InpaintingBackend.apply()` selbst
  `None` zurückgibt) und schreibt einen eigenen, kürzeren
  "nach manueller Korrektur"-QA-Bericht, exakt wie
  `run_pdf_correction_job()`s `_build_correction_qa_report()`.

  **Dialog (`ui/image_correction_dialog.py`, neue Datei):**
  `ImageCorrectionDialog` - bewusst EINFACHER als `PdfCorrectionDialog`:
  ein reiner `QPlainTextEdit` statt eines Rich-Text-`QTextEdit` mit Fett/
  Kursiv/Unterstrichen-Toolbar und Strg+B/I/U-Tastenkürzeln, weil
  rasterisiert eingefügter Bildtext (`PIL.ImageDraw.text()`) keine
  Formatierung kennt, die es zu erhalten gäbe; die Übersichtstabelle hat
  nur zwei statt drei Spalten (Original/Übersetzung, keine Seiten-
  Spalte). Ansonsten identisches Verhalten: Zeilenauswahl lädt die
  Übersetzung in den Editor, Dirty-Tracking pro Zeile
  (`_flush_active_row()` überschreibt `_row_text[row]` nur, wenn die
  Zeile tatsächlich in `_dirty` steht - ein nur angesehener, nie
  bearbeiteter Wechsel zwischen Zeilen lässt das Original-Objekt
  unangetastet), "Anwenden und speichern" ruft
  `build_corrected_replacements()` und dann `run_image_correction_job()`
  direkt auf dem UI-Thread auf (kein Hintergrund-Worker nötig, da kein
  Netzwerkaufruf involviert ist).

  **App-Anbindung (`ui/app.py`):** `correct_translation_button` wird
  jetzt für zwei Fälle sichtbar: ein `PdfJobResult` mit Blöcken (wie
  vorher) ODER ein `ImageBatchJobResult`, bei dem mindestens EINE Datei
  im Batch `stats.replacements` hat. `_open_correction_dialog()` wurde in
  einen gemeinsamen Dispatcher plus `_open_pdf_correction_dialog()`/
  `_open_image_correction_dialog()` aufgeteilt. Hat der Batch mehr als
  eine korrigierbare Datei, fragt `_open_image_correction_dialog()` per
  `QInputDialog.getItem()` (Auswahlliste nach Ausgabedateiname, eindeutig
  dank `safe_destination()`s Kollisionsvermeidung) welche Datei gemeint
  ist, bevor der Dialog geöffnet wird. Nach erfolgreicher Korrektur wird
  das passende `ImageJobResult` per Objektidentität (nicht `list.index()`s
  Wertevergleich, um eine Verwechslung bei zufällig feldgleichen
  Einträgen auszuschließen) im Batch-Ergebnis ersetzt und die Job-Anzeige
  aktualisiert - spiegelt `_open_pdf_correction_dialog()`s "Reopening muss
  von DIESER Korrekturrunde starten, nicht die alte Maschinenübersetzung
  wiederherstellen"-Verhalten.

  Neue i18n-Schlüssel `image_correction.*` (DE/EN, Parität über
  `tests/test_ui_i18n.py` geprüft, wiederverwendet `job.correct_translation`
  für den Button selbst, da der Text formatneutral genug ist).

  Neue/erweiterte Tests: `tests/test_translate_image.py` (drei neue
  Tests für `build_corrected_replacements()` plus der oben genannte
  `replacements`-Vertragstest), `tests/test_image_correction_job.py`
  (neue Datei, spiegelt `tests/test_pdf_correction_job.py`),
  `tests/test_ui_image_correction.py` (neue Datei, spiegelt
  `tests/test_ui_pdf_correction.py`: Button-Sichtbarkeit für beide
  Zustände, End-to-End-Korrektur inklusive echtem Tesseract-Rückcheck auf
  der Ausgabedatei, Datei-Picker-Pfad bei mehreren Kandidaten,
  Dirty-Guard-Verhalten beim Zeilenwechsel ohne Bearbeitung). Kern-
  Mechanik (`ImageCorrectionDialog._flush_active_row()`s Dirty-Guard) per
  Revert-Probe verifiziert: gezielt auf ein bedingungsloses
  `_row_text[row] = ...` zurückgebaut (Dirty-Check entfernt), erwarteter
  Testfehler bestätigt (`test_switching_rows_without_editing_keeps_original_text`
  schlägt fehl, weil ein unbearbeiteter Wert nun durch ein neues
  gleichlautendes String-Objekt statt des Originals ersetzt wird), aus
  Backup wiederhergestellt, `diff` bestätigt byte-genaue
  Wiederherstellung, danach Gesamtsuite erneut grün. Gesamter Testlauf am
  Ende: 242 passed, 2 skipped (vorher 229 passed, 2 skipped in dieser
  Sandbox - genau die 13 neu hinzugekommenen Tests aus diesem Eintrag).

- **Bildübersetzung/OCR - Textüberlauf und OCR-Fehllesungen behoben
  (18.08.2026):** Michael meldete anhand zweier eigener Testbilder ("4.
  August Stellar Russia.jpg" - ein Chat-App-Screenshot mit zwei
  Sprechblasen-Spalten, und "Zoom Live Transcription.jpg" - eine
  6-Kachel-Infografik-Anleitung), beide im Projekt-Root abgelegt und
  über die App in `tests/output/` übersetzt: "Es gibt schon noch durch
  die Übersetzung Text Verunstaltungen. Auch wenn etwas umrahmt ist,
  stimmt es nicht ganz. Oder Boxen überlappen oder sind an falscher
  Stelle." Beide Ergebnisdateien plus ihre QA-Berichte wurden über die
  Geräte-Bridge geholt und visuell geprüft - QA-Berichte zeigten, dass
  das Problem bei GPU-Inpainting UND Box-Overlay gleichermaßen auftrat
  (ein starker Hinweis, dass die Ursache im gemeinsamen Zeichen-Code am
  Ende aller Backends liegen musste, nicht in einem einzelnen Backend).

  **Diagnose mit echten Tesseract-Läufen** (nicht geraten) auf beiden
  gemeldeten Bildern direkt in dieser Sandbox (Tesseract war hier
  installiert) legte zwei unabhängige Ursachen offen:

  1. **Kein Zeilenumbruch/keine Schriftverkleinerung beim
     Zurückschreiben.** Alle drei Backends (Box-Overlay, CV-Inpainting,
     GPU-Inpainting) endeten in derselben einen Zeile Code:
     `draw.text((region.x, region.y), translated_text, ...)` - IMMER
     eine einzige, nicht umgebrochene Zeile, komplett unabhängig von
     `region.width`. Auf dem Chat-Screenshot füllten die meisten
     erkannten englischen Zeilen bereits fast die volle Spaltenbreite
     aus (z. B. Breite 527px bei ~600px Spaltenbreite) - da Deutsch
     typischerweise 20-40 % länger ist, lief praktisch JEDE übersetzte
     Zeile über ihre Box hinaus in benachbarten Text hinein, exakt was
     Michael als "Boxen überlappen" beschrieb. Auf dem Zoom-Bild kam ein
     zweiter Effekt hinzu: eine einzelne OCR-Zeile ("click the "CC"
     button.") bekam durch ein danebenliegendes Pfeil-Icon eine
     fehlerhaft überhöhte Bounding-Box (Höhe 46px statt der um sie herum
     üblichen 16px) - da die Schriftgröße bis dahin ungedeckelt direkt
     aus `region.height * 0.8` berechnet wurde, führte das zu
     übergroßer, seitenfüllender Schrift.

     Behoben durch eine neue, von allen drei Backends geteilte
     Rendering-Funktion in `pipeline/images/inpainting.py`:
     `_wrap_text_to_width()` (Greedy-Wortumbruch, gemessen über
     `draw.textlength()` - bewusst diese seit Pillow 8.0 stabile API
     statt einer neueren, siehe die `get_flattened_data()`-Lehre aus dem
     GPU-Inpainting-Eintrag oben) plus `_fit_text()` (probiert
     absteigende Schriftgrößen, bis der umgebrochene Textblock innerhalb
     von `region.height` passt oder eine lesbare Mindestgröße
     `_MIN_FONT_SIZE = 9` erreicht ist) plus `_draw_fitted_text()`
     (zeichnet die umgebrochenen Zeilen). Bewusst eine SCHRUMPF-, keine
     WACHS-Strategie: die Box wird nie höher als `region.height`
     gemacht, auch wenn der umgebrochene Text mehr Platz bräuchte - an
     beiden gemeldeten Bildern sitzen Zeilen eng gestaffelt (in der
     Zoom-Anleitung z. B. nur ~29-33px Zeilenabstand), ein Wachstum der
     Box hätte also mit hoher Wahrscheinlichkeit in die nächste,
     unbeteiligte Zeile hineingezeichnet - ein neues, potenziell
     schlimmeres Problem statt einer Lösung. Zusätzlich eine feste
     Obergrenze `_MAX_FONT_SIZE = 48` für die START-Schriftgröße,
     unabhängig von `region.height` - fängt genau den oben beschriebenen
     Icon-Bounding-Box-Fehler ab, ohne echte große Überschriften
     (bestätigt bis zu Originalgröße ~34px in den Testbildern) zu
     beschneiden.

  2. **OCR-Fehllesungen von UI-Icons/Grafiken als Text.** Ein direkter
     Dump aller von Tesseract erkannten Regionen (Text, Position,
     Konfidenz) auf dem Zoom-Bild zeigte mehrere klare Fehllesungen,
     jeweils mit auffällig niedriger Konfidenz verglichen mit echtem
     Text im selben Bild:
     ```
     y=209 w=19  h=9  conf=48.0 text='03'
     y=210 w=72  h=18 conf=22.0 text='&' Oo'
     y=219 w=145 h=33 conf=40.2 text='Stop Video Papats Cut'
     y=430 w=383 h=14 conf=23.7 text='-ONEICIIRE VOLE "TTINC?'  (Geister-
       Duplikat direkt über der ECHTEN, korrekt erkannten Überschrift
       'CONFIGURE YOUR SETTINGS' bei conf=96.0 - vermutlich ein Anti-
       Aliasing-Halo um die fette Schrift, den Tesseract fälschlich als
       eigene zweite Textzeile erkannte)
     ```
     verglichen mit echten Textzeilen im selben Bild bei conf=80-96.
     Dasselbe Muster auf dem Chat-Bild (z. B. `.¢ 2762)` bei conf=29.0,
     ein reines `&` bei conf=28.0 - beides UI-Chrome/Icons, keine echten
     Wörter). Diese Fehllesungen wurden bisher wie jede andere Zeile
     übersetzt und über das Bild gezeichnet - Kauderwelsch rein,
     Kauderwelsch raus, exakt Michaels "Text Verunstaltungen".

     Behoben über einen neuen Mindest-Konfidenz-Filter:
     `DEFAULT_MIN_OCR_CONFIDENCE = 40.0` (neue Konstante in
     `pipeline/images/translate_image.py`), `translate_image(...,
     min_confidence=...)` - eine Region unterhalb der Schwelle wird gar
     nicht erst an den Übersetzungs-Provider geschickt (spart auch
     unnötige API-Kosten für reinen Icon-Kauderwelsch) und bleibt im
     Ergebnisbild komplett unverändert. Neues Feld
     `ImageTranslationStats.skipped` (analog zu
     `PdfTranslationStats.skipped` - strukturell ausgeschlossen, kein
     Fehler), im QA-Bericht als eigene Zeile sichtbar
     ("Regionen übersprungen (niedrige OCR-Konfidenz): N"). 40.0 ist
     AUSDRÜCKLICH als konservativer, nur an diesen zwei realen Bildern
     kalibrierter Schwellwert dokumentiert, nicht als validierter
     Universalwert - fängt die eindeutigsten Fälle (20er-30er Konfidenz)
     zuverlässig ab, lässt aber mittelmäßig-konfidente Fehllesungen
     durch (z. B. 'a & 0' bei conf=65.7, 'Stop Video Partc' bei
     conf=72.7 - beides ebenfalls Icon-Fehllesungen, aber zu hoch für
     die aktuelle Schwelle). Dieser Rest ist ein bekanntes, bewusst
     nicht in diesem Fix adressiertes Problem (siehe "Offene Punkte"
     unten).

  **Verifikation an den ECHTEN gemeldeten Bildern, nicht nur an
  synthetischen Tests:** die tatsächliche `translate_image()`-Pipeline
  wurde direkt (mit echtem Tesseract, einem Fake-Provider, der
  realistisch-längere deutsche Texte simuliert) gegen beide Originalbilder
  laufen lassen und das Ergebnis visuell geprüft - kein Textüberlauf mehr,
  keine überlappenden Boxen mehr, die vom Nutzer selbst ins Bild gezeichneten
  pinken Hervorhebungsrahmen im Chat-Bild umschließen den übersetzten Text
  jetzt wieder korrekt (vorher liefen sie durch den Überlauf ins Leere).

  Kern-Mechanik je per Revert-Probe verifiziert: die Schrumpf-Abbruchbedingung
  in `_fit_text()` gezielt auf "immer beim ersten Versuch zurückgeben"
  zurückgebaut, erwarteter Testfehler bestätigt
  (`test_fit_text_shrinks_font_when_wrapped_block_exceeds_region_height`
  schlägt fehl), wiederhergestellt, `diff` bestätigt byte-genau. Ebenso die
  Konfidenz-Prüfung in `translate_image()` gezielt deaktiviert (`if False
  and region.confidence < min_confidence`), erwarteter Testfehler bestätigt
  (`test_translate_image_skips_region_below_min_confidence` schlägt fehl),
  wiederhergestellt, `diff` bestätigt byte-genau. Neue Tests in
  `tests/test_image_inpainting.py` (`_wrap_text_to_width()`/`_fit_text()`
  Unit-Tests plus ein Pixel-Sonden-Test, der bestätigt, dass nach dem Fix
  keine Textpixel mehr rechts der ursprünglichen Box auftauchen) und
  `tests/test_translate_image.py` (Konfidenz-Skip-Tests mit einem
  deterministischen Stub-OCR-Engine statt echtem Tesseract, damit die
  erwarteten Konfidenzwerte nicht von Tesseracts tatsächlicher Erkennung
  abhängen). Gesamter Testlauf am Ende: 251 passed, 2 skipped (9 neue
  Tests).

  **Offene Punkte, bewusst NICHT in diesem Fix gelöst** (für RoadMap.md/
  künftige Iterationen):
  - Mittelmäßig-konfidente OCR-Fehllesungen von Icons/Grafiken (65-75er
    Konfidenz) rutschen weiterhin durch den Filter und werden als
    (unsinnige) Übersetzung gezeichnet - allerdings jetzt wenigstens
    innerhalb ihrer Box umgebrochen statt überlappend, also weniger
    störend als vorher.
  - Cross-Spalten-Vermischung bei komplexen Mehrspalten-/Infografik-
    Layouts (Tesserects automatische Seitensegmentierung, PSM 3, ist für
    ein einzelnes, fließendes Dokument optimiert, nicht für ein 6-Kachel-
    Raster wie im Zoom-Testbild) ist NICHT behoben - das Geister-Duplikat
    über "CONFIGURE YOUR SETTINGS" wurde nur durch die Konfidenz-Schwelle
    zufällig mit abgefangen, nicht durch eine gezielte Lösung für dieses
    Muster. Eine echte Lösung bräuchte vermutlich Experimente mit
    Tesseracts `--psm`-Parameter (z. B. PSM 11 "sparse text" statt des
    Standards PSM 3) oder ein Cloud-OCR-Backend mit besserem
    Layout-Verständnis - beides noch nicht umgesetzt/getestet.
  - Der 40.0-Schwellwert ist nur an zwei Bildern kalibriert, nicht
    breit validiert; nicht als UI-Einstellung exponiert (nur als
    Funktionsparameter) - falls sich in weiteren Nutzertests zeigt, dass
    er zu aggressiv oder zu lasch ist, sollte er anpassbar gemacht
    werden.
