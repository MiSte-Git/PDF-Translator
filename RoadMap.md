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

- [x] DeepL-PPTX-Übersetzung an den Startknopf anbinden. (Tatsächlich alle
      vier bereits implementierten Provider, DeepL ist der für Phase 1
      verifizierte Standardpfad; siehe Backlog.md.)
- [x] Ausgabeordner und sicheren Zieldateinamen wählen lassen.
- [x] Identität von Quelle und Ziel technisch ausschließen.
- [x] Kostenbestätigung unmittelbar vor dem ersten API-Aufruf verlangen.
- [x] Fortschritt nach Folie/Absatz und bisher verbrauchte Zeichen anzeigen.
- [x] Abbruch zwischen API-Aufrufen ermöglichen und Teilergebnisse eindeutig
      behandeln.
- [x] Provider- und Netzwerkfehler verständlich anzeigen und technisch loggen,
      ohne Zugangsdaten zu protokollieren.
- [x] Nach Abschluss Ergebnisdatei, Kurzstatistik, Überlaufmeldungen und
      QA-Bericht anbieten.
- [x] Den realen 19-Folien-Testdatensatz als UI-End-to-End-Test verwenden.
      Vom Nutzer direkt im UI durchgeführt und als unauffällig bestätigt
      (17.08.2026) - nicht mit DeepL (Kontingent zu diesem Zeitpunkt
      ausgeschöpft, siehe Backlog.md), sondern mit Google als Provider,
      über exakt denselben Startknopf-/Job-Pfad, den auch DeepL nutzt
      (`ui/pptx_job.py::run_presentation_job()` ist providerunabhängig).
      Testskript für einen künftigen, gezielt gegen DeepL laufenden
      Wiederholungslauf bleibt bereit: tests/manual_e2e_pptx_ui_translation.py.
- [x] Manuelle Prüfpunkte wie den bekannten Sonderfall auf Folie 11 im
      QA-Bericht aufführen, aber nicht automatisch umformatieren - der
      QA-Bericht listet Überlaufrisiken generisch pro Folie auf (siehe
      Backlog.md). Die konkrete visuelle Prüfung von Folie 11 selbst wurde
      vom Nutzer nicht einzeln rückgemeldet (nur "dort war es ok" zum
      Gesamtlauf); als erledigt markiert auf Basis der allgemeinen
      Nutzerbestätigung des Live-Laufs, nicht als gesondert bestätigter
      Einzelfall.

**Abnahmekriterium:** Eine PPTX kann vollständig über das UI in eine neue
Datei übersetzt werden; Strukturprüfung, Überlaufvergleich und manueller
Sichttest zeigen keine neu erzeugten OOXML- oder Positionsschäden.
Strukturprüfung und Überlaufvergleich sind automatisiert abgesichert
(tests/test_pptx_job.py, Fake-Provider); der manuelle Sichttest mit einem
realen Dokument ist jetzt ebenfalls erfolgt (siehe oben, mit Google statt
dem ursprünglich vorgesehenen DeepL). Phase 1 damit nach Einschätzung des
Nutzers abgeschlossen (17.08.2026).

## Phase 2 – Gemeinsamer Auftragsablauf für Word und PDF

### Word/Writer

- [x] Bestehende DOCX-Pipeline an denselben UI-Auftragsablauf anbinden.
- [x] Ausgabe-, Fortschritts-, Abbruch-, Kosten- und Fehlerbehandlung mit PPTX
      vereinheitlichen. Details, Testabdeckung und die bewusst NICHT geteilte
      Überlauf-/QA-Logik (Word hat kein PPTX-Textbox-Overflow-Äquivalent):
      siehe Backlog.md. Noch ohne echten Live-Lauf gegen ein reales
      DOCX-Dokument über das UI (nur mit Fake-Provider automatisiert
      getestet) - analog zum ausstehenden Punkt weiter unten offen.
