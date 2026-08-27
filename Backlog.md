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
- [x] Bildübersetzungs-Modul (OCR + Inpainting) als separater Bereich - umgesetzt
  als pipeline/images/ (ocr.py, inpainting.py, translate_image.py), siehe
  RoadMap.md Phase 3 für den vollständigen Verlauf (Tesseract-OCR, drei
  Rückschreibe-Backends, Batch-Verarbeitung, Korrektur-Dialog, GPU-Backend
  auf echter Hardware verifiziert). Dieser Eintrag war seit Phase 3 nicht
  mehr aktualisiert (21.08.2026 beim Cross-Projekt-Check für TME
  aufgefallen, siehe "Ideen / später bewerten" unten) - Cloud-OCR und
  Cloud-Inpainting bleiben laut RoadMap.md offen.
- [ ] PyInstaller-Bundles für Releases (später, nach stabiler Kernfunktion)
- [ ] Optional: PyPI-Package
- [x] Bildübersetzung als eigenständige, in andere Programme einbindbare
  Schnittstelle bauen (22.08.2026, Klärung mit Michael - Vorgeschichte siehe
  "Ideen / später bewerten", Eintrag "Cross-Projekt: Bildübersetzung als
  Basis für TME"). TME läuft aktuell auf demselben Rechner wie
  PDF-Translator, soll aber später auch eigenständig laufen können - die
  Schnittstelle ist deshalb von Anfang an sauber konfiguriert und
  dokumentiert, nicht an interne, noch in Bewegung befindliche
  PDF-Translator-APIs gekoppelt. Ausdrücklich entkoppelt von der
  Deployment-Frage weiter unten: solange TME auf demselben Rechner läuft,
  ist kein PyInstaller/Standalone-Build nötig, nur eine saubere
  CLI-Schnittstelle.

  Umgesetzt als neues Top-Level-Paket `image_translate_cli/` (nicht unter
  `pipeline/` oder `ui/` - siehe Paket-Docstring): `cli.py` (zwei
  Subcommands, `check` und `translate`), `config.py` (versioniertes
  JSON-Config-Schema, `CONFIG_SCHEMA_VERSION`), `report.py` (versioniertes
  JSON-Report-Schema, `REPORT_SCHEMA_VERSION`), `CLI.md` (vollständige
  Dokumentation: Kommandos, Feldreferenz Config/Report, Exit-Codes,
  Versionierungspolitik, bekannte Grenzen, Subprocess-Aufrufbeispiel für
  TME). Config enthält nie Zugangsdaten - die werden wie überall im
  Projekt über `pipeline/credentials.py` aufgelöst.

  Dabei aufgeräumt: `PROVIDER_FACTORIES`/`OCR_ENGINE_FACTORIES`/
  `INPAINTING_BACKEND_FACTORIES` (+ Verfügbarkeitsprüfungen) lagen bisher
  in `ui/document_job_common.py` ("UI-facing string key -> Backend-Klasse
  ist ein UI-Layer-Concern") - genau die Kopplung, die für eine
  eigenständige Schnittstelle vermieden werden sollte. Nach
  `pipeline/registry.py` verschoben (reiner Move, keine
  Verhaltensänderung); `ui/document_job_common.py` re-exportiert
  unverändert für bestehende Aufrufer (`ui/app.py`, `ui/image_job.py`,
  `ui/pdf_job.py`, `ui/word_job.py`, `ui/pptx_job.py`, `ui/analysis.py`
  geprüft - alle importierten Namen bleiben verfügbar). `check`
  übersetzt das in einen Preflight-Befehl (Provider-Zugangsdaten +
  OCR-/Inpainting-Backend-Verfügbarkeit, kein API-Aufruf), damit TME einen
  `translate`-Lauf vorab prüfen kann.

  Nebenbei gefunden und behoben: `pipeline/credentials.py::get_api_key()`
  listete bei einem `get_deepl_api_key()`-artigen Aufruf dieselbe
  Umgebungsvariable doppelt in der Fehlermeldung (`env_names` enthielt
  bereits `key_name.upper()`) - aufgefallen, weil genau diese Meldung jetzt
  über `check`/den Report nach außen sichtbar ist. Fix: `candidates` per
  `dict.fromkeys()` dedupliziert, Reihenfolge erhalten.

  End-to-End lokal getestet (Sandbox mit Tesseract, ohne echte
  Provider-Zugangsdaten): `check` meldet fehlende Zugangsdaten korrekt und
  gibt Exit-Code 1 zurück; unbekannte `provider`/`schema_version` in der
  Config geben Exit-Code 2 mit klarer Fehlermeldung; `translate --dry-run`
  liefert eine Zeichen-/Kostenschätzung ohne Provider-Aufruf;
  `translate --input`/`--input-dir` erzeugen beide ein korrektes Bild plus
  einen vollständigen, schema-konformen JSON-Report, inklusive des
  Falls "eine Textregion schlägt fehl (TranslationError mangels
  Zugangsdaten), das Bild bleibt trotzdem Status `ok`" - mirrors
  `translate_image()`s eigene "eine schlechte Region bricht nicht das
  ganze Bild ab"-Regel.

  Noch offen (nicht blockierend für die Schnittstelle selbst): stabiler
  `console_scripts`-Entry-Point (`pyproject.toml`) für einen Aufruf ohne
  `python -m`; echter End-to-End-Test mit TME selbst (bisher nur isoliert
  gegen synthetische Testbilder verifiziert); `--dry-run`s Schätzung ist
  bewusst konservativ (siehe CLI.md "Bekannte Grenzen" - wendet
  `max_height_ratio` nicht an); kein Abbruch-Mechanismus über die
  CLI-Grenze hinweg (Report-Status `"cancelled"` ist vorgesehen, aber noch
  nicht auslösbar).

  **Nachtrag (22.08.2026, Michael: "für die Zukunft offen und dynamisch
  behalten"):** Zwei Fragen dazu geklärt und umgesetzt.

  Provider-Zugangsdaten: `config.json`s `provider`-Feld wählt nur AUS,
  welcher Anbieter genutzt wird; der API-Key bleibt getrennt und wird wie
  im Rest des Projekts über `pipeline/credentials.py` aufgelöst
  (Umgebungsvariable vor OS-Keyring `"pdf-translator"`). Ein Aufrufer wie
  TME braucht dafür keine eigene Provider-/Credential-Verwaltung für Bilder
  - er setzt beim Subprocess-Aufruf einfach die passende Umgebungsvariable
  mit seinem eigenen, bereits konfigurierten Key (dokumentiert in CLI.md,
  neuer Abschnitt "Zugangsdaten für den Provider").

  Provider-Liste dynamisch statt hartkodiert: vorher war "welcher Provider
  unterstützt wird" über DREI unabhängige Mappings verstreut
  (`pipeline/registry.py`s Dict, eine `PricingModel`-Konstante in
  `pipeline/translation/cost_control.py`, eine dritte Credential-Check-
  Zuordnung, die in `image_translate_cli/cli.py` neu entstanden wäre) -
  leicht zu vergessen, und unpassend für "wir wissen noch nicht, welche
  Provider künftig dazukommen". Umgebaut auf EINE zentrale Registrierung:
  `pipeline/registry.py::ProviderSpec` (Name + Factory + Pricing +
  Credential-Check in einem Objekt) und `register_provider()`;
  `PROVIDER_FACTORIES` wird jetzt live von dort abgeleitet (in-place
  mutiert, nicht einmalig berechnet - ein Bug in der ersten Fassung dieses
  Umbaus, bei dem eine spätere Registrierung nicht mehr auftauchte, wurde
  beim Testen gefunden und behoben). `image_translate_cli/cli.py` verwendet
  jetzt `get_provider_spec()`/`provider_credential_status()` statt einer
  eigenen Kopie der Provider-Zuordnung. Ein künftiger fünfter Provider
  braucht dadurch nur noch eine `TranslationProvider`-Implementierung plus
  EINEN `register_provider(ProviderSpec(...))`-Aufruf - kein Anfassen von
  `image_translate_cli/config.py`, `cli.py` oder der Desktop-UI mehr, da
  alle drei nur noch lesend auf die Registry zugreifen. Getestet: eine zur
  Laufzeit nachregistrierte Test-Provider-Spec wird von
  `image_translate_cli/config.py`s Config-Validierung sofort akzeptiert,
  ohne Codeänderung an `config.py` selbst; bestehende vier Provider
  weiterhin funktionsfähig (`check`/`translate` erneut end-to-end
  verifiziert). Details: CLI.md, neuer Abschnitt "Neue Provider
  hinzufügen".

  **Nachtrag 2 (22.08.2026, Michael: "Ich schicke ein Bild in die CLI,
  bekomme eine Vorschau um etwaige Korrekturen zu machen und bekomme dann
  ein übersetztes Bild zurück"):** Frage geklärt, ob der Korrektur-Dialog
  (`ui/image_correction_dialog.py`) mit ausgelagert werden sollte - Antwort
  nein für den Dialog selbst (inhärent interaktiv/visuell, jede aufrufende
  App braucht ohnehin ihre eigene Oberfläche dafür), aber ja für den
  Mechanismus dahinter: sonst müsste jede App (auch TME), die die
  Schnittstelle nutzt, das Neu-Rendern korrigierter Regionen selbst
  nachbauen.

  Umgesetzt: neues drittes Kommando `correct` (kein OCR, kein
  Provider-Aufruf, kein `--config` nötig) - headless-Äquivalent zu
  `ui/image_job.py::run_image_correction_job()`. `translate`s Report
  enthält jetzt pro Bild zusätzlich `regions` (`image_translate_cli/
  report.py::RegionRecord` - Position, Originaltext, übersetzter Text je
  erfolgreich übersetzter Region, additives Feld, keine
  `REPORT_SCHEMA_VERSION`-Erhöhung nötig). Ein Aufrufer entnimmt diese
  Liste, lässt `translated_text` (optional auch Position/Größe) in seiner
  eigenen Oberfläche bearbeiten, und übergibt sie unverändert in der Form
  an `correct --regions` - das rendert gegen die pristine Quelle neu.
  `correct`s eigener Report enthält wieder eine frische `regions`-Liste,
  direkt einsetzbar für eine weitere Korrekturrunde.

  End-to-End getestet: `translate` mit Fake-Provider erzeugt eine
  Region mit Originaltext/übersetztem Text; diese Liste als
  `--regions`-Datei manuell editiert (übersetzten Text geändert); `correct`
  rendert exakt den korrigierten Text neu, Report zeigt den korrigierten
  Stand. Fehlerpfade geprüft: fehlende Quelldatei, fehlerhaftes
  Regions-JSON (fehlende Pflichtfelder, kein Array), `--source`==`--output`,
  unbekanntes `--inpainting-backend` - alle mit Exit-Code 2 und klarer
  Meldung statt Absturz. Bekannte Grenze dokumentiert (CLI.md "Bekannte
  Grenzen"): `correct` kann nur bereits erfolgreich übersetzte Regionen
  bearbeiten, keine wegen niedriger OCR-Konfidenz übersprungenen oder
  fehlgeschlagenen nachträglich hinzufügen - dafür müsste erneut
  `translate` laufen. Details: CLI.md, neuer Abschnitt "Workflow:
  Vorschau, Korrektur, Ergebnis" und "`correct` - Bild mit bearbeiteten
  Regionen neu rendern".

  **Nachtrag 3 (22.08.2026, Michael: "Ich möchte aber gerne die Korrektur
  Logik mit UI auslagern. Ansonsten muss jede App das gleiche nochmal
  bauen."):** `correct` (Nachtrag 2) löst nur den Re-Render-Mechanismus,
  nicht die Korrektur-OBERFLÄCHE selbst - jede aufrufende App müsste die
  weiterhin eigenständig bauen. Diskutiert (nativ eingebettet via
  PySide6-Widget vs. lokale Web-UI im Browser); Michael entschied sich für
  die Browser-Variante, nachdem geklärt war, dass TME auf absehbare Zeit
  NICHT serverbasiert wird, sondern weiterhin auf demselben Rechner läuft
  - Auth/Hosting damit vorerst kein Thema.

  Umgesetzt: neues viertes Kommando `review`, das `correct`s Re-Render
  UND die Korrektur-Oberfläche in einem Aufruf abdeckt. Startet einen
  lokalen `http.server.ThreadingHTTPServer` (Standard: `127.0.0.1`, kein
  Netzwerkzugriff von außen, keine Authentifizierung - siehe CLI.md,
  Abschnitt "review", Unterabschnitt "Sicherheit"), öffnet automatisch
  einen Browser-Tab mit einer selbstständigen HTML/CSS/JS-Seite (kein
  Build-Schritt, kein CDN, kein Framework) auf der das Originalbild mit
  den übersetzten Textregionen als verschiebbare/skalierbare/editierbare
  Boxen überlagert angezeigt wird (Pointer Events statt reiner
  Maus-Events - funktioniert damit auch per Touch, relevant falls die
  iPad-Frage aus dem Deployment-Eintrag unten später wieder aufgegriffen
  wird). Nach Klick auf "Anwenden" rendert `review` mit exakt demselben
  `InpaintingBackend.apply()`-Pfad wie `correct` neu; "Abbrechen" beendet
  ohne Ausgabedatei (Exit-Code 3, neu). Geteilte Regionen-Validierung
  (`x`/`y`/`width`/`height`/`translated_text` Pflicht) aus `cli.py` in ein
  neues `image_translate_cli/regions_io.py` gezogen, damit `correct`
  (Datei-Pfad) und `review` (Browser-POST-Pfad) dieselbe Prüfung teilen
  statt zweier Kopien, die auseinanderlaufen könnten.

  Bewusst NICHT umgesetzt: Regionen im Browser hinzufügen/löschen (nur
  Text/Position/Größe der von `translate` gelieferten Regionen editierbar
  - dieselbe Grenze wie bei `correct`, siehe CLI.md "Bekannte Grenzen"),
  Live-Neu-Rendering bei jeder Änderung (die Browser-Vorschau ist eine
  Textbox-Overlay-Annäherung, kein echter Inpainting-Durchlauf pro
  Tastendruck).

  End-to-End lokal getestet (Sandbox): Server startet, `GET /`/`/api/state`/
  `/api/image` liefern korrekt (inkl. Content-Type des Bildes);
  `POST /api/apply` mit gültigem Payload beendet den Prozess mit Exit-Code
  0, korrektem Report (`"command": "review"`) und neu gerendertem Bild;
  `POST /api/apply` mit unvollständigem Payload liefert `400` mit
  Klartext-Fehler UND lässt den Server weiterlaufen (kein Absturz, Nutzer
  kann im Browser korrigieren und erneut senden); `POST /api/cancel`
  beendet mit Exit-Code 3, keine Ausgabedatei; `correct` nach dem Umbau
  (gemeinsames `regions_io.py`) erneut regressionsgetestet - unverändertes
  Verhalten inkl. Fehlerpfade. Details: CLI.md, neuer Abschnitt "review -
  Bild interaktiv im Browser korrigieren und neu rendern".

  Beobachtung, direkt relevant für die Deployment-Entscheidung unten (noch
  NICHT dort umgesetzt, siehe die dortige Ergänzung): der hier gebaute
  lokale Server + Browser-Ansatz ist etwas anderes als die dort bereits
  verworfene "Web-App" (die brauchte Hosting/eigene Zugangsdaten-
  Architektur) - hier läuft der Server nur lokal, keine Internetanbindung
  nötig, gleiches Vertriebsmodell wie ein normaler Installer heute. Nicht
  im Rahmen dieses Punkts weiterverfolgt, siehe Vermerk bei
  "Deployment-Lösung".

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

  **Klarstellung (22.08.2026):** ausdrücklich entkoppelt von der
  Bildübersetzungs-Schnittstelle für TME (siehe "Geplant" oben) - TME läuft
  vorerst auf demselben Rechner und braucht dafür keinen eigenständigen
  Standalone-Build. Die frühere Überlegung, beide Standalone-Bauten
  zusammenzulegen, gilt nur, falls TME später tatsächlich eigenständig
  laufen muss, nicht als aktuelle Abhängigkeit.

  **Wiedervorlage (22.08.2026):** Im Rahmen von `review` (siehe "Geplant"
  oben, Nachtrag 3 zum Bildübersetzungs-Schnittstelle-Punkt) wurde für die
  Korrektur-UI ein lokaler HTTP-Server + Browser-Seite gebaut, statt eines
  nativen PySide6-Dialogs. Das ist NICHT dieselbe Web-App-Option, die am
  18.08.2026 verworfen wurde (die brauchte Hosting/eine eigene
  Zugangsdaten-Architektur für mehrere Nutzer) - hier läuft der Server rein
  lokal (`127.0.0.1`), kein Internet, kein zusätzliches Zugangsdaten-
  Konzept, gleiches Vertriebsmodell wie ein normaler Installer.

  Das öffnet einen bisher nicht bedachten Weg für die iPad-Frage: Falls die
  ganze App (nicht nur die Bildkorrektur) irgendwann als lokaler Server +
  Browser-Oberfläche liefe, könnte die schwere Rechenarbeit (Tesseract,
  GPU-Inpainting) weiterhin auf einem "echten" Rechner laufen, während JEDES
  Gerät mit Browser im selben Netz - auch ein iPad - nur als Anzeige/
  Fernbedienung dient, ohne dass iPadOS selbst den PySide6/Tesseract-Stack
  tragen müsste. Das wäre eine dritte Option neben "native Installer" und
  "gehostete Web-App", mit anderen Kompromissen als beide.

  Ausdrücklich NICHT hiermit entschieden: das ist eine Weichenstellung für
  die GANZE App, nicht nur für die Bildkorrektur, und reißt die
  18.08.2026-Entscheidung (native Installer-Route) nicht automatisch wieder
  auf. Bewusst als offener Punkt für eine spätere, eigene Diskussion
  festgehalten statt sie nebenbei mitzuentscheiden - siehe Michael dazu
  befragen, sobald die Deployment-Frage wieder aktiv angegangen wird.

  **Update (26.08.2026) - Abhängigkeitsstrategie für den Installer
  geklärt, Umsetzung weiterhin nicht begonnen:** Michael, zum Einstieg:
  "Jetzt zum Installer. Wo stehen wir da?" - Rückfrage ergab, dass er
  zuerst die Abhängigkeitsfrage ausgearbeitet haben möchte, bevor
  irgendetwas gebaut wird (siehe unten für den vollen Rechercheteil).

  Ausgangslage aus der Recherche: Auto-Erkennung + Inline-Hinweis für
  fehlende optionale Abhängigkeiten ist bereits vollständig gebaut und
  läuft unabhängig davon, ob die App aus dem Quellcode oder als
  gebündelter Installer läuft - `pipeline.images.ocr.
  tesseract_available()`, `pipeline.registry.ocr_engine_available()`/
  `inpainting_backend_available()`, `pipeline.images.inpainting.
  gpu_inpainting_available()`. Offen war nur, WAS bei einer fehlenden
  Abhängigkeit im Installer-Kontext konkret passieren soll - je nach
  Abhängigkeit technisch unterschiedlich beantwortet:

  1. **Tesseract-Binary** (kein Python-Paket, System-Programm) -
     **Entscheidung: wird direkt in den jeweiligen Plattform-Installer
     mit reingepackt** (PyInstaller kann beliebige Binärdateien
     mitbündeln), statt nur auf einen externen Installer zu verlinken.
     Kostet geschätzt ~30-70 MB je nach Sprachpaketen, aber kein
     Mehraufwand beim Bauen selbst, da Windows/macOS/Linux ohnehin
     getrennt gebaut werden müssen (siehe 18.08.2026-Eintrag oben).
  2. **pytesseract + opencv-python-headless** (`requirements-ocr.txt`,
     reine, moderat große Python-Pakete) - vorgeschlagen, immer mit zu
     bündeln, unabhängig von Punkt 1 (Michael nicht widersprochen, aber
     auch nicht explizit einzeln bestätigt - beim nächsten Anfassen des
     Themas kurz gegenchecken).
  3. **PaddleOCR** (`requirements-paddleocr.txt`, mehrere hundert MB
     inkl. Modelle) **und GPU-Inpainting** (`requirements-gpu.txt`,
     torch/CUDA, GB-Bereich, muss laut der eigenen Anleitung dort
     ohnehin von Hand zur passenden CUDA-Version installiert werden) -
     beide sprengen Michaels Größenziel klar, bleiben deshalb NICHT im
     Basis-Download. Michael: "Es sollte eine Möglichkeit geben das bei
     der Installation ausgewählt werden kann ob man das mit runterladen
     möchte, also selbst runterladen, nicht mit im Installer oder gar
     nicht erst installieren. Mit Hinweis was das bedeutet." -
     **Entscheidung: eine Komponenten-Auswahl direkt im nativen
     Setup-Assistenten** (Windows/macOS/Linux, mit Erklärtext zu Größe/
     Internetbedarf/Zweck), NICHT als In-App-Nachinstallation nach dem
     ersten Start. Ausdrücklich gegen die einfachere Alternative
     entschieden (In-App-Download-Button, plattformunabhängig, nutzt
     die bereits vorhandene Erkennungs-/Hinweis-Logik direkt weiter) -
     Michael wurde der Mehraufwand genannt (für jede Plattform ein
     eigenes natives Installer-Toolkit mit eigener Download-Logik
     während der Installation, z. B. Inno Setup unter Windows, dreimal
     separat zu pflegen statt einmal in der plattformunabhängigen
     PySide6-App), hat sich aber bewusst dafür entschieden.

  Weiterhin unverändert offen (siehe 18.08.2026-Eintrag oben): ob
  Michael die Windows/macOS-Builds selbst auf seinen Geräten baut, oder
  eine CI-Pipeline das übernehmen soll - diese Entscheidung betrifft
  jetzt zusätzlich die Wahl des Installer-Toolkits je Plattform (das für
  Punkt 3 die Download-während-Setup-Logik tragen muss), ist aber noch
  nicht Teil dieses Updates gewesen. Umsetzung nach wie vor nicht
  begonnen - noch kein einziger Build (auch kein Linux-Build) erstellt.

  **Update (26.08.2026, direkt im Anschluss) - Build-Strategie geklärt,
  dabei die Architektur selbst noch einmal aufgerollt:** Michael zur
  Build-Hardware-Frage: "Im Moment habe ich nur Zugriff auf Linux. Auf
  einen MacOS werde ich voraussichtlich keinen haben. Deswegen war ja
  auch ein Web-Ansatz gedacht." Repo liegt bereits auf GitHub - CI
  (GitHub Actions mit `windows-latest`/`macos-latest`/`ubuntu-latest`-
  Runnern) würde das reine BAUEN ohne eigene Windows/macOS-Hardware
  lösen, aber nicht das Testen auf echter Hardware - dieser Unterschied
  wurde Michael erklärt, bevor er sich entschied.

  Zur Klärung, was "Web-Ansatz" konkret heißen soll, wurden die beiden
  im 22.08.2026-Eintrag oben bereits unterschiedenen Varianten noch
  einmal explizit gegenübergestellt: **lokaler Server + Browser-UI**
  (bleibt komplett lokal, löst das Test-Problem NICHT - das
  Python-Backend müsste weiterhin nativ pro Plattform gebaut UND
  getestet werden, nur mit Browser- statt Qt-Oberfläche) vs.
  **vollwertige gehostete Web-App** (löst das Test-Problem wirklich,
  da nur eine von Michael selbst betriebene [Linux-]Instanz existiert,
  aber Dokumente - auch die vertraulichen ICO-PDFs - würden dafür zur
  Verarbeitung hochgeladen statt lokal zu bleiben, plus dauerhafter
  Hosting-Betrieb und Mehrbenutzer-Zugangsdaten-Verwaltung).

  **Entscheidung (Michael, nach dieser Klarstellung):** "Also einen
  Installer der alles auf dem lokalen Browser startet. Also in Richtung
  Lokaler Server + Browser UI, aber auch als App." - also NICHT die
  gehostete Variante (Dokumente bleiben lokal), sondern ein Installer/
  Programm, das lokal einen Server startet und die Oberfläche im
  Browser (oder einer eingebetteten Browser-Ansicht) zeigt. Ausdrücklich
  noch einmal auf die Konsequenz hingewiesen - CI bleibt trotzdem nötig
  (das Backend muss weiterhin pro Plattform gebaut werden), Testen auf
  echter Hardware bleibt trotzdem ungelöst, und es wäre ein kompletter
  UI-Neubau (die gesamte bestehende PySide6/Qt-Oberfläche, inkl. des
  gerade erst fertiggestellten Card-Redesigns vom selben Tag, würde
  durch eine HTML/CSS/JS-Oberfläche ersetzt) - Michael, nach Nennung
  dieser drei Punkte: "Ja, trotzdem umbauen."

  **Umsetzung:** noch nicht begonnen. Nächster Schritt ist eine
  ausführliche Planungsrunde (Architektur: eingebettete Browser-Ansicht
  z. B. via pywebview vs. Start im System-Standardbrowser; wie der
  bestehende PySide6-Job-/Worker-/i18n-/Settings-Code wiederverwendet
  vs. neu gebaut wird; ob die 22.08.2026 bereits gebaute lokale-Server-
  Lösung der Bildkorrektur als Vorbild/Baustein dient), bevor
  irgendeine Zeile Code geändert wird - Umfang und Risiko sind deutlich
  größer als alles bisher in diesem Projekt umgebaute.

- Cross-Projekt: Bildübersetzung als Basis für TME (21.08.2026, Claude per
  Cowork, im Rahmen einer TME-Session geprüft): TME (github.com/MiSte-Git/TME,
  Telegram-Export-Tool desselben Nutzers) hat in seinem eigenen Backlog einen
  offenen Punkt für Bildübersetzung, praktisch identischer Scope zu
  pipeline/images/ hier (kein Font-Matching, kein Vektor-Text-Pfad). Geprüft,
  ob sich das hiesige pipeline/images/ dafür wiederverwenden lässt, statt in
  TME neu zu bauen.

  Ergebnis: pipeline/images/ ist sauber von PDF/Word/PPTX hier entkoppelt
  (einzige externe Abhängigkeit: pipeline.translation.base.TranslationProvider
  als Protocol, kein konkreter Import) - grundsätzlich wiederverwendbar. Eine
  geteilte Python-Bibliothek wurde trotzdem verworfen: TMEs eigene
  Provider-Abstraktion ist `async def` (Telethon-bedingt), pipeline/images/
  hier ruft `provider.translate()` synchron auf - ein direkter Import würde
  einen Adapter brauchen und TME eng an hiesige, noch in Bewegung befindliche
  interne APIs koppeln (siehe "Zu verifizieren"/"Bekannte Einschränkungen"
  oben - Mehrspalten-/Infografik-OCR-Fehllesungen, Cloud-Inpainting fehlt
  noch).

  Stattdessen angedachte Richtung: ein eigenständiges, per Subprocess/CLI
  aufrufbares Bildübersetzungs-Tool auf Basis von pipeline/images/ hier
  (Bildpfad(e) + Config rein, übersetzte Bilder + JSON-Report raus, analog zu
  run_image_batch_job()) - stabile, kleine Schnittstelle statt Kopplung an
  interne APIs, TME bräuchte dann keinen async/sync-Adapter. Das überschneidet
  sich mit der Deployment-Lösung/Entscheidung oben (native Standalone-Route):
  ein solcher Standalone-Build von pipeline/images/ hier könnte derselbe sein,
  der auch als CLI-Baustein für TME dient - beim Angehen der Deployment-Frage
  oben mitdenken. Zurückgestellt bis pipeline/images/ hier stabiler ist
  (siehe "Bildübersetzungs-Modul"-Eintrag oben) - noch nicht begonnen, kein
  Umsetzungsdruck von TME-Seite.

  **Update (22.08.2026):** mit Michael besprochen und priorisiert - konkreter
  nächster Schritt jetzt als aktiver Punkt in "Geplant" oben ("Bildübersetzung
  als eigenständige, in andere Programme einbindbare Schnittstelle bauen").

- PDFs zusammenführen / PDFs zwischeneinfügen als neue, von Übersetzung
  unabhängige Operation (26.08.2026, Michael, im Rahmen der Rückfrage zur
  fehlenden "Übersetzung gewünscht?"-Checkbox aus dem UI-Redesign): "Ja, so
  etwas schwebt mir vor. Falls wir nicht zwingend übersetzen wollen. Ich
  möchte später noch eine Funktion hinzufügen die PDFs zusammenführt und
  auch noch PDFs zwischeneinfügt. Ist so erst angedacht." Ausdrücklich noch
  keine feste Spezifikation, nur eine Richtung: die Motivation für eine
  optionale "keine Übersetzung"-Checkbox im UI ist also nicht in den
  bestehenden Vorgängen (PPTX/Word/PDF/Bilder übersetzen) zu suchen, sondern
  in einem oder mehreren NEUEN "Vorgang"-Einträgen (Merge/Insert), die gar
  keine Übersetzung durchführen. Eine Checkbox "Übersetzung überspringen"
  in den bestehenden Übersetzungs-Vorgängen selbst einzubauen wäre also
  vermutlich der falsche Ansatz (dort gibt es ohne Übersetzung nichts zu
  tun) - naheliegender: Merge/Insert als eigene(r) `mode`-Wert(e) in
  `ui/app.py`s `self.mode`/`MODE_KEYS`, analog zu den bestehenden Vorgängen,
  bei denen dann konsequenterweise die ganzen Übersetzungs-spezifischen
  Formularfelder (Anbieter, Sprachen, geschützte Begriffe, OCR/Inpainting)
  über `_mode_changed()`/`setRowVisible()` ausgeblendet blieben - kein
  Bedarf an einer separaten Checkbox. Zurückgestellt, bis Michael das Merge/
  Insert-Vorhaben konkretisiert (welche Reihenfolge-/Auswahl-UI, ob
  Seitenbereiche pro Quelldatei wählbar sein sollen, Umgang mit
  Formatierung/Bookmarks/Metadaten der Ergebnisdatei) - keine Umsetzung
  begonnen.

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
- [x] Font-Matching (Familie/Fett/Kursiv) + Hintergrund-Farbverlauf für
  BoxOverlayBackend (RoadMap.md Phase 3, "...echte Schrifterkennung
  (Font-Matching) weiterhin offen") - Michael, 22.08.2026, nach einem
  eigenen Google-Translate-Bildvergleich (Original-Infografik als Foto
  hochgeladen, Google lieferte layouttreue Übersetzung "in einer
  Wahnsinns Geschwindigkeit"): "Unser Ansatz hat eine Genauigkeit im
  Layout von vielleicht 60-70%... die sollten wir so wie auf das von
  Google bringen." Vorab per Websuche bestätigt: keine offizielle
  Google-API für Bild-zu-Bild-Übersetzung mit Layout-Rekonstruktion
  existiert (nur Consumer-App-Feature) - "einfach an Google
  weiterreichen" damit keine Option, eigene Pipeline verbessern die
  einzig gangbare Richtung. Michael explizit: "gleich richtig machen,
  wenn es nicht zwingend den pragmatischen Weg vorher braucht" +
  klassische Bildverarbeitung statt eines trainierten ML-Font-
  Klassifikators (keine neue Modell-Abhängigkeit).
  - Neu: `pipeline/images/font_style.py` - eigenständiges Modul,
    ausschließlich für Font-Stil-Erkennung zuständig (keine Rückimport-
    Abhängigkeit von `inpainting.py`, `size` bleibt dafür ein
    Pflichtparameter statt selbst rückgerechnet zu werden).
    `load_font(size, bold=, family=, italic=)` ersetzt/verallgemeinert
    `inpainting.py`s bisheriges `_load_font()` (nur Sans Regular/Bold) um
    Serif und Kursiv/Oblique, 6-stufige Fallback-Kaskade bis zu Pillows
    eingebautem Default-Font. `classify_family()`/`classify_bold()`/
    `classify_italic()`/`estimate_font_style()` nutzen konsequent
    dieselbe RELATIVE Vergleichsmethodik, die `_estimate_is_bold()`
    (21.08.2026) für Fett-Erkennung eingeführt hat: denselben
    Vergleichstext synthetisch in den jeweils in Frage kommenden
    Varianten rendern, dieselbe Kennzahl an beiden messen, die reale
    Region der Variante zuordnen, deren synthetischer Wert näher liegt -
    robust gegen Bild-zu-Bild-Rauschen, weil nur die Reihenfolge zählt,
    nicht der Absolutwert. Neue Kennzahlen: `_serif_score()`
    (Zeilen-Ink-Varianz oben/unten vs. Mitte - Serifen erzeugen an den
    Rändern eine ungleichmäßigere Verteilung), `_slant_ratio()`
    (Bänder-Schwerpunkt-Regression für Kursiv-Neigung). Reihenfolge in
    `estimate_font_style()`: Familie -> Fett -> Kursiv, jede Stufe nutzt
    die vorherige als Vergleichsbasis. Alle drei `InpaintingBackend.apply()`
    (Box-Overlay/CV/GPU) rufen jetzt `estimate_font_style()` statt des
    alten `_estimate_is_bold()`; letzteres bleibt als dünner
    Kompatibilitäts-Wrapper (`family="sans_serif"`) bestehen, bestehende
    Aufrufer/Tests unverändert lauffähig.
  - Bewusst NICHT Teil dieser Runde: Monospace-Erkennung (bräuchte
    zeichenweise statt zeilenweise Segmentierung, die die vorhandene OCR
    nicht liefert) und echte Font-FAMILIEN-Erkennung ("Arial" vs.
    "Helvetica" - optisch ohnehin kaum unterscheidbar) - beides als
    offener Folgepunkt dokumentiert, nicht stillschweigend als erledigt
    behandelt (siehe RoadMap.md-Eintrag).
  - Echter Bug gefunden UND gefixt (nicht nur synthetisch konstruiert):
    ein regulärer pytest-Lauf während der Entwicklung zeigte eine
    plain-DejaVu-Sans-Testzeile fälschlich als "serif" klassifiziert.
    Ursache: die REALE, aus der OCR-Box gecroppte Maske hatte spürbaren
    Leerraum über/unter dem eigentlichen Text (Tesseract-Zeilen-Boxen
    sind nicht eng an die Glyphen gecroppt), während die SYNTHETISCHEN
    Vergleichsmasken bereits eng zugeschnitten waren (`ImageDraw.
    textbbox()`) - dieser Leerraum, nicht die tatsächliche Schriftform,
    dominierte `_serif_score()`s randbasierte Varianzmessung. Fix: neue
    `_trim_to_ink_bbox()` schneidet jede Maske vor `_serif_score()`/
    `_slant_ratio()` auf ihre enge Tinten-Bounding-Box zu (mit einem
    relativen 8%-Rauschboden statt "jedes Pixel zählt" - einzelne
    Antialiasing-Randpixel hätten die Bounding-Box sonst weiterhin
    unvorhersehbar verlängert; auch dieser Rauschboden wurde erst nach
    einem zweiten, breiteren synthetischen Test nötig). Bewusst NICHT
    auf `_ink_ratio()`/Fett-Erkennung angewendet - die bestehende
    Fett-Erkennung funktioniert mit der ungetrimmten Fläche bereits
    zuverlässig (siehe unten, zwei Gegenversuche mit Trimmen dort haben
    das Ergebnis nachweislich verschlechtert).
  - Zwei Verbesserungsversuche gebaut, gemessen und wieder verworfen
    (dokumentiert statt stillschweigend entfernt, siehe Git-Historie von
    `font_style.py` falls das erneut aufgegriffen wird): (1) den
    beobachteten Ink-Ratio-Vergleich in `classify_bold()` ebenfalls auf
    die getrimmte Maske umzustellen - brach den bestehenden, an einem
    echten Bild kalibrierten `_estimate_is_bold()`-Test UND
    verschlechterte eine breitere synthetische Prüfung, sofort wieder
    zurückgebaut. (2) eine `_calibrate_size()`-Vorstufe, die die vom
    Aufrufer übergebene (nur grob geschätzte) Vergleichsgröße anhand der
    beobachteten Tinten-Höhe nachjustiert - verbesserte Familie
    geringfügig, verschlechterte Kursiv-Erkennung aber messbar, in Summe
    kein klarer Gewinn, entfernt.
  - Bekannte, bewusst dokumentierte Grenze (nicht durch obige Versuche
    gelöst): alle drei `classify_*()`-Funktionen rendern ihre
    synthetischen Referenzen bei der vom Aufrufer übergebenen Größe -
    normalerweise `_initial_font_size(region)`, nur eine grobe
    `region.height * 0.8`-Schätzung. Eine breite synthetische Text/
    Größe/Stil-Matrix (mehrere Texte x drei Größen x alle Stil-
    Kombinationen, realistisch verrauschte statt exakt passende
    Größenschätzung) ergab bei exakt passender Größe 100% Trefferquote,
    bei realistisch abweichender Schätzung nur rund 60-65% je Achse -
    siehe `font_style.py`s Moduldoc, Abschnitt "Bekannte Grenze".
  - Hintergrund-Rekonstruktion: `BoxOverlayBackend` füllte jede Box
    bisher IMMER einfarbig (ein flacher `draw.rectangle(fill=...)`),
    selbst wenn die Umgebung sichtbar einen Farbverlauf zeigte -
    passend zu Michaels "die sollten wir so wie auf das von Google
    bringen". Neu in `inpainting.py`: `GradientBackground`-Dataclass
    (Achse vertikal/horizontal, zwei Farb-Stopps), `_sample_background()`
    sampelt die vier Rand-Streifen (oben/unten/links/rechts) getrennt
    statt sie wie bisher `_sample_background_color()` zu einer einzigen
    Durchschnittsfarbe zu mitteln, und erkennt einen Verlauf, sobald die
    euklidische RGB-Distanz zwischen zwei gegenüberliegenden Streifen
    `_GRADIENT_DETECTION_THRESHOLD` (18.0, bewusst konservativ - im
    Zweifel eher die bisherige einfarbige Füllung als ein
    falscher/unnötiger Verlauf) übersteigt - sonst weiterhin die
    bisherige einfarbige Füllung (abwärtskompatibel). `_fill_gradient_rect()`
    füllt zeilen-/spaltenweise per linearer Interpolation (keine neue
    Abhängigkeit über das bereits vorhandene Pillow hinaus).
    `_representative_color()` liefert weiterhin eine einzelne Farbe
    (Mittelpunkt der beiden Stopps) für Textkontrast-Entscheidung und
    Font-Stil-Schätzung. Bewusst nur horizontale/vertikale Zwei-Stopp-
    Verläufe, keine diagonalen/radialen (deutlich mehr Sampling-Aufwand
    für den selteneren Fall) - `CvInpaintingBackend`/`GpuInpaintingBackend`
    betrifft das nicht, die rekonstruieren Hintergründe (inkl. Verläufe)
    bereits über echtes Inpainting.
  - Getestet: neue `tests/test_font_style.py` (31 Tests - `load_font()`-
    Fallback-Kaskade inkl. eines erzwungenen Total-Fallbacks via
    monkeypatch, `_trim_to_ink_bbox()` inkl. des Rauschboden-Falls,
    `_resolve_sample_text()`, alle vier `classify_*()`/
    `estimate_font_style()` in beide Richtungen je Achse plus Default-
    Fälle ohne Vergleichstext). Neue Gradient-Tests in
    `tests/test_image_inpainting.py` (8 Tests - Verlauf-Erkennung
    vertikal/horizontal, flacher Hintergrund bleibt flach,
    `_fill_gradient_rect()` direkt gegen Pixelwerte inkl. Monotonie-
    Check, End-to-End durch `BoxOverlayBackend.apply()` inkl. echtem
    Tesseract-OCR-Roundtrip). Ein OCR-Roundtrip-Test mit der Region
    exakt am Helligkeits-Umschlagpunkt des Verlaufs (Luminanz ~128)
    scheiterte zunächst NICHT wegen eines Rendering-Bugs, sondern weil
    Tesseracts eigene Binarisierung dort komplett leer zurückkam, obwohl
    der Text visuell erkennbar blieb (per Bild-Inspektion bestätigt) -
    Region im Test auf eine eindeutig kontrastreiche Position verschoben,
    mit Begründung im Test-Docstring dokumentiert statt stillschweigend
    "repariert". Bestehende `_load_font`/`_estimate_is_bold`/
    `_sample_background_color`-Importe/Tests in `tests/test_image_
    inpainting.py` unverändert lauffähig (Kompatibilitäts-Wrapper hält).
    Gesamter Testlauf am Ende: 102 passed, 1 skipped (GPU-Hardware-
    abhängiger Test, wie zuvor).
- **Bildübersetzung/OCR - dekorative Icon-Glyphen als OCR-Wortmüll
  gefiltert, QA-Bericht zeigt jetzt die tatsächlich benutzten
  Einstellungen (22.08.2026):** Michael: "Das Ergebnis ist immer noch
  eher bei 60-70% und immer noch nicht wirklich brauchbar. [...] Ich
  habe es hier mit echter Hardware getestet und der Option
  GPU-Inpainting (LaMa), und das schon seit Anfang. Wir brauchen
  unbedingt im qa_report.txt auch die Einstellungen mit denen ich es
  getestet habe. Es hört sich so an als wenn wir es noch nie mit der
  App an einem echtem Bild getestet hätten." - korrigierte damit eine
  falsche Annahme meinerseits (GPU-Inpainting sei noch ungetestet) und
  lieferte ein echtes Original ("Spirit - Soul - Meatsuit.jpg") plus
  die reale, sichtbar verunstaltete Ausgabe UND den echten
  `qa_report.txt` dieses Laufs (Anbieter=google, OCR=tesseract,
  Backend=gpu_inpainting, 99 Regionen erkannt, 83 übersetzt, 16
  übersprungen).

  **Diagnose gegen das echte Bild** (nicht synthetisch konstruiert):
  ein direkter Tesseract-Lauf gegen das Original zeigte, dass mehrere
  der auffälligsten Verunstaltungen in der Ausgabe ("©) NATURALLY
  COLLAPSES / ENDS", "@ \_ THE ESSENCE RETURNS.", ") Spirit/Essence",
  "© *") NICHT von Übersetzung oder Zurückschreiben kamen, sondern
  bereits in der OCR-Erkennung entstanden: Tesseract liest kleine
  dekorative Icon-/Bullet-/Checkbox-Grafiken in der Infografik
  wiederholt als eigenständige, rein aus Satzzeichen bestehende
  "Wörter" (z. B. ein Checkbox-Icon → "©)", teils mit hoher
  Einzel-Konfidenz - "©" wurde mit 94.0 erkannt, obwohl inhaltlich
  falsch). Diese Symbol-Wörter werden VOR dem eigentlichen Satz in
  dieselbe Zeile gruppiert, sauber übersetzt (der Übersetzer bekommt
  ja nur den bereits verunstalteten Text) und landen so mitten im
  übersetzten Ergebnis. Da `OcrTextRegion.confidence` der
  ARITHMETISCHE MITTELWERT aller Wort-Konfidenzen einer Zeile ist
  (`_region_from_word_indices()`), reicht ein einzelnes, hoch
  bewertetes Fehllese-Symbol-Wort, um den bestehenden
  `DEFAULT_MIN_OCR_CONFIDENCE`-Schwellwert (40.0) unbemerkt zu
  passieren - ein einfacher Mittelwert→Minimum-Schwellwert-Tausch
  wurde geprüft und wieder verworfen: er hätte an echten Daten
  desselben Bildes neue Fehlalarme erzeugt (z. B. die korrekte
  Überschrift "SPIRIT - SOUL » MEATSUIT" nur wegen eines harmlosen
  "»"/"·"-Satzzeichens mit min=35, oder die korrekte Bildunterschrift
  "Origin Silence." mit min=23).

  Behoben durch einen inhaltsbasierten (nicht konfidenzbasierten)
  Filter in `pipeline/images/ocr.py`: `_is_decorative_symbol_token()`
  verwirft ein Tesseract-Wort-Token bereits VOR der Gruppierung zu
  `OcrTextRegion`s, wenn es AUSSCHLIESSLICH aus Zeichen der neuen
  `_DECORATIVE_SYMBOL_CHARS`-Menge besteht (an echten Beispielen
  desselben Bildes kalibriert). Bewusst NICHT enthalten: `+ / - = & >
  < »` - alle im selben echten Bild an anderer Stelle als legitime,
  eigenständige Zeichen bestätigt. Eine (block, par, line)-Gruppe, die
  nach dem Filtern keine Wörter mehr übrig hat, wird schlicht gar
  keine Region mehr (z. B. die reine "© *"-Zeile verschwindet
  komplett). Verifiziert direkt gegen das echte Originalbild: Anzahl
  Regionen 99 → 96, bestätigte Fixes u. a. "@ Contains:" →
  "Contains:", ") Spirit/Essence" → "Spirit/Essence", "©) NATURALLY
  COLLAPSES / ENDS" → "NATURALLY COLLAPSES / ENDS". Bewusst NICHT
  behoben (dokumentierte, absichtliche Lücke): ein Symbol MITTEN in
  einem echten Wort (z. B. "@SSence" im echten Bild) - deutlich
  riskanter, ein Token teilweise statt komplett zu verwerfen, bleibt
  offen.

  **Noch offen, als Ursache identifiziert, aber NICHT in diesem
  Durchgang behoben:** `translate_image()` übergibt an
  `InpaintingBackend.apply()` ausschließlich `stats.replacements`
  (erfolgreich übersetzte Regionen) - übersprungene/fehlgeschlagene
  Regionen sind für `_vertical_room_below()`s Kollisionsvermeidung in
  `inpainting.py` komplett unsichtbar, sodass neu eingefügter Text in
  die noch sichtbaren Original-Pixel einer übersprungenen Region
  hineinwachsen kann - ein wahrscheinlicher Mitverursacher der
  optischen Unordnung im gemeldeten Bild. Braucht eine
  Signaturänderung über alle drei Backends
  (`BoxOverlayBackend`/`CvInpaintingBackend`/`GpuInpaintingBackend`),
  `translate_image.py` und `ui/image_job.py` - bewusst als separater,
  noch nicht umgesetzter Folgepunkt dokumentiert statt nebenbei
  mitgelöst.

  **QA-Bericht zeigt jetzt die echten Lauf-Einstellungen** (Michaels
  expliziter Wunsch): `ui/image_job.py::_build_qa_report()` druckt
  zusätzlich zu Anbieter/Sprache/OCR-Engine/Backend jetzt auch
  `ocr_language`, `min_confidence`, `max_height_ratio`,
  `protected_terms` und `max_chars_per_run` - alle bereits vorher als
  lokale Werte in `run_image_job()` vorhanden, aber bisher nie im
  Bericht gelandet. Zusätzlich fehlte in
  `_INPAINTING_BACKEND_LABELS` bisher der Eintrag für
  `"gpu_inpainting"` - der Bericht zeigte deshalb den rohen internen
  Schlüssel statt eines lesbaren Labels (genau wie im echten,
  gemeldeten `qa_report.txt` zu sehen: "Rückschreibe-Backend:
  gpu_inpainting"), jetzt ergänzt ("GPU-Inpainting (LaMa), Hintergrund
  rekonstruiert)").

  Getestet: `tests/test_image_ocr.py` um 5 neue Tests erweitert (2
  reine Unit-Tests für `_is_decorative_symbol_token()`, 3
  Tesseract-Integrationstests inkl. eines Tests, der ausdrücklich
  bestätigt, dass der Mixed-Symbol-Fall UNVERÄNDERT bleibt). Vor dem
  Versand frisch von `tests/test_image_job.py`,
  `tests/test_image_batch_job.py`, `tests/test_image_correction_job.py`
  vom Gerät nachgeladen (waren in dieser Sandbox noch nicht vorhanden)
  und mitlaufen lassen - keine Signatur-Bruchstelle durch die
  zusätzlichen `_build_qa_report()`-Parameter. Gesamter Testlauf am
  Ende: 121 passed, 1 skipped (GPU-Hardware-abhängiger Test, wie
  zuvor; `tests/test_ui_images_mode.py` in dieser Sandbox nicht
  ausführbar, da `ui/app.py`/Qt hier nicht vorhanden ist - separat auf
  dem Gerät mit vollem Testlauf zu bestätigen).
- **Bildübersetzung/OCR - Kollisionsvermeidung für übersprungene/
  fehlgeschlagene Regionen ergänzt, ECHTE Grenze der Verbesserung
  direkt am Nutzerbild verifiziert (22.08.2026):** Michael, nachdem er
  die Frage zum GPU-Inpainting-Status beantwortet bekam: "Ja, bitte."
  (auf das Angebot, den in der vorherigen Diagnose bereits benannten
  Folgepunkt anzugehen). Löst den in `_vertical_room_below()`s
  Docstring bis dahin dokumentierten bekannten Lücke: `translate_image()`
  übergab an `InpaintingBackend.apply()` bisher ausschließlich
  `stats.replacements` (erfolgreich übersetzte Regionen) - eine
  übersprungene (niedrige Konfidenz/Ausreißer-Höhe), fehlgeschlagene
  (Anbieterfehler) oder wegen `should_cancel` nie erreichte Region zeigt
  im Ergebnisbild trotzdem weiterhin ihre ORIGINALEN, unveränderten
  Pixel - war für die Kollisionsvermeidung aber unsichtbar, sodass eine
  benachbarte übersetzte Region ungehindert in sie hineinwachsen konnte.

  Behoben durch einen neuen `obstacle_regions`-Parameter auf
  `InpaintingBackend.apply()` (alle drei Implementierungen -
  `BoxOverlayBackend`/`CvInpaintingBackend`/`GpuInpaintingBackend` -
  sowie das `Protocol` selbst), den jede `apply()`-Implementierung in
  die an `_vertical_room_below()` übergebene Regionsliste einfließen
  lässt, OHNE diese Regionen selbst zu zeichnen oder (bei
  `CvInpaintingBackend`/`GpuInpaintingBackend`) in die
  Inpainting-Maske aufzunehmen - eine übersprungene Region bleibt exakt
  so unangetastet wie zuvor, zählt aber jetzt als echter Nachbar.
  `translate_image()` berechnet `obstacle_regions` selbst: jede Region
  aus `stats.regions`, die NICHT (per `id()`, da `OcrTextRegion` nicht
  hashbar ist und Regionsobjekte zwischen `regions` und
  `stats.replacements` unverändert wiederverwendet werden) in
  `stats.replacements` auftaucht - deckt alle drei Ursachen (übersprungen/
  fehlgeschlagen/durch Abbruch nie erreicht) in einem einzigen,
  einheitlichen Mechanismus ab, ohne einen weiteren Stats-Feld-Typ
  einzuführen. `run_image_correction_job()` (der direkte
  `apply()`-Aufruf des Korrektur-Dialogs) übergibt bewusst weiterhin
  KEINE `obstacle_regions` - seine `replacements`-Liste ist bereits die
  vollständige, vom Nutzer freigegebene Endmenge, siehe
  `InpaintingBackend.apply()`s Docstring für die Begründung.

  Getestet: 9 neue Tests. `tests/test_image_inpainting.py` (3 Tests,
  `BoxOverlayBackend`) - ein Kontroll-Test reproduziert absichtlich das
  ALTE Verhalten (ohne `obstacle_regions` überschreibt eine lange
  übersetzte Zeile eine echte Nachbarzeile - Fixture-Koordinaten UND
  erwartetes Ergebnis vorab direkt am echten `apply()`-Aufruf verifiziert,
  nicht nur von Hand durchgerechnet, da `_fit_text()`s diskrete
  Schriftgrößen-Stufen die tatsächlich gewählte Größe/Zeilenzahl nicht
  offensichtlich vorhersehbar machen), der zweite Test beweist den Fix am
  selben Fixture (nur `obstacle_regions` unterschiedlich), der dritte
  sichert Rückwärtskompatibilität (Aufruf ganz ohne den neuen Parameter).
  `tests/test_image_cv_inpainting.py` (2 Tests, `CvInpaintingBackend`) -
  zusätzlich ein expliziter Test, dass eine `obstacle_region` NIE in die
  `cv2.inpaint()`-Maske aufgenommen wird (ihre Pixel dürfen nicht
  rekonstruiert werden - nur die Platzierung der ECHTEN Übersetzung darf
  sich nach ihr richten). `tests/test_translate_image.py` (4 Tests,
  neuer `_RecordingBackend`, der `apply()`s Argumente ohne echtes
  Bild-Rendering aufzeichnet) - je ein Test für übersprungen/
  fehlgeschlagen/durch Abbruch nie erreicht, plus ein Test, dass
  `obstacle_regions` leer bleibt, wenn alles übersetzt wurde. Gesamter
  Testlauf am Ende: 130 passed, 1 skipped (vorher 121 passed, 1
  skipped).

  **Ehrliches Ergebnis nach Verifikation am ECHTEN Nutzerbild (nicht nur
  synthetisch) - dieser Fix reicht bei diesem Bild NICHT annähernd aus:**
  ein voller `translate_image()`-Lauf gegen "Spirit - Soul -
  Meatsuit.jpg" (echtes Tesseract-OCR, `BoxOverlayBackend`, ein
  Fake-Provider der jedem Text nur " [DE]" anhängt, damit Original vs.
  Veränderung eindeutig unterscheidbar bleibt) lief fehlerfrei durch (82
  übersetzt, 14 übersprungen, 0 fehlgeschlagen), aber das Ergebnisbild
  zeigt weiterhin deutliche Überlappungen - u. a. im rechten
  "THE CHALICE'S ROLE"/Prozess-Kasten, im "DISTORTION 1s"/"KEY
  TRUTH"-Bereich, und mehreren Stellen mit dicht gedrängten
  Aufzählungspunkten. Diagnose: das jetzt behobene Problem
  (übersetzt-vs-übersprungen) war real, aber NICHT die Hauptursache der
  von Michael beschriebenen "Boxen überlappen" auf diesem Bild - die
  sichtbaren Überlappungen entstehen überwiegend zwischen ZWEI
  ÜBERSETZTEN Regionen, die bereits vorher hätte kollisionsvermieden
  werden müssen (das war nie Teil der bisher dokumentierten Lücke).
  `_vertical_room_below()` betrachtet nur die NÄCHSTE Region unterhalb in
  derselben horizontalen Bande (x-Bereichs-Überlappung) - bei einem
  dicht gepackten Mehrspalten-Infografik-Layout mit vielen kleinen,
  eng benachbarten Boxen ist diese Heuristik (kalibriert an einem
  EINZELNEN früheren Bild, siehe deren Docstring) offenbar nicht mehr
  ausreichend. Nicht in diesem Durchgang untersucht, klar als nächster
  Diagnose-Schritt offen: ob die x-Bereichs-"gleiche-Bande"-Prüfung bei
  diesem Layout falsch positive/negative Nachbarschaften erzeugt, ob die
  Schrumpf-Untergrenze (`_MIN_FONT_SIZE = 9`) für so viele kurze,
  dicht stehende Zeilen zu grob ist, oder ob ein grundsätzlich anderer
  Ansatz (z. B. ALLE Regionen gemeinsam statt nacheinander unabhängig
  platzieren) für diese Art Layout nötig ist. Screenshot des vollen
  Testlaufs an Michael geschickt, damit die Einschätzung nicht nur auf
  Textbeschreibung beruht.
- **Bildübersetzung/OCR - Absatzweise Zusammenführung eng benachbarter
  OCR-Zeilen vor der Übersetzung, deutlicher Fortschritt am ECHTEN Bild
  bestätigt (22.08.2026):** Michael, nach dem ehrlichen Befund oben ("die
  sichtbaren Überlappungen entstehen überwiegend zwischen zwei
  übersetzten Regionen"): "Ja, bitte nächsten Punkt angehen."

  **Diagnose** (echten `translate_image()`-Lauf gegen "Spirit - Soul -
  Meatsuit.jpg" instrumentiert, `_fit_text()`/`_vertical_room_below()`
  live mitgeloggt, nicht geraten): `pipeline/images/ocr.py` erkennt Text
  auf TESSERACT-ZEILEN-Ebene - ein `OcrTextRegion` pro physischer Zeile.
  Ein normaler, über zwei Zeilen umgebrochener Satz ("Operates outside of
  time" / "and sequence.") wird dadurch als ZWEI unabhängig übersetzte
  und unabhängig zurückgeschriebene Regionen behandelt, nur durch den
  ursprünglichen (englischen) Zeilenabstand getrennt - 4 bis 13px im
  echten Bild. Für eine LÄNGERE deutsche Übersetzung ist das nahezu kein
  Platz, selbst wenn die jeweils NÄCHSTE Zeile (dank des
  `obstacle_regions`-Fixes) korrekt als Kollisions-Hindernis erkannt
  wird - denn diese "nächste Zeile" ist ja selbst Teil desselben Satzes
  und wird ihrerseits ebenfalls übersetzt und verschoben. Von 82
  übersetzten Regionen im echten Lauf benötigten 48 mehr Platz, als
  `_vertical_room_below()` ihnen geben konnte - damit als die
  dominierende Ursache der noch sichtbaren Überlappungen bestätigt, nicht
  die vom vorherigen Fix bereits geschlossene Lücke.

  **Fix:** vor der Übersetzung werden aufeinanderfolgende Original-Zeilen,
  die mit hoher Wahrscheinlichkeit derselbe umgebrochene Satz/dieselbe
  Aufzählung sind, zu EINER Übersetzungs-/Layout-Einheit
  zusammengefasst - neu `pipeline/images/ocr.py::merge_lines_into_
  paragraphs()`/`merge_region_group()`: gleiche Spalte (horizontale
  Überlappung), ein KLEINER vertikaler Abstand relativ zur eigenen
  Zeilenhöhe (normaler Zeilenabstand, nicht der größere Abstand vor
  einer neuen Aufzählung/einem neuen Absatz) UND eine ÄHNLICHE
  Zeilenhöhe (gleiche Schriftgröße - eine Überschrift direkt gefolgt von
  einer kleineren Textzeile hat oft ebenfalls einen kleinen Abstand,
  darf aber niemals zusammengefasst werden; genau dieser Fall wurde am
  echten Bild als konkreter Fehlversuch gefunden - siehe unten). Wird als
  EIN Übersetzungsaufruf gesendet (besserer Kontext, nicht nur besseres
  Layout) und als EIN wortumbrochener Block gegen die UNION der
  zusammengeführten Bounding-Boxen gezeichnet.

  Neues `OcrTextRegion.line_height`-Feld (Default `None`, rückwärts-
  kompatibel): eine zusammengeführte Region hat eine `height`, die den
  GESAMTEN mehrzeiligen Block umspannt (nötig für die
  Kollisionsvermeidung), aber `pipeline/images/inpainting.py::
  _initial_font_size()` braucht für eine sinnvolle Start-Schriftgröße die
  Höhe EINER Zeile, nicht die des ganzen Blocks - sonst würde ein
  zusammengeführter Absatz in einer viel zu großen Schrift gerendert.
  `_initial_font_size()` nutzt jetzt `line_height`, wenn gesetzt.

  `translate_image()` zählt `stats.translated`/`stats.failed` weiterhin
  in ORIGINAL-Zeilen-Einheiten (nicht in zusammengeführten Blöcken) -
  `stats.processed` bleibt unverändert gleich der Anzahl erkannter
  Regionen. Die `obstacle_regions`-Berechnung (voriger Fix) wurde
  entsprechend angepasst: eine zusammengeführte Ersatz-Region ist jetzt
  ein KOMPLETT NEUES Objekt (nicht mehr identisch mit einer
  Original-Region), daher wird jetzt über die tatsächlich in einer
  erfolgreich übersetzten Gruppe enthaltenen Original-Regionen verfolgt,
  welche Zeilen als Hindernis zählen müssen.

  **Kalibrierung direkt am echten Bild** (nicht geraten): nur Regionen,
  die bereits `min_confidence` bestehen, kommen als Zusammenführungs-
  Kandidaten infrage (ungefiltert probiert, führte zu Unsinns-
  Zusammenführungen mit niedrig-konfidenten OCR-Fehllesungen wie
  "peepee"/"aE" - verworfen). Abstand-Schwellwert 0.6× eigene Zeilenhöhe
  und Höhen-Ähnlichkeit min. 0.6 (kleinere/größere Zeilenhöhe) ergaben 18
  saubere Zusammenführungen aus 82 echten Regionen - jede einzelne
  manuell geprüft, keine einzige davon fasst inhaltlich unzusammen-
  gehörige Fragmente zusammen. Ohne die Höhen-Ähnlichkeits-Prüfung wurden
  zwei konkrete Fehlversuche gefunden und durch diese Prüfung behoben:
  die kleine Eyebrow-Beschriftung "SPIRIT - SOUL » MEATSUIT" (Höhe 37)
  wurde fälschlich mit der viel größeren Hauptüberschrift "HOW THE
  CHALICE RESTORES..." (Höhe 20) direkt darunter zusammengeführt, ebenso
  die Sidebar-Überschrift "THE CHALICE'S ROLE" (Höhe 28) mit der ersten
  Aufzählungszeile darunter (Höhe 12) - beide durch die
  Höhen-Ähnlichkeits-Prüfung jetzt korrekt getrennt gehalten.

  **Ergebnis am echten Bild, vorher/nachher (gleicher Fake-Provider,
  " [DE]"-Suffix, damit Original vs. Änderung eindeutig bleibt):** 82
  übersetzte Regionen wurden zu 59 Übersetzungs-/Zeichenblöcken
  zusammengefasst (18 echte Zusammenführungen). Blöcke, die ihren
  berechneten Platz überschreiten (`_fit_text()` live mitgeloggt): 48 von
  82 vorher -> 26 von 59 nachher - eine deutliche, messbare Verbesserung,
  visuell im Screenshot bestätigt: der komplette linke Hauptbereich (alle
  drei Aufzählungs-Blöcke unter "SPIRIT/ESSENCE", "SOUL/LEDGER/TIMELINE",
  "MEATSUIT/BODY/IDENTITY") ist jetzt sauber lesbar ohne Überlappungen,
  ebenso "THE CHALICE PROCESS"-Kasten rechts (vorher fast komplett
  unleserlich).

  **Ehrlich weiterhin offen:** einzelne Überlappungen bleiben bestehen,
  v. a. im dichtesten rechten Randbereich ("THE CHALICE'S ROLE"-Kasten:
  "Extracts, separates," überlappt weiterhin mit dem nächsten Fragment -
  vermutlich weil OCR die dazwischenliegenden Wörter "dissolves
  distortion, and returns what" gar nicht erkannt hat, sodass keine
  durchgehende Zusammenführung möglich war) und im unteren Zitat-/
  Banner-Bereich, wo teils auch die OCR-Erkennung selbst schon
  Fehllesungen produziert (z. B. "Diterton" statt eines echten Worts) -
  eine Layout-Verbesserung kann eine falsch erkannte Textgrundlage nicht
  reparieren. Diese verbleibenden Fälle sind eine Mischung aus (a)
  OCR-Vollständigkeitslücken (fehlende Wörter mitten im Satz) und (b)
  einem Layout, das schlicht zu dicht gepackt ist, um jede Übersetzung
  ohne Schriftverkleinerung unter das lesbare Minimum oder ohne
  Box-Vergrößerung überlappungsfrei unterzubringen - kein Folgepunkt mit
  einer offensichtlichen nächsten Lösung, eher ein grundsätzliches
  Limit dieses Ansatzes (Box-Overlay/Inpainting auf Basis der
  Original-Boxgrößen) bei extrem dichten Infografik-Layouts.

  Getestet: 18 neue Tests. `tests/test_image_ocr.py` (13 Tests, reine
  Geometrie-Tests ohne Tesseract - u. a. Zusammenführung über 3+ Zeilen,
  Nicht-Zusammenführung bei großem Abstand/anderer Spalte/anderer
  Schriftgröße, korrekte Behandlung verschachtelter Spalten-Reihenfolge
  in der Rohliste, ein deterministischer Konfliktfall wenn zwei Regionen
  dieselbe Kandidatin beanspruchen). `tests/test_image_inpainting.py` (2
  Tests für `_initial_font_size()`s `line_height`-Nutzung).
  `tests/test_translate_image.py` (3 Integrationstests: eine echte
  Zusammenführung führt zu GENAU EINEM Übersetzungsaufruf mit
  zusammengefügtem Text, ein Kontroll-Test mit dem bestehenden
  Zwei-Zeilen-Fixture zeigt weiterhin zwei unabhängige Aufrufe, ein
  fehlgeschlagener Übersetzungsaufruf einer zusammengeführten Gruppe
  zählt ALLE ihre Original-Zeilen als fehlgeschlagen). Bestehende Tests
  angepasst: `_RecordingBackend`-Tests vergleichen jetzt über
  `dataclasses.replace(..., line_height=...)` statt Objekt-Identität
  (jede zurückgeschriebene Region ist jetzt ein von
  `merge_region_group()` neu gebautes Objekt, auch bei Einzel-Zeilen-
  Gruppen), Fehlermeldungs-Test von "region" auf "block" umbenannt.
  Gesamter Testlauf am Ende: 148 passed, 1 skipped (vorher 130 passed, 1
  skipped). Zwei Screenshots (vorher/nachher) an Michael geschickt.

- **Bildübersetzung/OCR - zwei zusätzliche, wählbare OCR-Engines mit
  echter Absatz-/Layouterkennung (Google Cloud Vision, PaddleOCR),
  23.08.2026:** Nach dem ehrlichen Befund oben (verbleibende
  Überlappungen v. a. dichter rechter Bereich/unteres Zitat, "kein
  Folgepunkt mit einer offensichtlichen nächsten Lösung") fragte
  Michael: "Bei der Übersetzung des gleichen Bildes von Google haben wir
  all diese Probleme so gut wie gar nicht. Was nutzt Google da?" Recherche
  ergab zwei Techniken: GAN-basierte Hintergrundrekonstruktion (dieselbe
  Kategorie wie unser GPU-Inpainting/LaMa, nur ein größeres Modell) und,
  wichtiger, dass Googles OCR eine ECHTE, trainierte Absatz-/Layout-
  Hierarchie liefert (Page → Block → Paragraph → Word → Symbol) statt
  Tesseracts reiner Zeilengruppierung. Michael: "Wenn wir die Technik
  hätten plus die Korrekturmöglichkeit hätten wir eine super akzeptable
  Lösung." Auf "Erst mal prüfen was der Wechsel bedeuten würde" wurden
  zwei Kandidaten direkt am echten Bild ("Spirit - Soul - Meatsuit.jpg")
  geprüft, BEVOR irgendein Produktivcode angefasst wurde:

  - `tools/probe_google_vision.py` (Cloud Vision API, DOCUMENT_TEXT_DETECTION)
    - 58 Absätze erkannt, Ø-Konfidenz 0.96. Läuft über denselben API-Key
      wie der Google-Übersetzer (Michael bestätigt: "Beide API Cloud
      Translation und Vision laufen über den Key").
  - `tools/probe_paddleocr.py` (PP-StructureV3, lokal/Apache-2.0)
    - 58 Layout-Blöcke erkannt (text 28, image 16, paragraph_title 10,
      footer 3, doc_title 1).

  Beide gruppierten die vorher problematischen dichten Bereiche (rechter
  Prozess-Flowchart, "KEY TRUTH"-Kette, unterer "IT'S NOT / IT IS"-Block)
  sichtbar sauberer als unsere eigene `merge_lines_into_paragraphs()`-
  Heuristik - direkter Bildvergleich, nicht nur Zahlen. Vision neigte zu
  zwei zu groben Zusammenfassungen (Titel+Untertitel+Tagline als eine
  Box, Sidebar-Kopf+Text als eine Box), PaddleOCR wirkte insgesamt einen
  Tick konsistenter. Auf "Ich würde beide zur Auswahl einbauen." wurden
  beide implementiert.

  **Architektur:** `pipeline/images/ocr.py`'s `OcrEngine`-Protocol/
  `pipeline/registry.py`'s `OCR_ENGINE_FACTORIES` waren genau für diesen
  Fall vorbereitet (Kommentar seit 22.08.2026: "Cloud-OCR-Backend folgt
  als zweiter Eintrag") - kein Umbau nötig, nur zwei neue Einträge.
  `GoogleVisionOcrEngine`/`PaddleOcrEngine` liefern beide EIN
  `OcrTextRegion` pro ABSATZ statt pro Zeile - neues Klassenattribut
  `OcrEngine.returns_paragraph_regions` (Default `False`, geprüft via
  `getattr(...)`) sagt `translate_image()`, `merge_lines_into_
  paragraphs()` für diese Engines KOMPLETT zu überspringen (erneutes
  Anwenden der Zeilen-Merge-Heuristik auf bereits fertige Absätze hätte
  im besten Fall nichts gebracht, im schlechtesten Fall zwei echte,
  separate Absätze fälschlich zusammengezogen - der Abstands-Schwellwert
  ist für Zeilenabstände kalibriert, nicht für Absatzabstände). Der
  Ausreißer-Höhen-Filter (`DEFAULT_MAX_HEIGHT_RATIO`) und
  `_initial_font_size()` nutzen jetzt beide dieselbe neue, zentrale
  Hilfsfunktion `pipeline.images.ocr.region_line_height()` (vorher zwei
  duplizierte `line_height if line_height is not None else height`-
  Stellen) - notwendig, weil jetzt ZWEI verschiedene Quellen mehrzeilige
  Regionen liefern können (unser eigenes Merge UND diese zwei Engines),
  nicht mehr nur eine.

  **Zwei echte Daten-Überraschungen, direkt an den echten JSON-Antworten
  beider Kandidaten gefunden, nicht angenommen:**
  1. Vision liefert Wort-für-Wort-Symbole korrekt getrennt (leicht zu
     sauberem, leerzeichengetrenntem Text zu rekonstruieren).
  2. PP-StructureV3s eigenes `parsing_res_list`-Feld `block_content`
     klebt alle Wörter OHNE Leerzeichen zusammen
     ("HOWTHECHALICERESTORESWHATISETERNALLYPURE") - für PP-Structures
     eigenen Zweck (Layout-zu-Markdown) unproblematisch, für Übersetzung
     unbrauchbar (wäre als ein Nonsens-Token verschickt worden).
     `PaddleOcrEngine` nutzt deshalb NICHT `block_content`, sondern
     verknüpft die korrekt getrennten Zeilen aus dem Pipeline-eigenen
     Roh-OCR-Ergebnis (`overall_ocr_res`, `rec_texts`/`rec_boxes`) anhand
     geometrischer Lage (Zeilen-Box-Mittelpunkt innerhalb der Block-Box)
     zu jedem übersetzbaren Layout-Block. Nur Blöcke mit `block_label`
     in `{"text", "paragraph_title", "doc_title", "footer"}` werden
     übersetzt (am echten Bild bestätigte Kategorien) - alles andere
     (u. a. die 16 "image"-Blöcke im echten Bild) bewusst konservativ
     ausgeschlossen statt geraten.

  **Ein weiterer, unabhängiger Fund beim ersten echten PaddleOCR-Testlauf
  auf Michaels Rechner:** `NotImplementedError:
  ConvertPirAttribute2RuntimeAttribute not support ...` - bestätigte
  Regression im oneDNN/PIR-CPU-Backend von PaddlePaddle 3.3.x (siehe
  GitHub-Issues PaddlePaddle/Paddle#77340, PaddlePaddle/PaddleOCR#18162),
  nicht unser Fehler. Workaround (von Michael selbst erfolgreich
  angewendet): `pip install "paddlepaddle==3.2.2"`. `requirements-
  paddleocr.txt` pinnt entsprechend, `PaddleOcrEngine.recognize()` fängt
  eine solche Inferenz-Exception jetzt sauber als `OcrError` ab statt
  einen rohen Traceback durchzureichen.

  **UI:** Dropdown übernimmt beide neuen Einträge automatisch (iteriert
  bereits über `OCR_ENGINE_FACTORIES`, siehe `ui/app.py`) - dabei einen
  bestehenden Bug am Rande gefunden und mitbehoben: der "Engine nicht
  verfügbar"-Hinweistext war EIN gemeinsamer String
  ("ocr_engine.unavailable", auf Tesseract zugeschnitten: "Tesseract
  wurde nicht gefunden...") für ALLE Engines - für eine nicht verfügbare
  Google-Vision- oder PaddleOCR-Auswahl wäre das ein irreführender Text
  gewesen. Jetzt pro Engine ein eigener Schlüssel
  (`ocr_engine.{name}.unavailable`), generischer Fallback bleibt für
  einen zukünftigen Eintrag ohne eigenen Text.

  **Getestet:** `tests/test_image_ocr.py` (11 neue Tests: Vision-
  Absatzaufbau inkl. der "x"/"y"-Schlüssel-fehlt-bei-0-Macke, dekorative
  Symbol-Filterung, API-Fehler-/Request-Fehler-Behandlung; PaddleOCR-
  Zeilen-zu-Block-Zuordnung inkl. der block_content-Leerzeichen-Lücke,
  Label-Whitelist, Pipeline-Caching, saubere Fehlerbehandlung einer
  Inferenz-Exception). `tests/test_translate_image.py` (3 neue Tests: der
  Merge-Skip für `returns_paragraph_regions`, dass `line_height` NICHT
  von `merge_region_group()` überschrieben wird, dass der Ausreißer-
  Höhen-Filter bei einer echten mehrzeiligen Absatz-Region nicht
  fälschlich anschlägt). `tests/test_registry.py` (neu, 4 Tests:
  Registry-Eintrag/Factory/Verfügbarkeits-Dispatch pro Engine-Name).
  Gesamter Testlauf: 172 passed, 1 skipped (vorher 148 passed, 1
  skipped) - alle in der Sandbox lauffähigen Testdateien. **Ehrlicher
  Vorbehalt:** `tests/test_ui_images_mode.py` (prüft u. a. den
  Dropdown/Hinweistext-Code in `ui/app.py`) konnte in dieser Sandbox
  NICHT ausgeführt werden - die Sandbox hat nur einen Teil-Checkout ohne
  `pipeline/pdf` etc., dieser Testdatei fehlt dadurch eine Abhängigkeit
  zum Import. Die zwei `ui/app.py`-Änderungen (Hinweistext-Schlüssel) sind
  daher nur durch direkte Code-Prüfung verifiziert, nicht durch einen
  automatisierten Lauf - bitte bei Gelegenheit einmal `pytest tests/` im
  vollständigen lokalen Checkout laufen lassen, um das abzusichern.
  Kein Live-Lauf der beiden neuen Engines gegen ein echtes Bild INNERHALB
  von `translate_image()` (nur mit Fake-Daten unit-getestet) - Michael
  hat PaddleOCR bereits über `tools/probe_paddleocr.py` gegen das echte
  Bild verifiziert, ein echter End-to-End-`translate_image()`-Lauf mit
  `ocr_engine=paddleocr`/`google_vision` steht noch aus.

## 23.08.2026 - Erster echter `translate_image()`-Lauf mit den zwei neuen OCR-Engines: PaddleOCR-Absturz gefunden und behoben, Google Vision bestätigt gut

  Der oben angekündigte echte End-to-End-Lauf (Michael, direkt aus der
  App, `Spirit - Soul - Meatsuit.jpg`, GPU-Inpainting/LaMa als
  Rückschreibe-Backend): drei OCR-Engines nacheinander getestet.

  **Tesseract** (Baseline, "(9)" im Dateinamen, QA-Bericht: 96 Regionen
  erkannt, 82 übersetzt): zeigt die bereits bekannten, noch offenen
  Kollisions-/Überlappungsprobleme bei dichtem Layout (siehe RoadMap.md
  Phase 3) - nichts Neues, keine Regression durch diese Änderung.

  **Google Vision** ("(10)" im Dateinamen, QA-Bericht: 58 Regionen
  erkannt, 57 übersetzt, 1 übersprungen): lief fehlerfrei durch.
  Michaels Einschätzung: "echt schon sehr gut", "noch ganz kleine
  Unstimmigkeiten". Im gelieferten Bild sichtbar: zwei-drei Stellen mit
  Textüberlappung in eng bemessenen Boxen (u. a. "DIESES MUSTER KANN
  NICHT AUFRECHTERHALTEN WERDEN" und die Zeile über "VERÄNDERT DIE
  ZIELGANG") - dieselbe Klasse Kollisionsproblem wie bei Tesseract, nur
  seltener (deutlich weniger Regionen/Layout dadurch insgesamt
  sauberer). Kein neuer, engine-spezifischer Fehler - siehe die 4 schon
  besprochenen Lösungsansätze (Font-Schrumpfen, kaskadierendes Reflow,
  robustere OCR, reine Transparenz) weiter oben in diesem Dokument für
  die grundsätzliche Lösung, noch nicht umgesetzt.

  **PaddleOCR: Absturz.**
  ```
  Übersetzungslauf fehlgeschlagen: ValueError: The truth value of an
  array with more than one element is ambiguous. Use a.any() or a.all()
  ```
  Ursache gefunden: `PaddleOcrEngine`s eigener Nachverarbeitungscode
  (`_paddle_ocr_lines()`, `_paddle_block_to_region()`) nutzte
  `x or []` bzw. `not x`, um ein fehlendes/leeres Feld
  (`rec_boxes`/`rec_scores`/`block_bbox`) abzufangen - das prüft
  `bool(x)`. Auf der ECHTEN PP-StructureV3-Pipeline sind diese Felder
  aber numpy-Arrays, nicht reine Python-Listen (die Fake-Fixtures in
  `tests/test_image_ocr.py` verwendeten Listen und haben das deshalb
  nicht gefangen) - numpy verweigert `bool()` für ein Array mit mehr als
  einem Element genau mit dieser Fehlermeldung. Bugfix: explizite
  `is None`-Prüfung statt Truthiness-Test an allen vier betroffenen
  Stellen. Zusätzlich die komplette Nachverarbeitung
  (`_paddle_ocr_lines()`+Block-Schleife) in `PaddleOcrEngine.recognize()`
  jetzt in ein eigenes try/except gefasst (analog zum bereits
  bestehenden try/except um `pipeline.predict()`), damit ein zukünftiger
  ähnlicher Überraschungsfund als sauberer `OcrError` statt als roher,
  unabgefangener Traceback durchschlägt.

  Regressionstest ergänzt
  (`test_paddleocr_recognize_handles_numpy_array_result_fields`), der
  die Fixture bewusst mit `numpy.array(...)` statt Listen aufbaut -
  schlägt ohne den Fix nachweislich fehl, ist mit dem Fix grün.
  `pytest.importorskip("numpy")`, da numpy kein Kern-Requirement ist
  (kommt transitiv über opencv-python-headless/paddlepaddle mit, beide
  bereits Voraussetzung für diese Funktion).

  **Getestet:** Gesamter Testlauf danach erneut grün: 173 passed, 1
  skipped (vorher 172/1, +1 neuer Regressionstest) - weiterhin ohne
  `tests/test_ui_images_mode.py` (siehe Vorbehalt oben, unverändert
  offen). Der PaddleOCR-Fix selbst ist damit nur gegen die
  numpy-Fixture verifiziert, NICHT erneut gegen Michaels echtes Bild -
  bitte den App-Lauf mit `ocr_engine=paddleocr` gegen
  `Spirit - Soul - Meatsuit.jpg` einmal wiederholen, um den Fix am
  echten Fall zu bestätigen.

  **Nachtrag, selber Tag - zweiter Absturz beim Wiederholungslauf:**
  ```
  Übersetzungslauf fehlgeschlagen: OcrError: PaddleOCR-Ergebnis konnte
  nicht verarbeitet werden: 'LayoutBlock' object has no attribute 'get'
  ```
  Nächste Schicht derselben Fehlerklasse: `parsing_res_list`'s Einträge
  sind auf dem ECHTEN, live `pipeline.predict()`-Ergebnis
  `LayoutBlock`-Objekte mit Feldern als reinen Attributen
  (`block.block_label`), keine Dicts (`block.get("block_label")`) -
  wieder etwas, das nur in der über `save_to_json()` serialisierten
  Fassung (wie von `tools/probe_paddleocr.py` gespeichert und wie die
  ursprünglichen Test-Fixtures aufgebaut waren) ein Dict ist, auf dem
  rohen In-Prozess-Objekt aber nicht. `result` und `overall_ocr_res`
  selbst unterstützen weiterhin `.get()` (der numpy-Fix kam vorher schon
  so weit ohne AttributeError) - nur die einzelnen Block-Einträge nicht.

  Bugfix: `_paddle_field(obj, key, default=None)` - liest ein Feld
  gleichermaßen von einem Dict (`.get()`) oder einem Objekt mit
  Attributen (`getattr()`), an jeder Stelle eingesetzt, wo bisher direkt
  `block.get(...)` stand. Regressionstest ergänzt
  (`test_paddleocr_recognize_handles_attribute_based_layout_blocks`),
  Fixture mit einer eigenen `_FakeLayoutBlock`-Klasse (Attribute statt
  Dict) statt eines Dicts - schlägt ohne den Fix nachweislich fehl.

  **Getestet:** 174 passed, 1 skipped (vorher 173/1, +1 neuer
  Regressionstest). Gleicher ehrlicher Vorbehalt wie oben: nur gegen die
  Fake-Fixture verifiziert, noch nicht erneut gegen Michaels echtes
  Bild - jetzt zwei verschiedene reale Diskrepanzen zwischen der
  gespeicherten JSON-Fassung (worauf `PaddleOcrEngine` ursprünglich
  aufgebaut wurde) und dem rohen In-Prozess-Ergebnisobjekt gefunden
  (numpy-Arrays UND Attribut-statt-Dict-Objekte) - nicht auszuschließen,
  dass ein dritter, noch unentdeckter Unterschied beim nächsten
  Wiederholungslauf auftaucht; das neue try/except um die gesamte
  Nachverarbeitung (siehe oben) fängt einen solchen Fund aber
  wenigstens als sauberen `OcrError` statt als rohen Traceback ab.

  **Zwei Rückfragen von Michael dazu, beide beantwortet, kein
  Code-Fund/keine Änderung nötig:**
  - "Ist die Rückschreib-Methode bei PaddleOCR/Google Vision
    irrelevant?" - Nein: `translate_image()` nimmt `ocr_engine` und
    `inpainting_backend` als zwei komplett unabhängige Parameter
    entgegen (siehe dessen Signatur) - die OCR-Engine bestimmt NUR wo/
    was für Text erkannt wird, das Inpainting-Backend bestimmt NUR wie
    der Originaltext-Bereich vor dem Zurückschreiben rekonstruiert wird.
    Das GAN-Inpainting, das Googles eigenes Bildübersetzungs-Produkt
    nutzt (frühere Recherche in diesem Dokument), ist Teil eines ganz
    anderen Google-Produkts als die hier integrierte Cloud Vision API
    (reine Texterkennung, kein Inpainting) - wir haben also keine
    Inpainting-Fähigkeit "mitgeliefert bekommen". Beide
    Rückschreib-Backends (CPU/klassisch, GPU/LaMa) bleiben für JEDE
    OCR-Engine-Wahl exakt gleich relevant, nichts zu deaktivieren.
  - "Können wir bei Google und PaddleOCR auch das Bild korrigieren?" -
    Ja, unverändert: `ImageCorrectionDialog`
    (`ui/image_correction_dialog.py`) arbeitet ausschließlich auf den
    bereits berechneten `replacements` (Text + Box-Geometrie) und ruft
    beim Anwenden NUR `InpaintingBackend.apply()` erneut auf - kein
    erneuter OCR-/Provider-/Netzwerk-Aufruf (siehe die Datei-eigene
    Docstring, Zeile 12: "no OCR/provider/network call involved").
    Der Korrektur-Dialog ist damit komplett engine-unabhängig und
    funktioniert für Tesseract-, Google-Vision- und PaddleOCR-Ergebnisse
    identisch - keine Änderung nötig.

  **Zweiter Nachtrag, selber Tag - dritter Wiederholungslauf (QA-Bericht
  "(11)"): kein Absturz mehr, aber 0 Textregionen erkannt.** Kein
  Crash diesmal - der `_paddle_field()`-Fix greift also -, aber
  `PaddleOcrEngine.recognize()` liefert eine leere Liste zurück
  ("Erkannte Textregionen: 0", Ergebnisdatei = Original). Mit zwei
  bereits gefundenen Diskrepanzen zwischen dem JSON-serialisierten
  Ergebnis (worauf die Engine ursprünglich aufgebaut wurde,
  tools/probe_paddleocr.py) und dem rohen In-Prozess-Objekt (numpy-
  Arrays, Attribute statt Dict-Keys) an einem Tag ist ein dritter,
  ähnlicher Fund wahrscheinlicher als ein Zufall - z. B. ein
  Feldname, der auf dem Live-Objekt anders heißt als vermutet
  (`block_label` existiert unter diesem Namen vielleicht gar nicht,
  `getattr(..., default=None)` liefert dann für JEDEN Block `None`
  zurück, `None not in _PADDLE_TRANSLATABLE_LABELS` ist wahr für
  jeden Block -> alle werden übersprungen, ohne Fehler). Statt ein
  drittes Mal blind zu raten: `tools/probe_paddleocr_shape.py` (neu)
  geschrieben - druckt die ECHTEN Attribut-/Key-Namen des rohen
  Live-Ergebnisobjekts direkt (kein Umweg über save_to_json() mehr).
  Michael gebeten, es einmal laufen zu lassen und die Ausgabe zu
  teilen, bevor am eigentlichen Code weitergeraten wird.

  **Nebenbefund, keine Änderung vorgenommen:** Der "Korrigieren"-Button
  fehlte in diesem Lauf in der UI - das ist bestehendes, unverändertes
  Verhalten (`ui/app.py::_show_job_result()`, Bedingung
  `any(file_result.stats.replacements for file_result in stats.results)`,
  identisch für alle drei OCR-Engines und schon vor dieser Änderung so
  für PDF/Bild), keine Regression durch die neuen Engines. Bei 0
  gefundenen Regionen gibt es schlicht nichts, dessen Text/Position
  automatisch korrigierbar wäre. Trotzdem eine echte, vorbestehende
  Lücke: der Korrektur-Dialog kann auch eine komplett manuell
  hinzugefügte Box ohne jede OCR-Vorlage anlegen (siehe QA-Bericht-
  Hinweistext: "das manuelle Hinzufügen einer Box für nicht erkannten
  Text") - genau der Fall, in dem OCR nichts gefunden hat, ist der
  Fall, in dem diese Funktion am meisten gebraucht würde, aber der
  Button ist dann unerreichbar versteckt. Noch nicht behoben (erst mal
  auf Michaels Rückmeldung dazu gewartet) - müsste die o.g. Bedingung
  um einen dritten Fall erweitern (0 Regionen, aber Format
  grundsätzlich korrekturfähig).

  **Dritter Nachtrag, selber Tag - Ursache gefunden über
  `tools/probe_paddleocr_shape.py`s echte Ausgabe.** Bestätigt genau
  die vermutete Erklärung: `parsing_res_list[0]` (`LayoutBlock`) hat
  laut `vars()` die Attribute `label`/`bbox`/`content` - NICHT
  `block_label`/`block_bbox`/`block_content` (kein `block_id`
  überhaupt). `_paddle_field()` fragte bisher `getattr(block,
  "block_label", None)` ab - das existiert auf dem echten Objekt
  nicht, liefert also für JEDEN Block `None` zurück (kein Fehler -
  `getattr` mit Default wirft nur, wenn ÜBERHAUPT keine Fallback-Logik
  besteht), und `None not in _PADDLE_TRANSLATABLE_LABELS` ist für jeden
  Block wahr -> alle 58 Blöcke übersprungen, 0 Regionen, kein Absturz.
  Exakt das Verhalten aus QA-Bericht "(11)".

  `overall_ocr_res` bestätigt weiterhin unverändert: bleibt ein Dict
  mit den ORIGINALEN Schlüsselnamen (`rec_texts`/`rec_scores`/
  `rec_boxes`) - nur `parsing_res_list`'s Blockeinträge haben dieses
  zusätzliche Namens-Mapping-Problem.

  Bugfix: `_PADDLE_BLOCK_FIELD_ALIASES = {"block_label": "label",
  "block_bbox": "bbox", "block_content": "content"}` in `_paddle_field()`
  - bei einem Dict weiterhin der ursprüngliche "block_*"-Schlüssel
  (passt zu save_to_json()/den Test-Fixtures), bei einem Objekt der
  gemappte kurze Attributname (passt zum echten Live-Objekt). Beide
  Aufrufstellen (`block_label`-Check, `block_bbox`-Lesen) bleiben dabei
  unverändert - nur `_paddle_field()` selbst wurde angepasst.

  Der bestehende Regressionstest
  (`test_paddleocr_recognize_handles_attribute_based_layout_blocks`,
  `_FakeLayoutBlock`) hatte VORHER fälschlich die "block_*"-Namen
  selbst als Attributnamen verwendet (geraten, ohne echte Daten) -
  damit bestand er zwar, deckte aber genau diesen Bug nicht auf.
  Korrigiert auf die jetzt bestätigten echten Attributnamen
  (`label`/`bbox`/`content`, kein `block_id`) - mit der alten,
  ungefixten `_paddle_field()`-Logik schlägt der Test jetzt nachweislich
  fehl (manuell verifiziert), mit dem Fix ist er grün. Lehre daraus für
  dieses Projekt: eine Fake-Fixture, die aus einer Vermutung statt aus
  echten Daten gebaut wird, kann genau den Bug verstecken, den sie
  eigentlich fangen soll - deshalb jetzt zweimal auf echte
  `tools/probe_paddleocr_shape.py`-Ausgabe statt auf eine dritte
  Vermutung gewartet.

  **Getestet:** 174 passed, 1 skipped (Testanzahl unverändert - der
  bestehende Test wurde korrigiert, nicht ein neuer ergänzt). Diesmal
  ausdrücklich NICHT mehr geraten, sondern gegen die von Michaels
  eigenem Diagnose-Lauf bestätigten echten Feldnamen gebaut - höhere
  Zuversicht als bei den beiden Fixes zuvor, aber noch nicht erneut
  gegen das echte Bild verifiziert. Michael gebeten, `ocr_engine=
  paddleocr` gegen `Spirit - Soul - Meatsuit.jpg` noch einmal zu
  starten. Der Korrigieren-Button-Nebenbefund von oben bleibt bewusst
  zurückgestellt, bis dieser Fix am echten Bild bestätigt ist.

## 23.08.2026 - PaddleOCR-Fix bestätigt (QA-Bericht "(12)"), Korrektur-Dialog: Original nicht mehr lesbar wegen Übersetzungs-Overlay behoben, drei weitere Layout-Befunde dokumentiert

  Michael, nach dem `_paddle_field()`-Alias-Fix: "Wow, das ist schon
  sehr gut." Der dritte Fix (echte Attributnamen `label`/`bbox`/
  `content` statt geratener "block_*"-Namen) hat also gegriffen - drei
  Fixes an einem Tag, jeder auf dem vorherigen aufbauend, aber am Ende
  läuft PaddleOCR jetzt tatsächlich durch.

  **Korrektur-Dialog: Original hinter Übersetzung nicht lesbar - behoben.**
  "Bei der Korrektur sieht man leider den Text nicht deutlich, da ja
  die Übersetzung das Original überlagert." Ursache gefunden in
  `ui/image_correction_dialog.py::_ResizableRegionItem.paint()`: die
  Box selbst hat nur eine leicht transparente Füllung (`_FILL_COLOR`,
  Alpha 40/255), aber der Übersetzungs-VORSCHAUTEXT wird darüber
  VOLL DECKEND gezeichnet - genau an der Stelle, an der auch der
  Originaltext im pristinen Hintergrundbild sitzt (dieselbe Box). Bei
  einer längeren deutschen Übersetzung kollidieren beide sichtbar.
  Fix: neuer Umschalt-Button "Original anzeigen" in der Canvas-
  Toolbar (`ImageCorrectionDialog.toggle_original_button`,
  `_on_toggle_original_visible()`) - blendet den Vorschautext aller
  Boxen auf einmal aus (Umriss + die schon vorhandene, kaum sichtbare
  Füllung bleiben), damit das pristine Original klar lesbar wird;
  erneutes Umschalten zeigt die Vorschau wieder. Neue, manuell hinzu-
  gefügte Boxen übernehmen den aktuellen Umschalt-Zustand direkt beim
  Anlegen. Neue i18n-Schlüssel `image_correction.show_original`
  (DE/EN, Parität geprüft).

  **Getestet:** Kein eigener automatisierter Test (PySide6-Dialog,
  wie der Rest von `ui/image_correction_dialog.py` bisher ohne
  GUI-Testinfrastruktur - siehe Backlog frühere Einträge zu
  `tests/test_ui_images_mode.py`). Stattdessen manuell mit
  `QT_QPA_PLATFORM=offscreen` instanziiert und den Toggle direkt
  durchgeschaltet: Ausgangszustand `show_preview=True`, nach
  "angehakt" `False`, nach "abgehakt" wieder `True` - wie erwartet.
  Gesamter Testlauf (`tests/`, ohne `test_ui_images_mode.py`)
  weiterhin 174 passed, 1 skipped - unverändert, da diese Änderung
  reines UI-Verhalten ohne Pipeline-Logik betrifft. i18n-Test
  (`test_ui_i18n.py`) bestätigt DE/EN-Schlüsselparität weiterhin
  gegeben.

  **Drei weitere Befunde aus demselben Lauf, NOCH NICHT behoben -
  brauchen echte Regionsdaten bzw. sind der bereits bekannte, offene
  Architektur-Punkt:**

  1. Ein kompletter Abschnitt (die Eingabe-Liste "Thoughts/Emotions/
     .../Experiences ... recorded as PATTERNS" links Mitte) wurde gar
     nicht übersetzt. Begründete Vermutung, noch nicht bestätigt:
     `LayoutParsingResultV2` hat NEBEN `parsing_res_list` eigene
     Listen für `chart_res_list`/`table_res_list`/`seal_res_list`/
     `formula_res_list` (siehe die dict-keys aus
     `tools/probe_paddleocr_shape.py`s Ausgabe) - `PaddleOcrEngine`
     liest ausschliesslich `parsing_res_list`. Dieser Abschnitt
     (Icons, Pfeile, kurze Wortgruppen - diagrammartig) könnte vom
     Layout-Modell als "chart" statt als Text-Block eingeordnet und
     dadurch komplett übersprungen worden sein, ohne dass das wie ein
     Fehler aussieht (kein Skip-Grund im QA-Bericht, weil die Engine
     die Region nie sieht). Noch zu verifizieren.
  2. Das Kelch-Symbol zwischen den beiden Fusszeilen-Textboxen wurde
     als Text "AND"/"UND" erkannt und übersetzt über das Icon
     gerendert. Begründete Vermutung: eine Fehlerkennung der
     Text-DETEKTION (nicht der Layout-Klassifikation) auf dem Icon
     selbst, dessen Box zufällig in einen "text"-gelabelten Block
     fiel. Ebenfalls noch zu verifizieren.
  3. Die Fusszeile ist unten abgeschnitten, und der Text in der lila
     "DIE TEMPORÄRE SCHNITTSTELLE"-Box wurde auf 2 Zeilen umgebrochen.
     Das ist KEIN neuer Bug, sondern eine reale Ausprägung des schon
     ganz am Anfang dieser Zusammenarbeit besprochenen, noch nicht
     umgesetzten Problems (die 4 Lösungsansätze weiter oben in diesem
     Dokument: Font-Schrumpfen [umgesetzt], kaskadierendes Reflow
     [nicht umgesetzt], robustere OCR [jetzt teilweise durch die neuen
     Engines], reine Transparenz [nicht umgesetzt]). Code-seitig
     bestätigt: `pipeline/images/inpainting.py::insert_text()` bricht
     das Zeichnen einer Zeile nur ab, wenn ihre y-Startposition schon
     hinter der Bild-Unterkante liegt (`if y >= image_height: break`)
     - eine Zeile, die knapp DAVOR beginnt, aber deren Glyphen über den
     Bildrand hinausragen, wird trotzdem gezeichnet und von PIL an der
     Canvas-Grenze hart abgeschnitten. Das ist der seit
     `_fit_text()`s Docstring bekannte "_MIN_FONT_SIZE-and-still-
     overflowing"-Grenzfall, hier real eingetreten. Michaels eigener
     Vorschlag deckt sich mit dem "kaskadierendes Reflow"-Ansatz von
     ganz oben: den Text seitlich in nachweislich leeren Raum
     ausdehnen (links vom linken, rechts vom rechten Fusszeilen-Block,
     da der Kelch dazwischen nicht bewegt werden muss) statt nur nach
     unten zu brechen/zu schrumpfen. Nicht umgesetzt - eine
     grössere, noch zu planende Änderung, keine Ein-Zeilen-Korrektur.

  Michael gebeten, für Fund 1+2 entweder den fehlenden QA-Bericht
  nachzureichen oder `tools/probe_paddleocr.py` (volles JSON,
  visualisiertes Bild) noch einmal laufen zu lassen, bevor an diesen
  beiden Stellen Code geändert wird - echte Daten statt einer dritten
  Vermutung, nach den zwei vorherigen Fehlschlägen aus genau diesem
  Grund. Für Fund 3 Rückfrage an Michael, ob das kaskadierende Reflow
  jetzt priorisiert werden soll.

## 23.08.2026 - Kaskadierendes horizontales Reflow umgesetzt (Fund 3); beide Vermutungen zu Fund 1+2 durch echte Diagnosedaten widerlegt

  Michael: "Ja, bitte und hier die Ausgabe" - erweitertes
  `tools/probe_paddleocr_shape.py` gegen "Spirit - Soul -
  Meatsuit.jpg" noch einmal laufen lassen, mit der Bitte, das
  kaskadierende Reflow (Fund 3 oben) jetzt umzusetzen.

  **Fund 1+2: beide bisherigen Vermutungen widerlegt, kein Fix.**
  Die echte Ausgabe zeigt: `chart_res_list`, `table_res_list`,
  `seal_res_list` und `formula_res_list` sind alle LEER (len=0) -
  die Vermutung, der fehlende Abschnitt sei als "chart" o.ä. in eine
  dieser Spezial-Listen geroutet worden statt in `parsing_res_list`,
  ist damit widerlegt. `parsing_res_list` enthält weiterhin genau die
  58 Blöcke von vorher (`'text': 28, 'image': 16, 'paragraph_title':
  10, 'footer': 3, 'doc_title': 1`) - dieselbe Verteilung wie beim
  allerersten Probe-Lauf. Für Fund 2 wurde zusätzlich `overall_ocr_res`
  nach exakten "and"/"und"/"&"-Treffern unter allen 104 `rec_texts`
  durchsucht - keiner gefunden. Die Vermutung "Kelch-Icon wurde
  wörtlich als das Wort 'and' erkannt" ist damit ebenfalls widerlegt.
  Beide Befunde bleiben also ungeklärt und brauchen einen neuen
  Diagnoseansatz (z. B. alle 58 Blöcke mit Label+bbox+content
  vollständig ausgeben, um sie manuell gegen das Originalbild
  abzugleichen, oder `tools/probe_paddleocr.py`s visualisiertes Bild
  direkt ansehen) - keine dritte Vermutung ohne weitere echte Daten.

  **Fund 3: kaskadierendes horizontales Reflow, `pipeline/images/
  inpainting.py`.** Michaels eigene Beobachtung als Grundlage: "Der
  Text könnte ohne weiteres nach links auf der einen Seite und auf
  der anderen Seite des Kelches nach rechts erweitert werden. Links
  und Rechts davon ist nichts." Neue Funktion `_horizontal_room()`
  spiegelt die Logik von `_vertical_room_below()`, aber auf der
  x-Achse: sucht unter allen anderen erkannten Regionen die, die sich
  mit der aktuellen vertikal überlappen ("dieselbe Zeile"), und
  liefert den freien Platz links/rechts bis zum nächsten Nachbarn
  ODER bis zum Bildrand (je nachdem, was näher ist) - anders als bei
  `_vertical_room_below()` gibt es hier KEIN grosszügiges Fallback
  ohne Nachbarn, der Bildrand ist immer eine harte Grenze.
  `_fit_text()` nutzt diesen Freiraum als reinen FALLBACK: erst wird
  wie bisher die Schriftgrösse bis `_MIN_FONT_SIZE` verkleinert; passt
  der Text danach immer noch nicht in die verfügbare Höhe, wird die
  Umbruchbreite in Schritten in den freien seitlichen Raum hinein
  vergrössert (rechts zuerst, links erst wenn rechts ausgeschöpft
  ist - passend zur Kelch-Situation: rechte Box wächst nach rechts,
  linke Box nach links, die Mitte bleibt frei). `_draw_fitted_text()`
  gibt entsprechend zurück, wie weit der Text nach links verschoben
  gezeichnet werden muss. In allen drei Rückschreibe-Backends
  (`BoxOverlayBackend`, `CvInpaintingBackend`, `GpuInpaintingBackend`)
  eingebunden.

  **Bekannte Einschränkung, bewusst in Kauf genommen:** der neu
  gewonnene seitliche Rand wird NICHT vom Hintergrund-Rekonstruktions-
  schritt mit abgedeckt (die Inpainting-Maske bzw. die Box-Füllung
  wird weiterhin nur für die ursprüngliche, kleinere Box berechnet) -
  sicher ist das nur, wenn dort wirklich nichts anderes im Bild steht,
  wie von Michael für den Kelch-Fall selbst bestätigt. Für den
  allgemeinen Fall (Text stösst an eine andere, nicht-erfasste
  Bildregion) ist das keine vollständige Lösung.

  **Getestet:** 9 neue Tests in `tests/test_image_inpainting.py`
  (`_horizontal_room()`: keine Nachbarn/Bildrand-Begrenzung, nächster
  Nachbar links+rechts in derselben Zeile, Nachbar in anderer Zeile
  wird ignoriert, nie negativ bei Überlappung; `_fit_text()`: kein
  Offset wenn Schrumpfen allein reicht, Erweiterung zuerst nach
  rechts ohne Verschiebung, linker Raum erst nach Ausschöpfen des
  rechten, weiterhin Overflow ohne Absturz wenn kein Raum vorhanden;
  plus ein Wiring-Test über `BoxOverlayBackend.apply()` per Monkey-
  patch-Spy, der bestätigt, dass `_horizontal_room()`s Ergebnis
  tatsächlich bei `_fit_text()` ankommt). `tests/test_image_
  inpainting.py` allein: 45 passed (vorher 36). Gesamter Testlauf
  (`tests/`, ohne `test_ui_images_mode.py`): 183 passed, 1 skipped -
  keine Regressionen in `test_image_cv_inpainting.py` oder
  `test_image_gpu_inpainting.py`, die dieselben Funktionen indirekt
  mitnutzen.

  Noch offen: ein echter Lauf gegen das reale Bild (Fusszeile), um zu
  bestätigen, dass das Abschneiden dadurch tatsächlich behoben ist -
  bisher nur unit-getestet, nicht am realen Fall verifiziert. Michael
  gebeten, das zu testen.

## 24.08.2026 - Fund 1+2 endgültig geklärt und behoben: "image"-Blöcke mit echtem Text werden jetzt übersetzt, Icon-Fehlleser (Kelch als "Y", Personen-Icon als "穴") werden herausgefiltert

  Michael: "Lass uns probe_paddleocr.py laufen." Statt einen neuen
  Lauf zu verlangen, reichte die bereits vorhandene Ausgabe von
  `tools/probe_paddleocr.py`s letztem echten Lauf (`paddle_probe_out/`,
  Bild "Spirit - Soul - Meatsuit.jpg") - visualisiertes Bild
  (`_layout_det_res.jpg`) und volle Ergebnis-JSON. Beide seit dem
  22.08.2026 offenen Befunde konnten damit ohne weitere Rückfrage an
  Michael geklärt werden.

  **Fund 1 - Ursache bestätigt.** Der Block "Thoughts/Emotions/
  Choices/Beliefs/Trauma/Karma/Experiences ... recorded as PATTERNS"
  ist in der echten JSON als `block_label: "image"` klassifiziert
  (Bbox [25, 457, 394, 718]), NICHT als "text" - vermutlich wegen der
  Ledger-/Kugel-Grafik im selben Block. `block_content` enthält aber
  echten, erkannten Text ('WHERE \nThoughts \n\nEmotions \n\nChoices
  \n\nBeliefs LEDGER \nTraum...'). `_PADDLE_TRANSLATABLE_LABELS`
  akzeptierte bisher nur `{"text", "paragraph_title", "doc_title",
  "footer"}` - der Block wurde also nicht übersehen, sondern durch die
  Kategorie-Filterung bewusst (aber in diesem Fall fälschlich)
  verworfen, bevor `_paddle_block_to_region()` überhaupt lief.

  **Fund 2 - Ursache bestätigt, UND ein zweiter, bisher unbemerkter
  Fall gefunden.** Das Kelch-Icon zwischen den beiden Fusszeilen-Boxen
  wurde von PP-StructureV3s eigener Zeilen-OCR tatsächlich als der
  einzelne Buchstabe "Y" gelesen (Konfidenz 0.8409) - die Übersetzung
  hat "Y" im Satzkontext offenbar als spanisches "und" gedeutet und zu
  "UND" gerendert. Zusätzlich, direkt in derselben echten JSON
  gefunden: ein Personen-Icon im "KEY TRUTH"-Kasten (bei "Meatsuit/
  Body/Identity") wurde als das chinesische Zeichen "穴" gelesen -
  Konfidenz 0.2849, der NIEDRIGSTE Wert aller 104 echten OCR-Zeilen
  auf diesem Bild. Bisher unauffällig, nur weil dieser Block ebenfalls
  als "image" galt und komplett verworfen wurde - mit dem Fix zu Fund
  1 allein hätte er plötzlich angefangen, ein übersetztes "穴" über das
  Icon zu zeichnen. Beide Funde sind die zwei niedrigsten Konfidenz-
  werte aller 104 Zeilen; der niedrigste echte Textwert liegt bei
  0.9111 - klarer Abstand.

  **Fix, beide Stellen zusammen (`pipeline/images/ocr.py`):**
  1. `_PADDLE_TRANSLATABLE_LABELS` um `"image"` erweitert. Sicher, weil
     `_paddle_block_to_region()` weiterhin `None` liefert, wenn keine
     OCR-Zeile geometrisch in den Block fällt - ein rein grafischer
     "image"-Block (kein Text) bleibt also unverändert unübersetzt.
  2. Neuer Filter in `_paddle_ocr_lines()`: OCR-Zeilen mit ≤2 Zeichen
     UND Konfidenz < 0.90 (`_PADDLE_STRAY_GLYPH_MAX_CHARS`/
     `_PADDLE_STRAY_GLYPH_MIN_SCORE`) werden vor jedem Block-Matching
     verworfen - trifft "Y" (0.84) und "穴" (0.28), lässt aber
     kurzen, sicher erkannten Text wie "OR" (0.9817) unangetastet.

  **Getestet:** 2 neue Tests in `tests/test_image_ocr.py`
  (`test_paddleocr_recognize_translates_an_image_labeled_block_with_
  real_text_inside`, `test_paddleocr_recognize_filters_a_stray_icon_
  glyph_misread_as_short_text` - Letzterer mit allen drei echten
  Konfidenzwerten "Y"/0.8409, "穴"/0.2849, "OR"/0.9817 nachgebaut).
  Kommentare der beiden bereits bestehenden "image wird nie zur Region"
  -Tests präzisiert (gilt weiterhin, aber jetzt weil keine OCR-Zeile
  im Block liegt, nicht mehr weil "image" pauschal ausgeschlossen
  ist). `tests/test_image_ocr.py` allein: 42 passed (vorher 40).
  Gesamter Testlauf (`tests/`, ohne `test_ui_images_mode.py`):
  185 passed, 1 skipped - keine Regressionen.

  Noch offen: ein echter Lauf gegen das reale Bild, um Fund 1+2 UND
  das kaskadierende Reflow (Fund 3, siehe Eintrag oben) gemeinsam am
  tatsächlichen Ergebnis zu bestätigen - bisher nur unit-getestet.

## 24.08.2026 - Fund 1 ("image"-Block übersetzen) noch am selben Tag zurückgerollt: echter Test zeigte eine Verschlechterung statt Verbesserung; Fund 2 (Kelch-Icon) bestätigt korrekt behoben

  Michael, nach dem echten Testlauf mit dem obigen Fix: "Version 13
  ist schlechter als Version 12", dazu vier Screenshots von QA-Bericht
  "(13)" und die QA-Berichte "(12)" und "(13)" im Volltext. Ein
  klarer, unmittelbarer Fall für das Projekt-Prinzip "echte Daten vor
  weiterer Theorie" - beide Berichte zeigen "Erkannte Textregionen:
  42" (identisch!), aber "Gesendete Zeichen: 2109" (12) vs. "2201"
  (13) - 92 Zeichen mehr trotz gleicher Regionenzahl. Das allein zeigt
  schon: es wurde nicht einfach nur mehr übersetzt, es wurde etwas
  ANDERS gruppiert.

  **Die Region-Arithmetik klärt es vollständig, ohne dass ein neuer
  Diagnoselauf nötig war:** In (12) war der Kelch-Icon-Fehlleser "Y"
  bereits eine EIGENE, echte "footer"-Region (dieses Label war schon
  immer erlaubt) - genau DAS war die Ursache für das "UND" im
  Fusszeilenbereich, nicht ein Zusammenspiel mit dem Text drumherum.
  In (13) fällt diese Region durch den neuen Konfidenz-Filter weg
  (-1), aber die "Thoughts/Emotions/..."-Liste wird durch die
  "image"-Erweiterung neu zu einer Region (+1) - macht netto wieder
  42, exakt wie beobachtet. Diese Rechnung bestätigt beide Funde
  unabhängig voneinander, ohne Vermutung.

  **Fund 2 (Kelch als "UND"): korrekt behoben.** Die "Y"-Region fällt
  jetzt weg, der Konfidenz-Filter wirkt wie geplant.

  **Fund 1 (Thoughts/Emotions-Liste): technisch übersetzt, aber
  sichtbar schlechter.** Michaels Screenshot von (13) zeigt an der
  Stelle der Liste einen verwaschenen, überlappenden Textblock ("WO
  Gedanken Emotionen Entscheidungen BUCH GEDANKEN TRAUMA Karma
  Erfahrungen ...aufgezeichnet als MUSTER"), der über den
  benachbarten Banner-Block ("WHERE EXPERIENCES..." / y=457, exakt
  dieselbe Starthöhe wie der Listen-Block) hinweg gezeichnet wird.
  Ursache: `_paddle_block_to_region()` fügt ALLE im Block liegenden
  OCR-Zeilen zu EINEM Absatz zusammen und zeichnet EINEN Textblock an
  der Block-Bbox. Das passt für echten Fliesstext - dieser Block ist
  aber kein Fliesstext, sondern 9 kurze, unabhängige Icon-Labels
  ("Thoughts", "Emotions", ... "PATTERNS"), die um eine Kreisgrafik
  verteilt sind. Zusammengefügt und als ein String übersetzt/gezeichnet
  ergibt das Kauderwelsch - schlechter lesbar als der unübersetzte
  Originaltext davor. Michaels Einschätzung "schlechter" ist also
  korrekt und mit dem Screenshot direkt nachvollziehbar.

  **Fix: nur Fund 1 zurückgerollt, Fund 2 bleibt.**
  `_PADDLE_TRANSLATABLE_LABELS` wieder auf `{"text", "paragraph_title",
  "doc_title", "footer"}` (ohne "image") - der Konfidenz-Filter
  (`_PADDLE_STRAY_GLYPH_MAX_CHARS`/`_MIN_SCORE`) bleibt unverändert,
  er hat sich im echten Test bewährt und keinen Nachteil gezeigt.
  Beide Codestellen mit ausführlichem Kommentar versehen, WARUM
  "image" absichtlich (wieder) ausgeschlossen ist - damit das nicht
  versehentlich ein drittes Mal ohne Lösung für das eigentliche
  Problem (pro-Zeile-Rendering statt Block-Zusammenfassung) versucht
  wird.

  **Richtiger Fix für Fund 1, noch nicht umgesetzt:** jede der 9
  kurzen OCR-Zeilen innerhalb eines "image"-Blocks müsste als EIGENE
  kleine Region an ihrer EIGENEN ursprünglichen Position übersetzt und
  gezeichnet werden, statt zu einem Absatz zusammengefasst zu werden -
  deutlich näher am Originaldesign, aber eine grössere Änderung
  (eigene Zeilen-zu-Region-Logik nur für bestimmte Layoutkategorien,
  vermutlich mit eigener Kollisionsvermeidung). Nicht heute umgesetzt -
  Fund 1 bleibt vorerst so wie vor dem 23.08.2026: Block wird
  übersprungen, Original bleibt auf Englisch sichtbar.

  **Getestet:** `test_paddleocr_recognize_translates_an_image_labeled_
  block_with_real_text_inside` umbenannt/umgedreht zu
  `test_paddleocr_recognize_still_excludes_an_image_labeled_block_
  even_with_real_text_inside` (pinnt jetzt das zurückgerollte
  Verhalten, mit vollständiger Dokumentation der Historie im
  Docstring statt stillem Umschreiben). Der Stray-Glyph-Test bleibt
  unverändert gültig (Ergebnis identisch, ob der "穴"-Block durch
  Label-Ausschluss oder durch den Konfidenz-Filter rausfällt).
  `tests/test_image_ocr.py` allein: weiterhin 42 passed. Gesamter
  Testlauf (`tests/`, ohne `test_ui_images_mode.py`): 185 passed,
  1 skipped - keine Regressionen.

  Michael gebeten, im nächsten echten Testlauf zu bestätigen, dass (a)
  der Kelch nicht mehr als "UND" erscheint und (b) die Thoughts/
  Emotions-Liste wieder wie vor dem 23.08.2026 aussieht (unübersetzt,
  aber nicht mehr verwaschen/überlappend) - und ob die eigentliche
  Übersetzung dieser Liste (der grössere, noch offene Fix von oben)
  priorisiert werden soll.

## 24.08.2026 - Der Revert von eben war selbst die Ursache einer NEUEN, schlimmeren Regression: "image"-Block war komplett unsichtbar für die Kollisionsvermeidung; jetzt als Hindernis-Region ohne Übersetzung geführt

  Michael, nach dem echten Testlauf mit dem Revert: "Das ist jetzt
  noch schlimmer als das vorherige. Die Font stimmen gar nicht mehr
  usw.", dazu Screenshot und QA-Bericht "(15)". Screenshot zeigt: die
  Beschriftung "Enthält:" liegt jetzt weit links, direkt über
  "Emotions"; die Bullet-Zeile "Alle MUSTER über alle Fleischanzüge
  hinweg..." zieht sich quer über fast die ganze Breite des Abschnitts
  und überlappt "Choices"/"Beliefs". QA-Bericht: "Erkannte
  Textregionen: 41" (genau -1 gegenüber (12)/(13)s 42 - exakt der
  erwartete Effekt des Reverts, die Kelch-"Y"-Region ist weg, keine
  neue Region kam dazu). Die Regionenzahl allein sah also "richtig"
  aus - das eigentliche Problem lag wo anders.

  **Ursache (dritte Runde am selben Tag):** `translate_image.py`s
  `obstacle_regions`-Mechanismus (gebaut 22.08.2026 GENAU für "eine
  Nachbar-Region darf nicht über echten, sichtbaren Originalinhalt
  wachsen") wird aus `stats.regions` gespeist - der Liste, die
  `ocr_engine.recognize()` zurückgibt. Der Revert von eben liess den
  "image"-Block (und jede seiner OCR-Zeilen) komplett VOR
  `_paddle_block_to_region()` fallen - er wurde nie ein
  `OcrTextRegion`-Objekt, tauchte also auch nie in `stats.regions`
  auf. Das erst am 23.08.2026 gebaute kaskadierende horizontale
  Reflow (`_horizontal_room()`) sieht dort also "kein Hindernis, freie
  Bahn bis zum Bildrand" - und lässt Nachbar-Regionen (die "Enthält:"-
  Übersetzung, die Bullet-Punkte) ungehindert über den eigentlich noch
  sichtbaren, unübersetzten Thoughts/Emotions-Text wachsen. Das war
  VORHER (vor dem 23.08.2026, als es noch kein Reflow gab) nie ein
  Problem - der Bug entsteht erst durch das Zusammenspiel der beiden
  heute/gestern gebauten Features, keines der beiden für sich allein
  genommen ist fehlerhaft.

  **Verifiziert vor dem Fix, mit den echten Bbox-Werten aus der
  JSON:** `_horizontal_room()` auf die Bullet-Region ohne den
  Thoughts-Block als Hindernis angewendet liefert `left_room = 462`
  (praktisch bis zum Bildrand) - mit dem Thoughts-Block als Hindernis
  `left_room = 68` (korrekt an dessen rechter Kante begrenzt). Das
  bestätigt die Diagnose exakt, ohne dass ein weiterer echter Testlauf
  nötig war.

  **Fix: die Region bleibt bestehen, wird aber als nicht-übersetzbar
  markiert, statt ganz zu verschwinden.** Neues Feld `OcrTextRegion.
  translatable: bool = True` (`pipeline/images/ocr.py`) - jeder
  andere Aufrufer/jedes bestehende Fixture lässt es unangetastet auf
  True. `PaddleOcrEngine.recognize()` baut jetzt für JEDEN Block eine
  Region (sofern OCR-Zeilen matchen), und markiert sie erst danach
  `translatable=False`, falls das Label nicht in
  `_PADDLE_TRANSLATABLE_LABELS` steht (`dataclasses.replace()`, da
  `OcrTextRegion` frozen ist). `translate_image.py`s Eligibility-
  Schleife überspringt eine `translatable=False`-Region genauso wie
  eine mit zu niedriger Konfidenz (neuer `stats.skipped`-Zweig,
  eigene Logmeldung "Layout-Kategorie nicht für Übersetzung
  vorgesehen") - sie erreicht nie den Übersetzer, landet aber (über
  das bereits bestehende `translated_original_ids`-Bookkeeping, ohne
  jede Änderung dort) ganz normal in `obstacle_regions`.
  `_max_plausible_height()`s Median-Berechnung ebenfalls um
  `and region.translatable` ergänzt - ein grossflächiger, absichtlich
  unübersetzter Block (261px hoch gegenüber ~20px echten Textzeilen)
  darf den Ausreisser-Schwellwert für die Bounding-Box-Grössenprüfung
  nicht nach oben verzerren. QA-Bericht-Text in `ui/image_job.py` um
  den dritten Übersprungs-Grund ergänzt, damit er ehrlich bleibt.

  **Getestet:** `test_paddleocr_recognize_still_excludes_an_image_
  labeled_block_even_with_real_text_inside` (voriger Eintrag) ersetzt
  durch `test_paddleocr_recognize_marks_an_image_labeled_block_
  untranslatable_but_still_returns_it` (prüft `translatable is
  False`, Text und Bbox der zurückgegebenen Region - mit vollständiger
  Drei-Versuche-Historie im Docstring, damit niemand das morgen ein
  viertes Mal falsch macht). Zwei neue Tests in
  `tests/test_translate_image.py`: `test_translate_image_passes_
  untranslatable_region_as_an_obstacle_and_never_sends_it` (Provider
  sieht den Text nie, Region landet trotzdem in `obstacle_regions`)
  und `test_translate_image_height_outlier_check_ignores_
  untranslatable_regions` (grosser untranslatable Block verzerrt die
  Ausreisser-Median-Berechnung nicht, ein echter Icon-Blob-Ausreisser
  wird trotzdem weiterhin erkannt). `tests/test_image_ocr.py`
  weiterhin 42 passed. `tests/test_translate_image.py`: 31 passed
  (vorher 29). Gesamter Testlauf (`tests/`, ohne
  `test_ui_images_mode.py`): 187 passed, 1 skipped - keine
  Regressionen.

  Noch offen, unverändert gegenüber dem letzten Eintrag: der
  eigentliche, grössere Fix für Fund 1 (jede der 9 kurzen Icon-Zeilen
  einzeln an ihrer Originalposition übersetzen statt als ein Block
  zusammengefasst) - die Liste bleibt bis dahin unübersetzt (Englisch)
  sichtbar, jetzt aber korrekt als Hindernis respektiert statt
  überzeichnet zu werden. Michael gebeten, einen weiteren echten Lauf
  zu bestätigen: Kelch nicht mehr "UND", Thoughts/Emotions-Bereich
  nicht mehr überzeichnet, Fusszeilen-Reflow (Fund 3) funktioniert wie
  vorgesehen.

## 26.08.2026 - UI-Neugestaltung: helleres, "card"-basiertes Design nach Vorbild des Projekts "Konvertierung Audio-Video" (QSS-Designsystem in ui/theme.py, Re-Styling + Card-Umbau)

  Michael, nachdem der letzte Commit bestätigt war: "Ich würde jetzt
  gerne das aktuelle erst einmal hinten anstellen und am UI noch was
  anpassen. Das UI gefällt mir so gar nicht. Kannst Du Dir mal das UI
  aus dem Projekt Ordner 'Konvertierung Audio-Video' anschauen und
  sehen ob wir das UI hier gleich aufbauen können. Es ist heller, hat
  runde Buttons usw. Unseres schaut so staubig, technisch und trocken
  aus. Danach würde ich gerne die Installer Logik angehen."

  **Untersuchung des Referenzprojekts:** "Konvertierung Audio-Video"
  ist eine Tauri-App (Rust-Backend + reines HTML/CSS/JS-Frontend,
  `tauri-app/ui/{index.html,style.css,app.js}`) - technisch komplett
  anderer Stack als PDF-Translator (PySide6/Qt), Code selbst also
  nicht übertragbar. Die Designsprache aus `style.css` schon: warmes
  Off-White (`--bg: #f2f1ec`), weiße Karten mit abgerundeten Ecken
  (`.card { border-radius: 16px; box-shadow: ... }`), runde Buttons
  (`border-radius: 10px`), ein grüner Primär-Button (`button.primary`,
  `--accent: #1f7a5f`) gegenüber beige-grauen Sekundär-Buttons, runde
  Eingabefelder, eine voll abgerundete Fortschrittsleiste
  (`border-radius: 999px`).

  **Ursache des "staubig, technisch, trocken"-Eindrucks bestätigt:**
  PDF-Translator hatte bisher gar kein QSS-Stylesheet - `ui/app.py`
  baut nur eine explizite `QPalette` (`ui/theme.py`s
  `DARK_COLORS`/`LIGHT_COLORS`, kontrastgetestet, ursprünglich gebaut
  gegen einen echten Unlesbarkeits-Bug in manchen Linux-Dark-Mode-
  Umgebungen). Ohne QSS bekommt jedes Widget Qts kantigen, eckigen
  Standard-Look - genau das gemeinte Erscheinungsbild.

  **Entscheidung (per Rückfrage an Michael):** Umfang = "Re-Styling +
  Card-Umbau" (nicht nur Buttons/Felder/Gruppen-Boxen neu einfärben/
  abrunden, sondern auch das Formular in einen Card-Abschnitt wie im
  Referenzprojekt umbauen). Schatten = "Einfacher Rahmen" (Michael hat
  sich explizit gegen echte weiche Schlagschatten entschieden, für die
  robustere, einfachere native-QSS-Variante ohne
  `QGraphicsDropShadowEffect`).

  **Umsetzung:**
  - `ui/theme.py`: neues, von `DARK_COLORS`/`LIGHT_COLORS` getrenntes
    Token-Set `SURFACE_LIGHT`/`SURFACE_DARK` (bg/card/ink/muted/line/
    input_bg/button_bg/button_hover/button_text/accent/accent_hover/
    accent_text als Hex-Strings) plus `RADIUS_CARD`/`RADIUS_CONTROL`/
    `RADIUS_PILL`. `QPalette` bleibt bestehen und unverändert (steuert
    weiterhin natives/von QSS nicht erreichbares Chrome wie
    Datei-Dialoge) - `surface_colors()`/`build_stylesheet(is_dark)`
    kommen als zusätzliche, separate Schicht obendrauf. Neue
    `hex_to_rgb()`-Hilfsfunktion, damit die neuen Hex-Token durch
    dieselbe, bereits getestete `contrast_ratio()`-Funktion laufen wie
    `DARK_COLORS`/`LIGHT_COLORS` - keine zweite, ungetestete
    Kontrastrechnung. `accent`/`accent_hover` sind in Light und Dark
    bewusst identisch: ein zunächst erwogenes helleres Dark-Mode-Grün
    (`#2f9c79`) erreichte gegen weißen Button-Text nur 3.41:1 (unter
    der 4.5:1-Grenze, die dieses Modul für jedes andere Paar
    durchsetzt), `#1f7a5f` (das Light-Grün) erreicht 5.24:1 und
    funktioniert in beiden Modi. `build_stylesheet()` liefert das
    komplette QSS für `QGroupBox` (Card-Look: Hintergrund, 1px Rahmen,
    `border-radius: 14px`, Titel-Styling), `QPushButton` (inkl.
    `:hover`/`:disabled` und die `[cssClass="primary"]`-Variante für
    genau den Start-Button), `QLineEdit`/`QTextEdit`/`QComboBox`/
    `QSpinBox` (abgerundet, umrandet, gepolstert), `QCheckBox`
    (abgerundete Checkbox mit Akzentfarbe im angehakten Zustand),
    `QProgressBar` (voll abgerundeter Balken, Akzentfarbe).
  - `ui/app.py`: `self.start` (der einzige primäre Call-to-Action)
    bekommt `setProperty("cssClass", "primary")` - jeder andere Button
    bleibt beim neutralen Sekundär-Look, dieselbe Aufteilung wie im
    Referenzprojekt ("Start" grün, "Abbrechen"/"Log-Pfad" gedeckt).
    Das bisher direkt in `root` liegende Formular (`self.form`, als
    einziger Abschnitt bisher OHNE Card-Rahmen, `cost_box`/`job_box`
    waren schon `QGroupBox`) steckt jetzt in einer eigenen neuen
    `self.config_box`-`QGroupBox`, damit das ganze Fenster als
    einheitlicher Stapel von Cards wirkt statt einem card-losen
    Formular gefolgt von zwei Cards. `root` bekommt zusätzlich
    `setContentsMargins(20, 20, 20, 20)`/`setSpacing(16)` für Luft
    zwischen den Cards. `apply_explicit_palette()` ruft direkt nach
    `app.setPalette(palette)` jetzt zusätzlich
    `app.setStyleSheet(build_stylesheet(is_dark))` auf - mit demselben
    `is_dark`, das schon zuvor aus der GEERBTEN Palette ermittelt
    wurde (nicht neu aus der inzwischen überschriebenen Palette
    abgeleitet).
  - `ui/i18n.py`: neuer Schlüssel `"config.group"` ("Auftrag
    konfigurieren" / "Configure job") für den Titel der neuen
    `config_box`-Card, in beiden Katalogen ergänzt und auf
    Schlüssel-Parität geprüft (`set(CATALOGUES['de']) ==
    set(CATALOGUES['en'])`, keine Differenz).

  **Geprüft:** `QFormLayout.setRowVisible()` (von `_mode_changed()`
  für `ico_mode`/`exclude_header`/`exclude_footer`/`ocr_engine`/
  `inpainting_backend` genutzt) bleibt unberührt davon, dass `self.
  form` jetzt in einer `QGroupBox` statt direkt in `root` steckt -
  bestätigt sowohl durch Code-Lektüre als auch dadurch, dass
  `tests/test_ui_images_mode.py` (`window.form.isRowVisible(...)`)
  weiterhin exakt dasselbe `self.form`-Attribut anspricht, das nur
  sein Eltern-Layout gewechselt hat. Kein anderer `ui/*.py`-Dialog
  setzt ein eigenes, konkurrierendes `QGroupBox`/`QPushButton`-
  Stylesheet (nur einzelne `QLabel`s mit lokalem `padding`/
  `font-weight`, die nicht mit Farbe/Radius kollidieren) - das
  QApplication-weite `setStyleSheet()` kaskadiert also sauber auf
  alle Fenster/Dialoge (SettingsDialog, Korrektur-Dialoge, ...).

  **Getestet:** alle neuen Farbpaare (Light UND Dark) gegen die
  bestehende `contrast_ratio()`-Funktion geprüft, WCAG-AA (≥4.5:1)
  eingehalten: ink-auf-card 17.04/12.02, ink-auf-bg 15.07/13.59,
  muted-auf-card 5.31/5.74, muted-auf-bg 4.69/6.49, button_text-auf-
  button_bg 14.09/9.69, button_text-auf-button_hover 11.99/7.92,
  accent_text-auf-accent 5.24/5.24, accent_text-auf-accent_hover
  9.10/9.10, ink-auf-input_bg 16.47/13.18 (Light/Dark). Neue Tests in
  `tests/test_ui_theme.py`: `test_hex_to_rgb_parses_hash_prefixed_hex`,
  `test_surface_colors_selects_dark_or_light`,
  `test_surface_colors_meet_wcag_aa_for_text_pairs` (alle neun Paare
  oben, beide Modi), `test_surface_light_and_dark_share_the_same_
  accent`, `test_build_stylesheet_returns_qss_for_both_modes`
  (strukturelle Marker: `QGroupBox`, `QPushButton`,
  `QPushButton[cssClass="primary"]`, `QLineEdit`, `QCheckBox::
  indicator`, `QProgressBar`, alle drei Radius-Werte kommen im QSS
  tatsächlich vor) und `test_build_stylesheet_differs_between_light_
  and_dark`. `tests/test_ui_theme.py`: 10 passed (vorher 4).
  `tests/test_ui_i18n.py`: weiterhin 3 passed. Gesamter Testlauf
  (`tests/`, ohne `test_ui_images_mode.py`): 197 passed, 1 skipped -
  keine Regressionen.

  **Noch offen:** `test_ui_images_mode.py` selbst kann in dieser
  Sandbox mangels Display nicht laufen (bekannte, seit längerem
  bestehende Einschränkung) - Code-Lektüre spricht dagegen, dass der
  Card-Umbau dort etwas bricht, ein echter Lauf auf Michaels Maschine
  bestätigt das aber nicht automatisch. Vor allem: das tatsächliche
  Aussehen wurde in dieser Sitzung nicht visuell geprüft (kein Display
  im Sandbox) - Michael gebeten, die App zu starten und einen
  Screenshot zu schicken, damit das Ergebnis gegen die Absicht
  bestätigt werden kann, bevor es als erledigt gilt. Danach, wie von
  Michael angekündigt: Installer-Logik als nächstes Thema.

## 26.08.2026 - Fehlende Dropdown-Pfeile nach dem Card-Umbau behoben; Michaels Frage nach einer "Übersetzung gewünscht?"-Checkbox geklärt

  Michael, nach zwei Screenshots vom Dark-Mode-Ergebnis (insgesamt
  bestätigt das Grundbild - Cards, runde Buttons, grüner Start-Button):
  "Es fehlen die Pfeile an den Auswahlboxen. Und hatten wir nicht auch
  eine Checkbox ob überhaupt eine Übersetzung gewünscht ist?"

  **Pfeile:** echter, durch die neue QSS eingeführter Regressions-Bug.
  Sobald eine QComboBox IRGENDEINE Stylesheet-Regel bekommt (hier
  bereits durch das generische `QLineEdit, QTextEdit, QComboBox,
  QSpinBox { ... }`-Rahmen-Styling), zeichnet Qt den nativen
  Dropdown-Pfeil gar nicht mehr - die vorhandene
  `QComboBox::drop-down { border: none; width: 22px; }`-Regel entfernte
  zusätzlich den Rahmen um die (unsichtbare) Pfeilfläche, aber ohne
  einen Ersatzpfeil zu liefern, blieb da schlicht nichts. Gleiches
  Prinzip betrifft `QSpinBox`s Auf-/Ab-Buttons (im aktuellen UI nicht
  sichtbar, nur in den Einstellungen - vorsorglich mit behoben, statt
  denselben Bug erst beim nächsten Öffnen der Einstellungen gemeldet zu
  bekommen). Fix: `QComboBox::down-arrow`/`QSpinBox::up-arrow`/
  `QSpinBox::down-arrow` zeichnen den Pfeil als reines CSS-Dreieck
  (0×0-Box, eine Rahmenseite breit und farbig, die beiden anderen
  transparent) statt über eine Bild-Ressource - kein zusätzliches
  Icon-Asset nötig, färbt sich mit `muted` automatisch für Light UND
  Dark mit ein, `:disabled`-Variante für den Dropdown-Pfeil ergänzt
  (`line`-Farbe statt `muted`, sichtbar schwächer). Neuer struktureller
  Test in `tests/test_ui_theme.py::test_build_stylesheet_returns_qss_
  for_both_modes` prüft jetzt zusätzlich, dass alle drei neuen
  Pfeil-Selektoren im erzeugten QSS vorkommen - damit ein künftiger
  Umbau des Stylesheets nicht denselben Fehler unbemerkt wiederholt.

  **Checkbox-Frage:** Code (`ui/app.py`) und Backlog durchsucht - es
  gibt aktuell nur vier `QCheckBox`-Felder im gesamten UI: `ico_mode`,
  `exclude_header`, `exclude_footer` (alle drei modusabhängig
  ein-/ausgeblendet über `setRowVisible()`) und `confirm` ("Analyse und
  Kostenschätzung geprüft" in der Kostenbox). Keine davon ist oder war
  je eine generische "Übersetzung ja/nein"-Checkbox, und im gesamten
  Backlog findet sich kein Eintrag, der je eine solche Checkbox gebaut
  hätte - der Card-Umbau hat also nichts entfernt, was vorher da war.
  Bei Michael nachgefragt, was genau gemeint ist (evtl. eine
  Verwechslung mit `confirm`, oder ein neuer Wunsch, den Übersetzungs-
  schritt optional komplett überspringen zu können, z. B. nur OCR/Layout
  ohne echte Übersetzung) - noch offen, keine Änderung vorgenommen, bis
  das geklärt ist.

  **Getestet:** `tests/test_ui_theme.py`: weiterhin 10 passed (neuer
  Assert in einem bestehenden Test, keine neue Testfunktion). Noch
  nicht erneut visuell bestätigt - Michael um einen weiteren
  Screenshot gebeten.

## 26.08.2026 - Umbau auf lokaler Server + pywebview: Planungsrunde abgeschlossen, erster Umsetzungsschritt (i18n-Split + settings_store) fertig

  Direkt im Anschluss an die Build-Strategie-Klärung (siehe Eintrag oben,
  "Also einen Installer der alles auf dem lokalen Browser startet [...]
  Lokaler Server + Browser UI, aber auch als App", "Ja, trotzdem
  umbauen"): eine ausführliche Planungsrunde (drei parallele
  Explore-Agenten + ein Plan-Agent, per `EnterPlanMode`) hat einen
  konkreten Umsetzungsplan für einen ersten Gehversuch ergeben - nur der
  Bild-Übersetzungs-Modus, Ende-zu-Ende, bevor PDF/Word/PPTX angefasst
  werden. Michael hat dabei zwei weitere Entscheidungen getroffen:
  App-Hülle **pywebview** (natives Fenster statt System-Browser-Tab -
  `create_file_dialog()` gibt einen echten systemeigenen Datei-Dialog,
  ersetzt `QFileDialog` direkt, praktischer Vorteil nicht nur
  Kosmetik), und **Bilder übersetzen** als erster Gehversuch (weil dafür
  mit `image_translate_cli/review_server.py`, 22.08.2026 für den
  Korrektur-Dialog gebaut, bereits ein funktionierendes Vorbild für
  "lokaler `http.server` + eigenständige HTML/JS-Seite" existiert).

  Wichtiger Zwischenfund bei der Planung: die Sandbox-Kopien aus
  früheren Sitzungen waren uneinheitlich (teils veraltet, teils
  unvollständig) - vor dem eigentlichen Planen wurde deshalb ein
  frischer Abgleich gegen das echte Gerät gemacht (`ui/models.py`
  existiert und ist bereits vollständig Qt-frei laut eigenem Docstring;
  `image_translate_cli/cli.py`/`review_server.py`/`regions_io.py` sind
  auf dem echten Gerät vollständig und aktuell; `ui/i18n.py` importiert
  `PySide6.QtCore` bereits auf Modulebene, Zeile 6, VOR den reinen
  Katalog-Dicts). Der vollständige Plan liegt in
  `/root/.claude/plans/moonlit-humming-brook.md` (Architektur, HTTP-API,
  Reihenfolge in 8 Schritten, explizite Nicht-Ziele) - hier nur die
  Kurzfassung der ersten Umsetzung.

  **Schritt 1 umgesetzt (von 8 laut Plan):** `ui/i18n.py`s reine
  Katalog-Daten (`LocaleInfo`/`LOCALES`/`DE`/`EN`/`CATALOGUES`, 158
  Schlüssel je Sprache, byte-identisch übernommen) nach neues
  `ui/i18n_data.py` ausgelagert - dieses Modul importiert NICHTS aus
  PySide6, verifiziert durch einen echten Test mit geblocktem
  `PySide6`-Import (`sys.meta_path`-Trick, kein Mock). `ui/i18n.py`
  selbst bleibt als schlanker Re-Export bestehen (`from ui.i18n_data
  import ...`) und behält nur `LanguageManager(QObject)` - jeder
  bestehende `from ui.i18n import DE/CATALOGUES/...`-Aufruf funktioniert
  unverändert weiter, die Qt-App ist von diesem Schritt nicht betroffen.

  Neues Paket `webapp/` (gleichrangig zu `ui/`/`pipeline/`/
  `image_translate_cli/`), bisher nur `settings_store.py`: stdlib-only
  JSON-Datei im OS-üblichen Konfigurationsordner (`$XDG_CONFIG_HOME`/
  `%APPDATA%`/`~/Library/Application Support`, per `sys.platform`-
  Verzweigung ermittelt, bewusst ohne neue Abhängigkeit wie
  `platformdirs`) als Ersatz für `QSettings("PDF-Translator", "Document
  Translator")`. Feldnamen orientieren sich an `ui/app.py`s
  `_persist_form_state()`/`_restore_form_state()` (Zeile 380-438),
  minus der PDF/Word-only-Felder (`form.mode`, `form.ico_mode` usw.),
  die für den Bild-only-Piloten nicht gebraucht werden. `load()` fällt
  bei fehlender oder kaputter Datei sauber auf `DEFAULTS` zurück
  (nie ein Absturz beim Server-Start), `save()` ist ein
  Read-Modify-Write (Teil-Update, kein Überschreiben nicht genannter
  Felder) - beides mit echten Dateisystem-Tests in
  `tests/test_webapp_settings_store.py` verifiziert, nicht nur
  behauptet. Zugangsdaten (`ui/settings.py::credential_status()`/
  `save_credential()`) bleiben unverändert, da sie schon heute über
  Env-Variablen/`keyring` laufen, nicht über `QSettings`.

  **Getestet:** `webapp` importiert und läuft nachweislich auch mit
  komplett geblocktem `PySide6`-Import (derselbe `sys.meta_path`-Test
  wie oben, diesmal inklusive eines echten `save()`/`load()`-Rundlaufs).
  Neu: `tests/test_webapp_settings_store.py` (6 Tests: Standardwerte
  bei fehlender/kaputter Datei, echter Rundlauf, Teil-Update statt
  Überschreiben, automatisches Anlegen fehlender Ordner,
  Konfigurationspfad-Auflösung für Linux/Windows/macOS je einzeln mit
  `monkeypatch` geprüft - nie der echte `~/.config`-Pfad angefasst,
  analog zu `tests/conftest.py`s QSettings-Isolationsbegründung).
  `tests/test_ui_i18n.py`: weiterhin 3 passed (Katalog-Parität etc.
  unverändert, da `ui.i18n.CATALOGUES` weiterhin exakt dasselbe Objekt
  liefert wie vorher). Gesamter Testlauf (`tests/`, ohne
  `test_ui_images_mode.py`): 203 passed (vorher 197), 1 skipped - keine
  Regressionen.

  **Noch offen (Schritte 2-8 laut Plan):** `webapp/server.py` +
  `webapp/job_bridge.py` (HTTP-Server, `/api/config` + `/api/analyze`
  zuerst, noch ohne Seiteneffekte), das statische Frontend, der
  eigentliche Job-Start/Fortschritt/Abbruch-Pfad, das
  Bestätigungs-Gate Ende-zu-Ende, der pywebview-Bootstrap, die
  QA-Bericht-Anzeige, und zuletzt die `review_server.py`-Übergabe
  (braucht einen kleinen, abwärtskompatiblen Refactor von
  `run_review_session()` in `start_review_server()` + separate
  Blockier-Logik, damit die URL sofort verfügbar ist statt erst nach
  Ende der Korrektursitzung). Ausdrücklich nicht Teil dieses oder der
  nächsten Schritte: Installer/CI, PDF/Word/PPTX-Migration, Entfernen
  der bestehenden Qt-App.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 2 abgeschlossen:
  `webapp/server.py` + `webapp/job_bridge.py`, nur `/api/config` +
  `/api/analyze`.** Beim Schreiben von `job_bridge.py` fiel auf, dass das
  bereits ausgelieferte `webapp/settings_store.py` aus Schritt 1 einen
  falschen Wert hatte: `max_chars` stand dort hart auf `500_000`, geraten
  anhand einer Beispiel-Struktur statt geprüft. Der echte Wert (aus
  `pipeline/translation/cost_control.py`) ist
  `DEFAULT_MAX_CHARS_PER_RUN = 200_000`. Behoben durch Import dieser
  Konstante statt eines eigenen Literals - `settings_store.py` wird mit
  diesem Schritt korrigiert erneut ausgeliefert, damit der falsche Wert
  nicht unbemerkt in Schritt 4 (dem eigentlichen Job-Start) landet.

  `webapp/job_bridge.py` (neu, kein `http.server`-Import, bewusst isoliert
  testbar von der HTTP-Schicht): `build_config()` liefert alles, was das
  Formular im Bild-Modus zum Rendern braucht - Anbieterliste
  (`pipeline.registry.PROVIDER_FACTORIES`), Zugangsdaten-Status je
  Anbieter (`ui.settings.credential_status()`), OCR-Engine-/Backend-Namen
  und deren tatsächliche Verfügbarkeit
  (`pipeline.registry.ocr_engine_available()`/`inpainting_backend_available()`),
  zuletzt gespeicherter Formular-Stand (`settings_store.load()`).
  `analyze()` wrappt `ui.analysis.analyze_request()` unverändert (das
  RoadMap-Leitprinzip - jeder kostenpflichtige Lauf braucht Analyse,
  Kostenschätzung, ausdrückliche Bestätigung - hängt direkt an dieser
  einen Funktion, keine eigene Neuberechnung) und gibt bei
  Validierungsfehlern `{"ok": false, "errors": [...]}` statt einer
  Exception zurück.

  `webapp/server.py` (neu, `http.server.ThreadingHTTPServer` +
  `BaseHTTPRequestHandler`, exakt das Muster aus
  `image_translate_cli/review_server.py`, kein Framework): `create_server(host,
  port)` bindet und gibt sofort zurück, ohne `serve_forever()` zu
  blockieren (Aufrufer steuert den Serving-Thread) - `port=0` lässt das
  Betriebssystem einen freien Port wählen, wie `review_server.py` es
  heute schon nutzt. Routing bisher nur exakte Pfade (`/api/config` GET,
  `/api/analyze` POST) - dynamische Pfade wie `/api/jobs/<id>/status`
  kommen erst in Schritt 4 und brauchen dann eigenes Dispatching.

  Beim Aufbau kam wieder dieselbe Sandbox-Lücke wie schon in früheren
  Sitzungen zum Vorschein: `ui/models.py`, `pipeline/presentation/` und
  `pipeline/word/` fehlten im Sandbox-Checkout, obwohl `ui/analysis.py`
  sie zur Modulzeit importiert. Frisch vom Gerät nachgeladen (unverändert
  - keine Diffs, nur ergänzt), keine dieser Dateien war Teil dieser
  Auslieferung.

  **Getestet:** `webapp.server`/`webapp.job_bridge` importieren
  nachweislich weiterhin ohne `PySide6` (derselbe `sys.meta_path`-Test wie
  in Schritt 1). Neu: `tests/test_webapp_images_api.py` (6 Tests, echte
  HTTP-Aufrufe via `urllib.request` gegen einen auf `port=0` gestarteten
  Server) - deckt `/api/config`s Verfügbarkeitsflags ab,
  `/api/analyze`s Ablehnung bei leerer/fehlerhafter Quelldateiliste und
  bei kaputtem JSON-Body, eine 404 auf unbekannte Pfade, und einen
  echten Ende-zu-Ende-Lauf: `/api/analyze` gegen `demo_1_original.png`
  mit echtem Tesseract-OCR (kein Mock) - liefert eine reale
  Kostenschätzung zurück. Gesamter Testlauf (`tests/`, ohne
  `test_ui_images_mode.py`): 209 passed (vorher 203), 1 skipped - keine
  Regressionen.

  **Noch offen (Schritte 3-8 laut Plan):** statisches Frontend-Grundgerüst
  (zunächst im normalen Browser, `python -m webapp.server`, noch kein
  pywebview), `/api/jobs` (Start/Status/Abbruch/Ergebnis, eigener
  Hintergrund-Thread statt `QThreadPool`), das Bestätigungs-Gate
  Ende-zu-Ende inklusive serverseitiger Nachprüfung, der
  pywebview-Bootstrap mit `create_file_dialog()` statt `QFileDialog`, die
  QA-Bericht-Anzeige, und zuletzt die `review_server.py`-Übergabe.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 3 abgeschlossen:
  statisches Frontend-Grundgerüst, geöffnet im normalen Browser
  (`python -m webapp.server`), noch kein pywebview.** Neu unter
  `webapp/static/`: `index.html`/`app.css`/`app.js` als echte Dateien
  (keine Python-String-Konstante wie `review_server.py`s `_PAGE_HTML` -
  bewusste Entscheidung aus dem Plan, hier isoliert bewiesen), dazu
  `i18n/de.json` + `i18n/en.json`. Diese beiden JSON-Dateien werden nicht
  von Hand gepflegt, sondern per neuem `webapp/tools/export_i18n.py` aus
  `ui/i18n_data.py`s echten `DE`/`EN`-Katalogen exportiert (158 Schlüssel
  je Sprache) - die Bild-Modus-Formularfelder im Browser verwenden damit
  exakt dieselben deutschen/englischen Texte wie die Qt-App
  ("Übersetzungsanbieter", "Rückschreibe-Methode" usw.), keine separat
  gepflegte Kopie. Bei Änderungen an `ui/i18n_data.py` muss das Skript
  von Hand erneut laufen (`python -m webapp.tools.export_i18n`) - es gibt
  bewusst keinen Laufzeit-Import von `ui.i18n_data` im Server-Prozess
  (Begründung siehe Skript-Docstring), also auch keinen Test, der eine
  vergessene Neuauslieferung automatisch auffängt.

  `app.css` portiert `ui/theme.py`s `SURFACE_LIGHT`/`SURFACE_DARK`- und
  Radius-Werte 1:1 als CSS-Custom-Properties (hell per `:root`, dunkel
  per `prefers-color-scheme: dark` - im Browser gibt es kein QPalette-
  Äquivalent, daher automatisch statt manuell umschaltbar). Bei den
  `<select>`-Elementen trat derselbe Effekt auf, den Michael schon bei
  den Qt-Auswahlboxen gemeldet hatte ("Es fehlen die Pfeile an den
  Auswahlboxen") - ein `<select>` verliert seinen nativen Pfeil, sobald
  es umgestylt wird; behoben mit demselben Prinzip wie in
  `ui/theme.py` (Pfeil selbst gezeichnet statt auf das Standard-Rendering
  zu vertrauen).

  `webapp/server.py` bedient jetzt neben `/api/*` auch statische Dateien
  aus `webapp/static/` (`/` → `index.html`, `/app.js` → `app.js`, `/i18n/de.json`
  → `i18n/de.json` usw.) - mit Pfad-Traversal-Schutz (`unquote()` +
  `resolve()` + Prüfung, dass das Ergebnis innerhalb von `webapp/static/`
  bleibt, bevor irgendetwas gelesen wird) und einem eigenen `main()` für
  `python -m webapp.server`: startet den Server, öffnet die URL im
  Standardbrowser, blockiert bis Abbruch - ein reiner Entwickler-
  Einstiegspunkt für diesen Zwischenschritt, nicht der spätere
  pywebview-Start aus Schritt 6.

  `app.js` (kein Framework, kein Build-Schritt): lädt beim Start den
  Sprachkatalog und `/api/config`, füllt Anbieter-/OCR-Engine-/
  Rückschreibe-Methode-Auswahlboxen inklusive Zugangsdaten-/
  Verfügbarkeits-Hinweisen, belegt das Formular mit dem zuletzt
  gespeicherten Stand vor (`settings_store.py`), und ruft bei Klick auf
  "Dokument analysieren und Kosten schätzen" `/api/analyze` auf und
  rendert das Ergebnis (Kostenschätzung, Warnungen, Live-Kontingent bei
  DeepL) - mit denselben Platzhalter-Vorlagen wie die Qt-App
  (`analysis.summary` usw.), dafür ein kleiner Formatierer für Pythons
  `{wert:,}`/`{wert:.2f}`-Syntax innerhalb der Katalog-Strings. Die
  Quelldatei-Auswahl ist im Browser noch ein einfaches Textfeld (ein
  absoluter Pfad pro Zeile, deutlich als Übergangslösung markiert) - ein
  `<input type="file">` liefert im Browser aus Sicherheitsgründen keinen
  echten Dateisystempfad, genau der praktische Grund, warum pywebview
  mit seinem `create_file_dialog()` gewählt wurde (Schritt 6). Der
  "Übersetzung starten"-Button existiert schon im Layout, bleibt aber
  bewusst deaktiviert - `/api/jobs` kommt erst in Schritt 4.

  **Getestet:** Gesamter Testlauf (`tests/`, ohne `test_ui_images_mode.py`):
  212 passed (vorher 209), 1 skipped - keine Regressionen. Neu in
  `tests/test_webapp_images_api.py`: `/` liefert echtes `index.html` mit
  korrektem Content-Type, `/app.js`/`/i18n/de.json` werden mit korrektem
  Content-Type ausgeliefert (inklusive Prüfung des tatsächlichen JSON-
  Inhalts), ein Pfad-Traversal-Versuch (`/../job_bridge.py`) liefert 404
  ohne Dateiinhalt preiszugeben. Zusätzlich von Hand geprüft (nicht nur
  über die Test-Suite): Server real gestartet, `/`, `/app.js`, `/api/config`
  und ein echter `/api/analyze`-Aufruf gegen `demo_1_original.png` mit
  echtem Tesseract-OCR - Kostenschätzung kam mit dem korrekten
  `max_chars_per_run: 200000` zurück (bestätigt den Schritt-2-Fix).

  **Noch offen (Schritte 4-8 laut Plan):** `/api/jobs`
  (Start/Status/Abbruch/Ergebnis, eigener Hintergrund-Thread), das
  Bestätigungs-Gate Ende-zu-Ende inklusive serverseitiger Nachprüfung,
  der pywebview-Bootstrap mit `create_file_dialog()` statt dem
  Textfeld-Provisorium, die QA-Bericht-Anzeige, und zuletzt die
  `review_server.py`-Übergabe.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 4 abgeschlossen:
  `/api/jobs` (Start/Status/Abbruch/Ergebnis).** Erste Route mit echten
  Nebenwirkungen (kostet Anbieter-Budget, schreibt Dateien) - deshalb laut
  Plan der riskanteste Teil bisher (Thread-Lebenszyklus,
  Abbruch-Race, State-Konsistenz unter gleichzeitigem Poll+Schreiben) und
  am gründlichsten getestet.

  `webapp/job_bridge.py::start_job()` prüft VOR dem Start dieselben
  Fail-Fast-Bedingungen serverseitig noch einmal, die `ui/app.py::_start()`
  auch prüft - `validation_errors()`, `credential_status()`,
  `ocr_engine_available()`, `inpainting_backend_available()`. Das ist
  bewusst redundant zu einem vorherigen `/api/analyze`-Aufruf: das
  RoadMap-Leitprinzip verlangt die Prüfung vor JEDEM Lauf, nicht nur
  irgendwann vorher im selben Browser-Tab - ein Client, der direkt
  `/api/jobs` aufruft ohne vorher zu analysieren, wird genauso abgewiesen.
  Die eigentliche Verdrahtung im Frontend (Button erst nach erfolgreicher
  Analyse aktiv) ist Schritt 5, nicht dieser.

  Läuft auf einem eigenen `threading.Thread` (kein `QThreadPool` - `webapp/`
  hat keine Qt-Event-Loop) und ruft exakt dieselbe `run_image_batch_job()`
  auf, die auch `ui/workers.py::ImageTranslationWorker` schon verwendet -
  gleiche kooperative Abbruch-Logik über ein `threading.Event`
  (`should_cancel`), gleiche Progress-/Stats-/Total-Callbacks, nur per
  HTTP-Polling statt Qt-Signalen abgefragt (750ms-1s laut Plan). Job-Status
  liegt komplett im Arbeitsspeicher (kein Neustart-sicherer Zustand - dieselbe
  "ein lokaler Nutzer, ein Serverprozess"-Annahme wie schon bei
  `settings_store.py`), immer nur EIN aktiver Lauf gleichzeitig
  (`_ACTIVE_JOB_ID`) - ein zweiter `/api/jobs`-Aufruf während eines
  laufenden Jobs wird mit "Ein Lauf ist bereits aktiv." abgelehnt, exakt
  der ausdrückliche Nicht-Ziel-Punkt des Plans ("kein Mehrfach-Job-Betrieb").

  `webapp/server.py` bekam dafür erstmals dynamisches Routing
  (`/api/jobs/<id>/status`/`/cancel`/`/result`, per Regex statt einer
  Templating-Bibliothek - passt zum bestehenden "kein Framework"-Stil).

  **Getestet:** Neue `tests/test_webapp_jobs_api.py` (8 Tests, echte
  HTTP-Aufrufe, kein Mocking von `webapp.server`/`webapp.job_bridge`
  selbst): ein voller Ende-zu-Ende-Lauf mit einem echten generierten
  Testbild, echtem Tesseract-OCR und einem `FakeProvider` (per
  `monkeypatch` auf `ui.image_job.build_provider` injiziert, exakt wie
  bereits `tests/test_image_batch_job.py` es für `run_image_batch_job()`
  selbst tut - `job_bridge.py` bietet bewusst keine `provider=`-Injektion
  für HTTP-Aufrufer an, ein Web-Client geht immer über die echte
  Registry), Status-Polling bis "done", Ergebnis-Abruf inkl. echter
  Ausgabedatei und QA-Bericht auf der Platte; Ablehnung bei leerer
  Quelldateiliste, fehlendem Zielordner, nicht verfügbarer OCR-Engine
  (`google_vision` - in dieser Umgebung nachweislich nicht konfiguriert,
  siehe Schritt-2/3-Testdatei) und fehlendem API-Schlüssel; ein zweiter
  Job während eines laufenden (mit einem künstlich verlangsamten
  `FakeProvider`, um die Race deterministisch statt zeitabhängig zu
  testen) wird abgelehnt; unbekannte Job-IDs und ein Abbruch-Versuch nach
  Abschluss liefern die erwarteten Fehlermeldungen. Gesamter Testlauf
  (`tests/`, ohne `test_ui_images_mode.py`): 220 passed (vorher 212), 1
  skipped - keine Regressionen. `webapp.server`/`webapp.job_bridge`
  importieren weiterhin nachweislich ohne `PySide6`.

  **Noch offen (Schritte 5-8 laut Plan):** das Bestätigungs-Gate
  Ende-zu-Ende im Frontend verdrahtet (Start-Button erst nach
  erfolgreicher Analyse nutzbar, mit gezieltem Test gegen die
  serverseitige Nachprüfung ohne vorheriges `/api/analyze`), der
  pywebview-Bootstrap mit `create_file_dialog()`, die QA-Bericht-Anzeige,
  und zuletzt die `review_server.py`-Übergabe.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 5 abgeschlossen:
  Bestätigungs-Gate Ende-zu-Ende verdrahtet.** Die serverseitige Hälfte
  des Gates (die Fail-Fast-Prüfungen in `start_job()`) stand technisch
  schon seit Schritt 4, da `start_job()` nie geprüft hat, ob vorher
  `/api/analyze` aufgerufen wurde - neu ist die FRONTEND-Hälfte plus ein
  Test, der diese Unabhängigkeit ausdrücklich benennt statt sie nur
  beiläufig mitzubeweisen.

  `app.js` bekam eine Zustandsmaschine, die `ui/app.py`s eigene
  `_start_blocked_reason()`/`_invalidate_analysis()`/`_analysis_finished()`
  spiegelt: der Start-Button bleibt deaktiviert, bis (1) eine Analyse
  erfolgreich war UND (2) die neue Checkbox "Analyse und Kostenschätzung
  geprüft" angehakt ist. Jede Änderung an einem preisrelevanten Feld
  (Quelle, Anbieter, Sprachen, geschützte Begriffe, OCR-Engine,
  Rückschreibe-Methode) entwertet eine vorhandene Analyse sofort wieder -
  genau dieselben Feld-Änderungssignale, an die auch `ui/app.py`s
  `_invalidate_analysis()` gebunden ist. Wie in der Qt-App bleibt die
  Checkbox deaktiviert, wenn die Schätzung das Zeichen-Lauflimit
  überschreitet (`cost.within_run_limit`) - ein Überschuss lässt sich
  ansehen, aber nicht bestätigen. Nach jedem abgeschlossenen Lauf (fertig,
  abgebrochen oder fehlgeschlagen) verlangt der nächste Start wieder eine
  frische Analyse.

  Neu im Formular: ein Zielordner-Textfeld (`output_dir` für `/api/jobs`,
  dieselbe Interims-Begründung wie beim Quellpfade-Textfeld - Schritt 6
  ersetzt beide durch `pywebview.create_file_dialog()`), ein
  Abbrechen-Button (verdrahtet auf `/api/jobs/<id>/cancel`), ein
  Bestätigungsdialog vor dem eigentlichen Start (`window.confirm()` mit
  demselben `start.confirm_summary_images`-Text wie Qt's
  `QMessageBox.question()` - `window.confirm()` bleibt unter pywebview in
  Schritt 6 ein natives Dialogfenster, keine Anpassung nötig), und ein
  Status-Polling (800ms, `job.progress_count_files`/`job.progress_prefix`)
  bis zum Ergebnis (`job.result_summary_images`).

  **Getestet:** Gesamter Testlauf (`tests/`, ohne `test_ui_images_mode.py`):
  221 passed (vorher 220), 1 skipped - keine Regressionen. Neuer,
  ausdrücklich benannter Test `test_start_job_enforces_checks_without_a_
  prior_analyze_call` (ergänzt den bereits bestehenden
  `test_start_job_runs_a_real_batch_end_to_end`, der ebenfalls nie
  `/api/analyze` aufruft) - beweist beide Richtungen: `/api/jobs`
  funktioniert UND lehnt korrekt ab, unabhängig davon, ob der Client
  vorher analysiert hat.

  Zusätzlich mit Playwright (im Sandbox bereits vorinstalliert, echter
  Chromium, kein Mock) von Hand gegen den echten laufenden Server
  geprüft, nicht nur über die Test-Suite: Start-Button und Checkbox
  starten deaktiviert; nach erfolgreicher Analyse wird die Checkbox
  aktiv, der Start-Button bleibt bis zum Anhaken blockiert; nach dem
  Anhaken wird gestartet; der `window.confirm()`-Dialog erscheint mit dem
  korrekten, mit echten Zahlen gefüllten Text; der Lauf (echtes Testbild,
  echtes Tesseract-OCR, `FakeProvider`) läuft durch bis zum Ergebnis mit
  korrektem Text; danach ist das Gate wieder blockiert. Keine
  JavaScript-Fehler in der Konsole (bis auf ein harmloses
  `favicon.ico`-404, das der Browser automatisch anfragt - keine eigene
  Route dafür angelegt, nicht Teil des Plans).

  **Noch offen (Schritte 6-8 laut Plan):** der pywebview-Bootstrap
  (`webapp/__main__.py`, `create_file_dialog()` ersetzt die beiden
  Textfelder für Quelle/Zielordner), die QA-Bericht-Anzeige, und zuletzt
  die `review_server.py`-Übergabe.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 6 abgeschlossen:
  pywebview-Bootstrap mit echten nativen Datei-/Ordner-Dialogen.**
  Neu: `webapp/__main__.py` (`python -m webapp`) - startet
  `create_server()` wie bisher auf einem Hintergrund-Thread, öffnet aber
  jetzt statt "Seite im normalen Browser öffnen" (Schritt 3) ein echtes
  natives `pywebview`-Fenster (`webview.create_window(...)` +
  `webview.start(gui="qt")`) mit einer kleinen `Api`-Klasse
  (`pick_images()`/`pick_output_dir()`), die per `js_api=` an das Fenster
  gebunden und dem Frontend als `window.pywebview.api.*` sichtbar wird.
  `app.js` erkennt per Feature-Test (`window.pywebview` vorhanden ODER
  `pywebviewready`-Event abwarten), ob es in pywebview oder einem
  normalen Browser läuft, und blendet nur dann zwei neue
  "...auswählen"-Buttons neben den Quell-/Zielordner-Textfeldern ein, die
  echte OS-Dialoge öffnen (`webview.FileDialog.OPEN`/`.FOLDER`) statt der
  bisherigen manuellen Pfadeingabe - im normalen Browser (`python -m
  webapp.server`) bleiben die Textfelder unverändert die einzige
  Möglichkeit, da ein `<input type="file">` dort keinen echten
  Dateisystempfad preisgibt.

  Als GUI-Backend wurde bewusst `gui="qt"` gewählt statt GTK: pywebview
  braucht dafür zusätzlich nur `qtpy` (dünne PySide6/PyQt-Abstraktion),
  nutzt aber ansonsten dasselbe PySide6/QtWebEngine, das die Qt-App
  ohnehin schon voraussetzt - keine neue, schwere GUI-Abhängigkeit.
  `requirements.txt` bekam `pywebview` und `qtpy` dazu, mit einem
  Kommentarblock zu einer echten, in dieser Sandbox nachgewiesenen
  Installationsfalle: pywebviews Abhängigkeit `proxy_tools` (einzige
  verfügbare Version 0.1.0) hat ein sehr altes `setup.py`, das gegen ein
  neueres, distro-gepatchtes `setuptools` (hier: 68.1.2) mit
  `AttributeError: install_layout. Did you mean: 'install_platlib'?`
  fehlschlägt - `--no-build-isolation` behebt das NICHT, da weiterhin das
  Vorhandene System-`setuptools` genutzt wird. Verifizierter Fix (mit
  geleertem pip-Cache gegengeprüft, damit kein gecachtes Wheel den realen
  Fehler verdeckt): vor der Installation `pip install --upgrade
  "setuptools>=70"` ausführen. Relevant nur, falls Michael beim
  Einrichten auf seinem echten Rechner denselben Fehler sieht.

  `webapp/__init__.py`s Docstring wurde präzisiert: die Regel "kein
  PySide6-Import" gilt weiterhin für die HTTP-Schicht selbst
  (`server.py`, `job_bridge.py`, `settings_store.py` und alles, was diese
  aus `ui`/`pipeline` mitziehen) - `__main__.py` ist die eine bewusste
  Ausnahme, da sein einziger Zweck das Öffnen eines nativen GUI-Fensters
  ist und es damit zwangsläufig über pywebviews eigenes
  Qt/QtWebEngine-Backend von Qt abhängt. Diese Abhängigkeit bleibt auf
  `__main__.py` beschränkt - der von dort auf einem Hintergrund-Thread
  gestartete HTTP-Server selbst bleibt exakt so Qt-frei wie zuvor (erneut
  per `sys.meta_path`-Sperrtest nachgewiesen, diesmal nur noch gezielt für
  `webapp.server`/`webapp.job_bridge`, nicht mehr für `webapp.__main__`,
  das erwartungsgemäß Qt braucht).

  **Echter, im Bugfix endender Fund beim Testen (nicht durch bloßes
  Lesen des Codes):** Während der Regressionsprüfungen für die zwei neuen
  Auswahl-Buttons (die wie `#cancel-button` aus Schritt 5 das Muster
  `class="hidden"` nutzen) fiel auf, dass in `app.css` bislang nur die
  eng gefasste Regel `.result.hidden { display: none; }` existierte -
  eine bloße `class="hidden"` ohne die `.result`-Elternklasse hat also
  NIE gegriffen. Das bedeutet: der Abbrechen-Button aus Schritt 5 war seit
  dem Versand an Michaels Gerät durchgehend sichtbar, obwohl `app.js`s
  `classList.add("hidden")`/`.remove("hidden")`-Aufrufe die ganze Zeit
  korrekt liefen - nur visuell wirkungslos. Behoben durch eine generische,
  ungebundene `.hidden { display: none; }`-Regel in `app.css`, mit einem
  erklärenden Kommentar, damit derselbe Fehler nicht bei einem künftigen
  neuen Element wiederholt wird. Diese Korrektur ist bereits Teil des
  heute ausgelieferten `app.css`.

  **Getestet:** Neu `tests/test_webapp_main.py` (7 Tests) - `Api.
  pick_images()`/`pick_output_dir()` gegen ein gefälschtes
  `webview.active_window()` (Auswahl/Abbruch/kein-Fenster-Fall), sowie ein
  Test, der `main()` mit gefälschten `webview.create_window()`/`.start()`
  aufruft und prüft, dass Titel, URL, `js_api`-Instanz und `gui="qt"`
  korrekt übergeben werden, ohne dass tatsächlich ein Fenster geöffnet
  wird. Ein echtes natives Datei-/Ordner-Dialogfenster lässt sich in
  dieser Sandbox nicht per Klick durchsteuern - dieselbe bereits
  dokumentierte Grenze wie bei `tests/test_ui_images_mode.py`s
  Qt-Dialogen. Zusätzlich einmal von Hand ein ECHTES pywebview-Fenster
  unter `xvfb-run` (echtes virtuelles X, nicht `offscreen` - das schlug
  mit GL/Vulkan-Fehlern fehl) mit echtem QtWebEngine gestartet
  (`QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu"`, nötig weil
  diese Sandbox als root läuft - auf Michaels echtem Rechner nicht
  relevant) und per `evaluate_js()` geprüft: Fenstertitel korrekt,
  `window.pywebview.api.pick_images`/`pick_output_dir` beide als
  Funktionen vorhanden, alle 4 Anbieter geladen, Start-Button korrekt
  deaktiviert, und - nach dem CSS-Fix - beide Auswahl-Buttons sichtbar
  sowie der alte Hinweistext-Hinweis für die Quellpfade korrekt
  ausgeblendet. Zusätzlich Playwright-Regressionsprüfungen im normalen
  Browser ergänzt: ohne `window.pywebview` bleiben beide neuen Buttons
  ausgeblendet und der Interims-Hinweistext sichtbar - das ist exakt der
  Fall, in dem der oben beschriebene CSS-Fehler beim Abbrechen-Button
  bisher unbemerkt blieb. Gesamter Testlauf (`tests/`, ohne
  `test_ui_images_mode.py`): 228 passed (vorher 221), 1 skipped - keine
  Regressionen.

  **Noch offen (Schritte 7-8 laut Plan):** die QA-Bericht-Anzeige, und
  zuletzt die `review_server.py`-Übergabe.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 7 abgeschlossen:
  QA-Bericht-Anzeige inline pro Bild.** Neuer Endpunkt `GET
  /api/jobs/<id>/qa-report?file=...` (`webapp/job_bridge.py::
  job_qa_report()`, verdrahtet in `webapp/server.py`) liefert den
  Rohtext EINES Bildes QA-Bericht. Das Ergebnis (`#job-result`) listet
  jetzt jedes Bild einzeln auf (Dateiname, Statistik wie
  `job.stats_summary`) mit einem Button, der den Bericht direkt inline
  in einem `<pre>` ein-/ausblendet, statt ihn extern zu öffnen - genau
  die im Plan vorgesehene Alternative zu `QDesktopServices.openUrl()`.

  Wichtig dabei: die Bild-Modus-Qt-App hat für diesen Fall gar kein
  Äquivalent - `ui/app.py::_show_job_result()` blendet den
  "QA-Bericht öffnen"-Button für `ImageBatchJobResult` bewusst aus (ein
  Bericht PRO Bild, kein einzelner) und verweist stattdessen nur auf
  "Ordner öffnen". Die Web-Oberfläche kann das nicht 1:1 nachbauen (kein
  natives "Ordner öffnen" ohne eigene pywebview-API dafür, nicht Teil
  dieses Plans), bietet dafür aber etwas, das die Qt-App im Bild-Modus
  gar nicht hat: den Bericht direkt ansehen, ohne den Ausgabeordner
  überhaupt selbst zu öffnen - eine echte Verbesserung, kein bloßer
  Port.

  **Sicherheit bewusst mitgedacht:** der `file`-Query-Parameter ist kein
  freier Dateisystempfad. `job_qa_report()` akzeptiert NUR einen Pfad,
  der exakt einem der `qa_report`-Pfade aus dem eigenen `job_result()`
  dieses Laufs entspricht (Allow-Liste, keine bloße
  Existenzprüfung) - ohne diese Prüfung könnte diese lokale, nicht
  authentifizierte Serverinstanz (siehe `webapp/server.py`s eigener
  Docstring: "LOCAL ONLY - no auth") über `?file=/beliebiger/pfad` jede
  für den Prozess lesbare Datei ausliefern. Dieselbe Klasse Fehler, vor
  der `server.py::_serve_static()`s Pfad-Traversal-Check für statische
  Dateien schon schützt, hier nur für ein dynamisches Argument statt
  eines festen Verzeichnisses.

  Neue i18n-Schlüssel in `ui/i18n_data.py` (`job.show_report`,
  `job.hide_report`, `job.report_load_error`) - von der Qt-App nicht
  verwendet, genau wie schon `dialog.choose_images`/`job.cancel` usw.
  seit Schritt 6, aber weiterhin an derselben zentralen Stelle gepflegt
  statt in einer separaten webapp-eigenen Kopie; `webapp/static/i18n/
  {de,en}.json` frisch aus `ui/i18n_data.py` neu exportiert
  (`python -m webapp.tools.export_i18n`, jetzt 161 statt 158 Schlüssel).

  **Getestet:** Vier neue Tests in `tests/test_webapp_jobs_api.py`:
  ein voller Ende-zu-Ende-Lauf, dessen QA-Bericht-Text über die neue
  Route abgerufen und Byte für Byte gegen dieselbe Datei verglichen
  wird, die direkt von der Platte gelesen wurde (beweist echten Inhalt,
  keine Platzhalter-Antwort); ein gezielter Sicherheitstest, der
  versucht, eine echte, existierende, aber NICHT zum Job gehörende Datei
  (dieses Testmodul selbst) über den `file`-Parameter zu lesen - bewusst
  eine echte Datei statt eines nicht existierenden Pfads, damit die
  Prüfung nachweislich eine Allow-Liste ist und keine bloße
  `os.path.exists()`-Prüfung, durch die eine echte Datei einfach
  durchrutschen würde; unbekannte Job-ID; Abruf-Versuch, bevor der Lauf
  fertig ist (mit demselben künstlich verlangsamten `FakeProvider`-Trick
  wie beim bereits bestehenden Race-Test). Gesamter Testlauf (`tests/`,
  ohne `test_ui_images_mode.py`): 232 passed (vorher 228), 1 skipped -
  keine Regressionen. `webapp.server`/`webapp.job_bridge` importieren
  weiterhin nachweislich ohne `PySide6`.

  Zusätzlich mit Playwright von Hand gegen den echten laufenden Server
  geprüft (nicht nur die Test-Suite): nach einem echten Lauf erscheint
  genau eine Ergebniszeile mit dem Button "QA-Bericht anzeigen"; ein
  Klick lädt den echten Bericht ("Bildübersetzung - QA-Bericht ...") in
  das `<pre>`-Element und der Button wechselt auf "QA-Bericht
  ausblenden"; ein zweiter Klick blendet ihn wieder aus, ohne einen
  erneuten Request zu benötigen (Bericht wird höchstens einmal geladen,
  `loaded`-Flag in `app.js`). Keine neuen JavaScript-Fehler in der
  Konsole (weiterhin nur das schon dokumentierte harmlose
  `favicon.ico`-404).

  **Noch offen (Schritt 8 laut Plan):** die `review_server.py`-Übergabe -
  der riskanteste verbleibende Eingriff, da er einen bereits genutzten,
  bestehenden Ablauf (`image_translate_cli/cli.py::_cmd_review()`)
  aufspaltet; `_cmd_review()` wird danach erneut regressionsgeprüft.

  **Update (26.08.2026, direkt im Anschluss) - Schritt 8 abgeschlossen:
  `review_server.py`-Übergabe. Der Plan ist damit vollständig
  umgesetzt.** `image_translate_cli/review_server.py::run_review_session()`
  war bisher EIN blockierender Aufruf (bindet den Korrektur-Server, wartet
  bis "Anwenden"/"Abbrechen"/Zeitüberschreitung, gibt erst danach
  zurück) - für `webapp/` unbrauchbar, da ein HTTP-Request-Handler nie
  bis zu 30 Minuten auf einen Menschen in einem separaten Browser-Tab
  warten darf. Aufgespalten (wie im Plan vorgesehen) in
  `start_review_server()` (bindet, startet, gibt sofort eine neue
  `ReviewSession` mit fertiger `.url` zurück - blockiert nicht) und
  `ReviewSession.wait()` (die bisherige Blockier-/Wartelogik, jetzt
  separat aufrufbar). `run_review_session()` selbst ist nur noch ein
  dünner Wrapper aus beidem - exakt dieselbe Signatur, dasselbe
  Verhalten wie vorher, `image_translate_cli/cli.py::_cmd_review()`
  unverändert lauffähig.

  Neues `webapp/review_bridge.py`: `POST /api/jobs/<id>/files/<index>/
  correct` startet `start_review_server()` für EIN Bild aus einem
  abgeschlossenen Batch-Lauf (Quelle = `target.source_path`, Regionen =
  `target.stats.replacements` - dieselben Werte, die
  `ui/app.py::_open_image_correction_dialog()` auch an
  `ImageCorrectionDialog` übergibt) und antwortet SOFORT mit
  `{correction_id, url}`, ohne zu blockieren. Ein eigener
  Hintergrund-Thread ruft danach `ReviewSession.wait()` auf und
  reagiert je nach Ausgang: bei "Anwenden" wird
  `ui/image_job.py::run_image_correction_job()` aufgerufen (dieselbe
  Funktion, die `ImageCorrectionDialog._apply()` in der Qt-App auch
  nutzt) und das Ergebnis per neuem `job_bridge.apply_correction_result()`
  an derselben Position in `job.result.stats.results` gespliced -
  dieselbe Splice-Logik wie `_open_image_correction_dialog()`, nur nach
  Index statt nach Python-Objektidentität adressiert. `GET
  /api/corrections/<id>/status` wird vom Frontend gepollt (dieselbe
  "Polling statt Push"-Entscheidung wie beim Job-Status) und liefert bei
  "applied" das schon aktualisierte Datei-Objekt gleich mit.

  Ein zweiter gleichzeitiger Korrektur-Versuch auf DASSELBE Bild wird
  abgelehnt ("Für dieses Bild läuft bereits eine Korrektur.") - dieselbe
  "eine Sache gleichzeitig"-Grundidee wie `_ACTIVE_JOB_ID` für ganze
  Läufe, hier nur pro Bild statt pro Job; zwei VERSCHIEDENE Bilder
  desselben Laufs dürfen weiterhin gleichzeitig in zwei Tabs korrigiert
  werden.

  **Frontend:** jede Ergebniszeile mit korrigierbaren Regionen (Schritt
  7) bekommt jetzt zusätzlich einen "Übersetzung korrigieren"-Button.
  Klick startet die Korrektur, öffnet die zurückgegebene URL per
  `window.open()` und pollt bis zum Ergebnis, ohne die Hauptseite zu
  blockieren; bei "applied" wird die komplette Dateizeile neu gerendert
  (frischer QA-Bericht-Button statt des jetzt veralteten Berichtstexts).

  **Empirisch geklärt, was der Plan als offene Frage benannt hatte
  ("`window.open()` - in pywebview typischerweise ein neues natives
  Fenster statt Browser-Tab, aber plattformabhängig, muss in Schritt 6
  empirisch geprüft werden"):** unter pywebviews Qt-Backend ist das
  NICHT der Fall. `webview.platforms.qt.py`s `WebPage.createWindow()`
  fängt jede `window.open()`-Anfrage ab und übergibt sie an
  `NavigationHandler.acceptNavigationRequest()`, die (Standardeinstellung
  `OPEN_EXTERNAL_LINKS_IN_BROWSER = True`, in dieser Sandbox nachgewiesen
  über einen echten pywebview-Lauf unter `xvfb-run` mit einem
  monkeypatchten `webbrowser.open()`, das den Aufruf aufgezeichnet hat)
  `webbrowser.open()` aufruft - die URL landet also im System-
  Standardbrowser, NICHT in einem zweiten nativen pywebview-Fenster. Für
  diesen Anwendungsfall ist das genau richtig: das Haupt-App-Fenster
  bleibt dabei unblockiert weiter nutzbar (die Polling-Schleife läuft im
  selben Fenster weiter), während die Korrektur in einem gewöhnlichen
  Browser-Tab passiert - kein Sonderfall für pywebview nötig, dieselbe
  `window.open()`-Zeile funktioniert im normalen Browser (Schritt 3)
  identisch.

  **Getestet:** Zwei neue Testdateien. `tests/test_review_server.py` (6
  Tests, KEIN Browser - ein Hintergrund-Thread spielt exakt dieselben
  GET/POST-Aufrufe nach, die `_PAGE_HTML`s eigenes JS macht): beweist,
  dass `start_review_server()` sofort mit einer nutzbaren `.url`
  zurückkehrt, dass `ReviewSession.wait()` alle drei Ausgänge
  (apply/cancel/timeout) korrekt liefert, dass `run_review_session()`
  als dünner Wrapper `webbrowser.open()` weiterhin mit der richtigen URL
  aufruft und blockiert bis zur Aktion, UND (erste Testdatei überhaupt
  für `image_translate_cli/cli.py::main()`) dass der komplette `review`-
  Unterbefehl Ende-zu-Ende noch funktioniert - Regionen-Datei einlesen,
  Korrektur-Server starten, "Anwenden" simulieren, Exit-Code und
  neu gerenderte Datei prüfen.

  `tests/test_webapp_correction_api.py` (6 Tests, echte HTTP-Aufrufe
  gegen einen laufenden `webapp.server`, kein Mocking von
  `webapp.review_bridge`/`webapp.job_bridge` selbst): ein voller Lauf
  von Batch-Übersetzung bis Korrektur - Bild übersetzen, Korrektur
  starten, als "Browser" gegen die zurückgegebene Korrektur-URL
  `/api/state`+`/api/apply` mit bearbeitetem Text aufrufen, per Polling
  auf "applied" warten, prüfen, dass `/api/jobs/<id>/result` jetzt den
  korrigierten QA-Bericht ("... nach manueller Korrektur ...") liefert;
  derselbe Ablauf mit "Abbrechen" statt "Anwenden" lässt das
  Job-Ergebnis nachweislich unverändert; ein zweiter gleichzeitiger
  Korrektur-Versuch auf dasselbe Bild wird abgelehnt; unbekannte
  Job-ID/Datei-Nummer/Korrektur-ID liefern die erwarteten Fehler.
  Gesamter Testlauf (`tests/`, ohne `test_ui_images_mode.py`): 244
  passed (vorher 232), 1 skipped - keine Regressionen.
  `webapp.server`/`webapp.job_bridge`/`webapp.review_bridge` importieren
  weiterhin nachweislich ohne `PySide6`.

  Zusätzlich mit Playwright von Hand gegen den echten laufenden Server
  geprüft, inklusive Popup-Fenster-Handling (`page.context.expect_page()`):
  nach einem echten Übersetzungslauf öffnet "Übersetzung korrigieren"
  tatsächlich `review_server.py`s eigene Seite in einem neuen
  Browser-Tab, dort wurde der übersetzte Text bewusst bearbeitet
  ("Hallo (Schritt-8-Testkorrektur)") und "Anwenden" geklickt - die
  Hauptseite hat den Ausgang per Polling erkannt ("Korrektur
  angewendet."), und ein danach neu geladener QA-Bericht zeigt
  nachweislich den Korrektur-Header ("... nach manueller Korrektur
  ..."), nicht mehr den ursprünglichen. Keine neuen JavaScript-Fehler in
  der Konsole (weiterhin nur das schon dokumentierte harmlose
  `favicon.ico`-404).

  **Damit ist der komplette Walking-Skeleton-Plan
  (`/root/.claude/plans/moonlit-humming-brook.md`) umgesetzt** - der
  Bild-Übersetzungs-Modus läuft jetzt Ende-zu-Ende über den lokalen
  Server + pywebview: Quellbilder wählen (native Dialoge), konfigurieren,
  Kostenschätzung mit Bestätigungs-Gate, Lauf mit Live-Fortschritt,
  QA-Bericht pro Bild inline, und jetzt auch die manuelle Korrektur im
  Browser. PDF/Word/PPTX bleiben wie geplant unverändert auf der
  bestehenden Qt-App. Ausdrücklich nicht Teil dieses Plans (siehe dessen
  eigener "Ausdrücklich nicht Teil"-Abschnitt) und weiterhin offen: kein
  Installer/Packaging, keine CI-Workflow-Datei, kein Einbetten
  übersetzter Bilder zurück in PDF/Word/PPTX, keine Entfernung der
  bestehenden Qt-App - das bleibt eine separate, künftige Entscheidung,
  kein automatischer Folgeschritt dieses Piloten.

## 26.08.2026 - Erstes echtes Nutzer-Feedback nach dem Umbau: Fortschrittsbalken + "Ordner öffnen"-Button umgesetzt, zwei größere Punkte (Font-Erkennung, Vorschau-Genauigkeit) als offene Entscheidung dokumentiert

  Michael hat die neue Server-+pywebview-App zum ersten Mal gegen ein
  echtes, komplexes Bild getestet ("Spirit - Soul - Meatsuit.jpg", eine
  esoterische Infografik mit vielen Textregionen) und detailliertes
  Feedback gegeben (zwei Screenshots, ein QA-Bericht als Beleg):

  > "Was fehlt ist eine Fortschrittsanzeige. Ich sehe nur in der Shell
  > das etwas passiert."
  >
  > "Ich bin beeindruckt. Es schaut echt gut aus. Die Boxen verändern
  > ist super handabbar. Wenn man ein einzelnes Bild bearbeitet. Also
  > für eine Nachbearbeitung super."
  >
  > "Aber es fehlt noch die Font Erkenneung. Siehe Bild. Man sieht es
  > deutlich an der Überschrift. Wenn man noch einen Font Editor bei
  > der Korrektur noch hätte, wäre super. Schön das die Felder so
  > transparent sind, dann kann man das Original dahier sehen oder
  > eben kurz wegschieben."
  >
  > "Allerdings wird nach dem Übernehmen das Bild nicht so gespeichert
  > wie es in der Browservorschau angezeigt wird."
  >
  > "Es fehlt auch noch ein Button um den Zielordner, nachdem das Bild
  > generiert wurde, zu öffnen."

  Auf Rückfrage (drei gezielte Fragen, da die Meldungen mehrdeutig
  waren) hat Michael präzisiert: er weiß nicht, ob sich der
  Fortschrittstext im Fenster überhaupt bewegt oder einfach nur zu
  unauffällig ist; bei der Font-Erkennung wünscht er sich AUTOMATISCHE
  Erkennung aus dem Bild (nicht nur einen manuellen Font-Editor); bei
  der Vorschau-Diskrepanz weicht auch Position/Layout ab, nicht nur die
  Schrift.

  **Umgesetzt (dieser Eintrag):**

  1. Ein unbestimmter ("indeterminate") Fortschrittsbalken
     (`#job-progress-bar` in `webapp/static/index.html`, bewusst OHNE
     `value`-Attribut) wird jetzt während eines laufenden Auftrags
     eingeblendet und danach wieder versteckt (`webapp/static/app.js`s
     `runStart()`/`finishJob()`). Bewusst kein Prozentwert: echter
     Fortschritt ist laut `ui/image_job.py::ImageBatchStats`s eigenem
     Docstring nur auf DATEI-Ebene bekannt, nicht auf Regionen-Ebene -
     bei einem Ein-Bild-Batch mit vielen OCR-Regionen (genau Michaels
     Testfall) bliebe ein Prozentwert die ganze Laufzeit über bei 0%
     "hängen", was irreführender wäre als gar kein Balken. Die bereits
     vorhandene Detailzeile (`#start-status`,
     `job.progress_prefix`/"Verarbeite: ...") lief bei Prüfung
     nachweislich schon vorher korrekt durch (`_notify()` in
     `pipeline/images/translate_image.py` →
     `webapp/job_bridge.py`s `_progress()` → `GET .../status` →
     `renderJobProgress()`) - kein Bug gefunden, nur zu unauffällig; der
     neue Balken macht die laufende Aktivität jetzt zusätzlich auf den
     ersten Blick sichtbar, ohne die Detailzeile zu ersetzen.

  2. Ein "Ordner öffnen"-Button (`#open-output-folder-button`, nur unter
     pywebview sichtbar wie die Datei-/Ordner-Auswahl-Buttons aus
     Schritt 6) erscheint jetzt neben dem Job-Ergebnis und öffnet
     `result.output_dir` im Dateimanager des Betriebssystems - neue
     Methode `Api.open_folder(path)` in `webapp/__main__.py`, da
     pywebview selbst keinen "vorhandenen Ordner im Dateimanager
     anzeigen"-Aufruf mitbringt (`create_file_dialog()` öffnet nur
     Auswahl-Dialoge). Shellt je nach `platform.system()` auf
     `xdg-open`/`open`/`os.startfile()` aus - dasselbe, was
     `QDesktopServices.openUrl()` intern für die bestehende Qt-App tut
     (siehe `ui/app.py::_open_output_folder()`). Fehlerfall (Pfad
     existiert nicht, Start schlägt fehl) liefert `False` statt eine
     Exception über die JS-Bridge zu werfen - `app.js` zeigt dann
     `job.open_folder_failed` in der Statuszeile. Der bereits
     vorhandene i18n-Schlüssel `job.open_folder` (bisher nur von der
     Qt-App verwendet) wird für diesen Button wiederverwendet.

  **Beim Bau gefundener und behobener Bug (vor dem Versand, nicht erst
  bei Michael aufgefallen):** die erste Fassung der CSS-Regeln für
  beide neuen Elemente setzte `display: block` direkt am ID-Selektor
  (`#job-progress-bar { display: block; ... }` bzw.
  `#open-output-folder-button { display: block; ... }`). Eine
  ID-Selektor-Regel hat eine HÖHERE CSS-Spezifität als die generische
  Klassen-Regel `.hidden { display: none; }` - unabhängig von der
  Reihenfolge im Stylesheet hätte das `.hidden` IMMER überstimmt und
  beide Elemente dauerhaft sichtbar gelassen, exakt dieselbe Art Fehler,
  die laut `app.css`s eigenem Kommentar schon einmal beim Bau von
  Schritt 6 passiert ist ("MUSS eine plain, unscoped .hidden-Regel
  bleiben"). Durch den erweiterten Playwright-Smoke-Test aufgefallen
  (`assert not page.is_visible("#job-progress-bar")` direkt nach
  Seitenaufbau schlug fehl), nicht durch manuelles Anschauen. Behoben:
  `display: block` beim Fortschrittsbalken lebt jetzt unter einem
  eigenen `#job-progress-bar:not(.hidden)`-Selektor (greift nur, wenn
  die Klasse ohnehin fehlt - dann gibt es keinen Konflikt mehr mit
  `.hidden`); beim Ordner-Button wurde die `display`-Angabe ganz
  entfernt (Buttons sind standardmäßig `inline-block`, und das
  vorangehende `#job-result-summary` ist ohnehin ein Block-Element - der
  Button landet also auch ohne eigenes `display` in einer neuen Zeile).

  **Getestet:** `tests/test_webapp_main.py` um 5 Tests für
  `Api.open_folder()` erweitert (Linux/`xdg-open`,
  macOS/`open`, Windows/`os.startfile()`, nicht-existierender
  Pfad, fehlgeschlagener Start) - `subprocess.Popen`/`os.startfile`
  gemockt, `platform.system()` gemockt, `tmp_path` ist ein ECHTES
  Verzeichnis (`is_dir()` läuft also real). Gesamter Testlauf
  (`tests/`, ohne `test_ui_images_mode.py`): 249 passed (vorher 244), 1
  skipped. `webapp/`-Schicht importiert weiterhin nachweislich ohne
  `PySide6`.

  Playwright-Smoke-Test (`/tmp/pw_smoke.py`) um Prüfungen für beide
  neuen Elemente erweitert: Balken startet versteckt, wird sichtbar
  sobald der Lauf beginnt (bleibt dabei ohne `value`-Attribut =
  indeterminate), verschwindet wieder sobald der Lauf fertig ist; der
  "Ordner öffnen"-Button bleibt im normalen (nicht-pywebview) Browser
  während des GESAMTEN Ablaufs versteckt, auch nachdem `#job-result`
  selbst sichtbar wird (derselbe Regressionstest-Stil wie die
  bestehende Schritt-6-Prüfung für die Datei-/Ordner-Auswahl-Buttons).
  Der einzige Konsolenfehler bleibt das schon dokumentierte harmlose
  `favicon.ico`-404 (unabhängig reproduziert: sogar eine völlig
  eigenständige, leere Testseite ohne jeden Bezug zu diesem Projekt löst
  in dieser Chromium-Version denselben Fehler aus - kein neues Problem).

  **Bewusst NICHT in diesem Eintrag umgesetzt, sondern als offene
  Entscheidung an Michael zurückgespielt** (siehe Chat-Antwort):

  - **Font-Erkennung/-Editor:** Michael wünscht sich automatische
    Font-Erkennung aus dem Bild. Eine zuverlässige Schriftart-Erkennung
    per Bildanalyse bräuchte praktisch einen trainierten Klassifikator
    (Font-Familie aus einem gerenderten Textausschnitt zu erraten ist
    ein eigenständiges ML-Problem, keine Kleinigkeit) - ohne einen
    solchen wäre das Ergebnis unzuverlässig genug, um eher zu verwirren
    als zu helfen. Realistischere Zwischenschritte (manueller
    Font-Familie/Größe/Fett/Kursiv-Editor in der Korrektur-Ansicht,
    oder ein einfacher Hinweistext) wurden vorgeschlagen, aber noch
    nicht gebaut - Umfang/Aufwand ist mit Michael noch zu klären.

  - **Vorschau weicht von der gespeicherten Datei ab (auch bei
    Position/Layout, nicht nur Schrift):** Ursache gefunden.
    `pipeline/images/inpainting.py`s Renderer
    (`_vertical_room_below()`/`_horizontal_room()`) vergrößert/verschiebt
    Text-Boxen zur Laufzeit dynamisch, um Kollisionen mit
    Nachbarregionen zu vermeiden (horizontales Reflow, vertikales
    Wachstum, Mehrzeilen-Umbruch, Schriftgröße wird an diese DYNAMISCHE
    Box angepasst, nicht an die rohe OCR-Box). Die
    Browser-Korrektur-Vorschau (`image_translate_cli/review_server.py`s
    `_PAGE_HTML`) kennt davon nichts - sie zeigt ausschließlich die
    ROHE, STATISCHE OCR-Box (`region.x/y/width/height`) als CSS-Box.
    Das ist keine neue Regression, sondern eine von Anfang an bekannte,
    dokumentierte Einschränkung (`review_server.py`s eigener Docstring:
    "Deliberately NOT: ... a live re-rendered preview (would mean
    re-running InpaintingBackend.apply() on every keystroke; the
    overlay is a close-enough approximation without that cost)."). Eine
    wirklich pixelgenaue Vorschau würde bedeuten, die
    Kollisionsvermeidungs-Logik aus `inpainting.py` in JavaScript
    nachzubauen (oder bei jeder Änderung serverseitig neu zu rendern) -
    ein echter, nicht-trivialer Aufwand, noch nicht begonnen. Optionen
    dazu wurden Michael vorgeschlagen, noch keine Entscheidung
    getroffen.

## 26.08.2026 - "Übernehmen" verwarf Positions-/Größenkorrekturen: zwei separate Bugs gefunden und behoben; Fontgröße wird jetzt approximativ angezeigt

Michaels Feedback zur letzten Runde: *"...es scheint das am Schluss beim
Klicken auf übernehmen die Positionen, Grösse und Korrekturen nicht
übernommen werden. Also Live Rendering ist nicht erwünscht. Ich
verstehe darunter das ich erst alle Boxen korrigiere und erst dann
übernehme. [...] Wenigstens in etwas die Fontgrössen. Annähernd, nicht
genau. Ausserdem fehlte wieder der ganze linke Teil mit der Auflistung
um das Buch in der Kugel."* Drei Punkte, einzeln abgearbeitet:

**1) Positions-/Größenkorrekturen wurden nicht übernommen - zwei
unabhängige Bugs, beide gefunden und in einer echten Chromium-Sitzung
(nicht nur per Unit-Test) end-to-end nachgewiesen:**

- **Architektur-Bug:** `TextReplacement.region` war laut eigenem
  Docstring "die ORIGINAL erkannte OCR-Region", wurde aber von JEDEM
  Korrekturpfad (Qt-Dialog wie Browser-Korrektur) direkt überschrieben,
  sobald eine Box verschoben/vergrößert wurde. Da alle drei
  Rückschreibe-Backends (`BoxOverlayBackend`/`CvInpaintingBackend`/
  `GpuInpaintingBackend`) dieselbe `region` sowohl zum LÖSCHEN des
  Originaltexts als auch zum PLATZIEREN des übersetzten Texts nutzen,
  wurde die ursprüngliche englische Textstelle nie wirklich gelöscht,
  sobald `region` heimlich zur neuen Position wurde - an einer direkten
  Pixel-Reproduktion nachgewiesen (Originaltext blieb nach einer
  "Verschiebung" praktisch unverändert an der alten Stelle stehen).
  Behoben durch ein neues, separates Feld `TextReplacement.render_box`:
  `region` bleibt jetzt IMMER die wahre Original-Position (Löschen +
  Stil-Schätzung), `render_box` (falls gesetzt) ist die Stelle, an der
  tatsächlich gezeichnet wird - unterscheiden sich beide, wird auch die
  neue Zielstelle vor dem Zeichnen sauber freigeräumt. Betroffen und
  angepasst: alle drei Backends, `build_corrected_replacements()`
  (Qt-Dialog), `replacements_from_region_list()` (Browser-Korrektur +
  CLI `correct --regions`), sowie das gemeinsame JSON-Format in
  `report.py`/`regions_io.py` (neue, optionale `orig_x/y/width/height`-
  Felder, damit die wahre Originalposition beim Rundlauf über HTTP/Datei
  nicht verloren geht - bestehende Report-/`--regions`-Dateien bleiben
  dabei unverändert lesbar).

- **Zweiter, unabhängiger Bug in der Browser-Korrektur selbst** (erst
  durch eine echte, per Playwright gesteuerte Chromium-Sitzung
  gefunden, nicht durch Code-Lesen allein): `review_server.py`s
  `makeDraggable()` prüfte `if (e.target === textEl ...) return;` -
  da der Text-Layer die komplette Box optisch überdeckt (`width: 100%;
  height: 100%`), war `e.target` bei JEDEM Klick auf die sichtbare Box
  praktisch immer `textEl`. Ein Verschieben per Maus hat dadurch so gut
  wie NIE funktioniert (nur ein ca. 1,5px schmaler Rand war überhaupt
  klickbar) - das ist vermutlich die eigentliche, dominante Ursache für
  "Positionen werden nicht übernommen": die Box hat sich beim Ziehen
  schlicht nie sichtbar bewegt. Behoben mit einer Bewegungs-Schwelle
  (4px): ein Klick auf die Box startet immer einen potenziellen Zug,
  aber erst nach echter Bewegung wird tatsächlich verschoben - ein
  reiner Klick setzt weiterhin ganz normal den Textcursor.

  Beide Fixes zusammen in einer echten Playwright-Chromium-Sitzung
  verifiziert: Box tatsächlich per simulierten Maus-Events verschoben,
  "Anwenden" geklickt, Ausgabebild neu per OCR gelesen - ursprüngliches
  "Hello World" verschwunden, "Hallo" an der neuen Position gefunden,
  unbeteiligte zweite Zeile unverändert.

**2) Fontgröße - approximativ, wie gewünscht ("annähernd, nicht
genau"):** Der Renderer hat schon seit längerem eine Heuristik zur
Schätzung der Schriftgröße aus der Zeilenhöhe der erkannten Box
(`_initial_font_size()`), die aber nie in der Korrektur-Ansicht
ankam - dort stand immer ein fester, unabhängiger 13px-Wert. Über
`estimated_font_size()` jetzt öffentlich gemacht und bis in
`report.py`/`review_server.py` durchgereicht: die Box in der
Korrektur-Ansicht zeigt den Text jetzt ungefähr in der Größe, in der er
später tatsächlich gerendert wird - keine echte Font-Familien-Erkennung
(dafür bräuchte es einen trainierten Klassifikator, siehe letzter
Eintrag), aber genau die von Michael selbst als ausreichend genannte
Annäherung bei der Größe.

**3) Fehlende Liste links ("Buch in der Kugel") - KEIN neuer Bug,
sondern derselbe, bereits bekannte Kompromiss vom 24.08.2026:**
Geprüft am Original-Bild (`Spirit - Soul - Meatsuit.jpg`) und den
Diagnose-Bildern aus `paddle_probe_out/`. Der rohe OCR-Texterkenner
findet jeden Listeneintrag ("Thoughts, Emotions, Choices, Beliefs,
Trauma, Karma, Experiences...") einzeln korrekt - aber PaddleOCRs
LAYOUT-Klassifikator (ein separater Schritt) stuft den gesamten
Abschnitt als EIN einziges, niedrig-sicheres (`0.56`) "image"-Feld ein.
Genau dieser Fall wurde am 24.08.2026 schon einmal bearbeitet: Übersetzen
von "image"-Feldern mit echtem Text wurde ausprobiert → noch am selben
Tag zurückgerollt, weil es laut deinem eigenen Feedback ("Das ist jetzt
noch schlimmer als das vorherige") eine Verschlechterung war → der
Revert selbst löste eine NEUE Regression aus (Textüberlappung, weil das
Feld für die Kollisionsvermeidung unsichtbar wurde) → behoben durch
`translatable=False` (Feld bleibt als Hindernis erhalten, wird aber
nicht übersetzt) - das ist der aktuelle, bewusst so gewählte Zustand.
Ich habe das NICHT eigenmächtig wieder geändert, weil genau dieser Weg
schon zweimal zu einer Regression geführt hat - das braucht erst eine
Entscheidung von dir, siehe Chat-Antwort.

**Getestet:** neue Unit-Tests für alle drei Backends (Original wird
gelöscht, neue Position wird gezeichnet, Maske deckt beide Stellen ab),
für `build_corrected_replacements()`, `replacements_from_region_list()`
und `review_server.py`s HTTP-Schicht (inkl. Wiedereröffnen einer
Korrektur-Runde auf einem bereits korrigierten Bild). Zusätzlich eine
eigenständige, nicht in der Suite enthaltene Playwright-Reproduktion
mit echten Maus-Events gegen eine echte Chromium-Instanz (siehe oben).
Gesamter Testlauf (`tests/`, ohne `test_ui_images_mode.py`): 254
passed (vorher 249), 1 skipped. `webapp/`-Schicht weiterhin nachweislich
ohne `PySide6`-Import.

## 26.08.2026 - Klarstellung zum Resize-Fix + "Buch in der Kugel"-Liste jetzt tatsächlich übersetzt (Zeile für Zeile statt als ein Block)

**Klarstellung zum Drag-Fix von eben:** Michael wies zurecht darauf hin,
dass er nie Probleme mit dem Ziehen/Verschieben hatte - er benutzt
ausschliesslich das Greifkästchen unten rechts zum Vergrössern/
Verkleinern. Zur Einordnung: dieses Kästchen hat schon immer
funktioniert und wurde vom Drag-Bug gar nicht berührt - es hat einen
eigenen, komplett separaten Event-Listener (`makeResizable()`,
`e.stopPropagation()`), der nie mit dem betroffenen Code
(`makeDraggable()`) in Berührung kommt, und ändert grundsätzlich nur
Breite/Höhe, nie die Position (die obere linke Ecke bleibt beim
Grösse-Ändern immer fest). Der Drag-Fix von eben betrifft ausschliesslich
das direkte Anklicken und Ziehen der Box SELBST (nicht des
Eckkästchens), um sie zu VERSCHIEBEN ohne die Grösse zu ändern - das
hat Michael nach eigener Aussage nie benutzt, war also nicht die
Ursache seines eigentlichen Problems. Der wirkliche Übeltäter für
"Korrekturen werden nicht übernommen" war der Architektur-Bug
(`render_box`/Lösch-Logik) - unabhängig davon, mit welcher Maus-Geste
korrigiert wurde. Der Drag-Fix bleibt trotzdem sinnvoll (jetzt
tatsächlich funktionsfähig für den Fall, dass jemand die Box direkt statt
über das Eckkästchen verschieben will), war aber nicht die Erklärung für
Michaels konkreten Fall - das war zu Unrecht so dargestellt.

**"Buch in der Kugel"-Liste: Michaels Einwand berechtigt, jetzt richtig
gelöst statt nur dokumentiert.** Michael: "Wenn das als Bild gesehen
wird, sollte das Bild doch auch extrahiert und übersetzbar sein. Google
Vision kann es ja auch. [...] Leer lassen ist keine Option." Der
"richtige Fix", den der 24.08.2026-Eintrag schon damals als noch nicht
umgesetzt benannt hatte ("jede der 9 kurzen OCR-Zeilen [...] müsste als
EIGENE kleine Region an ihrer EIGENEN ursprünglichen Position übersetzt
und gezeichnet werden, statt zu einem Absatz zusammengefasst zu
werden"), ist jetzt gebaut: `pipeline/images/ocr.py`s neue
`_paddle_block_to_line_regions()` gibt für einen "image"-klassifizierten
Block mit echtem Text (`_PADDLE_SCATTERED_TEXT_LABELS`) zusätzlich zum
bisherigen, weiterhin als Hindernis geführten Gesamt-Block JEDE
zugeordnete OCR-Zeile als eigene, kleine, unabhängig übersetzbare Region
an ihrer eigenen Original-Position zurück - genau der Fix, der beim
ersten Versuch (23./24.08.2026) noch fehlte, als alle 9 Labels zu EINEM
Absatz zusammengefasst und als ein Textklumpen über den Nachbarblock
gezeichnet wurden ("Version 13 ist schlechter als Version 12"). Der
Gesamt-Block bleibt zusätzlich als `translatable=False`-Hindernis
bestehen, damit Nachbar-Regionen weiterhin nicht seitlich in die leeren
Zwischenräume zwischen den Labels hineinwachsen können (derselbe Schutz
wie beim vorherigen, dritten Versuch).

**Beim Testen mit dem echten Ergebnis-JSON gefunden und behoben, bevor
es zu einem sichtbaren Fehler wurde:** Der "image"-Block
[25,457,394,718] überlappt am oberen rechten Rand leicht mit dem
Bounding-Box des direkt benachbarten, bereits normal übersetzbaren
Banner-Blocks "WHEREEXPERIENCES,PATTERNS&DISTORTIONSLIVE" ([333,457,
733,476]). Eine einzelne OCR-Zeile ("WHERE") liegt mit ihrem
Mittelpunkt in BEIDEN Boxen - ohne Gegenmassnahme wäre sie ein zweites
Mal, unabhängig vom Banner, übersetzt und gezeichnet worden, direkt
über der bereits korrekten Banner-Übersetzung. Behoben durch einen
Vorab-Durchlauf über alle Blöcke (`claimed_line_indices` in
`recognize()`): jede OCR-Zeile, die bereits zu einem normal
übersetzbaren Block gehört, wird beim Aufsplitten des "image"-Blocks
ausgeschlossen. Ohne einen echten, vorhandenen Diagnose-Datensatz
(`paddle_probe_out/`) wäre dieser Randfall vermutlich erst bei Michael
aufgefallen.

**Echter Rendertest gegen das tatsächliche Bild (nicht nur Unit-Tests) -
gegeben die Vorgeschichte dieser Stelle (dreimal in Folge am 24.08.2026
regressiert) Pflicht, nicht optional:** Mit dem bereits vorhandenen,
echten PaddleOCR-Ergebnis (`paddle_probe_out/.../_res.json`) und einer
kleinen Wörterbuch-Übersetzung ("Thoughts"→"Gedanken" usw.) den
kompletten `translate_image()`-Lauf gegen die echte Bilddatei
ausgeführt und das Ergebnis visuell geprüft: alle 9-10 Listeneinträge
(Thoughts, Emotions, Choices, LEDGER, Beliefs, Trauma, Karma,
Experiences, "...aufgezeichnet als", PATTERNS) erscheinen jetzt einzeln,
an ihrer ursprünglichen Position um die Kugel-Grafik verteilt, lesbar,
ohne Überlappung mit dem Banner oder dem Titel darüber - keine
Wiederholung der Version-13-Verschlechterung.

**Ein kleiner, verbleibender Schönheitsfehler, ehrlich gemeldet statt
verschwiegen:** An genau einer Stelle sitzen zwei der neuen kleinen
Regionen ("...aufgezeichnet als" und "MUSTER") vertikal eng
übereinander - im Original waren das zwei kurze, eng gesetzte Zeilen
derselben Bildunterschrift. Die deutsche Übersetzung von "...rocorded
as" ist länger als das Original und bricht in der schmalen Box auf zwei
Zeilen um; für diesen Fall reicht der verfügbare Vertikal-Abstand zur
Nachbar-Region "MUSTER" knapp nicht, sie berühren sich leicht
("alsMUSTER"). Das ist keine neue Regression, sondern dieselbe, bereits
in `_vertical_room_below()`s eigenem Docstring dokumentierte,
allgemeine Grenze des Renderers (Schrumpfen bis zu einer Mindestgrösse,
danach wird ein Überlappen in Kauf genommen, statt bis zur
Unleserlichkeit zu schrumpfen) - sie betrifft grundsätzlich jedes eng
stehende Regionenpaar mit wachsender Übersetzung, wird hier nur zum
ersten Mal sichtbar, weil dieser Bereich vorher ein einziger,
unübersetzter Block war. Über die Korrektur-Ansicht von Hand leicht zu
beheben (Box verschieben/vergrössern); eine generelle Verbesserung des
Vertikal-Abstands wäre ein eigenes, separates Thema.

**Getestet:** `test_paddleocr_recognize_translates_an_image_labeled_
blocks_lines_individually` umgebaut (prüft jetzt: Gesamt-Block bleibt
Hindernis, jede Zeile erscheint zusätzlich einzeln). Neuer Test
`test_paddleocr_recognize_does_not_duplicate_a_line_already_claimed_by_
a_translatable_block` (bildet die echte WHERE-Überlappung nach).
Zusätzlich der oben beschriebene echte End-to-End-Rendertest gegen das
tatsächliche Bild und das echte, gespeicherte PaddleOCR-Ergebnis
(nicht Teil der automatisierten Suite). `tests/test_image_ocr.py`
allein: 43 passed (vorher 42). Gesamter Testlauf (`tests/`, ohne
`test_ui_images_mode.py`): 255 passed (vorher 254), 1 skipped.

## 27.08.2026 - Web-View-Einstellungen wurden nie gespeichert (nur gelesen); Korrektur-Runde verlor Kollisionsschutz für nicht übersetzte Regionen

Michaels Meldung, mit zwei Screenshots und einem echten QA-Bericht
belegt: "Im Web View werden die Einstellungen der vorigen Sitzung nicht
gespeichert. Ist das noch machbar?" und: "Nachdem ich die Felder und
den Text korrigiert habe, wurde zwar Bild gespeichert, aber nicht so
wie ich es im Browser korrigiert hatte." Zwei getrennte, echte Bugs,
in dieser Reihenfolge untersucht und behoben.

**Bug 1 - Einstellungen wurden nur gelesen, nie geschrieben:**
`webapp/settings_store.py::load()` wird zwar an zwei Stellen aufgerufen
(`build_config()` zum Vorbefüllen von `/api/config`, und als
`max_chars`-Fallback in `start_job()`) - `save()` dagegen wurde im
gesamten Code (`webapp/*.py` und `webapp/static/app.js`, per grep
geprüft) an KEINER Stelle aufgerufen. Die Schreibseite fehlte schlicht
komplett, seit dieses Modul existiert - kein Regressions-, sondern ein
von Anfang an unvollständiges Feature.

Behoben in `webapp/job_bridge.py::start_job()`: sobald eine
Job-Anfrage alle serverseitigen Prüfungen bestanden hat (Zugangsdaten,
OCR-Engine, Rückschreibe-Methode, Validierung - siehe RoadMap.md-
Leitprinzip), werden genau die Felder gespeichert, die
`ui/app.py::_persist_form_state()` für die Qt-App auch immer schon
persistiert hat (Anbieter, Ausgangs-/Zielordner, Ausgangs-/Zielsprache,
geschützte Begriffe, OCR-Engine, Rückschreibe-Methode). Bewusst beim
tatsächlichen Start eines Laufs statt bei jeder Tastatureingabe -
es gibt keinen eigenen Endpunkt für Zwischenstände, und ein Lauf-Start
ist der Moment, der `closeEvent()`s eigenem "was der Nutzer wirklich
übernommen hat" am nächsten kommt. Eine abgelehnte Anfrage (z.B.
fehlender API-Schlüssel) erreicht diesen Code-Pfad nicht - ein
Tippfehler im Formular überschreibt also nie eine zuvor gespeicherte,
funktionierende Einstellung.

Da beim Testen dieser Änderung auffiel, dass mehrere bestehende Tests
in `tests/test_webapp_jobs_api.py` durch diesen neuen echten
`save()`-Aufruf plötzlich in die ECHTE Konfigurationsdatei des
jeweiligen Testrechners geschrieben hätten (z.B.
`~/.config/pdf-translator/settings.json` unter Linux) - genau die Art
Verschmutzung, die `tests/conftest.py`s bestehende QSettings-Isolation
für die Qt-App schon verhindert -, wurde eine gleichwertige, auf
`tests/test_webapp_jobs_api.py` begrenzte Isolation ergänzt
(`config_dir()` wird pro Test auf ein `tmp_path`-Verzeichnis
umgeleitet). Bewusst NICHT in `tests/conftest.py` selbst, weil
`tests/test_webapp_settings_store.py`s eigene `test_config_dir_*`-Tests
genau die echte Plattform-Fallunterscheidung in `config_dir()` prüfen
sollen - eine testweite Umleitung dort hätte diese Tests kaputt
gemacht.

**Bug 2 - Korrektur-Runde rendert anders als im Browser gesehen
("HAUPTBUCH"-Screenshot):** `pipeline.images.inpainting.
InpaintingBackend.apply()` bekommt seit dem 22.08.2026 einen
`obstacle_regions`-Parameter (Regionen, die nicht neu gezeichnet
werden, deren Originalpixel aber noch sichtbar sind und deshalb beim
Größerwerden einer benachbarten Übersetzung respektiert werden müssen -
siehe `_vertical_room_below()`/`_horizontal_room()`). Beim
ursprünglichen Übersetzungslauf wird das schon korrekt befüllt
(`translate_image()`), aber `ui/image_job.py::run_image_correction_job()`
- die Funktion, die JEDE Korrektur-Runde tatsächlich rendert, sowohl im
Qt-Dialog (`ui/image_correction_dialog.py`) als auch im neuen
Web-View-Pfad (`webapp/review_bridge.py`) - hat diesen Parameter beim
`apply()`-Aufruf noch NIE weitergereicht. Das war bislang folgenlos,
weil eine Korrektur-Runde meist keine eigenen Hindernis-Regionen hatte
- seit dem gerade erst ausgelieferten Listen-Übersetzungs-Fix (Eintrag
vom 26.08.2026, "Buch in der Kugel") hat aber JEDES Bild mit einem
solchen Listen-Block jetzt einen dauerhaften, unübersetzten
Hindernis-Block ("image"-Label) - genau der Fall, den Michaels
"HAUPTBUCH"-Bild betrifft.

Behoben an allen drei Stellen: `ui/image_job.py::run_image_correction_
job()` reicht `obstacle_regions` jetzt an `apply()` durch und faltet sie
zusätzlich in das zurückgegebene `stats.regions`, damit eine ZWEITE
Korrektur-Runde denselben Schutz nicht wieder verliert.
`ui/image_correction_dialog.py` und `ui/app.py::_open_image_correction_
dialog()` berechnen die Hindernis-Regionen genau wie
`translate_image()` selbst (identitätsbasiert: alles in `stats.regions`,
was nicht in `stats.replacements` vorkommt) und reichen sie durch.
`webapp/job_bridge.py::get_correctable_file()` liefert sie jetzt als
fünftes Tupel-Element, `webapp/review_bridge.py::start_correction()`
reicht sie an `run_image_correction_job()` weiter.

**Ehrlich dazu gesagt, statt es zu verschweigen:** Eine Nachstellung mit
dem echten Bild und dem echten, gespeicherten PaddleOCR-Ergebnis (LEDGER
→HAUPTBUCH, unverändertes `render_box`) zeigte MIT und OHNE
`obstacle_regions` keinen sichtbaren Unterschied - der Fix ist also
real und durch eigene Tests belegt, erklärt aber vermutlich nicht
allein das exakte Erscheinungsbild in Michaels Screenshot. Eine zweite
Nachstellung, bei der zusätzlich die `render_box` der LEDGER-Region
künstlich vergrössert wurde (simuliert ein Ziehen am Grössenziehpunkt,
wie Michael ihn tatsächlich benutzt), erzeugte ein deutlich
grösseres, über den Rand der Grafik hinausragendes "HAUPTBUCH" mit
sichtbarem Hintergrund-Rechteck - eine teilweise, aber nicht exakte
Übereinstimmung mit dem gemeldeten Bild. Vermutung: eine Kombination
aus dem jetzt behobenen `obstacle_regions`-Fehlen UND dem inhärenten
Verhalten von `_fit_text()` (wählt die grösstmögliche, noch passende
Schriftgrösse für die vergrösserte Box) plus `BoxOverlayBackend`s
Hintergrund-erst-dann-Text-Vorgehen bei einer stark vergrösserten Box -
letzteres wäre kein Bug, sondern erwartetes Verhalten bei einer sehr
grossen Handkorrektur, aber noch nicht abschliessend an Michaels
genauem Fall verifiziert.

**Getestet:** `tests/test_image_correction_job.py`, drei neue Tests -
`test_correction_job_without_obstacle_regions_can_overwrite_a_real_
neighbour` (belegt den alten Fehler), `test_correction_job_passes_
obstacle_regions_through_and_protects_a_real_neighbour` (belegt den
Fix), `test_correction_job_folds_obstacle_regions_into_the_returned_
stats_regions` (belegt die Weitergabe an eine zweite Korrektur-Runde).
`tests/test_webapp_jobs_api.py`, zwei neue Tests -
`test_start_job_persists_form_state_for_the_next_session` (belegt
Bug 1s Fix end-to-end über echte HTTP-Aufrufe, inklusive `/api/config`
danach), `test_start_job_does_not_persist_a_rejected_request` (belegt,
dass eine abgelehnte Anfrage nichts überschreibt). Gesamter Testlauf
(`tests/`, ohne `test_ui_images_mode.py`): 260 passed (vorher 255),
1 skipped.

**Noch offen, aus derselben Meldung:** Font-Editierung im Korrektur-
Browser-Fenster (Familie/Stil) fehlt weiterhin - noch nicht begonnen,
vermutlich ein eigenes, grösseres Thema wie schon die
Font-Erkennung selbst. Michaels Vorschlag, die Korrektur nicht das
Original überschreiben zu lassen, sondern als separate Datei zu
speichern, ist bewusst noch nicht umgesetzt - das würde vom
bisherigen, mit `run_pdf_correction_job()` geteilten Entwurf abweichen
("Übernehmen" ersetzt die bestehende Übersetzung, analog zur PDF-
Variante) und sollte erst mit Michael abgestimmt werden, bevor daran
etwas geändert wird.
