# Projekt-Roadmap

Stand: 17. August 2026

Diese Roadmap bündelt die offenen Arbeiten für PDF-, Word-, Präsentations- und
Bildübersetzung sowie UI, Provider, Kostenkontrolle, Qualitätssicherung und
Auslieferung. `Backlog.md` bleibt das technische Detailarchiv für bereits
untersuchte Einzelfälle und ältere PDF-/Word-Befunde.

## Leitprinzipien

- Quelldateien werden niemals überschrieben.
- Format-, Positions- und Strukturtreue haben Vorrang vor automatischer
  Layoutoptimierung.
- Übersetzung und Dokumentmanipulation bleiben getrennt, damit Fehler eindeutig
  zugeordnet werden können.
- Footer, Header, Foliennummern, Datumsfelder und definierte Schutzbereiche
  werden nicht übersetzt.
- Vor jedem kostenpflichtigen Lauf erfolgen Analyse, Kostenschätzung und
  ausdrückliche Bestätigung.
- Nicht unterstützte Inhalte werden sichtbar katalogisiert und unverändert
  erhalten.

## Bereits vorhandene Grundlage

- Provider: DeepL, Google, OpenAI und Grok
- Zugangsdaten aus Umgebungsvariablen sowie optional aus dem OS-Keyring
- Geschützte Begriffe und providerunabhängige HTML-Übersetzung
- Zeichenbasierte Kostenschätzung, Monatsverbrauch und hartes Lauflimit
- DOCX-Lese-/Schreib- und Übersetzungspfad mit Header-/Footer-Schutz
- PDF-Extraktion, Text-Rekonstruktion und erste Layoutschutzmechanismen
- PPTX-OOXML-Engine mit verlustarmem Roundtrip und minimalem `<a:t>`-Writeback
- PPTX-Erfassung von Textfeldern, Platzhaltern, Tabellen und Gruppen
- PPTX-Überlauferkennung ohne automatische Layoutänderung
- UI-Grundgerüst mit expliziter Moduswahl und Dokumentanalyse
- deutsche und englische UI; weitere Sprachkataloge sind registriert

## Phase 1 – Produktiver PPTX-Ablauf im UI

- [ ] DeepL-PPTX-Übersetzung an den Startknopf anbinden.
- [ ] Ausgabeordner und sicheren Zieldateinamen wählen lassen.
- [ ] Identität von Quelle und Ziel technisch ausschließen.
- [ ] Kostenbestätigung unmittelbar vor dem ersten API-Aufruf verlangen.
- [ ] Fortschritt nach Folie/Absatz und bisher verbrauchte Zeichen anzeigen.
- [ ] Abbruch zwischen API-Aufrufen ermöglichen und Teilergebnisse eindeutig
      behandeln.
- [ ] Provider- und Netzwerkfehler verständlich anzeigen und technisch loggen,
      ohne Zugangsdaten zu protokollieren.
- [ ] Nach Abschluss Ergebnisdatei, Kurzstatistik, Überlaufmeldungen und
      QA-Bericht anbieten.
- [ ] Den realen 19-Folien-Testdatensatz als UI-End-to-End-Test verwenden.
- [ ] Manuelle Prüfpunkte wie den bekannten Sonderfall auf Folie 11 im
      QA-Bericht aufführen, aber nicht automatisch umformatieren.

**Abnahmekriterium:** Eine PPTX kann mit DeepL vollständig über das UI in eine
neue Datei übersetzt werden; Strukturprüfung, Überlaufvergleich und manueller
Sichttest zeigen keine neu erzeugten OOXML- oder Positionsschäden.

## Phase 2 – Gemeinsamer Auftragsablauf für Word und PDF

### Word/Writer

- [ ] Bestehende DOCX-Pipeline an denselben UI-Auftragsablauf anbinden.
- [ ] Ausgabe-, Fortschritts-, Abbruch-, Kosten- und Fehlerbehandlung mit PPTX
      vereinheitlichen.