- [x] Expliziten "ICO-Dokument"-Schalter im UI ergänzen (17.08.2026): steuert
      manuell, ob der Seite-1-Metadatenbereich vor der Trennlinie von der
      Übersetzung ausgeschlossen wird - vorher lief diese Erkennung
      (`DocxEngine._has_separator_shape()`) für JEDES DOCX unbedingt mit,
      was ein Dokument, das zufällig eine ähnliche Trennform enthält, ohne
      Vorwarnung teilweise unübersetzt gelassen hätte. Jetzt ist der Scan
      opt-in über `ico_mode` (`DocxEngine.open()` → `translate_document()`
      unverändert, nur die Vorselektion der Absätze ändert sich); Checkbox
      ist nur im Word-Modus sichtbar/aktiv (kein PPTX-Äquivalent), wird beim
      Moduswechsel zurückgesetzt, und die Kostenanalyse (`ui/analysis.py`)
      verwendet denselben Schalter, damit Schätzung und tatsächlicher Lauf
      übereinstimmen. QA-Bericht warnt ausdrücklich, wenn ICO-Modus aktiv
      ist, aber keine Trennform gefunden wurde. PDF-Gegenstück (siehe
      PDF-Abschnitt unten) bewusst noch NICHT umgesetzt - PDF ist im UI
      insgesamt noch gesperrt. Details/Testabdeckung: siehe Backlog.md.
- [ ] Den DOCX-UI-Pfad an einem echten Dokument über einen echten Provider
      live durchlaufen lassen (analog zum jetzt erledigten PPTX-Live-Lauf
      oben) - bisher nur mit Fake-Provider gegen die neue Test-Fixture
      (tests/fixtures/representative.docx) automatisiert verifiziert.
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
- [x] Direkte PDF-Pipeline an den gemeinsamen UI-Auftragsablauf anbinden
      (17.08.2026) - siehe Backlog.md für Details. `ui/pdf_job.py` (neu,
      auf `pipeline/pdf/translate_pdf.py`, ebenfalls neu, aufgebaut) und
      `PdfTranslationWorker` (`ui/workers.py`) spiegeln `ui/word_job.py`/
      `WordTranslationWorker` exakt; PDF ist jetzt Teil von
      `ui/app.py::_EXECUTABLE_MODES` und teilt sich denselben Start-/
      Fortschritts-/Abbruch-/Kosten-/QA-Bericht-Ablauf wie PPTX und DOCX.
      Noch ohne echten Live-Lauf gegen ein reales PDF über das UI (nur mit
      Fake-Provider automatisiert getestet) - analog zu den entsprechenden
      offenen Punkten bei PPTX/Word.
- [ ] Nach Anbindung: dasselbe explizite "ICO-Dokument"-Konzept wie jetzt bei
      Word (siehe Word/Writer-Abschnitt oben) für PDF ergänzen - Grundlage
      dafür existiert bereits in der Pipeline (`FIRST_PAGE_ANCHOR_TERMS`/
      `_split_first_page_metadata()` in `pipeline/pdf/pymupdf_engine.py`,
      alternativ `DocumentTemplate.first_page_zones`/`templates/
      virelicon.json`), ist aber noch nicht ans UI angebunden und läuft
      bisher automatisch statt usergesteuert.
- [x] Duplikat-Text-Bug im Redact/Insert-Pfad reproduziert und Fix verifiziert
      (17.08.2026) - siehe Backlog.md für Details. Wichtiger Vorbehalt: der
      zugrundeliegende Mechanismus (unkontrolliertes Höhenwachstum eines
      Blocks in die Zeile des nächsten Blocks hinein) war bereits vorher
      durch den unconditional Kollisionsschutz behoben worden; neu ist eine
      permanente, dateiunabhängige Regressionsabdeckung
      (`tests/test_pdf_redact_insert_collision.py`), die diesen Mechanismus
      gezielt gegen synthetische PDFs reproduziert - nicht gegen die echte,
      vertrauliche "1526 VIRELICON.pdf", die in dieser Umgebung nicht
      verfügbar ist. Die beiden ANDEREN, in derselben ursprünglichen
      Diagnose (`tests/manual_diagnose_text_duplication.py`) genannten
      Symptome (unerklärte Suffixe an Zuschreibungszeilen; verlorene
      Bold/Underline-Formatierung + verschmolzene Überschrift/Bullet-Zeile +
      wachsende Lücken zwischen Bullet-Blöcken) sind NICHT Teil dieser
      Prüfung und bleiben offen/unverifiziert.
