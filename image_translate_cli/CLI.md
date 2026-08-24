# image_translate_cli

Eigenständige, dokumentierte Kommandozeilen-/Subprocess-Schnittstelle für
die Bildübersetzung (`pipeline/images/`) dieses Projekts - gebaut, damit
andere Programme (zuerst
[TME](https://github.com/MiSte-Git/TME), das aktuell auf demselben Rechner
läuft, aber später auch eigenständig laufen soll) sie einbinden können,
ohne an interne, noch in Bewegung befindliche PDF-Translator-APIs gekoppelt
zu sein. Hintergrund und Entscheidung: `Backlog.md`, Abschnitt "Geplant"
("Bildübersetzung als eigenständige, in andere Programme einbindbare
Schnittstelle bauen", 22.08.2026) und "Ideen / später bewerten"
("Cross-Projekt: Bildübersetzung als Basis für TME", 21.08.2026).

Die Schnittstelle ist bewusst schmal: **Config-Datei + Bildpfad(e) rein,
übersetzte Bilder + JSON-Report raus.** Kein Zustand zwischen Aufrufen,
keine Rückrufe/Callbacks, keine Abhängigkeit von `ui/` oder sonstigen
PDF-Translator-internen Modulen außer `pipeline/`.

## Workflow: Vorschau, Korrektur, Ergebnis

Der vorgesehene Ablauf für einen Aufrufer, der dem Nutzer eine Korrektur-
Möglichkeit anbieten will (22.08.2026, Michael: "Ich schicke ein Bild in
die CLI, bekomme eine Vorschau um etwaige Korrekturen zu machen und
bekomme dann ein übersetztes Bild zurück"):

1. **`translate`** übersetzt das Bild wie gewohnt UND liefert im Report zu
   jedem Bild eine editierbare Liste aller übersetzten Textregionen
   (`results[].regions` - Position, Originaltext, übersetzter Text). Das
   übersetzte Bild selbst dient dabei schon als Vorschau.
2. Der Aufrufer zeigt diese Vorschau + Regionenliste in SEINER eigenen
   Oberfläche an (Tabelle, Canvas, Chat-Rückfrage - was zur jeweiligen App
   passt) und lässt den Nutzer `translated_text` (und optional Position/
   Größe) einzelner Regionen bearbeiten.
3. **`correct`** rendert mit der bearbeiteten Regionenliste GEGEN DAS
   ORIGINALBILD neu - ohne erneutes OCR, ohne erneuten Provider-Aufruf,
   ohne zusätzliche Kosten. Das Ergebnis ist das endgültige übersetzte
   Bild.

Schritt 3 lässt sich beliebig oft wiederholen (`correct`s eigener Report
enthält wieder eine frische `regions`-Liste, direkt einsetzbar für eine
weitere Korrekturrunde). Für Schritt 2+3 zusammen gibt es zwei Varianten:

- **Eigene Oberfläche des Aufrufers** (Schritte 2 und 3 getrennt, wie
  oben beschrieben) - die interaktive Oberfläche ist NICHT Teil dieser
  Schnittstelle, jede App bringt ihre eigene Art der Interaktion mit
  (Tabelle, Canvas, Chat-Rückfrage); geteilt wird nur der Datenaustausch
  und der Re-Render-Mechanismus, damit niemand ihn selbst nachbauen muss
  (mirrors `ui/image_job.py::run_image_correction_job()`, das genau
  dasselbe für PDF-Translators eigene Desktop-UI leistet).
- **`review`** (22.08.2026, Michael: "Ich möchte aber gerne die Korrektur
  Logik mit UI auslagern. Ansonsten muss jede App das gleiche nochmal
  bauen.") - deckt Schritt 2 UND 3 in einem Kommando ab: startet einen
  lokalen Server, öffnet eine Korrektur-Seite im Browser, und rendert nach
  Klick auf "Anwenden" selbst neu. Für einen Aufrufer, der KEINE eigene
  Korrektur-Oberfläche bauen will (z. B. TME) - siehe eigener Abschnitt
  unten.

## Voraussetzungen

Läuft aktuell in derselben Python-Umgebung wie PDF-Translator (siehe
Haupt-`README.md`: Python 3.10+, `requirements.txt`, für OCR zusätzlich
`requirements-ocr.txt` inkl. des Tesseract-Systempakets). Ein wirklich
eigenständiger Build (kein PDF-Translator-Checkout mehr nötig) ist bewusst
NICHT Teil dieser ersten Version - siehe `Backlog.md`, Punkt
"Deployment-Lösung": erst relevant, falls TME (oder ein anderer Aufrufer)
tatsächlich ohne denselben Rechner/dieselbe Umgebung auskommen muss.

## Kommandos

### `check` - Verfügbarkeit prüfen, ohne zu übersetzen

```bash
python -m image_translate_cli.cli check --config config.json
```

Prüft, ohne irgendeine OCR-/Übersetzungs-API zu bemühen:

- ob für `config.json`s `provider` Zugangsdaten konfiguriert sind
  (Umgebungsvariable oder OS-Keyring, siehe `pipeline/credentials.py`),
- ob `config.json`s `ocr.backend` auf diesem Rechner verfügbar ist
  (aktuell nur `tesseract`: Binary muss auf PATH liegen),
- ob `config.json`s `inpainting.backend` verfügbar ist (`box_overlay` und
  `cv_inpainting` immer; `gpu_inpainting` nur mit ausreichend starker
  CUDA-GPU).

Exit-Code `0`, wenn alle drei Prüfungen bestehen, sonst `1` (Details stehen
in der Ausgabe). Config-Fehler (siehe unten) geben `2`. Gedacht als
Preflight-Check, bevor ein Aufrufer wie TME einen echten `translate`-Lauf
anstößt.

### `translate` - Bild(er) übersetzen

```bash
python -m image_translate_cli.cli translate \
    --config config.json \
    --input bild1.png bild2.png \
    --output-dir ./translated \
    [--report report.json] \
    [--dry-run] \
    [--yes]
```

oder mit einem ganzen Ordner (nicht rekursiv, alle Dateien mit einer
Endung aus `.png .jpg .jpeg .bmp .tif .tiff .webp`):

```bash
python -m image_translate_cli.cli translate \
    --config config.json --input-dir ./screenshots --output-dir ./translated
```

`--input` und `--input-dir` schließen sich gegenseitig aus, genau eines ist
Pflicht. `--output-dir` wird bei Bedarf angelegt. Jedes übersetzte Bild
landet unter seinem ursprünglichen Dateinamen im Zielordner; ein Namens-
konflikt innerhalb desselben Laufs (z. B. zwei `--input`-Pfade aus
verschiedenen Ordnern mit demselben Dateinamen) bekommt einen numerischen
Suffix (`bild (2).png`). Ein erneuter Lauf mit demselben `--output-dir`
überschreibt absichtlich die Ausgabe eines vorherigen Laufs.

`--report` schreibt den JSON-Report (siehe unten) in eine Datei; ohne
`--report` geht er auf stdout.

`--dry-run` führt nur lokale OCR aus (kein Provider-Aufruf, keine
Rückschreibung, nichts wird gespeichert) und gibt eine geschätzte
Zeichenzahl und Kostenschätzung aus - siehe "Bekannte Grenzen" unten für
die Genauigkeit dieser Schätzung.

`--yes` erteilt die Kostenbestätigung automatisch, unabhängig davon, was
`config.json`s `budget.confirm` sagt - für nicht-interaktive Aufrufer wie
TME, die nicht auf eine y/n-Konsolenabfrage warten können.

**Exit-Codes:** `0` = alle Bilder mit Status `ok`/`cancelled` verarbeitet;
`1` = mindestens ein Bild mit Status `failed`; `2` = Config- oder
Argumentfehler, nichts wurde versucht.

### `correct` - Bild mit bearbeiteten Regionen neu rendern

```bash
python -m image_translate_cli.cli correct \
    --source original.png \
    --regions edited_regions.json \
    --output corrected.png \
    [--inpainting-backend box_overlay] \
    [--report report.json]
```

Kein OCR, kein Provider-Aufruf, kein `--config` nötig - siehe "Workflow:
Vorschau, Korrektur, Ergebnis" oben für den Gesamtablauf, den dieses
Kommando abschließt.

- `--source` (Pflicht): die **PRISTINE, unveränderte** Originaldatei -
  NIEMALS die bereits übersetzte Datei oder eine frühere Korrektur.
  `InpaintingBackend.apply()` rendert jeden Aufruf komplett neu gegen
  `--source`; wird hier versehentlich ein bereits übersetztes Bild
  übergeben, legt sich die Korrektur über die vorherige Übersetzung
  statt sie zu ersetzen.
- `--regions` (Pflicht): Pfad zu einer JSON-Datei - eine Liste von
  Objekten in genau der Form, die `translate`s (oder eines vorherigen
  `correct`-Laufs) Report unter `results[].regions` liefert. Pflichtfelder
  pro Eintrag: `x`, `y`, `width`, `height`, `translated_text`;
  `confidence`/`original_text`/`index` sind optional (werden ignoriert
  bzw. mit Default `0.0`/`""` versehen, falls nicht gebraucht). Die
  Reihenfolge der Einträge spielt keine Rolle - jeder Eintrag ist
  eigenständig (eigene Position/Größe), `index` dient nur der
  menschlichen Lesbarkeit.
- `--output` (Pflicht): Zieldatei für das neu gerenderte Bild.
- `--inpainting-backend` (optional, Default `box_overlay`): sollte
  normalerweise zum ursprünglichen `translate`-Lauf passen (siehe
  `config.json`s `inpainting.backend`), muss es aber technisch nicht -
  eine andere Wahl rendert einfach mit einem anderen Backend neu.
- `--report`: wie bei `translate` - JSON-Report in eine Datei statt auf
  stdout.

**Exit-Codes:** `0` = erfolgreich neu gerendert; `1` = das Rückschreiben
ist fehlgeschlagen (`InpaintingError`, z. B. Datei nicht schreibbar); `2`
= `--source` fehlt, `--regions` ist fehlerhaft, `--output` ist identisch
mit `--source`, oder `--inpainting-backend` ist unbekannt.

### `review` - Bild interaktiv im Browser korrigieren und neu rendern

```bash
python -m image_translate_cli.cli review \
    --source original.png \
    --regions results_regions.json \
    --output corrected.png \
    [--inpainting-backend box_overlay] \
    [--report report.json] \
    [--host 127.0.0.1] [--port 0] [--no-browser] [--timeout 1800]
```

`review` ist `correct` samt der Korrektur-Oberfläche selbst: statt eine
bereits fertig bearbeitete `--regions`-Datei entgegenzunehmen, zeigt es die
STARTREGIONEN (typischerweise `translate`s `results[].regions`) in einer
Browser-Seite an - Textboxen über dem Originalbild, per Zeigegerät/Touch
verschieb- und skalierbar, Text direkt anklickbar/editierbar - und rendert
erst neu, sobald im Browser auf "Anwenden" geklickt wird. `--source` und
`--regions` haben dieselbe Bedeutung wie bei `correct`; `--output` ist die
Zieldatei, die erst nach "Anwenden" geschrieben wird.

Ablauf: Der Server startet lokal, die URL wird auf stdout ausgegeben, ein
Browser-Tab öffnet sich automatisch (`--no-browser` unterdrückt das, falls
der Aufrufer die URL selbst in einem eigenen Fenster/WebView öffnen will).
`review` **blockiert**, bis im Browser "Anwenden" oder "Abbrechen" geklickt
wird (oder `--timeout` Sekunden ohne Aktion vergehen, Default 1800 = 30
Minuten, `0` = unbegrenzt warten) - kein Hintergrundprozess, ein einzelner
Aufruf pro Korrektur-Sitzung.

**Sicherheit:** Der Server bindet standardmäßig an `127.0.0.1` (`--host`),
ist also nur vom selben Rechner erreichbar, hat KEINE Authentifizierung
und liefert das Originalbild sowie die Regionen ungeschützt an jeden, der
die URL kennt. Passend für den aktuellen Anwendungsfall (TME läuft auf
demselben Rechner). Ein anderer `--host`-Wert (z. B. für ein Gerät im
selben Netz, etwa ein Tablet als reine Anzeige) ist technisch möglich,
aber dann liegt Absicherung (Netzsegment, ggf. ein vorgeschalteter
Reverse-Proxy mit Auth) beim Aufrufer - `review` bringt dafür nichts mit.

Es lassen sich keine Regionen hinzufügen/entfernen (siehe "Bekannte
Grenzen" unten) - nur Text/Position/Größe der übergebenen Regionen sind
editierbar, genau wie bei `correct`.

**Exit-Codes:** `0` = "Anwenden" geklickt, erfolgreich neu gerendert; `1`
= Rückschreibfehler ODER Zeitüberschreitung ohne Aktion; `2` = `--source`/
`--regions`/`--output`/`--inpainting-backend`-Fehler (wie bei `correct`,
vor dem Öffnen des Browsers geprüft); `3` = im Browser "Abbrechen"
geklickt, keine Ausgabedatei geschrieben.

## Config-Schema

JSON-Datei, per `--config` übergeben. `schema_version` ist Pflicht und
muss `1` sein (siehe "Versionierung" unten). Enthält **niemals**
Zugangsdaten - die werden wie im Rest des Projekts über
`pipeline/credentials.py` aufgelöst (Umgebungsvariable, dann OS-Keyring),
sodass eine Config-Datei bedenkenlos geloggt, versioniert oder an ein
anderes Programm weitergegeben werden kann.

```json
{
  "schema_version": 1,
  "provider": "deepl",
  "target_lang": "de",
  "source_lang": null,
  "protected_terms": ["ACME"],
  "ocr": {
    "backend": "tesseract",
    "language": "eng",
    "min_confidence": 40.0,
    "max_height_ratio": 4.0
  },
  "inpainting": {
    "backend": "box_overlay"
  },
  "budget": {
    "max_chars_per_run": 200000,
    "confirm": true
  }
}
```

Feldreferenz:

- `schema_version` (Pflicht): Config-Schema-Version, aktuell immer `1`.
- `provider` (Pflicht): `"deepl"`, `"google"`, `"openai"` oder `"grok"`.
- `target_lang` (Pflicht): Zielsprachcode, z. B. `"de"`.
- `source_lang` (optional, Default `null`): Quellsprachcode; `null` lässt
  den Provider automatisch erkennen (nicht jeder Provider unterstützt das
  gleich gut - siehe `pipeline/translation/base.py`).
- `protected_terms` (optional, Default `[]`): Begriffe, die unübersetzt
  bleiben sollen (z. B. ein Produkt-/Markenname), siehe
  `pipeline/translation/protected_terms.py`.
- `ocr.backend` (optional, Default `"tesseract"`): aktuell einziger
  gültiger Wert; ein Cloud-OCR-Backend ist laut RoadMap.md geplant.
- `ocr.language` (optional, Default `null`): Engine-spezifischer
  Sprach-Hinweis (Tesseract: 3-Buchstaben-Code, z. B. `"eng"`, `"deu"`).
- `ocr.min_confidence` (optional, Default `40.0`): Mindest-OCR-Konfidenz
  (0-100), unterhalb derer eine Textregion übersprungen statt übersetzt
  wird, siehe `pipeline/images/translate_image.py`.
- `ocr.max_height_ratio` (optional, Default `4.0`): siehe dieselbe Datei -
  Ausreißerschutz gegen als Text fehlerkannte Icons/Grafiken.
- `inpainting.backend` (optional, Default `"box_overlay"`): `"box_overlay"`
  (immer verfügbar), `"cv_inpainting"` (klassisches OpenCV-Inpainting) oder
  `"gpu_inpainting"` (LaMa/CUDA, braucht eine ausreichend starke GPU -
  siehe `check`).
- `budget.max_chars_per_run` (optional, Default `200000`): harte
  Zeichenobergrenze pro `translate`-Lauf, siehe
  `pipeline/translation/cost_control.py`.
- `budget.confirm` (optional, Default `true`): ob vor dem eigentlichen Lauf
  eine Kostenbestätigung nötig ist (per `--yes` auf der Kommandozeile
  übersteuerbar).

## JSON-Report-Schema

Von `translate` erzeugt (siehe `--report`). `schema_version` ist unter
`REPORT_SCHEMA_VERSION` in `image_translate_cli/report.py` versioniert
(unabhängig von der Config-Schema-Version).

```json
{
  "schema_version": 1,
  "tool": "image_translate_cli",
  "started_at": "2026-08-22T07:44:48.978375+00:00",
  "finished_at": "2026-08-22T07:44:49.381597+00:00",
  "config": { "...": "die aufgelöste Config, siehe oben" },
  "results": [
    {
      "input": "bild1.png",
      "output": "translated/bild1.png",
      "status": "ok",
      "translated": 8,
      "skipped": 1,
      "failed": 0,
      "chars_sent": 342,
      "errors": [],
      "error": null,
      "regions": [
        {
          "index": 0,
          "x": 21, "y": 71, "width": 108, "height": 28,
          "confidence": 76.6,
          "original_text": "Second line of text here.",
          "translated_text": "SECOND LINE OF TEXT HERE."
        }
      ]
    }
  ],
  "summary": {
    "images_planned": 1,
    "images_ok": 1,
    "images_cancelled": 0,
    "images_failed": 0,
    "total_chars_sent": 342,
    "estimated_cost_usd": null,
    "elapsed_seconds": 4.2
  }
}
```

`results[].status`:

- `"ok"` - der Lauf ist für dieses Bild durchgelaufen (unabhängig davon,
  wie viele EINZELNE Textregionen übersprungen/fehlgeschlagen sind - siehe
  `translated`/`skipped`/`failed`), die Ausgabedatei wurde geschrieben.
- `"cancelled"` - aktuell von `translate` nicht auslösbar (kein
  `should_cancel`-Callback über die CLI verdrahtet), im Schema für einen
  künftigen Aufrufer reserviert, der `translate_image()` direkt mit
  Abbruch-Unterstützung nutzt.
- `"failed"` - **fataler** Fehler für dieses eine Bild (OCR konnte gar
  nicht starten, oder das finale Rückschreiben ist fehlgeschlagen) - keine
  Ausgabedatei, `error` enthält die Meldung. Ein fehlgeschlagenes Bild
  bricht den restlichen Batch NICHT ab (mirrors `translate_image()`s
  eigene "eine schlechte Region bricht nicht das ganze Bild ab"-Regel,
  eine Ebene höher).

`errors` (pro Bild) enthält NUR fehlgeschlagene Einzelregionen (z. B. eine
Provider-Anfrage, die mit `TranslationError` fehlschlug) - das Bild selbst
bleibt dabei Status `"ok"`, die betroffene Region wird unverändert
gelassen.

`regions` (pro Bild) enthält jede ERFOLGREICH übersetzte und gerenderte
Region - leer bei Status `"failed"` (nichts wurde gerendert) und bei
`--dry-run` (nichts wird gerendert). Das ist exakt die Eingabeform für
`correct --regions` (siehe "Workflow: Vorschau, Korrektur, Ergebnis" und
den `correct`-Abschnitt oben) - ein Aufrufer entnimmt diese Liste, lässt
sie vom Nutzer bearbeiten und reicht sie unverändert in der Form, nur mit
editierten Werten, an `correct` weiter.

`summary.estimated_cost_usd` ist aktuell immer `null` (der echte Lauf
protokolliert tatsächlich gesendete Zeichen über
`pipeline/translation/cost_control.py`s Usage-Log, schätzt aber die
Kosten dafür nicht erneut) - für eine Kostenschätzung VOR dem Lauf siehe
`--dry-run`.

### `correct`s (und `review`s) Report

Etwas schmaler als `translate`s (kein `config`, kein `summary` - eine
reine Ein-Bild-Operation ohne Provider-/Kostenbezug). `review` erzeugt
dieselbe Form, nur mit `"command": "review"` statt `"command": "correct"`;
bei `review` und Status `"cancelled"` (im Browser abgebrochen) ist
`result.output` `null` und `result.regions` leer - kein Rückschreibversuch
fand statt.

```json
{
  "schema_version": 1,
  "tool": "image_translate_cli",
  "command": "correct",
  "started_at": "2026-08-22T09:38:12.707270+00:00",
  "finished_at": "2026-08-22T09:38:12.743797+00:00",
  "inpainting_backend": "box_overlay",
  "result": {
    "input": "original.png",
    "output": "corrected.png",
    "status": "ok",
    "translated": 1,
    "skipped": 0,
    "failed": 0,
    "chars_sent": 0,
    "errors": [],
    "error": null,
    "regions": [ "...", "wie bei translate, siehe oben" ]
  }
}
```

`result` ist ein einzelnes `ImageResult` (dieselbe Form wie ein Eintrag in
`translate`s `results[]`) - `result.regions` ist wieder direkt als Eingabe
für eine weitere `correct`-Runde nutzbar.

## Versionierung

`config.schema_version` und `report.schema_version` werden unabhängig
voneinander hochgezählt, jeweils nur bei einer Änderung, die die
Interpretation einer BESTEHENDEN Datei ändern würde (Feld entfernt,
Bedeutung/Typ eines Felds geändert, ein bisher optionales Feld wird
Pflicht). Ein neues optionales Feld mit abwärtskompatiblem Default
braucht KEINE Versionserhöhung. `check`/`translate` lehnen eine
unbekannte `config.schema_version` mit Exit-Code `2` und einer expliziten
Fehlermeldung ab, statt sie stillschweigend falsch zu interpretieren.

## Bekannte Grenzen

- `--dry-run`s Zeichen-/Kostenschätzung ist eine KONSERVATIVE
  Überschätzung: sie wendet `ocr.min_confidence` an, aber nicht den
  Ausreißerfilter `ocr.max_height_ratio` (der einen bereits über
  `min_confidence` gefilterten Median braucht - ein interner Helfer in
  `pipeline/images/translate_image.py`, nicht Teil dieser Schnittstelle).
  Der echte `translate`-Lauf wendet beide Filter an und sendet daher meist
  etwas weniger Zeichen als geschätzt.
- Kein Fortschritts-Callback über die CLI-Grenze hinweg - ein Aufrufer wie
  TME sieht Fortschritt aktuell nur pro fertig übersetztem Bild (eine
  Konsolenzeile pro Bild), nicht pro Textregion innerhalb eines Bildes.
  Für sehr große Batches ggf. später ergänzen (`--progress-file` o. ä.),
  aktuell nicht umgesetzt.
- `"cancelled"` ist im Report-Schema vorgesehen, aber von der CLI aktuell
  nicht auslösbar (siehe oben) - `translate_image()` selbst unterstützt
  Abbruch bereits, nur die CLI verdrahtet noch keinen Abbruch-Mechanismus
  (z. B. Signal-Handler).
- `correct`/`review` können nur bereits erfolgreich übersetzte Regionen
  bearbeiten (`translate`s `regions`-Liste) - eine Region, die `translate`
  wegen niedriger OCR-Konfidenz übersprungen hat oder deren Übersetzung
  fehlgeschlagen ist, taucht dort gar nicht erst auf und lässt sich weder
  über `correct` noch über `review` nachträglich hinzufügen (kein
  OCR/Provider-Zugriff hier - siehe "Workflow" oben). Ein Nachtrag für
  diesen Fall müsste erneut über `translate` laufen. Ebenso lässt sich
  über `review`s Browser-Oberfläche keine Region LÖSCHEN (nur Text/
  Position/Größe der vorhandenen bearbeiten) - dieselbe Grenze wie bei
  `correct`, nur in der UI sichtbar statt in der Datei.
- `review` hat keine Mehrbenutzer-/Mehrfach-Tab-Behandlung: der Server
  bearbeitet genau eine Korrektur-Sitzung und beendet sich nach dem ersten
  "Anwenden"/"Abbrechen" - ein zweiter geöffneter Tab auf dieselbe URL
  sieht denselben Zustand, aber ein zweites "Anwenden" nach dem ersten hat
  keine Wirkung mehr (Prozess ist bereits beendet).
- `review`s Vorschau im Browser ist eine Annäherung (Textbox-Overlay über
  dem Originalbild), kein Live-Rendering mit dem tatsächlichen
  `--inpainting-backend` - das würde bei jeder Änderung einen echten
  Rückschreibvorgang bedeuten. Das endgültige Ergebnis nach "Anwenden" kann
  daher in Feinheiten (Schriftgröße/-anpassung, Hintergrundfarbe bei
  `cv_inpainting`/`gpu_inpainting`) leicht von der Browser-Vorschau
  abweichen.

## Zugangsdaten für den Provider

`config.json`s `provider`-Feld wählt NUR aus, welcher Übersetzungsanbieter
verwendet wird - das ist unkritisch (siehe "Config-Schema" oben: darf
geloggt/versioniert werden). Der eigentliche API-Key wird davon getrennt
aufgelöst, genau wie überall sonst im Projekt (`pipeline/credentials.py`):
zuerst Umgebungsvariable (z. B. `DEEPL_API_KEY`), dann OS-Keyring unter dem
Service `"pdf-translator"`.

Das ist absichtlich so gebaut, damit ein Aufrufer wie TME **keine eigene
Provider-/Credential-Verwaltung für die Bildübersetzung braucht** - Provider
werden schließlich auch für normale Textübersetzung genutzt, eine zweite
Verwaltung nur für Bilder wäre doppelte Buchführung. TME muss seinen
bereits konfigurierten Key nicht in PDF-Translators Keyring duplizieren; es
reicht, ihn beim Subprocess-Aufruf als Umgebungsvariable für genau diesen
einen Aufruf zu setzen (Env-Var wird vor dem Keyring geprüft, siehe
`pipeline/credentials.py::get_api_key()`):

```python
subprocess.run(
    [...],
    env={**os.environ, "DEEPL_API_KEY": tme_eigener_key},
)
```

`check` (siehe oben) prüft transparent denselben Weg - ein per Env-Var
gesetzter Key wird dort genauso erkannt wie einer aus dem Keyring.

### Neue Provider hinzufügen

Die Provider-Liste ist bewusst offen gehalten (22.08.2026, Michael: "für
die Zukunft offen und dynamisch behalten") - `pipeline/registry.py` führt
dafür `PROVIDER_REGISTRY`/`register_provider()`/`ProviderSpec`: ein
`ProviderSpec` bündelt Name, Factory, `PricingModel` und
Credential-Check-Funktion in einem Objekt, `register_provider(spec)`
trägt es ein. `PROVIDER_FACTORIES` (die von `image_translate_cli/config.py`
zur Validierung genutzte Liste erlaubter `provider`-Werte) wird davon live
abgeleitet - eine neue Registrierung ist sofort und ohne Codeänderung an
`image_translate_cli` selbst sichtbar, weder in `config.py` noch in
`cli.py`.

Ein komplett neuer Provider braucht trotzdem etwas Code - eine neue API
lässt sich nicht per Config erfinden - aber genau EINEN, additiven
Schritt: eine Klasse, die `pipeline.translation.base.TranslationProvider`
implementiert (siehe `pipeline/translation/deepl_provider.py` als
Vorlage), plus ein `register_provider(ProviderSpec(...))`-Aufruf in
`pipeline/registry.py`. Kein Editieren von `image_translate_cli/config.py`,
`cli.py` oder der Desktop-UI nötig - alle drei lesen `PROVIDER_FACTORIES`/
`PROVIDER_REGISTRY` weiterhin nur aus, da beide Übersetzungswege (Text und
Bild) dieselbe Provider-Liste teilen.

## Für andere Programme (z. B. TME): Subprocess-Aufruf

```python
import json
import os
import subprocess

result = subprocess.run(
    [
        "python", "-m", "image_translate_cli.cli", "translate",
        "--config", "config.json",
        "--input", *image_paths,
        "--output-dir", str(output_dir),
        "--report", str(report_path),
        "--yes",
    ],
    cwd=PDF_TRANSLATOR_CHECKOUT,  # siehe "Voraussetzungen" oben
    env={**os.environ, "DEEPL_API_KEY": tme_eigener_key},  # siehe "Zugangsdaten für den Provider" oben
    capture_output=True,
    text=True,
)
report = json.loads(report_path.read_text(encoding="utf-8"))
if report["schema_version"] != 1:
    raise RuntimeError(f"unerwartete Report-Version: {report['schema_version']}")
failed = [r for r in report["results"] if r["status"] == "failed"]
```

`result.returncode` folgt der Exit-Code-Tabelle oben; der Report selbst
(nicht der Exit-Code) ist die maßgebliche Quelle für den Erfolg pro
einzelnem Bild, da ein Gesamtlauf mit `returncode == 1` trotzdem einige
erfolgreich übersetzte Bilder enthalten kann.

Dritte Variante, falls der Aufrufer KEINE eigene Korrektur-Oberfläche
bauen will (siehe "Workflow" oben und den `review`-Abschnitt): `review`
statt `correct` aufrufen - `review` blockiert bis der Nutzer im Browser
fertig ist, daher `capture_output=True` ohne Timeout (oder mit einem an
`--timeout` angepassten eigenen Subprocess-Timeout als zusätzliche
Absicherung):

```python
subprocess.run(
    [
        "python", "-m", "image_translate_cli.cli", "review",
        "--source", image_paths[0],
        "--regions", str(regions_path),  # z. B. report["results"][0]["regions"] als Startpunkt
        "--output", str(corrected_path),
        "--report", str(correction_report_path),
    ],
    cwd=PDF_TRANSLATOR_CHECKOUT,
    capture_output=True,
    text=True,
)
correction_report = json.loads(correction_report_path.read_text(encoding="utf-8"))
if correction_report["result"]["status"] == "cancelled":
    ...  # Nutzer hat im Browser abgebrochen (returncode 3), corrected_path existiert nicht
```

Zweiter Schritt, falls der Nutzer Korrekturen an `report["results"][0]
["regions"]` vorgenommen hat (siehe "Workflow: Vorschau, Korrektur,
Ergebnis" oben - `edited_regions` ist dieselbe Liste, mit vom Nutzer
bearbeiteten `translated_text`-Werten):

```python
regions_path.write_text(json.dumps(edited_regions), encoding="utf-8")
subprocess.run(
    [
        "python", "-m", "image_translate_cli.cli", "correct",
        "--source", image_paths[0],  # die PRISTINE Originaldatei, nicht report["results"][0]["output"]
        "--regions", str(regions_path),
        "--output", str(corrected_path),
        "--report", str(correction_report_path),
    ],
    cwd=PDF_TRANSLATOR_CHECKOUT,
    capture_output=True,
    text=True,
)
```