- [ ] Seitenzahl-/PAGE-Feld an einem tatsächlich länger werdenden Dokument
      prüfen und bei Bedarf Feldaktualisierung erzwingen.
- [ ] DeepL-Verschiebungen an `<br/>`-Grenzen als QA-Risiko besser erfassen,
      ohne unsichere automatische Textkorrektur.
- [ ] Verschachtelte Footer-Content-Controls (`<w:sdt>`) für Inventar und
      PAGE-Feld-Prüfung lesbar machen; Footer bleiben unübersetzt.
- [ ] Bekannten seltenen Hyperlink-Tag-Verlust reproduzierbar testen und eine
      sichere Wiederholungs-/Fallbackstrategie definieren.
- [ ] Optionalen Export des übersetzten DOCX nach PDF untersuchen und getrennt
      vom verlustarmen DOCX-Writeback behandeln.

### PDF

- [ ] Entscheiden und dokumentieren, wann der direkte PDF-Pfad produktiv
      eingesetzt wird und wann ein vorhandenes Word-Original Vorrang hat.
- [ ] Direkte PDF-Pipeline an den gemeinsamen UI-Auftragsablauf anbinden.
- [ ] Offenen Duplikat-Text-Bug im Redact/Insert-Pfad reproduzieren und beheben.
- [ ] Erhalt von Link-Annotationen nach Redaction technisch prüfen.
- [ ] Durchsuchbarkeit und Copy/Paste-Qualität erzeugter PDFs verifizieren.
- [ ] Führende Leerzeilen, Underline-Erhalt und Inline-Formatierung an mehreren
      realen Dokumenten und Providern regressionsprüfen.
- [ ] Fehlende Glyphen aus Symbol-/Private-Use-Fonts behandeln.
- [ ] Ungewollte `fi`-Ligatur bei Textsuche und Copy/Paste untersuchen.
- [ ] Einbettung beziehungsweise Wiederverwendung von Originalfonts bewerten.
- [ ] Hintergrundbilder und überlagerte Textblöcke gegen unbeabsichtigte
      Redaction absichern.

**Abnahmekriterium:** DOCX und freigegebene PDF-Typen verwenden denselben
kontrollierten UI-Lauf und liefern neue, prüfbare Ausgabedateien ohne Änderungen
an geschützten Bereichen.

## Phase 3 – Bildübersetzung und OCR

- [ ] Gemeinsames Bildmodell für PDF, DOCX, PPTX und einzelne Bilddateien
      definieren.
- [ ] OCR-Engine auswählen, kapseln und Sprachpakete verwalten.
- [ ] Scan-/Bild-PDFs über einen verpflichtenden OCR-Dokumentpfad verarbeiten.
- [ ] Optionalen Pfad für eingebettete Bilder klar vom Dokumenttext trennen.
- [ ] Auswahl „keine“, „einzelne“ oder „alle Bilder“ um Vorschauen und
      Mehrfachauswahl ergänzen.
- [ ] Eigenständige Übersetzung einer oder mehrerer Bilddateien implementieren.
- [ ] Textregionen, Leserichtung, Schrift, Farbe und Hintergrund erfassen.
- [ ] Übersetzten Text mit Inpainting/Maskierung sicher zurückschreiben.
- [ ] Logos, dekorative Bilder und Hintergründe standardmäßig ausschließen.
- [ ] Identische, mehrfach eingebettete Bilder deduplizieren, um API- und
      OCR-Kosten nicht mehrfach zu berechnen.
- [ ] OCR-, Übersetzungs- und Bildmodellkosten getrennt schätzen und erfassen.
- [ ] Originalbild, OCR-Text und Ergebnis in einer manuellen Prüfansicht zeigen.

**Abnahmekriterium:** Einzelbilder und ausgewählte eingebettete Bilder können
kontrolliert übersetzt werden; Scan-PDFs werden eindeutig als OCR-Auftrag
behandelt und Kosten sind vor dem Start nachvollziehbar.

## Phase 4 – PPTX-Erweiterungen