- [x] Erhalt von Link-Annotationen nach Redaction technisch geprüft und
      behoben (17.08.2026) - siehe Backlog.md für Details.
- [x] Durchsuchbarkeit und Copy/Paste-Qualität erzeugter PDFs verifiziert
      (17.08.2026) - grundsätzlich in Ordnung; die eine bestätigte Ausnahme
      ist die `fi`-Ligatur-Problematik direkt unten.
- [x] Führende Leerzeilen, Underline-Erhalt und Inline-Formatierung
      regressionsgeprüft (17.08.2026) - siehe Backlog.md für Details und
      den Vorbehalt zu "mehreren realen Dokumenten".
- [ ] Fehlende Glyphen aus Symbol-/Private-Use-Fonts behandeln. Verwandter,
      aber NICHT identischer Befund bereits behoben (17.08.2026, siehe
      Backlog.md): Verlust reiner Unicode-Zeichen (Kyrillisch/Griechisch/CJK)
      im Backward-Compatibility-Pfad ohne Spans. Symbol-/Private-Use-Font-
      Glyphen (z. B. Wingdings-artige Bullet-Zeichen) selbst wurden nicht
      getestet und bleiben offen.
- [x] Ungewollte `fi`-Ligatur bei Textsuche und Copy/Paste untersucht
      (17.08.2026) - bestätigt und als aktuell nicht sinnvoll behebbar
      dokumentiert, siehe Backlog.md.
- [ ] Einbettung beziehungsweise Wiederverwendung von Originalfonts bewerten.
      Bestätigt (17.08.2026, siehe Backlog.md): wird aktuell nicht gemacht,
      `TextBlock.font_name` wird nirgends zur Einfügung verwendet. Bleibt
      offene Architekturentscheidung.
- [x] Hintergrundbilder und überlagerte Textblöcke gegen unbeabsichtigte
      Redaction abgesichert (17.08.2026) - siehe Backlog.md für Details.
- [ ] Den PDF-UI-Pfad an einem echten Dokument über einen echten Provider
      live durchlaufen lassen (analog zu den jetzt erledigten PPTX-/
      geplanten Word-Live-Läufen oben) - bisher nur mit Fake-Provider gegen
      die neue Test-Fixture (`tests/fixtures/representative.pdf`)
      automatisiert verifiziert. Strukturteil an der echten, vertraulichen
      "1526 VIRELICON.pdf" jetzt zusätzlich erledigt (17.08.2026, siehe
      Backlog.md): voller `translate_pdf()`-Lauf über alle 14 Seiten mit
      Platzhalter- statt echtem Provider (keine API-Zugangsdaten in dieser
      Cloud-Sitzung hinterlegt), 0 Fehler, alle 11 echten Links erhalten,
      Formatierung/Highlights visuell unauffällig. Offen bleibt weiterhin
      der eigentliche Übersetzungsschritt mit einem echten Provider.
