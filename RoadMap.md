# Projekt-Roadmap

Stand: 18. August 2026 (PDF-ICO-Dokument, Word-vs-PDF-Priorität)

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

- [x] Entscheiden und dokumentieren, wann der direkte PDF-Pfad produktiv
      eingesetzt wird und wann ein vorhandenes Word-Original Vorrang hat
      (18.08.2026, Nutzerentscheidung): Liegt ein Word-Original vor, wird
      IMMER der Word-Pfad genommen; der direkte PDF-Pfad ist ausschließlich
      für den Fall vorgesehen, dass NUR ein PDF (kein Word-Original)
      existiert. Reine Dokumentationsentscheidung, keine Codeänderung -
      beide Pfade bleiben technisch unverändert nebeneinander bestehen und
      im UI weiterhin unabhängig wählbar.
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
- [x] Dasselbe explizite "ICO-Dokument"-Konzept wie bei Word (siehe
      Word/Writer-Abschnitt oben) auch für PDF ergänzt (18.08.2026), auf
      ausdrücklichen Nutzerwunsch ("ICO-Dokument auf alle Fälle
      nachrüsten"). Genau spiegelt Wort für Wort das bestehende
      Word-Muster (`DocxEngine.open(ico_mode=...)` /
      `self.separator_found`):
      - `pipeline/pdf/pymupdf_engine.py`: `PyMuPdfEngine.open(path,
        ico_mode=False)` - neuer Parameter, setzt `self._ico_mode` und
        setzt `self.first_page_metadata_found = False` zurück. Vorher lief
        `_split_first_page_metadata()` (Trennung auf
        `FIRST_PAGE_ANCHOR_TERMS = ["Issuer Address", "Asset Matrix"]`)
        für JEDE Seite 0 JEDES PDFs unbedingt mit - exakt derselbe
        Fehlerklasse, die `DocxEngine`s `ico_mode` schon für Word
        verhindert: ein PDF, das zufällig eine dieser Zeilen enthält, ohne
        ein tatsächliches ICO-Dokument zu sein, hätte ohne Vorwarnung
        einen Teil von Seite 1 unübersetzt gelassen. `extract_blocks()`
        wendet die Trennung jetzt nur noch an, wenn `page_index == 0 and
        self._ico_mode` gilt, und setzt `self.first_page_metadata_found`
        (Pendant zu `DocxEngine.separator_found`) danach frisch.
      - `ui/pdf_job.py`: `run_pdf_job(..., ico_mode=False)` reicht den
        Schalter an `engine.open()` durch; der QA-Bericht bekommt
        dieselbe dreistufige Meldung wie bei Word (aktiv & gefunden →
        Metadatenbereich ausgeschlossen; aktiv & nichts gefunden → Warnung,
        ob es wirklich ein ICO-Dokument ist; nicht aktiv → normale
        Volltextübersetzung).
      - `ui/workers.py` (`PdfTranslationWorker`), `ui/analysis.py`
        (Kostenanalyse nutzt denselben `ico_mode`, damit Schätzung und
        realer Lauf übereinstimmen) und `ui/i18n.py` (Tooltip-Text
        formatneutral für Word UND PDF umformuliert) entsprechend
        angepasst.
      - `ui/app.py`: statt eines zweiten, PDF-eigenen Schalters wird
        dieselbe `TranslationRequest.ico_mode`-Checkbox wiederverwendet
        (`TranslationRequest.ico_mode` war schon vorher ein generisches
        Feld, nur die UI-Sichtbarkeit war Word-only). `_mode_changed()`
        zeigt die Checkbox jetzt für Word ODER PDF und setzt sie nur beim
        Wechsel zu einem Modus zurück, der keines von beiden ist
        (Präsentation/Bilder); der Zustand bleibt beim Wechsel
        Word↔PDF bewusst erhalten, da beide Formate das Konzept
        unterstützen.
      - Neue Tests: `tests/test_pdf_ico_mode.py` (8 Tests, Engine- und
        Job-Ebene, inkl. Grenzfall "nur Seite 0 zählt" und
        "erneutes open() setzt zurück"); `tests/test_ui_word_mode.py`
        erweitert (Checkbox-Sichtbarkeit über beide Modi,
        Worker-Dispatch des Flags für PDF). Jeder Fix einzeln per
        Revert-Probe verifiziert (Engine-Gating, QA-Bericht-Meldung,
        UI-Sichtbarkeitslogik - jeweils gezielt zurückgebaut, Testfehler
        bestätigt, wiederhergestellt, `diff` bestätigt exakte
        Wiederherstellung, Gesamtsuite erneut grün). Gesamter Testlauf am
        Ende: 160 passed, 1 skipped.
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
- [x] Fehlende Glyphen aus Symbol-/Private-Use-Fonts behandelt (18.08.2026) -
      siehe Backlog.md für Details. Ein Symbol-/PUA-Font-Glyph (z. B. ein
      Wingdings-Bullet-Zeichen, Codepoint U+F086) verschwand beim
      Wiedereinfügen komplett spurlos (nicht einmal als Tofu-Box sichtbar),
      weil der Sans-Serif-Fallback-Font kein Glyph dafür kennt - direkt
      reproduziert: Output enthielt ein NUL-Codepoint statt des Symbols.
      Fix: jedes Private-Use-Area-Zeichen wird vor der Einfügung durch ein
      sichtbares Platzhalterzeichen ("□") ersetzt, plus Log-Eintrag im
      Anomalie-Log (Event `unsupported_symbol_glyph`). Das andere,
      NICHT identische Problem - Verlust reiner Unicode-Zeichen
      (Kyrillisch/Griechisch/CJK) im Backward-Compatibility-Pfad ohne
      Spans - war bereits vorher behoben (siehe Backlog.md).
- [x] Ungewollte `fi`-Ligatur bei Textsuche und Copy/Paste untersucht
      (17.08.2026) - bestätigt und als aktuell nicht sinnvoll behebbar
      dokumentiert, siehe Backlog.md.
- [x] Einbettung beziehungsweise Wiederverwendung von Originalfonts bewertet.
      Bestätigt (17.08.2026, siehe Backlog.md): wurde bis dahin gar nicht
      gemacht, `TextBlock.font_name` wurde nirgends zur Einfügung
      verwendet. Echte Font-Einbettung (Original-Font-Programm
      extrahieren/einbetten, mit Subsetting- und Lizenzfragen) bewusst als
      eigenes, größeres Vorhaben zurückgestellt - stattdessen kleine
      Verbesserung umgesetzt (18.08.2026, siehe Backlog.md):
      `block.font_name` wird jetzt grob auf eine CSS-Generic-Family
      (serif/monospace/weiterhin sans-serif als Default) abgebildet, statt
      immer unbedingt "sans-serif" zu verwenden. Deutlich näher am
      Original bei Serif-/Monospace-Dokumenten, aber weiterhin keine
      exakte Font-Wiedergabe - Font-Einbettung selbst bleibt offene,
      bewusst nicht angegangene Architekturentscheidung.
- [x] Hintergrundbilder und überlagerte Textblöcke gegen unbeabsichtigte
      Redaction abgesichert (17.08.2026) - siehe Backlog.md für Details.
- [x] Den PDF-UI-Pfad an einem echten Dokument über einen echten Provider
      live durchlaufen lassen (18.08.2026, als abgeschlossen markiert auf
      Nutzeranweisung) - dieser Punkt war ein stehengebliebenes Duplikat:
      der eigentliche echte Live-Lauf gegen "1526 VIRELICON.pdf" über
      Google als Provider ist bereits im direkt folgenden Eintrag unten
      ("Echter Live-Lauf des PDF-UI-Pfads...", 17.08.2026) vollständig
      dokumentiert, inklusive der drei dabei gefundenen und behobenen
      Bugs. Strukturteil (0 Fehler, alle Links erhalten, Formatierung
      unauffällig) war zu diesem Zeitpunkt bereits erledigt, siehe
      Backlog.md.
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
      Gesamter Testlauf zu diesem Zeitpunkt: 107 passed, 1 skipped
      (vorher 99 passed, 1 skipped - 8 neue Tests in 2 neuen Dateien plus
      3 neue Tests in `tests/test_ui_word_mode.py`).
- [x] Zwei weitere reale Formatierungsbugs auf Seite 2 derselben
      "1526 VIRELICON.pdf" gefunden (vom Nutzer anhand der echten
      Ausgabedatei gemeldet, nicht nur Screenshots) und behoben
      (17.08.2026):
      4. **Mehrere kurze, einzeilige Blöcke wurden nach der Übersetzung
         sichtbar kleiner geschrieben als ihre Nachbarn** - bis hinunter
         zu `_MIN_FONT_SIZE` (6pt) gegenüber dem normalen ~11pt-
         Fließtext. Erste Vermutung (zu knapp bemessene Original-Boxen)
         war falsch und wurde vom Nutzer korrekt zurückgewiesen - der
         Nutzer wies richtig darauf hin, dass der Originaltext an der
         fraglichen Stelle ganz gewöhnlich in der nächsten Zeile
         weiterläuft. Tatsächliche Root Cause in
         `PyMuPdfEngine._insert_html_text()`s CSS gefunden:
         `spans_to_html()` verpackt JEDEN Absatz in `<p>...</p>`, auch
         einen einzeiligen Block ohne echten Absatzumbruch, und
         PyMuPDFs Story-/CSS-Engine reserviert für ein `<p>`-Element
         zusätzlichen Rand-/Zeilenhöhenraum, den die Wachstumslogik
         (`try_grow()`) nicht kennt und nicht ausgleicht - direkt
         reproduziert: eine knapp bemessene, einzeilige Originalbox nahe
         Seitenrand/Kollisionsgrenze (wenig Wachstumsspielraum in beiden
         Achsen) passte mit einer nur geringfügig längeren Übersetzung
         NIE, egal wie weit `try_grow()` die Box verbreiterte - rein
         wegen dieses reservierten `<p>`-Raums, nicht aus echtem
         Platzmangel. Das erzwang ein Schrumpfen bis zur Untergrenze.
         Fix in neuer `_insert_html_css()`-Hilfsfunktion:
         `p {margin:0; line-height:1;}` setzt den reservierten Raum auf
         null; eine zusätzliche `p + p {margin-top: ...}`-Regel (nur für
         direkt aufeinanderfolgende `<p>`-Geschwister) stellt gezielt
         den Abstand zwischen zwei ECHTEN Absätzen innerhalb eines
         Blocks wieder her, damit ein echter Absatzumbruch nicht mit
         verschwindet - ohne diese Geschwister-Regel brach der erste
         Fix-Versuch (blankes `margin:0`) den bereits bestehenden
         Absatzabstand-Test in
         `tests/test_pdf_formatting_roundtrip.py`. Regressionsabdeckung
         in `tests/test_pdf_paragraph_css_reset.py` (2 Tests: keine
         Schrumpfung bei wenig Wachstumsspielraum, echter Mehrfach-
         Absatzabstand bleibt sichtbar) - beide Tests schlagen
         nachweislich fehl, wenn der alte CSS-String (ohne `p`-Reset)
         wiederhergestellt wird.
      5. **Markierte (blau hinterlegte) Blöcke verloren nach der
         Übersetzung ihren farbigen Hintergrund** - betraf ALLE
         markierten Blöcke außer dem einen, der (Symptom 3 oben) gar
         nicht übersetzt wurde. Vom Nutzer präzise beschrieben: ein
         dünner blauer Strich am unteren Rand der Box, "als wenn eine
         weiße Box mit Text drüberliegt". Root Cause in
         `PyMuPdfEngine.redact_block()` gefunden: die bisherige Annahme
         war, dass die ursprüngliche Markierungsfläche (als Seiteninhalt
         HINTER dem Blocktext gezeichnet) die Redaction unbeschadet
         übersteht und nur bei tatsächlichem Höhenwachstum
         (`_grow_highlight_if_needed()`) neu gezeichnet werden muss.
         Das ist falsch: `page.add_redact_annot(rect, fill=(1,1,1))`
         übermalt sein GESAMTES Rechteck weiß, unabhängig vom
         darunterliegenden Vektorinhalt - jeder redigierte markierte
         Block verlor daher seinen Hintergrund, nicht nur wachsende;
         `_grow_highlight_if_needed()` lief aber nur im Wachstumsfall
         und stellte die Farbe entsprechend auch nur dann wieder her.
         Fix: `redact_block()` zeichnet die Markierungsfarbe jetzt
         unmittelbar nach der Weiß-Redaction unbedingt neu, über die
         volle `_associated_highlight_extent()` (beide Achsen, nicht nur
         die bereits vorhandene Breiten-Verbreiterung) - jeder markierte
         Block startet damit vor jeder Texteinfügung von einer korrekt
         eingefärbten Ausgangslage, genau das, was
         `_grow_highlight_if_needed()` schon immer vorausgesetzt hatte.
         Regressionsabdeckung in
         `tests/test_pdf_highlight_background_persists.py` (2 Tests: Fall
         ohne nötiges Wachstum behält seinen Hintergrund vollständig -
         inklusive des Falls, dass die gezeichnete Markierungsfläche
         etwas über die reine Textbbox hinausragt -, unmarkierte Blöcke
         bleiben unverändert weiß).

      Beide Fixes zusätzlich gemeinsam gegen die echte, vertrauliche
      "1526 VIRELICON.pdf" verifiziert (Rendering der betroffenen
      Blöcke mit echtem extrahiertem deutschem Übersetzungstext zeigt
      durchgängig volle Originalschriftgröße und vollständigen blauen
      Hintergrund). Gesamter Testlauf am Ende: 111 passed, 1 skipped.
- [x] "PDF-Übersetzung korrigieren" - manuelle Nachbearbeitung einzelner
      Blöcke direkt im UI umgesetzt (18.08.2026). Auslöser: der Nutzer
      fand im selben Live-Lauf eine echte Fehlübersetzung - der
      Eigenname "Manuel" (Sprecher einer Zitat-Zuschreibungszeile, "-
      Manuel to PQ") kam vom Provider als "Handbuch" zurück. Geschützte
      Begriffe (`pipeline/translation/protected_terms.py`, bereits
      vorhanden) lösen das nur für einen Begriff, der IMMER ein Name
      ist - der Nutzer wies zurecht darauf hin, dass das die falsche
      Lösung für ein Wort ist, das mal Name, mal echtes Wort sein kann.
      Statt einer PDF-zu-Word-Konvertierung (erwogen, aber verworfen -
      das Rekonstruieren eines editierbaren Dokuments aus reinen
      PDF-Positionsdaten ist ein deutlich schwierigeres, verlustträch-
      tigeres Problem als das direkte In-Place-Bearbeiten, das diese
      PDF-Engine bereits beherrscht) und statt eines vollwertigen
      PDF-Editors (bewusst nicht nachgebaut) eine gezielte Korrektur-
      Tabelle, die dieselbe redact_block()/insert_text()-Maschinerie
      wiederverwendet, die translate_pdf() ohnehin schon nutzt:
      - `pipeline/pdf/translate_pdf.py`: neue `TranslatedBlockRecord`
        (Seite, Block-Index, Original, tatsächlich eingefügtes HTML) -
        `translate_pdf()` sammelt diese jetzt zusätzlich in
        `PdfTranslationStats.blocks` (rein additiv, bestehende Aufrufer
        unberührt). `html_to_plain_text()` (neu in
        `pipeline/pdf/pymupdf_engine.py`) macht daraus editierbaren
        Klartext für die Tabelle. `build_corrected_records()` baut nur
        für tatsächlich bearbeitete Zeilen neues HTML (über die
        bestehende `_plain_text_to_html()`) - unveränderte Zeilen
        behalten ihr Original-HTML und damit ihre Formatierung
        (fett/kursiv/unterstrichen) exakt. `apply_pdf_corrections()`
        spielt die (ggf. korrigierte) Liste gegen eine FRISCH vom
        unangetasteten Quell-PDF geöffnete Engine ein - nie gegen die
        bereits übersetzte, weil ein zweiter Redact-Durchlauf auf dem
        bereits gewachsenen Ergebnis Reste der ersten Übersetzung
        stehen lassen könnte (siehe Funktionsdocstring).
      - `ui/pdf_job.py`: neue `run_pdf_correction_job()` - im Gegensatz
        zu `run_pdf_job()` erlaubt sie bewusst eine bereits existierende
        Zieldatei (Nutzer-Entscheidung: die bestehende Übersetzung wird
        überschrieben statt immer eine neue Datei anzulegen), da hier
        ein bestehendes Ergebnis verfeinert statt eine neue Quelle
        geschützt wird.
      - `ui/correction_dialog.py` (neu): `PdfCorrectionDialog`, eine
        Tabelle Seite/Original (read-only)/Übersetzung (editierbar) mit
        "Anwenden und speichern"-Knopf - läuft synchron auf dem
        UI-Thread statt über einen Hintergrund-Worker, da hier (anders
        als beim eigentlichen Übersetzungslauf) keinerlei
        Provider-/Netzwerkaufruf mehr stattfindet.
      - `ui/app.py`: neuer Knopf "Übersetzung korrigieren" - erscheint
        nach einem PDF-Lauf nur, wenn tatsächlich korrigierbare Blöcke
        vorhanden sind (Nutzer-Entscheidung: über einen Knopf statt
        automatisch nach jedem Lauf). Ein zweiter Korrektur-Durchgang
        startet bewusst von der zuletzt gespeicherten Korrektur, nicht
        wieder von der ursprünglichen Maschinenübersetzung.
      Bekannte Einschränkung, dokumentiert statt stillschweigend
      übergangen: nur der `block.spans`-Pfad (HTML/Story) wird erfasst -
      der einzige, den echte Produktionsblöcke je durchlaufen (siehe
      `insert_text()`s Docstring); der reine Text-Fallback-Pfad ist
      nicht korrigierbar, aber auch praktisch nicht erreichbar.
      Regressionsabdeckung: `tests/test_pdf_translation_corrections.py`
      (6 Tests, Pipeline-Ebene), `tests/test_pdf_correction_job.py` (3
      Tests, UI-Job-Ebene), `tests/test_ui_pdf_correction.py` (5 Tests,
      Qt-Ebene inkl. End-to-End-Anwenden einer Korrektur) - jeweils per
      Revert-Probe gegen die entscheidenden Verhaltensänderungen
      bestätigt. Gesamter Testlauf am Ende: 134 passed, 1 skipped
      (vorher 120 passed, 1 skipped - 14 neue Tests in 3 neuen Dateien).

      **Nachtrag - Rich-Text-Editor statt Klartext (18.08.2026):** Die
      erste Version oben bearbeitete die Übersetzungs-Zelle direkt als
      Klartext, wodurch eine bearbeitete Zeile ihre Inline-Formatierung
      (fett/kursiv/unterstrichen) verlor. Auf Nachfrage bestätigte der
      Nutzer, dass das ein echtes Problem ist ("Ein Rich-Text-Editor ist
      wichtig für mich"). Umgesetzt:
      - `ui/rich_text.py` (neu): einziges Modul im Projekt, das Qt-
        Rich-Text-Klassen importieren darf (`QFont`/`QTextDocument`),
        analog zur fitz-Exklusivität von `pymupdf_engine.py`.
        `qt_document_to_project_html()` läuft ein `QTextDocument` Block
        für Block, Fragment für Fragment ab und baut daraus dasselbe
        minimale `<p>`/`<br/>`/`<u>`/`<i>`/`<b>`-Markup, das
        `spans_to_html()` erzeugt - bewusst NICHT
        `QTextDocument.toHtml()` (viel zu verbose/inkompatibel). Laden
        in die andere Richtung braucht keine Konvertierung:
        `QTextEdit.setHtml()` versteht das schmale Tag-Set direkt.
      - `pipeline/pdf/translate_pdf.py`: neue
        `build_corrected_records_from_html()` - Pendant zu
        `build_corrected_records()`, nimmt aber bereits fertiges
        Projekt-HTML (aus `qt_document_to_project_html()`) statt
        Klartext entgegen, also ohne den verlustbehafteten
        `_plain_text_to_html()`-Umweg. Die alte, klartextbasierte
        Funktion bleibt bestehen (eigene Tests, mögliche künftige
        Datei-/CLI-Korrekturwege), wird vom Dialog aber nicht mehr
        verwendet.
      - `ui/correction_dialog.py`: umgebaut auf Master-Detail - die
        Tabelle zeigt Seite/Original/Übersetzung nur noch als
        Nur-Lese-Vorschau; die eigentliche Bearbeitung passiert in
        einem separaten `QTextEdit` darunter mit Fett/Kursiv/
        Unterstrichen-Knöpfen (`QTextEdit.mergeCurrentCharFormat()` -
        wirkt automatisch auf die Selektion oder, ohne Selektion, auf
        neu getippten Text). Dirty-Tracking (`_dirty`-Set, gespeist vom
        `textChanged`-Signal, mit einem `_loading`-Guard gegen
        programmatisches `setHtml()`) sorgt dafür, dass eine nie
        angefasste Zeile ihr Original-HTML byte-genau behält statt
        einen visuell identischen, aber neu serialisierten Qt-Roundtrip
        zu bekommen.
      Zusätzliche Regressionsabdeckung:
      `tests/test_pdf_rich_text_corrections.py` (12 Tests: Bold/Italic/
      Underline-Rundlauf, Teilselektion, weicher Zeilenumbruch,
      HTML-Escaping, `build_corrected_records_from_html()`, sowie ein
      End-to-End-Test durch den echten Dialog, der "Manuel" korrigiert
      UND fett setzt, während ein unberührter fett formatierter Block
      seine Formatierung behält). `tests/test_ui_pdf_correction.py`
      erweitert (jetzt 6 Tests) inkl. eines gezielten Tests, der NUR
      `_flush_active_row()`s eigene Dirty-Prüfung isoliert prüft (per
      Revert-Probe bestätigt: eine schwächere `==`-Prüfung allein hätte
      diese Regression NICHT gefangen, da der Qt-Roundtrip für
      unformatierten Text zufällig denselben String erzeugt - erst die
      Objektidentitätsprüfung (`is`) auf `_row_html` beim Zeilenwechsel
      deckte es auf). Gesamter Testlauf am Ende: 147 passed, 1 skipped.

      **Nachtrag 2 - Tastaturkürzel (18.08.2026):** Auf Nutzerwunsch
      ("GErne noch die Tastaturkürzel mit einbauen") Strg+B/Strg+I/
      Strg+U ergänzt (`QKeySequence.StandardKey.Bold/Italic/Underline` -
      plattformgerechte Bindung, z. B. Cmd auf macOS), als
      `QShortcut(..., context=WidgetShortcut)` auf `self.editor`
      verdrahtet (wirkt nur bei Fokus im Editor). Da ein `QShortcut`
      selbst keinen Checked-Zustand hat, flippen die drei neuen
      `_shortcut_toggle_*()`-Handler den jeweiligen Knopf zuerst manuell
      und rufen dann dieselbe `_toggle_*()`-Logik wie ein echter Klick.
      Tooltips ("Fett (Strg+B)" etc.) neu, `correction.hint` erwähnt die
      Kürzel jetzt. Vier neue Tests in `tests/test_ui_pdf_correction.py`
      (Key-Binding-Check gegen `QKeySequence.StandardKey`, Bold-Handler
      inkl. Zurück-Toggle, Kursiv/Unterstrichen-Handler, End-to-End bis
      ins gespeicherte PDF) - per Revert-Probe bestätigt: drei der vier
      schlagen fehl, wenn die drei Handler zu No-Ops gemacht werden (der
      Key-Binding-Test bleibt korrekt grün, da er nur die Bindung selbst
      prüft, nicht das Verhalten). Gesamter Testlauf am Ende: 151 passed,
      1 skipped (vorher 147 passed, 1 skipped).

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
ignoriert. Alle sechs Detailfragen inzwischen geprüft (17./18.08.2026, siehe
oben und Backlog.md), zuletzt Symbol-/Private-Use-Font-Glyphen (behoben)
und Originalfont-Einbettung (kleine Verbesserung umgesetzt, echte
Einbettung bleibt bewusste, offene Architekturentscheidung, kein Bug). Der
echte Live-Lauf ist ebenfalls erledigt (17.08.2026, siehe oben) - diese
Formulierung war hier nicht mehr aktuell.

## Phase 3 – Bildübersetzung und OCR

- [x] Architektur abgestimmt (18.08.2026, Nutzerentscheidung nach Rücksprache):
      OCR und Rückschreibung werden je als eigene, austauschbare
      Backend-Abstraktion gebaut - genau nach dem Muster, das
      `pipeline/translation/base.py::TranslationProvider` für DeepL/Google/
      OpenAI/Grok schon vorgibt (`OcrEngine`- bzw.
      `InpaintingBackend`-Protokoll, mehrere Implementierungen dahinter,
      Verfügbarkeit wird vor dem Start geprüft und im UI angezeigt statt
      erst beim Lauf selbst zu scheitern).

      **OCR:** Tesseract lokal (bereits als Binary vorhanden, kostenlos,
      keine Bilddaten verlassen den Rechner) als erstes Backend, mit
      Verfügbarkeitsprüfung (`shutil.which("tesseract")`, analog zu
      `credential_status()` für die Übersetzungs-Provider). Cloud-OCR als
      zweites, auswählbares Backend vorgesehen (konkreter Anbieter noch
      offen) - Beweggrund: eine mögliche spätere Standalone-Version der App
      soll auch bei Nutzern ohne installiertes Tesseract und ohne
      ausreichend starke Hardware funktionieren.

      **Rückschreibung (vier Backends, alle hinter derselben Abstraktion):**
      1. Box-Overlay - Textregion wird mit einer Fläche übermalt (Prinzip
         wie beim bestehenden PDF-Redact/Insert), übersetzter Text wird
         eingefügt. Keine neue Abhängigkeit, funktioniert überall, aber bei
         fotografischen/strukturierten Hintergründen als "Flicken"
         erkennbar.
      2. Klassisches CPU-Inpainting (OpenCV `cv2.inpaint`, Bibliothek ist
         bereits installiert) - rekonstruiert den Hintergrund unter dem
         Originaltext ohne KI-Modell, läuft auf jeder CPU.
      3. KI-Inpainting lokal (GPU) - Modell: LaMa (etabliert genau für
         Objekt-/Text-Entfernung mit Hintergrund-Rekonstruktion, deutlich
         leichter als ein volles Stable-Diffusion-Modell). Braucht PyTorch
         plus heruntergeladene Modellgewichte (spürbare neue Abhängigkeit,
         mehrere hundert MB bis wenige GB) und im Idealfall eine
         ausreichend starke GPU. Eine Fähigkeitsprüfung (GPU vorhanden?
         genug Grafikspeicher für das Modell?) läuft vor dem Start in der
         Analyse-Phase (zusammen mit der Kostenschätzung); reicht die GPU
         nicht, wird die Cloud-Variante vorgeschlagen - keine automatische
         Umschaltung ohne Zustimmung.
      4. KI-Inpainting Cloud - OpenAI zuerst (Images-Edit-Endpunkt
         unterstützt maskenbasiertes Inpainting laut Dokumentation, und der
         API-Key ist über `get_openai_api_key()` bereits im OS-Keyring
         hinterlegt - kein neuer Zugangsdaten-Typ nötig). Google/Vertex AI
         (Imagen) unterstützt maskenbasiertes Inpainting ebenfalls, ist
         aber ein anderes Produkt als die bestehende Cloud-Translation-v2-
         Anbindung (`GoogleTranslateProvider`) und würde einen neuen
         Service-Account-Zugangsdaten-Typ statt des bisherigen einfachen
         API-Keys brauchen (Grund, warum `GoogleTranslateProvider` bewusst
         nicht das volle Google-SDK nutzt, siehe dessen Docstring) - als
         zweites Cloud-Backend vorgemerkt, in dieser Runde nicht umgesetzt.
         Grok (xAI) unterstützt laut Dokumentation nur allgemeine
         Bildbearbeitung per Textprompt, keine maskenbasierte
         Regionsbearbeitung - für diesen Anwendungsfall ungeeignet. DeepL
         hat keine Bild-API. Beide damit keine Kandidaten für dieses
         Feature.

      **Umsetzungsreihenfolge:** zuerst Box-Overlay und klassisches
      CPU-Inpainting (sofort lauffähig, keine neuen schweren
      Abhängigkeiten) zusammen mit der eigenständigen Bildübersetzung
      (einzelne Bilddateien, `TranslationMode.IMAGES`) als Fundament;
      danach GPU-Inpainting (LaMa) und Cloud-Inpainting (OpenAI); danach
      Einbettung in PDF/Word/PPTX, Auswahl-UI und Korrektur-Dialog (siehe
      restliche Punkte unten). Das GPU-Backend kann in der Cloud-Sandbox
      dieser Entwicklungsumgebung nur in seiner Logik/über einen
      CPU-Fallback getestet werden (keine GPU hier vorhanden) - die echte
      GPU-Ausführung muss wie bei anderen Features durch einen realen Lauf
      auf der Nutzer-Maschine verifiziert werden.
- [x] Pipeline-Fundament implementiert und getestet (18.08.2026, Stand
      dieser Session - UI-Anbindung fehlt noch, siehe unten): OCR-Backend-
      Abstraktion (`pipeline/images/ocr.py::OcrEngine`-Protocol,
      `TesseractOcrEngine`, `tesseract_available()`), Rückschreibe-
      Abstraktion (`pipeline/images/inpainting.py::InpaintingBackend`-
      Protocol, `BoxOverlayBackend`, `CvInpaintingBackend`), der komplette
      OCR-Übersetzung-Rückschreibung-Durchlauf
      (`pipeline/images/translate_image.py::translate_image()`, spiegelt
      `translate_pdf()`/`translate_document()`) sowie der Job-Ablauf
      (`ui/image_job.py::run_image_job()`, spiegelt `run_pdf_job()`, inkl.
      QA-Bericht). `ui/document_job_common.py` um
      `OCR_ENGINE_FACTORIES`/`INPAINTING_BACKEND_FACTORIES` und
      `build_ocr_engine()`/`build_inpainting_backend()`/
      `ocr_engine_available()` ergänzt - bewusst dort statt in
      `pipeline/images/`, damit die spätere Einbettung in PDF/Word/PPTX
      (siehe unten) dieselbe Auswahl direkt wiederverwenden kann. 38 neue
      Tests über sechs neue Testdateien
      (`tests/test_image_ocr.py`, `tests/test_image_inpainting.py`,
      `tests/test_image_cv_inpainting.py`, `tests/test_translate_image.py`,
      `tests/test_document_job_common.py`, `tests/test_image_job.py`),
      jede Kernmechanik per Revert-Probe verifiziert (Zeilen-Gruppierung
      der OCR-Erkennung, Hintergrundfarbe-Sampling/Kontrastfarbe bei
      Box-Overlay, `cv2.inpaint()`-Aufruf, Fehlerbehandlung pro Textregion
      in `translate_image()`, Verfügbarkeitsprüfung in
      `ocr_engine_available()`, Zieldatei-Existenzprüfung in
      `run_image_job()`). Gesamter Testlauf am Ende: 198 passed, 1
      skipped (vorher 160 passed, 1 skipped).

      Noch offen, bevor dieser Punkt vollständig abgeschlossen ist: echte
      UI-Anbindung (Start-Button-Dispatch für `TranslationMode.IMAGES`,
      OCR-Engine-/Rückschreibe-Backend-Auswahl im Formular,
      `ui/analysis.py`s IMAGES-Zweig nutzt noch keine echte OCR-
      Zeichenschätzung). Dabei außerdem eine bisher unadressierte Lücke
      entdeckt: `ui/app.py::_start()` verarbeitet unabhängig vom Modus nur
      `request.source_paths[0]` - für IMAGES-Modus, der laut
      `TranslationRequest.validation_errors()` bewusst MEHRERE Dateien
      gleichzeitig erlaubt (siehe `ui/models.py`), fehlt noch die
      Mehrdatei-Verarbeitung (mehrere `run_image_job()`-Aufrufe
      nacheinander, ein Ausgabebild + QA-Bericht pro Datei) - als
      eigener, noch nicht umgesetzter Teil dieses Punkts festgehalten,
      nicht stillschweigend übergangen.
- [x] Mehrdatei-Verarbeitung entschieden und umgesetzt (18.08.2026,
      Nutzerentscheidung: „Nacheinander, alle automatisch“): eine
      IMAGES-Auswahl mit mehreren Dateien wird sequenziell abgearbeitet,
      ein Ausgabebild + eine QA-Bericht-Datei pro Bild, EIN gemeinsamer
      Fortschrittsbalken über den ganzen Batch (`ui/image_job.py::
      run_image_batch_job()`, ruft `run_image_job()` pro Datei auf;
      `ImageBatchStats`/`ImageBatchJobResult` duck-typen dieselben
      `.processed`/`.translated`/… Felder wie
      `PresentationTranslationStats`/`WordTranslationStats`/
      `PdfTranslationStats`, damit `ui/app.py` sie ohne Sonderfall lesen
      kann). Bekannte, dokumentierte Vereinfachung: das
      Zeichen-Lauflimit (`max_chars_per_run`) gilt PRO DATEI (jede
      `run_image_job()`-Aufruf baut einen eigenen
      `TranslationBudgetGuard`), nicht gemeinsam über den ganzen Batch
      wie bei einem mehrseitigen PDF.
- [x] Echte UI-Anbindung fertiggestellt und verifiziert (18.08.2026):
      `ui/app.py` zeigt für `TranslationMode.IMAGES` zwei neue Dropdowns
      (OCR-Engine, Rückschreibe-Backend, gespeist aus
      `OCR_ENGINE_FACTORIES`/`INPAINTING_BACKEND_FACTORIES`) inkl. eines
      proaktiven Verfügbarkeitshinweises (`_update_ocr_engine_hint()`,
      spiegelt `_update_provider_credential_hint()`), Start-Button
      dispatcht jetzt EINEN `ImageTranslationWorker` für die gesamte
      Dateiauswahl (`ui/workers.py`) statt nur `source_paths[0]`, mit
      eigenem Bestätigungstext/eigener Fortschritts-/Ergebnisdarstellung
      (`start.confirm_summary_images`, `job.progress_count_files`,
      `job.result_summary_images` in `ui/i18n.py`, DE/EN-Parität durch
      bestehenden Test abgesichert). `ui/analysis.py`s IMAGES-Zweig
      führt jetzt echte Tesseract-OCR während der Analyse aus (statt
      immer 0 Zeichen zu melden), gated durch `ocr_engine_available()` -
      sonst hätte eine Kostenschätzung von $0.00 das Leitprinzip „Vor
      jedem kostenpflichtigen Lauf erfolgen Analyse, Kostenschätzung und
      ausdrückliche Bestätigung“ verletzt, sobald der IMAGES-Modus
      tatsächlich lauffähig wurde. 7 neue UI-Tests
      (`tests/test_ui_images_mode.py`, spiegelt
      `tests/test_ui_word_mode.py`s Muster: Worker-Dispatch,
      Zeilen-Sichtbarkeit, `_request()`-Felder, Fail-fast bei fehlender
      OCR-Engine, Fortschrittstext, Ergebnisdarstellung ohne
      QA-Bericht-Button). Kern-Mechanik (Batch-Dispatch: ein Worker für
      alle Dateien statt nur die erste) per Revert-Probe verifiziert.
      Gesamter Testlauf am Ende: 212 passed, 1 skipped (vorher 205
      passed, 1 skipped).
- [x] GPU-Inpainting-Backend (LaMa) implementiert und in Analyse/UI
      angebunden (18.08.2026): `pipeline/images/inpainting.py::
      GpuInpaintingBackend` nutzt das vortrainierte LaMa-Modell
      (https://github.com/advimman/lama) über die leichtgewichtige
      `simple-lama-inpainting`-Wrapper-Bibliothek (lazy import, neue
      optionale `requirements-gpu.txt` - getrennt von
      `requirements-ocr.txt`, da PyTorch eine deutlich größere,
      GPU-spezifische Installation ist). `gpu_inpainting_available()`
      prüft VOR jedem Lauf (mirrors `tesseract_available()`/
      `credential_status()`): PyTorch importierbar? CUDA-Gerät
      sichtbar? Mindestens `GPU_MIN_VRAM_GB` (4 GB, dokumentierter
      Schwellwert) Grafikspeicher? Bewusst KEIN automatischer
      CPU-Fallback bei unzureichender GPU (siehe Funktions-Docstring) -
      stattdessen als nicht verfügbar gemeldet, damit der Nutzer manuell
      auf Cloud-Inpainting wechseln kann, statt unbemerkt eine sehr
      langsame CPU-Inferenz zu bekommen. In `ui/document_job_common.py`
      neue `inpainting_backend_available()` (analog zu
      `ocr_engine_available()`) sowie Registrierung als
      `"gpu_inpainting"` in `INPAINTING_BACKEND_FACTORIES`. `ui/app.py`
      bekommt ein drittes Rückschreibe-Dropdown-Element plus einen
      proaktiven Verfügbarkeitshinweis
      (`_update_inpainting_backend_hint()`, spiegelt
      `_update_ocr_engine_hint()`) und einen Fail-fast-Check in
      `_start()`. Modell-Gewichte (mehrere hundert MB) werden beim
      ersten Lauf automatisch heruntergeladen und modul-weit gecached
      (`_LAMA_MODEL_CACHE`), damit ein Mehrdatei-Batch sie nicht pro
      Datei neu lädt; für eine spätere Standalone-Version ohne
      Internetzugriff zur Laufzeit können sie über die Umgebungsvariable
      `LAMA_MODEL` vorab lokal bereitgestellt werden.

      Wie schon beim Pipeline-Fundament dokumentiert: diese Cloud-Sandbox
      hat keine CUDA-GPU (siehe oben, "Umsetzungsreihenfolge") - getestet
      wurde deshalb die Logik ohne echte Hardware/das schwere PyTorch-
      Paket: `gpu_inpainting_available()`s komplette Verzweigung (PyTorch
      fehlt, keine CUDA, zu wenig VRAM, Geräte-Abfrage wirft eine
      Exception, ausreichend VRAM) über ein in `sys.modules` injiziertes
      Fake-`torch`-Modul statt einer echten (500+ MB) Installation, die
      reine Masken-Erzeugungslogik (`_build_inpainting_mask()`,
      Padding/Clamping an Bildgrenzen) sowie der Fail-fast-Guard in
      `GpuInpaintingBackend.apply()`. Ein echter Ende-zu-Ende-Testfall
      existiert bereits im Code (`test_apply_end_to_end_on_a_real_gpu`),
      wird hier aber automatisch übersprungen (via
      `gpu_inpainting_available()`) und muss auf der eigenen
      GPU-Maschine des Nutzers verifiziert werden - wie bei anderen
      "braucht echte Hardware/einen Live-Account"-Funktionen in diesem
      Projekt. 15 neue Tests über zwei Dateien
      (`tests/test_image_gpu_inpainting.py`: 10, `tests/
      test_document_job_common.py`: 5 zusätzliche) plus 3 neue UI-Tests
      in `tests/test_ui_images_mode.py`. Kern-Mechanik (VRAM-
      Schwellwertvergleich in `gpu_inpainting_available()`) per
      Revert-Probe verifiziert. Gesamter Testlauf am Ende: 229 passed, 2
      skipped (vorher 212 passed, 1 skipped).
- [x] GPU-Inpainting auf echter Nutzer-Hardware verifiziert (18.08.2026):
      `test_apply_end_to_end_on_a_real_gpu` lief auf Michaels Maschine
      tatsächlich durch (PASSED, nicht übersprungen) - echter LaMa-
      Modell-Download von GitHub Releases plus echte Inferenz auf einer
      CUDA-GPU bestätigt. Damit ist der oben offen gelassene
      Verifikations-Punkt geschlossen.

      Auf dem Weg dorthin zwei reale Installationsprobleme aufgetreten
      und behoben, beide dokumentiert für künftige Installationen:
      - `simple-lama-inpainting`s eigene (zu enge) Abhängigkeitsangaben
        (`numpy<2.0.0`, `pillow<10.0.0`, `opencv-python` statt der von
        `requirements-ocr.txt` verwendeten `opencv-python-headless`-
        Variante) haben bei einer naiven `pip install -r
        requirements-gpu.txt`-Installation in einer NICHT isolierten
        Python-Umgebung `opencv-python` zusätzlich zu
        `opencv-python-headless` installiert (beide belegen dasselbe
        `cv2`-Modul - ein von den opencv-python-Maintainern selbst als
        problematisch dokumentiertes Setup) und numpy/Pillow
        heruntergestuft, was mit dem bereits installierten
        `opencv-python-headless` sowie einem projektfremden Paket
        (scikit-image) in derselben geteilten Umgebung kollidierte.
        `pip uninstall opencv-python` hat dabei zusätzlich die
        tatsächlichen `cv2`-Dateien von `opencv-python-headless`
        mitgerissen (geteilte Installationspfade zwischen den
        opencv-python-Varianten) - behoben über
        `pip install --force-reinstall --no-deps opencv-python-headless`.
        `requirements-gpu.txt` empfiehlt seitdem ausdrücklich
        `pip install --no-deps simple-lama-inpainting` (durch
        Quellcode-Prüfung bestätigt: das Paket importiert nur torch,
        numpy, PIL und cv2 für reine Array-Operationen, keine
        GUI-Funktionen - `opencv-python-headless` deckt das vollständig
        ab) statt eines naiven `pip install -r requirements-gpu.txt`,
        um genau diesen Konflikt künftig gar nicht erst entstehen zu
        lassen.
      - Drei Tests (`tests/test_image_cv_inpainting.py`,
        `tests/test_image_inpainting.py`) nutzten `get_flattened_data()`
        für Pixel-Vergleiche - eine Pillow-Methode, die nur in sehr
        neuen Pillow-Versionen existiert (in dieser Entwicklungs-
        Sandbox vorhanden, auf Michaels durch obigen Konflikt auf 9.5.0
        heruntergestufter Installation nicht). Auf `.tobytes()`
        umgestellt (stabil über praktisch jede Pillow-Version hinweg,
        auch schneller als eine Tupel-Liste) - allgemeine Lehre: Test-
        Hilfsfunktionen sollten sich nicht auf sehr neue, wenig
        verbreitete API-Methoden stützen, wenn eine ebenso geeignete,
        breit kompatible Alternative existiert.
      Testlauf auf Michaels Maschine am Ende: 230 passed, 1 skipped
      (der verbleibende Skip: DeepL-Live-Kontingent-Test ohne
      konfigurierten Schlüssel, nicht GPU-bezogen).
- [x] Manueller Korrektur-Dialog für Bildübersetzungen implementiert
      (18.08.2026), analog zum bestehenden PDF-Korrektur-Dialog - bewusst
      VOR Cloud-Inpainting und der Einbettung von Bildübersetzung in PDF/
      Word/PPTX gebaut, da das Korrektur-Muster in allen diesen Fällen
      gebraucht wird und einmal gut statt mehrfach neu erfunden werden
      sollte.
      - Datenschicht: `ImageTranslationStats.replacements: list[TextReplacement]`
        (nur erfolgreich übersetzte Regionen, spiegelt
        `PdfTranslationStats.blocks`' Vertrag) plus
        `build_corrected_replacements(replacements, edited_texts: dict[int, str])`
        (Bild-Gegenstück zu `build_corrected_records_from_html()` - da
        `TextReplacement.translated_text` ein reiner `str` ist, kein
        Rich-Text, ist der Schlüssel schlicht der Listenindex, keine
        Seiten-/Block-Indizes wie bei PDF nötig).
      - `ImageJobResult` um `source_path` erweitert (nötig, da ein
        Batch-Lauf mehrere Dateien übersetzt und der Korrektur-Dialog pro
        Datei die passende PRISTINE Quelle braucht, nicht die schon
        übersetzte).
      - `ui/image_job.py::run_image_correction_job()` (Gegenstück zu
        `run_pdf_correction_job()`): kein OCR-/Provider-/Netzwerk-Aufruf,
        `destination` darf/soll bereits existieren (wird überschrieben),
        ruft direkt `InpaintingBackend.apply()` mit der (ggf. korrigierten)
        Replacement-Liste gegen die pristine Quelle auf.
      - `ui/image_correction_dialog.py::ImageCorrectionDialog` (neue
        Datei) - bewusst EINFACHER als `PdfCorrectionDialog`: reiner
        Klartext-Editor (`QPlainTextEdit`, kein Rich-Text-Toolbar/keine
        Tastenkürzel), da rasterisiert eingefügter Bildtext
        (`ImageDraw.text()`) kein Fett/Kursiv/Unterstrichen kennt; keine
        Seiten-Spalte, da ein Bild kein Seitenkonzept hat.
      - `ui/app.py`-Anbindung: `correct_translation_button` wird jetzt
        auch für einen `ImageBatchJobResult` mit mindestens einer
        korrigierbaren Datei angezeigt; hat der Batch mehrere
        korrigierbare Dateien, fragt ein `QInputDialog`-Picker (nach
        Ausgabedateiname) welche Datei korrigiert werden soll.
      - Neue i18n-Schlüssel `image_correction.*` (DE/EN, Parität über
        `tests/test_ui_i18n.py` geprüft).
      - Neue Tests: `tests/test_translate_image.py` (Datenschicht-
        Vertrag), `tests/test_image_correction_job.py`,
        `tests/test_ui_image_correction.py` (Button-Sichtbarkeit,
        End-to-End-Korrektur inkl. echtem OCR-Rückcheck, Datei-Picker bei
        mehreren Kandidaten). Kern-Mechanik (`_flush_active_row()`s
        Dirty-Guard) per Revert-Probe verifiziert. Gesamter Testlauf am
        Ende: 242 passed, 2 skipped.
- [x] Textüberlauf/-verunstaltung beim Zurückschreiben behoben (18.08.2026):
      Michael meldete anhand zweier echter Screenshots (Chat-App, Zoom-
      Anleitung), dass übersetzter Text über seine Box hinaus lief, Boxen
      sich überlappten und an falscher Stelle saßen. Ursachenanalyse mit
      echten Tesseract-Läufen auf den gemeldeten Bildern (nicht geraten)
      ergab ZWEI unabhängige Ursachen:
      1. Alle drei Rückschreibe-Backends zeichneten den kompletten
         übersetzten Text bisher IMMER auf einer einzigen, nicht
         umgebrochenen Zeile (`draw.text(...)`), unabhängig von
         `region.width` - Deutsch ist typischerweise 20-40 % länger als
         Englisch, lief also fast garantiert über die ursprüngliche
         Zeilenbreite hinaus in benachbarten Text hinein. Behoben durch
         eine neue geteilte Rendering-Funktion (`_fit_text()`/
         `_draw_fitted_text()` in `pipeline/images/inpainting.py`,
         genutzt von allen drei Backends): Text wird jetzt per Greedy-
         Wortumbruch auf `region.width` umgebrochen, die Schriftgröße bei
         Bedarf schrittweise verkleinert (bis zu einer lesbaren
         Mindestgröße), damit der umgebrochene Block innerhalb von
         `region.height` bleibt - bewusst SCHRUMPFEN statt die Box zu
         VERGRÖSSERN, da ein Wachstum der Box in eng gesetzten
         Screenshots (bestätigt an beiden gemeldeten Bildern) in den
         nächsten, unbeteiligten Textblock hineinlaufen würde. Zusätzlich
         eine feste Obergrenze für die Start-Schriftgröße
         (`_MAX_FONT_SIZE`, unabhängig von `region.height`) - Ursache für
         einen der auffälligsten gemeldeten Fehler (metergroße Schrift):
         eine OCR-Zeile hatte durch ein benachbartes Icon/Pfeil-
         Grafikelement eine fehlerhaft überhöhte Bounding-Box bekommen.
      2. Mehrere der schlimmsten "verunstalteten" Textstellen waren gar
         keine echten Übersetzungen, sondern von Tesseract falsch
         gelesene UI-Icons/Grafiken (z. B. eine Mute/Video-Symbolleiste
         als "a & 0"/"Papats Cut" erkannt, ein Pfeil-Icon als zusätzliche
         "4" in eine echte Textzeile hineingemischt, ein Anti-Aliasing-
         Halo um eine fette Überschrift als komplett unsinnige zweite,
         überlappende Geister-Zeile erkannt) - jeweils mit auffällig
         niedriger Tesseract-Konfidenz (20er-40er Werte) verglichen mit
         echtem Text (80er-90er) im SELBEN Bild. Behoben über einen neuen
         Mindest-Konfidenz-Filter (`DEFAULT_MIN_OCR_CONFIDENCE = 40.0`,
         `translate_image(..., min_confidence=...)` in
         `pipeline/images/translate_image.py`): eine Region unterhalb der
         Schwelle wird gar nicht erst übersetzt, sondern unverändert
         gelassen (neues `ImageTranslationStats.skipped`-Feld, im
         QA-Bericht sichtbar) - ausdrücklich als Heuristik dokumentiert,
         nicht als vollständige Lösung: mittelmäßig-konfidente
         Icon-Fehllesungen rutschen noch durch (siehe Backlog.md für die
         konkreten Restfälle).
      Beide Fixes gemeinsam an den ECHTEN, vom Nutzer gemeldeten Bildern
      über die tatsächliche `translate_image()`-Pipeline verifiziert
      (nicht nur an synthetischen Tests) - deutliche Verbesserung
      bestätigt, siehe Backlog.md für die Vorher/Nachher-Beobachtung.
      Kern-Mechanik (Schrumpf-Schleife in `_fit_text()`, Konfidenz-Skip in
      `translate_image()`) je per Revert-Probe verifiziert. Neue Tests in
      `tests/test_image_inpainting.py`/`tests/test_translate_image.py`.
      Gesamter Testlauf am Ende: 251 passed, 2 skipped.
- [ ] Gemeinsames Bildmodell für PDF, DOCX, PPTX und einzelne Bilddateien
      definieren.
- [ ] OCR-Engine auswählen, kapseln und Sprachpakete verwalten.
- [ ] Scan-/Bild-PDFs über einen verpflichtenden OCR-Dokumentpfad verarbeiten.
- [ ] Optionalen Pfad für eingebettete Bilder klar vom Dokumenttext trennen.
- [ ] Auswahl „keine“, „einzelne“ oder „alle Bilder“ um Vorschauen und
      Mehrfachauswahl ergänzen.
- [x] Eigenständige Übersetzung einer oder mehrerer Bilddateien implementieren.
- [ ] Textregionen, Leserichtung, Schrift, Farbe und Hintergrund erfassen -
      Textregionen/Farbe/Hintergrund werden bereits erfasst, Leserichtung/
      echte Schrifterkennung (Font-Matching) weiterhin offen.
- [x] Übersetzten Text mit Inpainting/Maskierung sicher zurückschreiben -
      Grundmechanik seit den drei Backends vorhanden, Überlauf-/Größen-
      Probleme siehe obiger Eintrag; verbleibende OCR-Fehllesungen bei
      komplexen Mehrspalten-/Infografik-Layouts (siehe Backlog.md) sind
      ein bekanntes, noch offenes Restrisiko, kein vollständig gelöstes
      Problem.
- [ ] Logos, dekorative Bilder und Hintergründe standardmäßig ausschließen.
- [ ] Identische, mehrfach eingebettete Bilder deduplizieren, um API- und
      OCR-Kosten nicht mehrfach zu berechnen.
- [ ] OCR-, Übersetzungs- und Bildmodellkosten getrennt schätzen und erfassen.
- [x] Originalbild, OCR-Text und Ergebnis in einer manuellen Prüfansicht zeigen
      (siehe Korrektur-Dialog-Eintrag oben).

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