- [ ] SmartArt-Text untersuchen und ausdrücklich unterstützen oder dauerhaft
      als unverändert/nicht unterstützt kennzeichnen.
- [ ] Diagramm- und Chart-Texte katalogisieren und getrennt freigeben.
- [ ] Sprecher- und Foliennotizen katalogisieren; Standard bleibt unübersetzt.
- [ ] Text auf Mastern und Layouts nur mit expliziter Schutzstrategie prüfen.
- [ ] Eingebettete OLE-Objekte weiterhin unverändert erhalten und melden.
- [ ] WordArt-spezifische Effekte bei Bedarf normalisiert dokumentieren.
- [ ] Folien- und Shape-Auswahl im UI ermöglichen.
- [ ] Keine automatische Schriftverkleinerung oder Shape-Vergrößerung ohne
      eigene, explizit freigegebene Layoutphase einführen.
- [ ] Optional eine konfliktfreie Verbreiterung von Textboxen zunächst nur als
      Vorschlag mit Vorher-/Nachher-Prüfung entwickeln.

## Phase 5 – UI vervollständigen

- [ ] Gemeinsames Auftragsmodell für PDF, PPTX, DOCX und Bilder fertigstellen.
- [ ] Startknopf abhängig von gültiger Analyse und Kostenbestätigung aktivieren.
- [ ] Warteschlange beziehungsweise Stapelverarbeitung mehrerer Aufträge.
- [ ] Laufstatus, Pause/Abbruch, Wiederholung und Teilfehler darstellen.
- [ ] Ergebnisverzeichnis, Berichte und problematische Stellen direkt öffnen.
- [ ] Geschützte Begriffe verwalten, importieren, exportieren und je Auftrag
      ergänzen.
- [ ] Anbieter- und Modellfähigkeiten abhängig vom Dokumentmodus anzeigen.
- [ ] API-Schlüssel anlegen, prüfen, ersetzen und entfernen.
- [ ] Zwischen Sitzungsvariable, dauerhafter Benutzer-Umgebungsvariable und
      OS-Keyring unterscheiden.
- [ ] Fehlenden oder nicht konfigurierten Keyring verständlich behandeln.
- [ ] Einstellungen sichern, zurücksetzen und als nicht geheime Konfiguration
      exportieren.
- [ ] Tastaturbedienung, Fokusreihenfolge, Skalierung und Barrierefreiheit.
- [ ] Temporäre Dateien und abgebrochene Läufe kontrolliert bereinigen.

## Phase 6 – Mehrsprachigkeit

- [x] Alle neuen Hauptfenster- und Einstellungsdialogtexte über Schlüssel führen.
- [x] Deutsch und Englisch zur Laufzeit umschaltbar bereitstellen.
- [x] Französisch, Spanisch, Italienisch, Niederländisch, Finnisch, Kroatisch
      und Russisch als vorbereitete Locales registrieren.
- [ ] Validierungs-, Backend- und providerabhängige Fehlermeldungen vollständig
      lokalisieren.
- [ ] Einheiten, Zahlen, Datum, Währung und Pluralformen locale-gerecht
      formatieren.
- [ ] Französische, spanische, italienische, niederländische, finnische,
      kroatische und russische Kataloge übersetzen und freischalten.
- [ ] Fehlende und veraltete Übersetzungsschlüssel im CI prüfen.
- [ ] Entscheiden, ob der Python-Katalog dauerhaft verwendet oder später auf
      Qt-Linguist-Dateien (`.ts`/`.qm`) migriert wird.

## Phase 7 – Kosten, Provider und Zugangsdaten

- [ ] Kostenansicht in allen Modi nach Text, OCR und Bildern aufschlüsseln.
- [ ] Tatsächlichen Verbrauch während und nach dem Lauf anzeigen.
- [ ] Lauf-, Monats- und optionales Geldlimit während der Ausführung erzwingen.
- [ ] Providerpreise versionieren und Zeitpunkt/Quelle der Schätzung anzeigen.
- [ ] Tokenbasierte OpenAI-/Grok-Schätzungen von zeichenbasierten Tarifen
      sichtbar unterscheiden.