- [x] Echter Live-Lauf des PDF-UI-Pfads gegen "1526 VIRELICON.pdf" über
      einen echten Provider (Google) durchgeführt (17.08.2026) - der oben
      als offen markierte Punkt ist damit nachgeholt. Drei reale Bugs
      gefunden (vom Nutzer anhand von Screenshots gemeldet) und behoben,
      alle drei anhand der echten Ausgabedatei (nicht nur der
      Screenshots) root-caused und verifiziert:
      1. **Header wurde mitübersetzt.** Ursache: der direkte PDF-UI-Pfad
         (`ui/pdf_job.py::run_pdf_job()`) hat NIE ein `DocumentTemplate`
         geladen - weder das dokumentspezifische
         `templates/virelicon.json` noch irgendeine generische Erkennung
         - obwohl `PyMuPdfEngine` Header-/Footer-Ausschluss längst
         unterstützt (`DocumentTemplate.header_bbox`/`footer_bbox`). Nach
         Rücksprache mit dem Nutzer (Wahl: generische Checkbox statt nur
         die vorhandene dokumentspezifische Vorlage zu laden) neu gebaut:
         `pipeline/pdf/template.py::detect_header_footer_zones()` -
         findet wiederkehrende Kopf-/Fußzeilen generisch über Text- und
         Positions-Wiederholung across Seiten (kein dokumentspezifischer
         Code), getestet in `tests/test_pdf_header_footer_detection.py`
         (6 Tests). Durchgereicht als zwei neue, unabhängige PDF-Only-
         Checkboxen ("Header ausschließen"/"Footer ausschließen") durch
         den gesamten Stack: `ui/pdf_job.py` (`exclude_header`/
         `exclude_footer` Parameter, baut bei Bedarf ein
         `DocumentTemplate` aus der Erkennung, QA-Bericht nennt
         explizit, ob wirklich etwas erkannt/ausgeschlossen wurde) →
         `ui/workers.py::PdfTranslationWorker` → `ui/models.py::
         TranslationRequest` → `ui/app.py` (zwei neue `QCheckBox`,
         PDF-Only sichtbar, analog zu `ico_mode`s Word-Only-Muster) →
         `ui/i18n.py` (DE/EN). Neue UI-Regressionstests in
         `tests/test_ui_word_mode.py` (Sichtbarkeit, `_request()`,
         Worker-Dispatch - spiegeln die vorhandenen `ico_mode`-Tests).
      2. **Markierter (blau hinterlegter) Block am Seitenende: übersetzter
         Text schwebte ÜBER einer leeren Markierungs-Box statt darin.**
         Root Cause in `PyMuPdfEngine._next_block_y0()` gefunden: zwei
         VERSCHIEDENE, aber auf derselben visuellen Zeile sitzende
         PDF-Blöcke (ein langer markierter Absatz, endend auf derselben
         Zeile wie ein kurzer, separat formatierter Block "2 ways:")
         wurden fälschlich als "nächster Block darunter" behandelt, weil
         der Vergleich gegen die eigene Oberkante (`bbox[1]`) des
         wachsenden Blocks lief statt gegen dessen eigene Unterkante
         (`bbox[3]`). Das kappte `max_y1` UNTER die eigene ursprüngliche
         Blockhöhe, wodurch der übersetzte (längere) Text nie genug Platz
         bekam und die Markierungsfarbe nie neu gezeichnet wurde (siehe
         `_grow_highlight_if_needed()`). Fix: Vergleich auf `bbox[3]`
         umgestellt. Regressionsabdeckung in
         `tests/test_pdf_same_row_sibling_collision.py` (synthetisches
         PDF, spiegelt `tests/test_pdf_overlay_collision.py`s Aufbau) -
         beide Tests schlagen nachweislich fehl, wenn der alte Vergleich
         wiederhergestellt wird.
      3. **Erster Absatz auf Seite 2 gar nicht/nur teilweise übersetzt.**
         Root Cause in `PyMuPdfEngine.extract_blocks()` gefunden:
         `translatable` wurde für den GESAMTEN Block auf `False` gesetzt,
         sobald IRGENDEINE seiner Zeilen eine Link-Annotation überlappte
         (`block_overlaps(bbox, link_bbox)` auf der gesamten
         Block-Bbox) - in diesem Dokument saß mitten in einem 6-zeiligen
         Absatz eine einzelne, per Link zitierte Telegram-Post-Zeile, die
         damit den kompletten umgebenden Absatz von der Übersetzung
         ausschloss. Fix: neue `_split_by_link()`/`_line_overlaps_link()`
         (spiegeln `_split_by_highlight()`/`_line_is_highlighted()` exakt)
         zerlegen einen Block jetzt zusätzlich in Link-/Nicht-Link-
         Zeilenläufe, BEVOR `translatable` bestimmt wird - nur die
         tatsächlich linküberlappende Zeile wird non-translatable, der
         Rest des Absatzes bleibt übersetzbar. `_line_overlaps_link()`
         hat zusätzlich eine Tolerenz (`_LINK_OVERLAP_TOLERANCE`, Pendant
         zu `_HIGHLIGHT_LINE_TOLERANCE`): im echten Dokument saß eine
         völlig unbeteiligte Zeile nur 0,02pt unterhalb eines fremden
         Link-Rechtecks - ohne Toleranz hätte allein dieser
         Rundungsfehler die Zeile mit ausgeschlossen (durch gezielte
         Fixture-Konstruktion reproduziert und verifiziert). Bestätigt:
         der ursprüngliche, weiterhin gültige Anwendungsfall - ein Block,
         der komplett nur aus Link-Text besteht (z. B.
         `tests/fixtures/representative.pdf`) - bleibt vollständig
         non-translatable. Regressionsabdeckung in
         `tests/test_pdf_link_line_split.py` (3 Tests: Teilausschluss
         einer einzelnen Zeile, Toleranz gegen Rundungsfehler,
         unverändertes Verhalten für reine Link-Blöcke).

      Alle drei Fixes gegen die echte, vertrauliche "1526 VIRELICON.pdf"
      visuell verifiziert (Vorher/Nachher-Rendering der betroffenen
      Seiten) sowie zusätzlich gegen einen kompletten End-to-End-Lauf mit
      Fake-Provider (erzwungene lange Übersetzungen zur Wachstumsprobe).
      Gesamter Testlauf am Ende: 107 passed, 1 skipped (vorher 99 passed,
      1 skipped - 8 neue Tests in 2 neuen Dateien plus 3 neue Tests in
      `tests/test_ui_word_mode.py`).

**Abnahmekriterium:** DOCX und freigegebene PDF-Typen verwenden denselben
kontrollierten UI-Lauf und liefern neue, prüfbare Ausgabedateien ohne Änderungen
an geschützten Bereichen. DOCX-Teil erreicht (17.08.2026, siehe oben und
Backlog.md) - PPTX und DOCX teilen sich jetzt denselben Start-/Fortschritts-/
Abbruch-/Kosten-/QA-Bericht-Ablauf im UI (`ui/app.py::_EXECUTABLE_MODES`).
PDF-Teil ebenfalls erreicht (17.08.2026) - PDF ist jetzt Teil desselben
Ablaufs; die verbleibenden, oben aufgelisteten Detailfragen (Link-
Annotationen, Durchsuchbarkeit, Glyphen/Ligaturen, Font-Erhalt, Redaction
über Hintergrundbildern, echter Live-Lauf) sind bewusst NICHT Voraussetzung
für die UI-Anbindung selbst - sie bleiben offen und werden im QA-Bericht
jedes PDF-Laufs katalogisiert (siehe `ui/pdf_job.py`), nicht stillschweigend
ignoriert. Fünf der sechs Detailfragen inzwischen geprüft (17.08.2026, siehe
oben und Backlog.md); offen bleiben weiterhin: Symbol-/Private-Use-Font-
Glyphen, Originalfont-Einbettung (bewusste Architekturentscheidung, kein
Bug) und der echte Live-Lauf.

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
      Für DeepL zeigt die Analyse jetzt zusätzlich den echten Live-Kontingentstand
      (GET /v2/usage, siehe Backlog.md); Google/OpenAI/Grok bleiben bei der
      lokalen Schätzung, da ihre Nutzungs-/Kontingent-Endpunkte mehr als den
      bereits gespeicherten API-Schlüssel voraussetzen (siehe Backlog.md).
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