- [ ] DeepL-Free und DeepL-Pro korrekt unterscheiden.
- [ ] Providerverfügbarkeit und Zugangsdaten vor dem kostenpflichtigen Lauf
      mit einem sicheren Test prüfen.
- [ ] Retries, Backoff, Rate-Limits und idempotente Wiederaufnahme
      vereinheitlichen.
- [ ] Keine Schlüsselwerte in UI, Logs, Reports oder Fehlermeldungen ausgeben.

## Phase 8 – Qualitätssicherung und Tests

- [ ] Automatisierte UI-Tests für jeden Modus und beide aktiven UI-Sprachen.
- [ ] End-to-End-Tests mit Fake-Providern ohne Netz und getrennte manuelle
      Live-Provider-Tests einrichten.
- [ ] Repräsentative, lizenzrechtlich unproblematische DOCX-, PDF-, PPTX- und
      Bild-Fixtures pflegen.
- [ ] No-op-Roundtrip, strukturellen Fingerprint und visuelle Regression für
      alle Dokumentpfade vereinheitlichen.
- [ ] LibreOffice- und – soweit verfügbar – Microsoft-Office-Kompatibilität
      prüfen.
- [ ] QA-Berichtsschema für Übersetzungsfehler, Überlauf, Marker-/Tag-Verlust,
      fehlende Glyphen und nicht unterstützte Inhalte definieren.
- [ ] Bestehende Probleme des Originals klar von neu entstandenen Regressionen
      unterscheiden.
- [ ] Syntaxprüfung, Unit-Tests und Katalogprüfung in CI ausführen.
- [ ] Große Dokumente, viele Bilder, niedrigen Speicher und API-Abbrüche testen.

## Phase 9 – Datenschutz, Betrieb und Auslieferung

- [ ] Datenschutzhinweis erstellen: Welche Inhalte werden an welchen Provider
      übertragen?
- [ ] Lokale Logs minimieren, sensible Dokumenttexte vermeiden und
      Aufbewahrungsregeln definieren.
- [ ] Lizenz- und Datenschutzanforderungen für OCR-, Inpainting- und
      Übersetzungsdienste prüfen.
- [ ] Konfigurierbare Diagnoseprotokolle und Support-Bundle ohne Geheimnisse.
- [ ] Abhängigkeiten und unterstützte Python-/Betriebssystemversionen festlegen.
- [ ] Reproduzierbare PyInstaller-Pakete erstellen.
- [ ] Installer, Desktop-Starter, Versionsnummern und Updateverfahren definieren.
- [ ] Benutzerhandbuch und kurze modusspezifische Anleitungen erstellen.
- [ ] Optionales PyPI-Paket erst nach Stabilisierung der öffentlichen APIs
      bewerten.

## Empfohlene Reihenfolge der nächsten Arbeiten

1. Produktiven PPTX-DeepL-Lauf im UI vollständig anbinden.
2. Gemeinsames Job-, Fortschritts-, Abbruch- und QA-Modell stabilisieren.
3. DOCX-Pipeline über dasselbe Modell anbinden.
4. Direkten PDF-Pfad anhand der offenen Qualitätsbefunde freigeben oder klar
   begrenzen.
5. Bild-/OCR-Architektur und Kostenmodell implementieren.
6. Weitere PPTX-Inhaltstypen und weitere UI-Sprachen schrittweise freigeben.
7. Packaging, Datenschutzprüfung und Release-Härtung abschließen.

## Pflege dieser Roadmap

- Neue Aufgaben werden dem passenden Arbeitsbereich zugeordnet.
- Abgeschlossene Punkte werden abgehakt, nicht entfernt.
- Technische Einzelfallanalysen verbleiben in `Backlog.md` und werden hier nur
  zusammengefasst.
- Jede fertiggestellte Phase endet mit automatisierten Tests, mindestens einem
  realen Sichttest, aktualisierter Grenzendokumentation und einem Vorschlag für
  den nächsten Schritt.
